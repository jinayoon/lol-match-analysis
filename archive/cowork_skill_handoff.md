# LoL Post-Match Coach Skill — Cowork Handoff

## What to tell Cowork

"I want to create a skill called `lol-game-review`. I already have the SKILL.md written and 3 eval cases ready. Please:
1. Save the SKILL.md to the user skills folder
2. Run the 3 evals (with-skill vs without-skill baseline)
3. Generate the eval viewer for me to review
4. Iterate based on my feedback"

---

## The SKILL.md (save this as-is)

```markdown
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

You need two things:

1. **Riot API key** — dev keys expire every 24h. If not already provided, ask:
   > "Paste your Riot API key (grab a fresh one from developer.riotgames.com — it's on your dashboard)."

2. **Player identity** — Riot ID in `Name#TAG` format. If the user hasn't specified, ask which player to analyze (default to the person asking). If you already know from context, use it.

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
```

Verify both files are valid JSON. If you get a 401, tell the user the key expired.

---

## Step 3 — Extract data with Python

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

Structure every finding as a block:

```
[MM:SS] PHASE — LENS — Title
Severity: HIGH / MEDIUM / LOW
What happened: One specific sentence with a number or name.
What to do instead: One specific, actionable sentence.
```

**Severity guide:**
- HIGH = directly caused or prevented a kill, objective, or 500+ gold swing
- MEDIUM = created a disadvantage that compounded over time
- LOW = missed efficiency, minor positioning error, small missed opportunity

### Full report structure

---
### Post-Match Coaching Report — [PlayerName] ([Champion], [Role]) | [W/L] [Duration] | Patch [X]

**Quick Stats** — inline table for the analyzed player:
KDA | CS | CS/min | Gold | Dmg | Dmg% of team | Vision | KP% | Time Dead

**Team Overview** — 10-player table:
Player | Champion | Role | KDA | CS | Gold | Dmg | KP% | (mark analyzed player with ← YOU)

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
Each gets: timestamp, what happened (2-3 sentences with data), why it was the pivot point.

### 3 Practice Focuses
Ranked by impact. Each must be traceable to a specific finding in this game.
1. **[Skill]** — why, and what to practice specifically
2. **[Skill]** — why, and what to practice specifically
3. **[Skill]** — why, and what to practice specifically

---

## Tone and standards

- Every finding must cite a timestamp, a number, or a player name. No vague claims.
- Be honest: if a loss was a team problem, say so. If the player made fixable mistakes, name them.
- If the player did something well, acknowledge it — good play that didn't get rewarded is worth noting.
- Don't pad. If a phase had no significant findings, write "No major issues detected in this phase."
- The Practice Focuses are the most important part. Make them specific to this game, not generic advice.
```

---

## The 3 Eval Cases

### Eval 1 — Positioning / early deaths
**Prompt:**
```
RGAPI-<fresh_key>

can you analyze my last game? i'm ahrisoo#ARIS. i keep dying early and i don't know if it's my positioning or just bad luck
```
**What a good output looks like:** Timestamped findings that identify specific deaths (with MM:SS), classify each as positioning error vs. unavoidable, severity ratings, and practice focuses that address deaths specifically.

**Assertions to check:**
- Contains at least 3 timestamps in MM:SS format
- Contains HIGH/MEDIUM/LOW severity labels
- Contains "What to do instead" sections
- Names specific deaths with timestamps (not generic advice)
- Ends with numbered practice focuses specific to this game

---

### Eval 2 — Swing moments / momentum
**Prompt:**
```
key: RGAPI-<fresh_key>, player: ahrisoo#ARIS

what were the swing moments in my last game? felt like we were winning then suddenly lost
```
**What a good output looks like:** 2-3 swing moments with exact timestamps and gold swing data. Explains *why* each was pivotal. Also addresses whether the feeling of "winning then losing" actually matches the data.

**Assertions to check:**
- Swing moments include specific MM:SS timestamps
- Mentions specific gold numbers or gold differential
- Identifies at least 2 distinct swing moments
- Each swing moment explains why it was pivotal
- Addresses the "felt like we were winning" framing with data

---

### Eval 3 — Full phased breakdown
**Prompt:**
```
RGAPI-<fresh_key> — review ahrisoo#ARIS's last game as a coach. give me the full breakdown across early/mid/late
```
**What a good output looks like:** All 4 phases covered, findings in `[MM:SS] PHASE — LENS — Title` format, severity on every finding, 10-player scoreboard, 3 practice focuses at the end.

**Assertions to check:**
- Covers all 4 phases: Draft, Early Game, Mid Game, Late Game
- Contains at least 5 timestamps in MM:SS format
- Each finding has HIGH/MEDIUM/LOW severity
- Findings follow the `[MM:SS] PHASE — LENS` format
- Contains a 10-player scoreboard table
- Ends with 3 numbered practice focuses
- Findings cite specific player names, numbers, or events

---

## Context / Notes for Cowork

- **API note:** Use `curl` via Bash for all Riot API calls, NOT Python `requests` — there are SSL issues with LibreSSL on Mac that cause Python requests to fail silently.
- **Rate limits:** Riot dev keys are limited to 20 requests/second, 100 requests/2 min. Fetch match and timeline sequentially with a small sleep between, not in parallel.
- **Key expiry:** Riot dev keys expire every 24 hours. The skill correctly prompts the user for a fresh key each time.
- **Region:** All API calls use `americas.api.riotgames.com` for NA players.
- **Timeline size:** Timeline JSON is ~1MB per match. Parse with Python3 inline scripts, not in memory all at once if possible.
- **The player:** ahrisoo#ARIS is a support main (Zyra, Nami, Lulu, Janna, Nautilus). The skill is designed for any player/role though.

---

## Example output quality bar

Here's a sample of what a HIGH-quality finding looks like (from a real test run on match NA1_5533826618):

```
[09:36–09:43] EARLY — Teamfight Breakdown — Three deaths in 7 seconds bot side
Severity: HIGH
What happened: Swain killed Sivir at 09:36, your Irelia at 09:40, and you at 09:43 in rapid succession — 3 players dead in 7 seconds, ~900g kill gold for Swain, free Chemtech Drake at 11:27.
What to do instead: The moment Sivir died, your fight was over. Disengage immediately — a Nami without her carry is just a target.
```

A LOW-quality finding (what the baseline produces without the skill):

```
The early deaths are probably the main thing to reflect on — try to play more passively when your team is behind.
```

The skill should consistently produce the high-quality version.
