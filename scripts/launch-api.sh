#!/usr/bin/env bash
set -euo pipefail

SCRIPT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_ROOT="$SCRIPT_ROOT"

if [[ $# -gt 0 && -d "$1" ]]; then
  TARGET_WORKSPACE="$(cd "$1" && pwd)"
  shift
else
  TARGET_WORKSPACE="$PWD"
fi

HOST="${AI_DEBATE_HOST:-127.0.0.1}"
PORT="${AI_DEBATE_PORT:-8000}"

cd "$APP_ROOT"

if [[ ! -f "app/main.py" ]]; then
  echo "AI Debate backend not found at $APP_ROOT/app/main.py" >&2
  exit 1
fi

if [[ ! -d "$TARGET_WORKSPACE" ]]; then
  echo "Target workspace not found: $TARGET_WORKSPACE" >&2
  exit 1
fi

export AI_DEBATE_WORKSPACE="$TARGET_WORKSPACE"
export GEMINI_CLI_TRUST_WORKSPACE="${GEMINI_CLI_TRUST_WORKSPACE:-true}"

if [[ -f ".venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source ".venv/bin/activate"
fi

if ! command -v uvicorn >/dev/null 2>&1; then
  echo "uvicorn is not installed. Run: python3 -m pip install -r requirements.txt" >&2
  exit 1
fi

echo "Starting AI Debate API: http://$HOST:$PORT"
echo "Docs:                  http://$HOST:$PORT/docs"
echo "Agent workspace:       $AI_DEBATE_WORKSPACE"
echo "Press Ctrl-C to stop."
echo

exec uvicorn app.main:app --host "$HOST" --port "$PORT" --reload
