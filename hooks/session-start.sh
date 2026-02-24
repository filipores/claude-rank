#!/bin/bash
RANK_FILE="$HOME/.claude/rank.json"
command -v jq >/dev/null 2>&1 || exit 0
[ ! -f "$RANK_FILE" ] && exit 0

LEVEL=$(jq -r '.level // 1' "$RANK_FILE")
TITLE=$(jq -r '.title // "Prompt Novice"' "$RANK_FILE")
TOTAL_XP=$(jq -r '.total_xp // 0' "$RANK_FILE")
STREAK=$(jq -r '.current_streak // 0' "$RANK_FILE")
ACHIEVEMENTS=$(jq -r '.achievements_unlocked // 0' "$RANK_FILE")
TOTAL_ACH=$(jq -r '.total_achievements // 25' "$RANK_FILE")
XP_IN=$(jq -r '.xp_in_level // 0' "$RANK_FILE")
XP_NEXT=$(jq -r '.xp_for_next // 100' "$RANK_FILE")
PRESTIGE=$(jq -r '.prestige_stars // ""' "$RANK_FILE")

if [ "$XP_NEXT" -gt 0 ] 2>/dev/null; then
    PCT=$((XP_IN * 100 / XP_NEXT))
else
    PCT=100
fi

PRESTIGE_STR=""
[ -n "$PRESTIGE" ] && PRESTIGE_STR=" ${PRESTIGE}"

echo "User Rank: Level ${LEVEL} ${TITLE}${PRESTIGE_STR} (${TOTAL_XP} XP total, ${PCT}% to next level). Streak: ${STREAK} days. Achievements: ${ACHIEVEMENTS}/${TOTAL_ACH} unlocked."
exit 0
