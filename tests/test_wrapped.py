from claude_rank.wrapped import get_period_dates, aggregate_wrapped, _calculate_period_streak


class TestGetPeriodDates:
    def test_month_january(self):
        start, end = get_period_dates("month", today="2026-01-15")
        assert start == "2026-01-01"
        assert end == "2026-01-31"

    def test_month_february_non_leap(self):
        start, end = get_period_dates("month", today="2026-02-10")
        assert start == "2026-02-01"
        assert end == "2026-02-28"

    def test_month_december(self):
        start, end = get_period_dates("month", today="2026-12-25")
        assert start == "2026-12-01"
        assert end == "2026-12-31"

    def test_year(self):
        start, end = get_period_dates("year", today="2026-06-15")
        assert start == "2026-01-01"
        assert end == "2026-12-31"

    def test_all_time(self):
        start, end = get_period_dates("all-time", today="2026-02-24")
        assert start == "0000-01-01"
        assert end == "2026-02-24"


class TestCalculatePeriodStreak:
    def test_empty_list(self):
        assert _calculate_period_streak([]) == 0

    def test_no_streak_days(self):
        stats = [{"date": "2026-01-01", "streak_day": False}]
        assert _calculate_period_streak(stats) == 0

    def test_single_day(self):
        stats = [{"date": "2026-01-01", "streak_day": True}]
        assert _calculate_period_streak(stats) == 1

    def test_consecutive_days(self):
        stats = [
            {"date": "2026-01-01", "streak_day": True},
            {"date": "2026-01-02", "streak_day": True},
            {"date": "2026-01-03", "streak_day": True},
        ]
        assert _calculate_period_streak(stats) == 3

    def test_gap_resets_streak(self):
        stats = [
            {"date": "2026-01-01", "streak_day": True},
            {"date": "2026-01-02", "streak_day": True},
            {"date": "2026-01-04", "streak_day": True},
            {"date": "2026-01-05", "streak_day": True},
            {"date": "2026-01-06", "streak_day": True},
        ]
        assert _calculate_period_streak(stats) == 3

    def test_mixed_streak_and_non_streak(self):
        stats = [
            {"date": "2026-01-01", "streak_day": True},
            {"date": "2026-01-02", "streak_day": False},
            {"date": "2026-01-03", "streak_day": True},
        ]
        assert _calculate_period_streak(stats) == 1


class TestAggregateWrapped:
    def test_empty_stats_returns_empty_summary(self):
        result = aggregate_wrapped([], {"level": "5", "total_xp": "1000"})
        assert result["total_xp_earned"] == 0
        assert result["current_level"] == 5

    def test_basic_aggregation(self):
        stats = [
            {"date": "2026-01-01", "total_xp": 100, "messages": 10, "sessions": 2, "tool_calls": 20, "streak_day": True},
            {"date": "2026-01-02", "total_xp": 200, "messages": 20, "sessions": 3, "tool_calls": 30, "streak_day": True},
        ]
        profile = {"level": "10", "total_xp": "5000", "longest_streak": "7", "prestige_count": "0"}
        result = aggregate_wrapped(stats, profile)
        assert result["total_xp_earned"] == 300
        assert result["total_messages"] == 30
        assert result["total_sessions"] == 5
        assert result["total_tool_calls"] == 50
        assert result["active_days"] == 2

    def test_busiest_day(self):
        stats = [
            {"date": "2026-01-01", "total_xp": 100, "messages": 0, "sessions": 0, "tool_calls": 0, "streak_day": True},
            {"date": "2026-01-02", "total_xp": 500, "messages": 0, "sessions": 0, "tool_calls": 0, "streak_day": True},
        ]
        result = aggregate_wrapped(stats, {})
        assert result["busiest_day"] == "2026-01-02"
        assert result["busiest_day_xp"] == 500

    def test_top_tools(self):
        stats = [
            {"date": "2026-01-01", "total_xp": 100, "messages": 0, "sessions": 0, "tool_calls": 0, "streak_day": True},
        ]
        tool_usage = {"Edit": 500, "Bash": 300, "Read": 200, "Write": 100, "Grep": 50, "Glob": 25}
        result = aggregate_wrapped(stats, {}, tool_usage=tool_usage)
        assert len(result["top_tools"]) == 5
        assert result["top_tools"][0] == ("Edit", 500)

    def test_busiest_hour(self):
        stats = [
            {"date": "2026-01-01", "total_xp": 100, "messages": 0, "sessions": 0, "tool_calls": 0, "streak_day": True},
        ]
        hours = [0] * 24
        hours[14] = 10
        result = aggregate_wrapped(stats, {}, hour_counts=hours)
        assert result["busiest_hour"] == 14

    def test_avg_xp_per_day(self):
        stats = [
            {"date": "2026-01-01", "total_xp": 100, "messages": 0, "sessions": 0, "tool_calls": 0, "streak_day": True},
            {"date": "2026-01-02", "total_xp": 200, "messages": 0, "sessions": 0, "tool_calls": 0, "streak_day": True},
            {"date": "2026-01-03", "total_xp": 0, "messages": 0, "sessions": 0, "tool_calls": 0, "streak_day": False},
        ]
        result = aggregate_wrapped(stats, {})
        assert result["avg_xp_per_day"] == 150  # 300 / 2 active days

    def test_projects_count(self):
        stats = [
            {"date": "2026-01-01", "total_xp": 100, "messages": 0, "sessions": 0, "tool_calls": 0, "streak_day": True},
        ]
        result = aggregate_wrapped(stats, {}, projects=["proj1", "proj2", "proj3"])
        assert result["projects_count"] == 3
