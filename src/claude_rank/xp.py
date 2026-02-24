"""XP calculation engine for claude-rank.

Pure functions that convert Claude Code activity data into XP points.
All calculations use integers (math.floor for rounding).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# Base XP values
XP_PER_SESSION = 10
XP_PER_MESSAGE = 1
XP_PER_TOOL_CALL = 2
XP_PER_PROJECT = 5
XP_PER_EDIT = 3
XP_PER_COMMIT = 5

# Anti-gaming
DAILY_XP_CAP = 800
DIMINISHING_THRESHOLD = 500
MIN_TOOL_CALLS_FOR_SESSION_XP = 5

# Streak multipliers (threshold -> multiplier)
STREAK_MULTIPLIERS: dict[int, float] = {
    7: 1.25,
    14: 1.5,
    30: 2.0,
}

# First session of day bonus
FIRST_SESSION_BONUS = 1.5


@dataclass
class DailyXP:
    """XP breakdown for a single day."""

    date: str
    base_xp: int
    multiplier: float
    final_xp: int
    breakdown: dict[str, int]


def get_streak_multiplier(streak_days: int) -> float:
    """Return the multiplier for current streak length.

    Uses highest applicable tier. Default 1.0 if no streak bonus.
    E.g., streak_days=10 -> 1.25 (7-day tier), streak_days=20 -> 1.5 (14-day tier).
    """
    multiplier = 1.0
    for threshold in sorted(STREAK_MULTIPLIERS.keys()):
        if streak_days >= threshold:
            multiplier = STREAK_MULTIPLIERS[threshold]
    return multiplier


def _apply_diminishing_returns(raw_xp: int) -> int:
    """Apply diminishing returns after DIMINISHING_THRESHOLD.

    First DIMINISHING_THRESHOLD XP at full rate, remainder at 50%.
    """
    if raw_xp <= DIMINISHING_THRESHOLD:
        return raw_xp
    excess = raw_xp - DIMINISHING_THRESHOLD
    return DIMINISHING_THRESHOLD + math.floor(excess * 0.5)


def _apply_daily_cap(xp: int) -> int:
    """Cap base XP at DAILY_XP_CAP."""
    return min(xp, DAILY_XP_CAP)


def _clamp_non_negative(value: int) -> int:
    """Treat negative values as 0."""
    return max(0, value)


def calculate_daily_xp(
    messages: int,
    sessions: int,
    tool_calls: int,
    projects: int = 0,
    edits: int = 0,
    commits: int = 0,
    is_first_session_of_day: bool = True,
    streak_days: int = 0,
) -> DailyXP:
    """Calculate XP for a single day.

    1. Calculate base XP from actions.
    2. Apply diminishing returns: after DIMINISHING_THRESHOLD, earn at 50% rate.
    3. Apply daily cap: max DAILY_XP_CAP base XP.
    4. Calculate multiplier from streak + first session bonus.
    5. Final XP = floor(capped_base_xp * multiplier).
    """
    messages = _clamp_non_negative(messages)
    sessions = _clamp_non_negative(sessions)
    tool_calls = _clamp_non_negative(tool_calls)
    projects = _clamp_non_negative(projects)
    edits = _clamp_non_negative(edits)
    commits = _clamp_non_negative(commits)

    # Calculate breakdown
    session_xp = sessions * XP_PER_SESSION
    message_xp = messages * XP_PER_MESSAGE
    tool_xp = tool_calls * XP_PER_TOOL_CALL
    project_xp = projects * XP_PER_PROJECT
    edit_xp = edits * XP_PER_EDIT
    commit_xp = commits * XP_PER_COMMIT

    breakdown: dict[str, int] = {
        "sessions": session_xp,
        "messages": message_xp,
        "tools": tool_xp,
        "projects": project_xp,
        "edits": edit_xp,
        "commits": commit_xp,
    }

    raw_xp = session_xp + message_xp + tool_xp + project_xp + edit_xp + commit_xp

    # Apply diminishing returns, then cap
    base_xp = _apply_daily_cap(_apply_diminishing_returns(raw_xp))

    # Calculate multiplier
    multiplier = get_streak_multiplier(streak_days)
    if is_first_session_of_day and sessions > 0:
        multiplier *= FIRST_SESSION_BONUS

    final_xp = math.floor(base_xp * multiplier)

    return DailyXP(
        date="",
        base_xp=base_xp,
        multiplier=multiplier,
        final_xp=final_xp,
        breakdown=breakdown,
    )


def calculate_total_xp(daily_xp_list: list[DailyXP]) -> int:
    """Sum all daily final_xp values."""
    return sum(day.final_xp for day in daily_xp_list)


def _count_streak(active_dates: set[str], current_date: str) -> int:
    """Count consecutive active days ending the day before current_date.

    Streak means how many consecutive days before today the user was active.
    If yesterday was not active, streak is 0.
    """
    from datetime import date, timedelta

    current = date.fromisoformat(current_date)
    streak = 0
    check_date = current - timedelta(days=1)
    while check_date.isoformat() in active_dates:
        streak += 1
        check_date -= timedelta(days=1)
    return streak


def calculate_historical_xp(daily_activities: list[dict], streak_data: dict) -> list[DailyXP]:
    """Calculate XP for a list of historical daily activities.

    Each daily_activity dict has: date, messageCount, sessionCount, toolCallCount
    streak_data has: active_dates set for streak calculation

    Process days chronologically to correctly calculate streaks and multipliers.
    """
    active_dates: set[str] = set(streak_data.get("active_dates", set()))

    # Sort chronologically
    sorted_activities = sorted(daily_activities, key=lambda d: d["date"])

    results: list[DailyXP] = []
    for activity in sorted_activities:
        day_date = activity["date"]
        messages = activity.get("messageCount", 0)
        sessions = activity.get("sessionCount", 0)
        tool_calls = activity.get("toolCallCount", 0)
        projects = activity.get("projectCount", 0)
        edits = activity.get("editCount", 0)
        commits = activity.get("commitCount", 0)

        streak = _count_streak(active_dates, day_date)

        daily = calculate_daily_xp(
            messages=messages,
            sessions=sessions,
            tool_calls=tool_calls,
            projects=projects,
            edits=edits,
            commits=commits,
            is_first_session_of_day=True,
            streak_days=streak,
        )
        daily.date = day_date

        # Add this day to active dates if there was meaningful activity
        if sessions > 0 and tool_calls >= MIN_TOOL_CALLS_FOR_SESSION_XP:
            active_dates.add(day_date)

        results.append(daily)

    return results
