"""llms/codex.py — OpenAI Codex CLI wrapper (ChatGPT Pro / Plus)."""

import json
from .base import AgentSession, LLM, MCPServerConfig, Message, ToolMode


class Codex(LLM):
    """
    Wraps the `codex` CLI (npm i -g @openai/codex).

    Streaming:  codex exec --json "<prompt>"  → newline-delimited JSON events
    Plain:      codex exec "<prompt>"         → raw text to stdout
    """

    name = "Codex (OpenAI)"
    cli_bin = "codex"
    supports_session_stream = True

    def __init__(self, model: str = "gpt-5.4", sandbox: str = "read-only"):
        """
        Args:
            model:    e.g. "gpt-5.4", "gpt-5.3-codex-spark" (Pro only),
                      "gpt-5.4-mini". Passed as --model flag.
            sandbox:  codex sandbox mode for non-interactive calls.
        """
        self.model = model
        self.sandbox = sandbox

    def _base_flags(self) -> list[str]:
        return [
            self.cli_bin, "exec",
            "--model", self.model,
            "--skip-git-repo-check",
            "--sandbox", self.sandbox,
            "--color", "never",
        ]

    def _session_flags(self, tool_mode: ToolMode) -> list[str]:
        flags = [
            self.cli_bin, "exec",
            "--model", self.model,
            "--skip-git-repo-check",
            "--color", "never",
        ]
        workspace = self._workspace_arg()
        if workspace:
            flags += ["--cd", workspace]
        if tool_mode == ToolMode.FULL:
            return flags + ["--dangerously-bypass-approvals-and-sandbox"]
        if tool_mode == ToolMode.PROBE:
            return flags + ["--dangerously-bypass-approvals-and-sandbox"]
        sandbox = "workspace-write" if tool_mode == ToolMode.EDIT else "read-only"
        return flags + ["--sandbox", sandbox]

    def _build_cmd(self, prompt: str, history: list[Message]) -> list[str]:
        # Codex exec is stateless; history is baked into the prompt string.
        full_prompt = self._flatten(prompt, history)
        return self._base_flags() + [full_prompt]

    def _build_stream_cmd(self, prompt: str, history: list[Message]) -> list[str]:
        full_prompt = self._flatten(prompt, history)
        return self._base_flags() + ["--json", full_prompt]

    def _build_start_cmd(
        self,
        prompt: str,
        tool_mode: ToolMode,
        mcp_servers: list[MCPServerConfig],
    ) -> list[str]:
        return self._session_flags(tool_mode) + self._mcp_config_flags(mcp_servers) + ["--json", prompt]

    def _build_resume_cmd(
        self,
        session: AgentSession,
        prompt: str,
    ) -> list[str]:
        cmd = [
            self.cli_bin, "exec", "resume",
            "--model", self.model,
            "--skip-git-repo-check",
            "--json",
        ]
        if session.tool_mode in {ToolMode.PROBE, ToolMode.FULL}:
            cmd.append("--dangerously-bypass-approvals-and-sandbox")
        return cmd + self._mcp_config_flags(session.mcp_servers) + [session.session_id, prompt]

    def _parse_stream_line(self, line: str) -> str:
        line = line.strip()
        if not line:
            return ""
        try:
            event = json.loads(line)
            etype = event.get("type", "")
            if etype == "item.started":
                return _format_progress_item("started", event.get("item", {}))
            if etype == "item.completed":
                item = event.get("item", {})
                if item.get("type") == "agent_message":
                    return item.get("text", "")
                return _format_progress_item("completed", item)
            # Full assistant message event
            if etype == "message" and event.get("role") == "assistant":
                for block in event.get("content", []):
                    if block.get("type") == "text":
                        return block["text"]
                    if block.get("type") in {"tool_use", "function_call"}:
                        return _format_progress_item("tool", block)
            # Incremental text delta
            if etype == "content_block_delta":
                delta = event.get("delta", {})
                if delta.get("type") == "text_delta":
                    return delta.get("text", "")
        except (json.JSONDecodeError, KeyError):
            pass
        return ""

    def _parse_plain(self, stdout: str) -> str:
        return stdout.strip()

    def _parse_session_plain(self, stdout: str) -> tuple[str, str | None, dict]:
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
            if event.get("type") == "thread.started":
                session_id = event.get("thread_id")
            if event.get("type") == "item.completed":
                item = event.get("item", {})
                if item.get("type") == "agent_message":
                    text_parts.append(item.get("text", ""))
            if event.get("type") == "turn.completed":
                metadata["usage"] = event.get("usage", {})
        return "".join(text_parts).strip(), session_id, metadata

    def _active_model(self) -> str:
        return self.model

    def _workspace_arg(self) -> str | None:
        return self._workspace_path_string()

    @staticmethod
    def _mcp_config_flags(mcp_servers: list[MCPServerConfig]) -> list[str]:
        flags: list[str] = ["-c", "mcp_servers={}"]
        for server in mcp_servers:
            prefix = f"mcp_servers.{server.name}"
            if server.transport == "stdio":
                flags.extend([
                    "-c",
                    f"{prefix}.command={_toml_string(server.command_or_url)}",
                    "-c",
                    f"{prefix}.args={_toml_array(server.args)}",
                ])
                if server.env:
                    flags.extend(["-c", f"{prefix}.env={_toml_table(server.env)}"])
            else:
                flags.extend(["-c", f"{prefix}.url={_toml_string(server.command_or_url)}"])
        return flags

    @staticmethod
    def _flatten(prompt: str, history: list[Message]) -> str:
        """Serialize history into the prompt string (Codex exec is single-shot)."""
        if not history:
            return prompt
        lines = [f"{m.role.upper()}: {m.content}" for m in history]
        lines.append(f"USER: {prompt}")
        return "\n".join(lines)


def _format_progress_item(status: str, item: dict) -> str:
    item_type = str(item.get("type") or "").strip()
    if not item_type or item_type == "agent_message":
        return ""

    if item_type in {"reasoning", "thinking"}:
        return "\n[event] reasoning updated\n"

    label = "tool" if _looks_like_tool_item(item_type, item) else "event"
    name = (
        item.get("name")
        or item.get("tool_name")
        or item.get("command")
        or item.get("title")
        or item_type
    )
    detail = (
        item.get("command")
        or item.get("path")
        or item.get("file_path")
        or item.get("query")
        or item.get("text")
    )
    if isinstance(detail, str):
        detail = " ".join(detail.split())
        if len(detail) > 180:
            detail = detail[:177].rstrip() + "..."
    else:
        detail = ""
    detail_text = f" {detail}" if detail and detail != name else ""
    return f"\n[{label}] {status}: {name}{detail_text}\n"


def _looks_like_tool_item(item_type: str, item: dict) -> bool:
    tool_words = ("tool", "call", "command", "exec", "shell", "patch", "file")
    return any(word in item_type for word in tool_words) or any(
        key in item for key in ("command", "tool_name", "file_path", "path", "query")
    )


def _toml_string(value: str) -> str:
    return json.dumps(value)


def _toml_array(values: list[str]) -> str:
    return "[" + ", ".join(_toml_string(value) for value in values) + "]"


def _toml_table(values: dict[str, str]) -> str:
    return "{ " + ", ".join(f"{_toml_key(key)} = {_toml_string(value)}" for key, value in values.items()) + " }"


def _toml_key(value: str) -> str:
    if value.replace("_", "").replace("-", "").isalnum() and value[0].isalpha():
        return value
    return _toml_string(value)
