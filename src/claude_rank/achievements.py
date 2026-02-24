"""Achievement definitions and checking for claude-rank."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Rarity(str, Enum):
    COMMON = "common"
    UNCOMMON = "uncommon"
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
    # --- Uncommon ---
    AchievementDef(
        id="veteran",
        name="Veteran",
        description="Complete 500 sessions",
        rarity=Rarity.UNCOMMON,
        target=500,
        check_field="total_sessions",
    ),
    AchievementDef(
        id="ten_thousand_voices",
        name="Ten Thousand Voices",
        description="Send 10,000 messages",
        rarity=Rarity.UNCOMMON,
        target=10000,
        check_field="total_messages",
    ),
    AchievementDef(
        id="globetrotter",
        name="Globetrotter",
        description="Work in 20 different projects",
        rarity=Rarity.UNCOMMON,
        target=20,
        check_field="unique_projects",
    ),
    AchievementDef(
        id="weekend_warrior",
        name="Weekend Warrior",
        description="Have 10 sessions on weekends",
        rarity=Rarity.UNCOMMON,
        target=10,
        check_field="weekend_sessions",
    ),
    AchievementDef(
        id="bash_master",
        name="Bash Master",
        description="Execute 1,000 Bash commands",
        rarity=Rarity.UNCOMMON,
        target=1000,
        check_field="bash_count",
    ),
    # --- Rare ---
    AchievementDef(
        id="the_legend",
        name="The Legend",
        description="Complete 1,000 sessions",
        rarity=Rarity.RARE,
        target=1000,
        check_field="total_sessions",
    ),
    AchievementDef(
        id="code_surgeon",
        name="Code Surgeon",
        description="Make 50,000 tool calls",
        rarity=Rarity.RARE,
        target=50000,
        check_field="total_tool_calls",
    ),
    AchievementDef(
        id="ultramarathon",
        name="Ultramarathon",
        description="Have a single session with 500+ messages",
        rarity=Rarity.RARE,
        target=500,
        check_field="longest_session_messages",
    ),
    AchievementDef(
        id="on_a_roll",
        name="On a Roll",
        description="Maintain a 14-day streak",
        rarity=Rarity.RARE,
        target=14,
        check_field="longest_streak",
    ),
    # --- Epic ---
    AchievementDef(
        id="zero_defect",
        name="Zero Defect",
        description="Reach 50,000 total XP",
        rarity=Rarity.EPIC,
        target=50000,
        check_field="total_xp",
    ),
    AchievementDef(
        id="the_inception",
        name="The Inception",
        description="Spawn 100 subagent tasks",
        rarity=Rarity.EPIC,
        target=100,
        check_field="task_count",
    ),
    AchievementDef(
        id="night_shift",
        name="Night Shift",
        description="Have 50 sessions between midnight and 5 AM",
        rarity=Rarity.EPIC,
        target=50,
        check_field="night_sessions",
    ),
    AchievementDef(
        id="century_streak",
        name="Century Streak",
        description="Maintain a 100-day streak",
        rarity=Rarity.EPIC,
        target=100,
        check_field="longest_streak",
    ),
    # --- Legendary ---
    AchievementDef(
        id="omega_grind",
        name="Omega Grind",
        description="Reach 200,000 total XP",
        rarity=Rarity.LEGENDARY,
        target=200000,
        check_field="total_xp",
    ),
    AchievementDef(
        id="world_builder",
        name="World Builder",
        description="Work in 50 different projects",
        rarity=Rarity.LEGENDARY,
        target=50,
        check_field="unique_projects",
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
