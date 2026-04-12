# Post-match coaching report — template

Follow this structure in the Markdown report. The HTML renderer (`scripts/render_coach_report.py`) auto-builds hero, quick stats, team table, and timeline from `coach_digest.json`; narrative should start at **`## Phase 1:`** so the HTML does not duplicate the top sections.

---

## Naming conventions

**Teams:** Team 100 = **blue team**, Team 200 = **red team** (never T100/T200).

**Champions:** Prefix every champion with **Ally** or **Enemy** in prose.

**Locations:** Every kill or fight needs plain-English map location. Derive from timeline `position` x/y on ~15000×15000 Summoner’s Rift:

- x < 5000, y < 5000 → red side / bot area  
- x > 10000, y > 10000 → blue side / top area  
- x,y 5000–10000 → mid / river  
- x < 6000, y 6000–9000 → bot river / dragon  
- x > 9000, y 6000–9000 → top river / Baron  

---

## Finding block format

```
[MM:SS | location] PHASE — LENS — Title
Severity: HIGH / MEDIUM / LOW
What happened: One specific sentence with a number or name.
What to do instead: One actionable sentence (no “watch a VOD”).
```

**Severity:** HIGH = kill/objective/500g+ swing; MEDIUM = compounding disadvantage; LOW = efficiency / small miss.

---

## Full document outline

```markdown
# Post-Match Coaching Report — [Player] ([Champion], [Role]) | [W/L] [Duration] | Patch [X]

**Match ID:** `...`
**OP.GG:** [placeholder — user pastes permalink if desired]

**Honest Verdict:** (1 sentence, blunt)

**Game Summary:** (1–3 sentences)

**3 Things to Work On:**
1. **[Skill]** — hook
2. ...
3. ...

---

## Quick Stats
| ... |

---

## Team Overview
| ... | ← YOU on analyzed player

**Damage split:** ...

---

## Phase 1: Draft
...

## Phase 2: Early Game (0–14 min)
...

## Phase 3: Mid Game (14–25 min)
...

## Phase 4: Late Game (25+ min)
...

---

### The 3 Swing Moments
...

### 3 Things to Work On (detailed)
...
```

---

## File naming

Save under **`reviews/[YYYY-MM-DD]_[HHMM]_[Champion].md`** at the **repository root** (same folder as `scripts/` and `docs/`), using `gameStartTimestamp` from `match.json`. If you use `ANALYZE_LOL_MATCH_ROOT` (or legacy `LOL_MATCH_ANALYSIS_ROOT`), that path is `$ANALYZE_LOL_MATCH_ROOT/reviews/...` or `$LOL_MATCH_ANALYSIS_ROOT/reviews/...`.

Append the Riot disclaimer from `docs/riot-disclaimer.txt` after a `---` divider (or use `render_coach_report.py --append-disclaimer-md`).
