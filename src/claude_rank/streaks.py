"""Streak tracking and freeze logic for claude-rank."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, timedelta


@dataclass
class StreakInfo:
    current_streak: int
    longest_streak: int
    freeze_count: int  # available freezes (max 3)
    last_active_date: str | None  # YYYY-MM-DD
    is_active_today: bool


def _parse_date(d: str) -> date:
    """Parse a YYYY-MM-DD string to a date object."""
    return date.fromisoformat(d)


def get_streak_from_dates(sorted_dates: list[str], reference_date: str) -> int:
    """Given a sorted list of active dates and a reference date,
    count consecutive days backwards from reference_date."""
    if not sorted_dates:
        return 0

    ref = _parse_date(reference_date)
    date_set = {_parse_date(d) for d in sorted_dates}

    if ref not in date_set:
        return 0

    streak = 0
    current = ref
    while current in date_set:
        streak += 1
        current -= timedelta(days=1)

    return streak


def calculate_streak(active_dates: set[str], today: str | None = None) -> StreakInfo:
    """Calculate current streak from a set of active date strings (YYYY-MM-DD).

    Rules:
    - Active day = date string present in active_dates
    - Streak = consecutive days ending at today (or most recent active day)
    - Today counts if present
    - Yesterday must be present for streak > 1
    """
    if not active_dates:
        return StreakInfo(
            current_streak=0,
            longest_streak=0,
            freeze_count=0,
            last_active_date=None,
            is_active_today=False,
        )

    today_date = _parse_date(today) if today else date.today()
    sorted_dates = sorted(active_dates)
    date_set = {_parse_date(d) for d in active_dates}

    is_active_today = today_date in date_set
    last_active = sorted_dates[-1]

    # Calculate current streak: count backwards from today or yesterday
    if is_active_today:
        current_streak = get_streak_from_dates(sorted_dates, today or today_date.isoformat())
    else:
        # Check if yesterday was active - streak continues from yesterday
        yesterday = (today_date - timedelta(days=1)).isoformat()
        if yesterday in active_dates:
            current_streak = get_streak_from_dates(sorted_dates, yesterday)
        else:
            current_streak = 0

    # Calculate longest streak over all dates
    longest = 0
    if sorted_dates:
        streak = 1
        for i in range(1, len(sorted_dates)):
            prev = _parse_date(sorted_dates[i - 1])
            curr = _parse_date(sorted_dates[i])
            if (curr - prev).days == 1:
                streak += 1
            else:
                longest = max(longest, streak)
                streak = 1
        longest = max(longest, streak)

    longest = max(longest, current_streak)

    freeze_count = earn_freeze(longest, 0)

    return StreakInfo(
        current_streak=current_streak,
        longest_streak=longest,
        freeze_count=freeze_count,
        last_active_date=last_active,
        is_active_today=is_active_today,
    )


def apply_freeze(streak_info: StreakInfo, missed_date: str) -> StreakInfo:
    """Apply a streak freeze for a missed day.

    Rules:
    - If freeze_count > 0: decrement freeze, preserve streak (don't increment it)
    - If freeze_count == 0: streak breaks
    - Return updated StreakInfo
    """
    if streak_info.freeze_count > 0:
        return StreakInfo(
            current_streak=streak_info.current_streak,
            longest_streak=streak_info.longest_streak,
            freeze_count=streak_info.freeze_count - 1,
            last_active_date=streak_info.last_active_date,
            is_active_today=False,
        )
    else:
        return StreakInfo(
            current_streak=0,
            longest_streak=streak_info.longest_streak,
            freeze_count=0,
            last_active_date=streak_info.last_active_date,
            is_active_today=False,
        )


def apply_grace_period(streak_info: StreakInfo, hours_since_last_active: float) -> StreakInfo:
    """Apply grace period rules.

    - Within 24h: streak fully restored
    - Within 48h: streak reduced by 25% (floor)
    - After 48h: streak resets to 0
    """
    if hours_since_last_active <= 24:
        return StreakInfo(
            current_streak=streak_info.current_streak,
            longest_streak=streak_info.longest_streak,
            freeze_count=streak_info.freeze_count,
            last_active_date=streak_info.last_active_date,
            is_active_today=streak_info.is_active_today,
        )
    elif hours_since_last_active <= 48:
        reduced = math.floor(streak_info.current_streak * 0.75)
        return StreakInfo(
            current_streak=reduced,
            longest_streak=streak_info.longest_streak,
            freeze_count=streak_info.freeze_count,
            last_active_date=streak_info.last_active_date,
            is_active_today=streak_info.is_active_today,
        )
    else:
        return StreakInfo(
            current_streak=0,
            longest_streak=streak_info.longest_streak,
            freeze_count=streak_info.freeze_count,
            last_active_date=streak_info.last_active_date,
            is_active_today=streak_info.is_active_today,
        )


def earn_freeze(current_streak: int, current_freezes: int) -> int:
    """Calculate freeze earnings.

    - Earn 1 freeze per 7-day streak milestone (7, 14, 21, ...)
    - Max 3 freezes stored
    - Return new freeze count
    """
    earned = current_streak // 7
    return min(current_freezes + earned, 3)
