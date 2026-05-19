"""Debate orchestration engine."""

import asyncio
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Awaitable, Callable

from llms import MCPServerConfig, ToolMode

from app.core.agent_registry import AgentRegistry
from app.core.events import new_event
from app.core.state import new_debate_id, now_iso, transition
from app.core.storage import DebateStorage
from app.core.tool_modes import resolve_tool_mode
from app.models.agent import AGENT_COLOR_SEQUENCE, AgentStatus, DebateAgentConfig
from app.models.debate import (
    ConsensusProposalState,
    ConsensusState,
    DebatePhase,
    DebateState,
    DebateTurnRecord,
    EvidenceRecord,
    FinalDraftState,
    FinalDocumentState,
    ThesisRecord,
    ToolModeName,
    UserMessageRecord,
)


class DebateEngine:
    def __init__(
        self,
        storage: DebateStorage,
        agents: AgentRegistry,
        broadcaster: Callable[[str, dict], Awaitable[None]] | None = None,
    ) -> None:
        self.storage = storage
        self.agents = agents
        self.broadcaster = broadcaster
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._thesis_runs: dict[str, set[str]] = {}
        self._auto_runs: set[str] = set()

    def _build_agent_states(self, configs: list[DebateAgentConfig] | None) -> dict[str, Any]:
        if not configs:
            return self.agents.default_agent_states()
        seen: set[str] = set()
        agents = {}
        for index, config in enumerate(configs):
            if config.name in seen:
                raise ValueError(f"duplicate debate agent name: {config.name}")
            seen.add(config.name)
            agents[config.name] = self.agents.state_from_config(config)
            if not agents[config.name].color:
                agents[config.name].color = AGENT_COLOR_SEQUENCE[index % len(AGENT_COLOR_SEQUENCE)]
        if len(agents) < 2:
            raise ValueError("a debate needs at least two agents")
        if not any(agent.write_thesis for agent in agents.values()):
            raise ValueError("at least one agent must be selected to write a thesis")
        return agents

    async def create_debate(
        self,
        title: str,
        user_prompt: str,
        allow_file_read: bool = False,
        allow_probe_commands: bool = False,
        allow_web_evidence: bool = True,
        agent_configs: list[DebateAgentConfig] | None = None,
        working_directory: str | None = None,
    ) -> DebateState:
        tool_mode = resolve_tool_mode(allow_file_read, allow_probe_commands)
        workspace = self._normalize_working_directory(working_directory)
        debate_id = new_debate_id(title)
        now = now_iso()
        agents = self._build_agent_states(agent_configs)
        state = DebateState(
            id=debate_id,
            title=title,
            user_prompt=user_prompt,
            working_directory=workspace,
            created_at=now,
            updated_at=now,
            tool_mode=ToolModeName(tool_mode.value),
            allow_web_evidence=allow_web_evidence,
            agents=agents,
            turn_order=list(agents),
        )
        self.storage.write_state(state)
        self.storage.append_event(
            new_event(
                debate_id,
                "debate_created",
                "user",
                {
                    "title": title,
                    "tool_mode": tool_mode.value,
                    "working_directory": workspace,
                    "allow_web_evidence": allow_web_evidence,
                },
            )
        )
        return state

    @staticmethod
    def _normalize_working_directory(working_directory: str | None) -> str | None:
        if working_directory is None:
            return None
        value = working_directory.strip()
        if not value:
            return None
        path = Path(value).expanduser()
        if not path.is_dir():
            raise ValueError(f"working directory does not exist: {working_directory}")
        return str(path.resolve())

    async def delete_debate(self, debate_id: str) -> None:
        async with self._locks[debate_id]:
            self.storage.delete_debate(debate_id)

    async def start_theses(self, debate_id: str) -> DebateState:
        async with self._locks[debate_id]:
            state = self.storage.read_state(debate_id)
            if self._thesis_runs.get(debate_id):
                return state
            if state.phase == DebatePhase.THESES_READY:
                return state
            state = self._enter_starting_theses(state)
            started_agent_ids = [
                agent_id for agent_id in state.turn_order
                if state.agents[agent_id].status != AgentStatus.DISABLED
                and state.agents[agent_id].write_thesis
                and agent_id not in state.theses
            ]
            self._thesis_runs.setdefault(debate_id, set()).update(started_agent_ids)
            self.storage.write_state(state)
            event = new_event(debate_id, "phase_changed", "system", {"phase": state.phase.value})
            self.storage.append_event(event)
            snapshot = _model_dump(state)
        await self._broadcast(debate_id, {"type": "event", "event": _model_dump(event)})
        await self._broadcast(debate_id, {"type": "state_snapshot", "state": snapshot})

        try:
            prompt_builder, validator = self._protocol_functions("build_initial_thesis_prompt", "validate_thesis")
            tool_mode = ToolMode(state.tool_mode.value)
            tasks = [
                self._start_one_thesis(state.id, agent_id, prompt_builder, validator, tool_mode)
                for agent_id in started_agent_ids
            ]
            await asyncio.gather(*tasks)

            async with self._locks[debate_id]:
                state = self.storage.read_state(debate_id)
                expected_theses = [
                    agent_id for agent_id in state.turn_order
                    if state.agents[agent_id].status != AgentStatus.DISABLED
                    and state.agents[agent_id].write_thesis
                ]
                should_share_theses = False
                queued_event = None
                if not state.theses or any(agent_id not in state.theses for agent_id in expected_theses):
                    state = self._force_phase(state, DebatePhase.FAILED)
                else:
                    state = self._force_phase(state, DebatePhase.AWAITING_THESES)
                    state = transition(state, DebatePhase.THESES_READY)
                    should_share_theses = state.auto_mode
                    queued_event = self._flush_send_after_this_locked(state)
                self.storage.write_state(state)
                event = new_event(debate_id, "phase_changed", "system", {"phase": state.phase.value})
                self.storage.append_event(event)
                if queued_event:
                    self.storage.append_event(queued_event)
                snapshot = _model_dump(state)
            await self._broadcast(debate_id, {"type": "event", "event": _model_dump(event)})
            await self._broadcast(debate_id, {"type": "state_snapshot", "state": snapshot})
            if should_share_theses:
                state = await self.share_theses(debate_id)
                return await self._maybe_continue_auto_mode(debate_id, state)
            async with self._locks[debate_id]:
                state = self.storage.read_state(debate_id)
            return await self._maybe_continue_auto_mode(debate_id, state)
        finally:
            async with self._locks[debate_id]:
                self._clear_thesis_runs(debate_id, started_agent_ids)

    async def regenerate_thesis(self, debate_id: str, agent_id: str) -> DebateState:
        async with self._locks[debate_id]:
            state = self.storage.read_state(debate_id)
            if agent_id not in state.agents:
                raise ValueError(f"unknown agent: {agent_id}")
            if agent_id in self._thesis_runs.get(debate_id, set()):
                raise RuntimeError(f"thesis generation is already running for {agent_id}")
            if not state.agents[agent_id].write_thesis:
                raise ValueError(f"agent {agent_id} is not configured to write a thesis")
            if state.agents[agent_id].status == AgentStatus.RUNNING:
                raise RuntimeError(f"agent {agent_id} is already running")
            if state.rounds:
                raise ValueError("cannot regenerate thesis after thesis sharing has started")
            if state.phase not in {
                DebatePhase.CREATED,
                DebatePhase.STARTING_THESES,
                DebatePhase.AWAITING_THESES,
                DebatePhase.THESES_READY,
                DebatePhase.FAILED,
            }:
                raise ValueError(f"cannot regenerate thesis in phase {state.phase}")

            state.theses.pop(agent_id, None)
            agent = state.agents[agent_id]
            agent.status = AgentStatus.QUEUED
            agent.last_error = None
            state = self._force_phase(state, DebatePhase.STARTING_THESES)
            self._thesis_runs.setdefault(debate_id, set()).add(agent_id)
            self.storage.write_state(state)
            event = new_event(
                debate_id,
                "thesis_regeneration_requested",
                agent_id,
                {"agent": agent_id},
            )
            self.storage.append_event(event)
            snapshot = _model_dump(state)
        await self._broadcast(debate_id, {"type": "event", "event": _model_dump(event)})
        await self._broadcast(debate_id, {"type": "state_snapshot", "state": snapshot})

        try:
            prompt_builder, validator = self._protocol_functions("build_initial_thesis_prompt", "validate_thesis")
            tool_mode = ToolMode(state.tool_mode.value)
            await self._start_one_thesis(state.id, agent_id, prompt_builder, validator, tool_mode)

            async with self._locks[debate_id]:
                self._clear_thesis_runs(debate_id, [agent_id])
                state = self.storage.read_state(debate_id)
                expected_theses = [
                    candidate_id for candidate_id in state.turn_order
                    if candidate_id in state.agents
                    and state.agents[candidate_id].status != AgentStatus.DISABLED
                    and state.agents[candidate_id].write_thesis
                ]
                should_share_theses = False
                queued_event = None
                active_thesis_runs = self._thesis_runs.get(debate_id, set())
                if active_thesis_runs:
                    state = self._force_phase(state, DebatePhase.STARTING_THESES)
                elif expected_theses and all(candidate_id in state.theses for candidate_id in expected_theses):
                    state = self._force_phase(state, DebatePhase.THESES_READY)
                    should_share_theses = state.auto_mode
                    queued_event = self._flush_send_after_this_locked(state)
                else:
                    state = self._force_phase(state, DebatePhase.FAILED)
                self.storage.write_state(state)
                event = new_event(debate_id, "phase_changed", "system", {"phase": state.phase.value})
                self.storage.append_event(event)
                if queued_event:
                    self.storage.append_event(queued_event)
                snapshot = _model_dump(state)
            await self._broadcast(debate_id, {"type": "event", "event": _model_dump(event)})
            await self._broadcast(debate_id, {"type": "state_snapshot", "state": snapshot})
            if should_share_theses:
                state = await self.share_theses(debate_id)
                return await self._maybe_continue_auto_mode(debate_id, state)
            async with self._locks[debate_id]:
                state = self.storage.read_state(debate_id)
            return await self._maybe_continue_auto_mode(debate_id, state)
        finally:
            async with self._locks[debate_id]:
                self._clear_thesis_runs(debate_id, [agent_id])

    async def share_theses(self, debate_id: str) -> DebateState:
        async with self._locks[debate_id]:
            state = self.storage.read_state(debate_id)
            if state.phase in {
                DebatePhase.DEBATING,
                DebatePhase.PAUSED,
                DebatePhase.CONSENSUS_REACHED,
                DebatePhase.DRAFTING_FINAL,
                DebatePhase.REVIEWING_FINAL,
                DebatePhase.REVISING_FINAL,
                DebatePhase.ACCEPTED,
            }:
                return await self._maybe_continue_auto_mode(debate_id, state)
            if state.phase != DebatePhase.THESES_READY:
                raise ValueError(f"cannot share theses in phase {state.phase}")

            state = transition(state, DebatePhase.DEBATING)
            self.storage.write_state(state)
            self.storage.append_event(
                new_event(
                    debate_id,
                    "theses_shared",
                    "system",
                    {"agents": list(state.theses)},
                )
            )
            self.storage.append_event(new_event(debate_id, "phase_changed", "system", {"phase": state.phase.value}))
        return await self._maybe_continue_auto_mode(debate_id, state)

    async def run_turn(self, debate_id: str, agent_id: str | None = None) -> DebateState:
        prompt_builder, validator = self._protocol_functions("build_debate_turn_prompt", "validate_debate_turn")
        async with self._locks[debate_id]:
            state = self.storage.read_state(debate_id)
            if state.phase == DebatePhase.FAILED:
                state = self._recover_failed_for_turn(state)
            if state.phase in {DebatePhase.THESES_READY, DebatePhase.PAUSED, DebatePhase.CONSENSUS_REACHED}:
                state = transition(state, DebatePhase.DEBATING)
            if state.phase != DebatePhase.DEBATING:
                raise ValueError(f"cannot run debate turn in phase {state.phase}")
            running = [
                agent_id
                for agent_id, agent in state.agents.items()
                if agent.status == AgentStatus.RUNNING
            ]
            if running:
                raise RuntimeError(f"cannot run debate turn while running: {', '.join(sorted(running))}")
            selected = str(agent_id) if agent_id else self._next_agent(state)
            if selected not in state.agents:
                raise ValueError(f"unknown debate agent: {selected}")
            queued_event = None
            if state.send_after_this:
                queued_event = self._flush_send_after_this_locked(state)
            state.agents[selected].status = AgentStatus.RUNNING
            state.agents[selected].last_error = None
            state.next_agent = selected
            self.storage.write_state(state)
            if queued_event:
                self.storage.append_event(queued_event)
            snapshot = _model_dump(state)

        await self._broadcast(debate_id, {"type": "state_snapshot", "state": snapshot})
        await self._broadcast(
            debate_id,
            {"type": "agent_status", "agent": selected, "status": AgentStatus.RUNNING.value},
        )

        tool_mode = ToolMode(state.tool_mode.value)
        prompt = self._with_tool_mode_instruction(
            prompt_builder(state, selected, self._user_context_since_last_turn(state)),
            tool_mode,
            state,
        )
        try:
            response = await self._send_or_start_agent(state, selected, prompt, tool_mode, stream=True)
            payload = await self._validate_with_repair(
                debate_id,
                selected,
                response.text,
                validator,
                "DebateTurnPayload",
                tool_mode,
            )
            state = await self._record_turn(debate_id, selected, payload)
        except Exception as exc:
            state = await self._record_agent_error(debate_id, selected, exc)
            raise

        async with self._locks[debate_id]:
            state = self.storage.read_state(debate_id)
            if state.pause_after_this:
                state.pause_after_this = False
                state = transition(state, DebatePhase.PAUSED)
            elif state.consensus:
                state = transition(state, DebatePhase.CONSENSUS_REACHED)
            self.storage.write_state(state)
        return await self._maybe_continue_auto_mode(debate_id, state)

    async def regenerate_last_turn(self, debate_id: str) -> DebateState:
        async with self._locks[debate_id]:
            state = self.storage.read_state(debate_id)
            if state.phase not in {
                DebatePhase.DEBATING,
                DebatePhase.PAUSED,
                DebatePhase.CONSENSUS_REACHED,
            }:
                raise ValueError(f"cannot regenerate discussion turn in phase {state.phase}")
            if not state.rounds:
                raise ValueError("cannot regenerate discussion turn because no rounds exist")
            running = [
                agent_id for agent_id, agent in state.agents.items()
                if agent.status == AgentStatus.RUNNING
            ]
            if running:
                raise RuntimeError(f"cannot regenerate discussion while running: {', '.join(sorted(running))}")

            last_turn = state.rounds[-1]
            state.rounds.pop()
            if last_turn.artifact_path:
                self.storage.delete_artifact(debate_id, last_turn.artifact_path)
            state.shared_evidence = [
                evidence for evidence in state.shared_evidence
                if not (evidence.source_type == "turn" and evidence.source_id == str(last_turn.index))
            ]
            self._rebuild_consensus_state(state)
            if last_turn.agent in state.agents:
                state.agents[last_turn.agent].status = AgentStatus.QUEUED
                state.agents[last_turn.agent].last_error = None
                state.agents[last_turn.agent].session_id = None
            state = self._force_phase(state, DebatePhase.DEBATING)
            self._write_evidence_artifact(debate_id, state)
            self.storage.write_state(state)
            self.storage.append_event(
                new_event(
                    debate_id,
                    "turn_regeneration_requested",
                    "user",
                    {"round": last_turn.index, "agent": last_turn.agent},
                )
            )
            snapshot = _model_dump(state)

        await self._broadcast(debate_id, {"type": "state_snapshot", "state": snapshot})
        return await self.run_turn(debate_id, last_turn.agent)

    async def _maybe_continue_auto_mode(
        self,
        debate_id: str,
        current_state: DebateState | None = None,
    ) -> DebateState:
        state = current_state or self.storage.read_state(debate_id)
        if state.auto_mode:
            self._schedule_auto_mode(debate_id)
        return state

    def _schedule_auto_mode(self, debate_id: str) -> None:
        if debate_id in self._auto_runs:
            return
        self._auto_runs.add(debate_id)
        asyncio.create_task(self._run_auto_mode(debate_id))

    async def _run_auto_mode(self, debate_id: str) -> None:
        try:
            try:
                for _ in range(64):
                    async with self._locks[debate_id]:
                        state = self.storage.read_state(debate_id)
                        if (
                            not state.auto_mode
                            or state.pause_after_this
                            or self._has_running_agent(state)
                            or state.phase in {
                                DebatePhase.ACCEPTED,
                                DebatePhase.CANCELLED,
                                DebatePhase.FAILED,
                                DebatePhase.STARTING_THESES,
                                DebatePhase.AWAITING_THESES,
                                DebatePhase.PAUSED,
                            }
                        ):
                            return

                    if state.phase == DebatePhase.CREATED:
                        state = await self.start_theses(debate_id)
                    elif state.phase == DebatePhase.THESES_READY:
                        state = await self.share_theses(debate_id)
                    elif state.phase == DebatePhase.DEBATING:
                        state = await self.run_turn(debate_id)
                    elif state.phase == DebatePhase.CONSENSUS_REACHED:
                        state = await self.draft_final(debate_id)
                    elif state.phase == DebatePhase.REVIEWING_FINAL:
                        state = await self.review_final(debate_id)
                    elif state.phase == DebatePhase.REVISING_FINAL:
                        state = await self.draft_final(debate_id)
                    else:
                        return

                    await self._broadcast(debate_id, {"type": "state_snapshot", "state": _model_dump(state)})

                async with self._locks[debate_id]:
                    state = self.storage.read_state(debate_id)
                    state.auto_mode = False
                    state = self._force_phase(state, DebatePhase.PAUSED)
                    self.storage.write_state(state)
                    self.storage.append_event(
                        new_event(
                            debate_id,
                            "auto_mode_stopped",
                            "system",
                            {"reason": "maximum auto steps reached"},
                        )
                    )
                    snapshot = _model_dump(state)
                await self._broadcast(debate_id, {"type": "state_snapshot", "state": snapshot})
            except Exception as exc:
                await self._stop_auto_mode_for_error(debate_id, exc)
                return
        finally:
            self._auto_runs.discard(debate_id)

    async def _stop_auto_mode_for_error(self, debate_id: str, exc: Exception) -> DebateState:
        error = str(exc)
        if len(error) > 1200:
            error = f"{error[:1197].rstrip()}..."
        async with self._locks[debate_id]:
            state = self.storage.read_state(debate_id)
            state.auto_mode = False
            state.pause_after_this = False
            state.updated_at = now_iso()
            self.storage.write_state(state)
            event = new_event(
                debate_id,
                "auto_mode_stopped",
                "system",
                {"reason": "step_error", "error": error},
            )
            self.storage.append_event(event)
            snapshot = _model_dump(state)
        await self._broadcast(debate_id, {"type": "event", "event": _model_dump(event)})
        await self._broadcast(debate_id, {"type": "state_snapshot", "state": snapshot})
        return state

    def _has_running_agent(self, state: DebateState) -> bool:
        return any(agent.status == AgentStatus.RUNNING for agent in state.agents.values())

    def _append_user_message_locked(self, state: DebateState, text: str):
        created_at = now_iso()
        record = UserMessageRecord(
            id=f"user-{len(state.user_messages) + 1:03d}",
            content=text.strip(),
            created_at=created_at,
            after_round=len(state.rounds),
        )
        state.user_messages.append(record)
        state.send_after_this = None
        state.updated_at = created_at
        self.storage.append_transcript(state.id, "User Opinion", record.content)
        return new_event(
            state.id,
            "user_opinion_submitted",
            "user",
            {"id": record.id, "text": record.content, "after_round": record.after_round},
        )

    def _flush_send_after_this_locked(self, state: DebateState):
        if not state.send_after_this or not state.send_after_this.strip():
            state.send_after_this = None
            return None
        return self._append_user_message_locked(state, state.send_after_this)

    @staticmethod
    def _user_context_since_last_turn(state: DebateState) -> str | None:
        if not state.user_messages:
            return None

        current_round = len(state.rounds)
        messages = [
            message.content.strip()
            for message in state.user_messages
            if message.after_round == current_round and message.content.strip()
        ]
        return "\n\n".join(messages) if messages else None

    async def resume_interrupted_auto_debates(self) -> None:
        for debate_id in self.storage.list_debates():
            async with self._locks[debate_id]:
                state = self.storage.read_state(debate_id)
                changed = False
                for agent in state.agents.values():
                    if state.auto_mode and agent.session_id:
                        agent.session_id = None
                        changed = True
                    if agent.status == AgentStatus.RUNNING:
                        agent.status = AgentStatus.QUEUED
                        changed = True
                if changed:
                    state.updated_at = now_iso()
                    self.storage.write_state(state)
            if state.auto_mode and changed:
                async with self._locks[debate_id]:
                    state = self.storage.read_state(debate_id)
                    state.auto_mode = False
                    self.storage.write_state(state)
                    self.storage.append_event(
                        new_event(
                            debate_id,
                            "auto_mode_stopped",
                            "system",
                            {"reason": "server restarted during an active step"},
                        )
                    )

    async def set_auto_mode(self, debate_id: str, enabled: bool) -> DebateState:
        async with self._locks[debate_id]:
            state = self.storage.read_state(debate_id)
            state.auto_mode = enabled
            state.updated_at = now_iso()
            self.storage.write_state(state)
            self.storage.append_event(new_event(debate_id, "auto_mode_set", "user", {"enabled": enabled}))
        if enabled:
            return await self._maybe_continue_auto_mode(debate_id, state)
        return state

    async def reorder_agents(self, debate_id: str, turn_order: list[str]) -> DebateState:
        async with self._locks[debate_id]:
            state = self.storage.read_state(debate_id)
            requested = [str(agent_id) for agent_id in turn_order]
            if len(requested) != len(set(requested)):
                raise ValueError("turn_order cannot contain duplicate agents")

            existing = set(state.agents)
            requested_set = set(requested)
            if requested_set != existing:
                missing = sorted(existing - requested_set)
                unknown = sorted(requested_set - existing)
                details = []
                if missing:
                    details.append(f"missing: {', '.join(missing)}")
                if unknown:
                    details.append(f"unknown: {', '.join(unknown)}")
                raise ValueError("turn_order must include exactly the debate agents" + (f" ({'; '.join(details)})" if details else ""))

            running = [
                agent_id for agent_id, agent in state.agents.items()
                if agent.status == AgentStatus.RUNNING
            ]
            if running:
                raise RuntimeError(f"cannot reorder agents while running: {', '.join(sorted(running))}")

            state.turn_order = requested
            state.updated_at = now_iso()
            self.storage.write_state(state)
            self.storage.append_event(
                new_event(debate_id, "agents_reordered", "user", {"turn_order": requested})
            )
            return state

    async def update_agent(self, debate_id: str, agent_id: str, config: DebateAgentConfig) -> DebateState:
        async with self._locks[debate_id]:
            state = self.storage.read_state(debate_id)
            self._ensure_agent_setup_editable(state)

            current_id = str(agent_id)
            updated_id = str(config.name)
            if current_id not in state.agents:
                raise ValueError(f"unknown debate agent: {current_id}")
            if updated_id != current_id and updated_id in state.agents:
                raise ValueError(f"duplicate debate agent name: {updated_id}")

            updated_agent = self.agents.state_from_config(config)
            if not updated_agent.color:
                updated_agent.color = state.agents[current_id].color

            agents = dict(state.agents)
            if updated_id == current_id:
                agents[current_id] = updated_agent
            else:
                reordered_agents: dict[str, Any] = {}
                for existing_id, existing_agent in agents.items():
                    if existing_id == current_id:
                        reordered_agents[updated_id] = updated_agent
                    else:
                        reordered_agents[existing_id] = existing_agent
                agents = reordered_agents
                state.turn_order = [
                    updated_id if existing_id == current_id else existing_id
                    for existing_id in state.turn_order
                ]
                if state.next_agent == current_id:
                    state.next_agent = updated_id

            if not any(agent.write_thesis for agent in agents.values()):
                raise ValueError("at least one agent must be selected to write a thesis")

            state.agents = agents
            state.updated_at = now_iso()
            self.storage.write_state(state)
            self.storage.append_event(
                new_event(
                    debate_id,
                    "agent_updated",
                    "user",
                    {"agent_id": current_id, "updated_agent_id": updated_id},
                )
            )
            return state

    @staticmethod
    def _ensure_agent_setup_editable(state: DebateState) -> None:
        if state.phase != DebatePhase.CREATED:
            raise RuntimeError("agent setup can only be edited before thesis generation starts")
        if state.theses or state.rounds:
            raise RuntimeError("agent setup can only be edited before thesis generation starts")
        running = [
            agent_id
            for agent_id, agent in state.agents.items()
            if agent.status == AgentStatus.RUNNING
        ]
        if running:
            raise RuntimeError(f"cannot edit agents while running: {', '.join(sorted(running))}")

    async def request_pause_after_this(self, debate_id: str) -> DebateState:
        async with self._locks[debate_id]:
            state = self.storage.read_state(debate_id)
            if state.phase != DebatePhase.DEBATING:
                raise ValueError(f"cannot request pause-after-this in phase {state.phase}")
            state.pause_after_this = True
            state.updated_at = now_iso()
            self.storage.write_state(state)
            self.storage.append_event(new_event(debate_id, "pause_requested", "user"))
            return state

    async def set_send_after_this(self, debate_id: str, text: str) -> DebateState:
        async with self._locks[debate_id]:
            state = self.storage.read_state(debate_id)
            cleaned = text.strip()
            if not cleaned:
                state.send_after_this = None
                state.updated_at = now_iso()
                self.storage.write_state(state)
                self.storage.append_event(new_event(debate_id, "send_after_this_set", "user", {"text": ""}))
                return state

            if not self._has_running_agent(state):
                event = self._append_user_message_locked(state, cleaned)
                self.storage.write_state(state)
                self.storage.append_event(event)
                return state

            state.send_after_this = cleaned
            state.updated_at = now_iso()
            self.storage.write_state(state)
            self.storage.append_event(new_event(debate_id, "send_after_this_set", "user", {"text": cleaned}))
            return state

    async def submit_user_opinion(self, debate_id: str, text: str) -> DebateState:
        async with self._locks[debate_id]:
            state = self.storage.read_state(debate_id)
            cleaned = text.strip()
            if not cleaned:
                return state
            event = self._append_user_message_locked(state, cleaned)
            self.storage.write_state(state)
            self.storage.append_event(event)
            return state

    async def force_consensus(self, debate_id: str, final_writer: str) -> DebateState:
        async with self._locks[debate_id]:
            state = self.storage.read_state(debate_id)
            writer = str(final_writer)
            if writer not in state.agents:
                raise ValueError(f"unknown final writer: {writer}")
            state.consensus = ConsensusState(
                final_writer=writer,
                consensus_summary="Consensus forced by user.",
                agreed_by=[],
                forced_by_user=True,
            )
            if state.phase != DebatePhase.CONSENSUS_REACHED:
                state = transition(state, DebatePhase.CONSENSUS_REACHED)
            self.storage.write_state(state)
            self.storage.append_event(
                new_event(debate_id, "final_writer_selected", "user", {"final_writer": writer})
            )
        return await self._maybe_continue_auto_mode(debate_id, state)

    async def draft_final(self, debate_id: str) -> DebateState:
        prompt_builder, validator = self._protocol_functions("build_final_draft_prompt", "validate_final_markdown")
        async with self._locks[debate_id]:
            state = self.storage.read_state(debate_id)
            if state.phase == DebatePhase.CONSENSUS_REACHED:
                state = transition(state, DebatePhase.DRAFTING_FINAL)
            if not state.consensus:
                raise ValueError("cannot draft final without consensus")
            writer = state.consensus.final_writer
            revision_reviews = dict(state.reviews)
            previous_draft = ""
            if state.phase == DebatePhase.REVISING_FINAL and state.final_document and state.final_document.draft_path:
                previous_draft = self.storage.read_artifact(debate_id, state.final_document.draft_path)
            state.agents[writer].status = AgentStatus.RUNNING
            state.agents[writer].last_error = None
            state.agents[writer].session_id = None
            self.storage.write_state(state)
            snapshot = _model_dump(state)

        await self._broadcast(debate_id, {"type": "state_snapshot", "state": snapshot})
        await self._broadcast(
            debate_id,
            {"type": "agent_status", "agent": writer, "status": AgentStatus.RUNNING.value},
        )

        if previous_draft and any(review.get("verdict") in {"reject", "rejected"} for review in revision_reviews.values()):
            revision_prompt_builder, _ = self._protocol_functions("build_revision_prompt", None)
            prompt = revision_prompt_builder(state, writer, previous_draft, revision_reviews)
        else:
            prompt = prompt_builder(state, writer)
        try:
            response = await self._send_or_start_agent(
                state,
                writer,
                prompt,
                ToolMode(state.tool_mode.value),
                stream=True,
            )
            markdown = validator(response.text)
        except Exception as exc:
            failed_state = await self._record_agent_error(debate_id, writer, exc)
            if failed_state.phase == DebatePhase.CONSENSUS_REACHED:
                await self._broadcast(
                    debate_id,
                    {"type": "state_snapshot", "state": _model_dump(failed_state)},
                )
            raise

        async with self._locks[debate_id]:
            state = self.storage.read_state(debate_id)
            current = state.final_document or FinalDocumentState()
            current.draft_version += 1
            current.draft_path = f"final/draft-v{current.draft_version:03d}.md"
            current.final_path = None
            current.accepted_by = []
            current.drafts.append(
                FinalDraftState(
                    draft_version=current.draft_version,
                    draft_path=current.draft_path,
                    created_at=now_iso(),
                )
            )
            state.final_document = current
            state.reviews = {}
            state.agents[writer].status = AgentStatus.DONE
            self.storage.write_artifact(debate_id, current.draft_path, markdown)
            state = transition(state, DebatePhase.REVIEWING_FINAL)
            queued_event = self._flush_send_after_this_locked(state)
            self.storage.write_state(state)
            self.storage.append_event(
                new_event(
                    debate_id,
                    "final_draft_written",
                    writer,
                    {"draft_version": current.draft_version, "draft_path": current.draft_path},
                )
            )
            if queued_event:
                self.storage.append_event(queued_event)
        return await self._maybe_continue_auto_mode(debate_id, state)

    async def review_final(self, debate_id: str) -> DebateState:
        prompt_builder, validator = self._protocol_functions("build_final_review_prompt", "validate_final_review")
        async with self._locks[debate_id]:
            state = self.storage.read_state(debate_id)
            if (
                state.phase != DebatePhase.REVIEWING_FINAL
                or state.final_document is None
                or not state.final_document.draft_path
            ):
                raise ValueError("cannot review final without draft")
            draft = self.storage.read_artifact(debate_id, state.final_document.draft_path)
            reviewer_ids = [
                agent_id
                for agent_id in state.turn_order
                if state.agents[agent_id].status != AgentStatus.DISABLED
            ]
            state.reviews = {}
            state.final_document.accepted_by = []
            for agent_id in reviewer_ids:
                state.agents[agent_id].status = AgentStatus.RUNNING
                state.agents[agent_id].last_error = None
            self.storage.write_state(state)
            snapshot = _model_dump(state)

        await self._broadcast(debate_id, {"type": "state_snapshot", "state": snapshot})
        for agent_id in reviewer_ids:
            await self._broadcast(
                debate_id,
                {"type": "agent_status", "agent": agent_id, "status": AgentStatus.RUNNING.value},
            )

        tasks = [
            self._review_one_final(state, agent_id, draft, prompt_builder, validator)
            for agent_id in reviewer_ids
        ]
        await asyncio.gather(*tasks)

        async with self._locks[debate_id]:
            state = self.storage.read_state(debate_id)
            accepted = set(state.final_document.accepted_by if state.final_document else [])
            required = {
                agent_id
                for agent_id in state.turn_order
                if state.agents[agent_id].status != AgentStatus.DISABLED
            }
            if accepted == required:
                state.final_document.final_path = "final/final.md"
                draft = self.storage.read_artifact(debate_id, state.final_document.draft_path)
                self.storage.write_artifact(debate_id, state.final_document.final_path, draft)
                _sync_current_final_draft(state, "accepted")
                state = transition(state, DebatePhase.ACCEPTED)
                self.storage.append_event(new_event(debate_id, "final_accepted", "system"))
            else:
                _sync_current_final_draft(state, "rejected")
                state = transition(state, DebatePhase.REVISING_FINAL)
            queued_event = self._flush_send_after_this_locked(state)
            self.storage.write_state(state)
            if queued_event:
                self.storage.append_event(queued_event)
        return await self._maybe_continue_auto_mode(debate_id, state)

    async def revise_final(self, debate_id: str) -> DebateState:
        async with self._locks[debate_id]:
            state = self.storage.read_state(debate_id)
            if state.phase != DebatePhase.REVISING_FINAL:
                raise ValueError(f"cannot revise final in phase {state.phase}")
            state = transition(state, DebatePhase.DRAFTING_FINAL)
            self.storage.write_state(state)
            return state

    async def _start_one_thesis(
        self,
        debate_id: str,
        agent_id: str,
        prompt_builder,
        validator,
        tool_mode: ToolMode,
    ) -> None:
        state = self.storage.read_state(debate_id)
        prompt = self._with_tool_mode_instruction(
            prompt_builder(state.user_prompt, agent_id, state),
            tool_mode,
            state,
        )
        agent = self.agents.get_agent(agent_id, state)
        try:
            async with self._locks[debate_id]:
                state = self.storage.read_state(debate_id)
                state.agents[agent_id].status = AgentStatus.RUNNING
                state.updated_at = now_iso()
                self.storage.write_state(state)
                snapshot = _model_dump(state)
            await self._broadcast(
                debate_id,
                {"type": "agent_status", "agent": agent_id, "status": AgentStatus.RUNNING.value},
            )
            await self._broadcast(debate_id, {"type": "state_snapshot", "state": snapshot})
            response = await self._start_llm_with_stream(
                debate_id,
                agent_id,
                agent,
                prompt,
                tool_mode,
                self._approved_mcp_servers(self.storage.read_state(debate_id)),
            )
            await self._record_session_id(debate_id, agent_id, response.session_id)
            payload = await self._validate_with_repair(
                debate_id,
                agent_id,
                response.text,
                validator,
                "ThesisPayload",
                tool_mode,
            )
            async with self._locks[debate_id]:
                state = self.storage.read_state(debate_id)
                artifact_path = f"theses/{agent_id}.md"
                evidence_refs, evidence_events = self._record_payload_evidence(
                    state,
                    agent_id,
                    payload,
                    "thesis",
                    agent_id,
                )
                record = ThesisRecord(
                    agent=agent_id,
                    position=payload.position,
                    decision=payload.decision,
                    action_plan=payload.action_plan,
                    risks=payload.risks,
                    success_criteria=payload.success_criteria,
                    evidence_refs=evidence_refs,
                    artifact_path=artifact_path,
                )
                state.theses[agent_id] = record
                state.agents[agent_id].status = AgentStatus.DONE
                self.storage.write_artifact(debate_id, artifact_path, _thesis_markdown(record))
                self._write_evidence_artifact(debate_id, state)
                self.storage.write_state(state)
                event = new_event(debate_id, "thesis_submitted", agent_id, _payload_dict(payload))
                self.storage.append_event(event)
                for evidence_event in evidence_events:
                    self.storage.append_event(evidence_event)
                snapshot = _model_dump(state)
            await self._broadcast(
                debate_id,
                {"type": "agent_status", "agent": agent_id, "status": AgentStatus.DONE.value},
            )
            await self._broadcast(debate_id, {"type": "event", "event": _model_dump(event)})
            await self._broadcast(debate_id, {"type": "state_snapshot", "state": snapshot})
        except Exception as exc:
            await self._record_agent_error(debate_id, agent_id, exc)

    async def _validate_with_repair(
        self,
        debate_id: str,
        agent_id: str,
        text: str,
        validator,
        schema_name: str,
        tool_mode: ToolMode,
    ) -> Any:
        try:
            payload = validator(text, agent_id)
            state = self.storage.read_state(debate_id)
            self._validate_payload_evidence_requirement(payload, state, tool_mode, schema_name)
            return payload
        except Exception as first_exc:
            self.storage.write_artifact(debate_id, f"errors/{agent_id}-{schema_name}-raw.txt", text)
            event = new_event(
                debate_id,
                "agent_output_repair_requested",
                agent_id,
                {"schema": schema_name, "error": str(first_exc)},
            )
            self.storage.append_event(event)
            await self._broadcast(debate_id, {"type": "event", "event": _model_dump(event)})
            prompt_builder, _ = self._protocol_functions("build_repair_prompt", None)
            async with self._locks[debate_id]:
                state = self.storage.read_state(debate_id)
                try:
                    session = self.agents.make_session(
                        state,
                        agent_id,
                        tool_mode,
                        self._approved_mcp_servers(state),
                    )
                except RuntimeError:
                    raise first_exc
            repair_prompt = prompt_builder(text, str(first_exc), schema_name)
            repaired = await self._call_llm(self.agents.get_agent(agent_id, state), "send", session, repair_prompt)
            self.storage.write_artifact(
                debate_id,
                f"errors/{agent_id}-{schema_name}-repair-raw.txt",
                repaired.text,
            )
            try:
                payload = validator(repaired.text, agent_id)
                state = self.storage.read_state(debate_id)
                self._validate_payload_evidence_requirement(payload, state, tool_mode, schema_name)
                return payload
            except Exception as second_exc:
                raise ValueError(f"{first_exc}; repair failed: {second_exc}") from second_exc

    async def _record_session_id(self, debate_id: str, agent_id: str, session_id: str | None) -> None:
        if not session_id:
            return
        async with self._locks[debate_id]:
            state = self.storage.read_state(debate_id)
            if state.agents[agent_id].session_id == session_id:
                return
            state.agents[agent_id].session_id = session_id
            state.updated_at = now_iso()
            self.storage.write_state(state)
            event = new_event(
                debate_id,
                "agent_session_started",
                agent_id,
                {"session_id": session_id},
            )
            self.storage.append_event(event)
            snapshot = _model_dump(state)
        await self._broadcast(debate_id, {"type": "event", "event": _model_dump(event)})
        await self._broadcast(debate_id, {"type": "state_snapshot", "state": snapshot})

    async def _record_turn(self, debate_id: str, agent_id: str, payload: Any) -> DebateState:
        async with self._locks[debate_id]:
            state = self.storage.read_state(debate_id)
            index = len(state.rounds) + 1
            artifact_path = f"rounds/round-{index:03d}-{agent_id}.md"
            evidence_refs, evidence_events = self._record_payload_evidence(
                state,
                agent_id,
                payload,
                "turn",
                str(index),
            )
            record = DebateTurnRecord(
                index=index,
                agent=agent_id,
                discussion=payload.discussion,
                agreements=payload.agreements,
                disagreements=payload.disagreements,
                updated_position=payload.updated_position,
                proposed_next_action=payload.proposed_next_action,
                evidence_refs=evidence_refs,
                consensus_action=_payload_dict(payload.consensus_action) if payload.consensus_action else None,
                consensus_signal=_payload_dict(payload.consensus_signal) if payload.consensus_signal else None,
                artifact_path=artifact_path,
            )
            state.rounds.append(record)
            state.agents[agent_id].status = AgentStatus.DONE
            state.agents[agent_id].last_error = None
            consensus_events = self._apply_consensus_action(state, agent_id, payload, index)
            queued_event = self._flush_send_after_this_locked(state)
            self.storage.write_artifact(debate_id, artifact_path, _turn_markdown(record))
            self._write_evidence_artifact(debate_id, state)
            self.storage.write_state(state)
            self.storage.append_event(
                new_event(debate_id, "turn_completed", agent_id, _payload_dict(payload))
            )
            if queued_event:
                self.storage.append_event(queued_event)
            for evidence_event in evidence_events:
                self.storage.append_event(evidence_event)
            for event_type, event_payload in consensus_events:
                self.storage.append_event(new_event(debate_id, event_type, agent_id, event_payload))
            return state

    async def _review_one_final(self, state: DebateState, agent_id: str, draft: str, prompt_builder, validator) -> None:
        prompt = prompt_builder(state, agent_id, draft)
        try:
            response = await self._send_or_start_agent(state, agent_id, prompt, ToolMode(state.tool_mode.value))
            payload = validator(response.text, agent_id)
        except Exception as exc:
            await self._record_agent_error(state.id, agent_id, exc)
            raise
        async with self._locks[state.id]:
            updated = self.storage.read_state(state.id)
            updated.reviews[agent_id] = _payload_dict(payload)
            if payload.verdict == "accept" and updated.final_document:
                if agent_id not in updated.final_document.accepted_by:
                    updated.final_document.accepted_by.append(agent_id)
            updated.agents[agent_id].status = AgentStatus.DONE
            self.storage.write_artifact(
                state.id,
                f"final/review-{agent_id}.json",
                json.dumps(_payload_dict(payload), indent=2),
            )
            self.storage.write_state(updated)
            event = new_event(state.id, "final_review_submitted", agent_id, _payload_dict(payload))
            self.storage.append_event(event)
            snapshot = _model_dump(updated)

        await self._broadcast(
            state.id,
            {"type": "agent_status", "agent": agent_id, "status": AgentStatus.DONE.value},
        )
        await self._broadcast(state.id, {"type": "event", "event": _model_dump(event)})
        await self._broadcast(state.id, {"type": "state_snapshot", "state": snapshot})

    async def _record_agent_error(self, debate_id: str, agent_id: str, exc: Exception) -> DebateState:
        async with self._locks[debate_id]:
            state = self.storage.read_state(debate_id)
            state.agents[agent_id].status = AgentStatus.FAILED
            state.agents[agent_id].last_error = str(exc)
            state.agents[agent_id].session_id = None
            state.next_agent = state.rounds[-1].agent if state.rounds else None
            state.updated_at = now_iso()
            self.storage.write_state(state)
            event = new_event(debate_id, "agent_error", agent_id, {"error": str(exc)})
            self.storage.append_event(event)
            snapshot = _model_dump(state)
        await self._broadcast(
            debate_id,
            {"type": "agent_status", "agent": agent_id, "status": AgentStatus.FAILED.value},
        )
        await self._broadcast(debate_id, {"type": "event", "event": _model_dump(event)})
        await self._broadcast(debate_id, {"type": "state_snapshot", "state": snapshot})
        async with self._locks[debate_id]:
            state = self.storage.read_state(debate_id)
            return state

    def _next_agent(self, state: DebateState) -> str:
        if state.next_agent is None:
            return state.turn_order[0]
        try:
            index = state.turn_order.index(state.next_agent)
        except ValueError:
            return state.turn_order[0]
        return state.turn_order[(index + 1) % len(state.turn_order)]

    def _set_all_status(self, state: DebateState, status: AgentStatus) -> DebateState:
        for agent in state.agents.values():
            if agent.status != AgentStatus.DISABLED:
                agent.status = status
                agent.last_error = None
        state.updated_at = now_iso()
        return state

    def _recover_failed_for_turn(self, state: DebateState) -> DebateState:
        if not state.theses:
            raise ValueError(
                "cannot run debate turn in phase failed; retry Start Theses first "
                "because no thesis records are available"
            )
        return self._force_phase(state, DebatePhase.THESES_READY)

    def _enter_starting_theses(self, state: DebateState) -> DebateState:
        if state.phase == DebatePhase.CREATED:
            state = transition(state, DebatePhase.STARTING_THESES)
        elif state.phase in {DebatePhase.STARTING_THESES, DebatePhase.AWAITING_THESES, DebatePhase.FAILED}:
            state = self._force_phase(state, DebatePhase.STARTING_THESES)
        else:
            raise ValueError(f"cannot start theses in phase {state.phase}")
        for agent_id, agent in state.agents.items():
            if agent.status == AgentStatus.DISABLED:
                continue
            if not agent.write_thesis:
                agent.status = AgentStatus.WAITING
            elif agent_id in state.theses:
                agent.status = AgentStatus.DONE
            else:
                agent.status = AgentStatus.QUEUED
            agent.last_error = None
        state.updated_at = now_iso()
        return state

    def _clear_thesis_runs(self, debate_id: str, agent_ids: list[str]) -> None:
        active = self._thesis_runs.get(debate_id)
        if not active:
            self._thesis_runs.pop(debate_id, None)
            return
        active.difference_update(agent_ids)
        if not active:
            self._thesis_runs.pop(debate_id, None)

    def _force_phase(self, state: DebateState, phase: DebatePhase) -> DebateState:
        state.phase = phase
        state.updated_at = now_iso()
        return state

    def _rebuild_consensus_state(self, state: DebateState) -> None:
        state.consensus_proposals = []
        state.consensus = None

        for round_rec in state.rounds:
            if round_rec.consensus_action:
                self._replay_consensus_action(state, round_rec)
            elif round_rec.consensus_signal:
                self._replay_consensus_signal(state, round_rec)

    def _replay_consensus_action(self, state: DebateState, round_rec: DebateTurnRecord) -> None:
        action = round_rec.consensus_action or {}
        action_name = str(action.get("action") or "")
        now = now_iso()

        if action_name == "propose":
            proposal = ConsensusProposalState(
                id=f"consensus-{round_rec.index:03d}-{round_rec.agent}",
                proposer=round_rec.agent,
                final_writer=str(action.get("final_writer") or ""),
                consensus_summary=str(action.get("consensus_summary") or ""),
                accepted_by=[round_rec.agent],
                created_at=now,
                updated_at=now,
            )
            state.consensus_proposals.append(proposal)
            return

        try:
            proposal = self._find_consensus_proposal(state, action.get("proposal_id"))
        except ValueError:
            return

        if action_name == "accept":
            if proposal.status != "withdrawn" and round_rec.agent not in proposal.accepted_by:
                proposal.accepted_by.append(round_rec.agent)
            proposal.rejected_by.pop(round_rec.agent, None)
            if proposal.status != "withdrawn":
                proposal.status = "rejected" if proposal.rejected_by else "active"
            proposal.updated_at = now
            required = set(self._required_consensus_agents(state))
            accepted = set(proposal.accepted_by)
            if required and required <= accepted and not proposal.rejected_by:
                proposal.status = "accepted"
                state.consensus = ConsensusState(
                    final_writer=proposal.final_writer,
                    consensus_summary=proposal.consensus_summary,
                    agreed_by=list(proposal.accepted_by),
                )
            return

        if action_name == "reject":
            proposal.rejected_by[round_rec.agent] = str(action.get("reason") or "Rejected without reason.")
            if round_rec.agent in proposal.accepted_by:
                proposal.accepted_by.remove(round_rec.agent)
            proposal.status = "rejected"
            proposal.updated_at = now
            if state.consensus and self._consensus_matches_proposal(state.consensus, proposal):
                state.consensus = None
            return

        if action_name == "withdraw":
            if proposal.proposer == round_rec.agent:
                proposal.status = "withdrawn"
            if round_rec.agent in proposal.accepted_by:
                proposal.accepted_by.remove(round_rec.agent)
            proposal.rejected_by.pop(round_rec.agent, None)
            proposal.updated_at = now
            if state.consensus and self._consensus_matches_proposal(state.consensus, proposal):
                state.consensus = None

    def _replay_consensus_signal(self, state: DebateState, round_rec: DebateTurnRecord) -> None:
        signal = round_rec.consensus_signal or {}
        if not signal.get("agreed"):
            return

        proposal = ConsensusProposalState(
            id=f"consensus-{round_rec.index:03d}-{round_rec.agent}",
            proposer=round_rec.agent,
            final_writer=str(signal.get("final_writer") or ""),
            consensus_summary=str(signal.get("consensus_summary") or ""),
            accepted_by=[round_rec.agent],
            created_at=now_iso(),
            updated_at=now_iso(),
        )
        state.consensus_proposals.append(proposal)

        agreed_by = self._matching_consensus_agents(state, round_rec.agent, _DictSignal(signal))
        if len(agreed_by) >= 2:
            proposal.accepted_by = agreed_by
            proposal.status = "accepted"
            proposal.updated_at = now_iso()
            state.consensus = ConsensusState(
                final_writer=proposal.final_writer,
                consensus_summary=proposal.consensus_summary,
                agreed_by=agreed_by,
            )

    def _matching_consensus_agents(self, state: DebateState, current_agent: str, signal) -> list[str]:
        agreed = [current_agent]
        for turn in state.rounds:
            existing = turn.consensus_signal or {}
            if existing.get("agreed") and existing.get("final_writer") == signal.final_writer:
                agreed.append(turn.agent)
        return list(dict.fromkeys(agreed))

    def _apply_consensus_action(
        self,
        state: DebateState,
        agent_id: str,
        payload: Any,
        turn_index: int,
    ) -> list[tuple[str, dict]]:
        if payload.consensus_action:
            return self._apply_structured_consensus_action(
                state,
                agent_id,
                payload.consensus_action,
                turn_index,
            )
        if payload.consensus_signal and payload.consensus_signal.agreed:
            proposal_id = f"consensus-{turn_index:03d}-{agent_id}"
            proposal = ConsensusProposalState(
                id=proposal_id,
                proposer=agent_id,
                final_writer=payload.consensus_signal.final_writer,
                consensus_summary=payload.consensus_signal.consensus_summary,
                accepted_by=[agent_id],
                created_at=now_iso(),
                updated_at=now_iso(),
            )
            state.consensus_proposals.append(proposal)
            agreed_by = self._matching_consensus_agents(state, agent_id, payload.consensus_signal)
            events = [("consensus_proposed", _model_dump(proposal))]
            if len(agreed_by) >= 2:
                proposal.accepted_by = agreed_by
                proposal.status = "accepted"
                proposal.updated_at = now_iso()
                state.consensus = ConsensusState(
                    final_writer=payload.consensus_signal.final_writer,
                    consensus_summary=payload.consensus_signal.consensus_summary,
                    agreed_by=agreed_by,
                )
                events.append(("consensus_reached", _model_dump(state.consensus)))
            return events
        return []

    def _apply_structured_consensus_action(
        self,
        state: DebateState,
        agent_id: str,
        action,
        turn_index: int,
    ) -> list[tuple[str, dict]]:
        now = now_iso()
        action_name = action.action.value if hasattr(action.action, "value") else str(action.action)
        if action_name == "propose":
            if action.final_writer not in state.agents:
                raise ValueError(f"consensus final_writer is not an active debate agent: {action.final_writer}")
            proposal = ConsensusProposalState(
                id=f"consensus-{turn_index:03d}-{agent_id}",
                proposer=agent_id,
                final_writer=action.final_writer,
                consensus_summary=action.consensus_summary or "",
                accepted_by=[agent_id],
                created_at=now,
                updated_at=now,
            )
            state.consensus_proposals.append(proposal)
            return [("consensus_proposed", _model_dump(proposal))]

        proposal = self._find_consensus_proposal(state, action.proposal_id)
        if action_name == "accept":
            if proposal.status == "withdrawn":
                raise ValueError(f"cannot accept withdrawn consensus proposal: {proposal.id}")
            if agent_id not in proposal.accepted_by:
                proposal.accepted_by.append(agent_id)
            proposal.rejected_by.pop(agent_id, None)
            proposal.status = "rejected" if proposal.rejected_by else "active"
            proposal.updated_at = now
            events = [("consensus_accepted", {"proposal_id": proposal.id, "agent": agent_id})]
            required = set(self._required_consensus_agents(state))
            accepted = set(proposal.accepted_by)
            if required and required <= accepted and not proposal.rejected_by:
                proposal.status = "accepted"
                state.consensus = ConsensusState(
                    final_writer=proposal.final_writer,
                    consensus_summary=proposal.consensus_summary,
                    agreed_by=list(proposal.accepted_by),
                )
                events.append(("consensus_reached", _model_dump(state.consensus)))
            return events

        if action_name == "reject":
            proposal.rejected_by[agent_id] = action.reason or "Rejected without reason."
            if agent_id in proposal.accepted_by:
                proposal.accepted_by.remove(agent_id)
            proposal.status = "rejected"
            proposal.updated_at = now
            if state.consensus and self._consensus_matches_proposal(state.consensus, proposal):
                state.consensus = None
            return [
                (
                    "consensus_rejected",
                    {"proposal_id": proposal.id, "agent": agent_id, "reason": proposal.rejected_by[agent_id]},
                )
            ]

        if action_name == "withdraw":
            if proposal.proposer == agent_id:
                proposal.status = "withdrawn"
            if agent_id in proposal.accepted_by:
                proposal.accepted_by.remove(agent_id)
            proposal.rejected_by.pop(agent_id, None)
            proposal.updated_at = now
            if state.consensus and self._consensus_matches_proposal(state.consensus, proposal):
                state.consensus = None
            return [("consensus_withdrawn", {"proposal_id": proposal.id, "agent": agent_id})]

        raise ValueError(f"unsupported consensus action: {action_name}")

    def _find_consensus_proposal(self, state: DebateState, proposal_id: str | None) -> ConsensusProposalState:
        for proposal in state.consensus_proposals:
            if proposal.id == proposal_id:
                return proposal
        raise ValueError(f"Consensus proposal not found: {proposal_id}")

    def _required_consensus_agents(self, state: DebateState) -> list[str]:
        return [
            agent_id
            for agent_id in state.turn_order
            if state.agents[agent_id].status != AgentStatus.DISABLED
        ]

    def _consensus_matches_proposal(
        self,
        consensus: ConsensusState,
        proposal: ConsensusProposalState,
    ) -> bool:
        return (
            consensus.final_writer == proposal.final_writer
            and consensus.consensus_summary == proposal.consensus_summary
        )

    def _validate_payload_evidence_requirement(
        self,
        payload: Any,
        state: DebateState,
        tool_mode: ToolMode,
        schema_name: str,
    ) -> None:
        evidence = getattr(payload, "evidence", []) or []
        local_kinds = {"file_ref", "command_result"}
        if tool_mode == ToolMode.TEXT_ONLY:
            blocked = [
                str(getattr(item.kind, "value", item.kind))
                for item in evidence
                if str(getattr(item.kind, "value", item.kind)) in local_kinds
            ]
            if blocked:
                raise ValueError(
                    f"{schema_name} used local evidence while file access is disabled: "
                    f"{', '.join(sorted(set(blocked)))}"
                )
        if not state.allow_web_evidence:
            if any(str(getattr(item.kind, "value", item.kind)) == "web_ref" for item in evidence):
                raise ValueError(f"{schema_name} used web evidence while web evidence is disabled")

    def _record_payload_evidence(
        self,
        state: DebateState,
        agent_id: str,
        payload: Any,
        source_type: str,
        source_id: str,
    ) -> tuple[list[str], list[Any]]:
        refs = list(dict.fromkeys(getattr(payload, "evidence_refs", []) or []))
        new_evidence = list(getattr(payload, "evidence", []) or [])
        generated_ids = {
            f"ev-{len(state.shared_evidence) + index + 1:03d}-{agent_id}"
            for index, _ in enumerate(new_evidence)
        }
        known_ids = {item.id for item in state.shared_evidence} | generated_ids
        unknown = [ref for ref in refs if ref not in known_ids]
        refs = [ref for ref in refs if ref in known_ids]

        events = []
        if unknown:
            events.append(
                new_event(
                    state.id,
                    "evidence_refs_ignored",
                    agent_id,
                    {
                        "source_type": source_type,
                        "source_id": source_id,
                        "unknown_refs": unknown,
                    },
                )
            )
        for evidence in new_evidence:
            record_id = f"ev-{len(state.shared_evidence) + 1:03d}-{agent_id}"
            record = EvidenceRecord(
                id=record_id,
                agent=agent_id,
                kind=evidence.kind.value if hasattr(evidence.kind, "value") else str(evidence.kind),
                summary=evidence.summary,
                source_type=source_type,
                source_id=source_id,
                path=evidence.path,
                line_start=evidence.line_start,
                line_end=evidence.line_end,
                excerpt=evidence.excerpt,
                command=evidence.command,
                cwd=evidence.cwd,
                exit_code=evidence.exit_code,
                output_summary=evidence.output_summary,
                url=evidence.url,
                title=evidence.title,
                query=evidence.query,
                snippet=evidence.snippet,
                retrieved_at=evidence.retrieved_at,
                mcp_server=evidence.mcp_server,
                mcp_tool=evidence.mcp_tool,
                created_at=now_iso(),
            )
            state.shared_evidence.append(record)
            refs.append(record.id)
            events.append(new_event(state.id, "evidence_recorded", agent_id, _model_dump(record)))

        return list(dict.fromkeys(refs)), events

    def _write_evidence_artifact(self, debate_id: str, state: DebateState) -> None:
        self.storage.write_artifact(
            debate_id,
            "evidence/evidence.json",
            json.dumps([_model_dump(item) for item in state.shared_evidence], indent=2),
        )

    def _approved_mcp_servers(self, state: DebateState | None = None) -> list[MCPServerConfig]:
        return [
            MCPServerConfig(
                name=server.id,
                command_or_url=server.command_or_url,
                args=server.args,
                env=server.env,
                transport=server.transport,
                headers=server.headers,
                trusted=server.trusted,
            )
            for server in self.storage.read_mcp_servers(enabled_only=True)
        ]

    def _protocol_functions(self, prompt_name: str, validator_name: str | None):
        try:
            prompts = __import__("app.core.prompts", fromlist=[prompt_name])
            prompt_builder = getattr(prompts, prompt_name)
            if validator_name is None:
                return prompt_builder, None
            validators = __import__("app.core.validators", fromlist=[validator_name])
            validator = getattr(validators, validator_name)
            return prompt_builder, validator
        except (ImportError, AttributeError) as exc:
            raise RuntimeError(
                "protocol layer is not available yet; Gemini-owned prompts/validators are required"
            ) from exc

    async def _send_or_start_agent(
        self,
        state: DebateState,
        agent_id: str,
        prompt: str,
        tool_mode: ToolMode,
        stream: bool = False,
    ):
        agent = self.agents.get_agent(agent_id, state)
        mcp_servers = self._approved_mcp_servers(state)
        if state.agents[agent_id].session_id:
            session = self.agents.make_session(state, agent_id, tool_mode, mcp_servers)
            if stream:
                return await self._send_llm_with_stream(state.id, agent_id, agent, session, prompt)
            return await self._call_llm(agent, "send", session, prompt)

        if stream:
            response = await self._start_llm_with_stream(
                state.id,
                agent_id,
                agent,
                prompt,
                tool_mode,
                mcp_servers,
            )
        else:
            response = await self._call_llm(agent, "start", prompt, tool_mode, mcp_servers)
        await self._record_session_id(state.id, agent_id, response.session_id)
        return response

    async def _call_llm(self, agent, method_name: str, *args):
        method = getattr(agent, method_name)
        if getattr(agent, "cli_bin", "") == "fake":
            return method(*args)
        return await asyncio.to_thread(method, *args)

    async def _send_llm_with_stream(
        self,
        debate_id: str,
        agent_id: str,
        agent,
        session,
        prompt: str,
    ):
        if getattr(agent, "cli_bin", "") == "fake" or not getattr(agent, "supports_session_stream", False):
            return await self._call_llm(agent, "send", session, prompt)
        return await self._run_streaming_agent_call(
            debate_id,
            agent_id,
            lambda on_chunk: agent.send_stream(session, prompt, on_chunk),
        )

    def _with_tool_mode_instruction(
        self,
        prompt: str,
        tool_mode: ToolMode,
        state: DebateState | None = None,
    ) -> str:
        if tool_mode == ToolMode.TEXT_ONLY:
            web_text = (
                "Web evidence may be used if your provider exposes web search."
                if not state or state.allow_web_evidence
                else "Web evidence is disabled."
            )
            instruction = f"""Tool-use requirement:
Local file and terminal command tools are disabled.
Do not inspect the working directory, mention local source paths, use <file:...> references, or return file_ref/command_result evidence.
{web_text}
If you use web evidence, record it as web_ref evidence in the JSON `evidence` array."""
            return f"{prompt}\n\n{instruction}"
        if tool_mode == ToolMode.READ_ONLY:
            instruction = """Tool-use requirement:
Read-only tools are available when they materially clarify the decision.
Do not edit, create, delete, or format files.
If you use tools, record the useful file range, command result, web/document result, or MCP result in the JSON `evidence` array. Cite existing shared evidence with `evidence_refs` when building on another agent's finding."""
        elif tool_mode == ToolMode.PROBE:
            instruction = """Tool-use requirement:
File and command probes are available when they materially clarify the decision.
Do not edit, create, delete, or format files in probe mode.
If you use tools, record the useful file range, command result, web/document result, or MCP result in the JSON `evidence` array. Cite existing shared evidence with `evidence_refs` when building on another agent's finding."""
        elif tool_mode == ToolMode.EDIT:
            instruction = """Tool-use requirement:
You may inspect, run commands, and edit when necessary for the current task.
Keep edits scoped to the requested project and return only the required JSON object.
If you use tools, record the useful file range, command result, web/document result, or MCP result in the JSON `evidence` array. Cite existing shared evidence with `evidence_refs` when building on another agent's finding."""
        else:
            instruction = """Tool-use requirement:
Full tool access is enabled. Inspect and run commands when they materially clarify the decision.
If you use tools, record the useful file range, command result, web/document result, or MCP result in the JSON `evidence` array. Cite existing shared evidence with `evidence_refs` when building on another agent's finding."""
        return f"{prompt}\n\n{instruction}"

    async def _start_llm_with_stream(
        self,
        debate_id: str,
        agent_id: str,
        agent,
        prompt: str,
        tool_mode: ToolMode,
        mcp_servers: list[MCPServerConfig],
    ):
        if getattr(agent, "cli_bin", "") == "fake" or not getattr(agent, "supports_session_stream", False):
            return await self._call_llm(agent, "start", prompt, tool_mode, mcp_servers)
        return await self._run_streaming_agent_call(
            debate_id,
            agent_id,
            lambda on_chunk: agent.start_stream(prompt, tool_mode, mcp_servers, on_chunk),
        )

    async def _run_streaming_agent_call(
        self,
        debate_id: str,
        agent_id: str,
        invoke,
    ):
        await self._broadcast(debate_id, {"type": "agent_output_start", "agent": agent_id})
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[str | None] = asyncio.Queue()

        async def forward_chunks() -> None:
            while True:
                chunk = await queue.get()
                if chunk is None:
                    return

                chunks = [chunk]
                while True:
                    try:
                        next_chunk = await asyncio.wait_for(queue.get(), timeout=0.05)
                    except asyncio.TimeoutError:
                        break
                    if next_chunk is None:
                        await self._broadcast(
                            debate_id,
                            {
                                "type": "agent_output_chunk",
                                "agent": agent_id,
                                "chunk": "".join(chunks),
                            },
                        )
                        return
                    chunks.append(next_chunk)
                    if sum(len(item) for item in chunks) >= 2048:
                        break

                await self._broadcast(
                    debate_id,
                    {"type": "agent_output_chunk", "agent": agent_id, "chunk": "".join(chunks)},
                )

        def on_chunk(chunk: str) -> None:
            loop.call_soon_threadsafe(queue.put_nowait, chunk)

        forwarder = asyncio.create_task(forward_chunks())
        try:
            return await asyncio.to_thread(invoke, on_chunk)
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, None)
            await forwarder
            await self._broadcast(debate_id, {"type": "agent_output_end", "agent": agent_id})

    async def _broadcast(self, debate_id: str, message: dict) -> None:
        if self.broadcaster is not None:
            await self.broadcaster(debate_id, message)


def _payload_dict(payload: Any) -> dict:
    if payload is None:
        return {}
    if hasattr(payload, "model_dump"):
        return payload.model_dump(mode="json")
    if hasattr(payload, "dict"):
        return payload.dict()
    return dict(payload)


def _model_dump(model) -> dict:
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json")
    return model.dict()


def _sync_current_final_draft(state: DebateState, status: str) -> None:
    document = state.final_document
    if not document or not document.draft_path:
        return

    for draft in reversed(document.drafts):
        if draft.draft_path != document.draft_path:
            continue
        draft.status = status
        draft.accepted_by = list(document.accepted_by)
        draft.reviews = dict(state.reviews)
        return


class _DictSignal:
    def __init__(self, data: dict) -> None:
        self.final_writer = data.get("final_writer")
        self.consensus_summary = data.get("consensus_summary")


def _thesis_markdown(record: ThesisRecord) -> str:
    sections = [
        f"# {record.agent} Thesis",
        f"## Decision\n\n{record.decision}",
        f"## Position\n\n{record.position}",
        "## Action Plan\n\n" + "\n".join(f"- {item}" for item in record.action_plan),
        "## Risks\n\n" + "\n".join(f"- {item}" for item in record.risks),
        "## Success Criteria\n\n" + "\n".join(f"- {item}" for item in record.success_criteria),
    ]
    if record.evidence_refs:
        sections.append("## Evidence\n\n" + "\n".join(f"- {item}" for item in record.evidence_refs))
    return "\n\n".join(sections) + "\n"


def _turn_markdown(record: DebateTurnRecord) -> str:
    consensus = ""
    if record.consensus_action:
        consensus = "\n\n## Consensus Action\n\n```json\n" + json.dumps(record.consensus_action, indent=2) + "\n```\n"
    elif record.consensus_signal:
        consensus = "\n\n## Consensus Signal\n\n```json\n" + json.dumps(record.consensus_signal, indent=2) + "\n```\n"
    sections = [
        f"# Round {record.index}: {record.agent}",
        record.discussion,
        "## Evidence\n\n" + "\n".join(f"- {item}" for item in record.evidence_refs)
        if record.evidence_refs else "",
    ]
    return "\n\n".join(section for section in sections if section.strip()) + consensus + "\n"
