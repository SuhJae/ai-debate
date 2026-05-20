import json
import re
from typing import Any

from app.mcp.schemas import (
    ConsensusAction,
    ConsensusActionPayload,
    DebateTurnPayload,
    FinalReviewPayload,
    ReviewVerdict,
    ThesisPayload,
)


class ValidationError(ValueError):
    pass


def extract_json_object(text: str) -> dict[str, Any]:
    """Extract the first valid top-level JSON object from model output."""
    try:
        # Check if the entire text is valid JSON
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find a JSON block using regex
    # Match from first { to last }
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValidationError("No JSON object found in text")
    
    json_str = match.group(0)
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValidationError(f"Failed to parse extracted JSON: {e}")


def _validate_common(
    payload_dict: dict[str, Any],
    expected_type: str,
    expected_agent: str,
) -> None:
    if "type" not in payload_dict:
        raise ValidationError("Missing 'type' in JSON payload")
    if payload_dict["type"] != expected_type:
        raise ValidationError(f"Expected type '{expected_type}', got '{payload_dict['type']}'")
    
    if "agent" not in payload_dict:
        raise ValidationError("Missing 'agent' in JSON payload")
    if payload_dict["agent"] != expected_agent:
        raise ValidationError(f"Expected agent '{expected_agent}', got '{payload_dict['agent']}'")


def validate_thesis(text: str, expected_agent: str) -> ThesisPayload:
    payload_dict = extract_json_object(text)
    _validate_common(payload_dict, "thesis", expected_agent)

    try:
        thesis = ThesisPayload(**payload_dict)
    except Exception as e:
        raise ValidationError(f"Invalid ThesisPayload schema: {e}")

    return thesis


def validate_debate_turn(text: str, expected_agent: str) -> DebateTurnPayload:
    payload_dict = extract_json_object(text)
    if payload_dict.get("type") == "consensus_action":
        return _validate_standalone_consensus_action(payload_dict, expected_agent)

    _validate_common(payload_dict, "debate_turn", expected_agent)

    try:
        turn = DebateTurnPayload(**payload_dict)
    except Exception as e:
        raise ValidationError(f"Invalid DebateTurnPayload schema: {e}")

    reply_targets = [str(agent) for agent in turn.reply_to if str(agent) != expected_agent]
    if not reply_targets:
        raise ValidationError("Debate turn must reply_to at least one other agent")
    if not turn.discussion.strip():
        raise ValidationError("Debate turn must include discussion")
    if not _mentions_other_agent(turn.discussion, expected_agent, reply_targets):
        raise ValidationError("Discussion must explicitly mention another agent with <@agent>")

    if turn.consensus_action:
        action = turn.consensus_action
        if action.agent != expected_agent:
            raise ValidationError(
                f"Consensus action agent must be '{expected_agent}', got '{action.agent}'"
            )
        if action.action == ConsensusAction.PROPOSE:
            if not action.final_writer:
                raise ValidationError("Consensus propose requires final_writer")
            if not action.consensus_summary or not action.consensus_summary.strip():
                raise ValidationError("Consensus propose requires consensus_summary")
        elif action.action in {ConsensusAction.ACCEPT, ConsensusAction.REJECT, ConsensusAction.WITHDRAW}:
            if not action.proposal_id:
                raise ValidationError(f"Consensus {action.action.value} requires proposal_id")
            if action.action == ConsensusAction.REJECT and not (action.reason or "").strip():
                raise ValidationError("Consensus reject requires reason")

    return turn


def _validate_standalone_consensus_action(
    payload_dict: dict[str, Any],
    expected_agent: str,
) -> DebateTurnPayload:
    """Accept action-only consensus replies as a compact debate turn.

    Agents sometimes follow the consensus examples as if they were tool calls
    and return only the nested consensus action object. Keeping the vote is
    safer than sending it through repair, where the action may be dropped.
    """
    try:
        action = ConsensusActionPayload(**payload_dict)
    except Exception as e:
        raise ValidationError(f"Invalid ConsensusActionPayload schema: {e}")
    if action.agent != expected_agent:
        raise ValidationError(
            f"Consensus action agent must be '{expected_agent}', got '{action.agent}'"
        )

    action_name = action.action.value if hasattr(action.action, "value") else str(action.action)
    proposal_text = f" for <{action.proposal_id}>" if action.proposal_id else ""
    return DebateTurnPayload(
        type="debate_turn",
        agent=expected_agent,
        reply_to=["system"],
        discussion=f"Recorded consensus action: {action_name}{proposal_text}.",
        evidence=[],
        evidence_refs=[],
        consensus_action=action,
        consensus_signal=None,
    )


def _mentions_other_agent(text: str, expected_agent: str, reply_targets: list[str]) -> bool:
    lowered = text.lower()
    return any(
        f"<@{target.lower()}>" in lowered
        for target in reply_targets
    )


def validate_final_review(text: str, expected_agent: str) -> FinalReviewPayload:
    payload_dict = extract_json_object(text)
    _validate_common(payload_dict, "final_review", expected_agent)

    try:
        review = FinalReviewPayload(**payload_dict)
    except Exception as e:
        raise ValidationError(f"Invalid FinalReviewPayload schema: {e}")

    if review.verdict == ReviewVerdict.REJECT and not review.required_changes:
        raise ValidationError("Rejection must include required_changes")
    
    if review.verdict == ReviewVerdict.ACCEPT and review.required_changes:
        raise ValidationError("Acceptance cannot include required_changes")

    return review


def validate_final_markdown(text: str) -> str:
    """Return markdown if required headings exist; otherwise raise ValidationError."""
    required_headings = [
        "# Final Engineering Thesis",
        "## Decision",
        "## Rationale",
        "## Implementation Plan",
        "## Risks",
        "## Acceptance Criteria"
    ]
    
    missing = []
    for heading in required_headings:
        # Allow extra whitespace or trailing text but ensure the heading exists
        # To be safe, just check if the literal string is in the text
        if heading not in text:
            missing.append(heading)
            
    if missing:
        raise ValidationError(f"Missing required markdown headings: {', '.join(missing)}")
        
    return text
