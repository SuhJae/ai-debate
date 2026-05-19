# Contributing

## Development Setup

```bash
./scripts/install.sh
```

Run the full local check before opening a pull request:

```bash
./scripts/check.sh
```

## Pull Requests

- Keep backend and frontend changes focused.
- Do not commit local debate sessions, provider credentials, generated Nuxt output, virtual environments, or `node_modules`.
- Add or update tests when behavior changes.
- Document new environment variables in `README.md` and `frontend-nuxt/.env.example`.

## LLM Provider CLIs

Provider CLI health checks are intentionally separate from CI:

```bash
ai-debate-check-llm
```

Run them only from a machine where the relevant CLIs are installed and authenticated.
