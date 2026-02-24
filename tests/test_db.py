"""Tests for the SQLite database layer."""

import pytest

from claude_rank.db import Database


@pytest.fixture
def db(tmp_path):
    """Create a temporary database for testing."""
    db_path = tmp_path / "test.db"
    database = Database(db_path=db_path)
    yield database
    database.close()


class TestDatabaseCreation:
    def test_creates_db_file(self, tmp_path):
        db_path = tmp_path / "sub" / "test.db"
        database = Database(db_path=db_path)
        assert db_path.exists()
        database.close()

    def test_creates_parent_directories(self, tmp_path):
        db_path = tmp_path / "a" / "b" / "test.db"
        database = Database(db_path=db_path)
        assert db_path.parent.exists()
        database.close()

    def test_tables_exist(self, db):
        cursor = db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = sorted(row["name"] for row in cursor.fetchall())
        assert "achievements" in tables
        assert "daily_stats" in tables
        assert "profile" in tables

    def test_wal_mode_enabled(self, db):
        result = db.conn.execute("PRAGMA journal_mode").fetchone()
        assert result[0] == "wal"


class TestProfile:
    def test_get_nonexistent_key(self, db):
        assert db.get_profile("nonexistent") is None

    def test_set_and_get(self, db):
        db.set_profile("total_xp", "500")
        assert db.get_profile("total_xp") == "500"

    def test_upsert_overwrites(self, db):
        db.set_profile("level", "3")
        db.set_profile("level", "5")
        assert db.get_profile("level") == "5"

    def test_get_all_profile_empty(self, db):
        assert db.get_all_profile() == {}

    def test_get_all_profile(self, db):
        db.set_profile("total_xp", "1000")
        db.set_profile("level", "7")
        db.set_profile("tier", "2")
        result = db.get_all_profile()
        assert result == {"total_xp": "1000", "level": "7", "tier": "2"}

    def test_set_profile_converts_to_string(self, db):
        db.set_profile("total_xp", 500)
        assert db.get_profile("total_xp") == "500"


class TestDailyStats:
    def test_get_nonexistent_date(self, db):
        assert db.get_daily_stats("2026-01-01") is None

    def test_upsert_insert(self, db):
        db.upsert_daily_stats("2026-01-15", total_xp=200, messages=50)
        stats = db.get_daily_stats("2026-01-15")
        assert stats is not None
        assert stats["total_xp"] == 200
        assert stats["messages"] == 50
        assert stats["sessions"] == 0
        assert stats["tool_calls"] == 0

    def test_upsert_update(self, db):
        db.upsert_daily_stats("2026-01-15", total_xp=200, messages=50)
        db.upsert_daily_stats("2026-01-15", total_xp=350, messages=80)
        stats = db.get_daily_stats("2026-01-15")
        assert stats["total_xp"] == 350
        assert stats["messages"] == 80

    def test_upsert_partial_update(self, db):
        db.upsert_daily_stats("2026-01-15", total_xp=200, messages=50, sessions=3)
        db.upsert_daily_stats("2026-01-15", total_xp=350)
        stats = db.get_daily_stats("2026-01-15")
        assert stats["total_xp"] == 350
        assert stats["messages"] == 50
        assert stats["sessions"] == 3

    def test_streak_day_flag(self, db):
        db.upsert_daily_stats("2026-01-15", streak_day=True)
        stats = db.get_daily_stats("2026-01-15")
        assert stats["streak_day"] == 1

    def test_date_range_empty(self, db):
        result = db.get_daily_stats_range("2026-01-01", "2026-01-31")
        assert result == []

    def test_date_range(self, db):
        db.upsert_daily_stats("2026-01-10", total_xp=100)
        db.upsert_daily_stats("2026-01-15", total_xp=200)
        db.upsert_daily_stats("2026-01-20", total_xp=300)
        db.upsert_daily_stats("2026-02-01", total_xp=400)

        result = db.get_daily_stats_range("2026-01-01", "2026-01-31")
        assert len(result) == 3
        assert result[0]["date"] == "2026-01-10"
        assert result[2]["date"] == "2026-01-20"

    def test_date_range_inclusive(self, db):
        db.upsert_daily_stats("2026-01-01", total_xp=100)
        db.upsert_daily_stats("2026-01-31", total_xp=200)
        result = db.get_daily_stats_range("2026-01-01", "2026-01-31")
        assert len(result) == 2

    def test_date_range_ordered(self, db):
        db.upsert_daily_stats("2026-01-20", total_xp=300)
        db.upsert_daily_stats("2026-01-10", total_xp=100)
        db.upsert_daily_stats("2026-01-15", total_xp=200)
        result = db.get_daily_stats_range("2026-01-01", "2026-01-31")
        dates = [r["date"] for r in result]
        assert dates == ["2026-01-10", "2026-01-15", "2026-01-20"]


class TestAchievements:
    def test_get_nonexistent(self, db):
        assert db.get_achievement("nonexistent") is None

    def test_unlock_achievement(self, db):
        db.unlock_achievement("hello_world", "Hello, World", "2026-01-15T10:30:00")
        ach = db.get_achievement("hello_world")
        assert ach is not None
        assert ach["name"] == "Hello, World"
        assert ach["unlocked_at"] == "2026-01-15T10:30:00"
        assert ach["progress"] == 1.0

    def test_update_progress(self, db):
        db.update_achievement_progress("centurion", "Centurion", 0.45)
        ach = db.get_achievement("centurion")
        assert ach["progress"] == 0.45
        assert ach["unlocked_at"] is None

    def test_progress_does_not_overwrite_unlock(self, db):
        db.unlock_achievement("hello_world", "Hello, World", "2026-01-15T10:30:00")
        db.update_achievement_progress("hello_world", "Hello, World", 0.5)
        ach = db.get_achievement("hello_world")
        assert ach["unlocked_at"] == "2026-01-15T10:30:00"
        assert ach["progress"] == 1.0

    def test_get_all_achievements_empty(self, db):
        assert db.get_all_achievements() == []

    def test_get_all_achievements(self, db):
        db.unlock_achievement("a_first", "First", "2026-01-01T00:00:00")
        db.update_achievement_progress("b_second", "Second", 0.5)
        db.unlock_achievement("c_third", "Third", "2026-01-02T00:00:00")
        all_ach = db.get_all_achievements()
        assert len(all_ach) == 3
        assert all_ach[0]["id"] == "a_first"
        assert all_ach[1]["id"] == "b_second"
        assert all_ach[2]["id"] == "c_third"

    def test_unlock_updates_existing_progress(self, db):
        db.update_achievement_progress("centurion", "Centurion", 0.7)
        db.unlock_achievement("centurion", "Centurion", "2026-02-01T12:00:00")
        ach = db.get_achievement("centurion")
        assert ach["unlocked_at"] == "2026-02-01T12:00:00"
        assert ach["progress"] == 1.0
