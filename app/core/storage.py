"""Filesystem storage for debate state, events, and artifacts."""

import json
import shutil
from pathlib import Path

from app.core.state import now_iso
from app.core.events import DebateEvent
from app.models.agent import AGENT_COLOR_SEQUENCE, AgentStatus
from app.models.debate import DebatePhase, DebateState, UserMessageRecord
from app.models.mcp import GlobalMcpServer, McpServerCreateRequest, McpServerUpdateRequest


class DebateStorage:
    def __init__(self, root: Path = Path("debate")) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def create_debate_dir(self, debate_id: str) -> Path:
        base = self.debate_dir(debate_id)
        for relative in ["theses", "rounds", "final", "mcp", "evidence"]:
            (base / relative).mkdir(parents=True, exist_ok=True)
        return base

    def debate_dir(self, debate_id: str) -> Path:
        path = self.root / debate_id
        return path

    def list_debates(self) -> list[str]:
        if not self.root.exists():
            return []
        return sorted(
            path.name
            for path in self.root.iterdir()
            if path.is_dir() and (path / "state.json").exists()
        )

    def delete_debate(self, debate_id: str) -> None:
        path = self.debate_dir(debate_id)
        if path.exists() and path.is_dir():
            shutil.rmtree(path)

    @property
    def mcp_servers_path(self) -> Path:
        return self.root / "mcp_servers.json"

    def read_mcp_servers(self, enabled_only: bool = False) -> list[GlobalMcpServer]:
        path = self.mcp_servers_path
        if not path.exists():
            return []
        data = json.loads(path.read_text() or "[]")
        servers = [
            GlobalMcpServer.model_validate(item)
            if hasattr(GlobalMcpServer, "model_validate")
            else GlobalMcpServer.parse_obj(item)
            for item in data
        ]
        if enabled_only:
            return [server for server in servers if server.enabled]
        return servers

    def create_mcp_server(self, request: McpServerCreateRequest) -> GlobalMcpServer:
        name = request.name.strip()
        command_or_url = request.command_or_url.strip()
        if not name:
            raise ValueError("MCP server name is required")
        if not command_or_url:
            raise ValueError("MCP command or URL is required")

        servers = self.read_mcp_servers()
        server_id = self._unique_mcp_server_id(name, servers)
        now = now_iso()
        server = GlobalMcpServer(
            id=server_id,
            name=name,
            description=request.description.strip(),
            transport=request.transport,
            command_or_url=command_or_url,
            args=request.args,
            env=request.env,
            headers=request.headers,
            enabled=request.enabled,
            trusted=request.trusted,
            created_at=now,
            updated_at=now,
        )
        servers.append(server)
        self.write_mcp_servers(servers)
        return server

    def update_mcp_server(self, server_id: str, request: McpServerUpdateRequest) -> GlobalMcpServer:
        servers = self.read_mcp_servers()
        for index, server in enumerate(servers):
            if server.id != server_id:
                continue

            update = request.model_dump(exclude_unset=True) if hasattr(request, "model_dump") else request.dict(exclude_unset=True)
            if "name" in update:
                update["name"] = str(update["name"]).strip()
                if not update["name"]:
                    raise ValueError("MCP server name is required")
            if "command_or_url" in update:
                update["command_or_url"] = str(update["command_or_url"]).strip()
                if not update["command_or_url"]:
                    raise ValueError("MCP command or URL is required")
            if "description" in update and update["description"] is not None:
                update["description"] = str(update["description"]).strip()

            updated = server.model_copy(update={**update, "updated_at": now_iso()}) if hasattr(server, "model_copy") else server.copy(update={**update, "updated_at": now_iso()})
            servers[index] = updated
            self.write_mcp_servers(servers)
            return updated
        raise ValueError(f"MCP server not found: {server_id}")

    def delete_mcp_server(self, server_id: str) -> None:
        servers = self.read_mcp_servers()
        remaining = [server for server in servers if server.id != server_id]
        if len(remaining) == len(servers):
            raise ValueError(f"MCP server not found: {server_id}")
        self.write_mcp_servers(remaining)

    def write_mcp_servers(self, servers: list[GlobalMcpServer]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self.mcp_servers_path.write_text(json.dumps([_model_dump(server) for server in servers], indent=2) + "\n")

    def read_state(self, debate_id: str) -> DebateState:
        text = (self.debate_dir(debate_id) / "state.json").read_text()
        if hasattr(DebateState, "model_validate_json"):
            state = DebateState.model_validate_json(text)
        else:
            state = DebateState.parse_raw(text)
        changed = self._backfill_agent_colors(state)
        changed = self._backfill_user_messages(state) or changed
        changed = self._dedupe_user_messages(state) or changed
        changed = self._repair_interrupted_final_draft(state) or changed
        if changed:
            (self.debate_dir(debate_id) / "state.json").write_text(_model_json(state) + "\n")
        return state

    def write_state(self, state: DebateState) -> None:
        self._backfill_agent_colors(state)
        base = self.create_debate_dir(state.id)
        (base / "state.json").write_text(_model_json(state) + "\n")

    def append_event(self, event: DebateEvent) -> None:
        base = self.create_debate_dir(event.debate_id)
        with (base / "events.jsonl").open("a") as handle:
            handle.write(_model_json(event, indent=None) + "\n")

    def read_events(self, debate_id: str) -> list[DebateEvent]:
        path = self.debate_dir(debate_id) / "events.jsonl"
        if not path.exists():
            return []
        events: list[DebateEvent] = []
        for line in path.read_text().splitlines():
            if hasattr(DebateEvent, "model_validate_json"):
                events.append(DebateEvent.model_validate_json(line))
            else:
                events.append(DebateEvent.parse_raw(line))
        return events

    def write_artifact(self, debate_id: str, relative_path: str, content: str) -> str:
        path = self._safe_artifact_path(debate_id, relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return relative_path

    def read_artifact(self, debate_id: str, relative_path: str) -> str:
        return self._safe_artifact_path(debate_id, relative_path).read_text()

    def delete_artifact(self, debate_id: str, relative_path: str) -> None:
        path = self._safe_artifact_path(debate_id, relative_path)
        if path.exists() and path.is_file():
            path.unlink()

    def append_transcript(self, debate_id: str, heading: str, content: str) -> None:
        base = self.create_debate_dir(debate_id)
        with (base / "transcript.md").open("a") as handle:
            handle.write(f"\n\n## {heading}\n\n{content.strip()}\n")

    def _safe_artifact_path(self, debate_id: str, relative_path: str) -> Path:
        base = self.create_debate_dir(debate_id).resolve()
        path = (base / relative_path).resolve()
        if base != path and base not in path.parents:
            raise ValueError(f"artifact path escapes debate directory: {relative_path}")
        return path

    @staticmethod
    def _backfill_agent_colors(state: DebateState) -> bool:
        changed = False
        ordered_agent_ids = [
            *[agent_id for agent_id in state.turn_order if agent_id in state.agents],
            *[agent_id for agent_id in state.agents if agent_id not in state.turn_order],
        ]
        for index, agent_id in enumerate(ordered_agent_ids):
            agent = state.agents[agent_id]
            if agent.color:
                continue
            agent.color = AGENT_COLOR_SEQUENCE[index % len(AGENT_COLOR_SEQUENCE)]
            changed = True
        return changed

    @staticmethod
    def _unique_mcp_server_id(name: str, servers: list[GlobalMcpServer]) -> str:
        base = "".join(char.lower() if char.isalnum() else "-" for char in name).strip("-")
        base = "-".join(part for part in base.split("-") if part) or "mcp-server"
        existing = {server.id for server in servers}
        if base not in existing:
            return base
        index = 2
        while f"{base}-{index}" in existing:
            index += 1
        return f"{base}-{index}"

    def _backfill_user_messages(self, state: DebateState) -> bool:
        if state.user_messages:
            return False

        events = self.read_events(state.id)
        completed_rounds = 0
        pending_text: str | None = None
        pending_created_at: str | None = None
        user_messages: list[UserMessageRecord] = []

        for event in events:
            if event.type == "user_opinion_submitted":
                text = str(event.payload.get("text") or "").strip()
                if text:
                    user_messages.append(
                        UserMessageRecord(
                            id=str(event.payload.get("id") or f"user-{len(user_messages) + 1:03d}"),
                            content=text,
                            created_at=event.created_at,
                            after_round=int(event.payload.get("after_round") or completed_rounds),
                        )
                    )
                pending_text = None
                pending_created_at = None
                continue

            if event.type == "send_after_this_set":
                text = str(event.payload.get("text") or "").strip()
                pending_text = text or None
                pending_created_at = event.created_at if text else None
                continue

            if event.type == "turn_completed":
                completed_rounds += 1
                if pending_text:
                    user_messages.append(
                        UserMessageRecord(
                            id=f"user-{len(user_messages) + 1:03d}",
                            content=pending_text,
                            created_at=pending_created_at or event.created_at,
                            after_round=completed_rounds,
                        )
                    )
                    pending_text = None
                    pending_created_at = None

        if not user_messages:
            return False

        state.user_messages = user_messages
        return True

    @staticmethod
    def _dedupe_user_messages(state: DebateState) -> bool:
        if len(state.user_messages) < 2:
            return False

        deduped: list[UserMessageRecord] = []
        seen: set[str] = set()
        for message in sorted(state.user_messages, key=lambda item: (item.after_round, item.created_at, item.id)):
            key = " ".join(message.content.split()).casefold()
            if not key or key in seen:
                continue
            seen.add(key)
            deduped.append(message)

        deduped.sort(key=lambda item: (item.after_round, item.created_at, item.id))
        if len(deduped) == len(state.user_messages):
            return False

        state.user_messages = deduped
        return True

    @staticmethod
    def _repair_interrupted_final_draft(state: DebateState) -> bool:
        if state.phase != DebatePhase.DRAFTING_FINAL:
            return False
        if not state.consensus:
            return False
        if state.final_document and state.final_document.draft_path:
            return False
        if any(agent.status == AgentStatus.RUNNING for agent in state.agents.values()):
            return False

        state.phase = DebatePhase.CONSENSUS_REACHED
        state.updated_at = now_iso()
        return True


def _model_json(model, indent: int | None = 2) -> str:
    if hasattr(model, "model_dump_json"):
        return model.model_dump_json(indent=indent)
    return model.json(indent=indent)


def _model_dump(model) -> dict:
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json")
    return json.loads(model.json())
