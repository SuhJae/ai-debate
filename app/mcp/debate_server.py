import json
from typing import Any

from app.mcp.schemas import (
    ConsensusActionPayload,
    ConsensusSignalPayload,
    DebateTurnPayload,
    EvidencePayload,
    FinalReviewPayload,
    ThesisPayload,
)

# This module simulates the tools exposed by the debate MCP server.
# In a full MCP SDK implementation, these would be decorated with @tool or similar.

def submit_thesis(payload: dict[str, Any]) -> str:
    """Submit an initial thesis. Expected to match ThesisPayload."""
    # Validate payload
    thesis = ThesisPayload(**payload)
    return json.dumps({"status": "success", "event": "thesis_submitted", "agent": thesis.agent.value if hasattr(thesis.agent, "value") else str(thesis.agent)})


def submit_debate_turn(payload: dict[str, Any]) -> str:
    """Submit a debate turn. Expected to match DebateTurnPayload."""
    turn = DebateTurnPayload(**payload)
    return json.dumps({"status": "success", "event": "turn_completed", "agent": turn.agent.value if hasattr(turn.agent, "value") else str(turn.agent)})


def signal_consensus(payload: dict[str, Any]) -> str:
    """Signal consensus on a final writer. Expected to match ConsensusSignalPayload."""
    signal = ConsensusSignalPayload(**payload)
    return json.dumps({"status": "success", "event": "consensus_signaled", "writer": signal.final_writer.value if hasattr(signal.final_writer, "value") else str(signal.final_writer)})


def propose_consensus(payload: dict[str, Any]) -> str:
    """Propose a final consensus package and writer."""
    action = ConsensusActionPayload(**{**payload, "action": "propose"})
    return json.dumps({
        "status": "success",
        "event": "consensus_proposed",
        "agent": action.agent.value if hasattr(action.agent, "value") else str(action.agent),
        "writer": action.final_writer.value if hasattr(action.final_writer, "value") else str(action.final_writer),
    })


def accept_consensus(payload: dict[str, Any]) -> str:
    """Accept an existing consensus proposal."""
    action = ConsensusActionPayload(**{**payload, "action": "accept"})
    return json.dumps({
        "status": "success",
        "event": "consensus_accepted",
        "agent": action.agent.value if hasattr(action.agent, "value") else str(action.agent),
        "proposal_id": action.proposal_id,
    })


def reject_consensus(payload: dict[str, Any]) -> str:
    """Reject an existing consensus proposal with a reason."""
    action = ConsensusActionPayload(**{**payload, "action": "reject"})
    return json.dumps({
        "status": "success",
        "event": "consensus_rejected",
        "agent": action.agent.value if hasattr(action.agent, "value") else str(action.agent),
        "proposal_id": action.proposal_id,
        "reason": action.reason,
    })


def withdraw_consensus(payload: dict[str, Any]) -> str:
    """Withdraw a consensus proposal or the caller's vote on that proposal."""
    action = ConsensusActionPayload(**{**payload, "action": "withdraw"})
    return json.dumps({
        "status": "success",
        "event": "consensus_withdrawn",
        "agent": action.agent.value if hasattr(action.agent, "value") else str(action.agent),
        "proposal_id": action.proposal_id,
    })


def debate_tool_manifest() -> str:
    """Return the debate tools agents should use through protocol JSON or MCP."""
    return json.dumps(
        {
            "tools": [
                {
                    "name": "propose_consensus",
                    "action": "propose",
                    "required": ["agent", "final_writer", "consensus_summary"],
                },
                {
                    "name": "accept_consensus",
                    "action": "accept",
                    "required": ["agent", "proposal_id"],
                },
                {
                    "name": "reject_consensus",
                    "action": "reject",
                    "required": ["agent", "proposal_id", "reason"],
                },
                {
                    "name": "withdraw_consensus",
                    "action": "withdraw",
                    "required": ["agent", "proposal_id"],
                },
                {
                    "name": "record_file_evidence",
                    "required": ["summary", "path", "line_start", "line_end", "excerpt"],
                },
                {
                    "name": "record_command_evidence",
                    "required": ["summary", "command", "cwd", "exit_code", "output_summary"],
                },
                {
                    "name": "record_web_evidence",
                    "required": ["summary", "url", "title", "snippet"],
                    "optional": ["query", "retrieved_at"],
                },
                {
                    "name": "record_mcp_evidence",
                    "required": ["summary", "mcp_server", "mcp_tool"],
                },
            ]
        }
    )


def nominate_final_writer(agent_id: str) -> str:
    """Nominate a final writer independently of a full turn payload."""
    return json.dumps({"status": "success", "event": "final_writer_nominated", "nominee": agent_id})


def submit_final_review(payload: dict[str, Any]) -> str:
    """Submit a review for the final draft. Expected to match FinalReviewPayload."""
    review = FinalReviewPayload(**payload)
    return json.dumps({"status": "success", "event": "final_review_submitted", "verdict": review.verdict.value if hasattr(review.verdict, "value") else str(review.verdict)})


def record_shared_evidence(evidence_name: str, content: str, proposed_by: str) -> str:
    """Record a piece of shared evidence for the debate."""
    return json.dumps({
        "status": "success", 
        "event": "shared_evidence_recorded", 
        "evidence_name": evidence_name,
        "proposed_by": proposed_by
    })


def record_file_evidence(payload: dict[str, Any]) -> str:
    """Validate a file/line evidence payload for the shared evidence ledger."""
    evidence = EvidencePayload(**{**payload, "kind": "file_ref"})
    return json.dumps({
        "status": "success",
        "event": "file_evidence_validated",
        "path": evidence.path,
        "line_start": evidence.line_start,
        "line_end": evidence.line_end,
    })


def record_command_evidence(payload: dict[str, Any]) -> str:
    """Validate a command-result evidence payload for the shared evidence ledger."""
    evidence = EvidencePayload(**{**payload, "kind": "command_result"})
    return json.dumps({
        "status": "success",
        "event": "command_evidence_validated",
        "command": evidence.command,
        "exit_code": evidence.exit_code,
    })


def record_web_evidence(payload: dict[str, Any]) -> str:
    """Validate a web/document search evidence payload for the shared evidence ledger."""
    evidence = EvidencePayload(**{**payload, "kind": "web_ref"})
    return json.dumps({
        "status": "success",
        "event": "web_evidence_validated",
        "url": evidence.url,
        "title": evidence.title,
        "query": evidence.query,
    })


def record_mcp_evidence(payload: dict[str, Any]) -> str:
    """Validate an MCP evidence payload for the shared evidence ledger."""
    evidence = EvidencePayload(**{**payload, "kind": "mcp_ref"})
    return json.dumps({
        "status": "success",
        "event": "mcp_evidence_validated",
        "mcp_server": evidence.mcp_server,
        "mcp_tool": evidence.mcp_tool,
    })
