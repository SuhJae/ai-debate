import json

from llms import Codex, Gemini, ToolMode
from llms.base import AgentSession, MCPServerConfig, NO_WORKSPACE, NO_WORKSPACE_DIR
from llms.claude import Claude


def test_gemini_probe_uses_yolo_approval_for_headless_tools():
    assert Gemini()._tool_flags(ToolMode.PROBE) == ["--approval-mode", "yolo"]
    cmd = Gemini()._build_start_cmd("probe", ToolMode.PROBE, [])
    assert "--skip-trust" in cmd
    assert cmd[cmd.index("--approval-mode") + 1] == "yolo"


def test_gemini_restricts_mcp_names_even_when_empty():
    cmd = Gemini()._build_start_cmd("prompt", ToolMode.READ_ONLY, [])

    assert "--allowed-mcp-server-names" in cmd
    assert cmd[cmd.index("--allowed-mcp-server-names") + 1] == "__ai_debate_no_mcp__"


def test_codex_receives_global_mcp_config_overrides():
    cmd = Codex()._build_start_cmd(
        "prompt",
        ToolMode.READ_ONLY,
        [
            MCPServerConfig(
                name="docs",
                command_or_url="docs-mcp",
                args=["--root", "/repo"],
                env={"TOKEN": "secret"},
            )
        ],
    )

    assert "mcp_servers={}" in cmd
    assert 'mcp_servers.docs.command="docs-mcp"' in cmd
    assert 'mcp_servers.docs.args=["--root", "/repo"]' in cmd
    assert 'mcp_servers.docs.env={ TOKEN = "secret" }' in cmd


def test_claude_uses_strict_inline_mcp_config():
    cmd = Claude()._build_start_cmd(
        "prompt",
        ToolMode.READ_ONLY,
        [MCPServerConfig(name="docs", command_or_url="https://example.com/mcp", transport="http")],
    )

    assert "--strict-mcp-config" in cmd
    assert "--mcp-config" in cmd
    config = json.loads(cmd[cmd.index("--mcp-config") + 1])
    assert config["mcpServers"]["docs"]["url"] == "https://example.com/mcp"


def test_codex_probe_start_and_resume_bypass_sandbox_for_commands(tmp_path):
    codex = Codex()
    codex.workspace = str(tmp_path)

    start_cmd = codex._session_flags(ToolMode.PROBE)
    assert "--dangerously-bypass-approvals-and-sandbox" in start_cmd
    assert "--skip-git-repo-check" in start_cmd

    session = AgentSession(
        provider="codex",
        session_id="00000000-0000-0000-0000-000000000000",
        model="gpt-5.4",
        tool_mode=ToolMode.PROBE,
    )
    resume_cmd = codex._build_resume_cmd(session, "continue")
    assert "--dangerously-bypass-approvals-and-sandbox" in resume_cmd
    assert "--skip-git-repo-check" in resume_cmd
    assert "--cd" not in resume_cmd


def test_codex_text_only_no_workspace_uses_empty_workspace():
    codex = Codex()
    codex.workspace = NO_WORKSPACE

    cmd = codex._session_flags(ToolMode.TEXT_ONLY)

    assert "--cd" in cmd
    assert cmd[cmd.index("--cd") + 1] == str(NO_WORKSPACE_DIR)


def test_claude_error_result_formats_usage_limit():
    raw = (
        '{"type":"result","is_error":true,"api_error_status":429,'
        '"result":"You\\u0027ve hit your limit · resets 8:50pm (America/Chicago)",'
        '"session_id":"abc"}'
    )
    try:
        Claude()._parse_session_plain(raw)
    except RuntimeError as exc:
        assert "Claude usage limit reached" in str(exc)
        assert "resets 8:50pm" in str(exc)
    else:
        raise AssertionError("Claude error result should raise")


def test_claude_nonzero_session_error_uses_result_event_message():
    raw = "\n".join([
        '{"type":"system","subtype":"init"}',
        (
            '{"type":"result","is_error":true,"api_error_status":429,'
            '"result":"You\\u0027ve hit your limit · resets 8:50pm (America/Chicago)",'
            '"session_id":"abc"}'
        ),
    ])

    detail = Claude()._session_error_detail(raw, "", 1)

    assert detail == "Claude usage limit reached: You've hit your limit · resets 8:50pm (America/Chicago)"


def test_claude_stream_surfaces_tool_use_progress():
    line = json.dumps({
        "type": "content_block_start",
        "content_block": {
            "type": "tool_use",
            "name": "Read",
            "input": {"file_path": "app/pages/chat/[id].vue"},
        },
    })

    chunk = Claude()._parse_stream_line(line)

    assert "[tool] Read app/pages/chat/[id].vue" in chunk


def test_claude_stream_reads_nested_partial_text_delta():
    line = json.dumps({
        "type": "stream_event",
        "event": {
            "type": "content_block_delta",
            "delta": {"type": "text_delta", "text": "partial text"},
        },
    })

    chunk = Claude()._parse_stream_line(line)

    assert chunk == "partial text"


def test_claude_stream_skips_final_assistant_text_when_partials_enabled():
    line = json.dumps({
        "type": "assistant",
        "message": {
            "content": [{"type": "text", "text": "final text"}],
        },
    })

    chunk = Claude()._parse_stream_line(line)

    assert chunk == ""


def test_codex_stream_surfaces_non_message_progress():
    line = json.dumps({
        "type": "item.started",
        "item": {
            "type": "command_execution",
            "command": "rg -n votes app server",
        },
    })

    chunk = Codex()._parse_stream_line(line)

    assert "[tool] started: rg -n votes app server" in chunk


def test_gemini_session_stream_uses_stream_json():
    cmd = Gemini()._build_start_stream_cmd("prompt", ToolMode.READ_ONLY, [])

    assert "--output-format" in cmd
    assert cmd[cmd.index("--output-format") + 1] == "stream-json"


def test_gemini_stream_json_parses_delta_and_final_text():
    gemini = Gemini()
    chunk = gemini._parse_stream_line(json.dumps({
        "type": "message",
        "role": "assistant",
        "content": "OK",
        "delta": True,
    }))
    stdout = "\n".join([
        json.dumps({"type": "init", "session_id": "session-1"}),
        json.dumps({"type": "message", "role": "assistant", "content": "O", "delta": True}),
        json.dumps({"type": "message", "role": "assistant", "content": "K", "delta": True}),
        json.dumps({"type": "result", "status": "success"}),
    ])

    text, session_id, metadata = gemini._parse_session_plain(stdout)

    assert chunk == "OK"
    assert text == "OK"
    assert session_id == "session-1"
    assert metadata["status"] == "success"
