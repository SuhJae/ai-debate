import asyncio

from app.api import routes
from app.core.agent_registry import AgentRegistry
from app.core.debate_engine import DebateEngine
from app.core.storage import DebateStorage
from app.models.agent import AgentState, ProviderKind
from app.models.debate import ConsensusState, DebatePhase, DebateState


def test_list_discussions_returns_sidebar_summaries(tmp_path):
    original_storage = routes.storage
    storage = DebateStorage(tmp_path)
    routes.storage = storage
    try:
        storage.write_state(
            _state(
                "older",
                "Older Debate",
                "2026-05-10T00:00:00+00:00",
                DebatePhase.CREATED,
            )
        )
        storage.write_state(
            _state(
                "newer",
                "Newer Debate",
                "2026-05-11T00:00:00+00:00",
                DebatePhase.CONSENSUS_REACHED,
                has_consensus=True,
            )
        )

        discussions = asyncio.run(routes.list_discussions())
    finally:
        routes.storage = original_storage

    body = [item.model_dump() for item in discussions]
    assert [item["id"] for item in body] == ["newer", "older"]
    assert body[0] == {
        "id": "newer",
        "title": "Newer Debate",
        "phase": "consensus_reached",
        "created_at": "2026-05-11T00:00:00+00:00",
        "updated_at": "2026-05-11T00:00:00+00:00",
        "agent_count": 2,
        "turn_count": 0,
        "has_consensus": True,
    }


def test_delete_debate_removes_discussion_from_storage(tmp_path):
    original_storage = routes.storage
    original_engine = routes.engine
    storage = DebateStorage(tmp_path)
    routes.storage = storage
    routes.engine = DebateEngine(storage, AgentRegistry())
    try:
        storage.write_state(
            _state(
                "delete-me",
                "Delete Me",
                "2026-05-11T00:00:00+00:00",
                DebatePhase.CREATED,
            )
        )

        result = asyncio.run(routes.delete_debate("delete-me"))

        assert result == {"ok": True}
        assert "delete-me" not in storage.list_debates()
        assert not storage.debate_dir("delete-me").exists()
    finally:
        routes.storage = original_storage
        routes.engine = original_engine


def _state(
    debate_id: str,
    title: str,
    updated_at: str,
    phase: DebatePhase,
    has_consensus: bool = False,
) -> DebateState:
    return DebateState(
        id=debate_id,
        title=title,
        user_prompt="Pick a stack.",
        phase=phase,
        created_at=updated_at,
        updated_at=updated_at,
        agents={
            "codex": AgentState(provider=ProviderKind.CODEX, display_name="Codex", model="fake"),
            "gemini": AgentState(provider=ProviderKind.GEMINI, display_name="Gemini", model="fake"),
        },
        turn_order=["codex", "gemini"],
        consensus=ConsensusState(
            final_writer="codex",
            consensus_summary="Done.",
            agreed_by=["codex", "gemini"],
        ) if has_consensus else None,
    )
