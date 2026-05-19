from app.core.events import new_event
from app.core.state import new_debate_id, transition
from app.core.storage import DebateStorage
from app.models.agent import AgentId, AgentState, AgentStatus
from app.models.debate import ConsensusState, DebatePhase, DebateState
from app.models.mcp import McpServerCreateRequest, McpServerUpdateRequest


def test_transition_rejects_invalid_jump():
    state = _state()
    try:
        transition(state, DebatePhase.ACCEPTED)
    except ValueError as exc:
        assert "invalid phase transition" in str(exc)
    else:
        raise AssertionError("invalid transition should fail")


def test_storage_round_trip(tmp_path):
    storage = DebateStorage(tmp_path)
    state = _state()
    storage.write_state(state)
    storage.append_event(new_event(state.id, "debate_created", "user", {"title": state.title}))
    storage.write_artifact(state.id, "theses/codex.md", "# Thesis\n")

    loaded = storage.read_state(state.id)
    assert loaded.id == state.id
    assert storage.read_events(state.id)[0].type == "debate_created"
    assert storage.read_artifact(state.id, "theses/codex.md") == "# Thesis\n"
    assert storage.list_debates() == [state.id]


def test_storage_repairs_interrupted_final_draft(tmp_path):
    storage = DebateStorage(tmp_path)
    state = _state()
    state.phase = DebatePhase.DRAFTING_FINAL
    state.consensus = ConsensusState(
        final_writer=AgentId.CODEX,
        consensus_summary="Ship the agreed plan.",
        agreed_by=[AgentId.CODEX, AgentId.GEMINI, AgentId.CLAUDE],
    )
    state.agents[AgentId.CODEX].status = AgentStatus.FAILED
    storage.write_state(state)

    loaded = storage.read_state(state.id)

    assert loaded.phase == DebatePhase.CONSENSUS_REACHED


def test_storage_keeps_active_final_draft_running(tmp_path):
    storage = DebateStorage(tmp_path)
    state = _state()
    state.phase = DebatePhase.DRAFTING_FINAL
    state.consensus = ConsensusState(
        final_writer=AgentId.CODEX,
        consensus_summary="Ship the agreed plan.",
        agreed_by=[AgentId.CODEX, AgentId.GEMINI, AgentId.CLAUDE],
    )
    state.agents[AgentId.CODEX].status = AgentStatus.RUNNING
    storage.write_state(state)

    loaded = storage.read_state(state.id)

    assert loaded.phase == DebatePhase.DRAFTING_FINAL


def test_storage_manages_global_mcp_servers(tmp_path):
    storage = DebateStorage(tmp_path)

    server = storage.create_mcp_server(
        McpServerCreateRequest(
            name="Docs MCP",
            command_or_url="docs-mcp",
            args=["--stdio"],
            env={"TOKEN": "secret"},
        )
    )

    assert server.id == "docs-mcp"
    assert storage.read_mcp_servers(enabled_only=True)[0].name == "Docs MCP"

    updated = storage.update_mcp_server(
        server.id,
        McpServerUpdateRequest(enabled=False, trusted=True),
    )

    assert updated.enabled is False
    assert updated.trusted is True
    assert storage.read_mcp_servers(enabled_only=True) == []

    storage.delete_mcp_server(server.id)
    assert storage.read_mcp_servers() == []


def test_new_debate_id_is_slugged():
    debate_id = new_debate_id("Use FastAPI + React")
    assert debate_id.endswith("use-fastapi-react")


def _state() -> DebateState:
    return DebateState(
        id="test-debate",
        title="Test Debate",
        user_prompt="Pick a stack.",
        created_at="2026-05-10T00:00:00+00:00",
        updated_at="2026-05-10T00:00:00+00:00",
        agents={
            AgentId.CODEX: AgentState(provider=AgentId.CODEX, display_name="Codex", model="fake"),
            AgentId.GEMINI: AgentState(provider=AgentId.GEMINI, display_name="Gemini", model="fake"),
            AgentId.CLAUDE: AgentState(provider=AgentId.CLAUDE, display_name="Claude", model="fake"),
        },
    )
