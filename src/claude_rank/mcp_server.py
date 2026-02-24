"""MCP server for claude-rank.

Exposes claude-rank stats as MCP tools so Claude can query them mid-conversation.
Run via: python3 -m claude_rank.mcp_server
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(name="claude-rank")


def _get_db():
    from claude_rank.db import Database
    return Database()


@mcp.tool()
def get_rank() -> dict[str, Any]:
    """Get current rank: level, tier, XP, streak, and prestige info."""
    rank_file = Path.home() / ".claude" / "rank.json"
    if rank_file.exists():
        try:
            return json.loads(rank_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    db = _get_db()
    try:
        from claude_rank.levels import prestige_stars, tier_from_level, xp_progress_in_level
        profile = db.get_all_profile()
        if not profile.get("total_xp"):
            return {"error": "No data yet. Run claude-rank sync first."}
        total_xp = int(profile.get("total_xp", "0"))
        level = int(profile.get("level", "1"))
        prestige_count = int(profile.get("prestige_count", "0"))
        xp_in_level, xp_for_next = xp_progress_in_level(total_xp)
        tier = tier_from_level(level)
        return {
            "level": level, "title": tier["name"], "tier": tier["tier"],
            "color": tier["color"], "total_xp": total_xp,
            "xp_in_level": xp_in_level, "xp_for_next": xp_for_next,
            "current_streak": int(profile.get("current_streak", "0")),
            "longest_streak": int(profile.get("longest_streak", "0")),
            "freeze_count": int(profile.get("freeze_count", "0")),
            "prestige_count": prestige_count,
            "prestige_stars": prestige_stars(prestige_count),
        }
    finally:
        db.close()


@mcp.tool()
def get_achievements() -> dict[str, Any]:
    """Get all achievements with unlock status and progress."""
    db = _get_db()
    try:
        from claude_rank.achievements import ACHIEVEMENTS
        db_achievements = {a["id"]: a for a in db.get_all_achievements()}
        result = []
        for achdef in ACHIEVEMENTS:
            db_ach = db_achievements.get(achdef.id)
            progress = db_ach["progress"] if db_ach else 0.0
            unlocked = bool(db_ach and db_ach["unlocked_at"])
            if unlocked:
                progress = 1.0
            result.append({
                "id": achdef.id, "name": achdef.name,
                "description": achdef.description, "rarity": achdef.rarity.value,
                "progress": progress, "progress_pct": int(progress * 100),
                "target": int(achdef.target), "unlocked": unlocked,
                "unlocked_at": db_ach["unlocked_at"] if db_ach else None,
            })
        return {"achievements": result, "unlocked_count": sum(1 for a in result if a["unlocked"]),
                "total_count": len(result)}
    finally:
        db.close()


@mcp.tool()
def get_wrapped(period: str = "month") -> dict[str, Any]:
    """Get stats summary for a time period (month, year, or all-time)."""
    valid = {"month", "year", "all-time"}
    if period not in valid:
        return {"error": f"Invalid period. Must be one of: {', '.join(sorted(valid))}"}
    db = _get_db()
    try:
        from claude_rank.parser import ClaudeDataParser
        from claude_rank.wrapped import aggregate_wrapped, get_period_dates
        profile = db.get_all_profile()
        if not profile.get("total_xp"):
            return {"error": "No data yet."}
        today_str = date.today().isoformat()
        start_date, end_date = get_period_dates(period, today=today_str)
        daily_stats = db.get_daily_stats_range(start_date, end_date)
        tool_usage, projects, hour_counts = {}, [], [0] * 24
        parser = ClaudeDataParser()
        stats = parser.parse_stats_cache()
        if stats:
            hour_counts = stats.hour_counts
            projects = stats.projects
            tool_usage = parser.get_tool_usage_summary()
        summary = aggregate_wrapped(
            daily_stats=daily_stats, profile=profile,
            tool_usage=tool_usage, projects=projects, hour_counts=hour_counts,
        )
        summary["period"] = period
        summary["top_tools"] = [{"tool": n, "count": c} for n, c in summary.get("top_tools", [])]
        return summary
    finally:
        db.close()


@mcp.tool()
def get_badge() -> dict[str, Any]:
    """Generate an SVG badge string showing current rank."""
    db = _get_db()
    try:
        from claude_rank.badge import generate_badge_svg
        profile = db.get_all_profile()
        if not profile.get("total_xp"):
            return {"error": "No data yet."}
        level = int(profile.get("level", "1"))
        tier_name = profile.get("tier_name", "Prompt Novice")
        tier_color = profile.get("tier_color", "grey")
        prestige_count = int(profile.get("prestige_count", "0"))
        total_xp = int(profile.get("total_xp", "0"))
        svg = generate_badge_svg(
            level=level, tier_name=tier_name, tier_color=tier_color,
            prestige_count=prestige_count, total_xp=total_xp,
        )
        return {"svg": svg, "level": level, "tier_name": tier_name, "total_xp": total_xp,
                "markdown": "![Claude Rank](claude-rank-badge.svg)"}
    finally:
        db.close()


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
