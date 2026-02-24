# claude-rank - Claude Code Usage Gamification

## Vision
Gamify Claude Code usage with XP, levels, achievements, and streaks.
All data local, privacy-first, opt-in everything.

## Architecture (MVP)

```
~/.claude/stats-cache.json  ──┐
~/.claude/history.jsonl     ──┤──→  claude-rank CLI  ──→  Terminal Output
~/.claude/projects/*/**.jsonl ─┘         │
                                         ▼
                                  ~/.claude-rank/
                                  ├── data.db (SQLite)
                                  └── config.json
```

## Tech Stack
- **Language**: Python 3.11+ (zero external deps for core, uv for running)
- **Storage**: SQLite (built-in sqlite3 module)
- **CLI**: argparse + rich (for colored terminal output)
- **Distribution**: pip install / uv tool install

## Data Sources (already available in ~/.claude/)

### stats-cache.json (Gold Mine)
- `totalSessions`, `totalMessages`
- `dailyActivity[]`: messageCount, sessionCount, toolCallCount per day
- `dailyModelTokens[]`: token usage by model per day
- `modelUsage{}`: cumulative input/output tokens by model
- `hourCounts[]`: usage by hour of day (0-23)
- `longestSession`: sessionId, duration, messageCount
- `firstSessionDate`

### history.jsonl
- Each line: `display` (prompt text), `timestamp`, `project`, `sessionId`

### Session JSONL files (~/.claude/projects/{id}/{session}.jsonl)
- Per-message: `type`, `model`, `usage` (tokens), tool_use blocks
- Tool names: Read, Edit, Write, Bash, Grep, Glob, Task, etc.

## XP System

### Base XP Values
| Action | XP | Source |
|--------|-----|--------|
| Session completed (>5 tool calls) | 10 | stats-cache |
| Message sent | 1 | stats-cache |
| Tool call made | 2 | stats-cache |
| Unique project worked on | 5 | history.jsonl |
| File edited (Write/Edit tool) | 3 | session JSONL |
| Commit created (Bash git commit) | 5 | session JSONL |
| Multi-agent session (Task tool) | 5 | session JSONL |

### Multipliers
| Condition | Factor |
|-----------|--------|
| First session of day | 1.5x |
| 7-day streak | 1.25x |
| 14-day streak | 1.5x |
| 30-day streak | 2.0x |

### Anti-Gaming
- Daily XP cap: 800 XP (before multipliers)
- Sessions with <5 tool calls earn no session XP
- Diminishing returns after 500 XP/day (50% rate)

## Level System (50 Levels, 10 Tiers)

### XP Curve
`XP_to_next_level(L) = floor(50 * L^1.8 + 100 * L)`

### Tiers
| Tier | Levels | Name | Color |
|------|--------|------|-------|
| 1 | 1-5 | Prompt Novice | Gray |
| 2 | 6-10 | Code Apprentice | Green |
| 3 | 11-15 | Bug Slayer | Blue |
| 4 | 16-20 | Context Master | Purple |
| 5 | 21-25 | Refactor Sage | Indigo |
| 6 | 26-30 | Pipeline Architect | Gold |
| 7 | 31-35 | Token Whisperer | Platinum |
| 8 | 36-40 | Neural Commander | Diamond |
| 9 | 41-45 | Singularity Vanguard | Prismatic |
| 10 | 46-50 | Omega Coder | Obsidian+Gold |

## Achievement System (MVP: 10 Achievements)

| # | Name | Condition | Rarity |
|---|------|-----------|--------|
| 1 | Hello, World | First session ever | Common |
| 2 | Centurion | 100 sessions | Rare |
| 3 | Thousand Voices | 1,000 messages | Common |
| 4 | Tool Master | 10,000 tool calls | Rare |
| 5 | Night Owl | Session between 0-5 AM | Common |
| 6 | Early Bird | Session before 7 AM | Common |
| 7 | On Fire | 7-day streak | Common |
| 8 | Iron Will | 30-day streak | Rare |
| 9 | Polyglot | Work in 5+ projects | Common |
| 10 | Marathon Runner | Single session >100 messages | Rare |

## Streak System
- Active day = at least 1 session with >5 tool calls
- Freeze: 1 earned per 7-day streak, max 3 stored, auto-activates
- Grace: Within 24h = full restore, within 48h = 25% reduction
- "Longest streak" permanently stored

## CLI Commands (MVP)

```bash
claude-rank              # Show dashboard (level, XP, streak, recent achievements)
claude-rank stats        # Detailed stats breakdown
claude-rank achievements # List all achievements with progress
claude-rank history      # XP history over time
claude-rank sync         # Re-parse Claude Code data and update DB
```

## File Structure

```
claude-rank/
├── CONCEPT.md              # This file
├── README.md               # Usage documentation
├── pyproject.toml           # Package config (uv/pip)
├── src/
│   └── claude_rank/
│       ├── __init__.py
│       ├── __main__.py      # Entry point (python -m claude_rank)
│       ├── cli.py           # CLI argument parsing + output formatting
│       ├── parser.py        # Parse ~/.claude/ data files
│       ├── xp.py            # XP calculation engine
│       ├── levels.py        # Level/tier progression logic
│       ├── achievements.py  # Achievement definitions + checking
│       ├── streaks.py       # Streak tracking + freeze logic
│       ├── db.py            # SQLite database management
│       └── display.py       # Rich terminal output formatting
├── tests/
│   ├── __init__.py
│   ├── test_parser.py
│   ├── test_xp.py
│   ├── test_levels.py
│   ├── test_achievements.py
│   ├── test_streaks.py
│   └── test_db.py
└── .gitignore
```
