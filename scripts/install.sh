#!/usr/bin/env bash
set -euo pipefail

SCRIPT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
FRONTEND_ROOT="$SCRIPT_ROOT/frontend-nuxt"

cd "$SCRIPT_ROOT"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python not found: $PYTHON_BIN" >&2
  exit 1
fi

if [[ ! -d ".venv" ]]; then
  "$PYTHON_BIN" -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -e ".[dev]"

if ! command -v pnpm >/dev/null 2>&1; then
  if command -v corepack >/dev/null 2>&1; then
    corepack enable
    corepack prepare pnpm@10.33.2 --activate
  else
    echo "pnpm is required. Install pnpm or Node.js with corepack enabled." >&2
    exit 1
  fi
fi

cd "$FRONTEND_ROOT"
pnpm install --frozen-lockfile
pnpm build

echo
echo "AI Debate install complete."
echo "Run: ./scripts/launch-adb.sh /path/to/workspace"
