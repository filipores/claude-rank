"""Tests for claude_rank.parser."""

import json
import os
import time
from pathlib import Path

import pytest

from claude_rank.parser import ClaudeDataParser

# -- Mock Data ----------------------------------------------------------------

MOCK_STATS_CACHE = {
    "totalSessions": 50,
    "totalMessages": 1200,
    "firstSessionDate": "2026-01-15",
    "longestSession": {"messageCount": 150, "duration": 3600000},
    "hourCounts": [0] * 6 + [10, 20, 30, 50, 40, 35, 25, 30, 40, 50, 30, 20, 15, 10, 5, 2, 0, 0],
    "dailyActivity": [
        {"date": "2026-01-15", "messageCount": 100, "sessionCount": 3, "toolCallCount": 250},
        {"date": "2026-01-16", "messageCount": 80, "sessionCount": 2, "toolCallCount": 180},
        {"date": "2026-01-17", "messageCount": 0, "sessionCount": 0, "toolCallCount": 0},
    ],
    "dailyModelTokens": [
        {"date": "2026-01-15", "tokensByModel": {"claude-opus-4-6": 50000}},
    ],
    "modelUsage": {
        "claude-opus-4-6": {"inputTokens": 100000, "outputTokens": 50000},
        "claude-sonnet-4-6": {"inputTokens": 20000, "outputTokens": 10000},
    },
}

MOCK_HISTORY_LINES = [
    '{"display": "fix the bug", "timestamp": "2026-01-15T10:00:00Z", "project": "/Users/test/project-a", "sessionId": "sess-1"}',
    '{"display": "add feature", "timestamp": "2026-01-16T14:00:00Z", "project": "/Users/test/project-b", "sessionId": "sess-2"}',
    '{"display": "refactor code", "timestamp": "2026-01-17T09:00:00Z", "project": "/Users/test/project-a", "sessionId": "sess-3"}',
]

MOCK_SESSION_LINES = [
    json.dumps(
        {
            "type": "human",
            "message": {"content": "fix the bug"},
        }
    ),
    json.dumps(
        {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "tool_use", "name": "Read", "input": {"file_path": "/foo/bar.py"}},
                ]
            },
        }
    ),
    json.dumps(
        {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "tool_use", "name": "Edit", "input": {}},
                    {"type": "tool_use", "name": "Read", "input": {}},
                    {"type": "text", "text": "Done!"},
                ]
            },
        }
    ),
    json.dumps(
        {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "tool_use", "name": "Bash", "input": {}},
                ]
            },
        }
    ),
]


# -- Fixtures -----------------------------------------------------------------


@pytest.fixture
def mock_claude_dir(tmp_path: Path) -> Path:
    """Create a mock ~/.claude/ directory with test data."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()

    # stats-cache.json
    (claude_dir / "stats-cache.json").write_text(json.dumps(MOCK_STATS_CACHE), encoding="utf-8")

    # history.jsonl
    (claude_dir / "history.jsonl").write_text("\n".join(MOCK_HISTORY_LINES) + "\n", encoding="utf-8")

    return claude_dir


@pytest.fixture
def mock_claude_dir_with_sessions(mock_claude_dir: Path) -> Path:
    """Extend mock dir with session JSONL files."""
    projects_dir = mock_claude_dir / "projects"
    project_hash = projects_dir / "abc123"
    project_hash.mkdir(parents=True)

    session_file = project_hash / "sess-1.jsonl"
    session_file.write_text("\n".join(MOCK_SESSION_LINES) + "\n", encoding="utf-8")

    return mock_claude_dir


@pytest.fixture
def parser(mock_claude_dir: Path) -> ClaudeDataParser:
    return ClaudeDataParser(claude_dir=mock_claude_dir)


@pytest.fixture
def parser_with_sessions(mock_claude_dir_with_sessions: Path) -> ClaudeDataParser:
    return ClaudeDataParser(claude_dir=mock_claude_dir_with_sessions)


# -- parse_stats_cache --------------------------------------------------------


class TestParseStatsCache:
    def test_valid_data(self, parser: ClaudeDataParser) -> None:
        stats = parser.parse_stats_cache()
        assert stats is not None
        assert stats.total_sessions == 50
        assert stats.total_messages == 1200
        assert stats.first_session_date == "2026-01-15"
        assert stats.longest_session_messages == 150

    def test_hour_counts(self, parser: ClaudeDataParser) -> None:
        stats = parser.parse_stats_cache()
        assert stats is not None
        assert len(stats.hour_counts) == 24
        assert stats.hour_counts[6] == 10
        assert stats.hour_counts[9] == 50
        assert stats.hour_counts[0] == 0

    def test_daily_activity(self, parser: ClaudeDataParser) -> None:
        stats = parser.parse_stats_cache()
        assert stats is not None
        assert len(stats.daily_activity) == 3
        day1 = stats.daily_activity[0]
        assert day1.date == "2026-01-15"
        assert day1.message_count == 100
        assert day1.session_count == 3
        assert day1.tool_call_count == 250

    def test_model_usage(self, parser: ClaudeDataParser) -> None:
        stats = parser.parse_stats_cache()
        assert stats is not None
        assert stats.model_usage["claude-opus-4-6"] == 150000  # 100k + 50k
        assert stats.model_usage["claude-sonnet-4-6"] == 30000  # 20k + 10k

    def test_projects_from_history(self, parser: ClaudeDataParser) -> None:
        stats = parser.parse_stats_cache()
        assert stats is not None
        assert "/Users/test/project-a" in stats.projects
        assert "/Users/test/project-b" in stats.projects
        assert len(stats.projects) == 2

    def test_missing_file(self, tmp_path: Path) -> None:
        parser = ClaudeDataParser(claude_dir=tmp_path / "nonexistent")
        stats = parser.parse_stats_cache()
        assert stats is None

    def test_malformed_json(self, tmp_path: Path) -> None:
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / "stats-cache.json").write_text("not valid json{{{", encoding="utf-8")
        parser = ClaudeDataParser(claude_dir=claude_dir)
        stats = parser.parse_stats_cache()
        assert stats is None

    def test_partial_data(self, tmp_path: Path) -> None:
        """Stats cache with only some fields should still parse."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        partial = {"totalSessions": 10}
        (claude_dir / "stats-cache.json").write_text(json.dumps(partial), encoding="utf-8")
        (claude_dir / "history.jsonl").write_text("", encoding="utf-8")
        parser = ClaudeDataParser(claude_dir=claude_dir)
        stats = parser.parse_stats_cache()
        assert stats is not None
        assert stats.total_sessions == 10
        assert stats.total_messages == 0
        assert stats.first_session_date is None
        assert stats.longest_session_messages == 0
        assert len(stats.hour_counts) == 24
        assert all(h == 0 for h in stats.hour_counts)
        assert stats.daily_activity == []
        assert stats.model_usage == {}

    def test_hour_counts_short_array(self, tmp_path: Path) -> None:
        """hourCounts with fewer than 24 entries should be padded."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        data = {"hourCounts": [1, 2, 3]}
        (claude_dir / "stats-cache.json").write_text(json.dumps(data), encoding="utf-8")
        (claude_dir / "history.jsonl").write_text("", encoding="utf-8")
        parser = ClaudeDataParser(claude_dir=claude_dir)
        stats = parser.parse_stats_cache()
        assert stats is not None
        assert stats.hour_counts[:3] == [1, 2, 3]
        assert stats.hour_counts[3:] == [0] * 21


# -- parse_history ------------------------------------------------------------


class TestParseHistory:
    def test_valid_data(self, parser: ClaudeDataParser) -> None:
        history = parser.parse_history()
        assert len(history) == 3
        assert history[0]["display"] == "fix the bug"
        assert history[1]["project"] == "/Users/test/project-b"
        assert history[2]["sessionId"] == "sess-3"

    def test_missing_file(self, tmp_path: Path) -> None:
        parser = ClaudeDataParser(claude_dir=tmp_path / "nonexistent")
        history = parser.parse_history()
        assert history == []

    def test_malformed_lines_skipped(self, tmp_path: Path) -> None:
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        lines = [
            '{"display": "valid entry", "timestamp": "2026-01-15T10:00:00Z"}',
            "this is not json",
            "",
            '{"display": "another valid", "timestamp": "2026-01-16T10:00:00Z"}',
            "{broken json",
        ]
        (claude_dir / "history.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
        parser = ClaudeDataParser(claude_dir=claude_dir)
        history = parser.parse_history()
        assert len(history) == 2
        assert history[0]["display"] == "valid entry"
        assert history[1]["display"] == "another valid"

    def test_empty_file(self, tmp_path: Path) -> None:
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / "history.jsonl").write_text("", encoding="utf-8")
        parser = ClaudeDataParser(claude_dir=claude_dir)
        history = parser.parse_history()
        assert history == []


# -- get_unique_projects ------------------------------------------------------


class TestGetUniqueProjects:
    def test_returns_unique(self, parser: ClaudeDataParser) -> None:
        projects = parser.get_unique_projects()
        assert len(projects) == 2
        assert "/Users/test/project-a" in projects
        assert "/Users/test/project-b" in projects

    def test_preserves_order(self, parser: ClaudeDataParser) -> None:
        projects = parser.get_unique_projects()
        assert projects[0] == "/Users/test/project-a"
        assert projects[1] == "/Users/test/project-b"

    def test_empty_history(self, tmp_path: Path) -> None:
        parser = ClaudeDataParser(claude_dir=tmp_path / "nonexistent")
        projects = parser.get_unique_projects()
        assert projects == []

    def test_entries_without_project(self, tmp_path: Path) -> None:
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        lines = [
            '{"display": "no project field", "timestamp": "2026-01-15T10:00:00Z"}',
            '{"display": "has project", "timestamp": "2026-01-16T10:00:00Z", "project": "/foo/bar"}',
        ]
        (claude_dir / "history.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
        parser = ClaudeDataParser(claude_dir=claude_dir)
        projects = parser.get_unique_projects()
        assert projects == ["/foo/bar"]


# -- get_active_dates ---------------------------------------------------------


class TestGetActiveDates:
    def test_returns_active_dates(self, parser: ClaudeDataParser) -> None:
        dates = parser.get_active_dates()
        assert "2026-01-15" in dates
        assert "2026-01-16" in dates
        # 2026-01-17 has sessionCount=0, should be excluded
        assert "2026-01-17" not in dates

    def test_missing_stats(self, tmp_path: Path) -> None:
        parser = ClaudeDataParser(claude_dir=tmp_path / "nonexistent")
        dates = parser.get_active_dates()
        assert dates == set()


# -- get_tool_usage_summary ---------------------------------------------------


class TestGetToolUsageSummary:
    def test_parses_tool_calls(self, parser_with_sessions: ClaudeDataParser) -> None:
        summary = parser_with_sessions.get_tool_usage_summary()
        assert summary["Read"] == 2
        assert summary["Edit"] == 1
        assert summary["Bash"] == 1

    def test_no_projects_dir(self, tmp_path: Path) -> None:
        parser = ClaudeDataParser(claude_dir=tmp_path / "nonexistent")
        summary = parser.get_tool_usage_summary()
        assert summary == {}

    def test_skips_old_sessions(self, tmp_path: Path) -> None:
        """Session files older than 30 days should be skipped."""
        claude_dir = tmp_path / ".claude"
        projects_dir = claude_dir / "projects" / "old-project"
        projects_dir.mkdir(parents=True)

        session_file = projects_dir / "old-session.jsonl"
        session_file.write_text(
            json.dumps(
                {
                    "type": "assistant",
                    "message": {"content": [{"type": "tool_use", "name": "Read", "input": {}}]},
                }
            )
            + "\n",
            encoding="utf-8",
        )

        # Set modification time to 60 days ago
        old_time = time.time() - (60 * 86400)
        os.utime(session_file, (old_time, old_time))

        parser = ClaudeDataParser(claude_dir=claude_dir)
        summary = parser.get_tool_usage_summary()
        assert summary == {}

    def test_handles_malformed_session_lines(self, tmp_path: Path) -> None:
        claude_dir = tmp_path / ".claude"
        projects_dir = claude_dir / "projects" / "proj"
        projects_dir.mkdir(parents=True)

        lines = [
            "not json at all",
            json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Grep", "input": {}}]}}),
            "{broken json",
            json.dumps({"type": "human", "message": {"content": "ignored"}}),
        ]
        session_file = projects_dir / "sess.jsonl"
        session_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

        parser = ClaudeDataParser(claude_dir=claude_dir)
        summary = parser.get_tool_usage_summary()
        assert summary == {"Grep": 1}

    def test_ignores_non_tool_use_blocks(self, tmp_path: Path) -> None:
        claude_dir = tmp_path / ".claude"
        projects_dir = claude_dir / "projects" / "proj"
        projects_dir.mkdir(parents=True)

        session_file = projects_dir / "sess.jsonl"
        session_file.write_text(
            json.dumps(
                {
                    "type": "assistant",
                    "message": {
                        "content": [
                            {"type": "text", "text": "Here is the result"},
                            {"type": "tool_use", "name": "Write", "input": {}},
                            {"type": "tool_result", "content": "ok"},
                        ]
                    },
                }
            )
            + "\n",
            encoding="utf-8",
        )

        parser = ClaudeDataParser(claude_dir=claude_dir)
        summary = parser.get_tool_usage_summary()
        assert summary == {"Write": 1}
