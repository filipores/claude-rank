"""Tests for the achievement system."""

from claude_rank.achievements import (
    ACHIEVEMENTS,
    Rarity,
    check_achievements,
    get_closest_achievements,
    get_newly_unlocked,
)


class TestCheckAchievements:
    """Tests for check_achievements function."""

    def test_hello_world_unlocks_at_one_session(self):
        stats = {"total_sessions": 1}
        results = check_achievements(stats)
        hello = next(r for r in results if r.definition.id == "hello_world")
        assert hello.unlocked is True
        assert hello.progress == 1.0

    def test_centurion_unlocks_at_100_sessions(self):
        stats = {"total_sessions": 100}
        results = check_achievements(stats)
        centurion = next(r for r in results if r.definition.id == "centurion")
        assert centurion.unlocked is True
        assert centurion.progress == 1.0

    def test_centurion_half_progress(self):
        stats = {"total_sessions": 50}
        results = check_achievements(stats)
        centurion = next(r for r in results if r.definition.id == "centurion")
        assert centurion.unlocked is False
        assert centurion.progress == 0.5

    def test_thousand_voices_unlocks(self):
        stats = {"total_messages": 1000}
        results = check_achievements(stats)
        tv = next(r for r in results if r.definition.id == "thousand_voices")
        assert tv.unlocked is True

    def test_tool_master_unlocks(self):
        stats = {"total_tool_calls": 10000}
        results = check_achievements(stats)
        tm = next(r for r in results if r.definition.id == "tool_master")
        assert tm.unlocked is True

    def test_night_owl_unlocks(self):
        stats = {"night_sessions": 1}
        results = check_achievements(stats)
        no = next(r for r in results if r.definition.id == "night_owl")
        assert no.unlocked is True

    def test_early_bird_unlocks(self):
        stats = {"early_sessions": 1}
        results = check_achievements(stats)
        eb = next(r for r in results if r.definition.id == "early_bird")
        assert eb.unlocked is True

    def test_on_fire_unlocks_at_7_day_streak(self):
        stats = {"current_streak": 7}
        results = check_achievements(stats)
        of = next(r for r in results if r.definition.id == "on_fire")
        assert of.unlocked is True

    def test_iron_will_unlocks_at_30_day_streak(self):
        stats = {"longest_streak": 30}
        results = check_achievements(stats)
        iw = next(r for r in results if r.definition.id == "iron_will")
        assert iw.unlocked is True

    def test_polyglot_unlocks_at_5_projects(self):
        stats = {"unique_projects": 5}
        results = check_achievements(stats)
        pg = next(r for r in results if r.definition.id == "polyglot")
        assert pg.unlocked is True

    def test_marathon_runner_unlocks(self):
        stats = {"longest_session_messages": 100}
        results = check_achievements(stats)
        mr = next(r for r in results if r.definition.id == "marathon_runner")
        assert mr.unlocked is True

    # --- New achievement unlock tests ---

    def test_veteran_unlocks(self):
        stats = {"total_sessions": 500}
        results = check_achievements(stats)
        ach = next(r for r in results if r.definition.id == "veteran")
        assert ach.unlocked is True

    def test_veteran_not_unlocked(self):
        stats = {"total_sessions": 499}
        results = check_achievements(stats)
        ach = next(r for r in results if r.definition.id == "veteran")
        assert ach.unlocked is False

    def test_ten_thousand_voices_unlocks(self):
        stats = {"total_messages": 10000}
        results = check_achievements(stats)
        ach = next(r for r in results if r.definition.id == "ten_thousand_voices")
        assert ach.unlocked is True

    def test_ten_thousand_voices_not_unlocked(self):
        stats = {"total_messages": 9999}
        results = check_achievements(stats)
        ach = next(r for r in results if r.definition.id == "ten_thousand_voices")
        assert ach.unlocked is False

    def test_globetrotter_unlocks(self):
        stats = {"unique_projects": 20}
        results = check_achievements(stats)
        ach = next(r for r in results if r.definition.id == "globetrotter")
        assert ach.unlocked is True

    def test_globetrotter_not_unlocked(self):
        stats = {"unique_projects": 19}
        results = check_achievements(stats)
        ach = next(r for r in results if r.definition.id == "globetrotter")
        assert ach.unlocked is False

    def test_weekend_warrior_unlocks(self):
        stats = {"weekend_sessions": 10}
        results = check_achievements(stats)
        ach = next(r for r in results if r.definition.id == "weekend_warrior")
        assert ach.unlocked is True

    def test_weekend_warrior_not_unlocked(self):
        stats = {"weekend_sessions": 9}
        results = check_achievements(stats)
        ach = next(r for r in results if r.definition.id == "weekend_warrior")
        assert ach.unlocked is False

    def test_bash_master_unlocks(self):
        stats = {"bash_count": 1000}
        results = check_achievements(stats)
        ach = next(r for r in results if r.definition.id == "bash_master")
        assert ach.unlocked is True

    def test_bash_master_not_unlocked(self):
        stats = {"bash_count": 999}
        results = check_achievements(stats)
        ach = next(r for r in results if r.definition.id == "bash_master")
        assert ach.unlocked is False

    def test_the_legend_unlocks(self):
        stats = {"total_sessions": 1000}
        results = check_achievements(stats)
        ach = next(r for r in results if r.definition.id == "the_legend")
        assert ach.unlocked is True

    def test_the_legend_not_unlocked(self):
        stats = {"total_sessions": 999}
        results = check_achievements(stats)
        ach = next(r for r in results if r.definition.id == "the_legend")
        assert ach.unlocked is False

    def test_code_surgeon_unlocks(self):
        stats = {"total_tool_calls": 50000}
        results = check_achievements(stats)
        ach = next(r for r in results if r.definition.id == "code_surgeon")
        assert ach.unlocked is True

    def test_code_surgeon_not_unlocked(self):
        stats = {"total_tool_calls": 49999}
        results = check_achievements(stats)
        ach = next(r for r in results if r.definition.id == "code_surgeon")
        assert ach.unlocked is False

    def test_ultramarathon_unlocks(self):
        stats = {"longest_session_messages": 500}
        results = check_achievements(stats)
        ach = next(r for r in results if r.definition.id == "ultramarathon")
        assert ach.unlocked is True

    def test_ultramarathon_not_unlocked(self):
        stats = {"longest_session_messages": 499}
        results = check_achievements(stats)
        ach = next(r for r in results if r.definition.id == "ultramarathon")
        assert ach.unlocked is False

    def test_on_a_roll_unlocks(self):
        stats = {"longest_streak": 14}
        results = check_achievements(stats)
        ach = next(r for r in results if r.definition.id == "on_a_roll")
        assert ach.unlocked is True

    def test_on_a_roll_not_unlocked(self):
        stats = {"longest_streak": 13}
        results = check_achievements(stats)
        ach = next(r for r in results if r.definition.id == "on_a_roll")
        assert ach.unlocked is False

    def test_zero_defect_unlocks(self):
        stats = {"total_xp": 50000}
        results = check_achievements(stats)
        ach = next(r for r in results if r.definition.id == "zero_defect")
        assert ach.unlocked is True

    def test_zero_defect_not_unlocked(self):
        stats = {"total_xp": 49999}
        results = check_achievements(stats)
        ach = next(r for r in results if r.definition.id == "zero_defect")
        assert ach.unlocked is False

    def test_the_inception_unlocks(self):
        stats = {"task_count": 100}
        results = check_achievements(stats)
        ach = next(r for r in results if r.definition.id == "the_inception")
        assert ach.unlocked is True

    def test_the_inception_not_unlocked(self):
        stats = {"task_count": 99}
        results = check_achievements(stats)
        ach = next(r for r in results if r.definition.id == "the_inception")
        assert ach.unlocked is False

    def test_night_shift_unlocks(self):
        stats = {"night_sessions": 50}
        results = check_achievements(stats)
        ach = next(r for r in results if r.definition.id == "night_shift")
        assert ach.unlocked is True

    def test_night_shift_not_unlocked(self):
        stats = {"night_sessions": 49}
        results = check_achievements(stats)
        ach = next(r for r in results if r.definition.id == "night_shift")
        assert ach.unlocked is False

    def test_century_streak_unlocks(self):
        stats = {"longest_streak": 100}
        results = check_achievements(stats)
        ach = next(r for r in results if r.definition.id == "century_streak")
        assert ach.unlocked is True

    def test_century_streak_not_unlocked(self):
        stats = {"longest_streak": 99}
        results = check_achievements(stats)
        ach = next(r for r in results if r.definition.id == "century_streak")
        assert ach.unlocked is False

    def test_omega_grind_unlocks(self):
        stats = {"total_xp": 200000}
        results = check_achievements(stats)
        ach = next(r for r in results if r.definition.id == "omega_grind")
        assert ach.unlocked is True

    def test_omega_grind_not_unlocked(self):
        stats = {"total_xp": 199999}
        results = check_achievements(stats)
        ach = next(r for r in results if r.definition.id == "omega_grind")
        assert ach.unlocked is False

    def test_world_builder_unlocks(self):
        stats = {"unique_projects": 50}
        results = check_achievements(stats)
        ach = next(r for r in results if r.definition.id == "world_builder")
        assert ach.unlocked is True

    def test_world_builder_not_unlocked(self):
        stats = {"unique_projects": 49}
        results = check_achievements(stats)
        ach = next(r for r in results if r.definition.id == "world_builder")
        assert ach.unlocked is False

    def test_progress_capped_at_one(self):
        stats = {"total_sessions": 500}
        results = check_achievements(stats)
        centurion = next(r for r in results if r.definition.id == "centurion")
        assert centurion.progress == 1.0

    def test_zero_stats_all_locked(self):
        stats = {}
        results = check_achievements(stats)
        for r in results:
            assert r.unlocked is False
            assert r.progress == 0.0

    def test_all_unlocked(self):
        stats = {
            "total_sessions": 1000,
            "total_messages": 10000,
            "total_tool_calls": 50000,
            "night_sessions": 50,
            "early_sessions": 1,
            "current_streak": 7,
            "longest_streak": 100,
            "unique_projects": 50,
            "longest_session_messages": 500,
            "total_xp": 200000,
            "bash_count": 1000,
            "task_count": 100,
            "weekend_sessions": 10,
        }
        results = check_achievements(stats)
        for r in results:
            assert r.unlocked is True

    def test_returns_25_achievements(self):
        results = check_achievements({})
        assert len(results) == 25

    def test_exact_threshold_unlocks(self):
        """Achievement should unlock at exactly the target value."""
        stats = {"total_sessions": 1}
        results = check_achievements(stats)
        hello = next(r for r in results if r.definition.id == "hello_world")
        assert hello.unlocked is True
        assert hello.progress == 1.0

    def test_one_below_threshold_stays_locked(self):
        stats = {"total_sessions": 99}
        results = check_achievements(stats)
        centurion = next(r for r in results if r.definition.id == "centurion")
        assert centurion.unlocked is False
        assert centurion.progress == 0.99

    def test_unlocked_at_is_none(self):
        """check_achievements does not set unlocked_at (that's for persistence)."""
        results = check_achievements({"total_sessions": 1})
        for r in results:
            assert r.unlocked_at is None


class TestGetNewlyUnlocked:
    """Tests for get_newly_unlocked function."""

    def test_detects_new_unlock(self):
        prev = check_achievements({"total_sessions": 0})
        curr = check_achievements({"total_sessions": 1})
        newly = get_newly_unlocked(prev, curr)
        ids = [a.id for a in newly]
        assert "hello_world" in ids

    def test_no_change_returns_empty(self):
        prev = check_achievements({"total_sessions": 1})
        curr = check_achievements({"total_sessions": 1})
        newly = get_newly_unlocked(prev, curr)
        assert newly == []

    def test_already_unlocked_not_reported(self):
        prev = check_achievements({"total_sessions": 1})
        curr = check_achievements({"total_sessions": 50})
        newly = get_newly_unlocked(prev, curr)
        ids = [a.id for a in newly]
        assert "hello_world" not in ids

    def test_multiple_unlocks_at_once(self):
        prev = check_achievements({})
        curr = check_achievements({
            "total_sessions": 100,
            "total_messages": 1000,
        })
        newly = get_newly_unlocked(prev, curr)
        ids = {a.id for a in newly}
        assert "hello_world" in ids
        assert "centurion" in ids
        assert "thousand_voices" in ids

    def test_both_empty_returns_empty(self):
        prev = check_achievements({})
        curr = check_achievements({})
        newly = get_newly_unlocked(prev, curr)
        assert newly == []


class TestGetClosestAchievements:
    """Tests for get_closest_achievements function."""

    def test_returns_top_n(self):
        stats = {
            "total_sessions": 90,  # 90% centurion
            "total_messages": 500,  # 50% thousand_voices
            "unique_projects": 3,  # 60% polyglot
        }
        results = check_achievements(stats)
        closest = get_closest_achievements(results, n=3)
        assert len(closest) <= 3

    def test_sorted_by_progress_descending(self):
        stats = {
            "total_sessions": 90,  # 90% centurion
            "total_messages": 500,  # 50% thousand_voices
            "unique_projects": 3,  # 60% polyglot
        }
        results = check_achievements(stats)
        closest = get_closest_achievements(results, n=10)
        for i in range(len(closest) - 1):
            assert closest[i].progress >= closest[i + 1].progress

    def test_excludes_unlocked(self):
        stats = {"total_sessions": 100}  # centurion + hello_world unlocked
        results = check_achievements(stats)
        closest = get_closest_achievements(results, n=10)
        for c in closest:
            assert c.unlocked is False

    def test_all_unlocked_returns_empty(self):
        stats = {
            "total_sessions": 1000,
            "total_messages": 10000,
            "total_tool_calls": 50000,
            "night_sessions": 50,
            "early_sessions": 1,
            "current_streak": 7,
            "longest_streak": 100,
            "unique_projects": 50,
            "longest_session_messages": 500,
            "total_xp": 200000,
            "bash_count": 1000,
            "task_count": 100,
            "weekend_sessions": 10,
        }
        results = check_achievements(stats)
        closest = get_closest_achievements(results)
        assert closest == []

    def test_none_unlocked_returns_n(self):
        results = check_achievements({})
        closest = get_closest_achievements(results, n=3)
        assert len(closest) == 3

    def test_default_n_is_3(self):
        results = check_achievements({})
        closest = get_closest_achievements(results)
        assert len(closest) == 3


class TestAchievementDefinitions:
    """Tests for the ACHIEVEMENTS constant."""

    def test_25_achievements_defined(self):
        assert len(ACHIEVEMENTS) == 25

    def test_unique_ids(self):
        ids = [a.id for a in ACHIEVEMENTS]
        assert len(ids) == len(set(ids))

    def test_all_have_positive_targets(self):
        for a in ACHIEVEMENTS:
            assert a.target > 0

    def test_rarity_values_are_valid(self):
        for a in ACHIEVEMENTS:
            assert isinstance(a.rarity, Rarity)

    def test_uncommon_rarity_valid(self):
        assert Rarity.UNCOMMON.value == "uncommon"

    def test_expected_ids(self):
        expected = {
            "hello_world", "centurion", "thousand_voices", "tool_master",
            "night_owl", "early_bird", "on_fire", "iron_will",
            "polyglot", "marathon_runner",
            # Uncommon
            "veteran", "ten_thousand_voices", "globetrotter", "weekend_warrior", "bash_master",
            # Rare
            "the_legend", "code_surgeon", "ultramarathon", "on_a_roll",
            # Epic
            "zero_defect", "the_inception", "night_shift", "century_streak",
            # Legendary
            "omega_grind", "world_builder",
        }
        actual = {a.id for a in ACHIEVEMENTS}
        assert actual == expected
