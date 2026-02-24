---
name: leaderboard
description: Show team leaderboard rankings, export your stats, or set up leaderboard sharing.
---

Show the team leaderboard. If $ARGUMENTS contains "export", export your stats. If $ARGUMENTS contains "setup", configure your leaderboard username and directory.

Usage:
- `/leaderboard` — show team rankings
- `/leaderboard export` — export your stats to the shared directory
- `/leaderboard setup --username <name> --dir <path>` — configure leaderboard

Run the appropriate command:

If $ARGUMENTS is empty or "show":
!`claude-rank leaderboard show`

If $ARGUMENTS starts with "export":
!`claude-rank leaderboard export`

If $ARGUMENTS starts with "setup":
!`claude-rank leaderboard setup $ARGUMENTS`
