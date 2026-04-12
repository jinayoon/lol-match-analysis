#!/usr/bin/env python3
"""
Build a self-contained coaching report HTML from coach_digest.json + report.md.

Auto-generates hero (favicon, loading art, spell strip when Data Dragon is available),
focus quick-stats, team table, and interactive timeline from the digest. Converts
the narrative portion of the markdown (from ## Phase 1 onward) to simple HTML.

Usage:
  python3 scripts/render_coach_report.py \\
    --digest /tmp/lol_match_export/coach_digest.json \\
    --markdown reviews/2026-04-10_0238_Braum.md \\
    --out reviews/2026-04-10_0238_Braum.html
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DISCLAIMER_HTML = PROJECT_ROOT / "docs" / "riot-disclaimer.html"
DDRAGON_VERSIONS = "https://ddragon.leagueoflegends.com/api/versions.json"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def http_get_json(url: str) -> Any:
    req = urllib.request.Request(
        url, headers={"User-Agent": "lol-coach-report/1.0", "Accept": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.loads(r.read().decode("utf-8"))


def resolve_version(game_version: str | None) -> str:
    versions: list[str] = http_get_json(DDRAGON_VERSIONS)
    gv = (game_version or "").strip().split()[0]
    parts = gv.split(".")
    if len(parts) >= 2:
        prefix = f"{parts[0]}.{parts[1]}."
        for v in versions:
            if v.startswith(prefix):
                return v
    return versions[0]


def extract_title_and_narrative(md: str) -> tuple[str, str]:
    """First # line is title; narrative starts at ## Phase 1 if present else after first ---."""
    text = md.strip()
    title = "Coaching Report"
    if text.startswith("#"):
        nl = text.find("\n")
        if nl == -1:
            title = text[1:].strip()
            return title, ""
        title = text[1:nl].strip()
        text = text[nl + 1 :].strip()
    m = re.search(r"(?m)^## Phase 1:", text)
    if m:
        return title, text[m.start() :].strip()
    parts = re.split(r"\n---\s*\n", text, maxsplit=1)
    if len(parts) == 2 and "Phase" in parts[1]:
        return title, parts[1].strip()
    return title, text


def inline_fmt(s: str) -> str:
    parts = re.split(r"(\*\*.+?\*\*)", s)
    chunks: list[str] = []
    for p in parts:
        if len(p) >= 4 and p.startswith("**") and p.endswith("**"):
            chunks.append("<strong>" + html.escape(p[2:-2]) + "</strong>")
        else:
            chunks.append(html.escape(p))
    return "".join(chunks)


def md_simple_to_html(md: str) -> str:
    """Subset: headers ###/##/#, **bold**, lists, pipes tables, paragraphs."""
    lines = md.split("\n")
    out: list[str] = []
    i = 0
    in_ul = False

    def close_ul() -> None:
        nonlocal in_ul
        if in_ul:
            out.append("</ul>")
            in_ul = False

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            close_ul()
            i += 1
            continue
        if stripped.startswith("|") and "|" in stripped[1:]:
            close_ul()
            rows: list[list[str]] = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                row = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                rows.append(row)
                i += 1
            if len(rows) >= 2 and re.match(r"^[-:| ]+$", "|".join(rows[1])):
                header = rows[0]
                body = rows[2:]
                out.append('<table style="width:100%;border-collapse:collapse;margin:12px 0;font-size:.88rem">')
                out.append("<thead><tr>")
                for c in header:
                    out.append(
                        f'<th style="border:1px solid var(--border);padding:8px;background:var(--surface2)">{inline_fmt(c)}</th>'
                    )
                out.append("</tr></thead><tbody>")
                for row in body:
                    out.append("<tr>")
                    for c in row:
                        out.append(
                            f'<td style="border:1px solid var(--border);padding:8px">{inline_fmt(c)}</td>'
                        )
                    out.append("</tr>")
                out.append("</tbody></table>")
                continue
            i += 1
            continue
        if stripped.startswith("### "):
            close_ul()
            out.append(f"<h3>{inline_fmt(stripped[4:])}</h3>")
        elif stripped.startswith("## "):
            close_ul()
            out.append(f"<h2>{inline_fmt(stripped[3:])}</h2>")
        elif stripped.startswith("# "):
            close_ul()
            out.append(f"<h1>{inline_fmt(stripped[2:])}</h1>")
        elif stripped.startswith(("- ", "* ")):
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            out.append(f"<li>{inline_fmt(stripped[2:])}</li>")
        else:
            close_ul()
            buf = [stripped]
            i += 1
            while i < len(lines) and lines[i].strip() and not lines[i].strip().startswith("#"):
                buf.append(lines[i].strip())
                i += 1
            out.append(f"<p>{inline_fmt(' '.join(buf))}</p>")
            continue
        i += 1
    close_ul()
    return "\n".join(out)


def css_block() -> str:
    return """
:root {
  --bg:#0e0f14;--surface:#16181f;--surface2:#1e2029;--border:#2a2d3a;
  --text:#dde1f0;--muted:#7b8099;--blue:#4e9eff;--gold:#c89b3c;--green:#3dca7e;
  --red:#e55c5c;--yellow:#f0b429;--purple:#9b7fe8;
}
* { box-sizing:border-box; }
body { margin:0;background:var(--bg);color:var(--text);font-family:system-ui,sans-serif;line-height:1.55;font-size:15px; }
.container { max-width:900px;margin:0 auto;padding:24px 16px 48px; }
.card { background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:16px;margin-bottom:14px; }
.hero { display:flex;gap:20px;flex-wrap:wrap;align-items:flex-start; }
.hero img.load { width:120px;height:120px;border-radius:10px;border:2px solid var(--gold);object-fit:cover; }
.spells { display:flex;gap:6px;margin-top:8px; }
.spells img { width:26px;height:26px;border-radius:4px;border:1px solid var(--border); }
.statgrid { display:grid;grid-template-columns:repeat(auto-fill,minmax(110px,1fr));gap:10px;margin:16px 0; }
.statbox { background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:10px;text-align:center; }
.statbox .v { font-size:1.25rem;font-weight:700; }
.statbox .l { font-size:.72rem;color:var(--muted); }
table.team { width:100%;border-collapse:collapse;font-size:.85rem;margin:12px 0; }
table.team th, table.team td { border:1px solid var(--border);padding:6px 8px; }
table.team th { background:var(--surface2); }
tr.you { background:#c89b3c18; }
.timeline-wrap { margin:20px 0; }
.prose h2 { color:var(--gold);margin-top:28px;font-size:1.1rem; }
.prose h3 { color:var(--blue);margin-top:18px;font-size:1rem; }
.prose p { margin:10px 0; }
.prose strong { color:var(--text); }
"""


def champion_spells(version: str, slug: str) -> list[dict[str, str]]:
    url = f"https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/champion/{slug}.json"
    try:
        data = http_get_json(url)
    except Exception:
        return []
    ent = (data.get("data") or {}).get(slug) or {}
    spells = ent.get("spells") or []
    keys = ["Q", "W", "E", "R"]
    out: list[dict[str, str]] = []
    for i, sp in enumerate(spells[:4]):
        img = (sp.get("image") or {}).get("full") or ""
        name = sp.get("name") or keys[i]
        out.append(
            {
                "key": keys[i] if i < 4 else str(i),
                "name": name,
                "icon": f"https://ddragon.leagueoflegends.com/cdn/{version}/img/spell/{img}",
            }
        )
    return out


def build_timeline_html(digest: dict[str, Any], version: str, total_sec: float) -> str:
    if total_sec <= 0:
        total_sec = 1.0
    evs = (digest.get("timeline_summary") or {}).get("events") or []
    kills = [e for e in evs if e.get("type") == "CHAMPION_KILL"][:45]
    early_pct = min(100, (14 * 60) / total_sec * 100)
    mid_pct = min(100, ((25 - 14) * 60) / total_sec * 100)
    late_pct = max(0, 100 - early_pct - mid_pct)
    parts = [
        '<div class="timeline-wrap">',
        '<h3>Match Timeline</h3>',
        f'<div style="display:flex;height:22px;border-radius:4px;overflow:hidden;margin-bottom:10px">'
        f'<div style="width:{early_pct:.1f}%;background:#2563eb30;text-align:center;font-size:.65rem;line-height:22px">Early</div>'
        f'<div style="width:{mid_pct:.1f}%;background:#7c3aed30;text-align:center;font-size:.65rem;line-height:22px">Mid</div>'
        f'<div style="width:{late_pct:.1f}%;background:#c026d330;text-align:center;font-size:.65rem;line-height:22px">Late</div></div>',
        '<div style="position:relative;height:72px;margin-top:8px">',
        '<div style="position:absolute;top:32px;left:0;right:0;height:6px;background:var(--border);border-radius:3px"></div>',
    ]
    for e in kills:
        ts = int(e.get("timestamp_ms") or 0) / 1000.0
        pct = min(100, max(0, ts / total_sec * 100))
        pol = e.get("polarity_for_focus") or "neutral"
        color = "var(--green)" if pol == "positive" else "var(--red)" if pol == "negative" else "var(--muted)"
        tip = html.escape(f"{e.get('time')} — kill (K{e.get('killerId')} → V{e.get('victimId')})")
        parts.append(
            f'<div style="position:absolute;top:8px;left:{pct:.2f}%;transform:translateX(-50%)" title="{tip}">'
            f'<div style="width:10px;height:10px;border-radius:50%;background:{color};border:2px solid var(--bg)"></div>'
            f'<div style="width:1px;height:20px;background:rgba(255,255,255,.2);margin:0 auto"></div></div>'
        )
    parts.append("</div></div>")
    return "\n".join(parts)


def render_html(digest: dict[str, Any], md_title: str, narrative_md: str) -> str:
    fm = digest.get("fetch_meta") or {}
    version = fm.get("ddragon_version") or resolve_version(digest.get("game_version"))
    focus = digest.get("focus") or {}
    slug = focus.get("ddragon_champion_slug") or ""
    champ_name = focus.get("championName") or "Champion"
    load_url = (
        f"https://ddragon.leagueoflegends.com/cdn/img/champion/loading/{slug}_0.jpg"
        if slug
        else ""
    )
    icon_url = (
        f"https://ddragon.leagueoflegends.com/cdn/{version}/img/champion/{slug}.png"
        if slug
        else ""
    )
    spells = champion_spells(version, slug) if slug else []

    subtitle_parts = [
        focus.get("riotIdGameName"),
        champ_name,
        focus.get("teamPosition"),
        digest.get("match_id"),
    ]
    subtitle = " · ".join(str(p) for p in subtitle_parts if p)

    duration = float(digest.get("game_duration_seconds") or 0)

    # Quick stats for focus
    fp = None
    for p in digest.get("participants") or []:
        if focus.get("puuid") and p.get("puuid") == focus.get("puuid"):
            fp = p
            break
    stat_items: list[tuple[str, str, str]] = []
    if fp:
        dpm = fp.get("damagePerMinute")
        gpm = fp.get("goldPerMinute")
        kp = fp.get("killParticipation")
        kp_s = f"{100 * float(kp):.0f}%" if kp is not None else "—"
        stat_items = [
            ("KDA", f"{fp.get('kills')}/{fp.get('deaths')}/{fp.get('assists')}", ""),
            ("CS", str(fp.get("cs")), ""),
            ("Gold", str(fp.get("goldEarned")), ""),
            ("Dmg", str(fp.get("totalDamageDealtToChampions")), ""),
            ("KP%", kp_s, "green"),
            ("Vision", str(fp.get("visionScore")), "green"),
        ]

    spell_html = ""
    if spells:
        spell_html = '<div class="spells">'
        for sp in spells:
            spell_html += (
                f'<img src="{html.escape(sp["icon"])}" title="{html.escape(sp["key"] + " — " + sp["name"])}" '
                f'alt="" onerror="this.style.display=\'none\'">'
            )
        spell_html += "</div>"

    hero_left = ""
    if load_url:
        hero_left = (
            f'<div><img class="load" src="{html.escape(load_url)}" alt="" onerror="this.style.display=\'none\'">'
            f"{spell_html}</div>"
        )

    statgrid = ""
    if stat_items:
        boxes = []
        for label, val, cls in stat_items:
            col = f"color:var(--{cls});" if cls else ""
            boxes.append(
                f'<div class="statbox"><div class="v" style="{col}">{html.escape(val)}</div>'
                f'<div class="l">{html.escape(label)}</div></div>'
            )
        statgrid = f'<div class="statgrid">{"".join(boxes)}</div>'

    # Team table
    rows: list[str] = []
    rows.append(
        "<tr><th>Player</th><th>Champ</th><th>Role</th><th>KDA</th><th>CS</th><th>Gold</th><th>Dmg</th><th>KP%</th></tr>"
    )
    fpu = focus.get("puuid")
    for p in digest.get("participants") or []:
        tid = int(p.get("teamId") or 0)
        side = "Blue" if tid == 100 else "Red"
        kp = p.get("killParticipation")
        kp_s = f"{100 * float(kp):.0f}%" if kp is not None else ""
        you = " class='you'" if fpu and p.get("puuid") == fpu else ""
        cslug = p.get("ddragon_champion_slug") or p.get("championName", "").replace(" ", "")
        portrait = f"https://ddragon.leagueoflegends.com/cdn/{version}/img/champion/{cslug}.png"
        name = f'{p.get("riotIdGameName")}#{p.get("riotIdTagline")}'
        rows.append(
            f"<tr{you}><td>{html.escape(name)}</td>"
            f'<td><img src="{html.escape(portrait)}" style="width:22px;height:22px;vertical-align:middle;margin-right:6px" '
            f'onerror="this.style.display=\'none\'"> {html.escape(str(p.get("championName")))}</td>'
            f"<td>{html.escape(str(p.get('teamPosition')))}</td>"
            f"<td>{p.get('kills')}/{p.get('deaths')}/{p.get('assists')}</td>"
            f"<td>{p.get('cs')}</td><td>{p.get('goldEarned')}</td><td>{p.get('totalDamageDealtToChampions')}</td>"
            f"<td>{kp_s}</td></tr>"
        )

    team_html = f'<table class="team">{"".join(rows)}</table>'

    timeline_html = ""
    if digest.get("timeline_available"):
        timeline_html = build_timeline_html(digest, version, duration)

    narrative_html = f'<div class="prose">{md_simple_to_html(narrative_md)}</div>'

    disclaimer = ""
    if DISCLAIMER_HTML.is_file():
        disclaimer = DISCLAIMER_HTML.read_text(encoding="utf-8")

    favicon_line = (
        f'<link rel="icon" type="image/png" href="{html.escape(icon_url)}">'
        if icon_url
        else ""
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(md_title)}</title>
{favicon_line}
<style>{css_block()}</style>
</head>
<body>
<div class="container">
  <div class="hero card">
    {hero_left}
    <div style="flex:1;min-width:200px">
      <h1 style="margin:0 0 8px;font-size:1.35rem">{html.escape(md_title)}</h1>
      <div style="font-size:.85rem;color:var(--muted);margin-bottom:12px">{html.escape(subtitle)}</div>
      <p style="margin:0;font-size:.9rem;color:var(--muted)">Patch {html.escape(str(digest.get("game_version")))} · Duration {html.escape(digest.get("game_duration_mmss") or "")}</p>
    </div>
  </div>
  {statgrid}
  <h2 style="color:var(--gold);font-size:1rem">Team overview</h2>
  {team_html}
  {timeline_html}
  {narrative_html}
</div>
{disclaimer}
</body>
</html>
"""


def append_disclaimer_to_md(md_path: Path) -> None:
    txt_path = PROJECT_ROOT / "docs" / "riot-disclaimer.txt"
    if not txt_path.is_file():
        return
    note = txt_path.read_text(encoding="utf-8").strip()
    text = md_path.read_text(encoding="utf-8")
    if "Riot Games, Inc" in text and "isn't endorsed" in text:
        return
    sep = "\n\n---\n\n"
    md_path.write_text(text.rstrip() + sep + note + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--digest", type=Path, required=True)
    ap.add_argument("--markdown", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--append-disclaimer-md", action="store_true")
    args = ap.parse_args()

    digest = load_json(args.digest)
    md_raw = args.markdown.read_text(encoding="utf-8")
    title, narrative = extract_title_and_narrative(md_raw)
    html_out = render_html(digest, title, narrative)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(html_out, encoding="utf-8")
    print(f"Wrote {args.out}")
    if args.append_disclaimer_md:
        append_disclaimer_to_md(args.markdown)
        print(f"Appended disclaimer to {args.markdown}")


if __name__ == "__main__":
    main()
