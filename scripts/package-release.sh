#!/usr/bin/env bash
set -euo pipefail

SCRIPT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${1:-${GITHUB_REF_NAME:-dev}}"
PLATFORM="${2:-$(uname -s | tr '[:upper:]' '[:lower:]')}"
DIST_DIR="$SCRIPT_ROOT/dist/release"
PACKAGE_ROOT="$DIST_DIR/ai-debate-$VERSION"
ARCHIVE_NAME="ai-debate-$VERSION-$PLATFORM.tar.gz"

cd "$SCRIPT_ROOT"

rm -rf "$PACKAGE_ROOT"
mkdir -p "$PACKAGE_ROOT"

INCLUDE_PATHS=(
  "README.md"
  "LICENSE"
  "NOTICE"
  "CONTRIBUTING.md"
  "SECURITY.md"
  "pyproject.toml"
  "requirements.txt"
  "check_llm.py"
  "app"
  "llms"
  "tests"
  "fixtures"
  "scripts"
  "frontend-nuxt/app"
  "frontend-nuxt/shared"
  "frontend-nuxt/public"
  "frontend-nuxt/package.json"
  "frontend-nuxt/pnpm-lock.yaml"
  "frontend-nuxt/pnpm-workspace.yaml"
  "frontend-nuxt/nuxt.config.ts"
  "frontend-nuxt/eslint.config.mjs"
  "frontend-nuxt/tsconfig.json"
  "frontend-nuxt/.env.example"
  "frontend-nuxt/README.md"
  "debate/.gitkeep"
  "debate/mcp_servers.example.json"
)

for path in "${INCLUDE_PATHS[@]}"; do
  if [[ -e "$path" ]]; then
    mkdir -p "$PACKAGE_ROOT/$(dirname "$path")"
    cp -R "$path" "$PACKAGE_ROOT/$path"
  fi
done

find "$PACKAGE_ROOT" -type d -name "__pycache__" -prune -exec rm -rf {} +
find "$PACKAGE_ROOT" -type f \( -name "*.pyc" -o -name "*.pyo" \) -delete

(
  cd "$DIST_DIR"
  tar -czf "$ARCHIVE_NAME" "ai-debate-$VERSION"
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$ARCHIVE_NAME" > "$ARCHIVE_NAME.sha256"
  else
    sha256sum "$ARCHIVE_NAME" > "$ARCHIVE_NAME.sha256"
  fi
)

echo "$DIST_DIR/$ARCHIVE_NAME"
