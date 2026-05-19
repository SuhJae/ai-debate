import type {
  DebateChatAgent,
  DebateChatMessage,
  DebateSystemKind,
  DebateToolEvent,
  DebateToolStatus
} from '~/types/debate-chat'
import type { DebateState, DebateTurnRecord, EvidenceRecord, ThesisRecord, UserMessageRecord } from '~/types/debate-state'
import { agentColorOptions } from '~/utils/debate-config'

export function debateAgentsFromState(state: DebateState): DebateChatAgent[] {
  return orderedAgentIds(state).map((agentId) => {
    const agent = state.agents[agentId]!
    return {
      id: agentId,
      name: agent.display_name || agentId,
      provider: agent.provider,
      color: stableAgentColor(state, agentId),
      debateStyle: agent.debate_style,
      technicalPreference: agent.technical_preference
    }
  })
}

export function debateMessagesFromState(
  state: DebateState,
  options: { includePrompt?: boolean, includeTheses?: boolean } = {}
): DebateChatMessage[] {
  const includePrompt = options.includePrompt ?? false
  const includeTheses = options.includeTheses ?? true
  const messages: DebateChatMessage[] = []

  if (includePrompt) {
    messages.push({
      id: `${state.id}-prompt`,
      role: 'user',
      content: state.user_prompt,
      createdAt: formatTime(state.created_at)
    })
  }

  const evidenceById = new Map(state.shared_evidence.map(evidence => [evidence.id, evidence]))
  const citationTools = debateCitationTools(state)
  const proposalById = new Map(state.consensus_proposals.map(proposal => [proposal.id, proposal]))
  const sharedThesisAgentIds = orderedThesisAgents(state)
  const userMessages = groupUserMessagesByRound(state.user_messages ?? [])

  if (includeTheses) {
    for (const agentId of sharedThesisAgentIds) {
      const thesis = state.theses[agentId]
      if (!thesis) continue

      messages.push({
        id: `${state.id}-thesis-${agentId}`,
        role: 'agent',
        agentId,
        content: thesisToMarkdown(thesis),
        tools: [
          artifactTool(thesis.artifact_path, 'Initial thesis artifact'),
          ...evidenceTools(thesis.evidence_refs, evidenceById)
        ],
        citations: citationTools,
        createdAt: ''
      })
    }
  } else if (thesesHaveBeenShared(state) && sharedThesisAgentIds.length) {
    messages.push({
      id: `${state.id}-theses-shared`,
      role: 'notice',
      content: thesesSharedToMarkdown(state, sharedThesisAgentIds),
      createdAt: ''
    })
  }

  messages.push(...userMessagesAfterRound(userMessages, 0))

  for (const round of state.rounds) {
    messages.push({
      id: `${state.id}-round-${round.index}-${round.agent}`,
      role: 'agent',
      agentId: round.agent,
      content: roundToMarkdown(round),
      tools: evidenceTools(round.evidence_refs, evidenceById),
      citations: citationTools,
      createdAt: ''
    })

    const consensusNotice = roundConsensusToNotice(round, proposalById)
    if (consensusNotice) {
      messages.push({
        id: `${state.id}-round-${round.index}-${round.agent}-consensus`,
        role: 'system',
        agentId: round.agent,
        content: consensusNotice.content,
        systemKind: consensusNotice.kind,
        systemTitle: consensusNotice.title,
        consensusProposalId: consensusNotice.proposalId,
        citations: citationTools,
        createdAt: ''
      })
    }

    messages.push(...userMessagesAfterRound(userMessages, round.index))
  }

  for (const mcpServer of state.mcp_registry) {
    messages.push({
      id: `${state.id}-mcp-${mcpServer.id}`,
      role: 'notice',
      content: sharedSourceToMarkdown(mcpServer),
      createdAt: formatTime(mcpServer.created_at)
    })
  }

  if (state.consensus) {
    messages.push({
      id: `${state.id}-consensus-final`,
      role: 'system',
      content: [
        `${mention(state.consensus.final_writer)} will write the final conclusion.`,
        state.consensus.consensus_summary
      ].filter(Boolean).join('\n\n'),
      systemKind: 'consensus_reached',
      systemTitle: 'Consensus reached',
      citations: citationTools,
      createdAt: formatTime(state.updated_at)
    })
  }

  return messages
}

function groupUserMessagesByRound(messages: UserMessageRecord[]) {
  const grouped = new Map<number, UserMessageRecord[]>()
  for (const message of messages) {
    const afterRound = Number.isFinite(message.after_round) ? message.after_round : 0
    const bucket = grouped.get(afterRound) ?? []
    bucket.push(message)
    grouped.set(afterRound, bucket)
  }
  return grouped
}

function userMessagesAfterRound(grouped: Map<number, UserMessageRecord[]>, roundIndex: number): DebateChatMessage[] {
  return (grouped.get(roundIndex) ?? []).map(message => ({
    id: message.id,
    role: 'user',
    content: message.content,
    createdAt: formatTime(message.created_at)
  }))
}

function orderedThesisAgents(state: DebateState) {
  const ordered = orderedAgentIds(state).filter(agentId => state.theses[agentId])
  const remaining = Object.keys(state.theses).filter(agentId => !ordered.includes(agentId))
  return [...ordered, ...remaining]
}

function orderedAgentIds(state: DebateState) {
  return [
    ...state.turn_order.filter(agentId => state.agents[agentId]),
    ...Object.keys(state.agents).filter(agentId => !state.turn_order.includes(agentId))
  ]
}

function stableAgentColor(state: DebateState, agentId: string) {
  const configuredColor = state.agents[agentId]?.color
  if (configuredColor) return configuredColor
  const rosterIndex = Object.keys(state.agents).indexOf(agentId)
  const colorIndex = rosterIndex === -1 ? 0 : rosterIndex
  return agentColorOptions[colorIndex % agentColorOptions.length]?.value ?? 'celadon'
}

export function thesisToMarkdown(thesis: ThesisRecord) {
  return [
    `## Thesis: ${thesis.decision}`,
    thesis.position,
    listSection('Action Plan', thesis.action_plan),
    listSection('Risks', thesis.risks),
    listSection('Success Criteria', thesis.success_criteria)
  ].filter(Boolean).join('\n\n')
}

function roundToMarkdown(round: DebateTurnRecord) {
  return round.discussion || 'No discussion text was recorded for this turn.'
}

function listSection(title: string, items: string[]) {
  if (!items.length) return ''
  return [`### ${title}`, ...items.map(item => `- ${item}`)].join('\n')
}

function thesesHaveBeenShared(state: DebateState) {
  return [
    'debating',
    'paused',
    'consensus_reached',
    'drafting_final',
    'reviewing_final',
    'revising_final',
    'accepted'
  ].includes(state.phase)
}

function thesesSharedToMarkdown(state: DebateState, agentIds: string[]) {
  const lines = [
    '**Initial theses shared**',
    'The agents now have each thesis in context for the discussion.',
    ...agentIds.map((agentId) => {
      const thesis = state.theses[agentId]
      const agentName = state.agents[agentId]?.display_name || agentId
      return thesis
        ? `- ${mention(agentId)} (${agentName}): ${thesis.decision}`
        : `- ${mention(agentId)} (${agentName})`
    })
  ]

  return lines.join('\n')
}

export function evidenceTools(refs: string[], evidenceById: Map<string, EvidenceRecord>) {
  return refs
    .map(ref => evidenceById.get(ref))
    .filter((evidence): evidence is EvidenceRecord => Boolean(evidence))
    .map(evidenceToTool)
}

export function evidenceLedgerTools(evidence: EvidenceRecord[]) {
  return evidence.map(evidenceToTool)
}

export function debateCitationTools(state: DebateState) {
  return [
    ...state.shared_evidence.map(evidenceToTool),
    ...state.consensus_proposals.map(consensusProposalToTool)
  ]
}

function consensusProposalToTool(
  proposal: DebateState['consensus_proposals'][number]
): DebateToolEvent {
  const rejectedBy = Object.keys(proposal.rejected_by)
  const status: DebateToolStatus = proposal.status === 'rejected' || rejectedBy.length
    ? 'failed'
    : proposal.status === 'active'
      ? 'pending'
      : 'succeeded'

  return {
    id: `tool-${proposal.id}`,
    kind: 'consensus',
    status,
    title: proposal.id,
    description: proposal.consensus_summary,
    actor: proposal.proposer,
    targetAgent: proposal.final_writer,
    action: proposal.status === 'withdrawn'
      ? 'withdraw'
      : status === 'failed'
        ? 'reject'
        : 'propose',
    proposalId: proposal.id
  }
}

function evidenceToTool(evidence: EvidenceRecord): DebateToolEvent {
  if (evidence.kind === 'command_result') {
    return {
      id: `tool-${evidence.id}`,
      kind: 'terminal_probe',
      status: evidence.exit_code === 0 ? 'succeeded' : 'failed',
      title: evidence.summary,
      actor: evidence.agent,
      command: evidence.command ?? undefined,
      exitCode: evidence.exit_code ?? undefined,
      output: evidence.output_summary ?? undefined,
      description: evidence.cwd ? `cwd: ${evidence.cwd}` : undefined
    }
  }

  if (evidence.kind === 'web_ref') {
    return {
      id: `tool-${evidence.id}`,
      kind: 'web_evidence',
      status: 'succeeded',
      title: evidence.title ?? evidence.summary,
      actor: evidence.agent,
      url: evidence.url ?? undefined,
      query: evidence.query ?? undefined,
      description: evidence.snippet ?? evidence.summary
    }
  }

  if (evidence.kind === 'mcp_ref') {
    return {
      id: `tool-${evidence.id}`,
      kind: 'mcp_proposal',
      status: 'succeeded',
      title: evidence.summary,
      actor: evidence.agent,
      proposalId: [evidence.mcp_server, evidence.mcp_tool].filter(Boolean).join('.') || evidence.id,
      description: evidence.excerpt ?? undefined
    }
  }

  return {
    id: `tool-${evidence.id}`,
    kind: 'file_evidence',
    status: 'succeeded',
    title: evidence.summary,
    actor: evidence.agent,
    path: evidence.path ?? undefined,
    lineStart: evidence.line_start ?? undefined,
    lineEnd: evidence.line_end ?? undefined,
    output: evidence.excerpt ?? undefined
  }
}

type ConsensusNotice = {
  kind: DebateSystemKind
  title: string
  content: string
  proposalId?: string
}

function roundConsensusToNotice(
  round: DebateTurnRecord,
  proposalById: Map<string, DebateState['consensus_proposals'][number]>
) {
  const action = round.consensus_action
  const generatedProposalId = generatedConsensusProposalId(round)
  if (action) return consensusActionToNotice(round.agent, action, proposalById, generatedProposalId)

  const signal = round.consensus_signal
  if (signal?.agreed) {
    return {
      kind: 'consensus_proposed',
      title: 'Consensus proposed',
      proposalId: generatedProposalId,
      content: [
        `${mention(round.agent)} proposed ${mention(String(signal.final_writer ?? ''))} as final writer.`,
        typeof signal.consensus_summary === 'string' ? signal.consensus_summary : ''
      ].filter(Boolean).join('\n\n')
    } satisfies ConsensusNotice
  }

  return null
}

function consensusActionToNotice(
  actor: string,
  action: Record<string, unknown>,
  proposalById: Map<string, DebateState['consensus_proposals'][number]>,
  generatedProposalId: string
): ConsensusNotice | null {
  const actionName = String(action.action ?? '')
  const proposalId = typeof action.proposal_id === 'string' ? action.proposal_id : ''
  const proposal = proposalId ? proposalById.get(proposalId) : undefined

  if (actionName === 'propose') {
    return {
      kind: 'consensus_proposed',
      title: 'Consensus proposed',
      proposalId: generatedProposalId,
      content: [
        `${mention(actor)} proposed ${mention(String(action.final_writer ?? ''))} as final writer.`,
        typeof action.consensus_summary === 'string' ? action.consensus_summary : ''
      ].filter(Boolean).join('\n\n')
    }
  }

  if (actionName === 'accept') {
    return {
      kind: 'consensus_accepted',
      title: 'Consensus accepted',
      proposalId,
      content: `${mention(actor)} accepted${proposal ? ` ${mention(proposal.final_writer)} as final writer` : ' the proposal'}.`
    }
  }

  if (actionName === 'reject') {
    return {
      kind: 'consensus_rejected',
      title: 'Consensus rejected',
      proposalId,
      content: [
        `${mention(actor)} rejected the proposal.`,
        typeof action.reason === 'string' ? action.reason : ''
      ].filter(Boolean).join('\n\n')
    }
  }

  if (actionName === 'withdraw') {
    return {
      kind: 'consensus_withdrawn',
      title: 'Consensus withdrawn',
      proposalId,
      content: `${mention(actor)} withdrew ${proposal?.proposer === actor ? 'the proposal' : 'their vote'}.`
    }
  }

  return null
}

function generatedConsensusProposalId(round: DebateTurnRecord) {
  return `consensus-${String(round.index).padStart(3, '0')}-${round.agent}`
}

function sharedSourceToMarkdown(source: DebateState['mcp_registry'][number]) {
  const lines = [
    `**Shared source ${sourceStatusLabel(source.status)}**`,
    `${mention(source.proposed_by)} shared **${source.name}**.`,
    source.description
  ]

  if (source.transport === 'stdio') {
    lines.push(`Command: \`${[source.command_or_url, ...source.args].join(' ')}\``)
  } else if (source.command_or_url) {
    lines.push(`URL: ${source.command_or_url}`)
  }

  return lines.filter(Boolean).join('\n\n')
}

function mention(agentId?: string) {
  return agentId ? `<@${agentId}>` : 'an agent'
}

function sourceStatusLabel(status: string) {
  if (status === 'approved') return 'approved'
  if (status === 'rejected') return 'rejected'
  return 'pending'
}

export function artifactTool(path: string, title: string): DebateToolEvent {
  return {
    id: `tool-artifact-${path}`,
    kind: 'file_evidence',
    status: 'succeeded',
    title,
    path,
    description: 'Markdown artifact generated in the debate workspace.'
  }
}

function formatTime(value: string) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return new Intl.DateTimeFormat(undefined, {
    hour: '2-digit',
    minute: '2-digit'
  }).format(date)
}
