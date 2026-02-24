"""Tests for the leaderboard module."""
import json
from pathlib import Path

import pytest

from claude_rank.leaderboard import (
    LEADERBOARD_FILE_SUFFIX,
    LEADERBOARD_SCHEMA_VERSION,
    build_entry,
    default_export_path,
    load_all_entries,
    rank_entries,
    read_entry,
    write_entry,
)


def _make_profile(**overrides):
    """Create a minimal valid profile dict."""
    base = {
        "leaderboard_username": "testuser",
        "total_xp": "5000",
        "level": "10",
        "tier_name": "Silver",
        "tier_color": "silver",
        "current_streak": "5",
        "longest_streak": "14",
        "prestige_count": "0",
    }
    base.update(overrides)
    return base


class TestBuildEntry:
    def test_builds_valid_entry(self):
        entry = build_entry(_make_profile(), achievements_count=8)
        assert entry["schema_version"] == LEADERBOARD_SCHEMA_VERSION
        assert entry["username"] == "testuser"
        assert entry["level"] == 10
        assert entry["tier"] == "Silver"
        assert entry["tier_color"] == "silver"
        assert entry["total_xp"] == 5000
        assert entry["current_streak"] == 5
        assert entry["longest_streak"] == 14
        assert entry["achievements_count"] == 8
        assert entry["prestige_count"] == 0
        assert "last_updated" in entry

    def test_raises_without_username(self):
        profile = _make_profile()
        del profile["leaderboard_username"]
        with pytest.raises(ValueError, match="No username"):
            build_entry(profile, achievements_count=0)

    def test_empty_username_raises(self):
        with pytest.raises(ValueError):
            build_entry(_make_profile(leaderboard_username=""), achievements_count=0)

    def test_defaults_for_missing_keys(self):
        profile = {"leaderboard_username": "alice"}
        entry = build_entry(profile, achievements_count=0)
        assert entry["level"] == 1
        assert entry["total_xp"] == 0
        assert entry["tier"] == "Bronze"


class TestWriteEntry:
    def test_creates_file(self, tmp_path):
        path = tmp_path / "test.leaderboard.json"
        entry = {"schema_version": 1, "username": "alice", "total_xp": 100}
        write_entry(entry, path)
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["username"] == "alice"

    def test_creates_parent_dirs(self, tmp_path):
        path = tmp_path / "sub" / "dir" / "test.leaderboard.json"
        write_entry({"schema_version": 1, "username": "bob", "total_xp": 0}, path)
        assert path.exists()

    def test_overwrites_existing(self, tmp_path):
        path = tmp_path / "test.leaderboard.json"
        write_entry({"schema_version": 1, "username": "v1", "total_xp": 0}, path)
        write_entry({"schema_version": 1, "username": "v2", "total_xp": 0}, path)
        data = json.loads(path.read_text())
        assert data["username"] == "v2"


class TestReadEntry:
    def test_reads_valid_file(self, tmp_path):
        path = tmp_path / "test.leaderboard.json"
        entry = {"schema_version": 1, "username": "alice", "total_xp": 500}
        path.write_text(json.dumps(entry))
        result = read_entry(path)
        assert result["username"] == "alice"

    def test_missing_file_returns_none(self, tmp_path):
        assert read_entry(tmp_path / "nope.json") is None

    def test_bad_json_returns_none(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("not json")
        assert read_entry(path) is None

    def test_wrong_schema_version_returns_none(self, tmp_path):
        path = tmp_path / "old.json"
        path.write_text(json.dumps({"schema_version": 999, "username": "x", "total_xp": 0}))
        assert read_entry(path) is None

    def test_missing_required_fields_returns_none(self, tmp_path):
        path = tmp_path / "incomplete.json"
        path.write_text(json.dumps({"schema_version": 1}))
        assert read_entry(path) is None

    def test_non_dict_returns_none(self, tmp_path):
        path = tmp_path / "array.json"
        path.write_text(json.dumps([1, 2, 3]))
        assert read_entry(path) is None


class TestLoadAllEntries:
    def test_loads_multiple_entries(self, tmp_path):
        for name in ["alice", "bob", "charlie"]:
            path = tmp_path / f"{name}.leaderboard.json"
            path.write_text(json.dumps({"schema_version": 1, "username": name, "total_xp": 100}))
        entries = load_all_entries(tmp_path)
        assert len(entries) == 3

    def test_skips_invalid_files(self, tmp_path):
        (tmp_path / "good.leaderboard.json").write_text(
            json.dumps({"schema_version": 1, "username": "good", "total_xp": 100})
        )
        (tmp_path / "bad.leaderboard.json").write_text("not json")
        entries = load_all_entries(tmp_path)
        assert len(entries) == 1

    def test_empty_directory(self, tmp_path):
        assert load_all_entries(tmp_path) == []

    def test_nonexistent_directory(self, tmp_path):
        assert load_all_entries(tmp_path / "nope") == []

    def test_ignores_non_leaderboard_json(self, tmp_path):
        (tmp_path / "other.json").write_text(json.dumps({"data": True}))
        (tmp_path / "test.leaderboard.json").write_text(
            json.dumps({"schema_version": 1, "username": "test", "total_xp": 0})
        )
        entries = load_all_entries(tmp_path)
        assert len(entries) == 1


class TestRankEntries:
    def test_ranks_by_xp_descending(self):
        entries = [
            {"username": "low", "total_xp": 100, "longest_streak": 0, "achievements_count": 0},
            {"username": "high", "total_xp": 999, "longest_streak": 0, "achievements_count": 0},
            {"username": "mid", "total_xp": 500, "longest_streak": 0, "achievements_count": 0},
        ]
        ranked = rank_entries(entries)
        assert ranked[0]["username"] == "high"
        assert ranked[0]["rank"] == 1
        assert ranked[1]["username"] == "mid"
        assert ranked[1]["rank"] == 2
        assert ranked[2]["username"] == "low"
        assert ranked[2]["rank"] == 3

    def test_tiebreak_by_longest_streak(self):
        entries = [
            {"username": "a", "total_xp": 100, "longest_streak": 5, "achievements_count": 0},
            {"username": "b", "total_xp": 100, "longest_streak": 10, "achievements_count": 0},
        ]
        ranked = rank_entries(entries)
        assert ranked[0]["username"] == "b"

    def test_tiebreak_by_achievements(self):
        entries = [
            {"username": "a", "total_xp": 100, "longest_streak": 5, "achievements_count": 3},
            {"username": "b", "total_xp": 100, "longest_streak": 5, "achievements_count": 10},
        ]
        ranked = rank_entries(entries)
        assert ranked[0]["username"] == "b"

    def test_empty_list(self):
        assert rank_entries([]) == []

    def test_single_entry(self):
        entries = [{"username": "solo", "total_xp": 42, "longest_streak": 0, "achievements_count": 0}]
        ranked = rank_entries(entries)
        assert ranked[0]["rank"] == 1


class TestDefaultExportPath:
    def test_constructs_correct_path(self):
        result = default_export_path("alice", Path("/shared/lb"))
        assert result == Path("/shared/lb/alice.leaderboard.json")
