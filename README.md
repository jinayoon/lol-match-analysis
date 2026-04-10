# lol-match-analysis

[![Demo screenshot](assets/demo-screenshot.png)](https://www.awesomescreenshot.com/video/51360222?key=e6d8dd45551a7f17d2cc092a93c839e0)

[![Watch demo](https://img.shields.io/badge/Watch%20demo-%E2%96%B6%20Awesome%20Screenshot-1a1a2e?style=for-the-badge&logo=data:image/svg%2bxml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZmlsbD0id2hpdGUiIGQ9Ik04IDV2MTRsMTEtN3oiLz48L3N2Zz4=)](https://www.awesomescreenshot.com/video/51360222?key=e6d8dd45551a7f17d2cc092a93c839e0)
[![Sample report](https://img.shields.io/badge/Sample%20report-%F0%9F%93%84%20Braum%20Support-4e9eff?style=for-the-badge)](https://jinayoon.github.io/lol-match-analysis/sample-braum.html)

A Claude Code skill that gives you an instant private coaching report for your last League of Legends match.

Designed for people who know they should review their matches to get better but are too lazy. It assumes you're never going to watch your replays and just tells you concrete things you should work on, with enough context to jog your memory on what happened and why.

I find it most helpful to generate and read the analysis right after a game while having my op.gg or in-client match details page open.

## What it does

- Analyzes your last match using your Riot ID and a Riot API key you provide
- Pulls live item and champion data from the official League of Legends wiki and Data Dragon — no stale patch info
- Breaks down all 4 game phases: draft, early, mid, and late game
- Covers decision audits, resource efficiency, objective priority, teamfight breakdowns, and win condition adherence
- Identifies the 3 swing moments that actually decided the game
- Gives 3 prioritized things to work on — grounded in specific timestamps from *this* game, not generic advice
- Saves the full report as a Markdown file

## Install

```bash
mkdir -p ~/.claude/skills/lol-match-analysis
curl -o ~/.claude/skills/lol-match-analysis/SKILL.md \
  "https://raw.githubusercontent.com/jinayoon/lol-match-analysis/main/skills/lol-match-analysis/SKILL.md"
```

## Usage

In Claude Code, run:

```
/lol-match-analysis
```

You'll be asked for:
1. Your **Riot API key** — get a free one at [developer.riotgames.com](https://developer.riotgames.com) (they expire every 24h so grab a fresh one)
2. Your **Riot ID** — format: `Name#TAG`

## Contributing

Contributions welcome! If you want to extend the analysis, add support for other regions, or improve the coaching framework, feel free to open a PR.

## Requirements

- [Claude Code](https://claude.ai/code)
- A Riot Games developer API key (free)
- `curl` and `python3` in your terminal (standard on Mac/Linux)
