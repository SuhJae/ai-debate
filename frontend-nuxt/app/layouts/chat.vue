<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { DebateAgentSetup, DebateDiscussion, LlmProvidersResponse } from '~/types/debate'
import type { DebateState } from '~/types/debate-state'

type AgentDropPosition = 'before' | 'after'

type AgentSetup = DebateAgentSetup

const agentColorOptions = [
  {
    value: 'celadon',
    label: 'Celadon',
    swatchClass: 'bg-celadon-600 dark:bg-celadon-400',
    softClass: 'bg-celadon-50/80 dark:bg-celadon-950/45',
    textClass: 'text-celadon-700 dark:text-celadon-300',
    borderClass: 'border-celadon-500/70 dark:border-celadon-400/70',
    ringClass: 'ring-celadon-600/25 dark:ring-celadon-400/25'
  },
  {
    value: 'joseon',
    label: 'Joseon Red',
    swatchClass: 'bg-joseon-600 dark:bg-joseon-400',
    softClass: 'bg-joseon-50/80 dark:bg-joseon-950/45',
    textClass: 'text-joseon-700 dark:text-joseon-300',
    borderClass: 'border-joseon-500/70 dark:border-joseon-400/70',
    ringClass: 'ring-joseon-600/25 dark:ring-joseon-400/25'
  },
  {
    value: 'brass',
    label: 'Brass',
    swatchClass: 'bg-brass-600 dark:bg-brass-400',
    softClass: 'bg-brass-50/80 dark:bg-brass-950/45',
    textClass: 'text-brass-700 dark:text-brass-300',
    borderClass: 'border-brass-500/70 dark:border-brass-400/70',
    ringClass: 'ring-brass-600/25 dark:ring-brass-400/25'
  },
  {
    value: 'pine',
    label: 'Pine',
    swatchClass: 'bg-pine-600 dark:bg-pine-400',
    softClass: 'bg-pine-50/80 dark:bg-pine-950/45',
    textClass: 'text-pine-700 dark:text-pine-300',
    borderClass: 'border-pine-500/70 dark:border-pine-400/70',
    ringClass: 'ring-pine-600/25 dark:ring-pine-400/25'
  },
  {
    value: 'sky',
    label: 'Sky',
    swatchClass: 'bg-sky-600 dark:bg-sky-400',
    softClass: 'bg-sky-50/80 dark:bg-sky-950/45',
    textClass: 'text-sky-700 dark:text-sky-300',
    borderClass: 'border-sky-500/70 dark:border-sky-400/70',
    ringClass: 'ring-sky-600/25 dark:ring-sky-400/25'
  },
  {
    value: 'violet',
    label: 'Violet',
    swatchClass: 'bg-violet-600 dark:bg-violet-400',
    softClass: 'bg-violet-50/80 dark:bg-violet-950/45',
    textClass: 'text-violet-700 dark:text-violet-300',
    borderClass: 'border-violet-500/70 dark:border-violet-400/70',
    ringClass: 'ring-violet-600/25 dark:ring-violet-400/25'
  },
  {
    value: 'slate',
    label: 'Slate',
    swatchClass: 'bg-slate-600 dark:bg-slate-300',
    softClass: 'bg-slate-100/80 dark:bg-slate-900/60',
    textClass: 'text-slate-700 dark:text-slate-200',
    borderClass: 'border-slate-500/70 dark:border-slate-400/70',
    ringClass: 'ring-slate-600/25 dark:ring-slate-300/25'
  },
  {
    value: 'orange',
    label: 'Orange',
    swatchClass: 'bg-orange-600 dark:bg-orange-400',
    softClass: 'bg-orange-50/80 dark:bg-orange-950/45',
    textClass: 'text-orange-700 dark:text-orange-300',
    borderClass: 'border-orange-500/70 dark:border-orange-400/70',
    ringClass: 'ring-orange-600/25 dark:ring-orange-400/25'
  },
  {
    value: 'lime',
    label: 'Lime',
    swatchClass: 'bg-lime-600 dark:bg-lime-400',
    softClass: 'bg-lime-50/80 dark:bg-lime-950/45',
    textClass: 'text-lime-700 dark:text-lime-300',
    borderClass: 'border-lime-500/70 dark:border-lime-400/70',
    ringClass: 'ring-lime-600/25 dark:ring-lime-400/25'
  },
  {
    value: 'indigo',
    label: 'Indigo',
    swatchClass: 'bg-indigo-600 dark:bg-indigo-400',
    softClass: 'bg-indigo-50/80 dark:bg-indigo-950/45',
    textClass: 'text-indigo-700 dark:text-indigo-300',
    borderClass: 'border-indigo-500/70 dark:border-indigo-400/70',
    ringClass: 'ring-indigo-600/25 dark:ring-indigo-400/25'
  },
  {
    value: 'fuchsia',
    label: 'Fuchsia',
    swatchClass: 'bg-fuchsia-600 dark:bg-fuchsia-400',
    softClass: 'bg-fuchsia-50/80 dark:bg-fuchsia-950/45',
    textClass: 'text-fuchsia-700 dark:text-fuchsia-300',
    borderClass: 'border-fuchsia-500/70 dark:border-fuchsia-400/70',
    ringClass: 'ring-fuchsia-600/25 dark:ring-fuchsia-400/25'
  },
  {
    value: 'rose',
    label: 'Rose',
    swatchClass: 'bg-rose-600 dark:bg-rose-400',
    softClass: 'bg-rose-50/80 dark:bg-rose-950/45',
    textClass: 'text-rose-700 dark:text-rose-300',
    borderClass: 'border-rose-500/70 dark:border-rose-400/70',
    ringClass: 'ring-rose-600/25 dark:ring-rose-400/25'
  }
]

const sidebarOpen = ref(false)
const searchOpen = ref(false)
const agentSetupOpen = ref(false)
const agentSummaryOpen = ref(false)
const deleteAgentConfirmOpen = ref(false)
const selectedAgentId = ref('codex1')
const agentSetupMode = ref<'create' | 'edit'>('edit')
const agentDraft = ref<AgentSetup | null>(null)
const pendingDeleteAgentId = ref<string | null>(null)
const draggingAgentId = ref<string | null>(null)
const dragOverAgentId = ref<string | null>(null)
const dragOverPosition = ref<AgentDropPosition>('before')
const openAgentActionsId = ref<string | null>(null)
const sidebarAgentReorderPending = ref(false)
const agentSetupSaving = ref(false)
const duplicateDiscussionPendingId = ref<string | null>(null)
const deleteDiscussionConfirmOpen = ref(false)
const pendingDeleteDiscussion = ref<{ id: string, label: string } | null>(null)
const deleteDiscussionPending = ref(false)
const hasMounted = ref(false)
const config = useRuntimeConfig()
const route = useRoute()
const toast = useToast()
const providerCatalogFailureToastShown = ref(false)

const {
  data: providerCatalog,
  error: providerCatalogError,
  pending: providerCatalogPending
} = useFetch<LlmProvidersResponse>(`${config.public.aiDebateApiUrl}/llms/providers`, {
  server: false
})

const { data: discussions } = useFetch<DebateDiscussion[]>(
  `${config.public.aiDebateApiUrl}/discussions`,
  {
    key: 'debate-discussions',
    server: false,
    default: () => []
  }
)

const chats = computed(() =>
  discussions.value.map(discussion => ({
    id: discussion.id,
    label: discussion.title,
    to: `/debate/${discussion.id}`,
    icon: discussion.has_consensus ? 'i-ph-check-circle' : 'i-ph-chat-circle',
    createdAt: discussion.updated_at
  }))
)

const draftAgents = useDebateAgents()
const activeDebate = useActiveDebateState()
const isDebateRoute = computed(() => route.name === 'debate-id')
const usesActiveDebateAgents = computed(() =>
  Boolean(isDebateRoute.value && activeDebate.value?.id === String(route.params.id ?? ''))
)
const agents = computed<AgentSetup[]>(() =>
  usesActiveDebateAgents.value && activeDebate.value
    ? debateAgentsForSidebar(activeDebate.value)
    : draftAgents.value
)
const canEditSidebarAgents = computed(() => !usesActiveDebateAgents.value)
const canEditActiveDebateAgents = computed(() =>
  Boolean(
    usesActiveDebateAgents.value
    && activeDebate.value
    && activeDebate.value.phase === 'created'
    && !Object.keys(activeDebate.value.theses).length
    && !activeDebate.value.rounds.length
    && !Object.values(activeDebate.value.agents).some(agent => agent.status === 'running')
  )
)
const canEditAgentSetup = computed(() =>
  canEditSidebarAgents.value || canEditActiveDebateAgents.value
)
const activeDebateAgentRunning = computed(() =>
  Boolean(
    usesActiveDebateAgents.value
    && activeDebate.value
    && Object.values(activeDebate.value.agents).some(agent => agent.status === 'running')
  )
)
const canReorderSidebarAgents = computed(() =>
  canEditSidebarAgents.value
  || Boolean(
    usesActiveDebateAgents.value
    && activeDebate.value
    && agents.value.length > 1
    && !activeDebateAgentRunning.value
    && !sidebarAgentReorderPending.value
  )
)

const debateStyleItems = [
  { label: 'Aggressive', value: 'aggressive', description: 'Makes strong claims and actively tries to convince other agents.' },
  { label: 'Normal', value: 'normal', description: 'Balances advocacy, listening, synthesis, and pushback.' },
  { label: 'Collaborative', value: 'collaborative', description: 'Builds on others eagerly and gives ground when evidence is better.' },
  { label: 'Neutral', value: 'neutral', description: 'Judges claims, steers discussion, and rectifies missed risks.' },
  { label: 'Politician', value: 'politician', description: 'Factional, combative, and entertainment-first.' }
]

const technicalPreferenceItems = [
  { label: 'Conservative', value: 'conservative', description: 'Safety-first; prefers proven, battle-tested implementation.' },
  { label: 'Neutral', value: 'neutral', description: 'Balances proven technology with newer options when justified.' },
  { label: 'Innovative', value: 'innovative', description: 'Prefers modern tools and novel designs with managed risk.' },
  { label: 'Frontier', value: 'frontier', description: 'Pushes latest technology and accepts more early-adopter risk.' }
]

const politicalFactionItems = [
  { label: 'Left', value: 'left', description: 'Public benefit, accountability, access, and vendor skepticism.' },
  { label: 'Right', value: 'right', description: 'Control, cost discipline, speed, ownership, and bureaucracy skepticism.' },
  { label: 'Independent', value: 'independent', description: 'Opportunistic coalition building and tactical distance.' }
]

const debateStyleTooltip = debateStyleItems
  .map(item => `${item.label}: ${item.description}`)
  .join('\n')
const technicalPreferenceTooltip = technicalPreferenceItems
  .map(item => `${item.label}: ${item.description}`)
  .join('\n')
const politicalFactionTooltip = politicalFactionItems
  .map(item => `${item.label}: ${item.description}`)
  .join('\n')
const modelTooltip = 'Models are provider-specific CLI model IDs. Changing provider resets this to that provider default; choose another model when you want different capability, speed, or cost behavior.'
const agentPreferenceLabel = computed(() => agentDraft.value?.debateStyle === 'politician' ? 'Political party' : 'Technical preference')
const agentPreferenceItems = computed(() => agentDraft.value?.debateStyle === 'politician' ? politicalFactionItems : technicalPreferenceItems)
const agentPreferenceTooltip = computed(() => agentDraft.value?.debateStyle === 'politician' ? politicalFactionTooltip : technicalPreferenceTooltip)

onNuxtReady(async () => {
})

const { groups } = useChats(chats)
const selectedAgent = computed(() => agents.value.find(agent => agent.id === selectedAgentId.value) ?? agents.value[0])
const pendingDeleteAgent = computed(() => agents.value.find(agent => agent.id === pendingDeleteAgentId.value))
const providers = computed(() => providerCatalog.value?.providers ?? {})
const modelCatalogReady = computed(() => Object.keys(providers.value).length > 0 && !providerCatalogError.value)
const modelCatalogDisabled = computed(() => hasMounted.value && !modelCatalogReady.value)
const providerItems = computed(() =>
  Object.values(providers.value).map(provider => ({
    label: provider.label,
    value: provider.id,
    icon: providerIcon(provider.id)
  }))
)
const selectedProviderInfo = computed(() => agentDraft.value ? providers.value[agentDraft.value.provider] : undefined)
const selectedModelItems = computed(() => {
  const agent = agentDraft.value
  const provider = selectedProviderInfo.value
  if (!agent || !provider) return []

  const items = provider.models.map(model => ({
    label: model.default ? `${model.label} (default)` : model.label,
    value: model.id
  }))

  if (agent.model && !items.some(item => item.value === agent.model)) {
    items.unshift({
      label: `${agent.model} (custom)`,
      value: agent.model
    })
  }

  return items
})

onMounted(() => {
  hasMounted.value = true
  window.addEventListener('ai-debate:open-agent', handleOpenAgentEvent)
})

onBeforeUnmount(() => {
  window.removeEventListener('ai-debate:open-agent', handleOpenAgentEvent)
})

watch(providerCatalogError, (error) => {
  if (!error || providerCatalogFailureToastShown.value) return

  providerCatalogFailureToastShown.value = true
  toast.add({
    title: 'Model catalog unavailable',
    description: 'Start the Python API server to choose providers and models.',
    color: 'error',
    icon: 'i-ph-warning'
  })
})

watch(providerCatalog, () => {
  applyProviderDefaults()
}, { immediate: true })

watch(agents, (currentAgents) => {
  if (!currentAgents.some(agent => agent.id === selectedAgentId.value)) {
    selectedAgentId.value = currentAgents[0]?.id ?? ''
  }
})

const items = computed(() =>
  groups.value?.flatMap((group) => {
    return [
      {
        label: group.label,
        type: 'label' as const
      },
      ...group.items.map(item => ({
        ...item,
        slot: 'chat' as const,
        icon: undefined,
        class:
          item.label === 'Untitled'
            ? 'text-muted'
            : 'font-brand-serif font-semibold'
      }))
    ]
  })
)

function getChatActions(_item: {
  id: string
  label: string
}): DropdownMenuItem[][] {
  return [
    [
      {
        label: 'Rename',
        icon: 'i-ph-pencil',
        onSelect: () => console.log('Rename')
      },
      {
        label: 'Duplicate',
        icon: 'i-ph-copy',
        disabled: duplicateDiscussionPendingId.value !== null,
        onSelect: () => duplicateDiscussion(_item)
      }
    ],
    [
      {
        label: 'Delete',
        icon: 'i-ph-trash',
        color: 'error' as const,
        onSelect: () => requestDeleteDiscussion(_item)
      }
    ]
  ]
}

async function duplicateDiscussion(item: { id: string, label: string }) {
  if (duplicateDiscussionPendingId.value) return

  duplicateDiscussionPendingId.value = item.id
  try {
    const debate = await $fetch<DebateState>(
      `${config.public.aiDebateApiUrl}/debates/${item.id}`
    )
    const clonedAgents = debateAgentDraftsFromState(debate)
    if (clonedAgents.length < 2) {
      throw new Error('The selected discussion does not have enough agents to duplicate.')
    }

    applyDebateDraftFromState(debate, { titleSuffix: 'copy' })
    draftAgents.value = clonedAgents
    selectedAgentId.value = clonedAgents[0]?.id ?? ''
    agentSetupOpen.value = false
    agentSummaryOpen.value = false

    await navigateTo('/')
    toast.add({
      title: 'Discussion duplicated',
      description: `${debate.title} is ready on the setup screen.`,
      color: 'success',
      icon: 'i-ph-copy'
    })
  } catch (error) {
    toast.add({
      title: 'Discussion was not duplicated',
      description:
        error instanceof Error
          ? error.message
          : 'The debate API could not load that discussion.',
      color: 'error',
      icon: 'i-ph-warning'
    })
  } finally {
    duplicateDiscussionPendingId.value = null
  }
}

function requestDeleteDiscussion(item: { id: string, label: string }) {
  pendingDeleteDiscussion.value = item
  deleteDiscussionConfirmOpen.value = true
}

async function confirmDeleteDiscussion() {
  const discussion = pendingDeleteDiscussion.value
  if (!discussion || deleteDiscussionPending.value) return

  deleteDiscussionPending.value = true
  try {
    await $fetch(
      `${config.public.aiDebateApiUrl}/debates/${discussion.id}`,
      {
        method: 'DELETE'
      }
    )

    discussions.value = discussions.value.filter(item => item.id !== discussion.id)

    if (activeDebate.value?.id === discussion.id) {
      activeDebate.value = null
    }

    if (route.name === 'debate-id' && String(route.params.id ?? '') === discussion.id) {
      await navigateTo('/')
    }

    toast.add({
      title: 'Discussion deleted',
      description: discussion.label,
      color: 'success',
      icon: 'i-ph-trash'
    })

    deleteDiscussionConfirmOpen.value = false
    pendingDeleteDiscussion.value = null
  } catch (error) {
    toast.add({
      title: 'Discussion was not deleted',
      description:
        error instanceof Error
          ? error.message
          : 'The debate API rejected the delete request.',
      color: 'error',
      icon: 'i-ph-warning'
    })
  } finally {
    deleteDiscussionPending.value = false
  }
}

function getAgentActions(item: {
  agentId?: string
}): DropdownMenuItem[][] {
  const agentId = item.agentId
  const actions: DropdownMenuItem[][] = [
    [
      {
        label: 'Edit',
        icon: 'i-ph-pencil',
        disabled: !canEditAgentSetup.value,
        onSelect: () => {
          if (agentId) openAgentSetup(agentId)
        }
      }
    ]
  ]

  if (canEditSidebarAgents.value) {
    actions.push([
      {
        label: 'Delete',
        icon: 'i-ph-trash',
        color: 'error' as const,
        onSelect: () => {
          if (agentId) requestDeleteAgent(agentId)
        }
      }
    ])
  }

  return actions
}

function handleAgentActionsOpen(agentId: string, open: boolean) {
  openAgentActionsId.value = open ? agentId : openAgentActionsId.value === agentId ? null : openAgentActionsId.value
}

function handleOpenAgentEvent(event: Event) {
  const detail = (event as CustomEvent<{ agentId?: string }>).detail
  const agentId = findSidebarAgentId(detail?.agentId)
  if (agentId) openAgentSummary(agentId)
}

function findSidebarAgentId(value?: string) {
  const needle = value?.toLowerCase().replace(/^@/, '').trim()
  if (!needle) return ''

  return agents.value.find((agent) => {
    const candidates = [
      agent.id,
      agent.mentionName,
      agent.provider,
      agent.displayName
    ].map(item => item.toLowerCase())

    return candidates.some(candidate => candidate === needle || candidate.includes(needle))
  })?.id ?? ''
}

function makeAgentId(provider: string) {
  const base = provider.toLowerCase().replace(/[^a-z0-9]+/g, '') || 'agent'
  let index = 1
  let id = `${base}${index}`

  while (draftAgents.value.some(agent => agent.id === id || agent.mentionName === id)) {
    index += 1
    id = `${base}${index}`
  }

  return id
}

function addAgent() {
  if (!canEditSidebarAgents.value) return

  const id = makeAgentId('agent')
  const defaultProvider = providers.value.codex ?? Object.values(providers.value)[0]
  if (!defaultProvider) {
    toast.add({
      title: 'Model catalog unavailable',
      description: 'Start the Python API server before adding an agent.',
      color: 'error',
      icon: 'i-ph-warning'
    })
    return
  }

  agentSetupMode.value = 'create'
  agentDraft.value = createDebateAgentSetup({
    id,
    displayName: 'New Agent',
    color: 'celadon',
    provider: defaultProvider.id,
    model: defaultProvider.default_model,
    writeThesis: true,
    debateStyle: 'normal',
    technicalPreference: 'neutral',
    note: ''
  })

  agentSummaryOpen.value = false
  agentSetupOpen.value = true
}

function providerIcon(provider: string) {
  if (provider === 'codex') return 'i-simple-icons-openai'
  if (provider === 'gemini') return 'i-simple-icons-googlegemini'
  if (provider === 'claude') return 'i-simple-icons-anthropic'
  return 'i-ph-cpu'
}

function agentColor(value: string | undefined) {
  return agentColorOptions.find(option => option.value === value) ?? agentColorOptions[0]!
}

function stableAgentColor(state: DebateState, agentId: string) {
  const configuredColor = state.agents[agentId]?.color
  if (configuredColor) return configuredColor
  const rosterIndex = Object.keys(state.agents).indexOf(agentId)
  const colorIndex = rosterIndex === -1 ? 0 : rosterIndex
  return agentColorOptions[colorIndex % agentColorOptions.length]?.value ?? 'celadon'
}

function debateAgentsForSidebar(state: DebateState): AgentSetup[] {
  const orderedIds = [
    ...state.turn_order.filter(agentId => state.agents[agentId]),
    ...Object.keys(state.agents).filter(agentId => !state.turn_order.includes(agentId))
  ]

  return orderedIds.map((agentId) => {
    const agent = state.agents[agentId]!
    const thesis = state.theses[agentId]
    const latestRound = [...state.rounds].reverse().find(round => round.agent === agentId)

    return {
      id: agentId,
      mentionName: agentId,
      displayName: agent.display_name || agentId,
      provider: agent.provider,
      model: agent.model,
      color: stableAgentColor(state, agentId),
      writeThesis: agent.write_thesis,
      debateStyle: agent.debate_style,
      technicalPreference: agent.technical_preference,
      note: agent.additional_note,
      status: agent.status,
      thesisDecision: thesis?.decision ?? (agent.write_thesis ? 'No thesis written yet.' : 'No thesis required.'),
      thesisSummary: thesis?.position ?? (agent.write_thesis ? 'Waiting for this agent to submit a thesis.' : 'This agent joins after thesis sharing.'),
      consensusStatus: consensusStatusForAgent(state, agentId),
      latestDiscussion: latestRound?.discussion ?? 'No discussion turns yet.'
    }
  })
}

function consensusStatusForAgent(state: DebateState, agentId: string) {
  if (state.consensus?.agreed_by.includes(agentId)) {
    return `Accepted final writer @${state.consensus.final_writer}.`
  }

  const proposal = [...state.consensus_proposals]
    .reverse()
    .find(item =>
      item.proposer === agentId
      || item.accepted_by.includes(agentId)
      || Object.hasOwn(item.rejected_by, agentId)
    )

  if (!proposal) return 'No consensus action recorded.'
  if (proposal.accepted_by.includes(agentId)) return `Accepted proposal ${proposal.id}.`
  if (Object.hasOwn(proposal.rejected_by, agentId)) return `Rejected proposal ${proposal.id}.`
  return `Proposed ${proposal.final_writer} as final writer.`
}

function isManualWaitAgent(agent: AgentSetup) {
  const debate = activeDebate.value
  if (!usesActiveDebateAgents.value || !debate || debate.auto_mode) return false
  if (!['debating', 'paused'].includes(debate.phase)) return false
  if (Object.values(debate.agents).some(item => item.status === 'running')) return false
  return debate.next_agent === agent.id && debate.agents[agent.id]?.status === 'done'
}

function sidebarAgentButtonClass(agent: AgentSetup) {
  const classes = []

  if (draggingAgentId.value === agent.id) {
    classes.push('opacity-45')
  }

  if (canReorderSidebarAgents.value) {
    classes.push('cursor-grab active:cursor-grabbing')
  } else {
    classes.push('cursor-default')
  }

  if (agent.status === 'running') {
    const color = agentColor(agent.color)
    classes.push(color.softClass, 'ring-1', color.ringClass)
  } else if (isManualWaitAgent(agent)) {
    classes.push('bg-brass-50/80 ring-1 ring-brass-600/25 dark:bg-brass-950/45 dark:ring-brass-400/25')
  }

  return classes
}

function setSelectedAgentProvider(value: unknown) {
  const provider = typeof value === 'string'
    ? value
    : value && typeof value === 'object' && 'value' in value
      ? String(value.value)
      : ''

  if (!agentDraft.value || !provider) return

  agentDraft.value.provider = provider
  agentDraft.value.model = providers.value[provider]?.default_model ?? ''
}

function applyProviderDefaults() {
  if (!modelCatalogReady.value) return

  draftAgents.value = draftAgents.value.map((agent) => {
    let provider = providers.value[agent.provider]
    if (!provider) {
      provider = providers.value.codex ?? Object.values(providers.value)[0]
    }

    if (!provider) return agent

    const hasModel = provider.models.some(model => model.id === agent.model)
    return {
      ...agent,
      provider: provider.id,
      model: hasModel ? agent.model : provider.default_model
    }
  })

  if (agentDraft.value) {
    const provider = providers.value[agentDraft.value.provider] ?? providers.value.codex ?? Object.values(providers.value)[0]
    if (!provider) return

    const hasModel = provider.models.some(model => model.id === agentDraft.value?.model)
    agentDraft.value.provider = provider.id
    agentDraft.value.model = hasModel ? agentDraft.value.model : provider.default_model
  }
}

function cloneAgent(agent: AgentSetup): AgentSetup {
  return { ...agent }
}

function isPoliticalFaction(value: string | undefined) {
  return politicalFactionItems.some(item => item.value === value)
}

function isTechnicalPreference(value: string | undefined) {
  return technicalPreferenceItems.some(item => item.value === value)
}

function setAgentDraftDebateStyle(value: unknown) {
  if (!agentDraft.value) return
  const debateStyle = String(value)
  agentDraft.value.debateStyle = debateStyle
  if (debateStyle === 'politician' && !isPoliticalFaction(agentDraft.value.technicalPreference)) {
    agentDraft.value.technicalPreference = 'independent'
  } else if (debateStyle !== 'politician' && !isTechnicalPreference(agentDraft.value.technicalPreference)) {
    agentDraft.value.technicalPreference = 'neutral'
  }
}

async function saveAgentSetup(close: () => void) {
  if (!agentDraft.value) return
  if (agentSetupSaving.value) return

  if (agentSetupMode.value === 'create') {
    if (!canEditSidebarAgents.value) return
    draftAgents.value.push(cloneAgent(agentDraft.value))
    selectedAgentId.value = agentDraft.value.id
    agentDraft.value = null
    close()
    return
  }

  if (canEditSidebarAgents.value) {
    const index = draftAgents.value.findIndex(agent => agent.id === agentDraft.value?.id)
    if (index !== -1) {
      draftAgents.value[index] = cloneAgent(agentDraft.value)
    }
    selectedAgentId.value = agentDraft.value.id
    agentDraft.value = null
    close()
    return
  }

  await saveActiveDebateAgentSetup(close)
}

async function saveActiveDebateAgentSetup(close: () => void) {
  const debate = activeDebate.value
  const draft = agentDraft.value
  if (!debate || !draft || !canEditActiveDebateAgents.value) return

  agentSetupSaving.value = true
  try {
    activeDebate.value = await $fetch<DebateState>(
      `${config.public.aiDebateApiUrl}/debates/${debate.id}/agents/${draft.id}`,
      {
        method: 'POST',
        body: {
          name: draft.mentionName,
          provider: draft.provider,
          model: draft.model,
          display_name: draft.displayName,
          color: draft.color,
          write_thesis: draft.writeThesis,
          debate_style: draft.debateStyle,
          technical_preference: draft.technicalPreference,
          additional_note: draft.note
        }
      }
    )
    selectedAgentId.value = draft.mentionName
    agentDraft.value = null
    close()
  } catch (error) {
    toast.add({
      title: 'Agent was not saved',
      description:
        error instanceof Error
          ? error.message
          : 'The debate API rejected the agent update.',
      color: 'error',
      icon: 'i-ph-warning'
    })
  } finally {
    agentSetupSaving.value = false
  }
}

function handleAgentSetupOpen(open: boolean) {
  agentSetupOpen.value = open
  if (!open) {
    agentDraft.value = null
  }
}

function requestDeleteAgent(agentId: string) {
  pendingDeleteAgentId.value = agentId
  deleteAgentConfirmOpen.value = true
}

function confirmDeleteAgent() {
  if (pendingDeleteAgentId.value) {
    deleteAgent(pendingDeleteAgentId.value)
  }

  pendingDeleteAgentId.value = null
  deleteAgentConfirmOpen.value = false
}

function deleteAgent(agentId: string) {
  if (!canEditSidebarAgents.value) return

  const index = draftAgents.value.findIndex(agent => agent.id === agentId)
  if (index === -1) return

  draftAgents.value.splice(index, 1)

  if (selectedAgentId.value === agentId) {
    selectedAgentId.value = draftAgents.value[0]?.id ?? ''
    agentSetupOpen.value = false
    agentSummaryOpen.value = false
  }
}

function handleAgentDragStart(event: DragEvent, agentId: string) {
  if (!canReorderSidebarAgents.value) return

  draggingAgentId.value = agentId
  event.dataTransfer?.setData('text/plain', agentId)
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move'
  }
}

function getAgentDropPosition(event: DragEvent): AgentDropPosition {
  const target = event.currentTarget
  if (!(target instanceof HTMLElement)) return 'before'

  const rect = target.getBoundingClientRect()
  return event.clientY >= rect.top + rect.height / 2 ? 'after' : 'before'
}

function handleAgentDragOver(event: DragEvent, agentId: string) {
  if (!canReorderSidebarAgents.value) return

  if (draggingAgentId.value && draggingAgentId.value !== agentId) {
    dragOverAgentId.value = agentId
    dragOverPosition.value = getAgentDropPosition(event)
  }
}

function handleAgentDragLeave(event: DragEvent, agentId: string) {
  const target = event.currentTarget
  const relatedTarget = event.relatedTarget

  if (target instanceof HTMLElement && relatedTarget instanceof Node && target.contains(relatedTarget)) return

  if (dragOverAgentId.value === agentId) {
    dragOverAgentId.value = null
  }
}

function handleAgentDrop(event: DragEvent, agentId: string) {
  if (!canReorderSidebarAgents.value) return

  const sourceId = draggingAgentId.value
  if (sourceId && sourceId !== agentId) {
    moveAgent(sourceId, agentId, getAgentDropPosition(event))
  }
  handleAgentDragEnd()
}

function handleAgentDragEnd() {
  draggingAgentId.value = null
  dragOverAgentId.value = null
  dragOverPosition.value = 'before'
}

function moveAgent(sourceId: string, targetId: string, position: AgentDropPosition) {
  if (!canReorderSidebarAgents.value) return

  const orderedIds = agents.value.map(agent => agent.id)
  const sourceIndex = orderedIds.indexOf(sourceId)
  if (sourceIndex === -1) return

  const [movedAgentId] = orderedIds.splice(sourceIndex, 1)
  if (!movedAgentId) return

  const targetIndex = orderedIds.indexOf(targetId)
  const insertIndex = targetIndex === -1
    ? orderedIds.length
    : targetIndex + (position === 'after' ? 1 : 0)

  orderedIds.splice(insertIndex, 0, movedAgentId)

  if (canEditSidebarAgents.value) {
    draftAgents.value = orderedIds
      .map(agentId => draftAgents.value.find(agent => agent.id === agentId))
      .filter((agent): agent is AgentSetup => Boolean(agent))
    return
  }

  void persistActiveDebateAgentOrder(orderedIds)
}

async function persistActiveDebateAgentOrder(turnOrder: string[]) {
  const debate = activeDebate.value
  if (!usesActiveDebateAgents.value || !debate || sidebarAgentReorderPending.value) return

  sidebarAgentReorderPending.value = true

  try {
    activeDebate.value = await $fetch<DebateState>(
      `${config.public.aiDebateApiUrl}/debates/${debate.id}/agents/reorder`,
      {
        method: 'POST',
        body: { turn_order: turnOrder }
      }
    )
  } catch (error) {
    toast.add({
      title: 'Agent order was not changed',
      description:
        error instanceof Error
          ? error.message
          : 'The debate API rejected the new agent order.',
      color: 'error',
      icon: 'i-ph-warning'
    })
  } finally {
    sidebarAgentReorderPending.value = false
  }
}

function openAgentSummary(agentId: string) {
  selectedAgentId.value = agentId
  agentSummaryOpen.value = true
}

function openAgentSetup(agentId: string) {
  if (!canEditAgentSetup.value) return

  const agent = agents.value.find(item => item.id === agentId)
  if (!agent) return

  selectedAgentId.value = agentId
  agentSetupMode.value = 'edit'
  agentDraft.value = cloneAgent(agent)
  agentSummaryOpen.value = false
  agentSetupOpen.value = true
}

defineShortcuts({
  meta_o: () => {
    navigateTo('/')
  }
})
</script>

<template>
  <UDashboardGroup unit="rem" class="app-print-shell">
    <UDashboardSidebar
      id="default"
      v-model:open="sidebarOpen"
      :min-size="12"
      collapsible
      resizable
      :menu="{ inset: true }"
      class="app-print-hidden border-r-0 py-4 dark:[--ui-bg-elevated:var(--ui-color-neutral-900)]"
    >
      <template #header="{ collapsed }">
        <BrandIdentity v-if="!collapsed" to="/" size="md" />

        <UDashboardSidebarCollapse class="ms-auto" />
      </template>

      <template #default="{ collapsed }">
        <UNavigationMenu
          :items="[
            {
              label: 'New Debate',
              to: '/',
              kbds: ['meta', 'o'],
              icon: 'i-ph-plus-circle'
            },
            {
              label: 'Search',
              icon: 'i-ph-magnifying-glass',
              kbds: ['meta', 'k'],
              onSelect: () => {
                searchOpen = true;
              }
            }
          ]"
          :collapsed="collapsed"
          orientation="vertical"
        >
          <template #item-trailing="{ item }">
            <div
              v-if="item.kbds?.length"
              class="flex items-center gap-px opacity-0 group-hover:opacity-100 transition-opacity"
            >
              <UKbd
                v-for="kbd in item.kbds"
                :key="kbd"
                :value="kbd"
                size="sm"
                variant="soft"
                class="bg-accented/50"
              />
            </div>
          </template>
        </UNavigationMenu>

        <div v-if="!collapsed" class="mt-4">
          <div class="flex min-h-8 items-center gap-2 pl-2.5 pr-0">
            <div class="text-xs font-medium text-muted">
              Agents
            </div>
            <UButton
              icon="i-ph-plus"
              color="neutral"
              variant="ghost"
              size="xs"
              class="ml-auto rounded-[5px] hover:bg-accented/50 focus-visible:bg-accented/50"
              aria-label="Add agent"
              :disabled="modelCatalogDisabled || !canEditSidebarAgents"
              @click="addAgent"
            />
          </div>
          <div
            v-if="usesActiveDebateAgents"
            class="px-2.5 pb-1 text-[11px] leading-4 text-dimmed"
          >
            Drag to reorder turns.
          </div>
          <div class="grid gap-1">
            <div
              v-for="agent in agents"
              :key="agent.id"
              class="relative"
            >
              <div
                v-if="dragOverAgentId === agent.id"
                class="pointer-events-none absolute inset-x-1 z-10 h-px rounded-full bg-primary"
                :class="dragOverPosition === 'before' ? '-top-px' : '-bottom-px'"
              />

              <button
                type="button"
                :draggable="canReorderSidebarAgents"
                class="group relative flex h-8 w-full min-w-0 items-center gap-2 overflow-hidden rounded-md px-2.5 pr-7.5 text-left text-sm transition-colors hover:bg-accented/70 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                :class="sidebarAgentButtonClass(agent)"
                @click="openAgentSummary(agent.id)"
                @dragstart="handleAgentDragStart($event, agent.id)"
                @dragover.prevent="handleAgentDragOver($event, agent.id)"
                @dragleave="handleAgentDragLeave($event, agent.id)"
                @drop.prevent="handleAgentDrop($event, agent.id)"
                @dragend="handleAgentDragEnd"
              >
                <span
                  class="size-2.5 shrink-0 rounded-full ring-2 ring-default"
                  :class="agentColor(agent.color).swatchClass"
                />
                <span
                  class="min-w-0 flex-1 truncate font-brand-serif font-semibold"
                  :class="agentColor(agent.color).textClass"
                >
                  {{ agent.displayName }}
                </span>
                <div
                  v-if="canEditAgentSetup"
                  class="absolute inset-y-0 end-0 flex items-center transition-transform group-hover:translate-x-0"
                  :class="openAgentActionsId === agent.id ? 'translate-x-0' : 'translate-x-full'"
                >
                  <UDropdownMenu
                    :items="getAgentActions({ agentId: agent.id })"
                    :content="{ align: 'end' }"
                    :open="openAgentActionsId === agent.id"
                    @update:open="handleAgentActionsOpen(agent.id, $event)"
                  >
                    <UButton
                      as="div"
                      icon="i-ph-dots-three"
                      color="neutral"
                      variant="link"
                      size="sm"
                      class="rounded-[5px] data-[state=open]:bg-accented/50"
                      aria-label="Agent actions"
                      tabindex="-1"
                      @click.stop.prevent
                    />
                  </UDropdownMenu>
                </div>
              </button>
            </div>
          </div>
        </div>

        <UNavigationMenu
          v-if="!collapsed"
          :items="items"
          :collapsed="collapsed"
          orientation="vertical"
          class="mt-4"
          :ui="{
            link: 'overflow-hidden pr-7.5',
            linkTrailing:
              'translate-x-full group-hover:translate-x-0 group-has-data-[state=open]:translate-x-0 transition-transform ms-0 absolute inset-e-px'
          }"
        >
          <template #chat-trailing="{ item }">
            <UDropdownMenu
              :items="getChatActions(item as { id: string; label: string })"
              :content="{ align: 'end' }"
            >
              <UButton
                as="div"
                icon="i-ph-dots-three"
                color="neutral"
                variant="link"
                size="sm"
                class="rounded-[5px] hover:bg-accented/50 focus-visible:bg-accented/50 data-[state=open]:bg-accented/50"
                aria-label="Debate actions"
                tabindex="-1"
                @click.stop.prevent
              />
            </UDropdownMenu>
          </template>
        </UNavigationMenu>
      </template>
    </UDashboardSidebar>

    <UDashboardSearch
      v-model:open="searchOpen"
      placeholder="Search debates..."
      :groups="[
        {
          id: 'links',
          items: [
            {
              label: 'New Debate',
              to: '/',
              icon: 'i-ph-plus-circle',
              kbds: ['meta', 'o']
            }
          ]
        },
        ...groups
      ]"
    />

    <div
      class="app-print-main flex-1 flex m-4 lg:ml-0 rounded-md ring ring-default bg-default/75 shadow min-w-0 overflow-hidden"
    >
      <slot />
    </div>

    <UModal
      v-model:open="agentSummaryOpen"
      :title="selectedAgent ? selectedAgent.displayName : 'Agent Summary'"
      :description="canEditAgentSetup ? 'Current setup for this debate agent.' : 'Read-only agent profile. Drag agents in the sidebar to change turn order.'"
      :ui="{ content: 'max-w-2xl overflow-hidden' }"
    >
      <template #body>
        <div v-if="selectedAgent" class="grid min-w-0 gap-4 overflow-hidden">
          <div class="flex min-w-0 flex-wrap items-center gap-2">
            <span
              class="size-2.5 shrink-0 rounded-full ring-2 ring-default"
              :class="agentColor(selectedAgent.color).swatchClass"
            />
            <span
              class="truncate text-sm font-semibold"
              :class="agentColor(selectedAgent.color).textClass"
            >
              {{ selectedAgent.displayName }}
            </span>
            <UBadge variant="soft" color="neutral" class="capitalize">
              {{ selectedAgent.provider }}
            </UBadge>
            <UBadge variant="soft" color="neutral">
              {{ selectedAgent.status }}
            </UBadge>
            <span class="truncate text-sm text-muted">
              @{{ selectedAgent.mentionName }} · {{ selectedAgent.model }}
            </span>
          </div>

          <div class="grid min-w-0 gap-3 sm:grid-cols-2">
            <div class="min-w-0 rounded-md bg-elevated/45 p-3 ring ring-default">
              <div class="mb-1 text-xs font-medium text-muted">
                Thesis
              </div>
              <p class="text-sm font-medium text-highlighted">
                {{ selectedAgent.thesisDecision }}
              </p>
              <p class="mt-2 [overflow-wrap:anywhere] text-sm text-muted">
                {{ selectedAgent.thesisSummary }}
              </p>
            </div>

            <div class="min-w-0 rounded-md bg-elevated/45 p-3 ring ring-default">
              <div class="mb-1 text-xs font-medium text-muted">
                Consensus Status
              </div>
              <p class="[overflow-wrap:anywhere] text-sm text-highlighted">
                {{ selectedAgent.consensusStatus }}
              </p>
              <div class="mt-3 flex flex-wrap gap-1.5">
                <UBadge size="sm" variant="soft" color="neutral">
                  {{ selectedAgent.debateStyle }}
                </UBadge>
                <UBadge size="sm" variant="soft" color="neutral">
                  {{ selectedAgent.technicalPreference }}
                </UBadge>
                <UBadge
                  size="sm"
                  variant="soft"
                  :color="selectedAgent.writeThesis ? 'primary' : 'neutral'"
                >
                  {{ selectedAgent.writeThesis ? 'Writes thesis' : 'Joins later' }}
                </UBadge>
              </div>
            </div>
          </div>

          <div class="min-w-0 rounded-md bg-elevated/45 p-3 ring ring-default">
            <div class="mb-1 text-xs font-medium text-muted">
              Latest Discussion
            </div>
            <p class="[overflow-wrap:anywhere] text-sm text-highlighted">
              {{ selectedAgent.latestDiscussion }}
            </p>
          </div>

          <div
            v-if="selectedAgent.note"
            class="min-w-0 rounded-md bg-elevated/45 p-3 ring ring-default"
          >
            <div class="mb-1 text-xs font-medium text-muted">
              Private Note
            </div>
            <p class="[overflow-wrap:anywhere] text-sm text-muted">
              {{ selectedAgent.note }}
            </p>
          </div>
        </div>
      </template>

      <template #footer="{ close }">
        <div class="flex w-full justify-end gap-2">
          <UButton color="neutral" variant="ghost" @click="close">
            Close
          </UButton>
          <UButton
            icon="i-ph-pencil"
            :disabled="!canEditAgentSetup"
            @click="() => selectedAgent && openAgentSetup(selectedAgent.id)"
          >
            Edit Agent
          </UButton>
        </div>
      </template>
    </UModal>

    <UModal
      :open="agentSetupOpen"
      :title="agentSetupMode === 'create' ? 'Add AI Agent' : 'AI Agent Setup'"
      :description="agentSetupMode === 'create' ? 'Configure the new debate agent before adding it.' : 'Edit this debate agent configuration.'"
      :ui="{ content: 'max-w-2xl' }"
      @update:open="handleAgentSetupOpen"
    >
      <template #body>
        <div v-if="agentDraft" class="grid gap-4">
          <div class="grid gap-3 sm:grid-cols-2">
            <UFormField label="Display name">
              <UInput v-model="agentDraft.displayName" class="w-full" />
            </UFormField>

            <UFormField label="Mention name">
              <UInput v-model="agentDraft.mentionName" class="w-full" />
            </UFormField>

            <UFormField label="Provider">
              <USelect
                :model-value="agentDraft.provider"
                :items="providerItems"
                :disabled="modelCatalogDisabled"
                class="w-full"
                @update:model-value="setSelectedAgentProvider"
              />
            </UFormField>

            <UFormField>
              <template #label>
                <span class="inline-flex items-center gap-1">
                  Model
                  <UTooltip
                    :text="modelTooltip"
                    :content="{ side: 'top', align: 'start' }"
                  >
                    <UIcon
                      name="i-ph-info"
                      class="size-3.5 text-muted hover:text-highlighted"
                    />
                  </UTooltip>
                </span>
              </template>

              <USelect
                v-model="agentDraft.model"
                :items="selectedModelItems"
                :loading="providerCatalogPending"
                :disabled="modelCatalogDisabled"
                class="w-full"
              />
            </UFormField>

            <UFormField>
              <template #label>
                <span class="inline-flex items-center gap-1">
                  Debate style
                  <UTooltip
                    :text="debateStyleTooltip"
                    :content="{ side: 'top', align: 'start' }"
                  >
                    <UIcon
                      name="i-ph-info"
                      class="size-3.5 text-muted hover:text-highlighted"
                    />
                  </UTooltip>
                </span>
              </template>

              <USelect
                :model-value="agentDraft.debateStyle"
                :items="debateStyleItems"
                class="w-full"
                @update:model-value="setAgentDraftDebateStyle"
              />
            </UFormField>

            <UFormField>
              <template #label>
                <span class="inline-flex items-center gap-1">
                  {{ agentPreferenceLabel }}
                  <UTooltip
                    :text="agentPreferenceTooltip"
                    :content="{ side: 'top', align: 'start' }"
                  >
                    <UIcon
                      name="i-ph-info"
                      class="size-3.5 text-muted hover:text-highlighted"
                    />
                  </UTooltip>
                </span>
              </template>

              <USelect
                v-model="agentDraft.technicalPreference"
                :items="agentPreferenceItems"
                class="w-full"
              />
            </UFormField>
          </div>

          <UCheckbox
            v-model="agentDraft.writeThesis"
            label="Write initial thesis"
            description="Agents that skip thesis can still join the debate later."
          />

          <UFormField label="Agent color">
            <div class="grid gap-2 sm:grid-cols-3">
              <button
                v-for="color in agentColorOptions"
                :key="color.value"
                type="button"
                class="flex min-w-0 items-center gap-2 rounded-md border px-2.5 py-2 text-left text-sm transition-colors"
                :class="agentDraft.color === color.value
                  ? ['ring-2', color.softClass, color.textClass, color.borderClass, color.ringClass]
                  : 'border-default hover:bg-elevated'"
                :aria-pressed="agentDraft.color === color.value"
                @click="agentDraft.color = color.value"
              >
                <span
                  class="size-4 shrink-0 rounded-full ring-2 ring-default"
                  :class="color.swatchClass"
                />
                <span class="truncate font-medium">
                  {{ color.label }}
                </span>
              </button>
            </div>
          </UFormField>

          <UFormField label="Private note">
            <UTextarea
              v-model="agentDraft.note"
              :rows="4"
              class="w-full"
              placeholder="Additional private behavior notes for this agent..."
            />
          </UFormField>

          <UAlert
            v-if="providerCatalogError"
            color="warning"
            variant="soft"
            icon="i-ph-warning"
            title="Model catalog unavailable"
            description="Start the Python API server to choose providers and models."
          />
        </div>
      </template>

      <template #footer="{ close }">
        <div class="flex w-full justify-end gap-2">
          <UButton color="neutral" variant="ghost" @click="handleAgentSetupOpen(false)">
            Close
          </UButton>
          <UButton
            :loading="agentSetupSaving"
            :disabled="agentSetupSaving || (hasMounted && agentSetupMode === 'create' && (!modelCatalogReady || !agentDraft?.provider || !agentDraft?.model))"
            @click="saveAgentSetup(close)"
          >
            {{ agentSetupMode === 'create' ? 'Add Agent' : 'Save Agent' }}
          </UButton>
        </div>
      </template>
    </UModal>

    <UModal
      v-model:open="deleteDiscussionConfirmOpen"
      title="Delete Discussion"
      :description="pendingDeleteDiscussion ? `Delete ${pendingDeleteDiscussion.label}? This removes the discussion and all generated artifacts.` : 'Delete this discussion?'"
      :ui="{ content: 'max-w-md' }"
    >
      <template #footer="{ close }">
        <div class="flex w-full justify-end gap-2">
          <UButton
            color="neutral"
            variant="ghost"
            :disabled="deleteDiscussionPending"
            @click="() => {
              pendingDeleteDiscussion = null;
              close();
            }"
          >
            Cancel
          </UButton>
          <UButton
            color="error"
            icon="i-ph-trash"
            :loading="deleteDiscussionPending"
            @click="confirmDeleteDiscussion"
          >
            Delete Discussion
          </UButton>
        </div>
      </template>
    </UModal>

    <UModal
      v-model:open="deleteAgentConfirmOpen"
      title="Delete Agent"
      :description="pendingDeleteAgent ? `Delete ${pendingDeleteAgent.displayName}? This removes the agent from the current roster.` : 'Delete this agent?'"
      :ui="{ content: 'max-w-md' }"
    >
      <template #footer="{ close }">
        <div class="flex w-full justify-end gap-2">
          <UButton
            color="neutral"
            variant="ghost"
            @click="() => {
              pendingDeleteAgentId = null;
              close();
            }"
          >
            Cancel
          </UButton>
          <UButton
            color="error"
            icon="i-ph-trash"
            @click="confirmDeleteAgent"
          >
            Delete Agent
          </UButton>
        </div>
      </template>
    </UModal>
  </UDashboardGroup>
</template>
