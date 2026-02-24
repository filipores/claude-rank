"""Tests for the config module."""
from pathlib import Path

from claude_rank.config import (
    get_leaderboard_dir,
    load_config,
    save_config,
    set_leaderboard_dir,
)


class TestLoadConfig:
    def test_missing_file_returns_empty(self, tmp_path):
        assert load_config(tmp_path / "nonexistent.json") == {}

    def test_invalid_json_returns_empty(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("not json", encoding="utf-8")
        assert load_config(path) == {}

    def test_loads_valid_json(self, tmp_path):
        path = tmp_path / "config.json"
        path.write_text('{"key": "value"}', encoding="utf-8")
        assert load_config(path) == {"key": "value"}


class TestSaveConfig:
    def test_creates_file(self, tmp_path):
        path = tmp_path / "config.json"
        save_config({"hello": "world"}, path)
        assert path.exists()
        import json
        assert json.loads(path.read_text()) == {"hello": "world"}

    def test_creates_parent_dirs(self, tmp_path):
        path = tmp_path / "sub" / "dir" / "config.json"
        save_config({"nested": True}, path)
        assert path.exists()

    def test_overwrites_existing(self, tmp_path):
        path = tmp_path / "config.json"
        save_config({"v": 1}, path)
        save_config({"v": 2}, path)
        import json
        assert json.loads(path.read_text()) == {"v": 2}


class TestLeaderboardDir:
    def test_not_set_returns_none(self, tmp_path):
        path = tmp_path / "config.json"
        assert get_leaderboard_dir(path) is None

    def test_set_and_get_roundtrip(self, tmp_path):
        config_path = tmp_path / "config.json"
        target = tmp_path / "shared" / "leaderboard"
        set_leaderboard_dir(target, config_path)
        result = get_leaderboard_dir(config_path)
        assert result == target

    def test_preserves_other_config_keys(self, tmp_path):
        config_path = tmp_path / "config.json"
        save_config({"other_key": "keep_me"}, config_path)
        set_leaderboard_dir(Path("/some/path"), config_path)
        config = load_config(config_path)
        assert config["other_key"] == "keep_me"
        assert config["leaderboard_dir"] == "/some/path"
