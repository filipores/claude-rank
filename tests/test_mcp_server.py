"""Tests for the MCP server tool functions."""
from unittest.mock import MagicMock, patch

from claude_rank.mcp_server import get_achievements, get_badge, get_leaderboard, get_rank, get_wrapped


class TestGetRank:
    @patch("claude_rank.mcp_server.Path")
    def test_reads_rank_json_if_exists(self, mock_path):
        mock_file = MagicMock()
        mock_file.exists.return_value = True
        mock_file.read_text.return_value = '{"level": 10, "title": "Silver"}'
        mock_path.home.return_value / ".claude" / "rank.json"  # noqa: B018
        mock_path.home.return_value.__truediv__.return_value.__truediv__.return_value = mock_file
        result = get_rank()
        assert result["level"] == 10
        assert result["title"] == "Silver"

    @patch("claude_rank.mcp_server._get_db")
    @patch("claude_rank.mcp_server.Path")
    def test_falls_back_to_db(self, mock_path, mock_get_db):
        mock_file = MagicMock()
        mock_file.exists.return_value = False
        mock_path.home.return_value.__truediv__.return_value.__truediv__.return_value = mock_file
        mock_db = MagicMock()
        mock_db.get_all_profile.return_value = {
            "total_xp": "5000", "level": "10", "prestige_count": "0",
            "current_streak": "3", "longest_streak": "7", "freeze_count": "1",
        }
        mock_get_db.return_value = mock_db
        result = get_rank()
        assert result["level"] == 10
        assert result["total_xp"] == 5000
        assert result["current_streak"] == 3
        mock_db.close.assert_called_once()

    @patch("claude_rank.mcp_server._get_db")
    @patch("claude_rank.mcp_server.Path")
    def test_no_data_returns_error(self, mock_path, mock_get_db):
        mock_file = MagicMock()
        mock_file.exists.return_value = False
        mock_path.home.return_value.__truediv__.return_value.__truediv__.return_value = mock_file
        mock_db = MagicMock()
        mock_db.get_all_profile.return_value = {}
        mock_get_db.return_value = mock_db
        result = get_rank()
        assert "error" in result


class TestGetAchievements:
    @patch("claude_rank.mcp_server._get_db")
    def test_returns_all_achievements(self, mock_get_db):
        mock_db = MagicMock()
        mock_db.get_all_achievements.return_value = []
        mock_get_db.return_value = mock_db
        result = get_achievements()
        assert "achievements" in result
        assert "total_count" in result
        assert "unlocked_count" in result
        assert result["unlocked_count"] == 0
        assert result["total_count"] > 0
        mock_db.close.assert_called_once()

    @patch("claude_rank.mcp_server._get_db")
    def test_unlocked_achievement_counted(self, mock_get_db):
        mock_db = MagicMock()
        mock_db.get_all_achievements.return_value = [
            {"id": "hello_world", "name": "Hello, World", "unlocked_at": "2026-01-01", "progress": 1.0},
        ]
        mock_get_db.return_value = mock_db
        result = get_achievements()
        assert result["unlocked_count"] == 1
        hw = next(a for a in result["achievements"] if a["id"] == "hello_world")
        assert hw["unlocked"] is True
        assert hw["progress_pct"] == 100

    @patch("claude_rank.mcp_server._get_db")
    def test_achievement_structure(self, mock_get_db):
        mock_db = MagicMock()
        mock_db.get_all_achievements.return_value = []
        mock_get_db.return_value = mock_db
        result = get_achievements()
        ach = result["achievements"][0]
        assert "id" in ach
        assert "name" in ach
        assert "description" in ach
        assert "rarity" in ach
        assert "progress" in ach
        assert "progress_pct" in ach
        assert "target" in ach
        assert "unlocked" in ach


class TestGetWrapped:
    def test_invalid_period(self):
        result = get_wrapped(period="invalid")
        assert "error" in result

    @patch("claude_rank.mcp_server._get_db")
    def test_no_data_returns_error(self, mock_get_db):
        mock_db = MagicMock()
        mock_db.get_all_profile.return_value = {}
        mock_get_db.return_value = mock_db
        result = get_wrapped(period="month")
        assert "error" in result
        mock_db.close.assert_called_once()

    def test_all_valid_periods_accepted(self):
        for period in ("month", "year", "all-time"):
            # Each valid period should not return "Invalid period" error
            result = get_wrapped(period=period)
            if "error" in result:
                assert "Invalid period" not in result["error"]


class TestGetBadge:
    @patch("claude_rank.mcp_server._get_db")
    def test_returns_svg(self, mock_get_db):
        mock_db = MagicMock()
        mock_db.get_all_profile.return_value = {
            "total_xp": "5000", "level": "10",
            "tier_name": "Silver", "tier_color": "silver",
            "prestige_count": "0",
        }
        mock_get_db.return_value = mock_db
        result = get_badge()
        assert "svg" in result
        assert "<svg" in result["svg"]
        assert result["level"] == 10
        assert result["tier_name"] == "Silver"
        assert result["total_xp"] == 5000
        assert "markdown" in result
        mock_db.close.assert_called_once()

    @patch("claude_rank.mcp_server._get_db")
    def test_no_data_returns_error(self, mock_get_db):
        mock_db = MagicMock()
        mock_db.get_all_profile.return_value = {}
        mock_get_db.return_value = mock_db
        result = get_badge()
        assert "error" in result
        mock_db.close.assert_called_once()


class TestGetLeaderboard:
    def test_no_directory_configured(self):
        """When no directory is set and none provided, returns error."""
        with patch("claude_rank.mcp_server._get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.get_profile.return_value = None
            mock_get_db.return_value = mock_db
            # Also patch get_leaderboard_dir to return None
            with patch("claude_rank.leaderboard.load_all_entries", return_value=[]):
                with patch("claude_rank.config.get_leaderboard_dir", return_value=None):
                    result = get_leaderboard(directory="")
                    assert "error" in result

    def test_with_valid_directory(self, tmp_path):
        """When directory has entries, returns ranked list."""
        import json as json_mod
        # Create leaderboard entries
        entry1 = {"schema_version": 1, "username": "alice", "total_xp": 5000,
                   "longest_streak": 10, "achievements_count": 5}
        entry2 = {"schema_version": 1, "username": "bob", "total_xp": 3000,
                   "longest_streak": 5, "achievements_count": 3}
        (tmp_path / "alice.leaderboard.json").write_text(json_mod.dumps(entry1))
        (tmp_path / "bob.leaderboard.json").write_text(json_mod.dumps(entry2))

        with patch("claude_rank.mcp_server._get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.get_profile.return_value = "alice"
            mock_get_db.return_value = mock_db
            result = get_leaderboard(directory=str(tmp_path))
            assert result["count"] == 2
            assert result["entries"][0]["username"] == "alice"
            assert result["entries"][0]["rank"] == 1
            assert result["your_rank"] == 1
            mock_db.close.assert_called_once()

    def test_empty_directory(self, tmp_path):
        """Empty directory returns zero entries."""
        with patch("claude_rank.mcp_server._get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.get_profile.return_value = None
            mock_get_db.return_value = mock_db
            result = get_leaderboard(directory=str(tmp_path))
            assert result["count"] == 0
            assert result["entries"] == []
            assert result["your_rank"] is None
