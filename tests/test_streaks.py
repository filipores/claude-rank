"""Tests for the streak tracking system."""

from claude_rank.streaks import (
    StreakInfo,
    apply_freeze,
    apply_grace_period,
    calculate_streak,
    earn_freeze,
    get_streak_from_dates,
)


class TestGetStreakFromDates:
    """Tests for get_streak_from_dates function."""

    def test_consecutive_five_days(self):
        dates = ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04", "2026-01-05"]
        assert get_streak_from_dates(dates, "2026-01-05") == 5

    def test_reference_not_in_dates(self):
        dates = ["2026-01-01", "2026-01-02"]
        assert get_streak_from_dates(dates, "2026-01-05") == 0

    def test_single_date(self):
        dates = ["2026-01-01"]
        assert get_streak_from_dates(dates, "2026-01-01") == 1

    def test_gap_breaks_streak(self):
        dates = ["2026-01-01", "2026-01-02", "2026-01-04", "2026-01-05"]
        assert get_streak_from_dates(dates, "2026-01-05") == 2

    def test_empty_dates(self):
        assert get_streak_from_dates([], "2026-01-01") == 0

    def test_streak_from_middle(self):
        dates = ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-05"]
        assert get_streak_from_dates(dates, "2026-01-03") == 3


class TestCalculateStreak:
    """Tests for calculate_streak function."""

    def test_five_consecutive_days(self):
        dates = {"2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04", "2026-01-05"}
        result = calculate_streak(dates, today="2026-01-05")
        assert result.current_streak == 5
        assert result.is_active_today is True

    def test_gap_in_dates(self):
        dates = {"2026-01-01", "2026-01-02", "2026-01-04", "2026-01-05"}
        result = calculate_streak(dates, today="2026-01-05")
        assert result.current_streak == 2

    def test_today_not_active_yesterday_active(self):
        dates = {"2026-01-01", "2026-01-02", "2026-01-03"}
        result = calculate_streak(dates, today="2026-01-04")
        assert result.current_streak == 3
        assert result.is_active_today is False

    def test_today_not_active_gap_before(self):
        dates = {"2026-01-01", "2026-01-02"}
        result = calculate_streak(dates, today="2026-01-05")
        assert result.current_streak == 0
        assert result.is_active_today is False

    def test_empty_dates(self):
        result = calculate_streak(set())
        assert result.current_streak == 0
        assert result.longest_streak == 0
        assert result.freeze_count == 0
        assert result.last_active_date is None
        assert result.is_active_today is False

    def test_single_date_is_today(self):
        result = calculate_streak({"2026-01-05"}, today="2026-01-05")
        assert result.current_streak == 1
        assert result.longest_streak == 1
        assert result.is_active_today is True

    def test_longest_streak_tracked(self):
        # Old streak of 4, then gap, then current streak of 2
        dates = {
            "2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04",
            "2026-01-10", "2026-01-11",
        }
        result = calculate_streak(dates, today="2026-01-11")
        assert result.current_streak == 2
        assert result.longest_streak == 4

    def test_last_active_date(self):
        dates = {"2026-01-01", "2026-01-03", "2026-01-05"}
        result = calculate_streak(dates, today="2026-01-05")
        assert result.last_active_date == "2026-01-05"

    def test_freeze_count_earned_from_longest_streak(self):
        # 14-day streak -> 2 freezes earned
        dates = {f"2026-01-{d:02d}" for d in range(1, 15)}
        result = calculate_streak(dates, today="2026-01-14")
        assert result.freeze_count == 2

    def test_current_streak_exceeds_historical_longest(self):
        dates = {"2026-01-01", "2026-01-02", "2026-01-03"}
        result = calculate_streak(dates, today="2026-01-03")
        assert result.current_streak == 3
        assert result.longest_streak == 3


class TestApplyFreeze:
    """Tests for apply_freeze function."""

    def test_freeze_preserves_streak(self):
        info = StreakInfo(current_streak=5, longest_streak=10, freeze_count=2, last_active_date="2026-01-05", is_active_today=True)
        result = apply_freeze(info, "2026-01-06")
        assert result.current_streak == 5
        assert result.freeze_count == 1
        assert result.is_active_today is False

    def test_freeze_decrements_count(self):
        info = StreakInfo(current_streak=5, longest_streak=10, freeze_count=3, last_active_date="2026-01-05", is_active_today=True)
        result = apply_freeze(info, "2026-01-06")
        assert result.freeze_count == 2

    def test_no_freeze_breaks_streak(self):
        info = StreakInfo(current_streak=5, longest_streak=10, freeze_count=0, last_active_date="2026-01-05", is_active_today=True)
        result = apply_freeze(info, "2026-01-06")
        assert result.current_streak == 0
        assert result.freeze_count == 0

    def test_freeze_preserves_longest_streak(self):
        info = StreakInfo(current_streak=5, longest_streak=10, freeze_count=1, last_active_date="2026-01-05", is_active_today=True)
        result = apply_freeze(info, "2026-01-06")
        assert result.longest_streak == 10

    def test_last_freeze_used(self):
        info = StreakInfo(current_streak=5, longest_streak=10, freeze_count=1, last_active_date="2026-01-05", is_active_today=True)
        result = apply_freeze(info, "2026-01-06")
        assert result.freeze_count == 0
        assert result.current_streak == 5


class TestApplyGracePeriod:
    """Tests for apply_grace_period function."""

    def test_within_24h_full_restore(self):
        info = StreakInfo(current_streak=10, longest_streak=10, freeze_count=0, last_active_date="2026-01-05", is_active_today=False)
        result = apply_grace_period(info, 20.0)
        assert result.current_streak == 10

    def test_exactly_24h_full_restore(self):
        info = StreakInfo(current_streak=10, longest_streak=10, freeze_count=0, last_active_date="2026-01-05", is_active_today=False)
        result = apply_grace_period(info, 24.0)
        assert result.current_streak == 10

    def test_within_48h_reduces_by_25_percent(self):
        info = StreakInfo(current_streak=10, longest_streak=10, freeze_count=0, last_active_date="2026-01-05", is_active_today=False)
        result = apply_grace_period(info, 30.0)
        assert result.current_streak == 7  # floor(10 * 0.75) = 7

    def test_exactly_48h_reduces(self):
        info = StreakInfo(current_streak=10, longest_streak=10, freeze_count=0, last_active_date="2026-01-05", is_active_today=False)
        result = apply_grace_period(info, 48.0)
        assert result.current_streak == 7

    def test_after_48h_resets(self):
        info = StreakInfo(current_streak=10, longest_streak=10, freeze_count=0, last_active_date="2026-01-05", is_active_today=False)
        result = apply_grace_period(info, 49.0)
        assert result.current_streak == 0

    def test_grace_preserves_longest_streak(self):
        info = StreakInfo(current_streak=10, longest_streak=20, freeze_count=2, last_active_date="2026-01-05", is_active_today=False)
        result = apply_grace_period(info, 100.0)
        assert result.longest_streak == 20

    def test_grace_preserves_freeze_count(self):
        info = StreakInfo(current_streak=10, longest_streak=10, freeze_count=2, last_active_date="2026-01-05", is_active_today=False)
        result = apply_grace_period(info, 100.0)
        assert result.freeze_count == 2

    def test_reduction_floors_result(self):
        info = StreakInfo(current_streak=3, longest_streak=3, freeze_count=0, last_active_date="2026-01-05", is_active_today=False)
        result = apply_grace_period(info, 30.0)
        assert result.current_streak == 2  # floor(3 * 0.75) = 2

    def test_zero_hours(self):
        info = StreakInfo(current_streak=5, longest_streak=5, freeze_count=0, last_active_date="2026-01-05", is_active_today=False)
        result = apply_grace_period(info, 0.0)
        assert result.current_streak == 5


class TestEarnFreeze:
    """Tests for earn_freeze function."""

    def test_7_day_streak_earns_one(self):
        assert earn_freeze(7, 0) == 1

    def test_14_day_streak_earns_two(self):
        assert earn_freeze(14, 0) == 2

    def test_21_day_streak_earns_three(self):
        assert earn_freeze(21, 0) == 3

    def test_max_three_freezes(self):
        assert earn_freeze(100, 0) == 3

    def test_existing_freezes_add(self):
        assert earn_freeze(7, 2) == 3

    def test_existing_freezes_capped(self):
        assert earn_freeze(7, 3) == 3

    def test_less_than_7_days_no_freeze(self):
        assert earn_freeze(6, 0) == 0

    def test_zero_streak_no_freeze(self):
        assert earn_freeze(0, 0) == 0

    def test_zero_streak_preserves_existing(self):
        assert earn_freeze(0, 2) == 2
