"""Tests for XP calculation engine."""

from claude_rank.xp import (
    DAILY_XP_CAP,
    DIMINISHING_THRESHOLD,
    DailyXP,
    calculate_daily_xp,
    calculate_historical_xp,
    calculate_total_xp,
    get_streak_multiplier,
)


class TestBasicXPCalculation:
    """Test basic XP calculation without multipliers."""

    def test_basic_calculation(self) -> None:
        """3 sessions, 80 messages, 180 tool calls -> 470 base XP."""
        result = calculate_daily_xp(
            messages=80,
            sessions=3,
            tool_calls=180,
            is_first_session_of_day=False,
            streak_days=0,
        )
        # 3*10 + 80*1 + 180*2 = 30 + 80 + 360 = 470
        assert result.base_xp == 470
        assert result.final_xp == 470
        assert result.multiplier == 1.0
        assert result.breakdown["sessions"] == 30
        assert result.breakdown["messages"] == 80
        assert result.breakdown["tools"] == 360

    def test_breakdown_includes_all_categories(self) -> None:
        result = calculate_daily_xp(
            messages=10,
            sessions=1,
            tool_calls=20,
            projects=2,
            edits=5,
            commits=1,
            is_first_session_of_day=False,
            streak_days=0,
        )
        assert result.breakdown["sessions"] == 10
        assert result.breakdown["messages"] == 10
        assert result.breakdown["tools"] == 40
        assert result.breakdown["projects"] == 10
        assert result.breakdown["edits"] == 15
        assert result.breakdown["commits"] == 5
        # Total raw = 10+10+40+10+15+5 = 90
        assert result.base_xp == 90
        assert result.final_xp == 90


class TestDiminishingReturns:
    """Test diminishing returns after threshold."""

    def test_below_threshold_full_rate(self) -> None:
        """Under 500 XP: no diminishing returns."""
        result = calculate_daily_xp(
            messages=100,
            sessions=2,
            tool_calls=100,
            is_first_session_of_day=False,
            streak_days=0,
        )
        # 2*10 + 100*1 + 100*2 = 20+100+200 = 320
        assert result.base_xp == 320

    def test_above_threshold_diminishing(self) -> None:
        """5 sessions, 200 messages, 300 tool calls -> diminishing returns."""
        result = calculate_daily_xp(
            messages=200,
            sessions=5,
            tool_calls=300,
            is_first_session_of_day=False,
            streak_days=0,
        )
        # Raw = 5*10 + 200*1 + 300*2 = 50 + 200 + 600 = 850
        # After diminishing: 500 + floor((850-500) * 0.5) = 500 + 175 = 675
        assert result.base_xp == 675

    def test_exactly_at_threshold(self) -> None:
        """Exactly 500 XP: no diminishing returns applied."""
        result = calculate_daily_xp(
            messages=100,
            sessions=0,
            tool_calls=200,
            is_first_session_of_day=False,
            streak_days=0,
        )
        # 0 + 100 + 400 = 500
        assert result.base_xp == DIMINISHING_THRESHOLD


class TestDailyCap:
    """Test daily XP cap."""

    def test_massive_activity_capped(self) -> None:
        """Massive activity still capped at 800."""
        result = calculate_daily_xp(
            messages=500,
            sessions=10,
            tool_calls=800,
            is_first_session_of_day=False,
            streak_days=0,
        )
        # Raw = 100 + 500 + 1600 = 2200
        # After diminishing: 500 + floor(1700 * 0.5) = 500 + 850 = 1350
        # After cap: 800
        assert result.base_xp == DAILY_XP_CAP

    def test_just_under_cap(self) -> None:
        """Activity just under the cap stays unchanged."""
        # Need base_xp after diminishing to be 799
        # First 500 at full rate + X at 50% = 799
        # X at 50% = 299 -> X = 598 -> raw excess = 598
        # raw = 500 + 598 = 1098
        # sessions=0, messages=98, tool_calls=500 -> 0+98+1000 = 1098
        result = calculate_daily_xp(
            messages=98,
            sessions=0,
            tool_calls=500,
            is_first_session_of_day=False,
            streak_days=0,
        )
        # Raw = 98 + 1000 = 1098
        # After diminishing: 500 + floor(598 * 0.5) = 500 + 299 = 799
        assert result.base_xp == 799
        assert result.base_xp < DAILY_XP_CAP


class TestStreakMultiplier:
    """Test streak multiplier calculation."""

    def test_no_streak(self) -> None:
        assert get_streak_multiplier(0) == 1.0

    def test_below_7_day_threshold(self) -> None:
        assert get_streak_multiplier(6) == 1.0

    def test_7_day_streak(self) -> None:
        assert get_streak_multiplier(7) == 1.25

    def test_10_day_streak(self) -> None:
        """Between 7 and 14: use 7-day tier."""
        assert get_streak_multiplier(10) == 1.25

    def test_14_day_streak(self) -> None:
        assert get_streak_multiplier(14) == 1.5

    def test_20_day_streak(self) -> None:
        """Between 14 and 30: use 14-day tier."""
        assert get_streak_multiplier(20) == 1.5

    def test_30_day_streak(self) -> None:
        assert get_streak_multiplier(30) == 2.0

    def test_100_day_streak(self) -> None:
        """Beyond 30: still 2.0x."""
        assert get_streak_multiplier(100) == 2.0

    def test_streak_applied_to_daily_xp(self) -> None:
        """7-day streak on 400 base XP -> floor(400 * 1.25) = 500."""
        result = calculate_daily_xp(
            messages=100,
            sessions=0,
            tool_calls=150,
            is_first_session_of_day=False,
            streak_days=7,
        )
        # Raw = 100 + 300 = 400
        assert result.base_xp == 400
        assert result.multiplier == 1.25
        assert result.final_xp == 500


class TestFirstSessionBonus:
    """Test first session of day bonus."""

    def test_first_session_bonus_applied(self) -> None:
        """First session bonus: 1.5x."""
        result = calculate_daily_xp(
            messages=80,
            sessions=3,
            tool_calls=180,
            is_first_session_of_day=True,
            streak_days=0,
        )
        # Base = 470 (below threshold)
        # Multiplier = 1.0 * 1.5 (first session) = 1.5
        assert result.multiplier == 1.5
        assert result.final_xp == 705  # floor(470 * 1.5)

    def test_first_session_no_bonus_when_no_sessions(self) -> None:
        """First session bonus requires at least 1 session."""
        result = calculate_daily_xp(
            messages=80,
            sessions=0,
            tool_calls=180,
            is_first_session_of_day=True,
            streak_days=0,
        )
        assert result.multiplier == 1.0

    def test_first_session_stacks_with_streak(self) -> None:
        """7-day streak + first session = 1.25 * 1.5 = 1.875x."""
        result = calculate_daily_xp(
            messages=80,
            sessions=3,
            tool_calls=180,
            is_first_session_of_day=True,
            streak_days=7,
        )
        # Base = 470
        assert result.multiplier == 1.25 * 1.5  # 1.875
        assert result.final_xp == 881  # floor(470 * 1.875)

    def test_first_session_stacks_with_30_day_streak(self) -> None:
        """30-day streak + first session = 2.0 * 1.5 = 3.0x."""
        result = calculate_daily_xp(
            messages=100,
            sessions=1,
            tool_calls=150,
            is_first_session_of_day=True,
            streak_days=30,
        )
        # Raw = 10 + 100 + 300 = 410
        assert result.base_xp == 410
        assert result.multiplier == 3.0
        assert result.final_xp == 1230  # floor(410 * 3.0)


class TestHistoricalCalculation:
    """Test historical XP calculation with streak progression."""

    def test_basic_historical(self) -> None:
        """5 consecutive days of activity."""
        activities = [
            {"date": "2025-01-01", "messageCount": 50, "sessionCount": 2, "toolCallCount": 100},
            {"date": "2025-01-02", "messageCount": 50, "sessionCount": 2, "toolCallCount": 100},
            {"date": "2025-01-03", "messageCount": 50, "sessionCount": 2, "toolCallCount": 100},
            {"date": "2025-01-04", "messageCount": 50, "sessionCount": 2, "toolCallCount": 100},
            {"date": "2025-01-05", "messageCount": 50, "sessionCount": 2, "toolCallCount": 100},
        ]
        streak_data: dict = {"active_dates": set()}

        results = calculate_historical_xp(activities, streak_data)
        assert len(results) == 5
        # All should have dates set
        assert results[0].date == "2025-01-01"
        assert results[4].date == "2025-01-05"

    def test_streak_builds_over_time(self) -> None:
        """Streak builds day by day: day 1 has no streak, day 8 has 7-day streak."""
        activities = []
        for day in range(1, 10):
            activities.append({
                "date": f"2025-01-{day:02d}",
                "messageCount": 50,
                "sessionCount": 2,
                "toolCallCount": 100,
            })
        streak_data: dict = {"active_dates": set()}

        results = calculate_historical_xp(activities, streak_data)

        # Day 1: streak=0, no bonus
        assert results[0].multiplier == 1.5  # first session only
        # Day 7: streak=6, no 7-day bonus yet (need 7 consecutive previous days)
        assert get_streak_multiplier(6) == 1.0
        # Day 8: streak=7, 1.25x streak kicks in
        assert results[7].multiplier == 1.25 * 1.5  # streak + first session

    def test_historical_with_existing_active_dates(self) -> None:
        """Pre-existing active dates affect streak calculation."""
        activities = [
            {"date": "2025-01-08", "messageCount": 50, "sessionCount": 2, "toolCallCount": 100},
        ]
        # 7 previous consecutive days already recorded
        streak_data = {
            "active_dates": {
                "2025-01-01",
                "2025-01-02",
                "2025-01-03",
                "2025-01-04",
                "2025-01-05",
                "2025-01-06",
                "2025-01-07",
            }
        }

        results = calculate_historical_xp(activities, streak_data)
        # 7 consecutive previous days -> streak=7 -> 1.25x
        assert results[0].multiplier == 1.25 * 1.5

    def test_historical_chronological_order(self) -> None:
        """Activities are processed in chronological order regardless of input order."""
        activities = [
            {"date": "2025-01-03", "messageCount": 50, "sessionCount": 2, "toolCallCount": 100},
            {"date": "2025-01-01", "messageCount": 50, "sessionCount": 2, "toolCallCount": 100},
            {"date": "2025-01-02", "messageCount": 50, "sessionCount": 2, "toolCallCount": 100},
        ]
        streak_data: dict = {"active_dates": set()}

        results = calculate_historical_xp(activities, streak_data)
        # Should be sorted chronologically
        assert results[0].date == "2025-01-01"
        assert results[1].date == "2025-01-02"
        assert results[2].date == "2025-01-03"

    def test_gap_in_activity_resets_streak(self) -> None:
        """A gap in activity resets the streak."""
        activities = [
            {"date": "2025-01-01", "messageCount": 50, "sessionCount": 2, "toolCallCount": 100},
            {"date": "2025-01-02", "messageCount": 50, "sessionCount": 2, "toolCallCount": 100},
            # Gap on Jan 3
            {"date": "2025-01-04", "messageCount": 50, "sessionCount": 2, "toolCallCount": 100},
        ]
        streak_data: dict = {"active_dates": set()}

        results = calculate_historical_xp(activities, streak_data)
        # Day 3 (Jan 4): Jan 3 not active, streak resets to 0
        # Multiplier is just first session bonus
        assert results[2].multiplier == 1.5  # first session only, no streak


class TestCalculateTotalXP:
    """Test total XP summation."""

    def test_sum_of_daily_xp(self) -> None:
        daily_list = [
            DailyXP(date="2025-01-01", base_xp=100, multiplier=1.0, final_xp=100, breakdown={}),
            DailyXP(date="2025-01-02", base_xp=200, multiplier=1.5, final_xp=300, breakdown={}),
            DailyXP(date="2025-01-03", base_xp=150, multiplier=1.25, final_xp=187, breakdown={}),
        ]
        assert calculate_total_xp(daily_list) == 587

    def test_empty_list(self) -> None:
        assert calculate_total_xp([]) == 0


class TestEdgeCases:
    """Test edge cases."""

    def test_zero_activity(self) -> None:
        result = calculate_daily_xp(
            messages=0,
            sessions=0,
            tool_calls=0,
            is_first_session_of_day=False,
            streak_days=0,
        )
        assert result.base_xp == 0
        assert result.final_xp == 0
        assert result.multiplier == 1.0

    def test_negative_values_treated_as_zero(self) -> None:
        result = calculate_daily_xp(
            messages=-10,
            sessions=-5,
            tool_calls=-100,
            is_first_session_of_day=False,
            streak_days=0,
        )
        assert result.base_xp == 0
        assert result.final_xp == 0

    def test_very_large_values_still_capped(self) -> None:
        result = calculate_daily_xp(
            messages=100000,
            sessions=1000,
            tool_calls=100000,
            is_first_session_of_day=False,
            streak_days=0,
        )
        assert result.base_xp == DAILY_XP_CAP

    def test_large_values_with_multiplier(self) -> None:
        """Capped base XP still gets multiplied."""
        result = calculate_daily_xp(
            messages=100000,
            sessions=1000,
            tool_calls=100000,
            is_first_session_of_day=True,
            streak_days=30,
        )
        assert result.base_xp == DAILY_XP_CAP
        # 2.0 * 1.5 = 3.0x
        assert result.final_xp == DAILY_XP_CAP * 3  # 800 * 3 = 2400

    def test_integer_rounding(self) -> None:
        """Verify floor rounding for fractional results."""
        result = calculate_daily_xp(
            messages=33,
            sessions=1,
            tool_calls=50,
            is_first_session_of_day=True,
            streak_days=7,
        )
        # Raw = 10 + 33 + 100 = 143
        # Multiplier = 1.25 * 1.5 = 1.875
        # final = floor(143 * 1.875) = floor(268.125) = 268
        assert result.final_xp == 268

    def test_historical_empty_activities(self) -> None:
        results = calculate_historical_xp([], {"active_dates": set()})
        assert results == []

    def test_historical_low_tool_calls_no_streak_credit(self) -> None:
        """Sessions with <5 tool calls don't count for streak building."""
        activities = [
            {"date": "2025-01-01", "messageCount": 10, "sessionCount": 1, "toolCallCount": 3},
            {"date": "2025-01-02", "messageCount": 10, "sessionCount": 1, "toolCallCount": 3},
            {"date": "2025-01-03", "messageCount": 10, "sessionCount": 1, "toolCallCount": 100},
        ]
        streak_data: dict = {"active_dates": set()}

        results = calculate_historical_xp(activities, streak_data)
        # Day 1 and 2 don't qualify (tool_calls < 5)
        # Day 3 has streak=0 because previous days weren't "active"
        # Multiplier is just first session bonus since sessions > 0
        assert results[2].multiplier == 1.5  # first session only, no streak
