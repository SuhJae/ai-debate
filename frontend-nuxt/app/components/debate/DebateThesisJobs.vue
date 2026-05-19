<script setup lang="ts">
import DebateMarkdown from '~/components/debate/DebateMarkdown.vue'
import DebateToolSections from '~/components/debate/DebateToolSections.vue'
import type { StreamingMessage } from '~/composables/useDebateStream'
import type { DebateChatAgent, DebateToolEvent } from '~/types/debate-chat'
import type { AgentState, DebateState, ThesisRecord } from '~/types/debate-state'
import { agentColor } from '~/utils/debate-config'
import { artifactTool, evidenceTools, thesisToMarkdown } from '~/utils/debate-transcript'

type ThesisJob = {
  agentId: string
  agent: AgentState
  chatAgent?: DebateChatAgent
  thesis?: ThesisRecord
  stream?: StreamingMessage
  status: 'pending' | 'running' | 'done' | 'failed' | 'skipped'
  tools: DebateToolEvent[]
}

const props = defineProps<{
  state: DebateState
  agents: DebateChatAgent[]
  streams?: Record<string, StreamingMessage>
  regeneratingAgentIds?: string[]
  canShare?: boolean
  sharePending?: boolean
}>()

const emit = defineEmits<{
  regenerate: [agentId: string]
  share: []
}>()

const selectedAgentId = ref<string | null>(null)
const detailOpen = ref(false)

const agentById = computed(() => new Map(props.agents.map(agent => [agent.id, agent])))
const evidenceById = computed(() => new Map(props.state.shared_evidence.map(evidence => [evidence.id, evidence])))
const orderedAgentIds = computed(() => [
  ...props.state.turn_order.filter(agentId => props.state.agents[agentId]),
  ...Object.keys(props.state.agents).filter(agentId => !props.state.turn_order.includes(agentId))
])
const thesisJobs = computed<ThesisJob[]>(() =>
  orderedAgentIds.value
    .map(agentId => [agentId, props.state.agents[agentId]!] as const)
    .filter(([, agent]) => agent.write_thesis)
    .map(([agentId, agent]) => {
      const thesis = props.state.theses[agentId]
      const stream = props.streams?.[agentId]
      const tools = thesis
        ? [
            artifactTool(thesis.artifact_path, 'Initial thesis artifact'),
            ...evidenceTools(thesis.evidence_refs, evidenceById.value)
          ]
        : []

      return {
        agentId,
        agent,
        chatAgent: agentById.value.get(agentId),
        thesis,
        stream,
        status: getThesisStatus(agent, thesis, stream),
        tools
      }
    })
)
const selectedJob = computed(() =>
  thesisJobs.value.find(job => job.agentId === selectedAgentId.value) ?? null
)
const thesisRegenerationLocked = computed(() =>
  props.state.rounds.length > 0
  || [
    'debating',
    'paused',
    'consensus_reached',
    'drafting_final',
    'reviewing_final',
    'revising_final',
    'accepted'
  ].includes(props.state.phase)
)

function getThesisStatus(
  agent: AgentState,
  thesis?: ThesisRecord,
  stream?: StreamingMessage
): ThesisJob['status'] {
  if (!agent.write_thesis) return 'skipped'
  if (thesis) return 'done'
  if (agent.status === 'running' || stream?.active) return 'running'
  if (agent.status === 'failed' || agent.last_error) return 'failed'
  return 'pending'
}

function statusColor(status: ThesisJob['status']) {
  if (status === 'done') return 'success'
  if (status === 'running') return 'info'
  if (status === 'failed') return 'error'
  return 'neutral'
}

function statusText(status: ThesisJob['status']) {
  if (status === 'done') return 'done'
  if (status === 'running') return 'working'
  if (status === 'failed') return 'error'
  if (status === 'skipped') return 'skipped'
  return 'waiting'
}

function agentName(job: ThesisJob) {
  return job.agent.display_name || job.chatAgent?.name || job.agentId
}

function streamPreview(content?: string) {
  if (!content?.trim()) return ''
  return content
    .split(/\r?\n/)
    .map(line => line.trim())
    .filter(Boolean)
    .slice(-2)
    .join('\n')
}

function openJob(job: ThesisJob) {
  selectedAgentId.value = job.agentId
  detailOpen.value = true
}

function canRegenerateJob(job: ThesisJob) {
  return !thesisRegenerationLocked.value && job.status !== 'running'
}

function showRegenerateJob(job: ThesisJob) {
  return job.status !== 'running' && !props.regeneratingAgentIds?.includes(job.agentId)
}

function regenerateTooltip(job: ThesisJob) {
  if (thesisRegenerationLocked.value) return 'Thesis sharing has already started'
  if (job.status === 'running') return 'Thesis is generating'
  return 'Regenerate thesis'
}

function regenerateJob(job: ThesisJob) {
  if (!canRegenerateJob(job)) return
  emit('regenerate', job.agentId)
}
</script>

<template>
  <section v-if="thesisJobs.length" class="grid gap-3">
    <div class="flex min-w-0 items-center justify-between gap-3">
      <h2 class="text-sm font-semibold text-highlighted">
        Initial Theses
      </h2>
      <UBadge size="sm" variant="soft" color="neutral">
        parallel
      </UBadge>
    </div>

    <div class="grid gap-2 sm:grid-cols-2">
      <div
        v-for="job in thesisJobs"
        :key="job.agentId"
        role="button"
        tabindex="0"
        class="grid h-42 min-w-0 cursor-pointer grid-rows-[auto_1fr_auto] gap-3 rounded-md border border-default bg-default/45 p-3 text-left transition-colors hover:bg-accented/45 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary"
        @click="openJob(job)"
        @keydown.enter.prevent="openJob(job)"
        @keydown.space.prevent="openJob(job)"
      >
        <div class="flex min-w-0 items-center gap-2">
          <span
            class="size-2.5 shrink-0 rounded-full ring-2 ring-default"
            :class="agentColor(job.chatAgent?.color).swatchClass"
          />
          <span
            class="min-w-0 flex-1 truncate font-brand-serif text-sm font-semibold"
            :class="agentColor(job.chatAgent?.color).textClass"
          >
            {{ agentName(job) }}
          </span>
          <UBadge size="sm" variant="soft" :color="statusColor(job.status)">
            {{ statusText(job.status) }}
          </UBadge>
        </div>

        <div class="min-h-0 min-w-0 overflow-hidden">
          <div v-if="job.thesis" class="grid h-full grid-rows-[1.25rem_2.5rem] gap-1">
            <p class="truncate text-sm font-medium leading-5 text-highlighted">
              {{ job.thesis.decision }}
            </p>
            <p class="line-clamp-2 text-sm leading-5 text-muted">
              {{ job.thesis.position }}
            </p>
          </div>
          <div
            v-else-if="streamPreview(job.stream?.content)"
            class="grid h-full min-w-0 grid-rows-[1rem_2.5rem] gap-1 overflow-hidden rounded-md bg-info/5 p-2 ring ring-info/15"
          >
            <div class="flex min-w-0 items-center gap-1.5 text-xs font-medium leading-4 text-info">
              <UIcon
                name="i-ph-spinner-gap"
                class="size-3.5 shrink-0"
                :class="job.stream?.active ? 'animate-spin' : ''"
              />
              <span class="truncate">{{ job.stream?.active ? 'Live activity' : 'Latest activity' }}</span>
            </div>
            <p class="line-clamp-2 whitespace-pre-wrap font-mono text-xs leading-5 text-toned">
              {{ streamPreview(job.stream?.content) }}
            </p>
          </div>
          <p
            v-else-if="job.agent.last_error"
            class="line-clamp-2 text-sm leading-5 text-error"
          >
            {{ job.agent.last_error }}
          </p>
          <p v-else class="line-clamp-2 text-sm leading-5 text-muted">
            Waiting for this agent to finish its independent thesis.
          </p>
        </div>

        <div class="flex h-7 min-w-0 items-center justify-between gap-2">
          <div class="flex h-7 min-w-0 flex-1 items-center gap-1.5 overflow-hidden">
            <UBadge size="sm" variant="soft" color="neutral">
              {{ job.agent.provider }}
            </UBadge>
            <UBadge
              v-if="job.agent.model"
              size="sm"
              variant="soft"
              color="neutral"
            >
              {{ job.agent.model }}
            </UBadge>
            <UBadge
              v-if="job.tools.length"
              size="sm"
              variant="soft"
              color="neutral"
            >
              {{ job.tools.length }} tools
            </UBadge>
          </div>

          <UTooltip
            v-if="showRegenerateJob(job)"
            :text="regenerateTooltip(job)"
          >
            <UButton
              type="button"
              icon="i-ph-arrow-clockwise"
              size="xs"
              color="neutral"
              variant="ghost"
              aria-label="Regenerate thesis"
              :loading="regeneratingAgentIds?.includes(job.agentId)"
              :disabled="!canRegenerateJob(job)"
              @click.stop="regenerateJob(job)"
            />
          </UTooltip>
        </div>
      </div>
    </div>

    <div
      v-if="canShare"
      class="flex min-w-0 justify-center pt-1"
    >
      <UButton
        type="button"
        icon="i-ph-share-network"
        :loading="sharePending"
        @click="emit('share')"
      >
        Share theses
      </UButton>
    </div>
  </section>

  <UModal
    :open="detailOpen"
    :title="selectedJob ? `${agentName(selectedJob)} Thesis` : 'Thesis Detail'"
    :description="selectedJob ? `@${selectedJob.agentId} · ${statusText(selectedJob.status)}` : undefined"
    :ui="{ content: 'max-w-3xl overflow-hidden' }"
    @update:open="detailOpen = $event"
  >
    <template #body>
      <div v-if="selectedJob" class="grid min-w-0 gap-4 overflow-hidden">
        <div class="flex min-w-0 flex-wrap gap-2">
          <UBadge size="sm" variant="soft" :color="statusColor(selectedJob.status)">
            {{ statusText(selectedJob.status) }}
          </UBadge>
          <UBadge size="sm" variant="soft" color="neutral">
            {{ selectedJob.agent.provider }}
          </UBadge>
          <UBadge
            v-if="selectedJob.agent.model"
            size="sm"
            variant="soft"
            color="neutral"
          >
            {{ selectedJob.agent.model }}
          </UBadge>
        </div>

        <UAlert
          v-if="selectedJob.agent.last_error"
          color="error"
          variant="soft"
          icon="i-ph-warning"
          title="Generation error"
          :description="selectedJob.agent.last_error"
        />

        <div v-if="selectedJob.thesis" class="grid min-w-0 gap-3">
          <DebateMarkdown
            :content="thesisToMarkdown(selectedJob.thesis)"
            :agents="agents"
            :tools="selectedJob.tools"
          />
        </div>
        <div
          v-else-if="selectedJob.stream?.content"
          class="grid min-w-0 gap-3"
        >
          <div class="flex min-w-0 items-center justify-between gap-3">
            <div class="text-sm font-semibold text-highlighted">
              Live Agent Activity
            </div>
            <UBadge
              size="sm"
              variant="soft"
              :color="selectedJob.stream.active ? 'info' : 'neutral'"
            >
              {{ selectedJob.stream.active ? 'streaming' : 'captured' }}
            </UBadge>
          </div>
          <div
            class="max-h-[60vh] min-w-0 overflow-y-auto rounded-md border border-default bg-default/45 p-3"
          >
            <DebateMarkdown
              :content="selectedJob.stream.content"
              :agents="agents"
              :tools="selectedJob.tools"
            />
          </div>
        </div>
        <UAlert
          v-else
          color="neutral"
          variant="soft"
          icon="i-ph-info"
          title="No thesis output yet"
          description="This agent has not submitted a validated thesis record."
        />

        <div class="grid min-w-0 gap-2">
          <div class="text-sm font-semibold text-highlighted">
            Tool Calls And Evidence
          </div>
          <DebateToolSections :tools="selectedJob.tools" />
          <p v-if="!selectedJob.tools.length" class="text-sm text-muted">
            No artifact, evidence, or tool-call records are available for this thesis.
          </p>
        </div>
      </div>
    </template>
  </UModal>
</template>
