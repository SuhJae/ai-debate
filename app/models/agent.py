"""Agent model definitions."""

from enum import StrEnum
import re

from pydantic import BaseModel, field_validator


AGENT_COLOR_SEQUENCE = [
    "celadon",
    "joseon",
    "brass",
    "pine",
    "sky",
    "violet",
    "slate",
    "orange",
    "lime",
    "indigo",
    "fuchsia",
    "rose",
]


class ProviderKind(StrEnum):
    CODEX = "codex"
    GEMINI = "gemini"
    CLAUDE = "claude"


# Backward-compatible import name used by older tests/modules. New code should
# treat provider and debate-agent name as separate concepts.
AgentId = ProviderKind


class AgentStatus(StrEnum):
    IDLE = "idle"
    QUEUED = "queued"
    RUNNING = "running"
    WAITING = "waiting"
    DONE = "done"
    FAILED = "failed"
    DISABLED = "disabled"


class DebateStyle(StrEnum):
    AGGRESSIVE = "aggressive"
    NORMAL = "normal"
    COLLABORATIVE = "collaborative"
    NEUTRAL = "neutral"
    POLITICIAN = "politician"


class TechnicalPreference(StrEnum):
    CONSERVATIVE = "conservative"
    NEUTRAL = "neutral"
    INNOVATIVE = "innovative"
    FRONTIER = "frontier"
    LEFT = "left"
    RIGHT = "right"
    INDEPENDENT = "independent"


class DebateAgentConfig(BaseModel):
    name: str
    provider: ProviderKind
    model: str | None = None
    display_name: str | None = None
    color: str | None = None
    write_thesis: bool = True
    debate_style: DebateStyle = DebateStyle.NORMAL
    technical_preference: TechnicalPreference = TechnicalPreference.NEUTRAL
    additional_note: str = ""

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{1,31}", value):
            raise ValueError(
                "agent name must start with a letter and contain 2-32 letters, numbers, _ or -"
            )
        return value


class AgentState(BaseModel):
    provider: ProviderKind
    display_name: str
    model: str
    color: str | None = None
    write_thesis: bool = True
    debate_style: DebateStyle = DebateStyle.NORMAL
    technical_preference: TechnicalPreference = TechnicalPreference.NEUTRAL
    additional_note: str = ""
    session_id: str | None = None
    status: AgentStatus = AgentStatus.IDLE
    last_error: str | None = None
