"""Debate state models."""

from enum import StrEnum

from pydantic import BaseModel, Field

from app.models.agent import AgentState


class DebatePhase(StrEnum):
    CREATED = "created"
    STARTING_THESES = "starting_theses"
    AWAITING_THESES = "awaiting_theses"
    THESES_READY = "theses_ready"
    DEBATING = "debating"
    PAUSE_REQUESTED = "pause_requested"
    PAUSED = "paused"
    CONSENSUS_REACHED = "consensus_reached"
    DRAFTING_FINAL = "drafting_final"
    REVIEWING_FINAL = "reviewing_final"
    REVISING_FINAL = "revising_final"
    ACCEPTED = "accepted"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DebateMode(StrEnum):
    ENGINEERING_DEBATE = "engineering_debate"


class ToolModeName(StrEnum):
    TEXT_ONLY = "text_only"
    READ_ONLY = "read_only"
    PROBE = "probe"
    EDIT = "edit"
    FULL = "full"


class EvidenceKind(StrEnum):
    FILE_REF = "file_ref"
    COMMAND_RESULT = "command_result"
    WEB_REF = "web_ref"
    MCP_REF = "mcp_ref"
    NOTE = "note"


class EvidenceRecord(BaseModel):
    id: str
    agent: str
    kind: EvidenceKind
    summary: str
    source_type: str
    source_id: str
    path: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    excerpt: str | None = None
    command: str | None = None
    cwd: str | None = None
    exit_code: int | None = None
    output_summary: str | None = None
    url: str | None = None
    title: str | None = None
    query: str | None = None
    snippet: str | None = None
    retrieved_at: str | None = None
    mcp_server: str | None = None
    mcp_tool: str | None = None
    created_at: str


class ThesisRecord(BaseModel):
    agent: str
    position: str
    decision: str
    action_plan: list[str]
    risks: list[str]
    success_criteria: list[str]
    evidence_refs: list[str] = Field(default_factory=list)
    artifact_path: str


class DebateTurnRecord(BaseModel):
    index: int
    agent: str
    discussion: str = ""
    agreements: list[str] = Field(default_factory=list)
    disagreements: list[str] = Field(default_factory=list)
    updated_position: str = ""
    proposed_next_action: str = ""
    evidence_refs: list[str] = Field(default_factory=list)
    consensus_action: dict | None = None
    consensus_signal: dict | None = None
    artifact_path: str


class ConsensusProposalState(BaseModel):
    id: str
    proposer: str
    final_writer: str
    consensus_summary: str
    status: str = "active"
    accepted_by: list[str] = Field(default_factory=list)
    rejected_by: dict[str, str] = Field(default_factory=dict)
    created_at: str
    updated_at: str


class ConsensusState(BaseModel):
    final_writer: str
    consensus_summary: str
    agreed_by: list[str]
    forced_by_user: bool = False


class FinalDraftState(BaseModel):
    draft_version: int
    draft_path: str
    created_at: str
    status: str = "drafted"
    accepted_by: list[str] = Field(default_factory=list)
    reviews: dict[str, dict] = Field(default_factory=dict)


class FinalDocumentState(BaseModel):
    draft_version: int = 0
    draft_path: str | None = None
    final_path: str | None = None
    accepted_by: list[str] = Field(default_factory=list)
    drafts: list[FinalDraftState] = Field(default_factory=list)


class UserMessageRecord(BaseModel):
    id: str
    content: str
    created_at: str
    after_round: int = 0


class McpServerState(BaseModel):
    id: str
    name: str
    description: str
    transport: str
    command_or_url: str
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    headers: dict[str, str] = Field(default_factory=dict)
    trusted: bool = False
    proposed_by: str
    status: str
    created_at: str


class DebateState(BaseModel):
    id: str
    title: str
    user_prompt: str
    working_directory: str | None = None
    phase: DebatePhase = DebatePhase.CREATED
    mode: DebateMode = DebateMode.ENGINEERING_DEBATE
    created_at: str
    updated_at: str
    tool_mode: ToolModeName = ToolModeName.TEXT_ONLY
    allow_web_evidence: bool = True
    agents: dict[str, AgentState]
    turn_order: list[str] = Field(default_factory=lambda: ["codex", "gemini", "claude"])
    next_agent: str | None = None
    auto_mode: bool = False
    pause_after_this: bool = False
    send_after_this: str | None = None
    user_messages: list[UserMessageRecord] = Field(default_factory=list)
    theses: dict[str, ThesisRecord] = Field(default_factory=dict)
    rounds: list[DebateTurnRecord] = Field(default_factory=list)
    shared_evidence: list[EvidenceRecord] = Field(default_factory=list)
    consensus_proposals: list[ConsensusProposalState] = Field(default_factory=list)
    consensus: ConsensusState | None = None
    final_document: FinalDocumentState | None = None
    reviews: dict[str, dict] = Field(default_factory=dict)
    mcp_registry: list[McpServerState] = Field(default_factory=list)
