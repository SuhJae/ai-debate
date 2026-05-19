"""FastAPI HTTP routes."""

import asyncio
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.websocket import manager
from app.core.agent_registry import (
    AVAILABLE_MODELS,
    DEFAULT_MODELS,
    PROVIDER_CLI_BINS,
    PROVIDER_DISPLAY_NAMES,
    AgentRegistry,
)
from app.core.debate_engine import DebateEngine
from app.core.storage import DebateStorage
from app.models.agent import DebateAgentConfig, ProviderKind
from app.models.artifacts import ArtifactContent
from app.models.debate import DebateState
from app.models.mcp import GlobalMcpServer, McpServerCreateRequest, McpServerUpdateRequest
from llms import Claude, Codex, Gemini, ToolMode

router = APIRouter(prefix="/api")

storage = DebateStorage()
agent_registry = AgentRegistry()
engine = DebateEngine(storage, agent_registry, manager.broadcast)
manager.snapshot_provider = lambda debate_id: _model_dump(storage.read_state(debate_id))


@router.on_event("startup")
async def resume_interrupted_auto_debates() -> None:
    await engine.resume_interrupted_auto_debates()


class CreateDebateRequest(BaseModel):
    title: str
    user_prompt: str
    working_directory: str | None = None
    allow_file_read: bool = False
    allow_probe_commands: bool = False
    allow_web_evidence: bool = True
    agents: list[DebateAgentConfig] | None = None


class WorkspaceValidationRequest(BaseModel):
    path: str


class WorkspaceValidationResponse(BaseModel):
    valid: bool
    normalized_path: str | None = None
    message: str


class AgentTurnRequest(BaseModel):
    agent_id: str | None = None


class AutoModeRequest(BaseModel):
    enabled: bool


class ReorderAgentsRequest(BaseModel):
    turn_order: list[str]


class TextRequest(BaseModel):
    text: str


class ForceConsensusRequest(BaseModel):
    final_writer: str


class ProviderModelInfo(BaseModel):
    id: str
    label: str
    default: bool = False


class ProviderInfo(BaseModel):
    id: ProviderKind
    label: str
    cli: str
    default_model: str
    models: list[ProviderModelInfo]


class LlmProvidersResponse(BaseModel):
    providers: dict[ProviderKind, ProviderInfo]


class DiscussionListItem(BaseModel):
    id: str
    title: str
    phase: str
    created_at: str
    updated_at: str
    agent_count: int
    turn_count: int
    has_consensus: bool = False


@router.get("/health")
async def health() -> dict:
    return {"ok": True}


@router.post("/workspace/validate", response_model=WorkspaceValidationResponse)
async def validate_workspace(request: WorkspaceValidationRequest) -> WorkspaceValidationResponse:
    value = request.path.strip()
    if not value:
        return WorkspaceValidationResponse(valid=False, message="Enter a working directory.")

    try:
        path = Path(value).expanduser()
        if not path.is_dir():
            return WorkspaceValidationResponse(valid=False, message="Directory not found.")
        normalized_path = str(path.resolve())
    except OSError as exc:
        return WorkspaceValidationResponse(valid=False, message=f"Directory could not be checked: {exc}")

    return WorkspaceValidationResponse(
        valid=True,
        normalized_path=normalized_path,
        message="Directory found.",
    )


@router.get("/llms/providers", response_model=LlmProvidersResponse)
async def llm_providers() -> LlmProvidersResponse:
    providers = {}
    for provider in ProviderKind:
        default_model = DEFAULT_MODELS[provider]
        providers[provider] = ProviderInfo(
            id=provider,
            label=PROVIDER_DISPLAY_NAMES[provider],
            cli=PROVIDER_CLI_BINS[provider],
            default_model=default_model,
            models=[
                ProviderModelInfo(
                    id=model,
                    label=model,
                    default=model == default_model,
                )
                for model in AVAILABLE_MODELS[provider]
            ],
        )
    return LlmProvidersResponse(providers=providers)


@router.get("/llms/check")
async def llm_check() -> dict:
    agents = {
        "codex": Codex(),
        "gemini": Gemini(),
        "claude": Claude(),
    }
    results = await asyncio.gather(
        *[_check_one_llm(name, llm) for name, llm in agents.items()],
        return_exceptions=False,
    )
    response = {"agents": dict(results)}
    response["ok"] = all(item["ok"] for item in response["agents"].values())
    return response


@router.post("/debates", response_model=DebateState)
async def create_debate(request: CreateDebateRequest) -> DebateState:
    try:
        return await engine.create_debate(
            title=request.title,
            user_prompt=request.user_prompt,
            allow_file_read=request.allow_file_read,
            allow_probe_commands=request.allow_probe_commands,
            allow_web_evidence=request.allow_web_evidence,
            agent_configs=request.agents,
            working_directory=request.working_directory,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/debates", response_model=list[DebateState])
async def list_debates() -> list[DebateState]:
    return [storage.read_state(debate_id) for debate_id in storage.list_debates()]


@router.get("/discussions", response_model=list[DiscussionListItem])
async def list_discussions() -> list[DiscussionListItem]:
    states = [storage.read_state(debate_id) for debate_id in storage.list_debates()]
    states.sort(key=lambda state: state.updated_at, reverse=True)
    return [
        DiscussionListItem(
            id=state.id,
            title=state.title,
            phase=state.phase.value if hasattr(state.phase, "value") else str(state.phase),
            created_at=state.created_at,
            updated_at=state.updated_at,
            agent_count=len(state.agents),
            turn_count=len(state.rounds),
            has_consensus=state.consensus is not None,
        )
        for state in states
    ]


@router.get("/debates/{debate_id}", response_model=DebateState)
async def get_debate(debate_id: str) -> DebateState:
    return _read_state_or_404(debate_id)


@router.delete("/debates/{debate_id}")
async def delete_debate(debate_id: str) -> dict:
    await engine.delete_debate(debate_id)
    return {"ok": True}


@router.post("/debates/{debate_id}/start-theses", response_model=DebateState)
async def start_theses(debate_id: str) -> DebateState:
    return await _mutate_and_broadcast(debate_id, engine.start_theses(debate_id))


@router.post("/debates/{debate_id}/theses/{agent_id}/regenerate", response_model=DebateState)
async def regenerate_thesis(debate_id: str, agent_id: str) -> DebateState:
    return await _mutate_and_broadcast(debate_id, engine.regenerate_thesis(debate_id, agent_id))


@router.post("/debates/{debate_id}/share-theses", response_model=DebateState)
async def share_theses(debate_id: str) -> DebateState:
    return await _mutate_and_broadcast(debate_id, engine.share_theses(debate_id))


@router.post("/debates/{debate_id}/turn", response_model=DebateState)
async def run_turn(debate_id: str, request: AgentTurnRequest) -> DebateState:
    return await _mutate_and_broadcast(debate_id, engine.run_turn(debate_id, request.agent_id))


@router.post("/debates/{debate_id}/turn/regenerate", response_model=DebateState)
async def regenerate_last_turn(debate_id: str) -> DebateState:
    return await _mutate_and_broadcast(debate_id, engine.regenerate_last_turn(debate_id))


@router.post("/debates/{debate_id}/auto", response_model=DebateState)
async def set_auto_mode(debate_id: str, request: AutoModeRequest) -> DebateState:
    return await _mutate_and_broadcast(debate_id, engine.set_auto_mode(debate_id, request.enabled))


@router.post("/debates/{debate_id}/agents/reorder", response_model=DebateState)
async def reorder_agents(debate_id: str, request: ReorderAgentsRequest) -> DebateState:
    return await _mutate_and_broadcast(debate_id, engine.reorder_agents(debate_id, request.turn_order))


@router.post("/debates/{debate_id}/agents/{agent_id}", response_model=DebateState)
async def update_agent(debate_id: str, agent_id: str, request: DebateAgentConfig) -> DebateState:
    return await _mutate_and_broadcast(debate_id, engine.update_agent(debate_id, agent_id, request))


@router.post("/debates/{debate_id}/pause-after-this", response_model=DebateState)
async def pause_after_this(debate_id: str) -> DebateState:
    return await _mutate_and_broadcast(debate_id, engine.request_pause_after_this(debate_id))


@router.post("/debates/{debate_id}/send-after-this", response_model=DebateState)
async def send_after_this(debate_id: str, request: TextRequest) -> DebateState:
    return await _mutate_and_broadcast(debate_id, engine.set_send_after_this(debate_id, request.text))


@router.post("/debates/{debate_id}/user-opinion", response_model=DebateState)
async def submit_user_opinion(debate_id: str, request: TextRequest) -> DebateState:
    return await _mutate_and_broadcast(debate_id, engine.submit_user_opinion(debate_id, request.text))


@router.post("/debates/{debate_id}/force-consensus", response_model=DebateState)
async def force_consensus(debate_id: str, request: ForceConsensusRequest) -> DebateState:
    return await _mutate_and_broadcast(
        debate_id,
        engine.force_consensus(debate_id, request.final_writer),
    )


@router.post("/debates/{debate_id}/draft-final", response_model=DebateState)
async def draft_final(debate_id: str) -> DebateState:
    return await _mutate_and_broadcast(debate_id, engine.draft_final(debate_id))


@router.post("/debates/{debate_id}/review-final", response_model=DebateState)
async def review_final(debate_id: str) -> DebateState:
    return await _mutate_and_broadcast(debate_id, engine.review_final(debate_id))


@router.get("/mcp/servers", response_model=list[GlobalMcpServer])
async def list_mcp_servers() -> list[GlobalMcpServer]:
    return storage.read_mcp_servers()


@router.post("/mcp/servers", response_model=GlobalMcpServer)
async def create_mcp_server(request: McpServerCreateRequest) -> GlobalMcpServer:
    try:
        return storage.create_mcp_server(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/mcp/servers/{server_id}", response_model=GlobalMcpServer)
async def update_mcp_server(server_id: str, request: McpServerUpdateRequest) -> GlobalMcpServer:
    try:
        return storage.update_mcp_server(server_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=404 if "not found" in str(exc) else 400, detail=str(exc)) from exc


@router.delete("/mcp/servers/{server_id}")
async def delete_mcp_server(server_id: str) -> dict:
    try:
        storage.delete_mcp_server(server_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True}


@router.get("/debates/{debate_id}/artifacts/{artifact_path:path}", response_model=ArtifactContent)
async def read_artifact(debate_id: str, artifact_path: str) -> ArtifactContent:
    try:
        content = storage.read_artifact(debate_id, artifact_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="artifact not found") from exc
    return ArtifactContent(path=artifact_path, content=content)


async def _mutate_and_broadcast(debate_id: str, awaitable) -> DebateState:
    try:
        state = await awaitable
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="debate not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await manager.broadcast(debate_id, {"type": "state_snapshot", "state": _model_dump(state)})
    return state


def _read_state_or_404(debate_id: str) -> DebateState:
    try:
        return storage.read_state(debate_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="debate not found") from exc


def _model_dump(model) -> dict:
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json")
    return model.dict()


async def _check_one_llm(name: str, llm) -> tuple[str, dict]:
    try:
        direct = await asyncio.to_thread(llm.ask, "Reply with exactly: OK")
        first = await asyncio.to_thread(
            llm.start,
            "Remember this codeword: API-CHECK-42. Reply with exactly: OK",
            ToolMode.READ_ONLY,
        )
        session = llm.make_session(first, ToolMode.READ_ONLY)
        second = await asyncio.to_thread(
            llm.send,
            session,
            "What is the codeword? Reply with only the codeword.",
        )
        ok = direct.text.strip() == "OK" and second.text.strip() == "API-CHECK-42"
        return name, {
            "ok": ok,
            "direct": direct.text.strip(),
            "session": second.session_id,
            "resume": second.text.strip(),
            "error": None,
        }
    except Exception as exc:
        return name, {"ok": False, "direct": None, "session": None, "resume": None, "error": str(exc)}
