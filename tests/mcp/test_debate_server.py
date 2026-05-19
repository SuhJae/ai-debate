import json
import pytest
from pydantic import ValidationError

from app.mcp.debate_server import (
    accept_consensus,
    debate_tool_manifest,
    record_command_evidence,
    record_file_evidence,
    record_mcp_evidence,
    record_web_evidence,
    propose_consensus,
    reject_consensus,
    submit_thesis,
    submit_debate_turn,
    withdraw_consensus,
)


def test_submit_thesis():
    valid = {
        "type": "thesis",
        "agent": "codex",
        "position": "position",
        "decision": "Concrete Decision",
        "action_plan": ["1", "2", "3"],
        "risks": [],
        "success_criteria": ["A", "B"]
    }
    result_str = submit_thesis(valid)
    result = json.loads(result_str)
    assert result["status"] == "success"
    assert result["event"] == "thesis_submitted"
    assert result["agent"] == "codex"


def test_submit_thesis_invalid():
    invalid = {
        "type": "thesis",
        "agent": "codex",
        # missing fields
    }
    with pytest.raises(ValidationError):
        submit_thesis(invalid)


def test_consensus_tools():
    proposed = json.loads(
        propose_consensus(
            {
                "type": "consensus_action",
                "agent": "codex",
                "final_writer": "codex",
                "consensus_summary": "Use FastAPI with React.",
            }
        )
    )
    assert proposed["event"] == "consensus_proposed"
    assert proposed["writer"] == "codex"

    accepted = json.loads(
        accept_consensus(
            {
                "type": "consensus_action",
                "agent": "gemini",
                "proposal_id": "consensus-001-codex",
            }
        )
    )
    assert accepted["event"] == "consensus_accepted"

    rejected = json.loads(
        reject_consensus(
            {
                "type": "consensus_action",
                "agent": "claude",
                "proposal_id": "consensus-001-codex",
                "reason": "Needs a clearer UI owner.",
            }
        )
    )
    assert rejected["event"] == "consensus_rejected"

    withdrawn = json.loads(
        withdraw_consensus(
            {
                "type": "consensus_action",
                "agent": "claude",
                "proposal_id": "consensus-001-codex",
            }
        )
    )
    assert withdrawn["event"] == "consensus_withdrawn"


def test_debate_tool_manifest_lists_consensus_actions():
    manifest = json.loads(debate_tool_manifest())
    names = {tool["name"] for tool in manifest["tools"]}
    assert {"propose_consensus", "accept_consensus", "reject_consensus", "withdraw_consensus"} <= names
    assert {"record_file_evidence", "record_command_evidence", "record_web_evidence", "record_mcp_evidence"} <= names
    assert "propose_shared_mcp" not in names


def test_evidence_tools_validate_payloads():
    file_result = json.loads(record_file_evidence({
        "summary": "Router exposes debate routes.",
        "path": "app/api/routes.py",
        "line_start": 1,
        "line_end": 20,
        "excerpt": "router = APIRouter(prefix=\"/api\")",
    }))
    assert file_result["event"] == "file_evidence_validated"

    command_result = json.loads(record_command_evidence({
        "summary": "Tests pass.",
        "command": "pytest -q",
        "cwd": "/repo",
        "exit_code": 0,
        "output_summary": "28 passed",
    }))
    assert command_result["event"] == "command_evidence_validated"

    web_result = json.loads(record_web_evidence({
        "summary": "Docs describe the API behavior.",
        "url": "https://example.com/docs",
        "title": "Example Docs",
        "query": "example docs api behavior",
        "snippet": "The API returns JSON.",
    }))
    assert web_result["event"] == "web_evidence_validated"

    mcp_result = json.loads(record_mcp_evidence({
        "summary": "Docs confirm API shape.",
        "mcp_server": "docs",
        "mcp_tool": "search",
    }))
    assert mcp_result["event"] == "mcp_evidence_validated"
