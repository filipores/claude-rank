"""Achievement definitions and checking for claude-rank."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Rarity(str, Enum):
    COMMON = "common"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"


@dataclass
class AchievementDef:
    id: str
    name: str
    description: str
    rarity: Rarity
    target: float
    check_field: str


@dataclass
class AchievementStatus:
    definition: AchievementDef
    progress: float  # 0.0 to 1.0
    unlocked: bool
    unlocked_at: str | None  # YYYY-MM-DD or None


ACHIEVEMENTS: list[AchievementDef] = [
    AchievementDef(
        id="hello_world",
        name="Hello, World",
        description="Complete your first Claude Code session",
        rarity=Rarity.COMMON,
        target=1,
        check_field="total_sessions",
    ),
    AchievementDef(
        id="centurion",
        name="Centurion",
        description="Complete 100 sessions",
        rarity=Rarity.RARE,
        target=100,
        check_field="total_sessions",
    ),
    AchievementDef(
        id="thousand_voices",
        name="Thousand Voices",
        description="Send 1,000 messages",
        rarity=Rarity.COMMON,
        target=1000,
        check_field="total_messages",
    ),
    AchievementDef(
        id="tool_master",
        name="Tool Master",
        description="Make 10,000 tool calls",
        rarity=Rarity.RARE,
        target=10000,
        check_field="total_tool_calls",
    ),
    AchievementDef(
        id="night_owl",
        name="Night Owl",
        description="Have a session between midnight and 5 AM",
        rarity=Rarity.COMMON,
        target=1,
        check_field="night_sessions",
    ),
    AchievementDef(
        id="early_bird",
        name="Early Bird",
        description="Have a session before 7 AM",
        rarity=Rarity.COMMON,
        target=1,
        check_field="early_sessions",
    ),
    AchievementDef(
        id="on_fire",
        name="On Fire",
        description="Maintain a 7-day streak",
        rarity=Rarity.COMMON,
        target=7,
        check_field="current_streak",
    ),
    AchievementDef(
        id="iron_will",
        name="Iron Will",
        description="Maintain a 30-day streak",
        rarity=Rarity.RARE,
        target=30,
        check_field="longest_streak",
    ),
    AchievementDef(
        id="polyglot",
        name="Polyglot",
        description="Work in 5 different projects",
        rarity=Rarity.COMMON,
        target=5,
        check_field="unique_projects",
    ),
    AchievementDef(
        id="marathon_runner",
        name="Marathon Runner",
        description="Have a single session with 100+ messages",
        rarity=Rarity.RARE,
        target=100,
        check_field="longest_session_messages",
    ),
]


def check_achievements(stats: dict) -> list[AchievementStatus]:
    """Check all achievements against current stats.

    stats dict should have keys matching check_field values:
    - total_sessions: int
    - total_messages: int
    - total_tool_calls: int
    - night_sessions: int (count of sessions in hours 0-4)
    - early_sessions: int (count of sessions in hours 5-6)
    - current_streak: int
    - longest_streak: int
    - unique_projects: int
    - longest_session_messages: int

    Returns list of AchievementStatus with progress calculated as min(current/target, 1.0).
    """
    results: list[AchievementStatus] = []
    for achievement in ACHIEVEMENTS:
        current_value = stats.get(achievement.check_field, 0)
        progress = min(current_value / achievement.target, 1.0) if achievement.target > 0 else 0.0
        unlocked = progress >= 1.0
        results.append(
            AchievementStatus(
                definition=achievement,
                progress=progress,
                unlocked=unlocked,
                unlocked_at=None,
            )
        )
    return results


def get_newly_unlocked(
    previous: list[AchievementStatus], current: list[AchievementStatus]
) -> list[AchievementDef]:
    """Compare previous and current achievement states, return newly unlocked ones."""
    prev_unlocked = {s.definition.id for s in previous if s.unlocked}
    return [s.definition for s in current if s.unlocked and s.definition.id not in prev_unlocked]


def get_closest_achievements(statuses: list[AchievementStatus], n: int = 3) -> list[AchievementStatus]:
    """Return the N achievements closest to being unlocked (highest progress < 1.0)."""
    in_progress = [s for s in statuses if not s.unlocked]
    in_progress.sort(key=lambda s: s.progress, reverse=True)
    return in_progress[:n]
