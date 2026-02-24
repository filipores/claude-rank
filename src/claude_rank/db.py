"""SQLite database layer for claude-rank."""

import sqlite3
from pathlib import Path


DEFAULT_DB_PATH = Path.home() / ".claude-rank" / "data.db"


class Database:
    """SQLite database manager with WAL mode."""

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.init_db()

    def init_db(self) -> None:
        """Create tables if they do not exist."""
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS daily_stats (
                date TEXT PRIMARY KEY,
                total_xp INTEGER DEFAULT 0,
                messages INTEGER DEFAULT 0,
                sessions INTEGER DEFAULT 0,
                tool_calls INTEGER DEFAULT 0,
                streak_day BOOLEAN DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS achievements (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                unlocked_at TEXT,
                progress REAL DEFAULT 0.0
            );

            CREATE TABLE IF NOT EXISTS profile (
                key TEXT PRIMARY KEY,
                value TEXT
            );

            CREATE TABLE IF NOT EXISTS engagement_history (
                date TEXT PRIMARY KEY,
                mu REAL DEFAULT 1500.0,
                phi REAL DEFAULT 350.0,
                sigma REAL DEFAULT 0.06,
                quality_score REAL DEFAULT 0.0,
                mu_before REAL DEFAULT 1500.0,
                outcome REAL DEFAULT 0.5
            );
        """)
        self.conn.commit()

    def get_profile(self, key: str) -> str | None:
        """Get a profile value by key."""
        row = self.conn.execute(
            "SELECT value FROM profile WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else None

    def set_profile(self, key: str, value: str) -> None:
        """Set a profile value (upsert)."""
        self.conn.execute(
            "INSERT INTO profile (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, str(value)),
        )
        self.conn.commit()

    def get_all_profile(self) -> dict[str, str]:
        """Return all profile key-value pairs as a dict."""
        rows = self.conn.execute("SELECT key, value FROM profile").fetchall()
        return {row["key"]: row["value"] for row in rows}

    def upsert_daily_stats(self, date: str, **kwargs: int | bool) -> None:
        """Insert or update daily stats for a given date."""
        existing = self.get_daily_stats(date)
        if existing is None:
            columns = ["date"] + list(kwargs.keys())
            placeholders = ", ".join(["?"] * len(columns))
            col_str = ", ".join(columns)
            values = [date] + list(kwargs.values())
            self.conn.execute(
                f"INSERT INTO daily_stats ({col_str}) VALUES ({placeholders})",
                values,
            )
        else:
            if kwargs:
                set_clause = ", ".join(f"{k} = ?" for k in kwargs)
                values = list(kwargs.values()) + [date]
                self.conn.execute(
                    f"UPDATE daily_stats SET {set_clause} WHERE date = ?",
                    values,
                )
        self.conn.commit()

    def get_daily_stats(self, date: str) -> dict | None:
        """Get daily stats for a specific date."""
        row = self.conn.execute(
            "SELECT * FROM daily_stats WHERE date = ?", (date,)
        ).fetchone()
        return dict(row) if row else None

    def get_daily_stats_range(self, start_date: str, end_date: str) -> list[dict]:
        """Get daily stats for a date range (inclusive)."""
        rows = self.conn.execute(
            "SELECT * FROM daily_stats WHERE date >= ? AND date <= ? ORDER BY date",
            (start_date, end_date),
        ).fetchall()
        return [dict(row) for row in rows]

    def get_achievement(self, achievement_id: str) -> dict | None:
        """Get a single achievement by ID."""
        row = self.conn.execute(
            "SELECT * FROM achievements WHERE id = ?", (achievement_id,)
        ).fetchone()
        return dict(row) if row else None

    def unlock_achievement(self, achievement_id: str, name: str, timestamp: str) -> None:
        """Unlock an achievement (upsert with unlocked_at timestamp)."""
        self.conn.execute(
            "INSERT INTO achievements (id, name, unlocked_at, progress) VALUES (?, ?, ?, 1.0) "
            "ON CONFLICT(id) DO UPDATE SET unlocked_at = excluded.unlocked_at, progress = 1.0",
            (achievement_id, name, timestamp),
        )
        self.conn.commit()

    def update_achievement_progress(self, achievement_id: str, name: str, progress: float) -> None:
        """Update achievement progress (0.0 to 1.0). Does not overwrite if already unlocked."""
        existing = self.get_achievement(achievement_id)
        if existing and existing["unlocked_at"] is not None:
            return
        self.conn.execute(
            "INSERT INTO achievements (id, name, progress) VALUES (?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET progress = excluded.progress, name = excluded.name",
            (achievement_id, name, progress),
        )
        self.conn.commit()

    def get_all_achievements(self) -> list[dict]:
        """Return all achievements."""
        rows = self.conn.execute(
            "SELECT * FROM achievements ORDER BY id"
        ).fetchall()
        return [dict(row) for row in rows]

    def upsert_er_history(self, date: str, **kwargs: float) -> None:
        """Insert or update ER history for a given date."""
        existing = self.get_er_history(date)
        if existing is None:
            columns = ["date"] + list(kwargs.keys())
            placeholders = ", ".join(["?"] * len(columns))
            col_str = ", ".join(columns)
            values = [date] + list(kwargs.values())
            self.conn.execute(
                f"INSERT INTO engagement_history ({col_str}) VALUES ({placeholders})",
                values,
            )
        else:
            if kwargs:
                set_clause = ", ".join(f"{k} = ?" for k in kwargs)
                values = list(kwargs.values()) + [date]
                self.conn.execute(
                    f"UPDATE engagement_history SET {set_clause} WHERE date = ?",
                    values,
                )
        self.conn.commit()

    def get_er_history(self, date: str) -> dict | None:
        """Get ER history for a specific date."""
        row = self.conn.execute(
            "SELECT * FROM engagement_history WHERE date = ?", (date,)
        ).fetchone()
        return dict(row) if row else None

    def get_er_history_range(self, start_date: str, end_date: str) -> list[dict]:
        """Get ER history for a date range (inclusive), ordered by date."""
        rows = self.conn.execute(
            "SELECT * FROM engagement_history WHERE date >= ? AND date <= ? ORDER BY date",
            (start_date, end_date),
        ).fetchall()
        return [dict(row) for row in rows]

    def get_latest_er_state(self) -> dict | None:
        """Get the most recent ER history entry."""
        row = self.conn.execute(
            "SELECT * FROM engagement_history ORDER BY date DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None

    def close(self) -> None:
        """Close the database connection."""
        self.conn.close()
