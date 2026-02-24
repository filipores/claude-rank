"""Tests for CLI commands and display helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from claude_rank.cli import (
    _count_weekend_sessions,
    build_parser,
    do_achievements,
    do_dashboard,
    do_leaderboard_export,
    do_leaderboard_setup,
    do_leaderboard_show,
    do_sync,
    do_stats,
)
from claude_rank.db import Database
from claude_rank.display import format_number
from claude_rank.parser import ClaudeStats, DailyActivity


@pytest.fixture
def db(tmp_path):
    """Create a temporary database for testing."""
    db_path = tmp_path / "test.db"
    database = Database(db_path=db_path)
    yield database
    database.close()


# ── Argument Parsing ──────────────────────────────────────────────────────────


class TestArgumentParsing:
    def test_no_args_defaults_to_none_command(self):
        parser = build_parser()
        args = parser.parse_args([])
        assert args.command is None

    def test_dashboard_command(self):
        parser = build_parser()
        args = parser.parse_args(["dashboard"])
        assert args.command == "dashboard"

    def test_sync_command(self):
        parser = build_parser()
        args = parser.parse_args(["sync"])
        assert args.command == "sync"

    def test_stats_command(self):
        parser = build_parser()
        args = parser.parse_args(["stats"])
        assert args.command == "stats"

    def test_achievements_command(self):
        parser = build_parser()
        args = parser.parse_args(["achievements"])
        assert args.command == "achievements"

    def test_invalid_command_raises(self):
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["nonexistent"])


# ── format_number ─────────────────────────────────────────────────────────────


class TestFormatNumber:
    def test_small_number(self):
        assert format_number(42) == "42"

    def test_number_with_commas(self):
        assert format_number(1200) == "1,200"

    def test_number_9999(self):
        assert format_number(9999) == "9,999"

    def test_ten_thousand(self):
        assert format_number(10_000) == "10.0K"

    def test_large_k(self):
        assert format_number(421_543) == "421.5K"

    def test_million(self):
        assert format_number(1_234_567) == "1.2M"

    def test_large_million(self):
        assert format_number(123_456_789) == "123M"

    def test_zero(self):
        assert format_number(0) == "0"

    def test_exact_million(self):
        assert format_number(1_000_000) == "1.0M"

    def test_hundred_k(self):
        assert format_number(100_000) == "100.0K"


# ── do_sync ───────────────────────────────────────────────────────────────────


class TestDoSync:
    def _make_mock_stats(self) -> ClaudeStats:
        return ClaudeStats(
            total_sessions=50,
            total_messages=500,
            first_session_date="2025-01-01",
            longest_session_messages=42,
            hour_counts=[0] * 24,
            daily_activity=[
                DailyActivity(date="2025-01-01", message_count=100, session_count=5, tool_call_count=20),
                DailyActivity(date="2025-01-02", message_count=150, session_count=8, tool_call_count=30),
                DailyActivity(date="2025-01-03", message_count=250, session_count=10, tool_call_count=50),
            ],
            model_usage={"claude-opus-4-6": 10000},
            projects=["/home/user/project1"],
        )

    @patch("claude_rank.cli.ClaudeDataParser")
    def test_sync_stores_profile(self, mock_parser_cls, db):
        mock_parser = MagicMock()
        mock_parser.parse_stats_cache.return_value = self._make_mock_stats()
        mock_parser.get_tool_usage_summary.return_value = {"Bash": 10, "Read": 5}
        mock_parser_cls.return_value = mock_parser

        result = do_sync(db)

        assert result["days_synced"] == 3
        assert result["total_xp"] > 0
        assert result["level"] >= 1
        assert db.get_profile("total_xp") is not None
        assert db.get_profile("level") is not None
        assert db.get_profile("member_since") == "2025-01-01"

    @patch("claude_rank.cli.ClaudeDataParser")
    def test_sync_stores_daily_stats(self, mock_parser_cls, db):
        mock_parser = MagicMock()
        mock_parser.parse_stats_cache.return_value = self._make_mock_stats()
        mock_parser.get_tool_usage_summary.return_value = {"Bash": 10, "Read": 5}
        mock_parser_cls.return_value = mock_parser

        do_sync(db)

        day1 = db.get_daily_stats("2025-01-01")
        assert day1 is not None
        assert day1["messages"] == 100
        assert day1["sessions"] == 5

    @patch("claude_rank.cli.ClaudeDataParser")
    def test_sync_checks_achievements(self, mock_parser_cls, db):
        mock_parser = MagicMock()
        mock_parser.parse_stats_cache.return_value = self._make_mock_stats()
        mock_parser.get_tool_usage_summary.return_value = {"Bash": 10, "Read": 5}
        mock_parser_cls.return_value = mock_parser

        do_sync(db)

        # "hello_world" (1 session) should be unlocked with 50 total sessions
        ach = db.get_achievement("hello_world")
        assert ach is not None
        assert ach["unlocked_at"] is not None

    @patch("claude_rank.cli.ClaudeDataParser")
    def test_sync_returns_result_dict(self, mock_parser_cls, db):
        mock_parser = MagicMock()
        mock_parser.parse_stats_cache.return_value = self._make_mock_stats()
        mock_parser.get_tool_usage_summary.return_value = {"Bash": 10, "Read": 5}
        mock_parser_cls.return_value = mock_parser

        result = do_sync(db)

        assert "days_synced" in result
        assert "total_xp" in result
        assert "level" in result
        assert "tier_name" in result
        assert "total_achievements_unlocked" in result
        assert "new_achievements" in result

    @patch("claude_rank.cli.ClaudeDataParser")
    def test_sync_with_no_data(self, mock_parser_cls, db):
        mock_parser = MagicMock()
        mock_parser.parse_stats_cache.return_value = None
        mock_parser_cls.return_value = mock_parser

        result = do_sync(db)

        assert result["days_synced"] == 0
        assert result["total_xp"] == 0

    @patch("claude_rank.cli.ClaudeDataParser")
    def test_sync_idempotent(self, mock_parser_cls, db):
        """Running sync twice with same data should not duplicate."""
        mock_parser = MagicMock()
        mock_parser.parse_stats_cache.return_value = self._make_mock_stats()
        mock_parser.get_tool_usage_summary.return_value = {"Bash": 10, "Read": 5}
        mock_parser_cls.return_value = mock_parser

        result1 = do_sync(db)
        result2 = do_sync(db)

        assert result1["total_xp"] == result2["total_xp"]
        assert result1["level"] == result2["level"]


# ── do_dashboard ──────────────────────────────────────────────────────────────


class TestDoDashboard:
    def test_empty_db_shows_no_data(self, db, capsys):
        """Dashboard with no profile data should print no-data message."""
        do_dashboard(db)
        # Should not raise; function handles empty state

    def test_populated_db_shows_dashboard(self, db):
        """Dashboard with profile data should render without error."""
        db.set_profile("total_xp", "5000")
        db.set_profile("level", "5")
        db.set_profile("current_streak", "3")
        db.set_profile("longest_streak", "7")
        db.set_profile("freeze_count", "1")
        db.set_profile("total_sessions", "100")
        db.set_profile("total_messages", "1000")
        db.set_profile("total_tool_calls", "500")
        db.set_profile("member_since", "2025-01-01")

        # Should not raise
        do_dashboard(db)

    def test_dashboard_with_achievements(self, db):
        """Dashboard shows recent and closest achievements."""
        db.set_profile("total_xp", "5000")
        db.set_profile("level", "5")
        db.set_profile("current_streak", "3")
        db.set_profile("longest_streak", "7")
        db.set_profile("freeze_count", "1")
        db.set_profile("total_sessions", "100")
        db.set_profile("total_messages", "1000")
        db.set_profile("total_tool_calls", "500")
        db.set_profile("member_since", "2025-01-01")

        db.unlock_achievement("hello_world", "Hello, World", "2025-01-01")
        db.update_achievement_progress("centurion", "Centurion", 0.5)

        # Should not raise
        do_dashboard(db)


# ── do_stats ──────────────────────────────────────────────────────────────────


class TestDoStats:
    def test_empty_db_shows_no_data(self, db):
        """Stats with no profile data should handle gracefully."""
        do_stats(db)

    @patch("claude_rank.cli.ClaudeDataParser")
    def test_populated_stats(self, mock_parser_cls, db):
        """Stats with profile + parser data should render without error."""
        mock_parser = MagicMock()
        mock_parser.parse_stats_cache.return_value = ClaudeStats(
            total_sessions=100,
            total_messages=5000,
            first_session_date="2025-01-01",
            longest_session_messages=80,
            hour_counts=[0, 0, 0, 0, 0, 0, 0, 5, 10, 20, 15, 10, 8, 12, 9, 7, 5, 3, 2, 1, 0, 0, 0, 0],
            model_usage={"claude-opus-4-6": 50000},
            projects=["/project/a", "/project/b"],
        )
        mock_parser.get_tool_usage_summary.return_value = {"Read": 100, "Edit": 50}
        mock_parser_cls.return_value = mock_parser

        db.set_profile("total_xp", "5000")
        db.set_profile("level", "5")
        db.set_profile("total_sessions", "100")
        db.set_profile("total_messages", "5000")
        db.set_profile("total_tool_calls", "500")
        db.set_profile("current_streak", "3")
        db.set_profile("longest_streak", "7")

        # Should not raise
        do_stats(db)


# ── do_achievements ───────────────────────────────────────────────────────────


class TestDoAchievements:
    def test_empty_db(self, db):
        """Achievements with no data should show all locked."""
        do_achievements(db)

    def test_with_some_unlocked(self, db):
        """Achievements with some unlocked should render correctly."""
        db.unlock_achievement("hello_world", "Hello, World", "2025-01-01")
        db.update_achievement_progress("centurion", "Centurion", 0.42)
        db.update_achievement_progress("tool_master", "Tool Master", 0.85)

        # Should not raise
        do_achievements(db)


# ── _count_weekend_sessions ──────────────────────────────────────────────────


class TestCountWeekendSessions:
    def test_counts_saturday_and_sunday(self):
        """Saturday and Sunday sessions are counted."""
        activity = [
            DailyActivity(date="2025-01-04", message_count=10, session_count=2, tool_call_count=5),  # Saturday
            DailyActivity(date="2025-01-05", message_count=10, session_count=3, tool_call_count=5),  # Sunday
        ]
        assert _count_weekend_sessions(activity) == 5

    def test_ignores_weekdays(self):
        """Weekday sessions are not counted."""
        activity = [
            DailyActivity(date="2025-01-06", message_count=10, session_count=4, tool_call_count=5),  # Monday
            DailyActivity(date="2025-01-07", message_count=10, session_count=2, tool_call_count=5),  # Tuesday
            DailyActivity(date="2025-01-08", message_count=10, session_count=1, tool_call_count=5),  # Wednesday
        ]
        assert _count_weekend_sessions(activity) == 0

    def test_empty_list(self):
        """Empty activity list returns 0."""
        assert _count_weekend_sessions([]) == 0

    def test_mixed_weekday_and_weekend(self):
        """Only weekend sessions are counted from mixed input."""
        activity = [
            DailyActivity(date="2025-01-06", message_count=10, session_count=4, tool_call_count=5),  # Monday
            DailyActivity(date="2025-01-11", message_count=10, session_count=2, tool_call_count=5),  # Saturday
            DailyActivity(date="2025-01-12", message_count=10, session_count=1, tool_call_count=5),  # Sunday
        ]
        assert _count_weekend_sessions(activity) == 3
