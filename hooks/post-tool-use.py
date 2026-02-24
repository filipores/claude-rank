#!/usr/bin/env python3
"""PostToolUse hook — incremental XP sync."""
from __future__ import annotations

import json
import sys
from pathlib import Path

_PLUGIN_ROOT = Path(__file__).parent.parent
_SRC = _PLUGIN_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


def main() -> None:
    try:
        stdin_data = sys.stdin.read()
        try:
            event = json.loads(stdin_data)
            tool_name = event.get("tool_name", "")
            skip_tools = {"Read", "Glob", "Grep", "WebFetch", "WebSearch"}
            if tool_name in skip_tools:
                sys.exit(0)
        except (json.JSONDecodeError, KeyError):
            pass
        from claude_rank.db import Database
        from claude_rank.cli import do_incremental_sync

        db = Database()
        try:
            do_incremental_sync(db)
        finally:
            db.close()
    except Exception:
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()
