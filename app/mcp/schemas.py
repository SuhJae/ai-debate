from enum import StrEnum
from pydantic import BaseModel, Field, model_validator


class ThesisPayload(BaseModel):
    type: str
    agent: str
    position: str
    decision: str
    action_plan: list[str] = Field(min_length=3)
    risks: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(min_length=2)
    evidence: list["EvidencePayload"] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


class EvidenceKind(StrEnum):
    FILE_REF = "file_ref"
    COMMAND_RESULT = "command_result"
    WEB_REF = "web_ref"
    MCP_REF = "mcp_ref"
    NOTE = "note"


class EvidencePayload(BaseModel):
    kind: EvidenceKind
    summary: str
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

    @model_validator(mode="after")
    def validate_kind_fields(self):
        if not self.summary.strip():
            raise ValueError("evidence summary is required")
        if self.kind == EvidenceKind.FILE_REF:
            if not self.path:
                raise ValueError("file_ref evidence requires path")
            if self.line_start is None or self.line_end is None:
                raise ValueError("file_ref evidence requires line_start and line_end")
            if self.line_start < 1 or self.line_end < self.line_start:
                raise ValueError("file_ref evidence line range is invalid")
        if self.kind == EvidenceKind.COMMAND_RESULT:
            if not self.command:
                raise ValueError("command_result evidence requires command")
            if self.exit_code is None:
                raise ValueError("command_result evidence requires exit_code")
            if not (self.output_summary or "").strip():
                raise ValueError("command_result evidence requires output_summary")
        if self.kind == EvidenceKind.WEB_REF:
            if not self.url:
                raise ValueError("web_ref evidence requires url")
            if not (self.title or "").strip():
                raise ValueError("web_ref evidence requires title")
            if not (self.snippet or "").strip():
                raise ValueError("web_ref evidence requires snippet")
        if self.kind == EvidenceKind.MCP_REF:
            if not self.mcp_server or not self.mcp_tool:
                raise ValueError("mcp_ref evidence requires mcp_server and mcp_tool")
        return self


class ConsensusSignalPayload(BaseModel):
    agreed: bool
    final_writer: str
    consensus_summary: str


class ConsensusAction(StrEnum):
    PROPOSE = "propose"
    ACCEPT = "accept"
    REJECT = "reject"
    WITHDRAW = "withdraw"


class ConsensusActionPayload(BaseModel):
    type: str = "consensus_action"
    agent: str
    action: ConsensusAction
    proposal_id: str | None = None
    final_writer: str | None = None
    consensus_summary: str | None = None
    reason: str | None = None

    @model_validator(mode="after")
    def validate_action_requirements(self):
        if self.type != "consensus_action":
            raise ValueError("type must be consensus_action")
        if self.action == ConsensusAction.PROPOSE:
            if self.final_writer is None:
                raise ValueError("propose requires final_writer")
            if not (self.consensus_summary or "").strip():
                raise ValueError("propose requires consensus_summary")
        if self.action in {ConsensusAction.ACCEPT, ConsensusAction.REJECT, ConsensusAction.WITHDRAW}:
            if not self.proposal_id:
                raise ValueError(f"{self.action.value} requires proposal_id")
        if self.action == ConsensusAction.REJECT and not (self.reason or "").strip():
            raise ValueError("reject requires reason")
        return self


class DebateTurnPayload(BaseModel):
    type: str
    agent: str
    reply_to: list[str]
    discussion: str
    agreements: list[str] = Field(default_factory=list)
    disagreements: list[str] = Field(default_factory=list)
    updated_position: str = ""
    proposed_next_action: str = ""
    evidence: list[EvidencePayload] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    consensus_action: ConsensusActionPayload | None = None
    consensus_signal: ConsensusSignalPayload | None = None


class ReviewVerdict(StrEnum):
    ACCEPT = "accept"
    REJECT = "reject"


class FinalReviewPayload(BaseModel):
    type: str
    agent: str
    verdict: ReviewVerdict
    reason: str
    required_changes: list[str] = Field(default_factory=list)


class McpProposalPayload(BaseModel):
    type: str
    name: str
    description: str
    transport: str
    command_or_url: str
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    headers: dict[str, str] = Field(default_factory=dict)
    reason: str
