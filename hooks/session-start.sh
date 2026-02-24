#!/bin/bash
RANK_FILE="$HOME/.claude/rank.json"
command -v jq >/dev/null 2>&1 || exit 0
[ ! -f "$RANK_FILE" ] && exit 0

ER_MU=$(jq -r '.er_mu // 1500' "$RANK_FILE")
ER_TIER=$(jq -r '.er_tier_name // "Unrated"' "$RANK_FILE")

# Round to integer
ER_MU_INT=$(printf '%.0f' "$ER_MU")

echo "ELO: ${ER_MU_INT} (${ER_TIER})"
exit 0
