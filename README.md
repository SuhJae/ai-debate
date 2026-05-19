# AI Debate

AI Debate is a local debate workbench for running structured discussions between CLI-backed LLM agents. It pairs a FastAPI backend with a Nuxt frontend and stores debate state on disk.

The app is intended for local, developer-controlled use. Provider CLIs and their accounts remain external dependencies.

## Features

- Multi-agent debate flow with thesis, round, review, and final-document phases.
- FastAPI HTTP and WebSocket backend.
- Nuxt 4 frontend for creating, monitoring, and reviewing debates.
- Local filesystem storage for debate state and artifacts.
- Provider wrappers for Codex, Gemini, and Claude CLIs.
- Focused backend tests and frontend lint/type/build checks.

## Requirements

- macOS or Linux.
- Python 3.11 or newer.
- Node.js 22 or newer.
- pnpm 10.33.2 or newer. Corepack can install the pinned pnpm version.
- At least one supported LLM CLI installed and authenticated:
  - `codex`
  - `gemini`
  - `claude`

## Install

From a fresh clone:

```bash
git clone https://github.com/<owner>/ai-debate.git
cd ai-debate
./scripts/install.sh
```

The installer creates `.venv`, installs the Python package in editable mode with dev dependencies, installs frontend dependencies, and builds the Nuxt app.

## Run

Start the full local app:

```bash
./scripts/launch-adb.sh /path/to/workspace
```

If no workspace is provided, the current directory is used. The default URLs are:

- Frontend: `http://127.0.0.1:5173`
- Backend API: `http://127.0.0.1:8000/api`
- Backend docs: `http://127.0.0.1:8000/docs`

Useful environment variables:

```bash
ADB_HOST=127.0.0.1
ADB_BACKEND_PORT=8000
ADB_FRONTEND_PORT=5173
AI_DEBATE_CORS_ORIGINS=http://localhost:5173
AI_DEBATE_CORS_ORIGIN_REGEX='^https?://(localhost|127\.0\.0\.1)(:\d+)?$'
```

Run only the API:

```bash
./scripts/launch-api.sh /path/to/workspace
```

## Check LLM CLIs

After installing and authenticating provider CLIs:

```bash
source .venv/bin/activate
ai-debate-check-llm
```

This command sends live prompts to the configured providers. It is not part of CI because it depends on local accounts, network access, and provider quotas.

## Development

Run all local checks:

```bash
./scripts/check.sh
```

Backend only:

```bash
source .venv/bin/activate
python -m pytest -q
```

Frontend only:

```bash
cd frontend-nuxt
pnpm lint
pnpm typecheck
pnpm build
```

Runtime debate data is written under `debate/` and is ignored by Git by default.

## Releases

Create a version tag:

```bash
git tag v0.1.0
git push origin v0.1.0
```

The release workflow builds macOS and Linux source archives with install/run scripts and checksums. The archives do not bundle Python, Node, pnpm, or provider CLIs.

To test packaging locally:

```bash
./scripts/package-release.sh v0.1.0
```

## License

Apache-2.0. See [LICENSE](LICENSE).
