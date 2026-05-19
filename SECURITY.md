# Security

AI Debate is designed for local use and can launch provider CLIs against a selected workspace. Treat workspace access as sensitive.

## Reporting

Open a private security advisory on GitHub if the repository supports it. Otherwise, contact the maintainer directly before disclosing a vulnerability publicly.

## Operational Notes

- Do not commit `.env` files or provider credentials.
- Review workspace paths before enabling read, probe, edit, or full tool modes.
- Prefer local-only bind addresses such as `127.0.0.1` unless you are deliberately exposing the app behind your own access controls.
