import type { DebateAgentSetup } from '~/types/debate'
import type { DebateState } from '~/types/debate-state'
import { agentColorOptions } from '~/utils/debate-config'
import { createDebateAgentSetup } from './useDebateAgents'

export function getDefaultDebateWorkingDirectory() {
  const config = useRuntimeConfig()
  return config.public.aiDebateDefaultWorkspace || ''
}

export function useDebateDraft() {
  return {
    title: useState<string>('debate-draft-title', () => ''),
    topic: useState<string>('debate-draft-topic', () => ''),
    workingDirectory: useState<string>('debate-draft-working-directory', getDefaultDebateWorkingDirectory),
    allowFileRead: useState<boolean>('debate-draft-allow-file-read', () => true),
    allowProbeCommands: useState<boolean>('debate-draft-allow-probe-commands', () => true),
    allowWebEvidence: useState<boolean>('debate-draft-allow-web-evidence', () => true)
  }
}

export function resetDebateDraftState() {
  const draft = useDebateDraft()
  draft.title.value = ''
  draft.topic.value = ''
  draft.workingDirectory.value = getDefaultDebateWorkingDirectory()
  draft.allowFileRead.value = true
  draft.allowProbeCommands.value = true
  draft.allowWebEvidence.value = true
}

export function applyDebateDraftFromState(
  state: DebateState,
  options: { titleSuffix?: string } = {}
) {
  const draft = useDebateDraft()
  const permissions = debateDraftPermissionsFromState(state)

  draft.title.value = options.titleSuffix
    ? `${state.title} ${options.titleSuffix}`.trim()
    : state.title
  draft.topic.value = state.user_prompt
  draft.workingDirectory.value = state.working_directory || getDefaultDebateWorkingDirectory()
  draft.allowFileRead.value = permissions.allowFileRead
  draft.allowProbeCommands.value = permissions.allowProbeCommands
  draft.allowWebEvidence.value = permissions.allowWebEvidence
}

export function debateDraftPermissionsFromState(state: DebateState) {
  const toolMode = state.tool_mode
  const allowFileRead = ['read_only', 'probe', 'edit', 'full'].includes(toolMode)
  return {
    allowFileRead,
    allowProbeCommands: ['probe', 'edit', 'full'].includes(toolMode),
    allowWebEvidence: state.allow_web_evidence
  }
}

export function debateAgentDraftsFromState(state: DebateState): DebateAgentSetup[] {
  const orderedAgentIds = [
    ...state.turn_order.filter(agentId => state.agents[agentId]),
    ...Object.keys(state.agents).filter(agentId => !state.turn_order.includes(agentId))
  ]

  return orderedAgentIds.map((agentId, index) => {
    const agent = state.agents[agentId]!
    return createDebateAgentSetup({
      id: agentId,
      displayName: agent.display_name || agentId,
      provider: agent.provider,
      model: agent.model,
      color: agent.color || agentColorOptions[index % agentColorOptions.length]!.value,
      writeThesis: agent.write_thesis,
      debateStyle: agent.debate_style,
      technicalPreference: agent.technical_preference,
      note: agent.additional_note
    })
  })
}
