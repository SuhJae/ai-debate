<script setup lang="ts">
import DebateFinalDocument from '~/components/debate/DebateFinalDocument.vue'
import DebateMarkdown from '~/components/debate/DebateMarkdown.vue'
import DebateTranscript from '~/components/debate/DebateTranscript.vue'
import DebateThesisJobs from '~/components/debate/DebateThesisJobs.vue'
import type { DebateChatMessage } from '~/types/debate-chat'
import type { DebateState } from '~/types/debate-state'
import { createDemoDebateState } from '~/utils/debate-demo'
import { agentColor } from '~/utils/debate-config'
import {
  debateAgentsFromState,
  debateMessagesFromState
} from '~/utils/debate-transcript'

type BadgeColor = 'primary' | 'neutral'

definePageMeta({
  layout: 'chat'
})

const route = useRoute()
const config = useRuntimeConfig()
const toast = useToast()
const debateId = computed(() => String(route.params.id ?? ''))
const hasMounted = ref(false)
const isDemo = computed(() => debateId.value === 'demo')
const messageDraft = ref('')
const localQueuedMessage = ref('')
const localMessages = ref<DebateChatMessage[]>([])
const sendingMessage = ref(false)
const autoModePending = ref(false)
const actionPending = ref(false)
const discussionRegenerating = ref(false)
const discussionRegeneratingAgentId = ref<string | null>(null)
const thesisRegeneratingAgentIds = ref<string[]>([])
const finalArtifactContents = ref<Record<string, string>>({})
const finalArtifactLoadingPaths = ref<Record<string, boolean>>({})
const finalArtifactRequestId = ref(0)
const streamEnabled = computed(() => !isDemo.value)
const activeDebate = useActiveDebateState()

const {
  data: debate,
  error,
  pending
} = useAsyncData<DebateState>(
  'debate-detail',
  () => {
    if (isDemo.value) return Promise.resolve(createDemoDebateState())
    return $fetch<DebateState>(
      `${config.public.aiDebateApiUrl}/debates/${debateId.value}`
    )
  },
  {
    server: false,
    watch: [debateId]
  }
)

const { streamingMessages, thesisStreams } = useDebateStream(
  debateId,
  debate,
  {
    enabled: streamEnabled,
    wsBaseUrl: String(config.public.aiDebateWsUrl)
  }
)

const transcriptAgents = computed(() =>
  debate.value ? debateAgentsFromState(debate.value) : []
)
const transcriptMessages = computed(() => {
  const messages = debate.value
    ? debateMessagesFromState(debate.value, { includeTheses: false })
    : []
  return [...messages, ...streamingMessages.value, ...localMessages.value]
})
const agentById = computed(() => new Map(transcriptAgents.value.map(agent => [agent.id, agent])))
const finalArtifactPaths = computed(() => {
  const state = debate.value
  const document = state?.final_document
  if (!state || state.id !== debateId.value || !document) return []

  const paths = document.drafts
    .map(draft => draft.draft_path)
    .filter(Boolean)
  return [...new Set(paths)]
})
const finalArtifactPathsKey = computed(() => finalArtifactPaths.value.join('|'))

const phaseLabel = computed(
  () => debate.value?.phase.replaceAll('_', ' ') ?? 'loading'
)
const permissionBadges = computed<Array<{
  key: string
  label: string
  icon: string
  color: BadgeColor
}>>(() => {
  const state = debate.value
  if (!state) return []

  const mode = state.tool_mode
  const localLabel = {
    text_only: 'Local off',
    read_only: 'Files',
    probe: 'Files + probes',
    edit: 'Edit',
    full: 'Full tools'
  }[mode] ?? mode.replaceAll('_', ' ')

  return [
    {
      key: 'local',
      label: localLabel,
      icon: mode === 'text_only' ? 'i-ph-lock-simple' : 'i-ph-folder-open',
      color: mode === 'text_only' ? 'neutral' : 'primary'
    },
    {
      key: 'web',
      label: state.allow_web_evidence ? 'Web on' : 'Web off',
      icon: state.allow_web_evidence ? 'i-ph-globe' : 'i-ph-globe-x',
      color: state.allow_web_evidence ? 'primary' : 'neutral'
    }
  ]
})
const queuedMessage = computed(
  () => localQueuedMessage.value || debate.value?.send_after_this || ''
)
const hasQueuedMessage = computed(() => queuedMessage.value.trim().length > 0)
const canSendMessage = computed(() =>
  Boolean(
    debate.value
    && messageDraft.value.trim()
    && !sendingMessage.value
    && !hasQueuedMessage.value
  )
)
const promptStatus = computed(() =>
  sendingMessage.value ? 'submitted' : 'ready'
)
const thesisGenerationRunning = computed(() =>
  Object.values(debate.value?.agents ?? {}).some(
    agent => agent.write_thesis && agent.status === 'running'
  )
)
const thesisRegenerationLocked = computed(() =>
  Boolean(
    debate.value
    && (
      debate.value.rounds.length > 0
      || [
        'debating',
        'paused',
        'consensus_reached',
        'drafting_final',
        'reviewing_final',
        'revising_final',
        'accepted'
      ].includes(debate.value.phase)
    )
  )
)
const nextAction = computed(() => {
  if (!debate.value || isDemo.value) return null

  if (['created', 'starting_theses', 'awaiting_theses', 'failed'].includes(debate.value.phase)) {
    return {
      label: 'Start theses',
      endpoint: 'start-theses',
      icon: 'i-ph-play'
    }
  }

  if (debate.value.phase === 'theses_ready') {
    return {
      label: 'Share theses',
      endpoint: 'share-theses',
      icon: 'i-ph-share-network'
    }
  }

  if (['debating', 'paused'].includes(debate.value.phase)) {
    return {
      label: 'Run turn',
      endpoint: 'turn',
      icon: 'i-ph-arrow-right',
      body: { agent_id: null }
    }
  }

  if (['consensus_reached', 'revising_final'].includes(debate.value.phase)) {
    return {
      label: 'Draft final',
      endpoint: 'draft-final',
      icon: 'i-ph-file-text'
    }
  }

  if (debate.value.phase === 'reviewing_final') {
    return {
      label: 'Review final',
      endpoint: 'review-final',
      icon: 'i-ph-check-circle'
    }
  }

  return null
})
const nextTurnAgentId = computed(() => {
  const state = debate.value
  if (!state?.turn_order.length) return null

  if (!state.next_agent) return state.turn_order[0] ?? null

  const currentIndex = state.turn_order.indexOf(state.next_agent)
  if (currentIndex === -1) return state.turn_order[0] ?? null
  return state.turn_order[(currentIndex + 1) % state.turn_order.length] ?? null
})
const nextActionAgent = computed(() => {
  if (discussionRegeneratingAgentId.value) {
    return transcriptAgents.value.find(agent => agent.id === discussionRegeneratingAgentId.value) ?? null
  }
  if (nextAction.value?.endpoint !== 'turn') return null
  const agentId = nextTurnAgentId.value
  if (!agentId) return null
  return transcriptAgents.value.find(agent => agent.id === agentId) ?? null
})
const debateAgentRunning = computed(() =>
  Object.values(debate.value?.agents ?? {}).some(agent => agent.status === 'running')
)
const nextActionDisabled = computed(() =>
  Boolean(
    discussionRegenerating.value
    || debateAgentRunning.value
    || (
      nextAction.value?.endpoint === 'start-theses'
      && thesisGenerationRunning.value
    )
  )
)
const showNextActionButton = computed(() =>
  Boolean(
    nextAction.value
    && nextAction.value.endpoint !== 'share-theses'
    && !discussionRegenerating.value
    && !debateAgentRunning.value
  )
)
const canRegenerateDiscussion = computed(() =>
  Boolean(
    debate.value
    && debate.value.rounds.length
    && ['debating', 'paused', 'consensus_reached'].includes(debate.value.phase)
    && !debateAgentRunning.value
    && !discussionRegenerating.value
  )
)
const nextActionButtonClasses = computed(() => {
  if (!nextActionAgent.value) return ''
  const color = agentColor(nextActionAgent.value.color)
  return [
    color.softClass,
    color.textClass,
    'ring-1',
    color.ringClass,
    'hover:bg-accented/60'
  ]
})
const activeConsensusProposal = computed(() => {
  const state = debate.value
  if (!state || state.consensus) return null

  return [...state.consensus_proposals]
    .reverse()
    .find(proposal =>
      proposal.status === 'active'
      && !Object.keys(proposal.rejected_by).length
    ) ?? null
})
const consensusVoteRows = computed(() => {
  const state = debate.value
  const proposal = activeConsensusProposal.value
  if (!state || !proposal) return []

  return state.turn_order
    .filter(agentId => state.agents[agentId]?.status !== 'disabled')
    .map((agentId) => {
      const rejected = proposal.rejected_by[agentId]
      const accepted = proposal.accepted_by.includes(agentId)
      const agent = agentById.value.get(agentId)

      return {
        agentId,
        name: agent?.name ?? agentId,
        color: agentColor(agent?.color),
        state: rejected ? 'rejected' : accepted ? 'accepted' : 'waiting',
        icon: rejected ? 'i-ph-x' : accepted ? 'i-ph-check' : 'i-ph-clock',
        title: rejected ? proposal.rejected_by[agentId] : accepted ? 'Accepted' : 'Waiting for vote'
      }
    })
})
const consensusFinalWriterName = computed(() => {
  const writer = activeConsensusProposal.value?.final_writer
  if (!writer) return ''
  return agentById.value.get(writer)?.name ?? writer
})
function consensusVoteClasses(row: typeof consensusVoteRows.value[number]) {
  if (row.state === 'rejected') {
    return [
      'bg-error/5 text-error border-error/30'
    ]
  }

  if (row.state === 'accepted') {
    return [
      row.color.softClass,
      row.color.textClass,
      row.color.borderClass
    ]
  }

  return [
    'border-default bg-muted/40 text-muted'
  ]
}
const shouldQueueMessage = computed(() => {
  if (!debate.value) return false

  return Object.values(debate.value.agents).some(
    agent => agent.status === 'running'
  )
})

watch(debateId, () => {
  messageDraft.value = ''
  localQueuedMessage.value = ''
  localMessages.value = []
  finalArtifactContents.value = {}
  finalArtifactLoadingPaths.value = {}
})

watch(
  debate,
  (state) => {
    if (isDemo.value) {
      activeDebate.value = null
      return
    }
    activeDebate.value = state ?? null
  },
  { immediate: true, deep: true }
)

watch(activeDebate, (state) => {
  if (isDemo.value) return
  if (!state || state.id !== debateId.value) return
  if (state === debate.value) return

  debate.value = state
})

watch(
  [debateId, finalArtifactPathsKey],
  async ([id]) => {
    const requestId = finalArtifactRequestId.value + 1
    finalArtifactRequestId.value = requestId
    const paths = finalArtifactPaths.value
    finalArtifactContents.value = {}
    finalArtifactLoadingPaths.value = {}
    if (!paths.length) return

    if (isDemo.value) {
      const demoContent = demoFinalMarkdown()
      finalArtifactContents.value = Object.fromEntries(paths.map(path => [path, demoContent]))
      return
    }

    finalArtifactLoadingPaths.value = Object.fromEntries(paths.map(path => [path, true]))
    try {
      const artifacts = await Promise.all(
        paths.map(path =>
          $fetch<{ path: string, content: string }>(
            `${config.public.aiDebateApiUrl}/debates/${id}/artifacts/${path}`
          )
        )
      )
      if (requestId !== finalArtifactRequestId.value) return
      finalArtifactContents.value = Object.fromEntries(
        artifacts.map(artifact => [artifact.path, artifact.content])
      )
    } catch (error) {
      if (requestId !== finalArtifactRequestId.value) return
      finalArtifactContents.value = {}
      toast.add({
        color: 'error',
        icon: 'i-ph-warning',
        title: 'Final draft was not loaded',
        description:
          error instanceof Error
            ? error.message
            : 'The debate API did not return the final artifact.'
      })
    } finally {
      if (requestId === finalArtifactRequestId.value) {
        finalArtifactLoadingPaths.value = {}
      }
    }
  },
  { immediate: true }
)

onBeforeUnmount(() => {
  activeDebate.value = null
})

watch(
  () => debate.value?.send_after_this,
  (queuedText, previousQueuedText) => {
    if (queuedText && !localQueuedMessage.value && !messageDraft.value) {
      messageDraft.value = queuedText
    }
    if (!queuedText && previousQueuedText && messageDraft.value === previousQueuedText) {
      messageDraft.value = ''
    }
  }
)

onMounted(() => {
  hasMounted.value = true
})

function openAgentProfile(agentId: string) {
  window.dispatchEvent(
    new CustomEvent('ai-debate:open-agent', {
      detail: { agentId }
    })
  )
}

function createLocalUserMessage(content: string): DebateChatMessage {
  return {
    id: `local-user-${Date.now()}`,
    role: 'user',
    content,
    createdAt: new Intl.DateTimeFormat(undefined, {
      hour: '2-digit',
      minute: '2-digit'
    }).format(new Date())
  }
}

function demoFinalMarkdown() {
  return `# Final Engineering Thesis

## Decision
Use FastAPI routes with a rich Nuxt transcript.

## Rationale
The accepted consensus favors a typed backend contract, visible evidence, and explicit consensus state.

## Implementation Plan
- Keep debate state in the backend API.
- Stream turn output into the transcript.
- Show evidence, consensus, and final review status in the UI.

## Risks
- Long-running model calls need visible progress.

## Acceptance Criteria
- Users can read the final draft and see each reviewer state.`
}

async function submitMessage() {
  const text = messageDraft.value.trim()
  if (!text || !debate.value || sendingMessage.value || hasQueuedMessage.value)
    return

  sendingMessage.value = true

  try {
    let queued = false

    if (shouldQueueMessage.value) {
      queued = true
      if (isDemo.value) {
        localQueuedMessage.value = text
      } else {
        const updatedDebate = await $fetch<DebateState>(
          `${config.public.aiDebateApiUrl}/debates/${debateId.value}/send-after-this`,
          {
            method: 'POST',
            body: { text }
          }
        )
        debate.value = updatedDebate
        queued = Boolean(updatedDebate.send_after_this)
      }
    } else if (!isDemo.value) {
      debate.value = await $fetch<DebateState>(
        `${config.public.aiDebateApiUrl}/debates/${debateId.value}/user-opinion`,
        {
          method: 'POST',
          body: { text }
        }
      )
    } else {
      localMessages.value.push(createLocalUserMessage(text))
    }

    if (!queued) {
      messageDraft.value = ''
    }
  } catch (error) {
    toast.add({
      color: 'error',
      icon: 'i-ph-warning',
      title: 'Message was not sent',
      description:
        error instanceof Error
          ? error.message
          : 'The debate API rejected the message.'
    })
  } finally {
    sendingMessage.value = false
  }
}

async function editQueuedMessage() {
  const text = queuedMessage.value
  if (!text || sendingMessage.value) return

  messageDraft.value = text
  localQueuedMessage.value = ''

  if (isDemo.value || !debate.value?.send_after_this) return

  try {
    debate.value = await $fetch<DebateState>(
      `${config.public.aiDebateApiUrl}/debates/${debateId.value}/send-after-this`,
      {
        method: 'POST',
        body: { text: '' }
      }
    )
  } catch (error) {
    toast.add({
      color: 'error',
      icon: 'i-ph-warning',
      title: 'Queued message stayed on the server',
      description:
        error instanceof Error
          ? error.message
          : 'The debate API rejected the queue edit.'
    })
  }
}

async function toggleAutoMode() {
  if (!debate.value || autoModePending.value) return

  const enabled = !debate.value.auto_mode
  autoModePending.value = true

  try {
    if (isDemo.value) {
      debate.value = {
        ...debate.value,
        auto_mode: enabled
      }
    } else {
      debate.value = await $fetch<DebateState>(
        `${config.public.aiDebateApiUrl}/debates/${debateId.value}/auto`,
        {
          method: 'POST',
          body: { enabled }
        }
      )
    }
  } catch (error) {
    toast.add({
      color: 'error',
      icon: 'i-ph-warning',
      title: 'Auto mode was not changed',
      description:
        error instanceof Error
          ? error.message
          : 'The debate API rejected the auto mode change.'
    })
  } finally {
    autoModePending.value = false
  }
}

async function advanceDebate() {
  if (!debate.value || !nextAction.value || actionPending.value) return
  if (nextActionDisabled.value) return

  actionPending.value = true

  try {
    debate.value = await $fetch<DebateState>(
      `${config.public.aiDebateApiUrl}/debates/${debateId.value}/${nextAction.value.endpoint}`,
      {
        method: 'POST',
        body: nextAction.value.body
      }
    )
  } catch (error) {
    toast.add({
      color: 'error',
      icon: 'i-ph-warning',
      title: 'Debate did not advance',
      description:
        error instanceof Error
          ? error.message
          : 'The debate API rejected the action.'
    })
  } finally {
    actionPending.value = false
  }
}

async function regenerateDiscussion() {
  if (!debate.value || !canRegenerateDiscussion.value) return

  discussionRegenerating.value = true
  const previousDebate = debate.value
  const lastRound = previousDebate.rounds.at(-1)
  discussionRegeneratingAgentId.value = lastRound?.agent ?? null

  debate.value = {
    ...previousDebate,
    next_agent: lastRound?.agent ?? previousDebate.next_agent,
    rounds: previousDebate.rounds.slice(0, -1),
    consensus_proposals: previousDebate.consensus_proposals.filter(
      proposal => proposal.status !== 'active'
    ),
    consensus: null
  }

  try {
    debate.value = await $fetch<DebateState>(
      `${config.public.aiDebateApiUrl}/debates/${debateId.value}/turn/regenerate`,
      {
        method: 'POST'
      }
    )
  } catch (error) {
    toast.add({
      color: 'error',
      icon: 'i-ph-warning',
      title: 'Discussion was not regenerated',
      description:
        error instanceof Error
          ? error.message
          : 'The debate API rejected discussion regeneration.'
    })
    debate.value = previousDebate
  } finally {
    discussionRegenerating.value = false
    discussionRegeneratingAgentId.value = null
  }
}

async function regenerateThesis(agentId: string) {
  if (!debate.value || thesisRegeneratingAgentIds.value.includes(agentId)) return
  if (thesisRegenerationLocked.value) return

  thesisRegeneratingAgentIds.value = [...thesisRegeneratingAgentIds.value, agentId]

  try {
    debate.value = await $fetch<DebateState>(
      `${config.public.aiDebateApiUrl}/debates/${debateId.value}/theses/${agentId}/regenerate`,
      {
        method: 'POST'
      }
    )
  } catch (error) {
    toast.add({
      color: 'error',
      icon: 'i-ph-warning',
      title: 'Thesis was not regenerated',
      description:
        error instanceof Error
          ? error.message
          : 'The debate API rejected the thesis regeneration.'
    })
  } finally {
    thesisRegeneratingAgentIds.value = thesisRegeneratingAgentIds.value.filter(id => id !== agentId)
  }
}
</script>

<template>
  <div class="debate-print-page contents">
    <UDashboardPanel
      id="debate-detail"
      class="debate-print-panel relative h-full min-h-0"
      :ui="{ body: 'flex h-full min-h-0 flex-col p-0 sm:p-0 overscroll-none' }"
    >
      <template #header>
        <Navbar class="debate-screen-only">
          <template #title>
            <div
              class="inline-flex h-8 max-w-full items-center gap-2 rounded-md bg-default/30 px-2.5 text-md font-semibold text-foreground backdrop-blur-md"
            >
              <span class="min-w-0 truncate">{{ debate?.title ?? "Debate" }}</span>
              <UBadge
                size="sm"
                variant="soft"
                color="neutral"
                class="shrink-0 capitalize"
              >
                {{ phaseLabel }}
              </UBadge>
            </div>
          </template>
        </Navbar>
      </template>

      <template #body>
        <div class="debate-print-body relative flex h-full min-h-0 flex-col">
          <div
            class="debate-print-scroll min-h-0 flex-1 overflow-y-auto pt-16"
            :class="activeConsensusProposal ? 'pb-40' : 'pb-28'"
          >
            <div
              class="debate-print-content mx-auto grid w-full max-w-4xl gap-5 px-4 sm:px-6 lg:px-8"
            >
              <div v-if="!hasMounted || pending" class="grid gap-3">
                <USkeleton class="h-20 w-full rounded-md" />
                <USkeleton class="h-48 w-full rounded-md" />
                <USkeleton class="h-36 w-full rounded-md" />
              </div>

              <UAlert
                v-else-if="error"
                color="error"
                variant="soft"
                icon="i-ph-warning"
                title="Debate failed to load"
                description="Check that the Python API server is running and that this debate id exists."
              />

              <template v-else-if="debate">
                <section
                  class="debate-screen-only grid gap-4 rounded-md border border-default bg-default/55 p-4"
                >
                  <div
                    class="flex min-w-0 flex-wrap items-start justify-between gap-3"
                  >
                    <div class="min-w-0 flex-1">
                      <h2
                        class="truncate font-brand-serif text-base font-semibold text-highlighted"
                      >
                        {{ debate.title }}
                      </h2>
                      <DebateMarkdown
                        :content="debate.user_prompt"
                        :agents="transcriptAgents"
                      />
                    </div>
                  </div>

                  <div class="flex min-w-0 flex-wrap items-center gap-2">
                    <span class="text-xs font-medium text-muted">
                      Permissions
                    </span>
                    <UBadge
                      v-for="permission in permissionBadges"
                      :key="permission.key"
                      size="sm"
                      variant="soft"
                      :color="permission.color"
                      class="shrink-0"
                    >
                      <UIcon :name="permission.icon" class="size-3.5" />
                      {{ permission.label }}
                    </UBadge>
                  </div>

                  <div class="flex min-w-0 flex-wrap items-center gap-2">
                    <span class="text-xs font-medium text-muted">
                      Participants
                    </span>
                    <button
                      v-for="agent in transcriptAgents"
                      :key="agent.id"
                      type="button"
                      class="inline-flex min-w-20 items-center justify-center rounded-md px-2.5 py-1.5 text-center ring ring-default transition-colors hover:bg-accented/60"
                      :class="
                        debate.next_agent === agent.id
                          ? agentColor(agent.color).softClass
                          : 'bg-default/40'
                      "
                      @click="openAgentProfile(agent.id)"
                    >
                      <span
                        class="truncate font-brand-serif text-sm font-semibold leading-5"
                        :class="agentColor(agent.color).textClass"
                      >
                        @{{ agent.id }}
                      </span>
                    </button>
                  </div>
                </section>

                <div class="debate-screen-only">
                  <DebateThesisJobs
                    :state="debate"
                    :agents="transcriptAgents"
                    :streams="thesisStreams"
                    :regenerating-agent-ids="thesisRegeneratingAgentIds"
                    :can-share="debate.phase === 'theses_ready' && !debate.auto_mode"
                    :share-pending="actionPending"
                    @regenerate="regenerateThesis"
                    @share="advanceDebate"
                  />
                </div>

                <DebateTranscript
                  class="debate-print-transcript"
                  :agents="transcriptAgents"
                  :messages="transcriptMessages"
                  @open-agent="openAgentProfile"
                />

                <div class="debate-screen-only">
                  <DebateFinalDocument
                    :state="debate"
                    :agents="transcriptAgents"
                    :contents="finalArtifactContents"
                    :loading-paths="finalArtifactLoadingPaths"
                  />
                </div>

                <div
                  v-if="(nextAction && nextAction.endpoint !== 'share-theses') || debate.rounds.length"
                  class="debate-screen-only grid min-w-0 grid-cols-[1fr_auto_1fr] items-center pb-2"
                >
                  <div class="col-start-2 justify-self-center">
                    <UButton
                      v-if="showNextActionButton"
                      type="button"
                      size="sm"
                      color="neutral"
                      variant="soft"
                      :icon="nextAction?.icon"
                      :loading="actionPending"
                      :disabled="nextActionDisabled"
                      :class="['h-8', nextActionButtonClasses]"
                      @click="advanceDebate"
                    >
                      <span v-if="nextActionAgent" class="truncate">
                        Run @{{ nextActionAgent.id }}
                      </span>
                      <span v-else>{{ nextAction?.label }}</span>
                    </UButton>
                  </div>

                  <div class="col-start-3 justify-self-end">
                    <UTooltip text="Regenerate latest discussion">
                      <UButton
                        v-if="debate.rounds.length"
                        type="button"
                        size="sm"
                        color="neutral"
                        variant="soft"
                        icon="i-ph-arrow-clockwise"
                        class="h-8"
                        :loading="discussionRegenerating"
                        :disabled="!canRegenerateDiscussion"
                        @click="regenerateDiscussion"
                      >
                        Regenerate
                      </UButton>
                    </UTooltip>
                  </div>
                </div>
              </template>
            </div>
          </div>

          <div
            v-if="hasMounted && !pending && !error && debate"
            class="debate-screen-only pointer-events-none absolute inset-x-0 bottom-0 z-10 mx-auto w-full max-w-4xl px-4 sm:px-6 lg:px-8"
          >
            <div class="pointer-events-auto">
              <div
                v-if="activeConsensusProposal"
                class="mb-1 flex h-8 min-w-0 items-center gap-2 overflow-hidden rounded-md border border-primary/15 bg-primary/5 px-2 text-xs text-toned backdrop-blur-sm"
              >
                <UIcon name="i-ph-handshake" class="size-3.5 shrink-0 text-primary" />
                <span class="shrink-0 font-semibold text-highlighted">
                  Consensus
                </span>
                <span class="hidden shrink-0 text-muted sm:inline">
                  writer
                </span>
                <span class="min-w-0 max-w-36 truncate font-brand-serif font-semibold text-primary">
                  {{ consensusFinalWriterName }}
                </span>
                <div class="min-w-0 flex-1 overflow-x-auto">
                  <div class="flex min-w-max items-center gap-1.5">
                    <span
                      v-for="row in consensusVoteRows"
                      :key="row.agentId"
                      class="inline-flex h-5 max-w-36 items-center gap-1 rounded border px-1.5 font-brand-serif font-semibold leading-none"
                      :class="consensusVoteClasses(row)"
                      :title="`${row.name}: ${row.title}`"
                    >
                      <UIcon :name="row.icon" class="size-3 shrink-0" />
                      <span class="truncate">{{ row.name }}</span>
                    </span>
                  </div>
                </div>
              </div>

              <UChatPrompt
                v-model="messageDraft"
                :status="promptStatus"
                placeholder="Add your opinion to the debate..."
                variant="subtle"
                :disabled="hasQueuedMessage"
                :class="[
                  'rounded-b-none transition-colors',
                  hasQueuedMessage
                    ? 'bg-muted/80 dark:bg-elevated/80 ring-1 ring-default'
                    : ''
                ]"
                :ui="{ base: 'px-1.5 font-brand-serif' }"
                @submit.prevent="submitMessage"
              >
                <template #footer>
                  <div class="flex w-full items-center justify-between gap-2">
                    <UButton
                      type="button"
                      :color="debate.auto_mode ? 'primary' : 'neutral'"
                      :variant="debate.auto_mode ? 'solid' : 'outline'"
                      size="sm"
                      :loading="autoModePending"
                      :title="debate.auto_mode ? 'Stop after current step' : 'Run automatically'"
                      @click="toggleAutoMode"
                    >
                      {{ debate.auto_mode ? "Stop auto" : "Manual mode" }}
                    </UButton>

                    <div class="shrink-0">
                      <UButton
                        v-if="hasQueuedMessage"
                        type="button"
                        icon="i-ph-pencil"
                        color="neutral"
                        variant="soft"
                        size="sm"
                        @click="editQueuedMessage"
                      >
                        Queued
                      </UButton>
                      <UChatPromptSubmit
                        v-else
                        :status="promptStatus"
                        color="neutral"
                        size="sm"
                        :loading="sendingMessage"
                        loading-icon="i-lucide-loader-circle"
                        :disabled="!canSendMessage"
                      />
                    </div>
                  </div>
                </template>
              </UChatPrompt>
            </div>
          </div>
        </div>
      </template>
    </UDashboardPanel>
  </div>
</template>
