"""Command-line entrypoints for AI Debate."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import uvicorn


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the AI Debate FastAPI backend.")
    parser.add_argument(
        "workspace",
        nargs="?",
        default=os.environ.get("AI_DEBATE_WORKSPACE") or str(Path.cwd()),
        help="Workspace directory exposed to LLM provider CLIs.",
    )
    parser.add_argument("--host", default=os.environ.get("AI_DEBATE_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("AI_DEBATE_PORT", "8000")))
    parser.add_argument("--reload", action="store_true", help="Enable uvicorn reload for development.")
    args = parser.parse_args(argv)

    workspace = Path(args.workspace).expanduser()
    if not workspace.is_dir():
        parser.error(f"workspace does not exist or is not a directory: {workspace}")

    os.environ["AI_DEBATE_WORKSPACE"] = str(workspace.resolve())
    uvicorn.run("app.main:app", host=args.host, port=args.port, reload=args.reload)
    return 0
