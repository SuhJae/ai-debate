"""State transition helpers."""

from datetime import datetime, timezone
import re

from app.models.debate import DebatePhase, DebateState


ALLOWED_TRANSITIONS: dict[DebatePhase, set[DebatePhase]] = {
    DebatePhase.CREATED: {DebatePhase.STARTING_THESES, DebatePhase.FAILED, DebatePhase.CANCELLED},
    DebatePhase.STARTING_THESES: {DebatePhase.AWAITING_THESES, DebatePhase.FAILED, DebatePhase.CANCELLED},
    DebatePhase.AWAITING_THESES: {DebatePhase.THESES_READY, DebatePhase.FAILED, DebatePhase.CANCELLED},
    DebatePhase.THESES_READY: {DebatePhase.DEBATING, DebatePhase.FAILED, DebatePhase.CANCELLED},
    DebatePhase.DEBATING: {
        DebatePhase.PAUSE_REQUESTED,
        DebatePhase.PAUSED,
        DebatePhase.CONSENSUS_REACHED,
        DebatePhase.FAILED,
        DebatePhase.CANCELLED,
    },
    DebatePhase.PAUSE_REQUESTED: {DebatePhase.PAUSED, DebatePhase.FAILED, DebatePhase.CANCELLED},
    DebatePhase.PAUSED: {DebatePhase.DEBATING, DebatePhase.FAILED, DebatePhase.CANCELLED},
    DebatePhase.CONSENSUS_REACHED: {
        DebatePhase.DEBATING,
        DebatePhase.DRAFTING_FINAL,
        DebatePhase.FAILED,
        DebatePhase.CANCELLED,
    },
    DebatePhase.DRAFTING_FINAL: {DebatePhase.REVIEWING_FINAL, DebatePhase.FAILED, DebatePhase.CANCELLED},
    DebatePhase.REVIEWING_FINAL: {
        DebatePhase.ACCEPTED,
        DebatePhase.REVISING_FINAL,
        DebatePhase.FAILED,
        DebatePhase.CANCELLED,
    },
    DebatePhase.REVISING_FINAL: {DebatePhase.REVIEWING_FINAL, DebatePhase.FAILED, DebatePhase.CANCELLED},
    DebatePhase.ACCEPTED: set(),
    DebatePhase.FAILED: {
        DebatePhase.STARTING_THESES,
        DebatePhase.THESES_READY,
        DebatePhase.DEBATING,
        DebatePhase.CANCELLED,
    },
    DebatePhase.CANCELLED: set(),
}


def assert_transition(current: DebatePhase, target: DebatePhase) -> None:
    if target not in ALLOWED_TRANSITIONS[current]:
        raise ValueError(f"invalid phase transition: {current} -> {target}")


def transition(state: DebateState, target: DebatePhase) -> DebateState:
    assert_transition(state.phase, target)
    updated = _copy_model(state, phase=target, updated_at=now_iso())
    return updated


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def slugify_title(title: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", title.lower()).strip("-")
    return slug[:48] or "debate"


def new_debate_id(title: str) -> str:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{stamp}-{slugify_title(title)}"


def _copy_model(model, **changes):
    if hasattr(model, "model_copy"):
        return model.model_copy(update=changes)
    return model.copy(update=changes)
