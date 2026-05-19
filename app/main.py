"""FastAPI entrypoint for the AI Debate app."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as api_router
from app.api.websocket import router as websocket_router


def _cors_origins() -> list[str]:
    configured = os.environ.get("AI_DEBATE_CORS_ORIGINS")
    if configured:
        return [origin.strip() for origin in configured.split(",") if origin.strip()]
    return [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


def _cors_origin_regex() -> str:
    configured = os.environ.get("AI_DEBATE_CORS_ORIGIN_REGEX")
    if configured:
        return configured
    return r"^https?://(localhost|127\.0\.0\.1|0\.0\.0\.0|(\d{1,3}\.){3}\d{1,3})(:\d+)?$"


def create_app() -> FastAPI:
    app = FastAPI(title="AI Debate", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_origin_regex=_cors_origin_regex(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router)
    app.include_router(websocket_router)
    return app


app = create_app()
