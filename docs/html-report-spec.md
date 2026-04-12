# HTML report spec (reference)

**Default path:** run `scripts/render_coach_report.py` — it applies the dark theme, hero (loading art + spell strip), focus stats, team table, kill timeline, markdown narrative, and `docs/riot-disclaimer.html`.

## When to hand-edit HTML

Use this doc if you need **pixel-perfect** parity with older reports (interactive timeline tooltips, per-finding severity borders, item chips in “Work on”). The script uses a **simplified** timeline (kill markers only) and renders phases from Markdown.

## Design tokens

```css
:root {
  --bg:#0e0f14; --surface:#16181f; --surface2:#1e2029; --border:#2a2d3a;
  --text:#dde1f0; --muted:#7b8099; --blue:#4e9eff; --gold:#c89b3c;
  --green:#3dca7e; --red:#e55c5c; --yellow:#f0b429; --purple:#9b7fe8;
}
```

Severity colors: HIGH → `--red`, MEDIUM → `--yellow`, LOW / positive → `--green`.

## Data Dragon assets

- Version: `fetch_meta.json` → `ddragon_version`, else match `gameVersion` prefix against `versions.json`.  
- Champion tile: `https://ddragon.leagueoflegends.com/cdn/{VERSION}/img/champion/{slug}.png`  
- Loading art: `https://ddragon.leagueoflegends.com/cdn/img/champion/loading/{slug}_0.jpg`  
- Spells: per-champion JSON `spells[i].image.full` under `cdn/{VERSION}/data/en_US/champion/{slug}.json`  
- Items: `cdn/{VERSION}/img/item/{id}.png`  

**Display names** in text must be Riot official names; **slugs** are URL-only (`MonkeyKing` not `Wukong` in URLs — digest provides `ddragon_champion_slug`).

Every `<img>` should include `onerror="this.style.display='none'"`.

## Advanced timeline (optional manual build)

- `left% = (event_seconds / game_duration_seconds) * 100`  
- Phase bands: Early 0–14 min, Mid 14–25, Late 25+.  
- Positive markers **above** ruler (`top:4px`), negative **below** (`top:46px`).  
- `.timeline-wrap` must **not** use `overflow:hidden` (tooltips).  
- Tooltip flip when `left% > 65`.

## Legal

Footer text lives in `docs/riot-disclaimer.html` (HTML) and `docs/riot-disclaimer.txt` (Markdown appendix).
