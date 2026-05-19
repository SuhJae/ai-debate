"""Fake LLM adapters for backend tests."""

import json
import time

from llms import AgentSession, LLM, Response, ToolMode


class FakeLLM(LLM):
    name = "Fake"
    cli_bin = "fake"

    def __init__(self, provider: str, scripted_responses: list[str]) -> None:
        self.provider = provider
        self.scripted_responses = list(scripted_responses)
        self.prompts: list[str] = []

    def ask(self, prompt: str, history: list | None = None) -> Response:
        return self._next_response(prompt=prompt)

    def start(self, prompt: str, tool_mode: ToolMode = ToolMode.TEXT_ONLY, mcp_servers=None) -> Response:
        return self._next_response(session_id=f"fake-{self.provider}-session", prompt=prompt)

    def send(self, session: AgentSession, prompt: str) -> Response:
        return self._next_response(session_id=session.session_id, prompt=prompt)

    def _build_cmd(self, prompt: str, history: list) -> list[str]:
        return ["fake", prompt]

    def _build_stream_cmd(self, prompt: str, history: list) -> list[str]:
        return ["fake", prompt]

    def _parse_stream_line(self, line: str) -> str:
        return line

    def _parse_plain(self, stdout: str) -> str:
        return stdout

    def _active_model(self) -> str:
        return "fake-model"

    def _next_response(self, session_id: str | None = None, prompt: str = "") -> Response:
        self.prompts.append(prompt)
        if not self.scripted_responses:
            raise RuntimeError(f"fake {self.provider} responses exhausted")
        if self._is_ack_response(self.scripted_responses[0]) and "Acknowledge" not in prompt:
            self.scripted_responses.pop(0)
        if not self.scripted_responses:
            raise RuntimeError(f"fake {self.provider} responses exhausted")
        return Response(
            text=self.scripted_responses.pop(0),
            model="fake-model",
            cli=self.provider,
            session_id=session_id,
        )

    @staticmethod
    def _is_ack_response(text: str) -> bool:
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return False
        return isinstance(payload, dict) and payload.get("type") == "ack"


class SlowFakeLLM(FakeLLM):
    cli_bin = "slow_fake"

    def __init__(self, provider: str, scripted_responses: list[str], delay: float = 0.05) -> None:
        super().__init__(provider, scripted_responses)
        self.delay = delay

    def start(self, prompt: str, tool_mode: ToolMode = ToolMode.TEXT_ONLY, mcp_servers=None) -> Response:
        time.sleep(self.delay)
        return super().start(prompt, tool_mode, mcp_servers)

    def send(self, session: AgentSession, prompt: str) -> Response:
        time.sleep(self.delay)
        return super().send(session, prompt)
