import asyncio
import json

from app.core.agent_registry import AgentRegistry
from app.core.debate_engine import DebateEngine
from app.core.events import new_event
from app.core.storage import DebateStorage
from app.models.agent import AgentId, AgentStatus, DebateAgentConfig, ProviderKind
from app.models.debate import DebatePhase, UserMessageRecord
from tests.backend.fakes import FakeLLM, SlowFakeLLM


async def _wait_for_phase(
    storage: DebateStorage,
    debate_id: str,
    phase: DebatePhase,
    attempts: int = 100,
) -> object:
    for _ in range(attempts):
        state = storage.read_state(debate_id)
        if state.phase == phase:
            return state
        await asyncio.sleep(0.01)
    state = storage.read_state(debate_id)
    raise AssertionError(f"debate stayed in phase {state.phase}, expected {phase}")


def test_fake_agents_can_start_theses_and_run_turn(tmp_path):
    storage = DebateStorage(tmp_path)
    registry = AgentRegistry(
        {
            AgentId.CODEX: FakeLLM("codex", [_thesis("codex"), _ack("codex"), _turn("codex")]),
            AgentId.GEMINI: FakeLLM("gemini", [_thesis("gemini"), _ack("gemini")]),
            AgentId.CLAUDE: FakeLLM("claude", [_thesis("claude"), _ack("claude")]),
        }
    )
    engine = DebateEngine(storage, registry)

    async def scenario():
        state = await engine.create_debate("Backend Test", "Choose one stack.")
        state = await engine.start_theses(state.id)
        assert state.phase == DebatePhase.THESES_READY
        assert set(state.theses) == {AgentId.CODEX, AgentId.GEMINI, AgentId.CLAUDE}

        state = await engine.share_theses(state.id)
        assert state.phase == DebatePhase.DEBATING

        state = await engine.run_turn(state.id, AgentId.CODEX)
        assert state.rounds[-1].agent == AgentId.CODEX
        assert state.rounds[-1].discussion.startswith("I like what <@gemini> said")

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(scenario())
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def test_user_opinion_is_persistent_and_used_next_turn(tmp_path):
    storage = DebateStorage(tmp_path)
    codex = FakeLLM("codex", [_thesis("codex"), _ack("codex"), _turn("codex")])
    registry = AgentRegistry(
        {
            AgentId.CODEX: codex,
            AgentId.GEMINI: FakeLLM("gemini", [_thesis("gemini"), _ack("gemini")]),
            AgentId.CLAUDE: FakeLLM("claude", [_thesis("claude"), _ack("claude")]),
        }
    )
    engine = DebateEngine(storage, registry)

    async def scenario():
        state = await engine.create_debate("User Message Test", "Choose one stack.")
        state = await engine.start_theses(state.id)
        state = await engine.share_theses(state.id)

        state = await engine.submit_user_opinion(state.id, "Please consider rollback safety.")
        assert state.send_after_this is None
        assert state.user_messages[-1].content == "Please consider rollback safety."
        assert state.user_messages[-1].after_round == 0

        state = await engine.run_turn(state.id, AgentId.CODEX)
        assert state.rounds[-1].agent == AgentId.CODEX
        assert "Please consider rollback safety." in codex.prompts[-1]

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(scenario())
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def test_user_opinion_is_only_used_for_immediate_next_turn_context(tmp_path):
    storage = DebateStorage(tmp_path)
    codex = FakeLLM("codex", [_thesis("codex"), _ack("codex"), _turn("codex")])
    gemini = FakeLLM("gemini", [_thesis("gemini"), _ack("gemini"), _turn_for("gemini", ["codex"])])
    registry = AgentRegistry(
        {
            AgentId.CODEX: codex,
            AgentId.GEMINI: gemini,
            AgentId.CLAUDE: FakeLLM("claude", [_thesis("claude"), _ack("claude")]),
        }
    )
    engine = DebateEngine(storage, registry)

    async def scenario():
        state = await engine.create_debate("User Context Once Test", "Choose one stack.")
        state = await engine.start_theses(state.id)
        state = await engine.share_theses(state.id)

        state = await engine.submit_user_opinion(state.id, "Apply this to one next turn only.")
        state = await engine.run_turn(state.id, AgentId.CODEX)
        assert "Apply this to one next turn only." in codex.prompts[-1]

        state = await engine.run_turn(state.id, AgentId.GEMINI)
        assert "Apply this to one next turn only." not in gemini.prompts[-1]

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(scenario())
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def test_queued_user_message_flushes_after_running_turn(tmp_path):
    storage = DebateStorage(tmp_path)
    gemini = FakeLLM("gemini", [_thesis("gemini"), _ack("gemini"), _turn_for("gemini", ["codex"])])
    registry = AgentRegistry(
        {
            AgentId.CODEX: SlowFakeLLM("codex", [_thesis("codex"), _ack("codex"), _turn("codex")], delay=0.05),
            AgentId.GEMINI: gemini,
            AgentId.CLAUDE: FakeLLM("claude", [_thesis("claude"), _ack("claude")]),
        }
    )
    engine = DebateEngine(storage, registry)

    async def scenario():
        state = await engine.create_debate("Queued Message Test", "Choose one stack.")
        state = await engine.start_theses(state.id)
        state = await engine.share_theses(state.id)

        turn_task = asyncio.create_task(engine.run_turn(state.id, AgentId.CODEX))
        for _ in range(100):
            running_state = storage.read_state(state.id)
            if running_state.agents[AgentId.CODEX].status.value == "running":
                break
            await asyncio.sleep(0.001)
        else:
            raise AssertionError("codex did not enter running state")

        queued_state = await engine.set_send_after_this(state.id, "Queued note for the next speaker.")
        assert queued_state.send_after_this == "Queued note for the next speaker."
        assert queued_state.user_messages == []

        state = await turn_task
        assert state.send_after_this is None
        assert state.user_messages[-1].content == "Queued note for the next speaker."
        assert state.user_messages[-1].after_round == 1

        state = await engine.run_turn(state.id, AgentId.GEMINI)
        assert state.rounds[-1].agent == AgentId.GEMINI
        assert "Queued note for the next speaker." in gemini.prompts[-1]

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(scenario())
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def test_storage_backfills_legacy_queued_user_messages(tmp_path):
    storage = DebateStorage(tmp_path)
    engine = DebateEngine(storage, AgentRegistry())

    async def scenario():
        state = await engine.create_debate("Legacy Queue Backfill Test", "Choose one stack.")
        storage.append_event(new_event(state.id, "turn_completed", "codex", {}))
        storage.append_event(
            new_event(
                state.id,
                "send_after_this_set",
                "user",
                {"text": "Please keep this dependency-free."},
            )
        )
        storage.append_event(new_event(state.id, "turn_completed", "gemini", {}))

        reloaded = storage.read_state(state.id)
        assert len(reloaded.user_messages) == 1
        assert reloaded.user_messages[0].content == "Please keep this dependency-free."
        assert reloaded.user_messages[0].after_round == 2

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(scenario())
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def test_storage_dedupes_repeated_user_messages(tmp_path):
    storage = DebateStorage(tmp_path)
    engine = DebateEngine(storage, AgentRegistry())

    async def scenario():
        state = await engine.create_debate("User Message Dedupe Test", "Choose one stack.")
        state.user_messages = [
            UserMessageRecord(
                id="user-001",
                content="Same message.",
                created_at="2026-05-11T00:00:00+00:00",
                after_round=1,
            ),
            UserMessageRecord(
                id="user-002",
                content="Same message.",
                created_at="2026-05-11T00:01:00+00:00",
                after_round=2,
            ),
        ]
        storage.write_state(state)

        reloaded = storage.read_state(state.id)
        assert len(reloaded.user_messages) == 1
        assert reloaded.user_messages[0].id == "user-001"

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(scenario())
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def test_next_agent_follows_current_turn_order_after_reorder(tmp_path):
    storage = DebateStorage(tmp_path)
    engine = DebateEngine(storage, AgentRegistry())

    async def scenario():
        state = await engine.create_debate("Order Test", "Choose one stack.")
        state.next_agent = AgentId.CODEX
        state.turn_order = [AgentId.CLAUDE, AgentId.CODEX, AgentId.GEMINI]

        assert engine._next_agent(state) == AgentId.GEMINI

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(scenario())
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def test_reorder_agents_persists_order_and_preserves_next_turn_anchor(tmp_path):
    storage = DebateStorage(tmp_path)
    engine = DebateEngine(storage, AgentRegistry())

    async def scenario():
        state = await engine.create_debate("Persist Order Test", "Choose one stack.")
        state.next_agent = AgentId.CODEX
        storage.write_state(state)

        state = await engine.reorder_agents(
            state.id,
            [AgentId.CLAUDE, AgentId.CODEX, AgentId.GEMINI],
        )

        assert state.turn_order == [AgentId.CLAUDE, AgentId.CODEX, AgentId.GEMINI]
        assert state.next_agent == AgentId.CODEX
        assert engine._next_agent(state) == AgentId.GEMINI
        assert storage.read_state(state.id).turn_order == [AgentId.CLAUDE, AgentId.CODEX, AgentId.GEMINI]

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(scenario())
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def test_reorder_agents_rejects_invalid_order(tmp_path):
    storage = DebateStorage(tmp_path)
    engine = DebateEngine(storage, AgentRegistry())

    async def scenario():
        state = await engine.create_debate("Invalid Order Test", "Choose one stack.")

        try:
            await engine.reorder_agents(state.id, [AgentId.CODEX, AgentId.CODEX])
        except ValueError as exc:
            assert "duplicate" in str(exc)
        else:
            raise AssertionError("reorder_agents should reject duplicate ids")

        try:
            await engine.reorder_agents(state.id, [AgentId.CODEX, AgentId.GEMINI, "unknown"])
        except ValueError as exc:
            assert "unknown" in str(exc)
        else:
            raise AssertionError("reorder_agents should reject unknown ids")

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(scenario())
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def test_update_agent_before_thesis_generation_persists_config(tmp_path):
    storage = DebateStorage(tmp_path)
    engine = DebateEngine(storage, AgentRegistry())

    async def scenario():
        state = await engine.create_debate("Agent Edit Test", "Choose one stack.")

        state = await engine.update_agent(
            state.id,
            AgentId.CODEX,
            DebateAgentConfig(
                name="architect",
                provider=ProviderKind.GEMINI,
                model="gemini-2.5-flash",
                display_name="Architect",
                color="rose",
                write_thesis=True,
                additional_note="Argue from maintainability.",
            ),
        )

        assert AgentId.CODEX not in state.agents
        assert "architect" in state.agents
        assert state.turn_order[0] == "architect"
        assert state.agents["architect"].provider == ProviderKind.GEMINI
        assert state.agents["architect"].model == "gemini-2.5-flash"
        assert state.agents["architect"].display_name == "Architect"
        assert state.agents["architect"].color == "rose"
        assert state.agents["architect"].additional_note == "Argue from maintainability."
        assert storage.read_state(state.id).agents["architect"].color == "rose"

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(scenario())
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def test_update_agent_rejects_after_thesis_generation_starts(tmp_path):
    storage = DebateStorage(tmp_path)
    registry = AgentRegistry(
        {
            AgentId.CODEX: FakeLLM("codex", [_thesis("codex")]),
            AgentId.GEMINI: FakeLLM("gemini", [_thesis("gemini")]),
            AgentId.CLAUDE: FakeLLM("claude", [_thesis("claude")]),
        }
    )
    engine = DebateEngine(storage, registry)

    async def scenario():
        state = await engine.create_debate("Agent Edit Locked Test", "Choose one stack.")
        state = await engine.start_theses(state.id)

        try:
            await engine.update_agent(
                state.id,
                AgentId.CODEX,
                DebateAgentConfig(
                    name=AgentId.CODEX,
                    provider=ProviderKind.CODEX,
                    display_name="Changed",
                ),
            )
        except RuntimeError as exc:
            assert "before thesis generation starts" in str(exc)
        else:
            raise AssertionError("update_agent should reject after thesis generation starts")

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(scenario())
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def test_start_theses_repairs_malformed_agent_json(tmp_path):
    storage = DebateStorage(tmp_path)
    registry = AgentRegistry(
        {
            AgentId.CODEX: FakeLLM("codex", ["I choose FastAPI.", _thesis("codex")]),
            AgentId.GEMINI: FakeLLM("gemini", [_thesis("gemini")]),
            AgentId.CLAUDE: FakeLLM("claude", [_thesis("claude")]),
        }
    )
    engine = DebateEngine(storage, registry)

    async def scenario():
        state = await engine.create_debate("Repair Test", "Choose one stack.")
        state = await engine.start_theses(state.id)
        assert state.phase == DebatePhase.THESES_READY
        assert state.theses[AgentId.CODEX].decision == "Use FastAPI with React"
        assert storage.read_artifact(state.id, "errors/codex-ThesisPayload-raw.txt") == "I choose FastAPI."

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(scenario())
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def test_start_theses_can_retry_stuck_starting_state(tmp_path):
    storage = DebateStorage(tmp_path)
    registry = AgentRegistry(
        {
            AgentId.CODEX: FakeLLM("codex", [_thesis("codex")]),
            AgentId.GEMINI: FakeLLM("gemini", [_thesis("gemini")]),
            AgentId.CLAUDE: FakeLLM("claude", [_thesis("claude")]),
        }
    )
    engine = DebateEngine(storage, registry)

    async def scenario():
        state = await engine.create_debate("Retry Test", "Choose one stack.")
        state.phase = DebatePhase.STARTING_THESES
        storage.write_state(state)

        state = await engine.start_theses(state.id)
        assert state.phase == DebatePhase.THESES_READY
        assert set(state.theses) == {AgentId.CODEX, AgentId.GEMINI, AgentId.CLAUDE}

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(scenario())
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def test_regenerate_thesis_reruns_one_agent(tmp_path):
    storage = DebateStorage(tmp_path)
    registry = AgentRegistry(
        {
            AgentId.CODEX: FakeLLM(
                "codex",
                [
                    _thesis("codex"),
                    _thesis("codex", decision="Use Django with Vue"),
                ],
            ),
            AgentId.GEMINI: FakeLLM("gemini", [_thesis("gemini")]),
            AgentId.CLAUDE: FakeLLM("claude", [_thesis("claude")]),
        }
    )
    engine = DebateEngine(storage, registry)

    async def scenario():
        state = await engine.create_debate("Regenerate Test", "Choose one stack.")
        state = await engine.start_theses(state.id)
        assert state.phase == DebatePhase.THESES_READY
        assert state.theses[AgentId.CODEX].decision == "Use FastAPI with React"

        state = await engine.regenerate_thesis(state.id, AgentId.CODEX)

        assert state.phase == DebatePhase.THESES_READY
        assert state.theses[AgentId.CODEX].decision == "Use Django with Vue"
        assert state.theses[AgentId.GEMINI].decision == "Use FastAPI with React"
        assert state.theses[AgentId.CLAUDE].decision == "Use FastAPI with React"

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(scenario())
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def test_regenerate_thesis_runs_multiple_agents_in_parallel(tmp_path):
    storage = DebateStorage(tmp_path)
    registry = AgentRegistry(
        {
            AgentId.CODEX: SlowFakeLLM(
                "codex",
                [
                    _thesis("codex"),
                    _thesis("codex", decision="Use Django with Vue"),
                ],
            ),
            AgentId.GEMINI: SlowFakeLLM(
                "gemini",
                [
                    _thesis("gemini"),
                    _thesis("gemini", decision="Use Phoenix with LiveView"),
                ],
            ),
            AgentId.CLAUDE: FakeLLM("claude", [_thesis("claude")]),
        }
    )
    engine = DebateEngine(storage, registry)

    async def scenario():
        state = await engine.create_debate("Parallel Regenerate Test", "Choose one stack.")
        state = await engine.start_theses(state.id)
        assert state.phase == DebatePhase.THESES_READY

        codex_state, gemini_state = await asyncio.gather(
            engine.regenerate_thesis(state.id, AgentId.CODEX),
            engine.regenerate_thesis(state.id, AgentId.GEMINI),
        )

        state = storage.read_state(state.id)
        assert codex_state.phase in {DebatePhase.STARTING_THESES, DebatePhase.THESES_READY}
        assert gemini_state.phase in {DebatePhase.STARTING_THESES, DebatePhase.THESES_READY}
        assert state.phase == DebatePhase.THESES_READY
        assert state.theses[AgentId.CODEX].decision == "Use Django with Vue"
        assert state.theses[AgentId.GEMINI].decision == "Use Phoenix with LiveView"
        assert state.theses[AgentId.CLAUDE].decision == "Use FastAPI with React"

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(scenario())
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def test_regenerate_thesis_rejects_after_debate_rounds_start(tmp_path):
    storage = DebateStorage(tmp_path)
    registry = AgentRegistry(
        {
            AgentId.CODEX: FakeLLM("codex", [_thesis("codex"), _ack("codex"), _turn("codex")]),
            AgentId.GEMINI: FakeLLM("gemini", [_thesis("gemini"), _ack("gemini")]),
            AgentId.CLAUDE: FakeLLM("claude", [_thesis("claude"), _ack("claude")]),
        }
    )
    engine = DebateEngine(storage, registry)

    async def scenario():
        state = await engine.create_debate("Regenerate Lock Test", "Choose one stack.")
        state = await engine.start_theses(state.id)
        state = await engine.share_theses(state.id)
        state = await engine.run_turn(state.id, AgentId.CODEX)

        try:
            await engine.regenerate_thesis(state.id, AgentId.CODEX)
        except ValueError as exc:
            assert "after thesis sharing has started" in str(exc)
        else:
            raise AssertionError("regenerate_thesis should reject after debate rounds start")

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(scenario())
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def test_auto_mode_shares_theses_after_generation(tmp_path):
    storage = DebateStorage(tmp_path)
    registry = AgentRegistry(
        {
            AgentId.CODEX: FakeLLM(
                "codex",
                [
                    _thesis("codex"),
                    _ack("codex"),
                    _consensus_turn("codex", "propose"),
                    _final_markdown(),
                    _final_review("codex"),
                ],
            ),
            AgentId.GEMINI: FakeLLM(
                "gemini",
                [
                    _thesis("gemini"),
                    _ack("gemini"),
                    _consensus_turn("gemini", "accept", "consensus-001-codex"),
                    _final_review("gemini"),
                ],
            ),
            AgentId.CLAUDE: FakeLLM(
                "claude",
                [
                    _thesis("claude"),
                    _ack("claude"),
                    _consensus_turn("claude", "accept", "consensus-001-codex"),
                    _final_review("claude"),
                ],
            ),
        }
    )
    engine = DebateEngine(storage, registry)

    async def scenario():
        state = await engine.create_debate("Auto Thesis Test", "Choose one stack.")
        state = await engine.set_auto_mode(state.id, True)
        assert state.auto_mode is True
        assert state.phase == DebatePhase.CREATED

        state = await _wait_for_phase(storage, state.id, DebatePhase.ACCEPTED)
        assert state.phase == DebatePhase.ACCEPTED
        assert set(state.theses) == {AgentId.CODEX, AgentId.GEMINI, AgentId.CLAUDE}
        assert state.consensus is not None
        assert state.final_document.final_path == "final/final.md"

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(scenario())
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def test_enabling_auto_mode_shares_ready_theses(tmp_path):
    storage = DebateStorage(tmp_path)
    registry = AgentRegistry(
        {
            AgentId.CODEX: FakeLLM(
                "codex",
                [
                    _thesis("codex"),
                    _ack("codex"),
                    _consensus_turn("codex", "propose"),
                    _final_markdown(),
                    _final_review("codex"),
                ],
            ),
            AgentId.GEMINI: FakeLLM(
                "gemini",
                [
                    _thesis("gemini"),
                    _ack("gemini"),
                    _consensus_turn("gemini", "accept", "consensus-001-codex"),
                    _final_review("gemini"),
                ],
            ),
            AgentId.CLAUDE: FakeLLM(
                "claude",
                [
                    _thesis("claude"),
                    _ack("claude"),
                    _consensus_turn("claude", "accept", "consensus-001-codex"),
                    _final_review("claude"),
                ],
            ),
        }
    )
    engine = DebateEngine(storage, registry)

    async def scenario():
        state = await engine.create_debate("Late Auto Thesis Test", "Choose one stack.")
        state = await engine.start_theses(state.id)
        assert state.phase == DebatePhase.THESES_READY

        state = await engine.set_auto_mode(state.id, True)

        assert state.auto_mode is True
        assert state.phase == DebatePhase.THESES_READY
        state = await _wait_for_phase(storage, state.id, DebatePhase.ACCEPTED)
        assert state.phase == DebatePhase.ACCEPTED
        assert state.consensus is not None
        assert state.final_document.final_path == "final/final.md"

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(scenario())
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def test_auto_mode_stops_and_records_reason_when_step_fails(tmp_path):
    storage = DebateStorage(tmp_path)
    registry = AgentRegistry(
        {
            AgentId.CODEX: FakeLLM("codex", [_thesis("codex"), _ack("codex"), _turn("codex")]),
            AgentId.GEMINI: FakeLLM("gemini", [_thesis("gemini"), _ack("gemini")]),
            AgentId.CLAUDE: FakeLLM("claude", [_thesis("claude"), _ack("claude")]),
        }
    )
    engine = DebateEngine(storage, registry)

    async def scenario():
        state = await engine.create_debate("Auto Failure Test", "Choose one stack.")
        state = await engine.start_theses(state.id)
        state = await engine.share_theses(state.id)
        state = await engine.run_turn(state.id, AgentId.CODEX)

        state = await engine.set_auto_mode(state.id, True)
        assert state.auto_mode is True

        for _ in range(100):
            current = storage.read_state(state.id)
            if (
                current.auto_mode is False
                and current.agents[AgentId.GEMINI].status == AgentStatus.FAILED
            ):
                break
            await asyncio.sleep(0.01)
        else:
            raise AssertionError("auto mode did not stop after the failing turn")

        assert current.phase == DebatePhase.DEBATING
        assert current.next_agent == AgentId.CODEX
        assert "responses exhausted" in current.agents[AgentId.GEMINI].last_error
        stop_events = [
            event
            for event in storage.read_events(state.id)
            if event.type == "auto_mode_stopped"
        ]
        assert stop_events[-1].payload["reason"] == "step_error"
        assert "responses exhausted" in stop_events[-1].payload["error"]

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(scenario())
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def test_consensus_propose_accept_withdraw(tmp_path):
    storage = DebateStorage(tmp_path)
    registry = AgentRegistry(
        {
            AgentId.CODEX: FakeLLM("codex", [_thesis("codex"), _ack("codex"), _consensus_turn("codex", "propose")]),
            AgentId.GEMINI: FakeLLM("gemini", [_thesis("gemini"), _ack("gemini"), _consensus_turn("gemini", "accept")]),
            AgentId.CLAUDE: FakeLLM("claude", [_thesis("claude"), _ack("claude"), _consensus_turn("claude", "accept")]),
        }
    )
    engine = DebateEngine(storage, registry)

    async def scenario():
        state = await engine.create_debate("Consensus Test", "Choose one stack.")
        state = await engine.start_theses(state.id)
        state = await engine.share_theses(state.id)

        state = await engine.run_turn(state.id, AgentId.CODEX)
        proposal_id = state.consensus_proposals[-1].id
        assert state.consensus is None

        registry.get_agent(AgentId.GEMINI).scripted_responses = [_consensus_turn(
            "gemini", "accept", proposal_id
        )]
        state = await engine.run_turn(state.id, AgentId.GEMINI)
        assert state.consensus is None

        registry.get_agent(AgentId.CLAUDE).scripted_responses = [_consensus_turn(
            "claude", "accept", proposal_id
        )]
        state = await engine.run_turn(state.id, AgentId.CLAUDE)
        assert state.phase == DebatePhase.CONSENSUS_REACHED
        assert state.consensus is not None
        assert set(state.consensus.agreed_by) == {AgentId.CODEX, AgentId.GEMINI, AgentId.CLAUDE}

        registry.get_agent(AgentId.GEMINI).scripted_responses.append(
            _consensus_turn("gemini", "withdraw", proposal_id)
        )
        storage.write_state(state)
        state = await engine.run_turn(state.id, AgentId.GEMINI)
        assert state.consensus is None
        assert AgentId.GEMINI not in state.consensus_proposals[-1].accepted_by

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(scenario())
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def test_run_turn_can_recover_failed_debate_with_existing_theses(tmp_path):
    storage = DebateStorage(tmp_path)
    registry = AgentRegistry(
        {
            AgentId.CODEX: FakeLLM("codex", [_thesis("codex"), _ack("codex"), _turn("codex")]),
            AgentId.GEMINI: FakeLLM("gemini", [_thesis("gemini"), _ack("gemini")]),
            AgentId.CLAUDE: FakeLLM("claude", [_thesis("claude"), _ack("claude")]),
        }
    )
    engine = DebateEngine(storage, registry)

    async def scenario():
        state = await engine.create_debate("Failed Turn Retry", "Choose one stack.")
        state = await engine.start_theses(state.id)
        state = await engine.share_theses(state.id)
        state.phase = DebatePhase.FAILED
        storage.write_state(state)

        state = await engine.run_turn(state.id, AgentId.CODEX)
        assert state.phase == DebatePhase.DEBATING
        assert state.rounds[-1].agent == AgentId.CODEX

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(scenario())
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def test_regenerate_last_turn_replaces_latest_discussion(tmp_path):
    storage = DebateStorage(tmp_path)
    registry = AgentRegistry(
        {
            AgentId.CODEX: FakeLLM(
                "codex",
                [
                    _thesis("codex"),
                    _ack("codex"),
                    _turn("codex"),
                    _turn("codex", discussion="I now build on <@gemini> with a revised discussion."),
                ],
            ),
            AgentId.GEMINI: FakeLLM("gemini", [_thesis("gemini"), _ack("gemini")]),
            AgentId.CLAUDE: FakeLLM("claude", [_thesis("claude"), _ack("claude")]),
        }
    )
    engine = DebateEngine(storage, registry)

    async def scenario():
        state = await engine.create_debate("Regenerate Turn Test", "Choose one stack.")
        state = await engine.start_theses(state.id)
        state = await engine.share_theses(state.id)
        state = await engine.run_turn(state.id, AgentId.CODEX)
        assert len(state.rounds) == 1
        assert state.rounds[-1].discussion.startswith("I like what <@gemini> said")
        state.agents[AgentId.CODEX].session_id = "stale-session-with-old-turn"
        storage.write_state(state)

        state = await engine.regenerate_last_turn(state.id)

        assert len(state.rounds) == 1
        assert state.rounds[-1].index == 1
        assert state.rounds[-1].agent == AgentId.CODEX
        assert state.rounds[-1].discussion == "I now build on <@gemini> with a revised discussion."
        assert state.next_agent == AgentId.CODEX
        assert state.agents[AgentId.CODEX].session_id != "stale-session-with-old-turn"

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(scenario())
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def test_consensus_rejection_closes_active_proposal(tmp_path):
    storage = DebateStorage(tmp_path)
    registry = AgentRegistry(
        {
            AgentId.CODEX: FakeLLM("codex", [_thesis("codex"), _ack("codex"), _consensus_turn("codex", "propose")]),
            AgentId.GEMINI: FakeLLM("gemini", [_thesis("gemini"), _ack("gemini"), _consensus_turn("gemini", "accept")]),
            AgentId.CLAUDE: FakeLLM("claude", [_thesis("claude"), _ack("claude"), _consensus_turn("claude", "reject")]),
        }
    )
    engine = DebateEngine(storage, registry)

    async def scenario():
        state = await engine.create_debate("Consensus Reject Test", "Choose one stack.")
        state = await engine.start_theses(state.id)
        state = await engine.share_theses(state.id)

        state = await engine.run_turn(state.id, AgentId.CODEX)
        proposal_id = state.consensus_proposals[-1].id

        registry.get_agent(AgentId.GEMINI).scripted_responses = [_consensus_turn(
            "gemini", "accept", proposal_id
        )]
        state = await engine.run_turn(state.id, AgentId.GEMINI)
        assert state.consensus_proposals[-1].status == "active"

        registry.get_agent(AgentId.CLAUDE).scripted_responses = [_consensus_turn(
            "claude", "reject", proposal_id, reason="Needs a more precise consensus summary."
        )]
        state = await engine.run_turn(state.id, AgentId.CLAUDE)
        assert state.consensus is None
        assert state.consensus_proposals[-1].status == "rejected"
        assert AgentId.CLAUDE in state.consensus_proposals[-1].rejected_by

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(scenario())
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def test_regenerate_last_turn_replaces_consensus_proposal(tmp_path):
    storage = DebateStorage(tmp_path)
    registry = AgentRegistry(
        {
            AgentId.CODEX: FakeLLM(
                "codex",
                [
                    _thesis("codex"),
                    _ack("codex"),
                    _consensus_turn("codex", "propose"),
                    _turn("codex", discussion="I now build on <@gemini> without proposing consensus."),
                ],
            ),
            AgentId.GEMINI: FakeLLM("gemini", [_thesis("gemini"), _ack("gemini")]),
            AgentId.CLAUDE: FakeLLM("claude", [_thesis("claude"), _ack("claude")]),
        }
    )
    engine = DebateEngine(storage, registry)

    async def scenario():
        state = await engine.create_debate("Regenerate Consensus Turn Test", "Choose one stack.")
        state = await engine.start_theses(state.id)
        state = await engine.share_theses(state.id)
        state = await engine.run_turn(state.id, AgentId.CODEX)
        assert len(state.rounds) == 1
        assert len(state.consensus_proposals) == 1

        state = await engine.regenerate_last_turn(state.id)

        assert len(state.rounds) == 1
        assert state.rounds[-1].agent == AgentId.CODEX
        assert state.rounds[-1].consensus_action is None
        assert state.rounds[-1].discussion == "I now build on <@gemini> without proposing consensus."
        assert state.consensus_proposals == []
        assert state.consensus is None

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(scenario())
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def test_regenerate_last_turn_reopens_reached_consensus(tmp_path):
    storage = DebateStorage(tmp_path)
    registry = AgentRegistry(
        {
            AgentId.CODEX: FakeLLM(
                "codex",
                [
                    _thesis("codex"),
                    _ack("codex"),
                    _consensus_turn("codex", "propose"),
                ],
            ),
            AgentId.GEMINI: FakeLLM(
                "gemini",
                [
                    _thesis("gemini"),
                    _ack("gemini"),
                    _consensus_turn("gemini", "accept", "consensus-001-codex"),
                ],
            ),
            AgentId.CLAUDE: FakeLLM(
                "claude",
                [
                    _thesis("claude"),
                    _ack("claude"),
                    _consensus_turn("claude", "accept", "consensus-001-codex"),
                    _turn("claude", discussion="I reopened <@gemini>'s final consensus turn for another pass."),
                ],
            ),
        }
    )
    engine = DebateEngine(storage, registry)

    async def scenario():
        state = await engine.create_debate("Regenerate Reached Consensus Test", "Choose one stack.")
        state = await engine.start_theses(state.id)
        state = await engine.share_theses(state.id)
        state = await engine.run_turn(state.id, AgentId.CODEX)
        state = await engine.run_turn(state.id, AgentId.GEMINI)
        state = await engine.run_turn(state.id, AgentId.CLAUDE)
        assert state.phase == DebatePhase.CONSENSUS_REACHED
        assert state.consensus is not None
        assert state.consensus_proposals[-1].status == "accepted"

        state = await engine.regenerate_last_turn(state.id)

        assert state.phase == DebatePhase.DEBATING
        assert state.consensus is None
        assert state.rounds[-1].agent == AgentId.CLAUDE
        assert state.rounds[-1].consensus_action is None
        assert state.rounds[-1].discussion == "I reopened <@gemini>'s final consensus turn for another pass."
        assert state.consensus_proposals[-1].status == "active"
        assert state.consensus_proposals[-1].accepted_by == [AgentId.CODEX, AgentId.GEMINI]

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(scenario())
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def test_draft_final_broadcasts_running_state_before_llm_call(tmp_path):
    storage = DebateStorage(tmp_path)
    broadcasts = []
    registry = AgentRegistry(
        {
            AgentId.CODEX: FakeLLM(
                "codex",
                [
                    _thesis("codex"),
                    _ack("codex"),
                    _consensus_turn("codex", "propose"),
                    _final_markdown(),
                    _final_review("codex"),
                ],
            ),
            AgentId.GEMINI: FakeLLM(
                "gemini",
                [
                    _thesis("gemini"),
                    _ack("gemini"),
                    _consensus_turn("gemini", "accept", "consensus-001-codex"),
                    _final_review("gemini"),
                ],
            ),
            AgentId.CLAUDE: FakeLLM(
                "claude",
                [
                    _thesis("claude"),
                    _ack("claude"),
                    _consensus_turn("claude", "accept", "consensus-001-codex"),
                    _final_review("claude"),
                ],
            ),
        }
    )

    async def broadcaster(debate_id: str, message: dict) -> None:
        broadcasts.append((debate_id, message))

    engine = DebateEngine(storage, registry, broadcaster)

    async def scenario():
        state = await engine.create_debate("Draft Final Streaming Test", "Choose one stack.")
        state = await engine.start_theses(state.id)
        state = await engine.share_theses(state.id)
        state = await engine.run_turn(state.id, AgentId.CODEX)
        state = await engine.run_turn(state.id, AgentId.GEMINI)
        state = await engine.run_turn(state.id, AgentId.CLAUDE)
        assert state.phase == DebatePhase.CONSENSUS_REACHED
        state.agents[AgentId.CODEX].session_id = "stale-turn-session"
        storage.write_state(state)

        broadcasts.clear()
        state = await engine.draft_final(state.id)

        assert state.phase == DebatePhase.REVIEWING_FINAL
        assert state.agents[AgentId.CODEX].status.value == "done"
        assert state.agents[AgentId.CODEX].session_id != "stale-turn-session"
        assert state.final_document.draft_path == "final/draft-v001.md"
        assert state.final_document.drafts[0].draft_path == "final/draft-v001.md"
        assert storage.read_artifact(state.id, "final/draft-v001.md").startswith("# Final Engineering Thesis")
        assert broadcasts[0][1]["type"] == "state_snapshot"
        assert broadcasts[0][1]["state"]["phase"] == "drafting_final"
        assert broadcasts[0][1]["state"]["agents"][AgentId.CODEX]["status"] == "running"
        assert broadcasts[1][1] == {
            "type": "agent_status",
            "agent": AgentId.CODEX,
            "status": "running",
        }

        broadcasts.clear()
        state = await engine.review_final(state.id)

        assert state.phase == DebatePhase.ACCEPTED
        assert set(state.final_document.accepted_by) == {AgentId.CODEX, AgentId.GEMINI, AgentId.CLAUDE}
        assert broadcasts[0][1]["type"] == "state_snapshot"
        assert broadcasts[0][1]["state"]["phase"] == "reviewing_final"
        assert broadcasts[0][1]["state"]["agents"][AgentId.CODEX]["status"] == "running"
        assert {
            message["agent"]
            for _, message in broadcasts
            if message["type"] == "agent_status" and message["status"] == "done"
        } == {AgentId.CODEX, AgentId.GEMINI, AgentId.CLAUDE}

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(scenario())
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def test_rejected_final_draft_is_preserved_when_revision_is_written(tmp_path):
    storage = DebateStorage(tmp_path)
    codex = FakeLLM(
        "codex",
        [
            _thesis("codex"),
            _ack("codex"),
            _consensus_turn("codex", "propose"),
            _final_markdown("Use FastAPI with React."),
            _final_review("codex"),
            _final_markdown("Use FastAPI with React, scoped to restart-safe duplicate suppression."),
            _final_review("codex"),
        ],
    )
    registry = AgentRegistry(
        {
            AgentId.CODEX: codex,
            AgentId.GEMINI: FakeLLM(
                "gemini",
                [
                    _thesis("gemini"),
                    _ack("gemini"),
                    _consensus_turn("gemini", "accept", "consensus-001-codex"),
                    _final_review("gemini", "reject"),
                    _final_review("gemini"),
                ],
            ),
            AgentId.CLAUDE: FakeLLM(
                "claude",
                [
                    _thesis("claude"),
                    _ack("claude"),
                    _consensus_turn("claude", "accept", "consensus-001-codex"),
                    _final_review("claude"),
                    _final_review("claude"),
                ],
            ),
        }
    )
    engine = DebateEngine(storage, registry)

    async def scenario():
        state = await engine.create_debate("Rejected Draft History Test", "Choose one stack.")
        state = await engine.start_theses(state.id)
        state = await engine.share_theses(state.id)
        state = await engine.run_turn(state.id, AgentId.CODEX)
        state = await engine.run_turn(state.id, AgentId.GEMINI)
        state = await engine.run_turn(state.id, AgentId.CLAUDE)

        state = await engine.draft_final(state.id)
        state = await engine.review_final(state.id)

        assert state.phase == DebatePhase.REVISING_FINAL
        assert state.final_document.draft_path == "final/draft-v001.md"
        assert state.final_document.drafts[0].status == "rejected"
        assert state.final_document.drafts[0].reviews[AgentId.GEMINI]["verdict"] == "reject"

        state = await engine.draft_final(state.id)

        assert "Your draft was rejected" in codex.prompts[-1]
        assert state.final_document.draft_path == "final/draft-v002.md"
        assert [draft.draft_path for draft in state.final_document.drafts] == [
            "final/draft-v001.md",
            "final/draft-v002.md",
        ]
        assert storage.read_artifact(state.id, "final/draft-v001.md")
        assert storage.read_artifact(state.id, "final/draft-v002.md")
        assert state.final_document.drafts[0].status == "rejected"
        assert state.final_document.drafts[1].status == "drafted"
        assert state.reviews == {}

        state = await engine.review_final(state.id)

        assert state.phase == DebatePhase.ACCEPTED
        assert state.final_document.drafts[0].status == "rejected"
        assert state.final_document.drafts[1].status == "accepted"
        assert state.final_document.final_path == "final/final.md"

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(scenario())
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def test_failed_draft_final_recovers_to_consensus_reached(tmp_path):
    storage = DebateStorage(tmp_path)
    broadcasts = []
    registry = AgentRegistry(
        {
            AgentId.CODEX: FakeLLM(
                "codex",
                [
                    _thesis("codex"),
                    _ack("codex"),
                    _consensus_turn("codex", "propose"),
                    "not a valid final draft",
                ],
            ),
            AgentId.GEMINI: FakeLLM(
                "gemini",
                [
                    _thesis("gemini"),
                    _ack("gemini"),
                    _consensus_turn("gemini", "accept", "consensus-001-codex"),
                ],
            ),
            AgentId.CLAUDE: FakeLLM(
                "claude",
                [
                    _thesis("claude"),
                    _ack("claude"),
                    _consensus_turn("claude", "accept", "consensus-001-codex"),
                ],
            ),
        }
    )

    async def broadcaster(debate_id: str, message: dict) -> None:
        broadcasts.append((debate_id, message))

    engine = DebateEngine(storage, registry, broadcaster)

    async def scenario():
        state = await engine.create_debate("Failed Draft Recovery Test", "Choose one stack.")
        state = await engine.start_theses(state.id)
        state = await engine.share_theses(state.id)
        state = await engine.run_turn(state.id, AgentId.CODEX)
        state = await engine.run_turn(state.id, AgentId.GEMINI)
        state = await engine.run_turn(state.id, AgentId.CLAUDE)
        assert state.phase == DebatePhase.CONSENSUS_REACHED

        try:
            await engine.draft_final(state.id)
        except Exception as exc:
            assert "Missing required markdown headings" in str(exc)
        else:
            raise AssertionError("invalid final draft should fail")

        recovered = storage.read_state(state.id)
        assert recovered.phase == DebatePhase.CONSENSUS_REACHED
        assert recovered.final_document is None
        assert recovered.agents[AgentId.CODEX].status == AgentStatus.FAILED
        state_snapshots = [message for _, message in broadcasts if message["type"] == "state_snapshot"]
        assert state_snapshots[-1]["state"]["phase"] == "consensus_reached"

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(scenario())
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def test_failed_regenerate_removes_old_turn_context(tmp_path):
    storage = DebateStorage(tmp_path)
    registry = AgentRegistry(
        {
            AgentId.CODEX: FakeLLM(
                "codex",
                [
                    _thesis("codex"),
                    _ack("codex"),
                    _turn("codex"),
                    '{"type":"debate_turn","agent":"codex","reply_to":["gemini"],"discussion":"invalid"}',
                ],
            ),
            AgentId.GEMINI: FakeLLM("gemini", [_thesis("gemini"), _ack("gemini")]),
            AgentId.CLAUDE: FakeLLM("claude", [_thesis("claude"), _ack("claude")]),
        }
    )
    engine = DebateEngine(storage, registry)

    async def scenario():
        state = await engine.create_debate("Failed Regenerate Cleanup Test", "Choose one stack.")
        state = await engine.start_theses(state.id)
        state = await engine.share_theses(state.id)
        state = await engine.run_turn(state.id, AgentId.CODEX)
        artifact_path = state.rounds[-1].artifact_path
        assert storage.read_artifact(state.id, artifact_path)

        try:
            await engine.regenerate_last_turn(state.id)
        except Exception:
            pass
        else:
            raise AssertionError("regeneration should fail validation")

        state = storage.read_state(state.id)
        assert state.rounds == []
        assert state.shared_evidence == []
        assert state.agents[AgentId.CODEX].session_id is None
        try:
            storage.read_artifact(state.id, artifact_path)
        except FileNotFoundError:
            pass
        else:
            raise AssertionError("old round artifact should be deleted before rerun")

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(scenario())
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def test_run_turn_failed_debate_without_theses_explains_retry_path(tmp_path):
    storage = DebateStorage(tmp_path)
    registry = AgentRegistry(
        {
            AgentId.CODEX: FakeLLM("codex", []),
            AgentId.GEMINI: FakeLLM("gemini", []),
            AgentId.CLAUDE: FakeLLM("claude", []),
        }
    )
    engine = DebateEngine(storage, registry)

    async def scenario():
        state = await engine.create_debate("Failed Thesis Retry", "Choose one stack.")
        state.phase = DebatePhase.FAILED
        storage.write_state(state)
        try:
            await engine.run_turn(state.id, AgentId.CODEX)
        except ValueError as exc:
            assert "retry Start Theses first" in str(exc)
        else:
            raise AssertionError("run_turn should require thesis retry first")

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(scenario())
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def test_custom_debate_agents_can_share_provider_models_and_skip_thesis(tmp_path):
    storage = DebateStorage(tmp_path)
    registry = AgentRegistry(
        {
            "codex1": FakeLLM("codex", [_thesis("codex1"), _ack("codex1")]),
            "codex2": FakeLLM("codex", [_thesis("codex2"), _ack("codex2")]),
            "judge": FakeLLM("claude", [_ack("judge"), _turn_for("judge", ["codex1", "codex2"])]),
        }
    )
    engine = DebateEngine(storage, registry)

    async def scenario():
        state = await engine.create_debate(
            "Dynamic Agents",
            "Choose one stack.",
            agent_configs=[
                DebateAgentConfig(name="codex1", provider=ProviderKind.CODEX, model="gpt-5.4"),
                DebateAgentConfig(name="codex2", provider=ProviderKind.CODEX, model="gpt-5.4-mini"),
                DebateAgentConfig(
                    name="judge",
                    provider=ProviderKind.CLAUDE,
                    model="claude-sonnet-4-6",
                    write_thesis=False,
                    debate_style="neutral",
                ),
            ],
        )
        assert state.turn_order == ["codex1", "codex2", "judge"]
        assert state.agents["codex2"].model == "gpt-5.4-mini"
        assert not state.agents["judge"].write_thesis

        state = await engine.start_theses(state.id)
        assert set(state.theses) == {"codex1", "codex2"}
        assert "judge" not in state.theses

        state = await engine.share_theses(state.id)
        state = await engine.run_turn(state.id, "judge")
        assert state.rounds[-1].agent == "judge"

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(scenario())
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def test_non_thesis_agent_turn_is_repaired_before_failure(tmp_path):
    storage = DebateStorage(tmp_path)
    registry = AgentRegistry(
        {
            "codex1": FakeLLM("codex", [_thesis("codex1"), _ack("codex1")]),
            "codex2": FakeLLM("codex", [_thesis("codex2"), _ack("codex2")]),
            "judge": FakeLLM(
                "claude",
                [
                    _ack("judge"),
                    _turn_for("judge", ["codex1", "codex2"], mention=False),
                    _turn_for("judge", ["codex1", "codex2"]),
                ],
            ),
        }
    )
    engine = DebateEngine(storage, registry)

    async def scenario():
        state = await engine.create_debate(
            "Dynamic Agents Repair",
            "Choose one stack.",
            agent_configs=[
                DebateAgentConfig(name="codex1", provider=ProviderKind.CODEX, model="gpt-5.4"),
                DebateAgentConfig(name="codex2", provider=ProviderKind.CODEX, model="gpt-5.4-mini"),
                DebateAgentConfig(
                    name="judge",
                    provider=ProviderKind.CLAUDE,
                    model="claude-sonnet-4-6",
                    write_thesis=False,
                    debate_style="neutral",
                ),
            ],
        )
        state = await engine.start_theses(state.id)
        state = await engine.share_theses(state.id)
        state = await engine.run_turn(state.id, "judge")

        assert state.rounds[-1].agent == "judge"
        assert "<@codex1>" in state.rounds[-1].discussion
        assert any(event.type == "agent_output_repair_requested" for event in storage.read_events(state.id))

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(scenario())
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def test_failed_turn_does_not_advance_turn_anchor(tmp_path):
    storage = DebateStorage(tmp_path)
    registry = AgentRegistry(
        {
            AgentId.CODEX: FakeLLM("codex", [_thesis("codex"), _ack("codex"), _turn("codex")]),
            AgentId.GEMINI: FakeLLM(
                "gemini",
                [
                    _thesis("gemini"),
                    _ack("gemini"),
                    _turn_for("gemini", ["codex"], mention=False),
                    _turn_for("gemini", ["codex"], mention=False),
                ],
            ),
            AgentId.CLAUDE: FakeLLM("claude", [_thesis("claude"), _ack("claude")]),
        }
    )
    engine = DebateEngine(storage, registry)

    async def scenario():
        state = await engine.create_debate("Failed Turn Anchor Test", "Choose one stack.")
        state = await engine.start_theses(state.id)
        state = await engine.share_theses(state.id)
        state = await engine.run_turn(state.id, AgentId.CODEX)

        try:
            await engine.run_turn(state.id, AgentId.GEMINI)
        except ValueError:
            pass
        else:
            raise AssertionError("gemini turn should fail after invalid repair")

        failed_state = storage.read_state(state.id)
        assert failed_state.next_agent == AgentId.CODEX
        assert engine._next_agent(failed_state) == AgentId.GEMINI

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(scenario())
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def test_run_turn_rejects_while_agent_is_running(tmp_path):
    storage = DebateStorage(tmp_path)
    registry = AgentRegistry(
        {
            AgentId.CODEX: FakeLLM("codex", [_thesis("codex"), _ack("codex"), _turn("codex")]),
            AgentId.GEMINI: FakeLLM("gemini", [_thesis("gemini"), _ack("gemini")]),
            AgentId.CLAUDE: FakeLLM("claude", [_thesis("claude"), _ack("claude")]),
        }
    )
    engine = DebateEngine(storage, registry)

    async def scenario():
        state = await engine.create_debate("Running Guard Test", "Choose one stack.")
        state = await engine.start_theses(state.id)
        state = await engine.share_theses(state.id)
        state.agents[AgentId.CODEX].status = AgentStatus.RUNNING
        storage.write_state(state)

        try:
            await engine.run_turn(state.id, AgentId.GEMINI)
        except RuntimeError as exc:
            assert "cannot run debate turn while running: codex" in str(exc)
        else:
            raise AssertionError("run_turn should reject while an agent is running")

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(scenario())
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def test_agent_colors_are_persisted_and_backfilled(tmp_path):
    storage = DebateStorage(tmp_path)
    engine = DebateEngine(storage, AgentRegistry())

    async def scenario():
        state = await engine.create_debate(
            "Color Persistence",
            "Choose one stack.",
            agent_configs=[
                DebateAgentConfig(name="codex1", provider=ProviderKind.CODEX, color="rose"),
                DebateAgentConfig(name="gemini1", provider=ProviderKind.GEMINI),
            ],
        )
        assert state.agents["codex1"].color == "rose"
        assert state.agents["gemini1"].color == "joseon"

        saved = storage.read_state(state.id)
        assert saved.agents["codex1"].color == "rose"
        assert saved.agents["gemini1"].color == "joseon"
        assert '"color": "rose"' in (tmp_path / state.id / "state.json").read_text()
        assert '"color": "joseon"' in (tmp_path / state.id / "state.json").read_text()

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(scenario())
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def test_tool_enabled_thesis_records_shared_evidence(tmp_path):
    storage = DebateStorage(tmp_path)
    registry = AgentRegistry(
        {
            AgentId.CODEX: FakeLLM("codex", [_thesis_with_evidence("codex"), _thesis_with_evidence("codex")]),
            AgentId.GEMINI: FakeLLM("gemini", [_thesis_with_evidence("gemini")]),
            AgentId.CLAUDE: FakeLLM("claude", [_thesis_with_evidence("claude")]),
        }
    )
    engine = DebateEngine(storage, registry)

    async def scenario():
        state = await engine.create_debate(
            "Evidence Test",
            "Choose one stack.",
            allow_file_read=True,
        )
        state = await engine.start_theses(state.id)
        assert len(state.shared_evidence) == 3
        assert state.theses[AgentId.CODEX].evidence_refs
        artifact = storage.read_artifact(state.id, "evidence/evidence.json")
        assert "pyproject.toml" in artifact

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(scenario())
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def test_text_only_thesis_rejects_local_file_evidence(tmp_path):
    storage = DebateStorage(tmp_path)
    registry = AgentRegistry(
        {
            AgentId.CODEX: FakeLLM(
                "codex",
                [_thesis_with_evidence("codex"), _thesis_with_evidence("codex")],
            ),
            AgentId.GEMINI: FakeLLM("gemini", [_thesis("gemini")]),
            AgentId.CLAUDE: FakeLLM("claude", [_thesis("claude")]),
        }
    )
    engine = DebateEngine(storage, registry)

    async def scenario():
        state = await engine.create_debate(
            "No Local Evidence Test",
            "Discuss policy.",
            allow_file_read=False,
            allow_web_evidence=True,
        )
        state = await engine.start_theses(state.id)
        assert state.phase == DebatePhase.FAILED
        assert "local evidence while file access is disabled" in state.agents[AgentId.CODEX].last_error

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(scenario())
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def test_web_evidence_is_recorded_in_shared_ledger(tmp_path):
    storage = DebateStorage(tmp_path)
    registry = AgentRegistry(
        {
            AgentId.CODEX: FakeLLM("codex", [_thesis_with_web_evidence("codex")]),
            AgentId.GEMINI: FakeLLM("gemini", [_thesis_with_web_evidence("gemini")]),
            AgentId.CLAUDE: FakeLLM("claude", [_thesis_with_web_evidence("claude")]),
        }
    )
    engine = DebateEngine(storage, registry)

    async def scenario():
        state = await engine.create_debate(
            "Web Evidence Test",
            "Choose one stack.",
            allow_file_read=True,
        )
        state = await engine.start_theses(state.id)
        assert state.shared_evidence[0].kind == "web_ref"
        assert state.shared_evidence[0].url == "https://example.com/docs"
        artifact = storage.read_artifact(state.id, "evidence/evidence.json")
        assert "Example Docs" in artifact

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(scenario())
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def test_same_payload_evidence_refs_are_accepted(tmp_path):
    storage = DebateStorage(tmp_path)
    registry = AgentRegistry(
        {
            AgentId.CODEX: FakeLLM("codex", [_thesis_with_web_evidence_ref("codex")]),
            AgentId.GEMINI: FakeLLM("gemini", [_thesis("gemini")]),
            AgentId.CLAUDE: FakeLLM("claude", [_thesis("claude")]),
        }
    )
    engine = DebateEngine(storage, registry)

    async def scenario():
        state = await engine.create_debate(
            "Same Payload Evidence Ref Test",
            "Choose one stack.",
            allow_web_evidence=True,
        )
        state = await engine.start_theses(state.id)
        assert state.phase == DebatePhase.THESES_READY
        assert state.theses[AgentId.CODEX].evidence_refs == ["ev-001-codex"]

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(scenario())
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def test_unknown_evidence_refs_are_ignored_without_failing_turn(tmp_path):
    storage = DebateStorage(tmp_path)
    registry = AgentRegistry(
        {
            AgentId.CODEX: FakeLLM("codex", [_thesis("codex"), _ack("codex"), _turn_with_refs("codex", ["ev-999-obama"])]),
            AgentId.GEMINI: FakeLLM("gemini", [_thesis("gemini"), _ack("gemini")]),
            AgentId.CLAUDE: FakeLLM("claude", [_thesis("claude"), _ack("claude")]),
        }
    )
    engine = DebateEngine(storage, registry)

    async def scenario():
        state = await engine.create_debate("Unknown Evidence Ref Test", "Choose one stack.")
        state = await engine.start_theses(state.id)
        state = await engine.share_theses(state.id)
        state = await engine.run_turn(state.id, AgentId.CODEX)

        assert state.rounds[-1].evidence_refs == []
        assert state.agents[AgentId.CODEX].status == AgentStatus.DONE
        ignored_events = [
            event
            for event in storage.read_events(state.id)
            if event.type == "evidence_refs_ignored"
        ]
        assert ignored_events[-1].payload["unknown_refs"] == ["ev-999-obama"]

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(scenario())
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def _thesis(agent: str, decision: str = "Use FastAPI with React") -> str:
    return json.dumps(
        {
            "type": "thesis",
            "agent": agent,
            "position": "Build the app with FastAPI and React.",
            "decision": decision,
            "action_plan": ["Create backend models", "Create API", "Connect frontend"],
            "risks": ["Contract drift"],
            "success_criteria": ["Backend starts", "Frontend builds"],
        }
    )


def _thesis_with_evidence(agent: str) -> str:
    payload = json.loads(_thesis(agent))
    payload["evidence"] = [
        {
            "kind": "file_ref",
            "summary": "Project metadata shows the framework dependency.",
            "path": "pyproject.toml",
            "line_start": 1,
            "line_end": 5,
            "excerpt": "[project]",
        }
    ]
    payload["evidence_refs"] = []
    return json.dumps(payload)


def _thesis_with_web_evidence(agent: str) -> str:
    payload = json.loads(_thesis(agent))
    payload["evidence"] = [
        {
            "kind": "web_ref",
            "summary": "Documentation search confirms the API behavior.",
            "url": "https://example.com/docs",
            "title": "Example Docs",
            "query": "example docs api behavior",
            "snippet": "The API returns JSON.",
        }
    ]
    payload["evidence_refs"] = []
    return json.dumps(payload)


def _thesis_with_web_evidence_ref(agent: str) -> str:
    payload = json.loads(_thesis_with_web_evidence(agent))
    payload["evidence_refs"] = [f"ev-001-{agent}"]
    return json.dumps(payload)


def _turn(
    agent: str,
    discussion: str = "I like what <@gemini> said about the shared contract; it keeps the agents aligned.",
) -> str:
    return json.dumps(
        {
            "type": "debate_turn",
            "agent": agent,
            "reply_to": ["gemini", "claude"],
            "discussion": discussion,
            "agreements": ["Use the shared contract"],
            "disagreements": [],
            "updated_position": "Keep the backend contract stable.",
            "proposed_next_action": "Implement fake-agent integration tests.",
            "consensus_action": None,
            "consensus_signal": None,
        }
    )


def _turn_with_refs(agent: str, refs: list[str]) -> str:
    payload = json.loads(_turn(agent))
    payload["evidence_refs"] = refs
    return json.dumps(payload)


def _turn_for(agent: str, reply_to: list[str], mention: bool = True) -> str:
    discussion = (
        f"I like what <@{reply_to[0]}> said about deterministic implementation; it narrows the decision."
        if mention
        else "I like that deterministic implementation narrows the decision."
    )
    return json.dumps(
        {
            "type": "debate_turn",
            "agent": agent,
            "reply_to": reply_to,
            "discussion": discussion,
            "agreements": [f"I agree with {reply_to[0]} on deterministic implementation because it improves execution."],
            "disagreements": [],
            "updated_position": "Keep the decision deterministic and evidence-based.",
            "proposed_next_action": "Ask the thesis writers to reconcile the implementation sequence.",
            "consensus_action": None,
            "consensus_signal": None,
        }
    )


def _ack(agent: str) -> str:
    return json.dumps({"type": "ack", "agent": agent, "ack": True})


def _consensus_turn(
    agent: str,
    action: str,
    proposal_id: str | None = None,
    reason: str | None = None,
) -> str:
    payload = {
        "type": "debate_turn",
        "agent": agent,
        "reply_to": ["codex" if agent != "codex" else "gemini"],
        "discussion": (
            "I like what <@gemini> said about stable contracts; it gives the final writer a clear target."
            if agent == "codex"
            else "I like what <@codex> said about stable contracts; it gives the final writer a clear target."
        ),
        "agreements": ["I agree with Codex on stable contracts because it reduces drift."],
        "disagreements": [],
        "updated_position": "Use the consensus package with Codex as final writer.",
        "proposed_next_action": "Move to final drafting after all agents accept.",
        "consensus_signal": None,
    }
    if action == "propose":
        payload["consensus_action"] = {
            "type": "consensus_action",
            "agent": agent,
            "action": "propose",
            "final_writer": "codex",
            "consensus_summary": "Use FastAPI with React and keep the backend contract stable.",
        }
    else:
        payload["consensus_action"] = {
            "type": "consensus_action",
            "agent": agent,
            "action": action,
            "proposal_id": proposal_id,
        }
        if reason:
            payload["consensus_action"]["reason"] = reason
    return json.dumps(payload)


def _final_markdown(decision: str = "Use FastAPI with React.") -> str:
    return f"""# Final Engineering Thesis

## Decision
{decision}

## Rationale
The agreed approach keeps the backend contract stable.

## Implementation Plan
- Implement the agreed API shape.

## Risks
- Keep migration scope controlled.

## Acceptance Criteria
- The final implementation matches consensus."""


def _final_review(agent: str, verdict: str = "accept") -> str:
    return json.dumps(
        {
            "type": "final_review",
            "agent": agent,
            "verdict": verdict,
            "reason": "The draft matches the consensus.",
            "required_changes": [] if verdict == "accept" else ["Clarify the implementation plan."],
        }
    )
