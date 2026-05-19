"""Registry mapping debate agents to LLM provider wrappers."""

from llms import AgentSession, Claude, Codex, Gemini, LLM, MCPServerConfig, ToolMode
from llms.base import NO_WORKSPACE

from app.models.agent import AGENT_COLOR_SEQUENCE, AgentState, DebateAgentConfig, ProviderKind
from app.models.debate import DebateState


DEFAULT_MODELS: dict[ProviderKind, str] = {
    ProviderKind.CODEX: "gpt-5.4",
    ProviderKind.GEMINI: "gemini-2.5-pro",
    ProviderKind.CLAUDE: "claude-sonnet-4-6",
}

AVAILABLE_MODELS: dict[ProviderKind, list[str]] = {
    ProviderKind.CODEX: ["gpt-5.4", "gpt-5.4-mini", "gpt-5.3-codex", "gpt-5.3-codex-spark"],
    ProviderKind.GEMINI: ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash"],
    ProviderKind.CLAUDE: ["claude-sonnet-4-6", "claude-haiku-4-5-20251001", "opus"],
}

PROVIDER_DISPLAY_NAMES: dict[ProviderKind, str] = {
    ProviderKind.CODEX: "Codex",
    ProviderKind.GEMINI: "Gemini",
    ProviderKind.CLAUDE: "Claude",
}

PROVIDER_CLI_BINS: dict[ProviderKind, str] = {
    ProviderKind.CODEX: Codex.cli_bin,
    ProviderKind.GEMINI: Gemini.cli_bin,
    ProviderKind.CLAUDE: Claude.cli_bin,
}


class AgentRegistry:
    def __init__(self, agents: dict[str, LLM] | None = None) -> None:
        self._agents = {str(key): value for key, value in (agents or {}).items()}

    def get_agent(self, agent_id: str, state: DebateState | None = None) -> LLM:
        agent_name = str(agent_id)
        if agent_name in self._agents:
            agent = self._agents[agent_name]
            self._configure_workspace(agent, state)
            return agent
        if state is None:
            agent = self._build_provider(ProviderKind(agent_name), DEFAULT_MODELS[ProviderKind(agent_name)])
            self._configure_workspace(agent, state)
            return agent
        agent_state = state.agents[agent_name]
        agent = self._build_provider(agent_state.provider, agent_state.model)
        self._configure_workspace(agent, state)
        return agent

    def get_all_agents(self) -> dict[str, LLM]:
        return dict(self._agents)

    def default_agent_states(self) -> dict[str, AgentState]:
        configs = [
            DebateAgentConfig(
                name="codex",
                provider=ProviderKind.CODEX,
                display_name="Codex",
                color=AGENT_COLOR_SEQUENCE[0],
            ),
            DebateAgentConfig(
                name="gemini",
                provider=ProviderKind.GEMINI,
                display_name="Gemini",
                color=AGENT_COLOR_SEQUENCE[2],
            ),
            DebateAgentConfig(
                name="claude",
                provider=ProviderKind.CLAUDE,
                display_name="Claude",
                color=AGENT_COLOR_SEQUENCE[3],
            ),
        ]
        return {config.name: self.state_from_config(config) for config in configs}

    def state_from_config(self, config: DebateAgentConfig) -> AgentState:
        model = config.model or DEFAULT_MODELS[config.provider]
        return AgentState(
            provider=config.provider,
            display_name=config.display_name or config.name,
            model=model,
            color=config.color,
            write_thesis=config.write_thesis,
            debate_style=config.debate_style,
            technical_preference=config.technical_preference,
            additional_note=config.additional_note,
        )

    def make_session(
        self,
        state: DebateState,
        agent_id: str,
        tool_mode: ToolMode,
        mcp_servers: list[MCPServerConfig],
    ) -> AgentSession:
        agent_name = str(agent_id)
        agent_state = state.agents[agent_name]
        if not agent_state.session_id:
            raise RuntimeError(f"{agent_id} has no session id")
        return AgentSession(
            provider=agent_state.provider.value,
            session_id=agent_state.session_id,
            model=agent_state.model,
            tool_mode=tool_mode,
            mcp_servers=mcp_servers,
        )

    def update_session_id(
        self,
        state: DebateState,
        agent_id: str,
        session_id: str,
    ) -> DebateState:
        state.agents[str(agent_id)].session_id = session_id
        return state

    @staticmethod
    def _build_provider(provider: ProviderKind, model: str) -> LLM:
        if provider == ProviderKind.CODEX:
            return Codex(model=model)
        if provider == ProviderKind.GEMINI:
            return Gemini(model=model)
        if provider == ProviderKind.CLAUDE:
            return Claude(model=model)
        raise ValueError(f"unsupported provider: {provider}")

    @staticmethod
    def _configure_workspace(agent: LLM, state: DebateState | None) -> None:
        if state and state.tool_mode.value == ToolMode.TEXT_ONLY.value:
            agent.workspace = NO_WORKSPACE
            return
        agent.workspace = state.working_directory if state else None
