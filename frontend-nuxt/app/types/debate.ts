export interface ProviderModelInfo {
  id: string
  label: string
  default: boolean
}

export interface ProviderInfo {
  id: string
  label: string
  cli: string
  default_model: string
  models: ProviderModelInfo[]
}

export interface LlmProvidersResponse {
  providers: Record<string, ProviderInfo>
}

export interface DebateDiscussion {
  id: string
  title: string
  phase: string
  created_at: string
  updated_at: string
  agent_count: number
  turn_count: number
  has_consensus: boolean
}

export interface DebateDiscussionSelectItem {
  label: string
  value: string
  description: string
}

export interface DebateAgentDraft {
  id: string
  mentionName: string
  displayName: string
  provider: string
  model: string
  color: string
  writeThesis: boolean
  debateStyle: string
  technicalPreference: string
  note: string
}

export interface DebateAgentSetup extends DebateAgentDraft {
  status: string
  thesisDecision: string
  thesisSummary: string
  consensusStatus: string
  latestDiscussion: string
}

export interface AgentColorOption {
  value: string
  label: string
  swatchClass: string
  softClass: string
  textClass: string
  borderClass: string
  ringClass: string
}
