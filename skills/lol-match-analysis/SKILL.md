---
name: lol-match-analysis
description: >
  Acts as a League of Legends post-match coach. Fetches the latest Ranked SR match
  via scripts/fetch_lol_match.py, builds coach_digest.json via summarize_match_for_coach.py,
  analyzes using docs in this repository, writes Markdown from docs/coach-report-template.md,
  and can render HTML via render_coach_report.py.

  Trigger whenever the user asks about a LoL match, coaching, why they won/lost,
  what they did wrong, how to improve, to review or analyze a game, to pull a match,
  or for role-specific problems (vision, jungle farm, trades, deaths). Works for any role.
---

# LoL Post-Match Coach (slim orchestration)

**Repository:** [github.com/jinayoon/lol-match-analysis](https://github.com/jinayoon/lol-match-analysis) — this skill assumes you have a **full clone** (not only `SKILL.md`), so `scripts/` and `docs/` exist.

## Repository root (`$REPO`)

All paths below are under the repo root (the folder that contains `scripts/` and `docs/`).

**Before running shell commands**, either:

1. `cd` into your clone, then use the snippets as-is with `$REPO` replaced by `.` or set  
   `export REPO="$(pwd)"`, **or**
2. Set once:  
   `export LOL_MATCH_ANALYSIS_ROOT="/path/to/lol-match-analysis"`  
   and use  
   `REPO="${LOL_MATCH_ANALYSIS_ROOT:-$PWD}"` in each shell session.

In bash examples below, `REPO` means that directory.

Coach with **timestamped, evidence-based findings** (severity + “what to do instead”). Every claim ties to match/timeline data — not vibes.

## Reference files (Read as needed — do not load all up front)

Paths are relative to **repository root**:

| Topic | Path |
|--------|------|
| LoL domain + Riot API + Skill Capped URLs | `docs/lol-reference.md` |
| Report outline + naming + finding format | `docs/coach-report-template.md` |
| 4 phases × 5 lenses | `docs/coach-analyze-rubric.md` |
| Smite, Braum/GW/item pitfalls | `docs/coach-pitfalls.md` |
| Shaco tone (only if champ is Shaco) | `docs/coach-shaco-overlay.md` |
| HTML details / hand-polish | `docs/html-report-spec.md` |
| Riot legal (HTML + plain) | `docs/riot-disclaimer.html`, `docs/riot-disclaimer.txt` |

## Pipeline

### 1) Inputs (one at a time)

1. **Riot API key** — ask alone first; dev keys expire ~24h.  
2. Then **Riot ID + platform** (`na1`, `euw1`, `kr`, …) **or** a **match ID** (`NA1_…`) for `--match-id`.

### 2) Fetch match + static data

```bash
REPO="${LOL_MATCH_ANALYSIS_ROOT:-$PWD}"
export RIOT_API_KEY="…"
export MATCH_EXPORT="/tmp/lol_match_export"
rm -rf "$MATCH_EXPORT" && mkdir -p "$MATCH_EXPORT"

python3 "$REPO/scripts/fetch_lol_match.py" --riot-id "GameName#TAG" --platform na1 --out "$MATCH_EXPORT" --timeline-optional
# or: python3 "$REPO/scripts/fetch_lol_match.py" --match-id NA1_xxxx --out "$MATCH_EXPORT" --timeline-optional
```

By default this also downloads **Data Dragon** `items.json` + `champion.json` into `$MATCH_EXPORT`. Use `--no-ddragon` only if you must skip. If `timeline.json` is a stub (`timeline_not_available`), say so in the report and skip frame-level work.

**Skill Capped:** before item critique, fetch the guide URL from `docs/lol-reference.md` (role slugs).

### 3) Digest (structured data for analysis + HTML)

```bash
REPO="${LOL_MATCH_ANALYSIS_ROOT:-$PWD}"
python3 "$REPO/scripts/summarize_match_for_coach.py" \
  --dir "$MATCH_EXPORT" --focus-riot "GameName#TAG" --write-md
```

Read **`coach_digest.json`** (and optional `coach_digest.md`) under `$MATCH_EXPORT` — **do not** re-derive field lists from scratch unless the script fails.

### 4) Analyze

Read **`docs/coach-analyze-rubric.md`** and **`docs/coach-pitfalls.md`**. If the analyzed champion is **Shaco**, read **`docs/coach-shaco-overlay.md`**.

### 5) Write Markdown

Follow **`docs/coach-report-template.md`**. Start phase sections at **`## Phase 1:`** so the HTML renderer can skip duplicating the opening blocks.

Resolve item names only via **`$MATCH_EXPORT/items.json`**.

### 6) Save `.md`

`$REPO/reviews/YYYY-MM-DD_HHMM_Champion.md` using `gameStartTimestamp` from `match.json` (see template).

### 7) Render HTML (optional but default for full deliverable)

```bash
REPO="${LOL_MATCH_ANALYSIS_ROOT:-$PWD}"
python3 "$REPO/scripts/render_coach_report.py" \
  --digest "$MATCH_EXPORT/coach_digest.json" \
  --markdown "$REPO/reviews/….md" \
  --out "$REPO/reviews/….html" \
  --append-disclaimer-md
```

`--append-disclaimer-md` appends `docs/riot-disclaimer.txt` to the Markdown once.

---

## Item icons / champion stats

Use Data Dragon + wiki per **`docs/lol-reference.md`** and **`docs/html-report-spec.md`** — never guess item names or patch-specific numbers from training data.
