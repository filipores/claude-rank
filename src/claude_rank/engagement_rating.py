"""Glicko-2 inspired single-player Engagement Rating system for claude-rank.

Measures engagement quality against the user's own historical patterns.
All rating math follows Glickman (2012) Glicko-2 paper.
No side effects. Pure functions only.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# --- Glicko-2 constants ---
MU_0 = 1500.0  # initial rating
PHI_0 = 350.0  # initial RD (high uncertainty for new users)
SIGMA_0 = 0.06  # initial volatility
TAU = 0.5  # system constant (constrains sigma changes)
EPSILON = 0.000001  # convergence tolerance for Illinois algorithm
PHI_MAX = 350.0  # maximum RD
_SCALE = 173.7178  # Glicko-2 display-to-internal scale factor

# --- Hysteresis ---
HYSTERESIS_BUFFER = 30.0  # points below tier threshold before demotion

# --- ER Tiers (10 tiers mapped to mu ranges) ---
ER_TIERS: list[dict] = [
    {"name": "Spectator", "min_mu": 0, "max_mu": 1099, "color": "grey50"},
    {"name": "Engaged", "min_mu": 1100, "max_mu": 1299, "color": "dark_orange3"},
    {"name": "Active", "min_mu": 1300, "max_mu": 1499, "color": "grey70"},
    {"name": "Focused", "min_mu": 1500, "max_mu": 1649, "color": "gold1"},
    {"name": "Dedicated", "min_mu": 1650, "max_mu": 1799, "color": "deep_sky_blue1"},
    {"name": "Intense", "min_mu": 1800, "max_mu": 1949, "color": "cyan"},
    {"name": "Expert", "min_mu": 1950, "max_mu": 2099, "color": "purple"},
    {"name": "Elite", "min_mu": 2100, "max_mu": 2249, "color": "dark_violet"},
    {"name": "Master", "min_mu": 2250, "max_mu": 2399, "color": "red1"},
    {"name": "Transcendent", "min_mu": 2400, "max_mu": 9999, "color": "orange_red1"},
]

# --- Quality score weights ---
DEPTH_WEIGHT = 0.40  # tool calls per session / 50.0
DIVERSITY_WEIGHT = 0.30  # unique tools / 8 (default 0.5 if unknown)
CONSISTENCY_WEIGHT = 0.30  # messages per session / 30.0


@dataclass
class ERState:
    """Current engagement rating state."""

    mu: float = MU_0  # display scale
    phi: float = PHI_0  # display scale
    sigma: float = SIGMA_0  # volatility
    last_rated_date: str | None = None


@dataclass
class DailyERResult:
    """Result of a single day's ER update."""

    date: str
    quality_score: float
    mu_before: float
    phi_before: float
    mu_after: float
    phi_after: float
    sigma_after: float
    er_tier: str
    outcome: float


def initial_er_state() -> ERState:
    """Return a fresh ERState with default values."""
    return ERState()


def compute_quality_score(
    messages: int,
    sessions: int,
    tool_calls: int,
    unique_tools: int = 0,
) -> float:
    """Compute a quality score in [0, 1] from session activity metrics.

    Returns 0.0 if sessions == 0.
    """
    if sessions == 0:
        return 0.0

    depth = min(tool_calls / sessions / 50.0, 1.0)
    diversity = min(unique_tools / 8, 1.0) if unique_tools > 0 else 0.5
    consistency = min(messages / sessions / 30.0, 1.0)

    return (
        DEPTH_WEIGHT * depth
        + DIVERSITY_WEIGHT * diversity
        + CONSISTENCY_WEIGHT * consistency
    )


# --- Glicko-2 core math ---


def _g(phi_internal: float) -> float:
    """g(phi) = 1 / sqrt(1 + 3 * phi^2 / pi^2)."""
    return 1.0 / math.sqrt(1.0 + 3.0 * phi_internal**2 / (math.pi**2))


def _E(mu: float, mu_j: float, phi_j: float) -> float:
    """Expected score: E = 1 / (1 + exp(-g(phi_j) * (mu - mu_j)))."""
    return 1.0 / (1.0 + math.exp(-_g(phi_j) * (mu - mu_j)))


def _new_sigma(sigma: float, phi: float, v: float, delta: float) -> float:
    """Compute new volatility using the Illinois algorithm (Glickman 2012 Section 5.4)."""
    a = math.log(sigma**2)
    delta_sq = delta**2
    phi_sq = phi**2

    def f(x: float) -> float:
        ex = math.exp(x)
        num1 = ex * (delta_sq - phi_sq - v - ex)
        den1 = 2.0 * (phi_sq + v + ex) ** 2
        return num1 / den1 - (x - a) / (TAU**2)

    # Set initial bounds
    A = a
    if delta_sq > phi_sq + v:
        B = math.log(delta_sq - phi_sq - v)
    else:
        k = 1
        while f(a - k * TAU) < 0:
            k += 1
        B = a - k * TAU

    f_A = f(A)
    f_B = f(B)

    # Illinois algorithm iteration
    for _ in range(100):
        if abs(B - A) < EPSILON:
            break
        C = A + (A - B) * f_A / (f_B - f_A)
        f_C = f(C)
        if f_C * f_B <= 0:
            A = B
            f_A = f_B
        else:
            # Guard against division by zero
            if abs(f_B - f_A) < 1e-10:
                break
            f_A = f_A / 2.0
        B = C
        f_B = f_C

    return math.exp(A / 2.0)


def update_er(
    state: ERState,
    quality_score: float,
    days_since_last_update: int = 1,
) -> ERState:
    """Perform a full Glicko-2 update and return the new ERState.

    1. Convert to internal scale.
    2. Inflate phi for idle days.
    3. Use virtual opponent at mu_j=0 (1500 display), phi_j=300/173.7178.
    4. s = quality_score (continuous 0-1).
    5. Full Glicko-2 update.
    6. Convert back to display scale.
    7. Clamp mu in [0, 3000], phi in [10, 350].
    """
    # Step 1: Convert to internal (Glicko-2) scale
    mu = (state.mu - MU_0) / _SCALE
    phi = state.phi / _SCALE

    # Step 2: Inflate phi for idle days (each idle day adds volatility)
    idle_days = max(0, days_since_last_update - 1)
    for _ in range(idle_days):
        phi = math.sqrt(phi**2 + state.sigma**2)

    # Step 3: Virtual opponent at 1500 display (mu_j=0 internal)
    mu_j = 0.0
    phi_j = 300.0 / _SCALE

    # Step 4: Outcome is the quality score
    s = quality_score

    # Step 5: Full Glicko-2 update
    g_phi_j = _g(phi_j)
    e_val = _E(mu, mu_j, phi_j)

    # Variance
    v = 1.0 / (g_phi_j**2 * e_val * (1.0 - e_val))

    # Delta (improvement)
    delta = v * g_phi_j * (s - e_val)

    # New volatility
    sigma_new = _new_sigma(state.sigma, phi, v, delta)

    # Pre-rating period RD
    phi_star = math.sqrt(phi**2 + sigma_new**2)

    # New phi and mu
    phi_new = 1.0 / math.sqrt(1.0 / phi_star**2 + 1.0 / v)
    mu_new = mu + phi_new**2 * g_phi_j * (s - e_val)

    # Step 6: Convert back to display scale
    mu_display = _SCALE * mu_new + MU_0
    phi_display = _SCALE * phi_new

    # Step 7: Clamp
    mu_display = max(0.0, min(3000.0, mu_display))
    phi_display = max(10.0, min(PHI_MAX, phi_display))

    return ERState(
        mu=mu_display,
        phi=phi_display,
        sigma=sigma_new,
        last_rated_date=state.last_rated_date,
    )


def er_tier_from_mu(mu: float, current_tier_name: str | None = None) -> dict:
    """Return the ER tier dict for a given mu value.

    Supports hysteresis: if current_tier_name is provided and the new tier
    would be lower, only demote if mu < current_tier.min_mu - HYSTERESIS_BUFFER.
    """
    # Find tier by mu range
    new_tier = ER_TIERS[0]
    for tier in ER_TIERS:
        if tier["min_mu"] <= mu <= tier["max_mu"]:
            new_tier = tier
            break

    if current_tier_name is None:
        return new_tier

    # Find current tier
    current_tier = None
    for tier in ER_TIERS:
        if tier["name"] == current_tier_name:
            current_tier = tier
            break

    if current_tier is None:
        return new_tier

    # If new tier is same or higher, promote freely
    if new_tier["min_mu"] >= current_tier["min_mu"]:
        return new_tier

    # New tier is lower: only demote if below hysteresis buffer
    if mu < current_tier["min_mu"] - HYSTERESIS_BUFFER:
        return new_tier

    return current_tier


def calculate_historical_er(daily_activities: list[dict]) -> list[DailyERResult]:
    """Calculate ER for a list of historical daily activities.

    Each daily_activity dict has:
        date, messageCount, sessionCount, toolCallCount

    Processes days chronologically. Inactive days inflate phi lazily
    via the days_since_last_update parameter.
    """
    sorted_activities = sorted(daily_activities, key=lambda d: d["date"])

    state = initial_er_state()
    current_tier_name: str | None = None
    last_rated_date: str | None = None
    results: list[DailyERResult] = []

    for activity in sorted_activities:
        day_date = activity["date"]
        messages = activity.get("messageCount", 0)
        sessions = activity.get("sessionCount", 0)
        tool_calls = activity.get("toolCallCount", 0)
        unique_tools = activity.get("uniqueToolCount", 0)

        if sessions == 0:
            continue

        # Calculate days since last rated
        if last_rated_date is not None:
            from datetime import date as _date

            d1 = _date.fromisoformat(last_rated_date)
            d2 = _date.fromisoformat(day_date)
            days_gap = (d2 - d1).days
        else:
            days_gap = 1

        quality = compute_quality_score(messages, sessions, tool_calls, unique_tools)

        mu_before = state.mu
        phi_before = state.phi

        state = update_er(state, quality, days_since_last_update=days_gap)
        state = ERState(
            mu=state.mu,
            phi=state.phi,
            sigma=state.sigma,
            last_rated_date=day_date,
        )

        tier = er_tier_from_mu(state.mu, current_tier_name)
        current_tier_name = tier["name"]
        last_rated_date = day_date

        results.append(
            DailyERResult(
                date=day_date,
                quality_score=quality,
                mu_before=mu_before,
                phi_before=phi_before,
                mu_after=state.mu,
                phi_after=state.phi,
                sigma_after=state.sigma,
                er_tier=tier["name"],
                outcome=quality,
            )
        )

    return results
