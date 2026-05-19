"""llms/claude.py — Anthropic Claude Code CLI wrapper (Claude Pro)."""

import json
from .base import AgentSession, LLM, MCPServerConfig, Message, ToolMode


class Claude(LLM):
    """
    Wraps the `claude` CLI (npm i -g @anthropic-ai/claude-code).

    Streaming:  claude -p "<prompt>" --output-format stream-json
                → newline-delimited JSON events
    Plain:      claude -p "<prompt>"
                → raw text to stdout
    """

    name = "Claude Code (Anthropic)"
    cli_bin = "claude"
    supports_session_stream = True

    def __init__(self, model: str = "claude-sonnet-4-6",
                 allowed_tools: str = "Read"):
        """
        Args:
            model:         Claude model string passed as --model.
            allowed_tools: Comma-separated tools Claude may use autonomously.
                           "Read" is safe for Q&A. Add "Edit,Bash" for coding tasks.
                           Use "none" to disable all tool use (pure text generation).
        """
        self.model = model
        self.allowed_tools = allowed_tools

    def _base_flags(self) -> list[str]:
        flags = [self.cli_bin, "-p", "--model", self.model]
        if self.allowed_tools and self.allowed_tools != "none":
            flags += ["--allowedTools", self.allowed_tools]
        return flags

    def _build_cmd(self, prompt: str, history: list[Message]) -> list[str]:
        full_prompt = self._flatten(prompt, history)
        # Insert prompt right after "-p"
        cmd = [self.cli_bin, "-p", full_prompt, "--model", self.model]
        if self.allowed_tools and self.allowed_tools != "none":
            cmd += ["--allowedTools", self.allowed_tools]
        return cmd

    def _tool_flags(self, tool_mode: ToolMode) -> list[str]:
        if tool_mode == ToolMode.FULL:
            return ["--dangerously-skip-permissions"]
        tools_by_mode = {
            ToolMode.TEXT_ONLY: "",
            ToolMode.READ_ONLY: "Read,Glob,Grep",
            ToolMode.PROBE: "Read,Glob,Grep,Bash",
            ToolMode.EDIT: "Read,Glob,Grep,Bash,Edit,Write",
        }
        return ["--tools", tools_by_mode[tool_mode]]

    def _mcp_flags(self, mcp_servers: list[MCPServerConfig]) -> list[str]:
        mcp_config = {"mcpServers": {}}
        for server in mcp_servers:
            if server.transport == "stdio":
                mcp_config["mcpServers"][server.name] = {
                    "command": server.command_or_url,
                    "args": server.args,
                    "env": server.env,
                }
            else:
                mcp_config["mcpServers"][server.name] = {
                    "type": server.transport,
                    "url": server.command_or_url,
                    "headers": server.headers,
                }
        return ["--strict-mcp-config", "--mcp-config", json.dumps(mcp_config)]

    def _build_start_cmd(
        self,
        prompt: str,
        tool_mode: ToolMode,
        mcp_servers: list[MCPServerConfig],
    ) -> list[str]:
        return [
            self.cli_bin, "-p", prompt,
            "--model", self.model,
            "--output-format", "json",
        ] + self._tool_flags(tool_mode) + self._mcp_flags(mcp_servers)

    def _build_start_stream_cmd(
        self,
        prompt: str,
        tool_mode: ToolMode,
        mcp_servers: list[MCPServerConfig],
    ) -> list[str]:
        return [
            self.cli_bin, "-p", prompt,
            "--model", self.model,
            "--output-format", "stream-json",
            "--verbose",
            "--include-partial-messages",
        ] + self._tool_flags(tool_mode) + self._mcp_flags(mcp_servers)

    def _build_resume_cmd(
        self,
        session: AgentSession,
        prompt: str,
    ) -> list[str]:
        return [
            self.cli_bin, "-p", prompt,
            "--model", self.model,
            "--resume", session.session_id,
            "--output-format", "json",
        ] + self._tool_flags(session.tool_mode) + self._mcp_flags(session.mcp_servers)

    def _build_resume_stream_cmd(
        self,
        session: AgentSession,
        prompt: str,
    ) -> list[str]:
        return [
            self.cli_bin, "-p", prompt,
            "--model", self.model,
            "--resume", session.session_id,
            "--output-format", "stream-json",
            "--verbose",
            "--include-partial-messages",
        ] + self._tool_flags(session.tool_mode) + self._mcp_flags(session.mcp_servers)

    def _build_stream_cmd(self, prompt: str, history: list[Message]) -> list[str]:
        return self._build_cmd(prompt, history) + [
            "--output-format", "stream-json", "--verbose", "--include-partial-messages"
        ]

    def _parse_stream_line(self, line: str) -> str:
        line = line.strip()
        if not line:
            return ""
        try:
            event = json.loads(line)
            payload = event.get("event") if event.get("type") == "stream_event" else event
            if not isinstance(payload, dict):
                return ""

            etype = payload.get("type", "")
            if etype == "assistant":
                for block in payload.get("message", {}).get("content", []):
                    if block.get("type") == "text":
                        # With --include-partial-messages enabled, text arrives
                        # through content_block_delta. Returning the final
                        # assistant message here would duplicate the stream.
                        return ""
                    if block.get("type") == "tool_use":
                        return _format_tool_use(block)
            # Incremental text delta (primary streaming event)
            if etype == "content_block_start":
                block = payload.get("content_block", {})
                if block.get("type") == "tool_use":
                    return _format_tool_use(block)
            if etype == "content_block_delta":
                delta = payload.get("delta", {})
                if delta.get("type") == "text_delta":
                    return delta.get("text", "")
            if etype == "tool_result":
                return _format_tool_result(payload)
        except (json.JSONDecodeError, KeyError):
            pass
        return ""

    def _parse_plain(self, stdout: str) -> str:
        return stdout.strip()

    def _parse_session_plain(self, stdout: str) -> tuple[str, str | None, dict]:
        event = self._result_event(stdout)
        if isinstance(event, list):
            event = next(
                (item for item in event if isinstance(item, dict) and item.get("type") == "result"),
                event[-1] if event else {},
            )
        if event.get("is_error"):
            raise RuntimeError(_format_claude_error(event))
        return event.get("result", "").strip(), event.get("session_id"), event

    def _active_model(self) -> str:
        return self.model

    @staticmethod
    def _result_event(stdout: str):
        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            result = None
            for raw_line in stdout.splitlines():
                raw_line = raw_line.strip()
                if not raw_line:
                    continue
                try:
                    event = json.loads(raw_line)
                except json.JSONDecodeError:
                    continue
                if isinstance(event, dict) and event.get("type") == "result":
                    result = event
            if result is not None:
                return result
            raise

    @staticmethod
    def _flatten(prompt: str, history: list[Message]) -> str:
        if not history:
            return prompt
        lines = [f"{m.role.upper()}: {m.content}" for m in history]
        lines.append(f"USER: {prompt}")
        return "\n".join(lines)


def _format_claude_error(event: dict) -> str:
    result = str(event.get("result") or "").strip()
    status = event.get("api_error_status")
    if status == 429:
        return f"Claude usage limit reached: {result or 'rate limited'}"
    if result:
        return result
    if status:
        return f"Claude API error status {status}"
    return "Claude returned an error result"


def _format_tool_use(block: dict) -> str:
    name = str(block.get("name") or "tool").strip()
    tool_input = block.get("input")
    if isinstance(tool_input, dict):
        detail = (
            tool_input.get("command")
            or tool_input.get("file_path")
            or tool_input.get("path")
            or tool_input.get("pattern")
            or tool_input.get("query")
        )
    else:
        detail = tool_input
    detail_text = f" {detail}" if detail else ""
    return f"\n\n[tool] {name}{detail_text}\n"


def _format_tool_result(event: dict) -> str:
    content = event.get("content")
    if isinstance(content, list):
        text = " ".join(
            str(item.get("text", "")).strip()
            for item in content
            if isinstance(item, dict) and item.get("text")
        )
    else:
        text = str(content or "").strip()
    text = " ".join(text.split())
    if len(text) > 220:
        text = text[:217].rstrip() + "..."
    return f"\n[tool result] {text}\n" if text else "\n[tool result]\n"
