"""llms/gemini.py — Google Gemini CLI wrapper (free / AI Premium)."""

import json

from .base import AgentSession, LLM, MCPServerConfig, Message, ToolMode


class Gemini(LLM):
    """
    Wraps the `gemini` CLI (npm i -g @google/gemini-cli).

    Streaming:  gemini --yolo -p "<prompt>"  → plain text to stdout (native)
    Plain:      same command, captured in full

    --yolo suppresses all interactive approval prompts, required for
    non-interactive / scripted use.
    """

    name = "Gemini (Google)"
    cli_bin = "gemini"
    supports_session_stream = True

    def __init__(self, model: str = "gemini-2.5-pro", yolo: bool = True):
        """
        Args:
            model:  Gemini model string, passed as --model.
                    Defaults to gemini-2.5-pro (available on AI Premium).
            yolo:   Auto-approve all tool actions. Set False only if you
                    want Gemini to pause and ask before running commands.
        """
        self.model = model
        self.yolo = yolo

    def _base_flags(self) -> list[str]:
        flags = [self.cli_bin, "--model", self.model, "--skip-trust"]
        if self.yolo:
            flags.append("--yolo")
        return flags

    def _build_cmd(self, prompt: str, history: list[Message]) -> list[str]:
        return self._base_flags() + ["-p", self._flatten(prompt, history)]

    def _build_stream_cmd(self, prompt: str, history: list[Message]) -> list[str]:
        return self._base_flags() + [
            "-p", self._flatten(prompt, history),
            "--output-format", "stream-json",
        ]

    def _tool_flags(self, tool_mode: ToolMode) -> list[str]:
        if tool_mode == ToolMode.TEXT_ONLY:
            return ["--approval-mode", "plan"]
        if tool_mode == ToolMode.READ_ONLY:
            return ["--approval-mode", "plan"]
        if tool_mode == ToolMode.PROBE:
            return ["--approval-mode", "yolo"]
        if tool_mode == ToolMode.EDIT:
            return ["--approval-mode", "auto_edit"]
        return ["--approval-mode", "yolo"]

    def _mcp_flags(self, mcp_servers: list[MCPServerConfig]) -> list[str]:
        # Gemini attaches MCP servers from native config. Restricting by name is
        # useful when a shared project MCP registry has multiple servers.
        names = [server.name for server in mcp_servers]
        return ["--allowed-mcp-server-names", ",".join(names) if names else "__ai_debate_no_mcp__"]

    def _build_start_cmd(
        self,
        prompt: str,
        tool_mode: ToolMode,
        mcp_servers: list[MCPServerConfig],
    ) -> list[str]:
        return [
            self.cli_bin, "--model", self.model,
            "--skip-trust",
            "-p", prompt,
            "--output-format", "json",
        ] + self._tool_flags(tool_mode) + self._mcp_flags(mcp_servers)

    def _build_start_stream_cmd(
        self,
        prompt: str,
        tool_mode: ToolMode,
        mcp_servers: list[MCPServerConfig],
    ) -> list[str]:
        return [
            self.cli_bin, "--model", self.model,
            "--skip-trust",
            "-p", prompt,
            "--output-format", "stream-json",
        ] + self._tool_flags(tool_mode) + self._mcp_flags(mcp_servers)

    def _build_resume_cmd(
        self,
        session: AgentSession,
        prompt: str,
    ) -> list[str]:
        return [
            self.cli_bin, "--model", self.model,
            "--skip-trust",
            "--resume", session.session_id,
            "-p", prompt,
            "--output-format", "json",
        ] + self._tool_flags(session.tool_mode) + self._mcp_flags(session.mcp_servers)

    def _build_resume_stream_cmd(
        self,
        session: AgentSession,
        prompt: str,
    ) -> list[str]:
        return [
            self.cli_bin, "--model", self.model,
            "--skip-trust",
            "--resume", session.session_id,
            "-p", prompt,
            "--output-format", "stream-json",
        ] + self._tool_flags(session.tool_mode) + self._mcp_flags(session.mcp_servers)

    def _parse_stream_line(self, line: str) -> str:
        stripped = line.strip()
        if not stripped:
            return ""
        try:
            event = json.loads(stripped)
        except json.JSONDecodeError:
            return line

        if event.get("type") == "message" and event.get("role") == "assistant":
            return event.get("content", "")
        return ""

    def _parse_plain(self, stdout: str) -> str:
        return stdout.strip()

    def _parse_session_plain(self, stdout: str) -> tuple[str, str | None, dict]:
        start = stdout.find("{")
        if start > 0:
            stdout = stdout[start:]
        try:
            event = json.loads(stdout)
            return event.get("response", "").strip(), event.get("session_id"), event
        except json.JSONDecodeError:
            text_parts: list[str] = []
            session_id: str | None = None
            metadata: dict = {}
            for raw_line in stdout.splitlines():
                raw_line = raw_line.strip()
                if not raw_line:
                    continue
                try:
                    event = json.loads(raw_line)
                except json.JSONDecodeError:
                    continue
                if event.get("type") == "init":
                    session_id = event.get("session_id")
                elif event.get("type") == "message" and event.get("role") == "assistant":
                    text_parts.append(event.get("content", ""))
                elif event.get("type") == "result":
                    metadata = event
            return "".join(text_parts).strip(), session_id, metadata

    def _active_model(self) -> str:
        return self.model

    @staticmethod
    def _flatten(prompt: str, history: list[Message]) -> str:
        if not history:
            return prompt
        lines = [f"{m.role.upper()}: {m.content}" for m in history]
        lines.append(f"USER: {prompt}")
        return "\n".join(lines)
