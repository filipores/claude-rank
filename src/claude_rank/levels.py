"""Level and tier progression calculation. Pure functions, no side effects."""

import math

MAX_LEVEL = 50

TIERS: list[dict] = [
    {"tier": 1, "levels": (1, 5), "name": "Bronze", "color": "bronze"},
    {"tier": 2, "levels": (6, 10), "name": "Silver", "color": "silver"},
    {"tier": 3, "levels": (11, 15), "name": "Gold", "color": "gold"},
    {"tier": 4, "levels": (16, 20), "name": "Platinum", "color": "teal"},
    {"tier": 5, "levels": (21, 25), "name": "Diamond", "color": "diamond"},
    {"tier": 6, "levels": (26, 30), "name": "Master", "color": "purple"},
    {"tier": 7, "levels": (31, 35), "name": "Candidate Master", "color": "deep_purple"},
    {"tier": 8, "levels": (36, 40), "name": "International Master", "color": "crimson"},
    {"tier": 9, "levels": (41, 45), "name": "Grandmaster", "color": "amber"},
    {"tier": 10, "levels": (46, 50), "name": "Legendary Grandmaster", "color": "legendary"},
]


def xp_for_level(level: int) -> int:
    """XP needed to reach a specific level. Formula: floor(50 * L^1.8 + 100 * L)."""
    if level <= 0:
        return 0
    return math.floor(50 * (level ** 1.8) + 100 * level)


def cumulative_xp_for_level(level: int) -> int:
    """Total XP needed from 0 to reach this level (sum of all previous levels)."""
    if level <= 0:
        return 0
    return sum(xp_for_level(lv) for lv in range(1, level + 1))


def level_from_xp(total_xp: int) -> int:
    """Given total XP, return current level (1-50, capped at 50)."""
    if total_xp <= 0:
        return 1
    cumulative = 0
    for lv in range(1, MAX_LEVEL + 1):
        cumulative += xp_for_level(lv)
        if total_xp < cumulative:
            return lv
    return MAX_LEVEL


def tier_from_level(level: int) -> dict:
    """Return tier info dict for given level."""
    level = max(1, min(level, MAX_LEVEL))
    for tier in TIERS:
        low, high = tier["levels"]
        if low <= level <= high:
            return tier
    return TIERS[-1]


def xp_progress_in_level(total_xp: int) -> tuple[int, int]:
    """Return (current_xp_in_level, xp_needed_for_next_level).

    If at max level, returns (xp_past_last_threshold, 0).
    """
    if total_xp <= 0:
        return (0, xp_for_level(1))

    current_level = level_from_xp(total_xp)
    xp_to_reach_current = cumulative_xp_for_level(current_level - 1)
    xp_in_level = total_xp - xp_to_reach_current

    if current_level >= MAX_LEVEL:
        return (xp_in_level, 0)

    xp_needed = xp_for_level(current_level)
    return (xp_in_level, xp_needed)


PRESTIGE_XP_THRESHOLD: int = cumulative_xp_for_level(MAX_LEVEL)


def get_prestige_xp(total_xp: int, prestige_count: int) -> int:
    """Return XP within the current prestige cycle.
    For prestige_count=0, returns total_xp unchanged.
    For prestige_count=1, returns total_xp - PRESTIGE_XP_THRESHOLD.
    """
    if prestige_count <= 0:
        return total_xp
    return total_xp - (prestige_count * PRESTIGE_XP_THRESHOLD)


def prestige_stars(prestige_count: int) -> str:
    """Return star characters: 1 -> '★', 3 -> '★★★', 0 -> ''."""
    if prestige_count <= 0:
        return ""
    return "★" * prestige_count


def can_prestige(total_xp: int, prestige_count: int) -> bool:
    """Return True if user has enough XP to prestige again."""
    required = (prestige_count + 1) * PRESTIGE_XP_THRESHOLD
    return total_xp >= required
