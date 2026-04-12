#!/usr/bin/env python3
"""
Fetch everything Riot exposes for a single League match: match JSON + timeline,
plus optional Data Dragon **item.json** and **champion.json** for the match patch
(no API key; used by coaching digest / HTML).

Targets Ranked Summoner's Rift only (queue 420 Solo/Duo and 440 Flex) unless you
pass --allow-non-ranked-match with an explicit match id.

Requires RIOT_API_KEY in the environment (never commit keys to git).

Usage:
  export RIOT_API_KEY="RGAPI-..."
  python3 scripts/fetch_lol_match.py --match-id NA1_1234567890 --out ./exports/NA1_1234567890

  python3 scripts/fetch_lol_match.py --riot-id "Name#TAG" --platform na1 --out ./exports/latest

Match-V5 and Account-V1 use regional hosts (americas, europe, asia, sea). The script
infers the region from the match id prefix, or from --platform when resolving Riot ID.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

USER_AGENT = "lol-match-fetch/1.0 (educational; Riot API)"

# Ranked 5v5 Summoner's Rift (see Riot queue reference)
QUEUE_RANKED_SOLO = 420
QUEUE_RANKED_FLEX = 440
RANKED_SR_QUEUE_IDS: frozenset[int] = frozenset({QUEUE_RANKED_SOLO, QUEUE_RANKED_FLEX})

# Platform routing (summoner/league) → regional routing (match, account)
PLATFORM_TO_REGIONAL: dict[str, str] = {
    "na1": "americas",
    "br1": "americas",
    "la1": "americas",
    "la2": "americas",
    "euw1": "europe",
    "eun1": "europe",
    "tr1": "europe",
    "ru": "europe",
    "kr": "asia",
    "jp1": "asia",
    "ph2": "sea",
    "sg2": "sea",
    "th2": "sea",
    "tw2": "sea",
    "vn2": "sea",
}


def regional_from_match_id(match_id: str) -> str:
    prefix = match_id.split("_", 1)[0].lower()
    for plat, reg in PLATFORM_TO_REGIONAL.items():
        if plat == prefix:
            return reg
    raise SystemExit(
        f"Unknown match id prefix {prefix!r} in {match_id!r}. "
        "Expected e.g. NA1_, EUW1_, KR_."
    )


def riot_request(
    url: str,
    api_key: str,
    *,
    max_retries: int = 5,
) -> tuple[int, bytes]:
    """GET url with X-Riot-Token; honor Retry-After on 429."""
    req = urllib.request.Request(
        url,
        headers={
            "X-Riot-Token": api_key,
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        },
        method="GET",
    )
    last_err: Exception | None = None
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < max_retries - 1:
                retry_after = e.headers.get("Retry-After")
                wait = float(retry_after) if retry_after else 2.0 * (attempt + 1)
                time.sleep(min(wait, 120.0))
                continue
            last_err = e
            break
        except urllib.error.URLError as e:
            last_err = e
            if attempt < max_retries - 1:
                time.sleep(1.0 * (attempt + 1))
                continue
            break
    assert last_err is not None
    raise last_err


DDRAGON_VERSIONS = "https://ddragon.leagueoflegends.com/api/versions.json"


def http_get(url: str, *, timeout: int = 60) -> bytes:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json,*/*"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def http_get_json(url: str) -> Any:
    return json.loads(http_get(url).decode("utf-8"))


def resolve_ddragon_version(game_version: str) -> str:
    """Pick a Data Dragon release that matches Riot match `gameVersion` string."""
    versions: list[str] = http_get_json(DDRAGON_VERSIONS)
    gv = (game_version or "").strip().split()[0]
    parts = gv.split(".")
    if len(parts) >= 2:
        prefix = f"{parts[0]}.{parts[1]}."
        for v in versions:
            if v.startswith(prefix):
                return v
    if parts:
        p0 = parts[0]
        for v in versions:
            if v.startswith(p0 + "."):
                return v
    return versions[0]


def fetch_ddragon_bundle(out_dir: Path, game_version: str) -> str:
    """Write items.json + champion.json; return Data Dragon version used."""
    ver = resolve_ddragon_version(game_version)
    base = f"https://ddragon.leagueoflegends.com/cdn/{ver}/data/en_US"
    items = http_get_json(f"{base}/item.json")
    champs = http_get_json(f"{base}/champion.json")
    write_json(out_dir / "items.json", items)
    write_json(out_dir / "champion.json", champs)
    return ver


def fetch_json(url: str, api_key: str) -> Any:
    status, body = riot_request(url, api_key)
    if status != 200:
        raise SystemExit(f"HTTP {status} for {url}\n{body[:500]!r}")
    return json.loads(body.decode("utf-8"))


def account_by_riot_id(
    game_name: str, tag_line: str, regional: str, api_key: str
) -> dict[str, Any]:
    gn = urllib.parse.quote(game_name, safe="")
    tl = urllib.parse.quote(tag_line, safe="")
    url = f"https://{regional}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{gn}/{tl}"
    return fetch_json(url, api_key)


def match_ids_by_puuid(
    puuid: str,
    regional: str,
    api_key: str,
    *,
    count: int,
    queue: int | None,
) -> list[str]:
    q = urllib.parse.urlencode(
        {k: v for k, v in {"count": count, "queue": queue}.items() if v is not None}
    )
    url = f"https://{regional}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?{q}"
    data = fetch_json(url, api_key)
    if not isinstance(data, list):
        raise SystemExit(f"Unexpected match id list: {type(data)}")
    return [str(x) for x in data]


def match_url(regional: str, match_id: str) -> str:
    base = f"https://{regional}.api.riotgames.com/lol/match/v5/matches"
    return f"{base}/{urllib.parse.quote(match_id, safe='')}"


def load_match_cached(
    match_id: str,
    regional: str,
    api_key: str,
    cache: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    if match_id not in cache:
        cache[match_id] = fetch_json(match_url(regional, match_id), api_key)
    return cache[match_id]


def game_creation_ms(match_data: dict[str, Any]) -> int:
    info = match_data.get("info") or {}
    raw = info.get("gameCreation")
    if raw is None:
        raise SystemExit("Match JSON missing info.gameCreation; cannot order history.")
    return int(raw)


def is_ranked_summoners_rift(match_data: dict[str, Any]) -> bool:
    info = match_data.get("info") or {}
    q = info.get("queueId")
    return q in RANKED_SR_QUEUE_IDS


def merge_ranked_sr_history(
    puuid: str,
    regional: str,
    api_key: str,
    *,
    per_queue_count: int,
    ranked_pool: str,
    need_count: int,
) -> tuple[list[str], dict[str, dict[str, Any]]]:
    """
    Build match ids in true chronological order (newest first) across ranked SR queues.
    Riot's by-puuid ids endpoint returns one queue at a time, so we merge with timestamps.
    """
    cache: dict[str, dict[str, Any]] = {}
    if ranked_pool == "solo":
        solo = match_ids_by_puuid(
            puuid, regional, api_key, count=per_queue_count, queue=QUEUE_RANKED_SOLO
        )
        return solo[:need_count], cache
    if ranked_pool == "flex":
        flex = match_ids_by_puuid(
            puuid, regional, api_key, count=per_queue_count, queue=QUEUE_RANKED_FLEX
        )
        return flex[:need_count], cache

    solo = match_ids_by_puuid(
        puuid, regional, api_key, count=per_queue_count, queue=QUEUE_RANKED_SOLO
    )
    flex = match_ids_by_puuid(
        puuid, regional, api_key, count=per_queue_count, queue=QUEUE_RANKED_FLEX
    )
    if not solo and not flex:
        return [], cache

    first_id = solo[0] if solo else flex[0]
    regional_m = regional_from_match_id(first_id)
    if regional_m != regional:
        # Should not happen for one account; use id-derived host for match GETs.
        regional = regional_m

    i = j = 0
    merged: list[str] = []
    while len(merged) < need_count and (i < len(solo) or j < len(flex)):
        if j >= len(flex):
            merged.append(solo[i])
            i += 1
            continue
        if i >= len(solo):
            merged.append(flex[j])
            j += 1
            continue
        cs = game_creation_ms(load_match_cached(solo[i], regional, api_key, cache))
        cf = game_creation_ms(load_match_cached(flex[j], regional, api_key, cache))
        if cs >= cf:
            merged.append(solo[i])
            i += 1
        else:
            merged.append(flex[j])
            j += 1
    return merged, cache


def parse_riot_id(riot_id: str) -> tuple[str, str]:
    s = riot_id.strip()
    if "#" not in s:
        raise SystemExit(
            'Riot ID must look like GameName#TAG, e.g. "Faker#KR1". '
            f"Got: {riot_id!r}"
        )
    name, tag = s.rsplit("#", 1)
    if not name or not tag:
        raise SystemExit(f"Invalid Riot ID: {riot_id!r}")
    return name, tag


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    p = argparse.ArgumentParser(description="Download LoL match + timeline from Riot API")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--match-id", help="e.g. NA1_5535342053")
    src.add_argument(
        "--riot-id",
        help='Resolve PUUID then take latest match from history, e.g. "Name#TAG"',
    )
    p.add_argument(
        "--platform",
        help="Required with --riot-id (e.g. na1, euw1, kr)",
    )
    p.add_argument(
        "--history-index",
        type=int,
        default=0,
        help="Which match from history when using --riot-id (0 = most recent)",
    )
    p.add_argument(
        "--history-count",
        type=int,
        default=20,
        help="How many ids to pull per ranked queue from the API (max 100; merge may need both)",
    )
    p.add_argument(
        "--ranked-pool",
        choices=("both", "solo", "flex"),
        default="both",
        help="For --riot-id: ranked SR queues to search — solo=420, flex=440, both=merge by time (default)",
    )
    p.add_argument(
        "--allow-non-ranked-match",
        action="store_true",
        help="With --match-id only: allow non–Ranked-SR games (normals, ARAM, etc.)",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output directory (default: ./match_export_<match_id>)",
    )
    p.add_argument(
        "--skip-timeline",
        action="store_true",
        help="Do not request /timeline (some matches have no timeline)",
    )
    p.add_argument(
        "--timeline-optional",
        action="store_true",
        help="If timeline returns 404, write a small stub file instead of failing",
    )
    p.add_argument(
        "--no-ddragon",
        action="store_true",
        help="Do not download Data Dragon item.json + champion.json into --out",
    )
    args = p.parse_args()

    api_key = os.environ.get("RIOT_API_KEY", "").strip()
    if not api_key:
        sys.exit("Set RIOT_API_KEY in your environment (do not paste keys into source files).")

    match_cache: dict[str, dict[str, Any]] = {}

    if args.riot_id:
        if not args.platform:
            sys.exit("--platform is required with --riot-id (e.g. na1, euw1, kr)")
        plat = args.platform.lower().strip()
        regional = PLATFORM_TO_REGIONAL.get(plat)
        if not regional:
            sys.exit(f"Unknown platform {plat!r}. Known: {sorted(PLATFORM_TO_REGIONAL)}")
        game_name, tag_line = parse_riot_id(args.riot_id)
        acct = account_by_riot_id(game_name, tag_line, regional, api_key)
        puuid = acct.get("puuid")
        if not puuid:
            sys.exit(f"No puuid in account response: {acct}")
        base_n = max(args.history_count, args.history_index + 1)
        # Merging two queues may need more IDs per side (alternating solo/flex games).
        per_queue = min(100, base_n * 2 if args.ranked_pool == "both" else base_n)
        need = args.history_index + 1
        ids, match_cache = merge_ranked_sr_history(
            puuid,
            regional,
            api_key,
            per_queue_count=per_queue,
            ranked_pool=args.ranked_pool,
            need_count=need,
        )
        if not ids:
            sys.exit(
                "No Ranked Summoner's Rift matches in history for this player "
                f"(--ranked-pool {args.ranked_pool})."
            )
        if args.history_index >= len(ids):
            sys.exit(
                f"--history-index {args.history_index} out of range; only {len(ids)} "
                "ranked SR games found with current --history-count / pool settings."
            )
        match_id = ids[args.history_index]
    else:
        match_id = args.match_id.strip()

    regional = regional_from_match_id(match_id)
    out_dir = args.out or Path.cwd() / f"match_export_{match_id.replace('/', '_')}"

    m_url = match_url(regional, match_id)
    timeline_url = f"{m_url}/timeline"

    print(f"Regional host: {regional}")
    print(f"Match: {m_url}")
    print(f"Writing to: {out_dir}")

    if match_id in match_cache:
        match_data = match_cache[match_id]
    else:
        match_data = fetch_json(m_url, api_key)

    if args.match_id and not args.allow_non_ranked_match:
        if not is_ranked_summoners_rift(match_data):
            qid = (match_data.get("info") or {}).get("queueId")
            sys.exit(
                f"queueId={qid} is not Ranked Summoner's Rift (420/440). "
                "Use --allow-non-ranked-match to export anyway."
            )

    write_json(out_dir / "match.json", match_data)

    info = match_data.get("info") or {}
    meta: dict[str, Any] = {
        "match_id": match_id,
        "regional_routing": regional,
        "queue_id": info.get("queueId"),
        "ranked_summoners_rift": is_ranked_summoners_rift(match_data),
        "fetched_match": True,
        "fetched_timeline": False,
    }
    if args.riot_id:
        meta["ranked_pool"] = args.ranked_pool

    if not args.skip_timeline:
        try:
            timeline_data = fetch_json(timeline_url, api_key)
            write_json(out_dir / "timeline.json", timeline_data)
            meta["fetched_timeline"] = True
        except urllib.error.HTTPError as e:
            if e.code == 404 and args.timeline_optional:
                stub = {
                    "error": "timeline_not_available",
                    "http_status": 404,
                    "match_id": match_id,
                }
                write_json(out_dir / "timeline.json", stub)
                meta["fetched_timeline"] = False
                meta["timeline_note"] = "404 — saved stub (use --timeline-optional)"
            else:
                raise
    else:
        meta["timeline_note"] = "skipped (--skip-timeline)"

    if not args.no_ddragon:
        try:
            gv = str(info.get("gameVersion") or "")
            dd_ver = fetch_ddragon_bundle(out_dir, gv)
            meta["ddragon_version"] = dd_ver
            meta["ddragon_items"] = True
        except Exception as e:
            meta["ddragon_error"] = str(e)
            print(f"Warning: Data Dragon fetch failed: {e}", file=sys.stderr)

    write_json(out_dir / "fetch_meta.json", meta)
    parts = ["match.json", "fetch_meta.json"]
    if meta.get("fetched_timeline"):
        parts.append("timeline.json")
    if meta.get("ddragon_items"):
        parts.extend(["items.json", "champion.json"])
    print("Done: " + ", ".join(parts))


if __name__ == "__main__":
    main()
