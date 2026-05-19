"""Event model and helpers."""

from uuid import uuid4

from pydantic import BaseModel, Field

from app.core.state import now_iso


class DebateEvent(BaseModel):
    id: str
    debate_id: str
    created_at: str
    type: str
    actor: str
    payload: dict = Field(default_factory=dict)


def new_event(
    debate_id: str,
    type: str,
    actor: str,
    payload: dict | None = None,
) -> DebateEvent:
    """Create a timestamped event with a UUID."""
    return DebateEvent(
        id=str(uuid4()),
        debate_id=debate_id,
        created_at=now_iso(),
        type=type,
        actor=actor,
        payload=payload or {},
    )
