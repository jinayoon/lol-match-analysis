---
name: lol-game-review
description: >
  Acts as a League of Legends post-match coach. Fetches a player's most recent match
  from the Riot API, analyzes it across 4 game phases and 5 coaching lenses, and
  produces timestamped, actionable findings — each with a severity rating and a
  specific "what to do instead". Ends with the 2-3 biggest swing moments and
  3 prioritized practice focuses for that player.

  Trigger this skill whenever the user asks about a LoL match, wants to know why
  they won or lost, wants coaching feedback, asks "what did I do wrong", "was it
  my fault", "how do I improve from this", "review my game", "analyze my last game",
  "pull my match", or any variant of post-game analysis. Also trigger if they mention
  a specific in-game problem like jungler farming, bad trades, poor vision, or dying
  too much. Works for any player and any role.
---

# LoL Post-Match Coach

Your job is to analyze a League of Legends match the way a coach would — not with a
summary, but with timestamped, specific findings that tell the player exactly what went
wrong (or right), why it mattered, and what to do differently. Every claim must be
grounded in real data from the match.

---

## Step 1 — Gather inputs

You need two things, collected **one at a time**:

1. **Riot API key** — dev keys expire every 24h. Ask for this first, alone:
   > "Paste your Riot API key (grab a fresh one from developer.riotgames.com — it's on your dashboard)."
   Wait for the user to reply before asking for anything else.

2. **Player identity** — only after receiving the API key, ask:
   > "What's your Riot ID? (format: Name#TAG)"
   If you already know it from context, skip this and proceed.

Once you have both, proceed immediately.

---

## Step 2 — Fetch data

Use `curl` via Bash (do NOT use Python `requests` — SSL issues on Mac).

```bash
KEY="<api_key>"

# 1. Resolve PUUID from Riot ID
PUUID=$(curl -s -H "X-Riot-Token: $KEY" \
  "https://americas.api.riotgames.com/riot/account/v1/accounts/by-riot-id/<name>/<tag>" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['puuid'])")

# 2. Get latest match ID (add ?queue=420 for ranked-only, omit for any mode)
MATCH_ID=$(curl -s -H "X-Riot-Token: $KEY" \
  "https://americas.api.riotgames.com/lol/match/v5/matches/by-puuid/$PUUID/ids?count=1" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)[0])")

# 3. Fetch match + timeline sequentially (rate limit caution)
curl -s -H "X-Riot-Token: $KEY" \
  "https://americas.api.riotgames.com/lol/match/v5/matches/$MATCH_ID" > /tmp/lol_match.json
curl -s -H "X-Riot-Token: $KEY" \
  "https://americas.api.riotgames.com/lol/match/v5/matches/$MATCH_ID/timeline" > /tmp/lol_timeline.json

# 4. Fetch current item data from Data Dragon (use gameVersion from match JSON for exact patch)
PATCH=$(python3 -c "import json; d=json.load(open('/tmp/lol_match.json')); print(d['info']['gameVersion'].rsplit('.',1)[0]+'.1')" 2>/dev/null || \
  curl -s "https://ddragon.leagueoflegends.com/api/versions.json" | python3 -c "import sys,json; print(json.load(sys.stdin)[0])")
curl -s "https://ddragon.leagueoflegends.com/cdn/${PATCH}/data/en_US/item.json" > /tmp/lol_items.json
```

Verify both match files are valid JSON. If you get a 401, tell the user the key expired.

**IMPORTANT — item names:** The Riot API returns numeric item IDs only. NEVER guess item names from training data — item names and stats change every patch and training data will be wrong. Always resolve item IDs using `/tmp/lol_items.json`. If an item ID is missing from the file (removed items, components), note it as "Unknown item (ID: XXXX)" rather than guessing.

---

## Step 3 — Extract data with Python

**Before writing any analysis**, build an item name lookup from `/tmp/lol_items.json`:

```python
import json
items_raw = json.load(open('/tmp/lol_items.json'))['data']
ITEMS = {int(k): v['name'] for k, v in items_raw.items()}

def item_name(item_id):
    if item_id == 0:
        return None
    return ITEMS.get(item_id, f"Unknown item (ID: {item_id})")
```

Use `item_name(id)` everywhere you reference a purchased or final item. Also apply this to `item0`–`item6` in participant data.

**For champion ability stats** (ranges, cooldowns, damage values) referenced in findings, do not rely on training data. Use WebFetch to look up the champion's page on `https://wiki.leagueoflegends.com/en-us/wiki/<ChampionName>` if you need to cite a specific stat. Only do this if the stat is directly relevant to a finding (e.g., Thresh hook range when citing a positioning error).

Write and run a Python script that extracts the following. You'll need all of it for the analysis.

### From `/tmp/lol_match.json` → `info.participants`

For each of the 10 players:
- `riotIdGameName`, `riotIdTagline`, `championName`, `teamPosition`, `teamId`
- `kills`, `deaths`, `assists`
- `totalMinionsKilled` + `neutralMinionsKilled` = CS
- `goldEarned`, `totalDamageDealtToChampions`
- `physicalDamageDealtToChampions`, `magicDamageDealtToChampions`, `trueDamageDealtToChampions`
- `visionScore`, `wardsPlaced`, `wardsKilled`, `detectorWardsPlaced`
- `timeCCingOthers`, `totalTimeSpentDead`, `totalDamageTaken`
- `item0`–`item6` (final items)
- `challenges.killParticipation`, `challenges.damagePerMinute`, `challenges.goldPerMinute`, `challenges.visionScorePerMinute`, `challenges.laneMinionsFirst10Minutes`

Compute:
- Kill participation per player: (kills + assists) / max(team_kills, 1)
- AD%/AP% split for each team
- Identify the player being analyzed (match by Riot ID)

### From `/tmp/lol_timeline.json` → `info.frames`

One frame per minute. For each frame:
- `participantFrames[pid].totalGold`, `.minionsKilled`, `.jungleMinionsKilled`, `.xp`, `.currentGold`
- `events` — filter and timestamp the following:
  - `CHAMPION_KILL`: `timestamp`, `killerId`, `victimId`, `assistingParticipantIds`, position
  - `ELITE_MONSTER_KILL`: `timestamp`, `monsterType` (DRAGON/BARON_NASHOR/RIFTHERALD/HORDE), `teamId`, `killerId`
  - `BUILDING_KILL`: `timestamp`, `buildingType`, `towerType`, `teamId`, `laneType`
  - `ITEM_PURCHASED`: `timestamp`, `participantId`, `itemId` — track item completion order

Compute from timeline:
- Gold differential (my team vs enemy) at minutes 5, 10, 15, 20, 25
- CS differential per role at minutes 5, 10, 15
- Each player's gold at 5/10/15/20/25 min vs their opponent in the same role
- Jungler: CS per 3-min interval, kill involvement per minute

Convert all `timestamp` values from milliseconds to `MM:SS` format for output.

---

## Step 4 — Analyze across 4 phases and 5 lenses

Work through each phase systematically. For each **finding**, ask yourself:
- Is this backed by a specific number or timestamp?
- Did it meaningfully affect the game outcome?
- Can I give a concrete alternative action?

If the answer to any of those is no, skip it.

### Four phases
1. **Draft / Pre-game** — comp identity, win conditions, power spikes, AD/AP balance
2. **Early game (0–14 min)** — laning, first objectives, jungler pathing, first blood, CS leads
3. **Mid game (14–25 min)** — objective trades, roaming, teamfight initiation, tower control
4. **Late game (25+ min)** — Baron/Elder, inhibitors, teamfight execution, win condition adherence

### Five lenses (apply each to every phase)

**1. Decision audits** — At key moments (first drake spawn ~5 min, Rift Herald ~8 min, second drake, Baron spawn ~20 min, any ace), what did each team do, and was it the right call?

**2. Resource efficiency** — Is each player getting the resources their role requires?
- CS/min role averages: Support ~1.0, ADC/Mid/Top ~7–9, Jungle ~5–7 including camps
- Vision score/min: Support ≥2.5, Jungle ≥1.0
- Damage per gold: high gold + low damage = inefficient

**3. Objective priority mistakes** — Did either team give up a more valuable objective for a less valuable one? (e.g., taking a drake while enemy takes an inhibitor tower)

**4. Teamfight breakdowns** — For any fight with 3+ kills in under 60 seconds:
- Who initiated? Was it a good engage or forced/mistimed?
- Who died first and why?
- What was the gold swing?

**5. Win condition adherence** — What is this comp's win condition (teamfight, pick, split push, scaling, poke)? Did the team play toward it?

---

## Step 5 — Write the coaching report

### Naming conventions (apply throughout the entire report)

**Teams:**
- Team 100 = **Blue team** (spawns bottom-left, attacks top-right)
- Team 200 = **Red team** (spawns top-right, attacks bottom-left)
- Always use "blue team" / "red team" — never T100/T200 or Team 100/Team 200.

**Champions:**
- When referring to any champion in the report text, prefix with **"Ally"** or **"Enemy"** before the name.
- Example: "Enemy Ryze flashed onto Ally Briar in the mid lane river."
- Apply this to every champion mention, including the analyzed player's own champion.

**Map locations:**
- Every kill or fight timestamp must include a map location. Use plain English: "in the bot lane river", "at dragon pit", "mid lane near blue team's outer turret", "in the top side jungle near Baron pit", "at the mid lane intersection", etc.
- Derive location from the event's position coordinates in the timeline JSON: x/y values map roughly as follows (for a standard 15000×15000 map):
  - x < 5000, y < 5000 → bottom-right area (red team base / bot lane)
  - x > 10000, y > 10000 → top-left area (blue team base / top lane)
  - x 5000–10000, y 5000–10000 → mid lane / river
  - x < 6000, y 6000–9000 → bot side river / dragon pit
  - x > 9000, y 6000–9000 → top side river / Baron pit
  - Use judgment to label locations descriptively.

### Finding format

```
[MM:SS | location] PHASE — LENS — Title
Severity: HIGH / MEDIUM / LOW
What happened: One specific sentence with a number or name.
What to do instead: One actionable sentence. Do NOT tell the player to watch a VOD or review footage — just state what to do differently next time.
```

**Severity guide:**
- HIGH = directly caused or prevented a kill, objective, or 500+ gold swing
- MEDIUM = created a disadvantage that compounded over time
- LOW = missed efficiency, minor positioning error, small missed opportunity

### Full report structure

---
### Post-Match Coaching Report — [PlayerName] ([Champion], [Role]) | [W/L] [Duration] | Patch [X]

**Match ID:** `[MATCH_ID]`
**OP.GG:** [paste permalink here — find it on your match history at op.gg/summoners/na/[GameName]-[TagLine]]

> Note: OP.GG uses an opaque permalink format (base64 hash + timestamp) that cannot be computed from the Riot API match ID. Leave the placeholder above and ask the user to paste their OP.GG permalink if they want it linked. If they provide it, update the file.

**Honest Verdict** (1 sentence, blunt): Was this primarily a team loss, a personal loss, or both? Give a single direct verdict — e.g., "This was a team loss driven by [X]; your individual mistakes were fixable but not the deciding factor" or "You made 3 specific errors that directly cost this game." This appears first, before everything else.

**Game Summary** (1–3 sentences): Who won and why — focus on the whole-game factors (jungler dominance, a fed carry, objective control, a specific teamfight) rather than individual mistakes. Call out the biggest macro theme or recurring pattern of the game.

**3 Things to Work On** (surfaced here at the top, detailed at the bottom):
1. **[Skill]** — one-sentence hook on why it mattered this game
2. **[Skill]** — one-sentence hook on why it mattered this game
3. **[Skill]** — one-sentence hook on why it mattered this game

---

**Quick Stats** — inline table for the analyzed player:
KDA | CS | CS/min | Gold | Dmg | Dmg% of team | Vision | KP% | Time Dead

**Team Overview** — 10-player table:
Player | Champion | Role | KDA | CS | Gold | Dmg | KP% | (mark analyzed player with ← YOU)
Label each team's header row as "🔵 Blue Team" or "🔴 Red Team".

---

#### Phase 1: Draft
[1-2 findings on comp identity and win condition]

#### Phase 2: Early Game (0–14 min)
[3-5 findings, the most detailed phase]

#### Phase 3: Mid Game (14–25 min)
[2-4 findings]

#### Phase 4: Late Game (25+ min)
[1-3 findings, or "No major issues detected" if game ended early]

---

### The 3 Swing Moments
Each gets: timestamp + map location, what happened (2-3 sentences with data), why it was the pivot point.

### 3 Things to Work On (detailed)
Ranked by impact. Each must be traceable to a specific finding in this game. Do NOT tell the player to watch VODs — just tell them what went wrong and what to do differently next time.
1. **[Skill]** — why it mattered, and exactly what to do differently
2. **[Skill]** — why it mattered, and exactly what to do differently
3. **[Skill]** — why it mattered, and exactly what to do differently

---

## Step 6 — Save report to file

After writing the report in your response, also save it as a Markdown file:

```
/Users/jinayoon/Projects/lol analysis/reviews/[YYYY-MM-DD]_[HHMM]_[ChampionName].md
```

Derive the timestamp from `info.gameStartTimestamp` in the match JSON (milliseconds → local time):

```python
import datetime
ts = match_data['info']['gameStartTimestamp'] // 1000
dt = datetime.datetime.fromtimestamp(ts)
filename_ts = dt.strftime('%Y-%m-%d_%H%M')
# Result: e.g. "2026-04-08_1822_Zyra.md"
```

Use the Write tool to create the file. The file should contain the full report exactly as written in your response — no extra content, no wrapping. Then tell the user: "Report saved to `reviews/[YYYY-MM-DD]_[HHMM]_[ChampionName].md`."

Create the `reviews/` directory first with a Bash `mkdir -p` call if it doesn't already exist.

---

## Step 7 — Generate the HTML report

After saving the markdown, also write a self-contained `.html` file at the same path (same base name, `.html` extension). It must work by opening it in any browser with no server — all assets loaded from URLs, no local dependencies.

### 7a — Resolve ddragon version and asset URLs

```bash
VERSION=$(curl -s https://ddragon.leagueoflegends.com/api/versions.json \
  | python3 -c "import sys,json; print(json.load(sys.stdin)[0])")
# e.g. "16.7.1" — matches the game patch
```

Asset URL patterns:
- **Champion portrait tile** (26×26 in tables, 20×20 inline):
  `https://ddragon.leagueoflegends.com/cdn/$VERSION/img/champion/{Name}.png`
  Name must be ddragon-formatted: no spaces, special chars removed (e.g. `MissFortune`, `KSante`, `AurelionSol`, `Wukong` → `MonkeyKing`).
- **Champion loading screen art** (120×120 in hero header):
  `https://ddragon.leagueoflegends.com/cdn/img/champion/loading/{Name}_0.jpg`
  No version segment in this URL.
- **Spell icon** (22×22 inline, 26×26 in ability strip):
  `https://ddragon.leagueoflegends.com/cdn/$VERSION/img/spell/{SpellFile}.png`
  Get `SpellFile` from ddragon champion JSON `spells[i].image.full` (e.g. `BraumW.png`, `BraumRWrapper.png`). Fetch:
  `curl -s "https://ddragon.leagueoflegends.com/cdn/$VERSION/data/en_US/champion/{Name}.json"`
- **Item icon** (24–30px):
  `https://ddragon.leagueoflegends.com/cdn/$VERSION/img/item/{itemId}.png`
  Item IDs come from the already-fetched `/tmp/lol_items.json`. If an item isn't in that file, look it up on `https://wiki.leagueoflegends.com/en-us/{ItemName}` rather than guessing.

Always add `onerror="this.style.display='none'"` to every `<img>` tag.

### 7b — Design system (CSS variables)

```css
:root {
  --bg:      #0e0f14;   /* page background */
  --surface: #16181f;   /* cards */
  --surface2:#1e2029;   /* table headers, inline code bg */
  --border:  #2a2d3a;
  --text:    #dde1f0;
  --muted:   #7b8099;
  --blue:    #4e9eff;
  --gold:    #c89b3c;
  --green:   #3dca7e;
  --red:     #e55c5c;
  --yellow:  #f0b429;
  --purple:  #9b7fe8;
}
```

Severity → color: HIGH = `--red`, MEDIUM = `--yellow`, LOW/positive = `--green`, net-positive-medium = `#7eca9c`.

### 7c — Page structure

Build these sections in order:

**1. Hero header** — two-column flex:
- Left: champion loading screen art (120×120, border-radius 10px, 2px gold border) with a strip of 4 ability icons (26×26) beneath it. Each ability icon has a `title="{Key} — {Spell Name}"` attribute.
- Right: `<h1>` title, subtitle line (player · champion · W/L · duration · patch · match ID in monospace badge), then the Honest Verdict and Game Summary as stacked cards.

**2. Quick stats grid** — `repeat(auto-fill, minmax(110px, 1fr))`. Each box: large value + small label. Color overrides: green for vision/KP%, red for deaths/time-dead.

**3. Team overview table** — 10 rows, both teams. Champion name cell includes a 26×26 portrait icon. Analyzed player row: gold background tint (`#c89b3c18`) + YOU badge. Primary carry: ★ suffix.

**4. Match timeline** — see §7d.

**5. Findings by phase** — a phase divider label before each phase, then one card per finding:
- 3px left border colored by severity
- Meta row: timestamp badge (monospace), severity badge, phase/lens badge
- Title line, body paragraph, Fix line (`Fix: ` prefix in `--blue` for errors; green italic for positives)
- Inline 20×20 champion portrait wherever a champion name appears in body/fix text
- Inline 22×22 spell icon + key badge (`E`, `W`, etc.) wherever a specific ability is referenced

**6. Swing moments** — 3 cards, each with a colored left border (red/gold/green), a 22×22 champion icon in the title row, a timestamp badge, and a 2–3 sentence body.

**7. 3 Things to Work On** — yellow-left-bordered cards. For any item timing finding, include an item chip row with icons:
```html
<div style="display:flex;gap:6px;margin:8px 0;flex-wrap:wrap">
  <div style="display:flex;align-items:center;gap:5px;background:var(--surface2);
              border:1px solid var(--border);border-radius:6px;padding:4px 8px;font-size:.78rem">
    <img src="{itemIconUrl}" style="width:24px;height:24px;border-radius:3px" onerror="this.style.display='none'">
    <span>{Item Name}</span>
    <span style="color:var(--muted);font-size:.7rem">✓ {actual time}</span>
  </div>
  <span style="color:var(--muted);align-self:center">→</span>
  <!-- next item chip, mark with yellow border + red time if delayed -->
</div>
```

### 7d — Interactive timeline

The full-width bar represents 0:00 → game duration. All marker positions are:
```
left% = (event_start_seconds / total_game_seconds) * 100
```

Phase band widths:
```
early_pct = (14 * 60) / total_seconds * 100   → "Early (0–14)"
mid_pct   = ((25 - 14) * 60) / total_seconds * 100  → "Mid (14–25)"
late_pct  = 100 - early_pct - mid_pct          → "Late (25+)"
```

**HTML skeleton:**
```html
<div class="timeline-wrap">  <!-- NO overflow:hidden here — tooltips must escape freely -->
  <div class="tl-phases" style="display:flex;height:22px;border-radius:4px;overflow:hidden;margin-bottom:8px">
    <div style="width:{early_pct}%;background:#2563eb30;display:flex;align-items:center;
                justify-content:center;font-size:.65rem;color:rgba(255,255,255,.45)">Early (0–14)</div>
    <div style="width:{mid_pct}%;background:#7c3aed30;...">Mid (14–25)</div>
    <div style="width:{late_pct}%;background:#c026d330;...">Late (25+)</div>
  </div>
  <!-- vertical phase-divider lines at early/mid and mid/late percentages -->
  <div style="position:relative">
    <div style="height:6px;background:var(--border);border-radius:3px"></div>  <!-- ruler -->
    <div style="position:relative;height:56px">   <!-- markers row -->
      <!-- one marker per notable event -->
    </div>
    <div style="display:flex;justify-content:space-between;font-size:.65rem;color:var(--muted)">
      <span>0:00</span> ... <span>{total}</span>
    </div>
  </div>
</div>
```

**Each event marker:**
```html
<div style="position:absolute;top:6px;left:{pct}%;transform:translateX(-50%);cursor:pointer;z-index:10">
  <div style="width:12px;height:12px;border-radius:50%;background:{severityColor};
              border:2px solid var(--bg);transition:transform .15s"
       onmouseover="this.style.transform='scale(1.5)'"
       onmouseout="this.style.transform='scale(1)'"></div>
  <div style="width:1px;height:10px;background:rgba(255,255,255,.2);margin:0 auto"></div>
  <div class="tooltip" style="display:none;position:absolute;bottom:130%;left:50%;
       transform:translateX(-50%);background:#1e2029;border:1px solid var(--border);
       border-radius:6px;padding:9px 12px;font-size:.75rem;width:220px;
       box-shadow:0 8px 24px rgba(0,0,0,.5);z-index:100;pointer-events:none;line-height:1.5;
       {flip: bottom:auto;top:130% if left% > 65}">
    <div style="color:var(--muted);font-size:.7rem">{MM:SS} — {location}</div>
    <div style="font-weight:600;margin:3px 0">
      <img src="{champIcon}" style="width:16px;height:16px;border-radius:3px;vertical-align:middle;
           margin-right:4px" onerror="this.style.display='none'">{title}
    </div>
    <div style="font-size:.68rem;color:{severityColor}">{severity label}</div>
    <div style="margin-top:5px;color:#b0b8d0;font-size:.72rem">{one-line summary}</div>
  </div>
</div>
```

Tooltip show/hide via inline JS on the parent div:
```html
onmouseenter="this.querySelector('.tooltip').style.display='block'"
onmouseleave="this.querySelector('.tooltip').style.display='none'"
```

Pin size: 14–16px for HIGH/key positive events; 12px default. Flip tooltip (bottom→top of marker) when `left% > 65` to avoid running off the right edge.

**CRITICAL:** `.timeline-wrap` must NOT have `overflow:hidden`. The phase band `<div>` gets `overflow:hidden` for its own rounded corners, but the outer wrapper must let tooltips escape.

### 7e — Icon placement reference

| Where | Icon | Size |
|---|---|---|
| Hero header: champion | Loading screen art | 120×120 |
| Hero header: ability strip | Spell icons Q/W/E/R | 26×26 |
| Team table: champion column | Portrait tile | 26×26 |
| Finding body/fix: champion named | Portrait tile | 20×20 inline |
| Finding fix: ability named | Spell icon + key badge | 22×22 + badge |
| Timeline tooltip: title | Portrait tile | 16×16 inline |
| Swing moment: card title | Portrait tile | 22×22 |
| Work-on: item chip | Item icon | 24×24 |
| Work-on: inline item mention | Item icon | 22×22 inline |

Key badge style: `font-size:.65rem;font-weight:700;background:#4e9eff22;color:var(--blue);border-radius:3px;padding:1px 4px;font-family:monospace`

### 7f — File save

Same directory and base name as the markdown:
```
/Users/jinayoon/Projects/lol analysis/reviews/[YYYY-MM-DD]_[HHMM]_[Champion].html
```

Tell the user both files were saved once done.

### 7g — Required disclaimer

The Riot Games developer policies require this notice on all products using the API. Add it as a `<footer>` at the bottom of every generated HTML report, after the closing `</div>` of `.container`:

```html
<footer style="max-width:900px;margin:40px auto 0;padding:20px 16px;
               border-top:1px solid var(--border);font-size:.72rem;
               color:var(--muted);line-height:1.6;text-align:center">
  lol-match-analysis isn't endorsed by Riot Games and doesn't reflect the views
  or opinions of Riot Games or anyone officially involved in producing or managing
  Riot Games properties. Riot Games and all associated properties are trademarks
  or registered trademarks of Riot Games, Inc.
</footer>
```

Also append the same text (plain, no HTML) to the bottom of every generated `.md` report, separated by a `---` divider.

---

## Tone and standards

- Every finding must cite a timestamp, a number, or a player name. No vague claims.
- Be honest: if a loss was a team problem, say so. If the player made fixable mistakes, name them.
- If the player did something well, acknowledge it — good play that didn't get rewarded is worth noting.
- Don't pad. If a phase had no significant findings, write "No major issues detected in this phase."
- The Practice Focuses are the most important part. Make them specific to this game, not generic advice.

## Common errors to avoid

**Smite attribution:** Only the jungler has Smite. Any player can last-hit an objective with a regular attack — if the `ELITE_MONSTER_KILL` killerId is a non-jungler, say they "secured" or "last-hit" the objective, never that they "landed the smite."

**Counterplay advice:** Before telling the player to dodge or avoid an enemy ability, check whether the analyzed champion's kit directly counters it. For example: Braum E (Unbreakable) blocks projectiles — advising a Braum player to dodge Miss Fortune's Bullet Time is wrong; the correct advice is to W into position and pop E into the channel. When giving counterplay advice, use the champion's actual toolkit first.
