"""Configuration file management for claude-rank.

Reads and writes ~/.claude-rank/config.json for settings that don't belong in the DB
(e.g., shared directory paths).
"""
from __future__ import annotations

import json
from pathlib import Path

DEFAULT_CONFIG_PATH: Path = Path.home() / ".claude-rank" / "config.json"


def load_config(config_path: Path | None = None) -> dict:
    """Load config from JSON file. Returns {} if file missing or invalid."""
    path = config_path or DEFAULT_CONFIG_PATH
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_config(data: dict, config_path: Path | None = None) -> None:
    """Write config dict to JSON file. Creates parent dirs if needed."""
    path = config_path or DEFAULT_CONFIG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def get_leaderboard_dir(config_path: Path | None = None) -> Path | None:
    """Return the configured leaderboard directory, or None if not set."""
    config = load_config(config_path)
    raw = config.get("leaderboard_dir")
    if raw:
        return Path(raw)
    return None


def set_leaderboard_dir(directory: Path, config_path: Path | None = None) -> None:
    """Persist the leaderboard directory path to config."""
    config = load_config(config_path)
    config["leaderboard_dir"] = str(directory)
    save_config(config, config_path)
