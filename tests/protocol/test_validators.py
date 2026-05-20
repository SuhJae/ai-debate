import json
import pytest

from app.core.validators import (
    ValidationError,
    extract_json_object,
    validate_thesis,
    validate_final_markdown,
    validate_debate_turn,
    validate_final_review
)

# Dummy AgentId for tests since we don't have the real enum
class DummyAgentId:
    pass


def test_extract_json_object():
    valid_json = '{"key": "value"}'
    assert extract_json_object(valid_json) == {"key": "value"}
    
    embedded_json = 'Here is some text: {"key": "value"} and more text'
    assert extract_json_object(embedded_json) == {"key": "value"}
    
    with pytest.raises(ValidationError):
        extract_json_object("Just some text")


def test_validate_thesis_success():
    valid = {
        "type": "thesis",
        "agent": "codex",
        "position": "position",
        "decision": "Concrete Decision",
        "action_plan": ["1", "2", "3"],
        "risks": [],
        "success_criteria": ["A", "B"]
    }
    thesis = validate_thesis(json.dumps(valid), "codex")
    assert thesis.decision == "Concrete Decision"


def test_validate_thesis_allows_judgment_calls():
    valid = {
        "type": "thesis",
        "agent": "codex",
        "position": "position",
        "decision": "Use GET /api/chats/[id]/votes or maybe replace it later",
        "action_plan": ["1", "2", "3"],
        "risks": [],
        "success_criteria": ["A", "B"]
    }
    thesis = validate_thesis(json.dumps(valid), "codex")
    assert thesis.decision == valid["decision"]


def test_validate_thesis_wrong_agent():
    valid = {
        "type": "thesis",
        "agent": "gemini",
        "position": "position",
        "decision": "Concrete",
        "action_plan": ["1", "2", "3"],
        "risks": [],
        "success_criteria": ["A", "B"]
    }
    with pytest.raises(ValidationError, match="Expected agent 'codex'"):
        validate_thesis(json.dumps(valid), "codex")


def test_validate_final_markdown():
    valid_md = """
# Final Engineering Thesis
## Decision
We chose FastAPI.
## Rationale
It is fast.
## Implementation Plan
1. Do this.
## Risks
None
## Acceptance Criteria
It works.
"""
    assert validate_final_markdown(valid_md) == valid_md
    
    invalid_md = """
# Final Engineering Thesis
## Decision
We chose FastAPI.
"""
    with pytest.raises(ValidationError, match="Missing required markdown headings"):
        validate_final_markdown(invalid_md)


def test_validate_final_review_reject():
    reject = {
        "type": "final_review",
        "agent": "claude",
        "verdict": "reject",
        "reason": "bad plan",
        "required_changes": []
    }
    with pytest.raises(ValidationError, match="Rejection must include required_changes"):
        validate_final_review(json.dumps(reject), "claude")

    reject["required_changes"] = ["Fix the DB schema"]
    review = validate_final_review(json.dumps(reject), "claude")
    assert review.verdict == "reject"


def test_validate_debate_turn_requires_discussion():
    valid = {
        "type": "debate_turn",
        "agent": "codex",
        "reply_to": ["gemini"],
        "discussion": "I like what <@gemini> said about validators; it keeps the protocol deterministic.",
        "consensus_action": None,
        "consensus_signal": None,
    }
    turn = validate_debate_turn(json.dumps(valid), "codex")
    assert turn.discussion.startswith("I like what <@gemini> said")

    invalid = dict(valid)
    invalid["discussion"] = "I still prefer what @gemini said."
    with pytest.raises(ValidationError, match="mention another agent"):
        validate_debate_turn(json.dumps(invalid), "codex")


def test_validate_debate_turn_consensus_action_requirements():
    invalid = {
        "type": "debate_turn",
        "agent": "codex",
        "reply_to": ["gemini"],
        "discussion": "I like what <@gemini> said about consensus; it needs explicit votes.",
        "consensus_action": {
            "type": "consensus_action",
            "agent": "codex",
            "action": "propose",
            "final_writer": "codex",
        },
        "consensus_signal": None,
    }
    with pytest.raises(ValidationError, match="consensus_summary"):
        validate_debate_turn(json.dumps(invalid), "codex")


def test_validate_debate_turn_accepts_standalone_consensus_action():
    payload = {
        "type": "consensus_action",
        "agent": "codexAnalyst",
        "action": "accept",
        "proposal_id": "consensus-007-claud",
    }

    turn = validate_debate_turn(json.dumps(payload), "codexAnalyst")

    assert turn.type == "debate_turn"
    assert turn.agent == "codexAnalyst"
    assert turn.consensus_action is not None
    assert turn.consensus_action.action == "accept"
    assert turn.consensus_action.proposal_id == "consensus-007-claud"
