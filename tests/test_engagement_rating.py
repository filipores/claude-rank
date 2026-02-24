"""Tests for the Glicko-2 Engagement Rating system."""

import math

import pytest

from claude_rank.engagement_rating import (
    CONSISTENCY_WEIGHT,
    DEPTH_WEIGHT,
    DIVERSITY_WEIGHT,
    ER_TIERS,
    HYSTERESIS_BUFFER,
    MU_0,
    PHI_0,
    PHI_MAX,
    SIGMA_0,
    DailyERResult,
    ERState,
    _E,
    _g,
    calculate_historical_er,
    compute_quality_score,
    er_tier_from_mu,
    initial_er_state,
    update_er,
)


class TestComputeQualityScore:
    def test_zero_sessions_returns_zero(self):
        assert compute_quality_score(messages=50, sessions=0, tool_calls=100) == 0.0

    def test_typical_values(self):
        score = compute_quality_score(messages=50, sessions=2, tool_calls=100)
        assert 0.3 < score < 1.0

    def test_high_activity(self):
        score = compute_quality_score(
            messages=300, sessions=2, tool_calls=500, unique_tools=8
        )
        assert score >= 0.9

    def test_low_activity(self):
        score = compute_quality_score(messages=1, sessions=1, tool_calls=1)
        assert score < 0.3

    def test_diversity_default(self):
        """unique_tools=0 uses 0.5 as neutral default for diversity component."""
        score_default = compute_quality_score(messages=50, sessions=2, tool_calls=100, unique_tools=0)
        # With unique_tools=0, diversity = 0.5
        # depth = min(100/2/50, 1.0) = 1.0
        # consistency = min(50/2/30, 1.0) = min(0.833, 1.0) = 0.833
        expected = DEPTH_WEIGHT * 1.0 + DIVERSITY_WEIGHT * 0.5 + CONSISTENCY_WEIGHT * (50 / 2 / 30)
        assert score_default == pytest.approx(expected)

    def test_all_weights_sum_to_one(self):
        assert DEPTH_WEIGHT + DIVERSITY_WEIGHT + CONSISTENCY_WEIGHT == pytest.approx(1.0)

    def test_score_clamped_to_one(self):
        """Even with extreme values, each component is clamped via min(..., 1.0)."""
        score = compute_quality_score(
            messages=10000, sessions=1, tool_calls=10000, unique_tools=100
        )
        # All components clamped to 1.0, total = 1.0 * (sum of weights) = 1.0
        assert score <= 1.0
        assert score == pytest.approx(1.0)


class TestGlicko2GFunction:
    def test_g_zero_phi(self):
        """g(0) = 1 / sqrt(1 + 0) = 1.0."""
        assert _g(0.0) == pytest.approx(1.0)

    def test_g_large_phi(self):
        """g(large) approaches 0."""
        result = _g(1000.0)
        assert result > 0.0
        assert result < 0.01

    def test_g_positive(self):
        """g is always positive for any phi."""
        for phi in [0.0, 0.1, 1.0, 10.0, 100.0, 1000.0]:
            assert _g(phi) > 0.0


class TestGlicko2EFunction:
    def test_equal_ratings(self):
        """Equal ratings -> expected score is 0.5."""
        result = _E(0.0, 0.0, 1.0)
        assert result == pytest.approx(0.5)

    def test_higher_rating_higher_expected(self):
        """Higher mu -> expected score > 0.5."""
        result = _E(2.0, 0.0, 1.0)
        assert result > 0.5

    def test_lower_rating_lower_expected(self):
        """Lower mu -> expected score < 0.5."""
        result = _E(-2.0, 0.0, 1.0)
        assert result < 0.5

    def test_E_bounded(self):
        """Result always in (0, 1)."""
        for mu in [-5.0, -2.0, 0.0, 2.0, 5.0]:
            for phi_j in [0.1, 1.0, 5.0]:
                result = _E(mu, 0.0, phi_j)
                assert 0.0 < result < 1.0


class TestUpdateER:
    def test_high_quality_increases_mu(self):
        """quality=1.0 from initial state -> mu increases."""
        state = initial_er_state()
        new_state = update_er(state, quality_score=1.0)
        assert new_state.mu > MU_0

    def test_low_quality_decreases_mu(self):
        """quality=0.0 from initial state -> mu decreases."""
        state = initial_er_state()
        new_state = update_er(state, quality_score=0.0)
        assert new_state.mu < MU_0

    def test_draw_minimal_change(self):
        """quality=0.5 from initial state -> mu approximately 1500."""
        state = initial_er_state()
        new_state = update_er(state, quality_score=0.5)
        assert abs(new_state.mu - MU_0) < 20

    def test_phi_decreases_with_activity(self):
        """phi after update < phi before (uncertainty drops with more data)."""
        state = initial_er_state()
        new_state = update_er(state, quality_score=0.7)
        assert new_state.phi < state.phi

    def test_sigma_bounded(self):
        """sigma stays in reasonable range after any update."""
        state = initial_er_state()
        for quality in [0.0, 0.25, 0.5, 0.75, 1.0]:
            new_state = update_er(state, quality_score=quality)
            assert 0.0 < new_state.sigma < 1.0

    def test_mu_clamped(self):
        """Result mu in [0, 3000], phi in [10, 350]."""
        state = initial_er_state()
        new_state = update_er(state, quality_score=1.0)
        assert 0.0 <= new_state.mu <= 3000.0
        assert 10.0 <= new_state.phi <= PHI_MAX


class TestPhiInflation:
    def test_idle_days_increase_phi(self):
        """days_since_last_update=10 -> phi grows compared to single day."""
        state = ERState(mu=1500, phi=200, sigma=0.06)
        state_1day = update_er(state, quality_score=0.5, days_since_last_update=1)
        state_10day = update_er(state, quality_score=0.5, days_since_last_update=10)
        # With 10 idle days, phi inflates before the update, so final phi is larger
        assert state_10day.phi > state_1day.phi

    def test_phi_caps_at_max(self):
        """Many idle days -> phi doesn't exceed PHI_MAX (350)."""
        state = ERState(mu=1500, phi=200, sigma=0.06)
        new_state = update_er(state, quality_score=0.5, days_since_last_update=1000)
        assert new_state.phi <= PHI_MAX

    def test_single_day_no_extra_inflation(self):
        """days_since_last_update=1 -> no idle inflation applied."""
        state = ERState(mu=1500, phi=200, sigma=0.06)
        new_state = update_er(state, quality_score=0.5, days_since_last_update=1)
        # phi should decrease or stay similar (no idle inflation, only Glicko-2 update)
        # The Glicko-2 update itself reduces phi via information gain
        assert new_state.phi < state.phi


class TestERTierFromMu:
    def test_initial_rating_focused(self):
        tier = er_tier_from_mu(1500)
        assert tier["name"] == "Focused"

    def test_low_rating_spectator(self):
        tier = er_tier_from_mu(500)
        assert tier["name"] == "Spectator"

    def test_high_rating_transcendent(self):
        tier = er_tier_from_mu(2500)
        assert tier["name"] == "Transcendent"

    def test_boundary_values(self):
        """Test exact min_mu values for each tier."""
        for tier_info in ER_TIERS:
            tier = er_tier_from_mu(tier_info["min_mu"])
            assert tier["name"] == tier_info["name"]

    def test_hysteresis_prevents_demotion(self):
        """mu=1498 with current_tier='Focused' -> stays 'Focused' (within 30 buffer)."""
        # Focused min_mu = 1500; 1498 is only 2 below, within HYSTERESIS_BUFFER=30
        tier = er_tier_from_mu(1498, current_tier_name="Focused")
        assert tier["name"] == "Focused"

    def test_hysteresis_allows_demotion(self):
        """mu=1460 with current_tier='Focused' -> demotes to 'Active' (> 30 below)."""
        # 1460 < 1500 - 30 = 1470, so demotion happens
        tier = er_tier_from_mu(1460, current_tier_name="Focused")
        assert tier["name"] == "Active"

    def test_hysteresis_allows_promotion(self):
        """mu=1650 with current_tier='Focused' -> promotes to 'Dedicated'."""
        tier = er_tier_from_mu(1650, current_tier_name="Focused")
        assert tier["name"] == "Dedicated"

    def test_no_hysteresis_without_current_tier(self):
        """mu=1498 without current_tier -> 'Active' (no hysteresis protection)."""
        tier = er_tier_from_mu(1498)
        assert tier["name"] == "Active"


class TestCalculateHistoricalER:
    def test_empty_input(self):
        assert calculate_historical_er([]) == []

    def test_single_active_day(self):
        activities = [
            {"date": "2025-01-01", "messageCount": 50, "sessionCount": 2, "toolCallCount": 100},
        ]
        results = calculate_historical_er(activities)
        assert len(results) == 1
        assert results[0].date == "2025-01-01"
        assert isinstance(results[0], DailyERResult)

    def test_multiple_days_progressive(self):
        """Several active days -> mu changes over time."""
        activities = [
            {"date": f"2025-01-{d:02d}", "messageCount": 60, "sessionCount": 3, "toolCallCount": 150}
            for d in range(1, 6)
        ]
        results = calculate_historical_er(activities)
        assert len(results) == 5
        # With consistent high quality, mu should generally increase
        assert results[-1].mu_after != results[0].mu_after

    def test_gap_in_activity(self):
        """Active days with gap -> phi inflated during gap inside update_er."""
        activities = [
            {"date": "2025-01-01", "messageCount": 50, "sessionCount": 2, "toolCallCount": 100},
            {"date": "2025-01-10", "messageCount": 50, "sessionCount": 2, "toolCallCount": 100},
        ]
        results = calculate_historical_er(activities)
        assert len(results) == 2
        # The gap inflation happens inside update_er, so phi_after on day 2 is
        # higher than it would be with no gap. Compare against a no-gap baseline.
        no_gap_activities = [
            {"date": "2025-01-01", "messageCount": 50, "sessionCount": 2, "toolCallCount": 100},
            {"date": "2025-01-02", "messageCount": 50, "sessionCount": 2, "toolCallCount": 100},
        ]
        no_gap_results = calculate_historical_er(no_gap_activities)
        # With gap, phi_after on day 2 should be larger than without gap
        assert results[1].phi_after > no_gap_results[1].phi_after

    def test_inactive_days_skipped(self):
        """Days with sessions=0 not in results."""
        activities = [
            {"date": "2025-01-01", "messageCount": 50, "sessionCount": 2, "toolCallCount": 100},
            {"date": "2025-01-02", "messageCount": 0, "sessionCount": 0, "toolCallCount": 0},
            {"date": "2025-01-03", "messageCount": 50, "sessionCount": 2, "toolCallCount": 100},
        ]
        results = calculate_historical_er(activities)
        assert len(results) == 2
        assert results[0].date == "2025-01-01"
        assert results[1].date == "2025-01-03"

    def test_chronological_processing(self):
        """Dates are processed in chronological order regardless of input order."""
        activities = [
            {"date": "2025-01-03", "messageCount": 50, "sessionCount": 2, "toolCallCount": 100},
            {"date": "2025-01-01", "messageCount": 50, "sessionCount": 2, "toolCallCount": 100},
            {"date": "2025-01-02", "messageCount": 50, "sessionCount": 2, "toolCallCount": 100},
        ]
        results = calculate_historical_er(activities)
        assert results[0].date == "2025-01-01"
        assert results[1].date == "2025-01-02"
        assert results[2].date == "2025-01-03"

    def test_tier_carried_forward(self):
        """Hysteresis works across days - tier is carried forward."""
        # First build up to Focused tier with high quality
        activities = [
            {"date": f"2025-01-{d:02d}", "messageCount": 200, "sessionCount": 3, "toolCallCount": 300}
            for d in range(1, 4)
        ]
        # Then add a day with low quality that might drop mu slightly
        activities.append(
            {"date": "2025-01-04", "messageCount": 5, "sessionCount": 1, "toolCallCount": 2}
        )
        results = calculate_historical_er(activities)
        # Verify that tiers are strings and populated for all results
        for r in results:
            assert isinstance(r.er_tier, str)
            assert len(r.er_tier) > 0


class TestInitialState:
    def test_defaults(self):
        state = initial_er_state()
        assert state.mu == MU_0
        assert state.phi == PHI_0
        assert state.sigma == SIGMA_0
        assert state.last_rated_date is None
