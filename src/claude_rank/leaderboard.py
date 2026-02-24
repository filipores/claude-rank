"""Leaderboard entry management for claude-rank.

Pure functions for building, reading, writing, and ranking leaderboard entries.
No side effects beyond file I/O for write/read operations.
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

LEADERBOARD_SCHEMA_VERSION = 1
LEADERBOARD_FILE_SUFFIX = ".leaderboard.json"


def build_entry(profile: dict, achievements_count: int) -> dict:
    """Construct a leaderboard entry dict from DB profile data.

    profile must contain 'leaderboard_username'. Other keys read:
    total_xp, level, tier_name, tier_color, current_streak,
    longest_streak, prestige_count.

    Raises ValueError if leaderboard_username is not set.
    """
    username = profile.get("leaderboard_username")
    if not username:
        raise ValueError(
            "No username configured. Run: claude-rank leaderboard setup --username <name>"
        )
    return {
        "schema_version": LEADERBOARD_SCHEMA_VERSION,
        "username": username,
        "level": int(profile.get("level", "1")),
        "tier": profile.get("tier_name", "Bronze"),
        "tier_color": profile.get("tier_color", "bronze"),
        "total_xp": int(profile.get("total_xp", "0")),
        "current_streak": int(profile.get("current_streak", "0")),
        "longest_streak": int(profile.get("longest_streak", "0")),
        "achievements_count": achievements_count,
        "prestige_count": int(profile.get("prestige_count", "0")),
        "last_updated": datetime.now(tz=timezone.utc).isoformat(),
    }


def write_entry(entry: dict, output_path: Path) -> None:
    """Write a leaderboard entry JSON to output_path using atomic write."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_path = tempfile.mkstemp(dir=output_path.parent, suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(entry, f, indent=2)
            f.write("\n")
        os.replace(tmp_path, output_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def read_entry(path: Path) -> dict | None:
    """Read and validate one .leaderboard.json file.

    Returns None if file is missing, unreadable, or fails validation.
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return None
        if data.get("schema_version") != LEADERBOARD_SCHEMA_VERSION:
            return None
        if "username" not in data or "total_xp" not in data:
            return None
        return data
    except Exception:
        return None


def load_all_entries(directory: Path) -> list[dict]:
    """Glob all *.leaderboard.json files in directory and return valid entries."""
    if not directory.is_dir():
        return []
    entries = []
    for path in sorted(directory.glob(f"*{LEADERBOARD_FILE_SUFFIX}")):
        entry = read_entry(path)
        if entry is not None:
            entries.append(entry)
    return entries


def rank_entries(entries: list[dict]) -> list[dict]:
    """Sort entries by total_xp descending. Adds 'rank' key (1-based).

    Tie-break: longest_streak desc, then achievements_count desc.
    """
    sorted_entries = sorted(
        entries,
        key=lambda e: (
            -e.get("total_xp", 0),
            -e.get("longest_streak", 0),
            -e.get("achievements_count", 0),
        ),
    )
    for i, entry in enumerate(sorted_entries):
        entry["rank"] = i + 1
    return sorted_entries


def default_export_path(username: str, leaderboard_dir: Path) -> Path:
    """Return the canonical export path: {leaderboard_dir}/{username}.leaderboard.json"""
    return leaderboard_dir / f"{username}{LEADERBOARD_FILE_SUFFIX}"
