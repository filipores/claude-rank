"""Parse Claude Code's local data files from ~/.claude/."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path


@dataclass
class DailyActivity:
    date: str  # YYYY-MM-DD
    message_count: int
    session_count: int
    tool_call_count: int


@dataclass
class SessionInfo:
    session_id: str
    project: str | None
    timestamp: str
    prompt_count: int
    tool_calls: dict[str, int] = field(default_factory=dict)
    total_tokens: int = 0


@dataclass
class ClaudeStats:
    total_sessions: int = 0
    total_messages: int = 0
    first_session_date: str | None = None
    longest_session_messages: int = 0
    hour_counts: list[int] = field(default_factory=lambda: [0] * 24)
    daily_activity: list[DailyActivity] = field(default_factory=list)
    model_usage: dict[str, int] = field(default_factory=dict)
    projects: list[str] = field(default_factory=list)


class ClaudeDataParser:
    def __init__(self, claude_dir: Path | None = None):
        self.claude_dir = claude_dir or Path.home() / ".claude"

    def parse_stats_cache(self) -> ClaudeStats | None:
        """Parse ~/.claude/stats-cache.json.

        Returns ClaudeStats with all available data, or None if the file
        doesn't exist or can't be parsed.
        """
        stats_path = self.claude_dir / "stats-cache.json"
        try:
            raw = json.loads(stats_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return None

        daily_activity = []
        for entry in raw.get("dailyActivity", []):
            daily_activity.append(
                DailyActivity(
                    date=entry.get("date", ""),
                    message_count=entry.get("messageCount", 0),
                    session_count=entry.get("sessionCount", 0),
                    tool_call_count=entry.get("toolCallCount", 0),
                )
            )

        # Aggregate model usage: sum inputTokens + outputTokens per model
        model_usage: dict[str, int] = {}
        for model_name, tokens in raw.get("modelUsage", {}).items():
            if isinstance(tokens, dict):
                total = tokens.get("inputTokens", 0) + tokens.get("outputTokens", 0)
                model_usage[model_name] = total
            elif isinstance(tokens, int):
                model_usage[model_name] = tokens

        # Get unique projects from dailyModelTokens or history
        projects = self.get_unique_projects()

        longest = raw.get("longestSession", {})
        hour_counts_raw = raw.get("hourCounts", [])
        # Handle both list and dict formats for hourCounts
        if isinstance(hour_counts_raw, dict):
            hour_counts = [hour_counts_raw.get(str(h), 0) for h in range(24)]
        elif isinstance(hour_counts_raw, list):
            hour_counts = (hour_counts_raw + [0] * 24)[:24]
        else:
            hour_counts = [0] * 24

        return ClaudeStats(
            total_sessions=raw.get("totalSessions", 0),
            total_messages=raw.get("totalMessages", 0),
            first_session_date=raw.get("firstSessionDate"),
            longest_session_messages=longest.get("messageCount", 0) if isinstance(longest, dict) else 0,
            hour_counts=hour_counts,
            daily_activity=daily_activity,
            model_usage=model_usage,
            projects=projects,
        )

    def parse_history(self) -> list[dict]:
        """Parse ~/.claude/history.jsonl.

        Each line is JSON with display, timestamp, project, sessionId.
        Returns list of parsed entries. Malformed lines are skipped.
        """
        history_path = self.claude_dir / "history.jsonl"
        entries: list[dict] = []
        try:
            text = history_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return entries

        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                entries.append(entry)
            except json.JSONDecodeError:
                continue

        return entries

    def get_unique_projects(self) -> list[str]:
        """Get unique project paths from history.jsonl."""
        history = self.parse_history()
        seen: set[str] = set()
        projects: list[str] = []
        for entry in history:
            project = entry.get("project")
            if project and project not in seen:
                seen.add(project)
                projects.append(project)
        return projects

    def get_active_dates(self) -> set[str]:
        """Get set of dates (YYYY-MM-DD) where user had activity.

        From dailyActivity in stats-cache.json where sessionCount > 0.
        """
        stats = self.parse_stats_cache()
        if stats is None:
            return set()
        return {da.date for da in stats.daily_activity if da.session_count > 0}

    def get_tool_usage_summary(self) -> dict[str, int]:
        """Parse session JSONL files to get aggregate tool usage.

        Session files are at: ~/.claude/projects/{project-hash}/{session-id}.jsonl
        Looks for assistant messages containing content blocks with type "tool_use".
        Only parses sessions from the last 30 days for performance.

        Returns: {"Read": 1234, "Edit": 567, "Bash": 890, ...}
        """
        tool_counts: dict[str, int] = {}
        projects_dir = self.claude_dir / "projects"
        if not projects_dir.is_dir():
            return tool_counts

        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=30)

        for project_dir in projects_dir.iterdir():
            if not project_dir.is_dir():
                continue
            for session_file in project_dir.glob("*.jsonl"):
                # Check file modification time for 30-day cutoff
                try:
                    mtime = datetime.fromtimestamp(session_file.stat().st_mtime, tz=timezone.utc)
                    if mtime < cutoff:
                        continue
                except OSError:
                    continue

                self._parse_session_file(session_file, tool_counts)

        return tool_counts

    def _parse_session_file(self, path: Path, tool_counts: dict[str, int]) -> None:
        """Parse a single session JSONL file for tool usage."""
        try:
            text = path.read_text(encoding="utf-8")
        except (FileNotFoundError, OSError):
            return

        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            if entry.get("type") != "assistant":
                continue

            message = entry.get("message", {})
            if not isinstance(message, dict):
                continue

            for block in message.get("content", []):
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    tool_name = block.get("name", "unknown")
                    tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1
