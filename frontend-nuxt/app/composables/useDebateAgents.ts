import type { DebateAgentSetup } from '~/types/debate'
import { makeAgent } from '~/utils/debate-config'

function makeAgentSetup(
  id: string,
  displayName: string,
  provider: string,
  color: string,
  technicalPreference: string,
  debateStyle: string,
  writeThesis: boolean,
  status: string,
  thesisDecision: string,
  thesisSummary: string,
  consensusStatus: string,
  latestDiscussion: string,
  note = ''
): DebateAgentSetup {
  return {
    ...makeAgent(
      id,
      displayName,
      provider,
      color,
      technicalPreference,
      debateStyle,
      writeThesis
    ),
    note,
    status,
    thesisDecision,
    thesisSummary,
    consensusStatus,
    latestDiscussion
  }
}

export function createDebateAgentSetup(
  agent: {
    id: string
    displayName: string
    provider: string
    model?: string
    color: string
    technicalPreference?: string
    debateStyle?: string
    writeThesis?: boolean
    note?: string
  }
): DebateAgentSetup {
  return {
    ...makeAgentSetup(
      agent.id,
      agent.displayName,
      agent.provider,
      agent.color,
      agent.technicalPreference ?? 'neutral',
      agent.debateStyle ?? 'normal',
      agent.writeThesis ?? true,
      'draft',
      'No thesis written yet.',
      'This agent has not joined the debate.',
      'No consensus action recorded.',
      'No discussion turns yet.',
      agent.note ?? ''
    ),
    model: agent.model ?? ''
  }
}

export function useDebateAgents() {
  return useState<DebateAgentSetup[]>('debate-agents', () => [
    makeAgentSetup(
      'codex1',
      'Codex Architect',
      'codex',
      'celadon',
      'conservative',
      'normal',
      true,
      'ready',
      'Use FastAPI with async SQLAlchemy for the service boundary.',
      'Prioritizes explicit async I/O, low framework overhead, and OpenAPI-first contracts while keeping migrations and persistence conventional.',
      'No active consensus proposal.',
      'Waiting for the first debate turn.'
    ),
    makeAgentSetup(
      'gemini1',
      'Gemini Analyst',
      'gemini',
      'brass',
      'innovative',
      'collaborative',
      true,
      'ready',
      'Prototype FastAPI first, then validate operational risk with load and migration tests.',
      'Supports Codex on FastAPI, but wants hard evidence from benchmark, dependency, and deployment checks before locking the choice.',
      'Leaning toward FastAPI; awaiting Claude review.',
      'Agrees with the async API direction and wants evidence on driver behavior.'
    ),
    makeAgentSetup(
      'judge',
      'Neutral Judge',
      'claude',
      'pine',
      'neutral',
      'neutral',
      false,
      'standby',
      'No initial thesis; evaluate claims for evidence quality and missing risks.',
      'Checks whether the chosen stack has clear failure modes, maintainable ownership, and a realistic migration path.',
      'Neutral reviewer; no acceptance recorded.',
      'Waiting to compare agent claims.',
      'Steer discussion toward evidence and unresolved tradeoffs.'
    )
  ])
}
