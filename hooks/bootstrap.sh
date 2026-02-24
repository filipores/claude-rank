#!/bin/bash
set -euo pipefail

PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
VENV_DIR="${PLUGIN_ROOT}/.venv"
SENTINEL="${VENV_DIR}/.claude-rank-installed"

if [ ! -f "${SENTINEL}" ]; then
    python3 -m venv "${VENV_DIR}" 2>/dev/null
    "${VENV_DIR}/bin/pip" install --quiet "rich>=13.0" "mcp>=1.0"
    "${VENV_DIR}/bin/pip" install --quiet -e "${PLUGIN_ROOT}"
    touch "${SENTINEL}"
fi

exec "${VENV_DIR}/bin/python3" "$@"
