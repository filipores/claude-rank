# claude-rank

Gamify your Claude Code usage. Earn XP, level up, unlock achievements, and maintain streaks — all fully automatic.

![Claude Rank](claude-rank-badge.svg)

```
╭───────────────── CLAUDE RANK ──────────────────╮
│                                                │
│   Level 16 - Context Master                    │
│   [██████████░░░░░░░░░░] 4,916/8,951 XP        │
│   Total: 55.3K XP                              │
│                                                │
│   Streak: 7 days  |  Freezes: 2/3              │
│   Sessions: 1,292  |  Messages: 421.5K         │
│                                                │
│   Recent Achievements:                         │
│   Centurion (Complete 100 sessions)             │
│   Night Owl (Session between midnight-5 AM)     │
│                                                │
│   Almost There:                                │
│   Iron Will: 19/30 (63%)                       │
│   On Fire: 5/7 (71%)                           │
│                                                │
╰────────────────────────────────────────────────╯
```

## Install

```bash
/install filipores/claude-rank
```

That's it. No manual config needed — everything works automatically after install.

### What happens on install

- **SessionStart hook** — Claude sees your rank at the start of every session
- **PostToolUse hook** — XP is tracked in real-time after each tool call
- **MCP server** — Claude can query your stats, achievements, and badge mid-conversation
- **Slash commands** — `/rank`, `/achievements`, `/wrapped`, `/badge`

### Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI
- Python 3.11+
- `jq` (for the status line hook)

## Features

- **XP System** — Earn XP from sessions, messages, tool calls, and more
- **50 Levels, 10 Tiers** — From *Prompt Novice* to *Omega Coder*
- **25 Achievements** — Common, Uncommon, Rare, Epic, and Legendary
- **Streak Tracking** — Daily streaks with freezes and grace periods
- **Prestige System** — Hit Level 50? Reset and earn permanent star badges
- **GitHub Badge** — Generate an SVG badge for your README
- **Claude Code Wrapped** — Monthly, yearly, or all-time stats summary
- **MCP Server** — Claude can query your rank mid-conversation
- **Anti-Gaming** — Daily caps, diminishing returns, minimum thresholds
- **Privacy-First** — All data stays local, reads from `~/.claude/`

## Slash Commands

After installing the plugin, these commands are available in Claude Code:

| Command | Description |
|---------|-------------|
| `/rank` | Show your rank dashboard |
| `/achievements` | List all 25 achievements with progress |
| `/wrapped` | Stats summary (month, year, or all-time) |
| `/badge` | Generate an SVG badge for your GitHub README |

## Tier System

| Tier | Levels | Name | Color |
|------|--------|------|-------|
| 1 | 1-5 | Prompt Novice | Grey |
| 2 | 6-10 | Code Apprentice | Green |
| 3 | 11-15 | Bug Slayer | Blue |
| 4 | 16-20 | Context Master | Purple |
| 5 | 21-25 | Refactor Sage | Indigo |
| 6 | 26-30 | Pipeline Architect | Gold |
| 7 | 31-35 | Token Whisperer | Platinum |
| 8 | 36-40 | Neural Commander | Cyan |
| 9 | 41-45 | Singularity Vanguard | Magenta |
| 10 | 46-50 | Omega Coder | Obsidian+Gold |

## XP System

| Action | XP |
|--------|-----|
| Session completed | 10 |
| Message sent | 1 |
| Tool call | 2 |
| Unique project/day | 5 |
| File edit | 3 |
| Commit | 5 |

**Multipliers**: 7-day streak (1.25x), 14-day (1.5x), 30-day (2.0x), first session of day (1.5x).

**Anti-gaming**: Daily cap 800 XP, diminishing returns after 500, min 5 tool calls per session.

## Achievements

25 achievements across 5 rarity tiers:

<details>
<summary><strong>Common</strong> (6)</summary>

| Achievement | Condition |
|-------------|-----------|
| Hello, World | Complete your first session |
| Thousand Voices | Send 1,000 messages |
| Night Owl | Session between midnight and 5 AM |
| Early Bird | Session before 7 AM |
| On Fire | 7-day streak |
| Polyglot | Work in 5 different projects |

</details>

<details>
<summary><strong>Uncommon</strong> (5)</summary>

| Achievement | Condition |
|-------------|-----------|
| Veteran | Complete 500 sessions |
| Ten Thousand Voices | Send 10,000 messages |
| Globetrotter | Work in 20 different projects |
| Weekend Warrior | 10 sessions on weekends |
| Bash Master | Execute 1,000 Bash commands |

</details>

<details>
<summary><strong>Rare</strong> (8)</summary>

| Achievement | Condition |
|-------------|-----------|
| Centurion | Complete 100 sessions |
| Tool Master | 10,000 tool calls |
| Marathon Runner | 100+ message session |
| Iron Will | 30-day streak |
| The Legend | Complete 1,000 sessions |
| Code Surgeon | 50,000 tool calls |
| Ultramarathon | 500+ message session |
| On a Roll | 14-day streak |

</details>

<details>
<summary><strong>Epic</strong> (4)</summary>

| Achievement | Condition |
|-------------|-----------|
| Zero Defect | Reach 50,000 total XP |
| The Inception | Spawn 100 subagent tasks |
| Night Shift | 50 sessions between midnight and 5 AM |
| Century Streak | 100-day streak |

</details>

<details>
<summary><strong>Legendary</strong> (2)</summary>

| Achievement | Condition |
|-------------|-----------|
| Omega Grind | Reach 200,000 total XP |
| World Builder | Work in 50 different projects |

</details>

## Prestige

Reached Level 50? You can **prestige** — reset your level and earn a permanent star badge (★). Your total XP is preserved, and each prestige unlocks another star.

```bash
claude-rank prestige
```

## Badge

Generate an SVG badge showing your current rank:

```bash
claude-rank badge --output claude-rank-badge.svg
```

Then embed it in your GitHub README:

```markdown
![Claude Rank](claude-rank-badge.svg)
```

## How It Works

claude-rank reads Claude Code's local data files:

- `~/.claude/stats-cache.json` — Sessions, messages, tool calls, hourly activity
- `~/.claude/history.jsonl` — Conversation history with timestamps and projects
- `~/.claude/projects/*/` — Session-level tool usage data

All data stays local. Nothing is sent anywhere.

### Plugin Architecture

```
claude-rank/
├── .claude-plugin/
│   ├── plugin.json         # Plugin manifest
│   └── marketplace.json    # Marketplace catalog
├── hooks/
│   ├── hooks.json          # Hook definitions (SessionStart + PostToolUse)
│   ├── bootstrap.sh        # Auto-creates venv and installs deps
│   ├── session-start.sh    # Injects rank into Claude's context
│   └── post-tool-use.py    # Tracks XP after each tool call
├── skills/
│   ├── rank/SKILL.md       # /rank command
│   ├── achievements/SKILL.md
│   ├── wrapped/SKILL.md
│   └── badge/SKILL.md
├── .mcp.json               # MCP server registration
└── src/claude_rank/        # Core Python package
    ├── cli.py              # CLI entry point
    ├── mcp_server.py       # FastMCP server with 4 tools
    ├── levels.py           # XP/level/tier/prestige calculations
    ├── achievements.py     # 25 achievement definitions
    ├── badge.py            # SVG badge generation
    ├── wrapped.py          # Period stats aggregation
    ├── database.py         # SQLite storage (WAL mode)
    ├── parser.py           # ~/.claude/ data parser
    └── display.py          # Rich terminal output
```

## CLI Reference

```bash
claude-rank              # Dashboard (default)
claude-rank sync         # Full sync from Claude Code data
claude-rank stats        # Detailed statistics
claude-rank achievements # All achievements with progress
claude-rank prestige     # Prestige (reset level, earn star)
claude-rank badge        # Generate SVG badge
claude-rank wrapped      # Stats summary (--period month|year|all-time)
```

## Development

```bash
git clone https://github.com/filipores/claude-rank.git
cd claude-rank
pip install -e ".[dev]"

# Run tests (315 tests)
python3 -m pytest tests/ -v

# Lint
python3 -m ruff check src/ tests/
```

## Roadmap

- [x] XP system with 50 levels and 10 tiers
- [x] 25 achievements across 5 rarity tiers
- [x] Streak tracking with freezes
- [x] Auto-sync via PostToolUse hook
- [x] MCP server (Claude queries your stats mid-conversation)
- [x] Prestige system with star badges
- [x] GitHub README badge (SVG)
- [x] Claude Code Wrapped (monthly/yearly stats)
- [x] Claude Code Plugin with zero-config install
- [ ] Team leaderboards (opt-in competitive rankings)
- [ ] Seasonal events (quarterly themes with bonus XP)
- [ ] PyPI publishing

## License

MIT
