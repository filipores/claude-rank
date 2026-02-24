"""Tests for the prestige system functions."""

from claude_rank.levels import (
    PRESTIGE_XP_THRESHOLD,
    MAX_LEVEL,
    can_prestige,
    cumulative_xp_for_level,
    get_prestige_xp,
    prestige_stars,
)


class TestPrestigeXpThreshold:
    def test_threshold_equals_cumulative_max_level(self):
        assert PRESTIGE_XP_THRESHOLD == cumulative_xp_for_level(MAX_LEVEL)

    def test_threshold_positive(self):
        assert PRESTIGE_XP_THRESHOLD > 0


class TestGetPrestigeXp:
    def test_no_prestige_returns_total(self):
        assert get_prestige_xp(1000, 0) == 1000

    def test_negative_prestige_returns_total(self):
        assert get_prestige_xp(1000, -1) == 1000

    def test_first_prestige_subtracts_threshold(self):
        xp = PRESTIGE_XP_THRESHOLD + 500
        assert get_prestige_xp(xp, 1) == 500

    def test_second_prestige_subtracts_twice(self):
        xp = PRESTIGE_XP_THRESHOLD * 2 + 100
        assert get_prestige_xp(xp, 2) == 100

    def test_exact_threshold_returns_zero(self):
        assert get_prestige_xp(PRESTIGE_XP_THRESHOLD, 1) == 0


class TestPrestigeStars:
    def test_zero_returns_empty(self):
        assert prestige_stars(0) == ""

    def test_negative_returns_empty(self):
        assert prestige_stars(-1) == ""

    def test_one_star(self):
        assert prestige_stars(1) == "★"

    def test_three_stars(self):
        assert prestige_stars(3) == "★★★"

    def test_five_stars(self):
        assert prestige_stars(5) == "★★★★★"


class TestCanPrestige:
    def test_not_enough_xp(self):
        assert can_prestige(PRESTIGE_XP_THRESHOLD - 1, 0) is False

    def test_exact_threshold(self):
        assert can_prestige(PRESTIGE_XP_THRESHOLD, 0) is True

    def test_above_threshold(self):
        assert can_prestige(PRESTIGE_XP_THRESHOLD + 1000, 0) is True

    def test_second_prestige_needs_double(self):
        assert can_prestige(PRESTIGE_XP_THRESHOLD * 2 - 1, 1) is False

    def test_second_prestige_exact(self):
        assert can_prestige(PRESTIGE_XP_THRESHOLD * 2, 1) is True

    def test_zero_xp(self):
        assert can_prestige(0, 0) is False
