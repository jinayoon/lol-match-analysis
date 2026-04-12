#!/usr/bin/env python3
"""
Build coach_digest.json (+ optional .md) from match.json, timeline.json, items.json.

Run after fetch_lol_match.py (same --out directory). Resolves item names from
items.json; never guesses names from training data.

Usage:
  python3 scripts/summarize_match_for_coach.py --dir /tmp/lol_match_export
  python3 scripts/summarize_match_for_coach.py --dir /tmp/lol_match_export \\
      --focus-riot "Name#TAG" --write-md
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def ms_to_mmss(ms: int) -> str:
    s = max(0, int(ms // 1000))
    m, sec = divmod(s, 60)
    return f"{m:02d}:{sec:02d}"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def item_lookup(items_root: dict[str, Any]) -> dict[int, str]:
    raw = (items_root or {}).get("data") or {}
    return {int(k): v.get("name", "?") for k, v in raw.items()}


def item_names_for_participant(
    p: dict[str, Any], items: dict[int, str]
) -> list[str | None]:
    out: list[str | None] = []
    for k in range(7):
        iid = p.get(f"item{k}", 0) or 0
        if iid == 0:
            out.append(None)
        else:
            out.append(items.get(iid, f"Unknown item (ID: {iid})"))
    return out


def ddragon_slug(champion_json: dict[str, Any], champion_id: int, champion_name: str) -> str | None:
    data = (champion_json or {}).get("data") or {}
    for slug, c in data.items():
        if str(c.get("key")) == str(champion_id):
            return slug
    for slug, c in data.items():
        if c.get("name") == champion_name or slug == champion_name.replace(" ", ""):
            return slug
    return None


def normalize_riot(s: str) -> str:
    s = s.strip().lower()
    if "#" in s:
        a, b = s.rsplit("#", 1)
        return f"{a.strip()}#{b.strip()}"
    return s


def pick_focus(
    participants: list[dict[str, Any]], focus_riot: str | None, focus_puuid: str | None
) -> dict[str, Any] | None:
    if focus_puuid:
        pu = focus_puuid.strip()
        for p in participants:
            if p.get("puuid") == pu:
                return p
    if focus_riot:
        target = normalize_riot(focus_riot)
        for p in participants:
            gn = (p.get("riotIdGameName") or "").strip().lower()
            tag = (p.get("riotIdTagline") or "").strip().lower()
            cand = f"{gn}#{tag}"
            if cand == target:
                return p
    return None


def team_kills(participants: list[dict[str, Any]], team_id: int) -> int:
    return sum(int(p.get("kills") or 0) for p in participants if p.get("teamId") == team_id)


def damage_split_team(participants: list[dict[str, Any]], team_id: int) -> tuple[float, float, float]:
    phy = mag = true = 0.0
    for p in participants:
        if p.get("teamId") != team_id:
            continue
        phy += float(p.get("physicalDamageDealtToChampions") or 0)
        mag += float(p.get("magicDamageDealtToChampions") or 0)
        true += float(p.get("trueDamageDealtToChampions") or 0)
    tot = phy + mag + true
    if tot <= 0:
        return 0.0, 0.0, 0.0
    return 100 * phy / tot, 100 * mag / tot, 100 * true / tot


def frame_at_or_before(frames: list[dict[str, Any]], target_ms: int) -> dict[str, Any] | None:
    best: dict[str, Any] | None = None
    best_ts = -1
    for fr in frames:
        ts = int(fr.get("timestamp") or 0)
        if ts <= target_ms and ts >= best_ts:
            best = fr
            best_ts = ts
    return best


def iter_timeline_events(timeline: dict[str, Any]) -> list[dict[str, Any]]:
    if not timeline or timeline.get("error"):
        return []
    frames = (timeline.get("info") or {}).get("frames") or []
    evs: list[dict[str, Any]] = []
    for fr in frames:
        for ev in fr.get("events") or []:
            evs.append(ev)
    return evs


def summarize_timeline(
    timeline: dict[str, Any],
    participants: list[dict[str, Any]],
    game_duration_sec: float,
    focus_team_id: int | None,
) -> dict[str, Any]:
    pid_team = {int(p["participantId"]): int(p["teamId"]) for p in participants}
    frames = (timeline.get("info") or {}).get("frames") or []

    gold_snapshots: dict[str, dict[str, float]] = {}
    for label, minute in [("5", 5), ("10", 10), ("15", 15), ("20", 20), ("25", 25)]:
        target = minute * 60 * 1000
        fr = frame_at_or_before(frames, target)
        if not fr:
            continue
        pf = fr.get("participantFrames") or {}
        b_g, r_g = 0.0, 0.0
        for pid_s, data in pf.items():
            pid = int(pid_s)
            tid = pid_team.get(pid)
            g = float((data or {}).get("totalGold") or 0)
            if tid == 100:
                b_g += g
            elif tid == 200:
                r_g += g
        gold_snapshots[label] = {"blue_total_gold": b_g, "red_total_gold": r_g, "diff_blue_minus_red": b_g - r_g}

    # Role gold vs lane opponent at key minutes (by teamPosition)
    by_role: dict[str, dict[int, dict[str, Any]]] = {}
    for p in participants:
        role = (p.get("teamPosition") or "UNKNOWN").upper()
        tid = int(p.get("teamId") or 0)
        pid = int(p.get("participantId") or 0)
        by_role.setdefault(role, {})[tid] = {"participantId": pid, "championName": p.get("championName")}

    role_gold_pairs: dict[str, Any] = {}
    for role, m in by_role.items():
        if 100 in m and 200 in m:
            pid_b = m[100]["participantId"]
            pid_r = m[200]["participantId"]
            entry: dict[str, Any] = {"blue": m[100], "red": m[200]}
            for label, minute in [("5", 5), ("10", 10), ("15", 15)]:
                target = minute * 60 * 1000
                fr = frame_at_or_before(frames, target)
                if not fr:
                    continue
                pf = (fr.get("participantFrames") or {})
                gb = float((pf.get(str(pid_b)) or {}).get("totalGold") or 0)
                gr = float((pf.get(str(pid_r)) or {}).get("totalGold") or 0)
                entry[f"gold_min_{label}"] = {"blue": gb, "red": gr, "diff_blue_minus_red": gb - gr}
            role_gold_pairs[role] = entry

    events_out: list[dict[str, Any]] = []
    for ev in iter_timeline_events(timeline):
        et = ev.get("type")
        ts = int(ev.get("timestamp") or 0)
        base: dict[str, Any] = {
            "type": et,
            "timestamp_ms": ts,
            "time": ms_to_mmss(ts),
        }
        if et == "CHAMPION_KILL":
            killer = ev.get("killerId")
            victim = ev.get("victimId")
            assists = ev.get("assistingParticipantIds") or []
            pos = ev.get("position") or {}
            base.update(
                {
                    "killerId": killer,
                    "victimId": victim,
                    "assistingParticipantIds": assists,
                    "position": pos,
                }
            )
            if focus_team_id and killer and victim:
                kt = pid_team.get(int(killer))
                vt = pid_team.get(int(victim))
                if kt == focus_team_id and vt != focus_team_id:
                    base["polarity_for_focus"] = "positive"
                elif vt == focus_team_id and kt != focus_team_id:
                    base["polarity_for_focus"] = "negative"
                else:
                    base["polarity_for_focus"] = "neutral"
        elif et == "ELITE_MONSTER_KILL":
            base.update(
                {
                    "monsterType": ev.get("monsterType"),
                    "killerId": ev.get("killerId"),
                    "teamId": ev.get("teamId"),
                }
            )
        elif et == "BUILDING_KILL":
            base.update(
                {
                    "buildingType": ev.get("buildingType"),
                    "towerType": ev.get("towerType"),
                    "teamId": ev.get("teamId"),
                    "laneType": ev.get("laneType"),
                }
            )
        elif et == "ITEM_PURCHASED":
            base.update(
                {"participantId": ev.get("participantId"), "itemId": ev.get("itemId")}
            )
        else:
            continue
        events_out.append(base)

    # Jungler CS buckets (3-min windows) — first jungler found per team
    junglers = [p for p in participants if (p.get("teamPosition") or "").upper() == "JUNGLE"]
    jg_cs: dict[str, Any] = {}
    for p in junglers:
        pid = int(p["participantId"])
        buckets: list[dict[str, Any]] = []
        window_sec = 180
        nwin = max(1, int(game_duration_sec // window_sec) + 1)
        for w in range(nwin):
            end_ms = min((w + 1) * window_sec * 1000, int(game_duration_sec * 1000))
            fr = frame_at_or_before(frames, end_ms)
            if not fr:
                continue
            data = (fr.get("participantFrames") or {}).get(str(pid)) or {}
            cs = int(data.get("minionsKilled") or 0) + int(data.get("jungleMinionsKilled") or 0)
            buckets.append({"window_end_mmss": ms_to_mmss(end_ms), "cumulative_cs": cs})
        jg_cs[str(pid)] = {
            "championName": p.get("championName"),
            "teamId": p.get("teamId"),
            "cumulative_cs_buckets_3min": buckets,
        }

    return {
        "gold_team_snapshots": gold_snapshots,
        "role_gold_pairs": role_gold_pairs,
        "events": events_out,
        "jungler_cs": jg_cs,
    }


def participant_row(
    p: dict[str, Any],
    items: dict[int, str],
    team_k: int,
    champion_root: dict[str, Any] | None,
) -> dict[str, Any]:
    slug = None
    if champion_root:
        slug = ddragon_slug(
            champion_root,
            int(p.get("championId") or 0),
            str(p.get("championName") or ""),
        )
    ch = p.get("challenges") or {}
    kills = int(p.get("kills") or 0)
    deaths = int(p.get("deaths") or 0)
    assists = int(p.get("assists") or 0)
    cs = int(p.get("totalMinionsKilled") or 0) + int(p.get("neutralMinionsKilled") or 0)
    kp = ch.get("killParticipation")
    if kp is None and team_k > 0:
        kp = (kills + assists) / team_k
    return {
        "participantId": p.get("participantId"),
        "puuid": p.get("puuid"),
        "riotIdGameName": p.get("riotIdGameName"),
        "riotIdTagline": p.get("riotIdTagline"),
        "championName": p.get("championName"),
        "championId": p.get("championId"),
        "teamId": p.get("teamId"),
        "teamPosition": p.get("teamPosition"),
        "kills": kills,
        "deaths": deaths,
        "assists": assists,
        "kda_ratio": (kills + assists) / max(deaths, 1),
        "cs": cs,
        "goldEarned": p.get("goldEarned"),
        "totalDamageDealtToChampions": p.get("totalDamageDealtToChampions"),
        "physicalDamageDealtToChampions": p.get("physicalDamageDealtToChampions"),
        "magicDamageDealtToChampions": p.get("magicDamageDealtToChampions"),
        "trueDamageDealtToChampions": p.get("trueDamageDealtToChampions"),
        "visionScore": p.get("visionScore"),
        "wardsPlaced": p.get("wardsPlaced"),
        "wardsKilled": p.get("wardsKilled"),
        "detectorWardsPlaced": p.get("detectorWardsPlaced"),
        "timeCCingOthers": p.get("timeCCingOthers"),
        "totalTimeSpentDead": p.get("totalTimeSpentDead"),
        "totalDamageTaken": p.get("totalDamageTaken"),
        "item0": p.get("item0"),
        "item1": p.get("item1"),
        "item2": p.get("item2"),
        "item3": p.get("item3"),
        "item4": p.get("item4"),
        "item5": p.get("item5"),
        "item6": p.get("item6"),
        "item_names": item_names_for_participant(p, items),
        "killParticipation": kp,
        "damagePerMinute": ch.get("damagePerMinute"),
        "goldPerMinute": ch.get("goldPerMinute"),
        "visionScorePerMinute": ch.get("visionScorePerMinute"),
        "laneMinionsFirst10Minutes": ch.get("laneMinionsFirst10Minutes"),
        "ddragon_champion_slug": slug,
    }


def build_digest(
    match: dict[str, Any],
    timeline: dict[str, Any],
    items_root: dict[str, Any] | None,
    champion_root: dict[str, Any] | None,
    focus_riot: str | None,
    focus_puuid: str | None,
) -> dict[str, Any]:
    info = match.get("info") or {}
    participants_raw = info.get("participants") or []
    items = item_lookup(items_root or {})
    t100 = team_kills(participants_raw, 100)
    t200 = team_kills(participants_raw, 200)
    team_k_map = {100: t100, 200: t200}

    participants = [
        participant_row(
            p, items, team_k_map.get(int(p.get("teamId") or 0), 1), champion_root
        )
        for p in participants_raw
    ]

    focus = pick_focus(participants_raw, focus_riot, focus_puuid)
    focus_team = int(focus["teamId"]) if focus else None
    focus_slug = None
    if focus and champion_root:
        focus_slug = ddragon_slug(
            champion_root,
            int(focus.get("championId") or 0),
            str(focus.get("championName") or ""),
        )

    duration = float(info.get("gameDuration") or 0)
    if duration <= 0:
        duration = float(info.get("gameEndTimestamp") or 0) - float(
            info.get("gameStartTimestamp") or 0
        )
        duration = max(0.0, duration / 1000.0)

    ad100, ap100, tr100 = damage_split_team(participants_raw, 100)
    ad200, ap200, tr200 = damage_split_team(participants_raw, 200)

    timeline_ok = bool(timeline and not timeline.get("error") and (timeline.get("info") or {}).get("frames"))

    tl_summary = (
        summarize_timeline(timeline, participants_raw, duration, focus_team)
        if timeline_ok
        else {"note": "no_timeline", "events": [], "gold_team_snapshots": {}}
    )

    winner = "unknown"
    teams = info.get("teams") or []
    for t in teams:
        if t.get("win"):
            winner = "blue" if t.get("teamId") == 100 else "red"
            break

    return {
        "match_id": str(info.get("matchId") or match.get("metadata", {}).get("matchId")),
        "game_version": info.get("gameVersion"),
        "game_duration_seconds": duration,
        "game_duration_mmss": ms_to_mmss(int(duration * 1000)),
        "queue_id": info.get("queueId"),
        "game_start_timestamp": info.get("gameStartTimestamp"),
        "winner_side": winner,
        "timeline_available": timeline_ok,
        "focus": (
            {
                "puuid": focus.get("puuid"),
                "riotIdGameName": focus.get("riotIdGameName"),
                "riotIdTagline": focus.get("riotIdTagline"),
                "championName": focus.get("championName"),
                "championId": focus.get("championId"),
                "teamId": focus.get("teamId"),
                "teamPosition": focus.get("teamPosition"),
                "ddragon_champion_slug": focus_slug,
            }
            if focus
            else None
        ),
        "team_damage_pct": {
            "blue": {"ad_pct": ad100, "ap_pct": ap100, "true_pct": tr100},
            "red": {"ad_pct": ad200, "ap_pct": ap200, "true_pct": tr200},
        },
        "participants": participants,
        "timeline_summary": tl_summary,
    }


def write_digest_md(path: Path, digest: dict[str, Any]) -> None:
    lines: list[str] = []
    lines.append(f"# Coach digest — {digest.get('match_id')}")
    lines.append("")
    lines.append(f"- Duration: {digest.get('game_duration_mmss')} | Patch: {digest.get('game_version')}")
    lines.append(f"- Timeline: {'yes' if digest.get('timeline_available') else 'no'}")
    if digest.get("focus"):
        f = digest["focus"]
        lines.append(
            f"- Focus: {f.get('riotIdGameName')}#{f.get('riotIdTagline')} — "
            f"{f.get('championName')} ({f.get('teamPosition')})"
        )
    lines.append("")
    lines.append("## Participants")
    lines.append("")
    lines.append("| # | Side | Player | Champ | Role | KDA | CS | Gold | Dmg | KP% |")
    lines.append("|---|------|--------|-------|------|-----|----| -----|-----|-----|")
    for p in digest.get("participants") or []:
        tid = int(p.get("teamId") or 0)
        side = "Blue" if tid == 100 else "Red"
        name = f"{p.get('riotIdGameName')}#{p.get('riotIdTagline')}"
        kp = p.get("killParticipation")
        kp_s = f"{100 * float(kp):.0f}%" if kp is not None else ""
        lines.append(
            f"| {p.get('participantId')} | {side} | {name} | {p.get('championName')} | "
            f"{p.get('teamPosition')} | {p.get('kills')}/{p.get('deaths')}/{p.get('assists')} | "
            f"{p.get('cs')} | {p.get('goldEarned')} | {p.get('totalDamageDealtToChampions')} | {kp_s} |"
        )
    lines.append("")
    gs = (digest.get("timeline_summary") or {}).get("gold_team_snapshots") or {}
    if gs:
        lines.append("## Gold (team totals at minute)")
        lines.append("")
        for k in sorted(gs.keys(), key=lambda x: int(x)):
            g = gs[k]
            lines.append(
                f"- {k} min: blue {g.get('blue_total_gold', 0):.0f} vs red "
                f"{g.get('red_total_gold', 0):.0f} (diff {g.get('diff_blue_minus_red', 0):+.0f})"
            )
        lines.append("")
    evs = (digest.get("timeline_summary") or {}).get("events") or []
    if evs:
        lines.append(f"## Timeline events ({len(evs)} extracted)")
        lines.append("")
        for ev in evs[:80]:
            lines.append(f"- [{ev.get('time')}] {ev.get('type')} {json.dumps({k: v for k, v in ev.items() if k not in ('type', 'time', 'timestamp_ms')}, ensure_ascii=False)}")
        if len(evs) > 80:
            lines.append(f"- … {len(evs) - 80} more in JSON")
        lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Build coach_digest.json from match export dir")
    ap.add_argument("--dir", type=Path, default=Path("/tmp/lol_match_export"))
    ap.add_argument("--focus-riot", default=None, help='Player to highlight, e.g. "Name#TAG"')
    ap.add_argument("--focus-puuid", default=None)
    ap.add_argument("--write-md", action="store_true", help="Also write coach_digest.md")
    args = ap.parse_args()

    d = args.dir
    match_path = d / "match.json"
    if not match_path.is_file():
        sys.exit(f"Missing {match_path}")

    match = load_json(match_path)
    tl_path = d / "timeline.json"
    timeline = load_json(tl_path) if tl_path.is_file() else {}

    items_path = d / "items.json"
    champ_path = d / "champion.json"
    items_root = load_json(items_path) if items_path.is_file() else {}
    champ_root = load_json(champ_path) if champ_path.is_file() else {}

    digest = build_digest(
        match,
        timeline,
        items_root,
        champ_root,
        args.focus_riot,
        args.focus_puuid,
    )

    meta_path = d / "fetch_meta.json"
    if meta_path.is_file():
        digest["fetch_meta"] = load_json(meta_path)

    out_json = d / "coach_digest.json"
    out_json.write_text(json.dumps(digest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {out_json}")

    if args.write_md:
        md_path = d / "coach_digest.md"
        write_digest_md(md_path, digest)
        print(f"Wrote {md_path}")


if __name__ == "__main__":
    main()
