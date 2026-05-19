export interface AgentState {
  provider: string
  display_name: string
  model: string
  color?: string | null
  write_thesis: boolean
  debate_style: string
  technical_preference: string
  additional_note: string
  session_id?: string | null
  status: string
  last_error?: string | null
}

export interface EvidenceRecord {
  id: string
  agent: string
  kind: 'file_ref' | 'command_result' | 'web_ref' | 'mcp_ref' | 'note'
  summary: string
  source_type: string
  source_id: string
  path?: string | null
  line_start?: number | null
  line_end?: number | null
  excerpt?: string | null
  command?: string | null
  cwd?: string | null
  exit_code?: number | null
  output_summary?: string | null
  url?: string | null
  title?: string | null
  query?: string | null
  snippet?: string | null
  retrieved_at?: string | null
  mcp_server?: string | null
  mcp_tool?: string | null
  created_at: string
}

export interface ThesisRecord {
  agent: string
  position: string
  decision: string
  action_plan: string[]
  risks: string[]
  success_criteria: string[]
  evidence_refs: string[]
  artifact_path: string
}

export interface DebateTurnRecord {
  index: number
  agent: string
  discussion: string
  agreements: string[]
  disagreements: string[]
  updated_position: string
  proposed_next_action: string
  evidence_refs: string[]
  consensus_action?: Record<string, unknown> | null
  consensus_signal?: Record<string, unknown> | null
  artifact_path: string
}

export interface ConsensusProposalState {
  id: string
  proposer: string
  final_writer: string
  consensus_summary: string
  status: string
  accepted_by: string[]
  rejected_by: Record<string, string>
  created_at: string
  updated_at: string
}

export interface ConsensusState {
  final_writer: string
  consensus_summary: string
  agreed_by: string[]
  forced_by_user: boolean
}

export interface FinalDraftState {
  draft_version: number
  draft_path: string
  created_at: string
  status: string
  accepted_by: string[]
  reviews: Record<string, Record<string, unknown>>
}

export interface FinalDocumentState {
  draft_version: number
  draft_path?: string | null
  final_path?: string | null
  accepted_by: string[]
  drafts: FinalDraftState[]
}

export interface UserMessageRecord {
  id: string
  content: string
  created_at: string
  after_round: number
}

export interface McpServerState {
  id: string
  name: string
  description: string
  transport: string
  command_or_url: string
  args: string[]
  env: Record<string, string>
  headers: Record<string, string>
  trusted: boolean
  proposed_by: string
  status: string
  created_at: string
}

export interface GlobalMcpServer {
  id: string
  name: string
  description: string
  transport: 'stdio' | 'http' | 'sse'
  command_or_url: string
  args: string[]
  env: Record<string, string>
  headers: Record<string, string>
  enabled: boolean
  trusted: boolean
  created_at: string
  updated_at: string
}

export interface DebateState {
  id: string
  title: string
  user_prompt: string
  working_directory?: string | null
  phase: string
  mode: string
  created_at: string
  updated_at: string
  tool_mode: string
  allow_web_evidence: boolean
  agents: Record<string, AgentState>
  turn_order: string[]
  next_agent?: string | null
  auto_mode: boolean
  pause_after_this: boolean
  send_after_this?: string | null
  user_messages: UserMessageRecord[]
  theses: Record<string, ThesisRecord>
  rounds: DebateTurnRecord[]
  shared_evidence: EvidenceRecord[]
  consensus_proposals: ConsensusProposalState[]
  consensus?: ConsensusState | null
  final_document?: FinalDocumentState | null
  reviews: Record<string, Record<string, unknown>>
  mcp_registry: McpServerState[]
}
