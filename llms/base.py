"""llms/base.py — shared interface all CLI wrappers implement."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
import os
from pathlib import Path
from typing import Callable, Iterator

NO_WORKSPACE = "__ai_debate_no_workspace__"
NO_WORKSPACE_DIR = Path("/tmp/ai-debate-no-workspace")


class ToolMode(Enum):
    """Provider-neutral access level for a model invocation."""

    TEXT_ONLY = "text_only"
    READ_ONLY = "read_only"
    PROBE = "probe"
    EDIT = "edit"
    FULL = "full"


@dataclass
class Message:
    role: str   # "user" | "assistant"
    content: str


@dataclass
class MCPServerConfig:
    """
    Declarative MCP server attachment.

    Some CLIs can receive this inline per invocation; others require the server
    to be registered in their native config first. The wrappers expose the same
    shape so higher-level orchestration code can reason about shared tools.
    """

    name: str
    command_or_url: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    transport: str = "stdio"  # "stdio" | "http" | "sse"
    headers: dict[str, str] = field(default_factory=dict)
    trusted: bool = False


@dataclass
class AgentSession:
    provider: str
    session_id: str
    model: str
    tool_mode: ToolMode = ToolMode.TEXT_ONLY
    mcp_servers: list[MCPServerConfig] = field(default_factory=list)


@dataclass
class Response:
    text: str
    model: str
    cli: str                        # e.g. "codex", "claude", "gemini"
    session_id: str | None = None
    metadata: dict = field(default_factory=dict)


class LLM(ABC):
    """
    Shared interface for CLI-backed LLM wrappers.

    Subclasses must implement:
      - _build_cmd(prompt, history)  → list[str]
      - _parse_stream_line(line)     → str   (chunk or "")
      - _parse_plain(stdout)         → str

    Public API (ready to use):
      - ask(prompt, history?)        → Response          (blocking)
      - stream(prompt, history?)     → Iterator[str]     (token-by-token)
      - start(prompt, tool_mode?)    → Response          (new session)
      - send(session, prompt)        → Response          (resume session)
    """

    name: str       # human label, set in subclass
    cli_bin: str    # executable name, set in subclass
    supports_session_stream: bool = False

    # ── must override ─────────────────────────────────────────────

    @abstractmethod
    def _build_cmd(self, prompt: str, history: list[Message]) -> list[str]:
        """Return the full argv list for a single non-interactive call."""

    @abstractmethod
    def _build_stream_cmd(self, prompt: str, history: list[Message]) -> list[str]:
        """Return argv for a streaming call (may be same as _build_cmd)."""

    @abstractmethod
    def _parse_stream_line(self, line: str) -> str:
        """Extract a text chunk from one raw stdout line. Return '' to skip."""

    @abstractmethod
    def _parse_plain(self, stdout: str) -> str:
        """Extract final text from the complete stdout of a plain call."""

    def _build_start_cmd(
        self,
        prompt: str,
        tool_mode: ToolMode,
        mcp_servers: list[MCPServerConfig],
    ) -> list[str]:
        """Return argv for a new session-aware call."""
        return self._build_cmd(prompt, [])

    def _build_start_stream_cmd(
        self,
        prompt: str,
        tool_mode: ToolMode,
        mcp_servers: list[MCPServerConfig],
    ) -> list[str]:
        """Return argv for a streaming new session-aware call."""
        return self._build_start_cmd(prompt, tool_mode, mcp_servers)

    def _build_resume_cmd(
        self,
        session: AgentSession,
        prompt: str,
    ) -> list[str]:
        """Return argv for a native session continuation."""
        raise NotImplementedError(f"{self.cli_bin} does not implement session resume")

    def _build_resume_stream_cmd(
        self,
        session: AgentSession,
        prompt: str,
    ) -> list[str]:
        """Return argv for a streaming native session continuation."""
        return self._build_resume_cmd(session, prompt)

    def _parse_session_plain(self, stdout: str) -> tuple[str, str | None, dict]:
        """Extract (text, session_id, metadata) from session-aware stdout."""
        return self._parse_plain(stdout), None, {}

    # ── public API ────────────────────────────────────────────────

    def ask(self, prompt: str, history: list[Message] | None = None) -> Response:
        """Blocking call. Returns a Response with the full reply."""
        import subprocess
        cmd = self._build_cmd(prompt, history or [])
        try:
            result = subprocess.run(
                cmd, text=True, capture_output=True, stdin=subprocess.DEVNULL,
                timeout=120, cwd=self._workspace_cwd(),
            )
            if result.returncode != 0:
                detail = self._session_error_detail(result.stdout, result.stderr, result.returncode)
                raise RuntimeError(f"{self.cli_bin} failed: {detail}")
            text = self._parse_plain(result.stdout)
            return Response(text=text, model=self._active_model(), cli=self.cli_bin)
        except FileNotFoundError:
            raise RuntimeError(f"{self.cli_bin} not found — is it installed?")
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"{self.cli_bin} timed out")

    def stream(self, prompt: str, history: list[Message] | None = None) -> Iterator[str]:
        """Streaming call. Yields text chunks as they arrive from the CLI."""
        import subprocess
        cmd = self._build_stream_cmd(prompt, history or [])
        try:
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL, text=True, bufsize=1,
                cwd=self._workspace_cwd(),
            )
            for raw_line in proc.stdout:
                chunk = self._parse_stream_line(raw_line)
                if chunk:
                    yield chunk
            returncode = proc.wait(timeout=120)
            if returncode != 0:
                detail = proc.stderr.read().strip() if proc.stderr else ""
                if not detail:
                    detail = f"exit code {returncode}"
                raise RuntimeError(f"{self.cli_bin} failed: {detail}")
        except FileNotFoundError:
            raise RuntimeError(f"{self.cli_bin} not found — is it installed?")
        except subprocess.TimeoutExpired:
            proc.kill()
            raise RuntimeError(f"{self.cli_bin} timed out")

    def start(
        self,
        prompt: str,
        tool_mode: ToolMode = ToolMode.TEXT_ONLY,
        mcp_servers: list[MCPServerConfig] | None = None,
    ) -> Response:
        """Start a native CLI conversation and return its session id when exposed."""
        response = self._run_session_cmd(
            self._build_start_cmd(prompt, tool_mode, mcp_servers or [])
        )
        response.metadata["tool_mode"] = tool_mode.value
        response.metadata["mcp_servers"] = [server.name for server in mcp_servers or []]
        return response

    def start_stream(
        self,
        prompt: str,
        tool_mode: ToolMode = ToolMode.TEXT_ONLY,
        mcp_servers: list[MCPServerConfig] | None = None,
        on_chunk: Callable[[str], None] | None = None,
    ) -> Response:
        """Start a native CLI conversation and forward visible text chunks when supported."""
        response = self._run_session_cmd_stream(
            self._build_start_stream_cmd(prompt, tool_mode, mcp_servers or []),
            on_chunk,
        )
        response.metadata["tool_mode"] = tool_mode.value
        response.metadata["mcp_servers"] = [server.name for server in mcp_servers or []]
        return response

    def send(self, session: AgentSession, prompt: str) -> Response:
        """Send a prompt to an existing native CLI conversation."""
        response = self._run_session_cmd(self._build_resume_cmd(session, prompt))
        if response.session_id is None:
            response.session_id = session.session_id
        response.metadata["tool_mode"] = session.tool_mode.value
        response.metadata["mcp_servers"] = [server.name for server in session.mcp_servers]
        return response

    def send_stream(
        self,
        session: AgentSession,
        prompt: str,
        on_chunk: Callable[[str], None] | None = None,
    ) -> Response:
        """Send a prompt to an existing conversation and forward visible chunks."""
        response = self._run_session_cmd_stream(
            self._build_resume_stream_cmd(session, prompt),
            on_chunk,
        )
        if response.session_id is None:
            response.session_id = session.session_id
        response.metadata["tool_mode"] = session.tool_mode.value
        response.metadata["mcp_servers"] = [server.name for server in session.mcp_servers]
        return response

    def make_session(
        self,
        response: Response,
        tool_mode: ToolMode = ToolMode.TEXT_ONLY,
        mcp_servers: list[MCPServerConfig] | None = None,
    ) -> AgentSession:
        """Build an AgentSession from a start() response."""
        if not response.session_id:
            raise RuntimeError(f"{self.cli_bin} did not return a session id")
        return AgentSession(
            provider=self.cli_bin,
            session_id=response.session_id,
            model=response.model,
            tool_mode=tool_mode,
            mcp_servers=mcp_servers or [],
        )

    def _run_session_cmd(self, cmd: list[str]) -> Response:
        import subprocess
        try:
            result = subprocess.run(
                cmd, text=True, capture_output=True, stdin=subprocess.DEVNULL,
                timeout=120, cwd=self._workspace_cwd(),
            )
            if result.returncode != 0:
                detail = self._session_error_detail(result.stdout, result.stderr, result.returncode)
                raise RuntimeError(f"{self.cli_bin} failed: {detail}")
            text, session_id, metadata = self._parse_session_plain(result.stdout)
            if result.stderr.strip():
                metadata["stderr"] = result.stderr.strip()
            return Response(
                text=text,
                model=self._active_model(),
                cli=self.cli_bin,
                session_id=session_id,
                metadata=metadata,
            )
        except FileNotFoundError:
            raise RuntimeError(f"{self.cli_bin} not found — is it installed?")
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"{self.cli_bin} timed out")

    def _run_session_cmd_stream(
        self,
        cmd: list[str],
        on_chunk: Callable[[str], None] | None = None,
    ) -> Response:
        import subprocess
        try:
            proc = subprocess.Popen(
                cmd,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                bufsize=1,
                cwd=self._workspace_cwd(),
            )
            stdout_parts: list[str] = []
            assert proc.stdout is not None
            for raw_line in proc.stdout:
                stdout_parts.append(raw_line)
                chunk = self._parse_stream_line(raw_line)
                if chunk and on_chunk:
                    on_chunk(chunk)
            try:
                returncode = proc.wait(timeout=120)
            except subprocess.TimeoutExpired:
                proc.kill()
                raise RuntimeError(f"{self.cli_bin} timed out")
            stderr = proc.stderr.read().strip() if proc.stderr else ""
            stdout = "".join(stdout_parts)
            if returncode != 0:
                detail = self._session_error_detail(stdout, stderr, returncode)
                raise RuntimeError(f"{self.cli_bin} failed: {detail}")
            text, session_id, metadata = self._parse_session_plain(stdout)
            if stderr:
                metadata["stderr"] = stderr
            return Response(
                text=text,
                model=self._active_model(),
                cli=self.cli_bin,
                session_id=session_id,
                metadata=metadata,
            )
        except FileNotFoundError:
            raise RuntimeError(f"{self.cli_bin} not found — is it installed?")

    # ── optional override ─────────────────────────────────────────

    def _active_model(self) -> str:
        """Override to return the model string if the CLI exposes it."""
        return "unknown"

    def _session_error_detail(self, stdout: str, stderr: str, returncode: int) -> str:
        if stdout.strip():
            try:
                self._parse_session_plain(stdout)
            except Exception as exc:
                detail = str(exc).strip()
                if detail:
                    return detail
        detail = (stderr or stdout).strip()
        return detail or f"exit code {returncode}"

    def _workspace_cwd(self) -> str | None:
        """Run provider CLIs from the target project selected by the launcher."""
        return self._workspace_path_string()

    def _workspace_path_string(self) -> str | None:
        workspace = getattr(self, "workspace", None) or os.environ.get("AI_DEBATE_WORKSPACE")
        if not workspace:
            return None
        if workspace == NO_WORKSPACE:
            NO_WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
            return str(NO_WORKSPACE_DIR)
        path = Path(workspace).expanduser()
        if path.is_dir():
            return str(path)
        return None

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} cli={self.cli_bin!r}>"
