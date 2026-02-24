"""CLI commands for claude-rank."""

from __future__ import annotations

import argparse
from datetime import date, datetime, timezone

from claude_rank.achievements import (
    ACHIEVEMENTS,
    AchievementStatus,
    check_achievements,
    get_closest_achievements,
    get_newly_unlocked,
)
from claude_rank.db import Database
from claude_rank.display import (
    print_achievements,
    print_dashboard,
    print_no_data_message,
    print_stats,
    print_sync_result,
)
from claude_rank.levels import level_from_xp, tier_from_level, xp_progress_in_level
from claude_rank.parser import ClaudeDataParser
from claude_rank.streaks import calculate_streak
from claude_rank.xp import calculate_historical_xp, calculate_total_xp


def build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser."""
    parser = argparse.ArgumentParser(
        prog="claude-rank",
        description="Gamify your Claude Code usage",
    )
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("dashboard", help="Show main dashboard")
    subparsers.add_parser("stats", help="Detailed stats breakdown")
    subparsers.add_parser("achievements", help="List all achievements")
    subparsers.add_parser("sync", help="Re-parse Claude Code data and update")
    return parser


def main() -> None:
    """Entry point for the CLI."""
    parser = build_parser()
    args = parser.parse_args()
    command = args.command or "dashboard"

    db = Database()

    try:
        if command == "sync":
            do_sync(db)
        elif command == "dashboard":
            do_dashboard(db)
        elif command == "stats":
            do_stats(db)
        elif command == "achievements":
            do_achievements(db)
    finally:
        db.close()


def _build_achievement_stats(stats_obj: object, streak_info: object, tool_calls: int) -> dict:
    """Build stats dict for achievement checking.

    stats_obj: ClaudeStats from parser
    streak_info: StreakInfo from streaks module
    tool_calls: total tool calls across all daily activities
    """
    hour_counts = getattr(stats_obj, "hour_counts", [0] * 24)
    night_sessions = sum(hour_counts[0:5])  # hours 0-4
    early_sessions = sum(hour_counts[5:7])  # hours 5-6

    return {
        "total_sessions": getattr(stats_obj, "total_sessions", 0),
        "total_messages": getattr(stats_obj, "total_messages", 0),
        "total_tool_calls": tool_calls,
        "night_sessions": night_sessions,
        "early_sessions": early_sessions,
        "current_streak": getattr(streak_info, "current_streak", 0),
        "longest_streak": getattr(streak_info, "longest_streak", 0),
        "unique_projects": len(getattr(stats_obj, "projects", [])),
        "longest_session_messages": getattr(stats_obj, "longest_session_messages", 0),
    }


def do_sync(db: Database) -> dict:
    """Parse Claude Code data, calculate XP, update DB, check achievements.

    Returns a dict with sync results (useful for testing).
    """
    parser = ClaudeDataParser()
    stats = parser.parse_stats_cache()

    if stats is None:
        print_no_data_message()
        return {"days_synced": 0, "total_xp": 0, "level": 1, "tier_name": "Prompt Novice"}

    # Build daily activity dicts for XP calculation
    active_dates = {da.date for da in stats.daily_activity if da.session_count > 0}
    daily_dicts = [
        {
            "date": da.date,
            "messageCount": da.message_count,
            "sessionCount": da.session_count,
            "toolCallCount": da.tool_call_count,
        }
        for da in stats.daily_activity
    ]

    # Calculate historical XP
    daily_xp_list = calculate_historical_xp(
        daily_dicts,
        {"active_dates": active_dates},
    )
    total_xp = calculate_total_xp(daily_xp_list)

    # Store daily stats in DB
    for dxp in daily_xp_list:
        activity = next((da for da in stats.daily_activity if da.date == dxp.date), None)
        if activity:
            db.upsert_daily_stats(
                dxp.date,
                total_xp=dxp.final_xp,
                messages=activity.message_count,
                sessions=activity.session_count,
                tool_calls=activity.tool_call_count,
                streak_day=dxp.date in active_dates,
            )

    # Calculate level and tier
    level = level_from_xp(total_xp)
    tier = tier_from_level(level)

    # Calculate streak
    today_str = date.today().isoformat()
    streak_info = calculate_streak(active_dates, today=today_str)

    # Total tool calls for achievements
    total_tool_calls = sum(da.tool_call_count for da in stats.daily_activity)

    # Check achievements
    achievement_stats = _build_achievement_stats(stats, streak_info, total_tool_calls)

    # Get previous achievement state for comparison
    previous_statuses: list[AchievementStatus] = []
    for achdef in ACHIEVEMENTS:
        db_ach = db.get_achievement(achdef.id)
        if db_ach and db_ach["unlocked_at"]:
            previous_statuses.append(
                AchievementStatus(
                    definition=achdef,
                    progress=1.0,
                    unlocked=True,
                    unlocked_at=db_ach["unlocked_at"],
                )
            )
        else:
            previous_statuses.append(
                AchievementStatus(
                    definition=achdef,
                    progress=db_ach["progress"] if db_ach else 0.0,
                    unlocked=False,
                    unlocked_at=None,
                )
            )

    current_statuses = check_achievements(achievement_stats)
    newly_unlocked = get_newly_unlocked(previous_statuses, current_statuses)

    # Store achievements in DB
    now_str = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    for status in current_statuses:
        if status.unlocked:
            # Check if already unlocked in DB
            existing = db.get_achievement(status.definition.id)
            if existing and existing["unlocked_at"]:
                continue
            db.unlock_achievement(status.definition.id, status.definition.name, now_str)
        else:
            db.update_achievement_progress(
                status.definition.id, status.definition.name, status.progress
            )

    # Store profile data
    db.set_profile("total_xp", str(total_xp))
    db.set_profile("level", str(level))
    db.set_profile("tier_name", tier["name"])
    db.set_profile("tier_color", tier["color"])
    db.set_profile("current_streak", str(streak_info.current_streak))
    db.set_profile("longest_streak", str(streak_info.longest_streak))
    db.set_profile("freeze_count", str(streak_info.freeze_count))
    db.set_profile("total_sessions", str(stats.total_sessions))
    db.set_profile("total_messages", str(stats.total_messages))
    db.set_profile("total_tool_calls", str(total_tool_calls))
    db.set_profile("days_synced", str(len(daily_xp_list)))
    db.set_profile("last_sync", now_str)
    if stats.first_session_date:
        db.set_profile("member_since", stats.first_session_date)

    total_unlocked = sum(1 for s in current_statuses if s.unlocked)

    result = {
        "days_synced": len(daily_xp_list),
        "total_xp": total_xp,
        "level": level,
        "tier_name": tier["name"],
        "total_achievements_unlocked": total_unlocked,
        "new_achievements": [a.name for a in newly_unlocked],
    }

    print_sync_result(result)
    return result


def do_dashboard(db: Database) -> None:
    """Show main dashboard with level, XP, streak, recent achievements."""
    profile = db.get_all_profile()

    if not profile.get("total_xp"):
        print_no_data_message()
        return

    total_xp = int(profile.get("total_xp", "0"))
    level = int(profile.get("level", "1"))
    tier = tier_from_level(level)
    xp_in_level, xp_for_next = xp_progress_in_level(total_xp)

    # Get recent unlocked achievements (from DB)
    all_db_achievements = db.get_all_achievements()
    unlocked_achievements = [a for a in all_db_achievements if a["unlocked_at"]]
    unlocked_achievements.sort(key=lambda a: a["unlocked_at"] or "", reverse=True)

    recent_achievements = []
    for ach in unlocked_achievements[:3]:
        achdef = next((a for a in ACHIEVEMENTS if a.id == ach["id"]), None)
        if achdef:
            recent_achievements.append({
                "name": achdef.name,
                "description": achdef.description,
                "unlocked_at": ach["unlocked_at"],
            })

    # Get closest achievements (from DB)
    db_statuses: list[AchievementStatus] = []
    for achdef in ACHIEVEMENTS:
        db_ach = db.get_achievement(achdef.id)
        if db_ach and db_ach["unlocked_at"]:
            db_statuses.append(
                AchievementStatus(
                    definition=achdef, progress=1.0, unlocked=True, unlocked_at=db_ach["unlocked_at"]
                )
            )
        else:
            db_statuses.append(
                AchievementStatus(
                    definition=achdef,
                    progress=db_ach["progress"] if db_ach else 0.0,
                    unlocked=False,
                    unlocked_at=None,
                )
            )

    closest_statuses = get_closest_achievements(db_statuses)
    closest_achievements = []
    for status in closest_statuses:
        current_val = int(status.progress * status.definition.target)
        closest_achievements.append({
            "name": status.definition.name,
            "progress": status.progress,
            "current": current_val,
            "target": int(status.definition.target),
        })

    data = {
        "level": level,
        "total_xp": total_xp,
        "xp_in_level": xp_in_level,
        "xp_for_next": xp_for_next,
        "tier_name": tier["name"],
        "tier_color": tier["color"],
        "current_streak": int(profile.get("current_streak", "0")),
        "longest_streak": int(profile.get("longest_streak", "0")),
        "freeze_count": int(profile.get("freeze_count", "0")),
        "total_sessions": int(profile.get("total_sessions", "0")),
        "total_messages": int(profile.get("total_messages", "0")),
        "recent_achievements": recent_achievements,
        "closest_achievements": closest_achievements,
        "member_since": profile.get("member_since", "unknown"),
    }
    print_dashboard(data)


def do_stats(db: Database) -> None:
    """Show detailed stats by parsing fresh data."""
    profile = db.get_all_profile()

    if not profile.get("total_xp"):
        print_no_data_message()
        return

    parser = ClaudeDataParser()
    stats = parser.parse_stats_cache()

    total_tool_calls = int(profile.get("total_tool_calls", "0"))
    level = int(profile.get("level", "1"))
    tier = tier_from_level(level)

    data: dict = {
        "total_sessions": int(profile.get("total_sessions", "0")),
        "total_messages": int(profile.get("total_messages", "0")),
        "total_tool_calls": total_tool_calls,
        "current_streak": int(profile.get("current_streak", "0")),
        "longest_streak": int(profile.get("longest_streak", "0")),
        "total_xp": int(profile.get("total_xp", "0")),
        "level": level,
        "tier_name": tier["name"],
        "tier_color": tier["color"],
        "longest_session_messages": 0,
        "hour_counts": [0] * 24,
        "model_usage": {},
        "projects": [],
        "tool_usage": {},
    }

    if stats:
        data["longest_session_messages"] = stats.longest_session_messages
        data["hour_counts"] = stats.hour_counts
        data["model_usage"] = stats.model_usage
        data["projects"] = stats.projects
        data["tool_usage"] = parser.get_tool_usage_summary()

    print_stats(data)


def do_achievements(db: Database) -> None:
    """Show all achievements with progress."""
    achievements_data: list[dict] = []
    for achdef in ACHIEVEMENTS:
        db_ach = db.get_achievement(achdef.id)
        progress = db_ach["progress"] if db_ach else 0.0
        unlocked = bool(db_ach and db_ach["unlocked_at"])
        unlocked_at = db_ach["unlocked_at"] if db_ach else None

        if unlocked:
            progress = 1.0

        current_val = int(progress * achdef.target)

        achievements_data.append({
            "id": achdef.id,
            "name": achdef.name,
            "description": achdef.description,
            "rarity": achdef.rarity.value,
            "progress": progress,
            "unlocked": unlocked,
            "unlocked_at": unlocked_at,
            "current": current_val,
            "target": int(achdef.target),
        })

    print_achievements(achievements_data)
