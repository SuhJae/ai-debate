export type DebateChatRole = 'agent' | 'user' | 'system' | 'notice'

export type DebateSystemKind
  = | 'consensus_proposed'
    | 'consensus_accepted'
    | 'consensus_rejected'
    | 'consensus_withdrawn'
    | 'consensus_reached'

export type DebateToolKind
  = | 'file_evidence'
    | 'terminal_probe'
    | 'web_evidence'
    | 'consensus'
    | 'mcp_proposal'

export type DebateToolStatus = 'running' | 'succeeded' | 'failed' | 'pending'

export interface DebateChatAgent {
  id: string
  name: string
  provider: string
  color: string
  debateStyle?: string
  technicalPreference?: string
}

export interface DebateToolEvent {
  id: string
  kind: DebateToolKind
  status: DebateToolStatus
  title: string
  description?: string
  actor?: string
  targetAgent?: string
  action?: 'propose' | 'accept' | 'reject' | 'withdraw'
  path?: string
  lineStart?: number
  lineEnd?: number
  command?: string
  exitCode?: number
  output?: string
  url?: string
  query?: string
  proposalId?: string
}

export interface DebateChatMessage {
  id: string
  role: DebateChatRole
  agentId?: string
  content: string
  createdAt?: string
  systemKind?: DebateSystemKind
  systemTitle?: string
  consensusProposalId?: string
  tools?: DebateToolEvent[]
  citations?: DebateToolEvent[]
  streamPreview?: boolean
}
