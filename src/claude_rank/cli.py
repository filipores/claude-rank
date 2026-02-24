"""CLI commands for claude-rank."""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timezone
from pathlib import Path

from claude_rank.achievements import (
    ACHIEVEMENTS,
    AchievementStatus,
    check_achievements,
    get_closest_achievements,
    get_newly_unlocked,
)
from claude_rank.db import Database
from claude_rank.config import get_leaderboard_dir, set_leaderboard_dir
from claude_rank.display import (
    console,
    print_achievements,
    print_badge_result,
    print_dashboard,
    print_leaderboard,
    print_leaderboard_export_result,
    print_leaderboard_setup_result,
    print_no_data_message,
    print_prestige_not_ready,
    print_prestige_result,
    print_stats,
    print_sync_result,
    print_wrapped,
)
from claude_rank.leaderboard import (
    build_entry,
    default_export_path,
    load_all_entries,
    rank_entries,
    write_entry,
)
from claude_rank.levels import (
    MAX_LEVEL,
    PRESTIGE_XP_THRESHOLD,
    can_prestige,
    get_prestige_xp,
    level_from_xp,
    prestige_stars,
    tier_from_level,
    xp_progress_in_level,
)
from claude_rank.parser import ClaudeDataParser
from claude_rank.streaks import calculate_streak
from claude_rank.engagement_rating import calculate_historical_er, er_tier_from_mu
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
    subparsers.add_parser("hook", help="Incremental sync for PostToolUse hook")
    subparsers.add_parser("prestige", help="Prestige to reset level and earn a star badge")
    badge_parser = subparsers.add_parser("badge", help="Generate SVG badge for README")
    badge_parser.add_argument("--output", "-o", default="claude-rank-badge.svg", help="Output file path")
    wrapped_parser = subparsers.add_parser("wrapped", help="Show coding stats summary")
    wrapped_parser.add_argument("--period", choices=["month", "year", "all-time"], default="month")
    lb_parser = subparsers.add_parser("leaderboard", help="Team leaderboard (opt-in)")
    lb_sub = lb_parser.add_subparsers(dest="lb_command")
    lb_setup_p = lb_sub.add_parser("setup", help="Configure username and shared directory")
    lb_setup_p.add_argument("--username", "-u", required=True, help="Your display name")
    lb_setup_p.add_argument("--dir", "-d", default=None, help="Path to shared leaderboard directory")
    lb_export_p = lb_sub.add_parser("export", help="Export your stats to shared directory")
    lb_export_p.add_argument("--output", "-o", default=None, help="Override output path")
    lb_show_p = lb_sub.add_parser("show", help="Show team leaderboard")
    lb_show_p.add_argument("--dir", "-d", default=None, help="Override leaderboard directory")
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
        elif command == "hook":
            import sys
            sys.stdin.read()  # Required by hook protocol
            do_incremental_sync(db)
        elif command == "prestige":
            do_prestige(db)
        elif command == "badge":
            do_badge(db, output=args.output)
        elif command == "wrapped":
            do_wrapped(db, period=args.period)
        elif command == "leaderboard":
            lb_cmd = getattr(args, "lb_command", None)
            if lb_cmd == "setup":
                do_leaderboard_setup(db, username=args.username, leaderboard_dir=args.dir)
            elif lb_cmd == "export":
                do_leaderboard_export(db, output=getattr(args, "output", None))
            else:
                do_leaderboard_show(db, directory=getattr(args, "dir", None))
    finally:
        db.close()


def _count_weekend_sessions(daily_activity: list) -> int:
    """Count sessions that occurred on Saturday (5) or Sunday (6)."""
    count = 0
    for da in daily_activity:
        try:
            d = date.fromisoformat(da.date)
            if d.weekday() >= 5:
                count += da.session_count
        except (ValueError, AttributeError):
            continue
    return count


def _build_achievement_stats(
    stats_obj: object, streak_info: object, tool_calls: int, total_xp: int = 0, tool_usage: dict | None = None
) -> dict:
    """Build stats dict for achievement checking.

    stats_obj: ClaudeStats from parser
    streak_info: StreakInfo from streaks module
    tool_calls: total tool calls across all daily activities
    total_xp: total XP earned
    tool_usage: tool usage summary dict from parser
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
        "total_xp": total_xp,
        "bash_count": (tool_usage or {}).get("Bash", 0),
        "task_count": (tool_usage or {}).get("Task", 0),
        "weekend_sessions": _count_weekend_sessions(getattr(stats_obj, "daily_activity", [])),
    }


def do_sync(db: Database) -> dict:
    """Parse Claude Code data, calculate XP, update DB, check achievements.

    Returns a dict with sync results (useful for testing).
    """
    parser = ClaudeDataParser()
    stats = parser.parse_stats_cache()

    if stats is None:
        print_no_data_message()
        return {"days_synced": 0, "total_xp": 0, "level": 1, "tier_name": "Bronze"}

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

    # Calculate Engagement Rating
    er_results = calculate_historical_er(daily_dicts)
    if er_results:
        last_er = er_results[-1]
        er_tier = er_tier_from_mu(last_er.mu_after)
        db.set_profile("er_mu", str(round(last_er.mu_after, 2)))
        db.set_profile("er_phi", str(round(last_er.phi_after, 2)))
        db.set_profile("er_sigma", str(round(last_er.sigma_after, 4)))
        db.set_profile("er_tier_name", er_tier["name"])
        db.set_profile("er_last_rated_date", last_er.date)
        for er in er_results:
            db.upsert_er_history(
                er.date, mu=er.mu_after, phi=er.phi_after, sigma=er.sigma_after,
                quality_score=er.quality_score, mu_before=er.mu_before, outcome=er.outcome,
            )

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

    # Calculate level and tier (prestige-aware)
    prestige_count = int(db.get_profile("prestige_count") or "0")
    prestige_xp = get_prestige_xp(total_xp, prestige_count)
    level = level_from_xp(prestige_xp)
    tier = tier_from_level(level)

    # Calculate streak
    today_str = date.today().isoformat()
    streak_info = calculate_streak(active_dates, today=today_str)

    # Total tool calls for achievements
    total_tool_calls = sum(da.tool_call_count for da in stats.daily_activity)

    # Check achievements
    tool_usage_data = parser.get_tool_usage_summary()
    achievement_stats = _build_achievement_stats(
        stats, streak_info, total_tool_calls,
        total_xp=total_xp,
        tool_usage=tool_usage_data,
    )

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
    db.set_profile("prestige_count", str(prestige_count))
    historical = max(total_xp, int(db.get_profile("historical_total_xp") or "0"))
    db.set_profile("historical_total_xp", str(historical))
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
        "er_mu": float(db.get_profile("er_mu") or "1500.0"),
        "er_tier_name": db.get_profile("er_tier_name") or "Unrated",
    }

    # Write rank.json for status line and hooks
    _write_rank_json(
        total_xp, level, tier, streak_info, total_unlocked, prestige_count,
        er_mu=float(db.get_profile("er_mu") or "1500.0"),
        er_phi=float(db.get_profile("er_phi") or "350.0"),
        er_tier_name=db.get_profile("er_tier_name") or "Unrated",
    )

    print_sync_result(result)
    return result


def _write_rank_json(
    total_xp: int,
    level: int,
    tier: dict,
    streak_info: object,
    achievements_unlocked: int,
    prestige_count: int = 0,
    *,
    er_mu: float = 1500.0,
    er_phi: float = 350.0,
    er_tier_name: str = "Unrated",
) -> None:
    """Write ~/.claude/rank.json for status line and SessionStart hook."""
    prestige_xp = get_prestige_xp(total_xp, prestige_count)
    xp_in_level, xp_for_next = xp_progress_in_level(prestige_xp)
    rank_data = {
        "level": level,
        "title": tier["name"],
        "tier": tier["tier"],
        "color": tier["color"],
        "total_xp": total_xp,
        "xp_in_level": xp_in_level,
        "xp_for_next": xp_for_next,
        "current_streak": getattr(streak_info, "current_streak", 0),
        "longest_streak": getattr(streak_info, "longest_streak", 0),
        "freeze_count": getattr(streak_info, "freeze_count", 0),
        "achievements_unlocked": achievements_unlocked,
        "total_achievements": len(ACHIEVEMENTS),
        "prestige_count": prestige_count,
        "prestige_stars": prestige_stars(prestige_count),
        "er_mu": er_mu,
        "er_phi": er_phi,
        "er_tier_name": er_tier_name,
        "last_sync": datetime.now(tz=timezone.utc).isoformat(),
    }
    rank_file = Path.home() / ".claude" / "rank.json"
    rank_file.write_text(json.dumps(rank_data, indent=2) + "\n")


def do_incremental_sync(db: Database) -> dict:
    """Lightweight sync for today only. For PostToolUse hook calls."""
    from datetime import date as date_cls

    parser = ClaudeDataParser()
    stats = parser.parse_stats_cache()

    if stats is None:
        return {"ok": False}

    today_str = date_cls.today().isoformat()

    today_activity = next(
        (da for da in stats.daily_activity if da.date == today_str),
        None,
    )

    if today_activity is None or today_activity.session_count == 0:
        return {"ok": True, "changed": False}

    # Get previous total XP
    prev_total_xp = int(db.get_profile("total_xp") or "0")

    # Calculate all daily XP to get accurate total
    active_dates = {da.date for da in stats.daily_activity if da.session_count > 0}
    all_daily_dicts = [
        {
            "date": da.date,
            "messageCount": da.message_count,
            "sessionCount": da.session_count,
            "toolCallCount": da.tool_call_count,
        }
        for da in stats.daily_activity
    ]
    daily_xp_list = calculate_historical_xp(all_daily_dicts, {"active_dates": active_dates})
    total_xp = calculate_total_xp(daily_xp_list)

    if total_xp == prev_total_xp:
        return {"ok": True, "changed": False}

    # Upsert today's row
    today_xp = next((d for d in daily_xp_list if d.date == today_str), None)
    if today_xp:
        db.upsert_daily_stats(
            today_str,
            total_xp=today_xp.final_xp,
            messages=today_activity.message_count,
            sessions=today_activity.session_count,
            tool_calls=today_activity.tool_call_count,
            streak_day=True,
        )

    # Calculate Engagement Rating
    er_results = calculate_historical_er(all_daily_dicts)
    if er_results:
        last_er = er_results[-1]
        er_tier = er_tier_from_mu(last_er.mu_after)
        db.set_profile("er_mu", str(round(last_er.mu_after, 2)))
        db.set_profile("er_phi", str(round(last_er.phi_after, 2)))
        db.set_profile("er_sigma", str(round(last_er.sigma_after, 4)))
        db.set_profile("er_tier_name", er_tier["name"])
        db.set_profile("er_last_rated_date", last_er.date)
        for er in er_results:
            db.upsert_er_history(
                er.date, mu=er.mu_after, phi=er.phi_after, sigma=er.sigma_after,
                quality_score=er.quality_score, mu_before=er.mu_before, outcome=er.outcome,
            )

    # Recalculate level, tier, streak (prestige-aware)
    prestige_count = int(db.get_profile("prestige_count") or "0")
    prestige_xp = get_prestige_xp(total_xp, prestige_count)
    level = level_from_xp(prestige_xp)
    tier = tier_from_level(level)
    streak_info = calculate_streak(active_dates, today=today_str)

    # Update profile
    db.set_profile("total_xp", str(total_xp))
    db.set_profile("level", str(level))
    db.set_profile("tier_name", tier["name"])
    db.set_profile("tier_color", tier["color"])
    db.set_profile("current_streak", str(streak_info.current_streak))
    db.set_profile("longest_streak", str(streak_info.longest_streak))
    db.set_profile("freeze_count", str(streak_info.freeze_count))
    db.set_profile("total_sessions", str(stats.total_sessions))
    db.set_profile("total_messages", str(stats.total_messages))
    db.set_profile("prestige_count", str(prestige_count))
    historical = max(total_xp, int(db.get_profile("historical_total_xp") or "0"))
    db.set_profile("historical_total_xp", str(historical))

    # Check achievements
    total_tool_calls = sum(da.tool_call_count for da in stats.daily_activity)
    achievement_stats = _build_achievement_stats(stats, streak_info, total_tool_calls, total_xp=total_xp)
    current_statuses = check_achievements(achievement_stats)
    now_str = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    total_unlocked = 0
    for status in current_statuses:
        if status.unlocked:
            total_unlocked += 1
            existing = db.get_achievement(status.definition.id)
            if not (existing and existing["unlocked_at"]):
                db.unlock_achievement(status.definition.id, status.definition.name, now_str)
        else:
            db.update_achievement_progress(
                status.definition.id, status.definition.name, status.progress
            )

    _write_rank_json(
        total_xp, level, tier, streak_info, total_unlocked, prestige_count,
        er_mu=float(db.get_profile("er_mu") or "1500.0"),
        er_phi=float(db.get_profile("er_phi") or "350.0"),
        er_tier_name=db.get_profile("er_tier_name") or "Unrated",
    )
    return {"ok": True, "changed": True, "total_xp": total_xp, "level": level}


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
        "prestige_count": int(profile.get("prestige_count", "0")),
        "historical_total_xp": int(profile.get("historical_total_xp", "0")),
        "er_mu": float(profile.get("er_mu", "1500.0")),
        "er_phi": float(profile.get("er_phi", "350.0")),
        "er_sigma": float(profile.get("er_sigma", "0.06")),
        "er_tier_name": profile.get("er_tier_name", "Unrated"),
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
        "er_mu": float(profile.get("er_mu", "1500.0")),
        "er_phi": float(profile.get("er_phi", "350.0")),
        "er_sigma": float(profile.get("er_sigma", "0.06")),
        "er_tier_name": profile.get("er_tier_name", "Unrated"),
    }

    if stats:
        data["longest_session_messages"] = stats.longest_session_messages
        data["hour_counts"] = stats.hour_counts
        data["model_usage"] = stats.model_usage
        data["projects"] = stats.projects
        data["tool_usage"] = parser.get_tool_usage_summary()

    print_stats(data)


def _write_rank_badge(total_xp: int, level: int, tier: dict, prestige_count: int = 0) -> None:
    """Write ~/.claude/rank-badge.svg."""
    from claude_rank.badge import generate_badge_svg
    svg = generate_badge_svg(
        level=level, tier_name=tier["name"], tier_color=tier["color"],
        prestige_count=prestige_count, total_xp=total_xp,
    )
    badge_path = Path.home() / ".claude" / "rank-badge.svg"
    badge_path.write_text(svg, encoding="utf-8")


def do_prestige(db: Database) -> dict:
    """Prestige to reset level progress and earn a star badge."""
    profile = db.get_all_profile()
    total_xp = int(profile.get("total_xp", "0"))
    prestige_count = int(profile.get("prestige_count", "0"))

    if not total_xp:
        print_no_data_message()
        return {"ok": False, "reason": "no_data"}

    if not can_prestige(total_xp, prestige_count):
        xp_needed = (prestige_count + 1) * PRESTIGE_XP_THRESHOLD - total_xp
        result = {
            "ok": False, "reason": "not_ready", "xp_needed": xp_needed,
            "current_level": int(profile.get("level", "1")), "max_level": MAX_LEVEL,
        }
        print_prestige_not_ready(result)
        return result

    new_prestige_count = prestige_count + 1
    historical = max(total_xp, int(profile.get("historical_total_xp", str(total_xp))))
    db.set_profile("prestige_count", str(new_prestige_count))
    db.set_profile("historical_total_xp", str(historical))

    prestige_xp = get_prestige_xp(total_xp, new_prestige_count)
    new_level = level_from_xp(prestige_xp)
    new_tier = tier_from_level(new_level)
    db.set_profile("level", str(new_level))
    db.set_profile("tier_name", new_tier["name"])
    db.set_profile("tier_color", new_tier["color"])

    # Rebuild streak info from profile for rank.json
    streak_info_data = type("SI", (), {
        "current_streak": int(profile.get("current_streak", "0")),
        "longest_streak": int(profile.get("longest_streak", "0")),
        "freeze_count": int(profile.get("freeze_count", "0")),
    })()
    total_unlocked = sum(1 for a in db.get_all_achievements() if a["unlocked_at"])
    _write_rank_json(
        total_xp, new_level, new_tier, streak_info_data, total_unlocked, new_prestige_count,
        er_mu=float(profile.get("er_mu", "1500.0")),
        er_phi=float(profile.get("er_phi", "350.0")),
        er_tier_name=profile.get("er_tier_name", "Unrated"),
    )

    result = {
        "ok": True, "prestige_count": new_prestige_count, "stars": prestige_stars(new_prestige_count),
        "new_level": new_level, "tier_name": new_tier["name"], "historical_total_xp": historical,
    }
    print_prestige_result(result)
    return result


def do_badge(db: Database, output: str = "claude-rank-badge.svg") -> dict:
    """Generate an SVG badge for README."""
    from claude_rank.badge import generate_badge_svg
    profile = db.get_all_profile()
    if not profile.get("total_xp"):
        print_no_data_message()
        return {"ok": False}
    level = int(profile.get("level", "1"))
    tier_name = profile.get("tier_name", "Bronze")
    tier_color = profile.get("tier_color", "bronze")
    prestige_count = int(profile.get("prestige_count", "0"))
    total_xp = int(profile.get("total_xp", "0"))
    svg = generate_badge_svg(
        level=level, tier_name=tier_name, tier_color=tier_color,
        prestige_count=prestige_count, total_xp=total_xp,
    )
    output_path = Path(output)
    output_path.write_text(svg, encoding="utf-8")
    result = {"ok": True, "output": str(output_path.resolve()), "level": level, "tier_name": tier_name}
    print_badge_result(result)
    return result


def do_wrapped(db: Database, period: str = "month") -> dict:
    """Show coding stats summary for a time period."""
    from claude_rank.wrapped import aggregate_wrapped, get_period_dates
    profile = db.get_all_profile()
    if not profile.get("total_xp"):
        print_no_data_message()
        return {"ok": False}
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
    summary["period_start"] = start_date
    summary["period_end"] = end_date
    print_wrapped(summary)
    return {"ok": True, **summary}


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


def do_leaderboard_setup(db: Database, username: str, leaderboard_dir: str | None = None) -> dict:
    """Configure leaderboard username and shared directory."""
    db.set_profile("leaderboard_username", username)
    result: dict = {"ok": True, "username": username, "leaderboard_dir": None}
    if leaderboard_dir:
        expanded = Path(leaderboard_dir).expanduser().resolve()
        set_leaderboard_dir(expanded)
        result["leaderboard_dir"] = str(expanded)
    print_leaderboard_setup_result(result)
    return result


def do_leaderboard_export(db: Database, output: str | None = None) -> dict:
    """Export current stats to a leaderboard entry file."""
    profile = db.get_all_profile()
    username = profile.get("leaderboard_username")
    if not username:
        console.print("[red]No username set. Run: claude-rank leaderboard setup --username <name>[/]")
        return {"ok": False, "reason": "no_username"}

    achievements_count = sum(1 for a in db.get_all_achievements() if a["unlocked_at"])
    entry = build_entry(profile, achievements_count)

    if output:
        output_path = Path(output)
    else:
        lb_dir = get_leaderboard_dir()
        if lb_dir is None:
            console.print(
                "[red]No leaderboard directory set. "
                "Use --output or run: claude-rank leaderboard setup --dir <path>[/]"
            )
            return {"ok": False, "reason": "no_dir"}
        output_path = default_export_path(username, lb_dir)

    write_entry(entry, output_path)
    result = {"ok": True, "output": str(output_path), "entry": entry}
    print_leaderboard_export_result(result)
    return result


def do_leaderboard_show(db: Database, directory: str | None = None) -> dict:
    """Show team leaderboard from shared directory."""
    if directory:
        lb_dir = Path(directory).expanduser().resolve()
    else:
        lb_dir = get_leaderboard_dir()

    if lb_dir is None:
        console.print(
            "[red]No leaderboard directory configured. "
            "Run: claude-rank leaderboard setup --dir <path>[/]"
        )
        return {"ok": False, "reason": "no_dir"}

    if not lb_dir.is_dir():
        console.print(f"[red]Directory not found: {lb_dir}[/]")
        return {"ok": False, "reason": "dir_not_found"}

    entries = load_all_entries(lb_dir)
    ranked = rank_entries(entries)

    profile = db.get_all_profile()
    username = profile.get("leaderboard_username")
    print_leaderboard(ranked, highlight_username=username)
    return {"ok": True, "entries": ranked, "count": len(ranked)}
