# analyze-lol-match

[![Demo screenshot](assets/demo-screenshot.png)](https://www.awesomescreenshot.com/video/51360222?key=e6d8dd45551a7f17d2cc092a93c839e0)

[![Watch demo](https://img.shields.io/badge/Watch%20demo-%E2%96%B6%20Awesome%20Screenshot-1a1a2e?style=for-the-badge&logo=data:image/svg%2bxml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZmlsbD0id2hpdGUiIGQ9Ik04IDV2MTRsMTEtN3oiLz48L3N2Zz4=)](https://www.awesomescreenshot.com/video/51360222?key=e6d8dd45551a7f17d2cc092a93c839e0)
[![Sample report](https://img.shields.io/badge/Sample%20report-%F0%9F%93%84%20Braum%20Support-4e9eff?style=for-the-badge)](https://jinayoon.github.io/lol-reviews/sample-braum.html)

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
| [`skills/analyze-lol-match/SKILL.md`](skills/analyze-lol-match/SKILL.md) | Skill definition (orchestration + pipeline) |
| [`scripts/`](scripts/) | `fetch_lol_match.py`, `summarize_match_for_coach.py`, `render_coach_report.py` |
| [`docs/`](docs/) | Reference docs (Riot API, templates, rubric, pitfalls, disclaimers) |
| [`reviews/`](reviews/) | Local output for `.md` / `.html` reports (**gitignored** — not on GitHub) |
| [`assets/`](assets/) | Demo screenshot and other assets |

**Sample HTML on the web:** hosted from a **separate** Pages repo ([`lol-reviews`](https://github.com/jinayoon/lol-reviews) — create it from the `lol-reviews` export folder next to this project; see that folder’s `README.md`). Disable Pages on this repo in GitHub Settings if you still have it enabled.

The coaching pipeline needs a **full clone** of this repository so `scripts/`, `docs/`, and the skill folder under `skills/` are all present. `SKILL.md` runs `python3` against those paths; downloading only the skill file is not enough.

---

## Install (for people brand new to using Claude Code)

These steps install Claude Code, clone the repo, register the skill, and set the repo root so the skill can find `scripts/` and `docs/`.

### Windows

**1. Install Node.js**  
Go to [nodejs.org/en/download](https://nodejs.org/en/download) and use the **Windows Installer** (LTS). Download, run the installer, and finish the wizard (including the option to install tools for native modules if the installer offers it).

**2. Install Python 3**  
Go to [python.org/downloads](https://www.python.org/downloads/) and install **Python 3** for Windows. In the installer, enable **Add python.exe to PATH** (or add it manually afterward). Open a new PowerShell window and confirm `python3 --version` or `python --version` works; the skill runs `python3` in its commands.

**3. Install Git for Windows**  
Go to [git-scm.com/downloads/win](https://git-scm.com/downloads/win) and install the 64-bit build. Git is required for `git clone` and for Claude Code on Windows.

**4. Install Claude Code**  
Open **PowerShell** and run these commands **one at a time**:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

*(If Windows asks to confirm the policy change, type `Y` and press Enter.)*

```powershell
irm https://claude.ai/install.ps1 | iex
```

```powershell
npm install -g @anthropic-ai/claude-code
```

When everything finishes, **close PowerShell completely and open a new window** so `claude` is recognized.

**5. Connect your account**  
Run `claude`, finish browser login, then type `/exit` in the session.

**6. Clone this repo and wire the skill**  
Choose a folder (for example `Documents\Source` or your user folder), then:

```powershell
cd $HOME
git clone https://github.com/jinayoon/analyze-lol-match.git
cd analyze-lol-match
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.claude\skills"
```

Link Claude’s skill folder to the skill inside your clone. From the **`analyze-lol-match` repo root**, run (adjust if your clone lives elsewhere):

```powershell
$target = "$env:USERPROFILE\.claude\skills\analyze-lol-match"
$source = (Resolve-Path ".\skills\analyze-lol-match").Path
if (Test-Path $target) { Remove-Item $target -Recurse -Force }
cmd /c mklink /J "$target" "$source"
```

`mklink /J` creates a **directory junction** so Claude reads `SKILL.md` from your clone without copying files. If that command fails, create the skills folder and copy the skill file, **and** you must still set the repo root in the next step:

```powershell
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.claude\skills\analyze-lol-match"
Copy-Item ".\skills\analyze-lol-match\SKILL.md" "$env:USERPROFILE\.claude\skills\analyze-lol-match\SKILL.md"
```

**7. Point the skill at the repo root (recommended)**  
Set a user environment variable to the folder that contains `scripts` and `docs` (your clone path), for example:

```powershell
setx ANALYZE_LOL_MATCH_ROOT "$HOME\analyze-lol-match"
```

Close PowerShell and open a **new** window so `setx` takes effect.  
(Legacy: `LOL_MATCH_ANALYSIS_ROOT` still works in `SKILL.md`.)

**8. Get a Riot API key**  
Go to [developer.riotgames.com](https://developer.riotgames.com), sign in with your Riot account, and copy the key from the dashboard. *(Developer keys expire about every 24 hours — use a fresh key when you start a session.)*

**9. Run it**  
Start `claude`, then `/analyze-lol-match`, and provide your key and Riot ID when asked.

---

### Mac

**1. Install Node.js**  
Go to [nodejs.org/en/download](https://nodejs.org/en/download) and use the **macOS Installer** (LTS). Download, run the installer, and finish the wizard.

**2. Install Python 3**  
Go to [python.org/downloads](https://www.python.org/downloads/) and install the latest **Python 3** for macOS. The scripts use the standard library only, but you need the `python3` command available in Terminal.

**3. Install Git (if you do not have it)**  
Open Terminal and run `git --version`. If macOS offers to install the **Command Line Developer Tools**, accept and wait for the install to finish.

**4. Install Claude Code**  
In Terminal, run these **two commands**, one at a time:

```bash
curl -fsSL https://claude.ai/install.sh | bash
```

```bash
npm install -g @anthropic-ai/claude-code
```

When both finish, **quit Terminal completely and open a new window** so the `claude` command is on your `PATH`.

**5. Connect your account**  
Run `claude` and press Enter. Complete login in the browser, return to Terminal, then type `/exit` to leave the session.

**6. Clone this repo and wire the skill**  
Pick a folder where you keep projects, then:

```bash
git clone https://github.com/jinayoon/analyze-lol-match.git
cd analyze-lol-match
mkdir -p ~/.claude/skills
ln -sfn "$(pwd)/skills/analyze-lol-match" ~/.claude/skills/analyze-lol-match
```

That symlink makes Claude load `SKILL.md` from your clone. The pipeline still needs to know the **repository root** (the folder that contains `scripts/` and `docs/`).

**7. Point the skill at the repo root (recommended)**  
So you do not have to `cd` into the clone every time, add this to `~/.zshrc` (or `~/.bash_profile` if you use bash), using the real path to your clone:

```bash
export ANALYZE_LOL_MATCH_ROOT="$HOME/path/to/analyze-lol-match"
```

Open a **new** Terminal tab or run `source ~/.zshrc`.  
(Legacy: `LOL_MATCH_ANALYSIS_ROOT` still works in `SKILL.md` if you already set it.)

**8. Get a Riot API key**  
Go to [developer.riotgames.com](https://developer.riotgames.com), sign in with your Riot account, and copy the key from the dashboard. *(Developer keys expire about every 24 hours — use a fresh key when you start a session.)*

**9. Run it**  
Start `claude`, then run `/analyze-lol-match`. It will ask for your API key and Riot ID (`Name#TAG`) and walk through the full pipeline using your clone.

---

## Install (for developers)

Assume **Node.js**, **Python 3**, **Git**, and **Claude Code** are already installed and you can run `claude` from a terminal.

**1. Clone and register the skill (macOS / Linux)**

```bash
git clone https://github.com/jinayoon/analyze-lol-match.git
cd analyze-lol-match
mkdir -p ~/.claude/skills
ln -sfn "$(pwd)/skills/analyze-lol-match" ~/.claude/skills/analyze-lol-match
```

**2. Repo root for scripts** — either `cd` into the clone whenever you run the pipeline or set (e.g. in your shell profile):

```bash
export ANALYZE_LOL_MATCH_ROOT="$(pwd)"   # or an absolute path to the clone
```

**Windows (from repo root in PowerShell):** junction as in the beginner steps, or copy `skills\analyze-lol-match\SKILL.md` into `%USERPROFILE%\.claude\skills\analyze-lol-match\` and set `ANALYZE_LOL_MATCH_ROOT` to the clone path.

**3. Manual script usage** (from repository root, same as `SKILL.md`):

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

**Contributing:** Keep [`skills/analyze-lol-match/SKILL.md`](skills/analyze-lol-match/SKILL.md) lean; put long reference material in [`docs/`](docs/).

---

## Troubleshooting

**`claude: command not found` / `claude` is not recognized**  
You need to close your Terminal or PowerShell window completely and reopen it after installing Claude Code. The install script adds `claude` to your PATH, but that change only takes effect in new shell sessions – not the one you ran the installer in.

If it still doesn't work after reopening:

- **Mac:** Run `echo $PATH` and confirm it includes `~/.npm-global/bin` or wherever Claude Code was installed. If not, re-run the install script in the new terminal window.
- **Windows:** Make sure you installed Git for Windows before Claude Code (see **Install** above). Some Windows setups also require running PowerShell as Administrator for the install to complete.

**`execution of scripts is disabled on this system` (Windows)**  
PowerShell blocks scripts by default. Run this first, then re-run the Claude Code install:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

If it asks "Do you want to change the execution policy?", type `Y` and hit Enter.

**Riot API 429 / rate limits** — `fetch_lol_match.py` retries; avoid hammering the API manually.

---

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

analyze-lol-match isn't endorsed by Riot Games and doesn't reflect the views or opinions of Riot Games or anyone officially involved in producing or managing Riot Games properties. Riot Games and all associated properties are trademarks or registered trademarks of Riot Games, Inc.
