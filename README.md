# lol-match-analysis

[![Demo screenshot](assets/demo-screenshot.png)](https://www.awesomescreenshot.com/video/51360222?key=e6d8dd45551a7f17d2cc092a93c839e0)

[![Watch demo](https://img.shields.io/badge/Watch%20demo-%E2%96%B6%20Awesome%20Screenshot-1a1a2e?style=for-the-badge&logo=data:image/svg%2bxml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZmlsbD0id2hpdGUiIGQ9Ik04IDV2MTRsMTEtN3oiLz48L3N2Zz4=)](https://www.awesomescreenshot.com/video/51360222?key=e6d8dd45551a7f17d2cc092a93c839e0)
[![Sample report](https://img.shields.io/badge/Sample%20report-%F0%9F%93%84%20Braum%20Support-4e9eff?style=for-the-badge)](https://jinayoon.github.io/lol-match-analysis/sample-braum.html)

A Claude Code skill that gives you an instant private coaching report for your last League of Legends match.

Designed for people who know they should review their matches to get better but are too lazy. It assumes you're never going to watch your replays and just tells you concrete things you should work on, with enough context to jog your memory on what happened and why.

I find it most helpful to generate and read the analysis right after a game while having my op.gg or in-client match details page open.

> **Note:** This only works in Terminal (Mac) or PowerShell (Windows) – not the Claude Code desktop app.

## What it does

- Analyzes your last **Ranked Summoner’s Rift** match using your Riot ID, **platform shard** (e.g. `na1`), and a Riot API key you provide
- Uses scripts in this repo to fetch match + timeline + Data Dragon item/champion data — no guessed item names
- Breaks down all 4 game phases: draft, early, mid, and late game
- Covers decision audits, resource efficiency, objective priority, teamfight breakdowns, and win condition adherence
- Identifies the 3 swing moments that actually decided the game
- Gives 3 prioritized things to work on – grounded in specific timestamps from *this* game, not generic advice
- Saves the full report as Markdown and can render **HTML** via `scripts/render_coach_report.py`

---

## Repository layout

| Path | Purpose |
|------|---------|
| [`skills/lol-match-analysis/SKILL.md`](skills/lol-match-analysis/SKILL.md) | Skill definition (orchestration + pipeline) |
| [`scripts/`](scripts/) | `fetch_lol_match.py`, `summarize_match_for_coach.py`, `render_coach_report.py` |
| [`docs/`](docs/) | Reference docs (Riot API, templates, rubric, pitfalls, disclaimers) |
| [`reviews/`](reviews/) | Default output for `.md` / `.html` reports (optional: ignore in git) |
| [`assets/`](assets/) | Demo screenshot and other assets |

The **full coaching pipeline** expects a **clone** of this repo so `scripts/` and `docs/` exist. Installing **only** `SKILL.md` with `curl` (below) gives you the skill instructions without the scripts — fine for experimentation, but for the automated flow you want a **full install**.

---

## Quick start (no coding required)

### Mac

**1. Install Node.js**  
Go to [nodejs.org/en/download](https://nodejs.org/en/download) and click the green button that says **macOS Installer**. Download and run it.

**2. Install Claude Code**  
Open Terminal (search "Terminal" in Spotlight) and paste these **two commands**, one at a time:

```bash
curl -fsSL https://claude.ai/install.sh | bash
```

```bash
npm install -g @anthropic-ai/claude-code
```

When both finish, **close Terminal completely and reopen it** before continuing. This is required for the `claude` command to be recognized.

**3. Connect your account**  
Type `claude` and hit enter. It'll open a browser to log in – follow the prompts, then come back to Terminal. Once you're in, type `/exit` to close the session.

**4. Install the skill**  
Back in Terminal, paste:

```bash
mkdir -p ~/.claude/skills/lol-match-analysis && curl -o ~/.claude/skills/lol-match-analysis/SKILL.md "https://raw.githubusercontent.com/jinayoon/lol-match-analysis/main/skills/lol-match-analysis/SKILL.md"
```

**5. Get a Riot API key**  
Go to [developer.riotgames.com](https://developer.riotgames.com), log in with your League account, and copy the key on your dashboard. Free, takes 30 seconds. *(Keys expire every 24h – grab a fresh one each session.)*

**6. Run it**  
Type `claude` to start a session, then type `/lol-match-analysis` and hit enter. It'll ask for your API key and Riot ID (`Name#TAG`), then analyze your last game automatically.

---

### Windows

**1. Install Node.js**  
Go to [nodejs.org/en/download](https://nodejs.org/en/download) and click the green button that says **Windows Installer**. Download and run it.

**2. Install Git for Windows**  
Go to [git-scm.com/downloads/win](https://git-scm.com/downloads/win) and click the download button for the 64-bit installer. Required for Claude Code to work on Windows.

**3. Install Claude Code**  
Open PowerShell (search "PowerShell" in the Start menu) and paste these **two commands**, one at a time:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

*(This unlocks script execution – Windows blocks it by default. If it asks "Do you want to change the execution policy?", type `Y` and hit Enter.)*

```powershell
irm https://claude.ai/install.ps1 | iex
```

```powershell
npm install -g @anthropic-ai/claude-code
```

When both finish, **close PowerShell completely and reopen it** before continuing. This is required for the `claude` command to be recognized.

**4. Connect your account**  
Type `claude` and hit enter. It'll open a browser to log in – follow the prompts, then come back to PowerShell. Once you're in, type `/exit` to close the session.

**5. Install the skill**  
Back in PowerShell, paste:

```powershell
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.claude\skills\lol-match-analysis"; Invoke-WebRequest -Uri "https://raw.githubusercontent.com/jinayoon/lol-match-analysis/main/skills/lol-match-analysis/SKILL.md" -OutFile "$env:USERPROFILE\.claude\skills\lol-match-analysis\SKILL.md"
```

**6. Get a Riot API key**  
Go to [developer.riotgames.com](https://developer.riotgames.com), log in with your League account, and copy the key on your dashboard. Free, takes 30 seconds. *(Keys expire every 24h – grab a fresh one each session.)*

**7. Run it**  
Type `claude` to start a session, then type `/lol-match-analysis` and hit enter. It'll ask for your API key and Riot ID (`Name#TAG`), then analyze your last game automatically.

---

## Full install (recommended — scripts + `docs/`)

For the pipeline in `SKILL.md` (`fetch_lol_match.py`, digest, HTML, reading `docs/`), clone the repo and point Claude at the skill folder:

```bash
git clone https://github.com/jinayoon/lol-match-analysis.git
cd lol-match-analysis
mkdir -p ~/.claude/skills
ln -sfn "$(pwd)/skills/lol-match-analysis" ~/.claude/skills/lol-match-analysis
```

Optional — if you don’t always `cd` into the repo:

```bash
export LOL_MATCH_ANALYSIS_ROOT="$(pwd)"   # e.g. add to ~/.zshrc
```

**Windows:** use **Copy** instead of symlink if needed:

```powershell
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.claude\skills\lol-match-analysis"
Copy-Item "skills\lol-match-analysis\SKILL.md" "$env:USERPROFILE\.claude\skills\lol-match-analysis\SKILL.md"
```

…and keep a full clone somewhere so `scripts/` and `docs/` exist; set `LOL_MATCH_ANALYSIS_ROOT` to that folder.

### Manual script usage (from repo root)

```bash
export RIOT_API_KEY="RGAPI-..."
export MATCH_EXPORT="/tmp/lol_match_export"
rm -rf "$MATCH_EXPORT" && mkdir -p "$MATCH_EXPORT"

python3 scripts/fetch_lol_match.py --riot-id "Summoner#TAG" --platform na1 --out "$MATCH_EXPORT" --timeline-optional
python3 scripts/summarize_match_for_coach.py --dir "$MATCH_EXPORT" --focus-riot "Summoner#TAG" --write-md
python3 scripts/render_coach_report.py \
  --digest "$MATCH_EXPORT/coach_digest.json" \
  --markdown "reviews/your_report.md" \
  --out "reviews/your_report.html" \
  --append-disclaimer-md
```

---

## Troubleshooting

**`claude: command not found` / `claude` is not recognized**  
You need to close your Terminal or PowerShell window completely and reopen it after installing Claude Code. The install script adds `claude` to your PATH, but that change only takes effect in new shell sessions – not the one you ran the installer in.

If it still doesn't work after reopening:

- **Mac:** Run `echo $PATH` and confirm it includes `~/.npm-global/bin` or wherever Claude Code was installed. If not, re-run the install script in the new terminal window.
- **Windows:** Make sure you installed Git for Windows (Step 2) before Claude Code. Some Windows setups also require running PowerShell as Administrator for the install to complete.

**`execution of scripts is disabled on this system` (Windows)**  
PowerShell blocks scripts by default. Run this first, then re-run the Claude Code install:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

If it asks "Do you want to change the execution policy?", type `Y` and hit Enter.

**Riot API 429 / rate limits** — `fetch_lol_match.py` retries; avoid hammering the API manually.

---

## For developers

```bash
# Mac/Linux — same as published install, or clone + symlink (see Full install above)
curl -fsSL https://claude.ai/install.sh | bash
mkdir -p ~/.claude/skills/lol-match-analysis
curl -o ~/.claude/skills/lol-match-analysis/SKILL.md \
  "https://raw.githubusercontent.com/jinayoon/lol-match-analysis/main/skills/lol-match-analysis/SKILL.md"
```

Contributors: use a **full clone**; keep `SKILL.md` lean and put long reference in `docs/`.

## Contributing

Contributions welcome! If you want to extend the analysis, add support for other regions, or improve the coaching framework, feel free to open a PR.

## Requirements

- [Node.js](https://nodejs.org/en/download) (LTS)
- [Python 3](https://www.python.org/downloads/) (for scripts; stdlib only)
- Claude Code – install via Terminal/PowerShell (see above), not the desktop app
- A Riot Games developer API key (free)
- Mac: Terminal (built in)
- Windows: PowerShell + [Git for Windows](https://git-scm.com/downloads/win)

---

lol-match-analysis isn't endorsed by Riot Games and doesn't reflect the views or opinions of Riot Games or anyone officially involved in producing or managing Riot Games properties. Riot Games and all associated properties are trademarks or registered trademarks of Riot Games, Inc.
