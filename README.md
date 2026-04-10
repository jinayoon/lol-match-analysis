# lol-match-analysis

A Claude Code skill that gives you an instant private coaching report for your last League of Legends match.

Designed for people who know they should review their matches to get better but are too lazy. It assumes you're never going to watch your replays and just tells you concrete things you should work on, with enough context to jog your memory on what happened and why.

I find it most helpful to generate and read the analysis right after a game while having my op.gg or in-client match details page open.

## What it does

- Analyzes your last match using your Riot ID and a Riot API key you provide
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

## Requirements

- [Claude Code](https://claude.ai/code)
- A Riot Games developer API key (free)
- `curl` and `python3` in your terminal (standard on Mac/Linux)
