<script setup lang="ts">
import NewDebateAgentEditor from '~/components/debate/NewDebateAgentEditor.vue'
import NewDebateAgentList from '~/components/debate/NewDebateAgentList.vue'
import NewDebateMcpManager from '~/components/debate/NewDebateMcpManager.vue'
import NewDebatePermissions from '~/components/debate/NewDebatePermissions.vue'
import NewDebateTopicForm from '~/components/debate/NewDebateTopicForm.vue'
import type { DebateAgentDraft, DebateDiscussion, DebateDiscussionSelectItem, LlmProvidersResponse } from '~/types/debate'
import type { DebateState } from '~/types/debate-state'
import { agentColorOptions } from '~/utils/debate-config'

type AgentDropPosition = 'before' | 'after'

const config = useRuntimeConfig()
const toast = useToast()
const providerCatalogFailureToastShown = ref(false)
const {
  data: providerCatalog,
  error: providerCatalogError,
  pending: providerCatalogPending
} = useFetch<LlmProvidersResponse>(
  `${config.public.aiDebateApiUrl}/llms/providers`,
  {
    server: false
  }
)

const {
  title,
  topic,
  workingDirectory,
  allowFileRead,
  allowProbeCommands,
  allowWebEvidence
} = useDebateDraft()
const selectedAgentId = ref('codex1')
const draggingAgentId = ref<string | null>(null)
const dragOverAgentId = ref<string | null>(null)
const dragOverPosition = ref<AgentDropPosition>('before')
const selectedImportDiscussionId = ref<string | null>(null)
const hasMounted = ref(false)
const creatingDebate = ref(false)
const importingAgents = ref(false)
const agents = useDebateAgents()
const {
  data: discussions,
  pending: discussionsPending,
  refresh: refreshDiscussions
} = useFetch<DebateDiscussion[]>(
  `${config.public.aiDebateApiUrl}/discussions`,
  {
    key: 'debate-discussions',
    server: false,
    default: () => []
  }
)

const providers = computed(() => providerCatalog.value?.providers ?? {})
const providerItems = computed(() =>
  Object.values(providers.value).map(provider => ({
    label: provider.label,
    value: provider.id
  }))
)
const modelCatalogReady = computed(
  () => Object.keys(providers.value).length > 0 && !providerCatalogError.value
)
const activeAgent = computed(
  () =>
    agents.value.find(agent => agent.id === selectedAgentId.value)
    ?? agents.value[0]
)
const activeProvider = computed(() =>
  activeAgent.value ? providers.value[activeAgent.value.provider] : undefined
)
const activeModelItems = computed(() => {
  const provider = activeProvider.value
  if (!provider) return []

  return provider.models.map(model => ({
    label: model.default ? `${model.label} (default)` : model.label,
    value: model.id
  }))
})
const showProviderCatalogLoading = computed(
  () => hasMounted.value && providerCatalogPending.value
)
const modelCatalogDisabled = computed(() => hasMounted.value && !modelCatalogReady.value)
const importDiscussionItems = computed<DebateDiscussionSelectItem[]>(() =>
  (discussions.value ?? []).map(discussion => ({
    label: discussion.title || discussion.id,
    value: discussion.id,
    description: `${discussion.agent_count} agents · ${discussion.updated_at.replace('T', ' ').slice(0, 16)}`
  }))
)
const thesisAgentCount = computed(
  () => agents.value.filter(agent => agent.writeThesis).length
)
const canCreateDebate = computed(() =>
  Boolean(
    title.value.trim()
    && topic.value.trim()
    && thesisAgentCount.value > 0
    && modelCatalogReady.value
    && !creatingDebate.value
  )
)

onMounted(() => {
  hasMounted.value = true
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

watch(
  providerCatalog,
  () => {
    applyProviderDefaults()
  },
  { immediate: true }
)

function addAgent() {
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

  const id = nextAgentId()
  const color
    = agentColorOptions[agents.value.length % agentColorOptions.length]!.value
  const agent = createDebateAgentSetup({
    id,
    displayName: 'New Agent',
    provider: defaultProvider.id,
    color,
    model: defaultProvider.default_model
  })

  agents.value.push(agent)
  selectedAgentId.value = agent.id
}

async function importAgentsFromDiscussion() {
  const discussionId = selectedImportDiscussionId.value
  if (!discussionId || importingAgents.value) return

  importingAgents.value = true
  try {
    const debate = await $fetch<DebateState>(
      `${config.public.aiDebateApiUrl}/debates/${discussionId}`
    )
    const importedAgents = debateAgentDraftsFromState(debate)
    if (importedAgents.length < 2) {
      throw new Error('The selected discussion does not have enough agents to import.')
    }
    agents.value = importedAgents
    selectedAgentId.value = importedAgents[0]?.id ?? ''
    toast.add({
      title: 'Agent setup loaded',
      description: `Imported ${importedAgents.length} agents from ${debate.title}.`,
      color: 'success',
      icon: 'i-ph-check'
    })
  } catch (error) {
    toast.add({
      title: 'Agent setup was not loaded',
      description:
        error instanceof Error
          ? error.message
          : 'The Python API could not load that discussion.',
      color: 'error',
      icon: 'i-ph-warning'
    })
  } finally {
    importingAgents.value = false
  }
}

function removeAgent(id: string) {
  if (agents.value.length <= 1) return

  agents.value = agents.value.filter(agent => agent.id !== id)
  if (selectedAgentId.value === id) {
    selectedAgentId.value = agents.value[0]?.id ?? ''
  }
}

function updateAgent(updatedAgent: DebateAgentDraft) {
  const index = agents.value.findIndex(agent => agent.id === updatedAgent.id)
  if (index !== -1) {
    agents.value[index] = {
      ...agents.value[index]!,
      ...updatedAgent
    }
  }
}

function setAgentProvider(value: unknown) {
  const provider
    = typeof value === 'string'
      ? value
      : value && typeof value === 'object' && 'value' in value
        ? String(value.value)
        : ''

  if (!activeAgent.value || !provider || !providers.value[provider]) return

  updateAgent({
    ...activeAgent.value,
    provider,
    model: providers.value[provider]?.default_model ?? ''
  })
}

function applyProviderDefaults() {
  if (!modelCatalogReady.value) return

  agents.value = agents.value.map((agent) => {
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
}

function nextAgentId() {
  let index = agents.value.length + 1
  let id = `agent${index}`

  while (
    agents.value.some(agent => agent.id === id || agent.mentionName === id)
  ) {
    index += 1
    id = `agent${index}`
  }

  return id
}

function handleAgentDragStart(event: DragEvent, agentId: string) {
  draggingAgentId.value = agentId
  event.dataTransfer?.setData('text/plain', agentId)
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move'
  }
}

function handleAgentDragOver(agentId: string, position: AgentDropPosition) {
  if (draggingAgentId.value && draggingAgentId.value !== agentId) {
    dragOverAgentId.value = agentId
    dragOverPosition.value = position
  }
}

function handleAgentDragLeave(agentId: string) {
  if (dragOverAgentId.value === agentId) {
    dragOverAgentId.value = null
  }
}

function handleAgentDrop(agentId: string, position: AgentDropPosition) {
  const sourceId = draggingAgentId.value
  if (sourceId && sourceId !== agentId) {
    moveAgent(sourceId, agentId, position)
  }
  handleAgentDragEnd()
}

function handleAgentDragEnd() {
  draggingAgentId.value = null
  dragOverAgentId.value = null
  dragOverPosition.value = 'before'
}

function moveAgent(
  sourceId: string,
  targetId: string,
  position: AgentDropPosition
) {
  const sourceIndex = agents.value.findIndex(agent => agent.id === sourceId)
  if (sourceIndex === -1) return

  const [movedAgent] = agents.value.splice(sourceIndex, 1)
  if (!movedAgent) return

  const targetIndex = agents.value.findIndex(agent => agent.id === targetId)
  const insertIndex
    = targetIndex === -1
      ? agents.value.length
      : targetIndex + (position === 'after' ? 1 : 0)

  agents.value.splice(insertIndex, 0, movedAgent)
}

function resetDebateDraft() {
  resetDebateDraftState()
}

async function createDebate() {
  if (!canCreateDebate.value) return

  creatingDebate.value = true

  try {
    const debate = await $fetch<DebateState>(
      `${config.public.aiDebateApiUrl}/debates`,
      {
        method: 'POST',
        body: {
          title: title.value.trim(),
          user_prompt: topic.value.trim(),
          allow_file_read: allowFileRead.value,
          allow_probe_commands: allowFileRead.value && allowProbeCommands.value,
          allow_web_evidence: allowWebEvidence.value,
          working_directory: workingDirectory.value.trim() || undefined,
          agents: agents.value.map(agent => ({
            name: agent.mentionName || agent.id,
            provider: agent.provider,
            model: agent.model || undefined,
            display_name: agent.displayName,
            color: agent.color,
            write_thesis: agent.writeThesis,
            debate_style: agent.debateStyle,
            technical_preference: agent.technicalPreference,
            additional_note: agent.note
          }))
        }
      }
    )
    const discussionsCache = useNuxtData<DebateDiscussion[]>('debate-discussions')
    if (discussionsCache.data.value) {
      discussionsCache.data.value = [
        {
          id: debate.id,
          title: debate.title,
          phase: debate.phase,
          created_at: debate.created_at,
          updated_at: debate.updated_at,
          agent_count: Object.keys(debate.agents).length,
          turn_count: debate.rounds.length,
          has_consensus: Boolean(debate.consensus)
        },
        ...discussionsCache.data.value.filter(discussion => discussion.id !== debate.id)
      ]
    }
    await navigateTo(`/debate/${debate.id}`)
  } catch (error) {
    toast.add({
      title: 'Debate was not created',
      description:
        error instanceof Error
          ? error.message
          : 'The Python API rejected the debate setup.',
      color: 'error',
      icon: 'i-ph-warning'
    })
  } finally {
    creatingDebate.value = false
  }
}

definePageMeta({
  layout: 'chat'
})
</script>

<template>
  <UDashboardPanel
    id="new-debate"
    class="relative min-h-0"
    :ui="{ body: 'p-0 sm:p-0 overscroll-none' }"
  >
    <template #header>
      <Navbar>
        <template #title>
          <div
            class="inline-flex h-8 max-w-full items-center rounded-md bg-default/30 px-2.5 text-md font-semibold text-foreground backdrop-blur-md"
          >
            <span class="truncate">New Debate</span>
          </div>
        </template>
      </Navbar>
    </template>

    <template #body>
      <div
        class="min-h-0 flex-1 overflow-y-auto px-4 pb-6 pt-16 sm:px-6 lg:px-8"
      >
        <div class="mx-auto grid w-full max-w-6xl gap-5">
          <section
            class="grid gap-4 border-b border-default pb-5 lg:grid-cols-[minmax(0,1fr)_20rem]"
          >
            <ClientOnly>
              <NewDebateTopicForm v-model:title="title" v-model:topic="topic" />
              <template #fallback>
                <div class="flex h-full min-h-0 flex-col gap-3">
                  <USkeleton class="h-14 w-full rounded-md" />
                  <USkeleton class="min-h-44 flex-1 rounded-md" />
                </div>
              </template>
            </ClientOnly>
            <NewDebatePermissions
              v-model:working-directory="workingDirectory"
              v-model:allow-file-read="allowFileRead"
              v-model:allow-probe-commands="allowProbeCommands"
              v-model:allow-web-evidence="allowWebEvidence"
            />
          </section>

          <ClientOnly>
            <NewDebateMcpManager />
            <template #fallback>
              <section class="grid gap-3 border-b border-default pb-4">
                <USkeleton class="h-10 w-full rounded-md" />
              </section>
            </template>
          </ClientOnly>

          <section
            class="grid min-h-[26rem] gap-4 lg:grid-cols-[18rem_minmax(0,1fr)]"
          >
            <NewDebateAgentList
              :agents="agents"
              :selected-agent-id="selectedAgentId"
              :thesis-agent-count="thesisAgentCount"
              :dragging-agent-id="draggingAgentId"
              :drag-over-agent-id="dragOverAgentId"
              :drag-over-position="dragOverPosition"
              :model-catalog-disabled="modelCatalogDisabled"
              :import-discussions="importDiscussionItems"
              :selected-import-discussion-id="selectedImportDiscussionId"
              :import-pending="discussionsPending"
              :importing-agents="importingAgents"
              @add="addAgent"
              @update:selected-import-discussion-id="selectedImportDiscussionId = $event"
              @load-agents="importAgentsFromDiscussion"
              @refresh-imports="refreshDiscussions"
              @select="selectedAgentId = $event"
              @drag-start="handleAgentDragStart"
              @drag-over="handleAgentDragOver"
              @drag-leave="handleAgentDragLeave"
              @drop="handleAgentDrop"
              @drag-end="handleAgentDragEnd"
            />

            <NewDebateAgentEditor
              v-if="hasMounted && activeAgent"
              :key="activeAgent.id"
              :agent="activeAgent"
              :agents-count="agents.length"
              :provider-items="providerItems"
              :model-items="activeModelItems"
              :model-loading="showProviderCatalogLoading"
              :model-catalog-disabled="modelCatalogDisabled"
              @update:agent="updateAgent"
              @provider-change="setAgentProvider"
              @remove="removeAgent"
            />
          </section>

          <div class="flex w-full items-center justify-end gap-2">
            <UButton color="neutral" variant="ghost" @click="resetDebateDraft">
              Reset
            </UButton>
            <UButton
              icon="i-ph-play"
              :disabled="!canCreateDebate"
              :loading="creatingDebate"
              @click="createDebate"
            >
              Create Debate
            </UButton>
          </div>
        </div>
      </div>
    </template>
  </UDashboardPanel>
</template>
