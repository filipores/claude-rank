"""Data aggregation for Claude Code Wrapped summaries.

Pure functions that aggregate daily_stats data into wrapped summary dicts.
No side effects, no DB access - accepts raw data as input.
"""

from __future__ import annotations

from datetime import date, timedelta


def get_period_dates(period: str, today: str | None = None) -> tuple[str, str]:
    """Return (start_date, end_date) ISO strings for a period name.

    period: "month" | "year" | "all-time"
    """
    ref = date.fromisoformat(today) if today else date.today()

    if period == "month":
        start = ref.replace(day=1)
        if ref.month == 12:
            end = ref.replace(month=12, day=31)
        else:
            end = ref.replace(month=ref.month + 1, day=1) - timedelta(days=1)
        return (start.isoformat(), end.isoformat())

    if period == "year":
        start = ref.replace(month=1, day=1)
        end = ref.replace(month=12, day=31)
        return (start.isoformat(), end.isoformat())

    # all-time
    return ("0000-01-01", ref.isoformat())


def aggregate_wrapped(
    daily_stats: list[dict],
    profile: dict,
    tool_usage: dict[str, int] | None = None,
    projects: list[str] | None = None,
    hour_counts: list[int] | None = None,
) -> dict:
    """Aggregate daily_stats rows into a wrapped summary dict."""
    if not daily_stats:
        return _empty_wrapped_summary(profile)

    total_xp_earned = sum(d.get("total_xp", 0) for d in daily_stats)
    total_messages = sum(d.get("messages", 0) for d in daily_stats)
    total_sessions = sum(d.get("sessions", 0) for d in daily_stats)
    total_tool_calls = sum(d.get("tool_calls", 0) for d in daily_stats)
    active_days = sum(1 for d in daily_stats if d.get("streak_day", False))
    total_days = len(daily_stats)

    current_level = int(profile.get("level", "1"))
    prestige_count = int(profile.get("prestige_count", "0"))

    busiest_day_row = max(daily_stats, key=lambda d: d.get("total_xp", 0), default=None)
    busiest_day = busiest_day_row["date"] if busiest_day_row else None
    busiest_day_xp = busiest_day_row.get("total_xp", 0) if busiest_day_row else 0

    busiest_hour: int | None = None
    if hour_counts and any(h > 0 for h in hour_counts):
        busiest_hour = hour_counts.index(max(hour_counts))

    period_streak = _calculate_period_streak(daily_stats)

    top_tools: list[tuple[str, int]] = []
    if tool_usage:
        sorted_tools = sorted(tool_usage.items(), key=lambda x: x[1], reverse=True)
        top_tools = sorted_tools[:5]

    avg_xp_per_day = total_xp_earned // active_days if active_days > 0 else 0

    return {
        "total_xp_earned": total_xp_earned,
        "total_messages": total_messages,
        "total_sessions": total_sessions,
        "total_tool_calls": total_tool_calls,
        "active_days": active_days,
        "total_days": total_days,
        "avg_xp_per_day": avg_xp_per_day,
        "busiest_day": busiest_day,
        "busiest_day_xp": busiest_day_xp,
        "busiest_hour": busiest_hour,
        "period_streak": period_streak,
        "top_tools": top_tools,
        "current_level": current_level,
        "prestige_count": prestige_count,
        "projects_count": len(projects) if projects else 0,
        "lifetime_xp": int(profile.get("total_xp", "0")),
        "longest_streak": int(profile.get("longest_streak", "0")),
        "member_since": profile.get("member_since", "unknown"),
    }


def _calculate_period_streak(daily_stats: list[dict]) -> int:
    """Calculate longest consecutive streak within the given daily_stats window."""
    if not daily_stats:
        return 0

    streak_days = {d["date"] for d in daily_stats if d.get("streak_day", False)}
    if not streak_days:
        return 0

    sorted_dates = sorted(streak_days)
    longest = 1
    current = 1
    for i in range(1, len(sorted_dates)):
        prev = date.fromisoformat(sorted_dates[i - 1])
        curr = date.fromisoformat(sorted_dates[i])
        if (curr - prev).days == 1:
            current += 1
            longest = max(longest, current)
        else:
            current = 1
    return longest


def _empty_wrapped_summary(profile: dict) -> dict:
    """Return an empty wrapped summary when no data is available."""
    return {
        "total_xp_earned": 0,
        "total_messages": 0,
        "total_sessions": 0,
        "total_tool_calls": 0,
        "active_days": 0,
        "total_days": 0,
        "avg_xp_per_day": 0,
        "busiest_day": None,
        "busiest_day_xp": 0,
        "busiest_hour": None,
        "period_streak": 0,
        "top_tools": [],
        "current_level": int(profile.get("level", "1")),
        "prestige_count": int(profile.get("prestige_count", "0")),
        "projects_count": 0,
        "lifetime_xp": int(profile.get("total_xp", "0")),
        "longest_streak": int(profile.get("longest_streak", "0")),
        "member_since": profile.get("member_since", "unknown"),
    }
