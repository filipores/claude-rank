"""Tests for the level and tier progression system."""

import math

from claude_rank.levels import (
    TIERS,
    MAX_LEVEL,
    cumulative_xp_for_level,
    level_from_xp,
    tier_from_level,
    xp_for_level,
    xp_progress_in_level,
)


class TestXpForLevel:
    def test_level_1(self):
        # floor(50 * 1^1.8 + 100 * 1) = floor(50 + 100) = 150
        assert xp_for_level(1) == 150

    def test_level_5(self):
        # floor(50 * 5^1.8 + 100 * 5) = floor(50 * 16.7194... + 500)
        expected = math.floor(50 * (5 ** 1.8) + 100 * 5)
        assert xp_for_level(5) == expected

    def test_level_10(self):
        expected = math.floor(50 * (10 ** 1.8) + 100 * 10)
        assert xp_for_level(10) == expected

    def test_level_50(self):
        expected = math.floor(50 * (50 ** 1.8) + 100 * 50)
        assert xp_for_level(50) == expected

    def test_level_0_returns_0(self):
        assert xp_for_level(0) == 0

    def test_negative_level_returns_0(self):
        assert xp_for_level(-5) == 0

    def test_increasing(self):
        """XP requirement should increase with level."""
        for lv in range(1, 50):
            assert xp_for_level(lv) < xp_for_level(lv + 1)


class TestCumulativeXpForLevel:
    def test_level_0(self):
        assert cumulative_xp_for_level(0) == 0

    def test_level_1(self):
        assert cumulative_xp_for_level(1) == xp_for_level(1)

    def test_level_3(self):
        expected = xp_for_level(1) + xp_for_level(2) + xp_for_level(3)
        assert cumulative_xp_for_level(3) == expected

    def test_negative(self):
        assert cumulative_xp_for_level(-1) == 0

    def test_monotonically_increasing(self):
        prev = 0
        for lv in range(1, 51):
            curr = cumulative_xp_for_level(lv)
            assert curr > prev
            prev = curr


class TestLevelFromXp:
    def test_zero_xp(self):
        assert level_from_xp(0) == 1

    def test_negative_xp(self):
        assert level_from_xp(-100) == 1

    def test_just_under_level_2(self):
        xp_needed = xp_for_level(1)
        assert level_from_xp(xp_needed - 1) == 1

    def test_exactly_level_2(self):
        xp_needed = cumulative_xp_for_level(1)
        assert level_from_xp(xp_needed) == 2

    def test_just_over_level_2(self):
        xp_needed = cumulative_xp_for_level(1)
        assert level_from_xp(xp_needed + 1) == 2

    def test_max_level_cap(self):
        huge_xp = 999_999_999
        assert level_from_xp(huge_xp) == MAX_LEVEL

    def test_level_progression(self):
        """Verify several known levels."""
        for target_level in [1, 5, 10, 20, 30, 40, 50]:
            if target_level == 1:
                assert level_from_xp(0) == 1
            else:
                xp = cumulative_xp_for_level(target_level - 1)
                assert level_from_xp(xp) == target_level


class TestTierFromLevel:
    def test_all_tiers(self):
        for tier_info in TIERS:
            low, high = tier_info["levels"]
            for lv in range(low, high + 1):
                result = tier_from_level(lv)
                assert result["tier"] == tier_info["tier"]
                assert result["name"] == tier_info["name"]

    def test_level_1_is_tier_1(self):
        tier = tier_from_level(1)
        assert tier["name"] == "Prompt Novice"
        assert tier["tier"] == 1

    def test_level_50_is_tier_10(self):
        tier = tier_from_level(50)
        assert tier["name"] == "Omega Coder"
        assert tier["tier"] == 10

    def test_level_below_1_clamps(self):
        tier = tier_from_level(0)
        assert tier["tier"] == 1

    def test_level_above_50_clamps(self):
        tier = tier_from_level(100)
        assert tier["tier"] == 10

    def test_tier_boundaries(self):
        assert tier_from_level(5)["tier"] == 1
        assert tier_from_level(6)["tier"] == 2
        assert tier_from_level(10)["tier"] == 2
        assert tier_from_level(11)["tier"] == 3
        assert tier_from_level(45)["tier"] == 9
        assert tier_from_level(46)["tier"] == 10


class TestXpProgressInLevel:
    def test_zero_xp(self):
        current, needed = xp_progress_in_level(0)
        assert current == 0
        assert needed == xp_for_level(1)

    def test_negative_xp(self):
        current, needed = xp_progress_in_level(-50)
        assert current == 0
        assert needed == xp_for_level(1)

    def test_midway_through_level(self):
        # Give exactly level 1 xp + half of level 2 xp
        xp_l1 = xp_for_level(1)
        xp_l2 = xp_for_level(2)
        total = xp_l1 + xp_l2 // 2
        current, needed = xp_progress_in_level(total)
        assert current == xp_l2 // 2
        assert needed == xp_l2

    def test_at_max_level(self):
        huge_xp = 999_999_999
        current, needed = xp_progress_in_level(huge_xp)
        assert needed == 0
        assert current > 0

    def test_just_leveled_up(self):
        # Exactly at level 2 boundary
        xp = cumulative_xp_for_level(1)
        current, needed = xp_progress_in_level(xp)
        assert current == 0
        assert needed == xp_for_level(2)
