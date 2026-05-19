from app.core.prompts import (
    build_debate_turn_prompt,
    build_final_draft_prompt,
    build_initial_thesis_prompt,
    build_repair_prompt,
    build_share_theses_prompt,
    SYSTEM_DEBATE_PROMPT
)


def test_build_initial_thesis_prompt():
    prompt = build_initial_thesis_prompt("Build a web app", "codex")
    assert SYSTEM_DEBATE_PROMPT in prompt
    assert "Build a web app" in prompt
    assert "Generate your initial engineering thesis" in prompt
    assert "<file:app/api/websocket.py:41>" in prompt
    assert "Do not write local source locations as URLs" in prompt


def test_text_only_initial_prompt_hides_local_file_features():
    state = DummyState()
    state.tool_mode = "text_only"
    prompt = build_initial_thesis_prompt("Discuss policy", "codex", state)

    assert "<file:app/api/websocket.py:41>" not in prompt
    assert '"kind": "file_ref"' not in prompt
    assert '"kind": "command_result"' not in prompt
    assert '"kind": "web_ref"' in prompt
    assert "Local file references are disabled" in prompt
    assert "Target project workspace" not in prompt


def test_build_repair_prompt():
    prompt = build_repair_prompt('{"bad": "json"}', "Missing type", "ThesisPayload")
    assert "Missing type" in prompt
    assert '{"bad": "json"}' in prompt
    assert "ThesisPayload" in prompt


class DummyState:
    def __init__(self):
        self.theses = {}
        self.agents = {}
        self.turn_order = []
        self.rounds = []
        self.shared_evidence = []
        self.consensus_proposals = []
        self.tool_mode = "read_only"
        self.allow_web_evidence = True
        self.working_directory = "/tmp"


class DummyAgent:
    def __init__(self, debate_style="normal", technical_preference="neutral"):
        self.debate_style = debate_style
        self.technical_preference = technical_preference
        self.additional_note = ""


class DummyThesis:
    def __init__(self, position, decision):
        self.position = position
        self.decision = decision


class DummyConsensusProposal:
    def __init__(self):
        self.id = "consensus-007-bush"
        self.proposer = "bush"
        self.final_writer = "obama"
        self.consensus_summary = "A strange housing compromise with theatrical concessions"
        self.status = "active"
        self.accepted_by = ["bush"]
        self.rejected_by = {}


def test_build_share_theses_prompt():
    state = DummyState()
    state.theses = {
        "gemini": DummyThesis("position a", "decision a"),
        "claude": DummyThesis("position b", "decision b")
    }
    prompt = build_share_theses_prompt(state, "codex")
    assert "decision a" in prompt
    assert "decision b" in prompt
    assert '"agent":"codex"' in prompt


def test_text_only_debate_turn_prompt_hides_local_file_features():
    state = DummyState()
    state.tool_mode = "text_only"
    state.user_prompt = "Discuss policy"
    state.agents = {
        "codex": DummyAgent(),
        "gemini": DummyAgent(),
    }
    state.turn_order = ["codex", "gemini"]
    prompt = build_debate_turn_prompt(state, "codex")

    assert "<file:app/api/websocket.py:41>" not in prompt
    assert '"kind": "file_ref"' not in prompt
    assert '"kind": "command_result"' not in prompt
    assert "Local file references are disabled" in prompt


def test_debate_turn_prompt_teaches_consensus_references():
    state = DummyState()
    state.user_prompt = "Discuss policy"
    state.agents = {
        "bush": DummyAgent("politician", "right"),
        "obama": DummyAgent("politician", "left"),
    }
    state.turn_order = ["bush", "obama"]
    state.consensus_proposals = [DummyConsensusProposal()]

    prompt = build_debate_turn_prompt(state, "obama")

    assert "- <consensus-007-bush>: writer=obama;" in prompt
    assert "for example <consensus-007-bush>" in prompt
    assert "Do not write bare consensus IDs like consensus-001-agent in prose." in prompt
    assert "Do not invent consensus IDs" in prompt


def test_politician_prompt_uses_factions_and_messy_consensus():
    state = DummyState()
    state.user_prompt = "Choose a stack"
    state.agents = {
        "lefty": DummyAgent("politician", "left"),
        "righty": DummyAgent("politician", "right"),
    }
    state.turn_order = ["lefty", "righty"]
    thesis_prompt = build_initial_thesis_prompt("Choose a stack", "lefty", state)
    assert "Politician thesis instruction" in thesis_prompt
    assert "fictionalized entertainment" in thesis_prompt

    prompt = build_debate_turn_prompt(state, "lefty")
    assert "Political entertainment mode is active" in prompt
    assert "<@lefty>=left" in prompt
    assert "theatrical legislator" in prompt
    assert "Politician debate-turn instruction" in prompt
    assert "collaborator would speak in a working design review" not in prompt
    assert "no slurs" in prompt
    assert "<file:app/api/websocket.py:41>" in prompt

    final_prompt = build_final_draft_prompt(state, "lefty")
    assert "Preserve the messy political bargain" in final_prompt
    assert "symbolic riders" in final_prompt
