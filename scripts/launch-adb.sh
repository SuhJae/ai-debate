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
BACKEND_PORT="${ADB_BACKEND_PORT:-8000}"
FRONTEND_PORT="${ADB_FRONTEND_PORT:-5173}"
HOST="${ADB_HOST:-127.0.0.1}"
FRONTEND_ROOT="frontend-nuxt"
FRONTEND_OUTPUT="$APP_ROOT/$FRONTEND_ROOT/.output/server/index.mjs"

cd "$APP_ROOT"

if [[ ! -f "app/main.py" ]]; then
  echo "AI Debate backend not found at $APP_ROOT/app/main.py" >&2
  exit 1
fi

if [[ ! -f "$FRONTEND_ROOT/package.json" ]]; then
  echo "AI Debate frontend not found at $APP_ROOT/$FRONTEND_ROOT/package.json" >&2
  exit 1
fi

if [[ ! -d "$TARGET_WORKSPACE" ]]; then
  echo "Target workspace not found: $TARGET_WORKSPACE" >&2
  exit 1
fi

export AI_DEBATE_WORKSPACE="$TARGET_WORKSPACE"
export GEMINI_CLI_TRUST_WORKSPACE="${GEMINI_CLI_TRUST_WORKSPACE:-true}"
export NUXT_PUBLIC_SITE_URL="${NUXT_PUBLIC_SITE_URL:-http://$HOST:$FRONTEND_PORT}"
export NUXT_PUBLIC_AI_DEBATE_API_URL="${NUXT_PUBLIC_AI_DEBATE_API_URL:-http://$HOST:$BACKEND_PORT/api}"
export NUXT_PUBLIC_AI_DEBATE_WS_URL="${NUXT_PUBLIC_AI_DEBATE_WS_URL:-ws://$HOST:$BACKEND_PORT/ws}"
export NUXT_PUBLIC_AI_DEBATE_DEFAULT_WORKSPACE="${NUXT_PUBLIC_AI_DEBATE_DEFAULT_WORKSPACE:-$TARGET_WORKSPACE}"

if [[ -f ".venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source ".venv/bin/activate"
fi

if ! command -v uvicorn >/dev/null 2>&1; then
  echo "uvicorn is not installed. Run: python3 -m pip install -r requirements.txt" >&2
  exit 1
fi

if ! command -v pnpm >/dev/null 2>&1; then
  echo "pnpm is not installed or not on PATH." >&2
  exit 1
fi

if [[ ! -d "$FRONTEND_ROOT/node_modules" ]]; then
  echo "$FRONTEND_ROOT/node_modules missing; running pnpm install..."
  (cd "$FRONTEND_ROOT" && pnpm install --frozen-lockfile)
fi

if [[ ! -f "$FRONTEND_OUTPUT" ]]; then
  echo "$FRONTEND_ROOT production output missing; running pnpm build..."
  (cd "$FRONTEND_ROOT" && pnpm build)
fi

open_browser() {
  local url="$1"
  if [[ "${ADB_NO_BROWSER:-0}" == "1" ]]; then
    return 0
  fi
  if [[ -n "${BROWSER:-}" ]]; then
    "$BROWSER" "$url" >/dev/null 2>&1 &
    return 0
  fi
  if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$url" >/dev/null 2>&1 &
    return 0
  fi
  if command -v open >/dev/null 2>&1; then
    open "$url" >/dev/null 2>&1 &
    return 0
  fi
  if command -v sensible-browser >/dev/null 2>&1; then
    sensible-browser "$url" >/dev/null 2>&1 &
    return 0
  fi
  echo "No browser opener found. Open manually: $url"
}

cleanup() {
  local code=$?
  trap - INT TERM EXIT
  if [[ -n "${BACKEND_PID:-}" ]]; then
    kill "$BACKEND_PID" >/dev/null 2>&1 || true
  fi
  if [[ -n "${FRONTEND_PID:-}" ]]; then
    kill "$FRONTEND_PID" >/dev/null 2>&1 || true
  fi
  wait >/dev/null 2>&1 || true
  exit "$code"
}

trap cleanup INT TERM EXIT

echo "Starting AI Debate backend:  http://$HOST:$BACKEND_PORT"
uvicorn app.main:app --host "$HOST" --port "$BACKEND_PORT" --reload &
BACKEND_PID=$!

echo "Starting AI Debate frontend: http://$HOST:$FRONTEND_PORT"
(cd "$FRONTEND_ROOT" && HOST="$HOST" PORT="$FRONTEND_PORT" node "$FRONTEND_OUTPUT") &
FRONTEND_PID=$!

echo
echo "AI Debate is launching."
echo "Agent workspace: $AI_DEBATE_WORKSPACE"
echo "Open: http://$HOST:$FRONTEND_PORT"
echo "Press Ctrl-C to stop backend and frontend."
echo

(
  sleep 1
  open_browser "http://$HOST:$FRONTEND_PORT"
) &

wait -n "$BACKEND_PID" "$FRONTEND_PID"
