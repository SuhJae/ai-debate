<script setup lang="ts">
import DebateMarkdown from '~/components/debate/DebateMarkdown.vue'
import DebateToolSections from '~/components/debate/DebateToolSections.vue'
import type { DebateChatAgent, DebateChatMessage, DebateToolEvent } from '~/types/debate-chat'
import { agentColor } from '~/utils/debate-config'

const props = defineProps<{
  agents: DebateChatAgent[]
  messages: DebateChatMessage[]
}>()

const emit = defineEmits<{
  openAgent: [agentId: string]
}>()

const selectedEvidence = ref<DebateToolEvent | null>(null)
const highlightedConsensusId = ref<string | null>(null)
const agentById = computed(() => new Map(props.agents.map(agent => [agent.id, agent])))

function getAgent(message: DebateChatMessage) {
  return message.agentId ? agentById.value.get(message.agentId) : undefined
}

function getDisplayName(message: DebateChatMessage) {
  if (message.role === 'user') return 'You'
  if (message.role === 'notice') return 'Shared source'
  return getAgent(message)?.name ?? message.agentId ?? 'Agent'
}

function getProvider(message: DebateChatMessage) {
  if (message.role === 'notice') return 'notice'
  if (message.role !== 'agent') return message.role
  return getAgent(message)?.provider ?? 'agent'
}

function getFaction(message: DebateChatMessage) {
  const agent = getAgent(message)
  if (message.role !== 'agent' || agent?.debateStyle !== 'politician') return null
  if (agent.technicalPreference === 'left') return 'left'
  if (agent.technicalPreference === 'right') return 'right'
  return 'independent'
}

function getFactionColor(faction: string | null) {
  if (faction === 'left') return agentColor('joseon')
  if (faction === 'right') return agentColor('celadon')
  return agentColor('slate')
}

function getMessageAccent(message: DebateChatMessage) {
  if (message.role === 'user') return 'joseon'
  if (message.role === 'notice') return 'slate'
  return getAgent(message)?.color
}

function messageAlignmentClass(message: DebateChatMessage) {
  return message.role === 'user' ? 'justify-end' : 'justify-start'
}

function messageStackClass(message: DebateChatMessage) {
  if (message.role === 'system') return 'w-full'
  if (message.role === 'notice') return 'w-full max-w-3xl'
  if (message.role !== 'user') return 'w-full'

  return 'max-w-[88%] items-stretch'
}

function articleSpacingClass(message: DebateChatMessage) {
  if (message.role === 'agent') return 'pt-5'
  if (message.role === 'system') return 'py-1'
  if (message.role === 'notice') return 'py-1'
  return ''
}

function systemIconName(message: DebateChatMessage) {
  if (message.systemKind === 'consensus_rejected') return 'i-ph-x-circle'
  if (message.systemKind === 'consensus_withdrawn') return 'i-ph-arrow-counter-clockwise'
  if (message.systemKind === 'consensus_reached') return 'i-ph-gavel'
  if (message.systemKind === 'consensus_accepted') return 'i-ph-check-circle'
  if (message.systemKind === 'consensus_proposed') return 'i-ph-handshake'

  const content = message.content.toLowerCase()

  if (content.includes('consensus rejected')) return 'i-ph-x-circle'
  if (content.includes('consensus withdrawn')) return 'i-ph-arrow-counter-clockwise'
  if (content.includes('consensus accepted') || content.includes('consensus reached')) return 'i-ph-check-circle'
  if (content.includes('consensus proposed')) return 'i-ph-handshake'
  return 'i-ph-info'
}

function openEvidenceCitation(citationId: string, message: DebateChatMessage) {
  const tool = findCitationTool(citationId, message.citations ?? message.tools ?? [])
  if (tool?.kind === 'consensus') {
    jumpToConsensusBlock(tool.proposalId ?? normalizedToolId(tool))
    return
  }
  if (tool) selectedEvidence.value = tool
}

function findCitationTool(citationId: string, tools: DebateToolEvent[]) {
  const normalized = citationId.toLowerCase()

  return tools.find((tool) => {
    const ids = [tool.id, tool.proposalId]
    if (tool.id.startsWith('tool-')) ids.push(tool.id.slice(5))
    return ids.some(id => id?.toLowerCase() === normalized)
  }) ?? null
}

function normalizedToolId(tool: DebateToolEvent) {
  return tool.id.startsWith('tool-') ? tool.id.slice(5) : tool.id
}

function consensusBlockDomId(consensusId: string) {
  return `consensus-block-${consensusId.replace(/[^A-Za-z0-9_-]/g, '-')}`
}

function consensusArticleId(message: DebateChatMessage) {
  if (message.systemKind !== 'consensus_proposed' || !message.consensusProposalId) return undefined
  return consensusBlockDomId(message.consensusProposalId)
}

function consensusArticleData(message: DebateChatMessage) {
  return message.consensusProposalId ?? undefined
}

function consensusHighlightClass(message: DebateChatMessage) {
  return message.consensusProposalId && highlightedConsensusId.value === message.consensusProposalId
    ? 'rounded-md bg-primary/10 ring-2 ring-primary/35 ring-offset-2 ring-offset-default transition'
    : ''
}

function jumpToConsensusBlock(consensusId: string) {
  const target = document.getElementById(consensusBlockDomId(consensusId))
    ?? document.querySelector(`[data-consensus-id="${consensusId}"]`)

  if (!(target instanceof HTMLElement)) return

  selectedEvidence.value = null
  highlightedConsensusId.value = consensusId
  target.scrollIntoView({ behavior: 'smooth', block: 'center' })

  window.setTimeout(() => {
    if (highlightedConsensusId.value === consensusId) highlightedConsensusId.value = null
  }, 1800)
}

function evidenceKindLabel(tool: DebateToolEvent) {
  if (tool.kind === 'file_evidence') return 'File evidence'
  if (tool.kind === 'terminal_probe') return 'Terminal probe'
  if (tool.kind === 'web_evidence') return 'Web evidence'
  if (tool.kind === 'mcp_proposal') return 'Shared source'
  if (tool.kind === 'consensus') return 'Consensus'
  return 'Evidence'
}

function evidenceLineLabel(tool: DebateToolEvent) {
  if (!tool.path) return ''
  if (!tool.lineStart) return tool.path
  if (!tool.lineEnd || tool.lineEnd === tool.lineStart) return `${tool.path}:${tool.lineStart}`
  return `${tool.path}:${tool.lineStart}-${tool.lineEnd}`
}

function streamPreviewTitle(message: DebateChatMessage) {
  return message.createdAt === 'streaming' ? 'Generating' : 'Latest activity'
}
</script>

<template>
  <section class="grid gap-4">
    <div class="debate-screen-transcript grid gap-4">
      <article
        v-for="message in messages"
        :id="consensusArticleId(message)"
        :key="message.id"
        :data-consensus-id="consensusArticleData(message)"
        class="group flex min-w-0 flex-col gap-2"
        :class="[articleSpacingClass(message), consensusHighlightClass(message)]"
      >
        <div
          class="flex min-w-0"
          :class="messageAlignmentClass(message)"
        >
          <div
            class="flex min-w-0 flex-col"
            :class="messageStackClass(message)"
          >
            <div
              v-if="message.role === 'user'"
              class="min-w-0 rounded-md bg-elevated px-3.5 py-2.5 ring ring-default"
            >
              <div
                v-if="message.streamPreview"
                class="grid max-w-2xl min-w-0 gap-1 rounded-md bg-info/5 px-2 py-1.5 ring ring-info/15"
              >
                <div class="flex min-w-0 items-center gap-1.5 text-xs font-medium leading-4 text-info">
                  <UIcon name="i-ph-spinner-gap" class="size-3.5 shrink-0 animate-spin" />
                  <span class="truncate">Waiting for model output</span>
                </div>
                <p
                  v-if="message.content"
                  class="line-clamp-2 whitespace-pre-wrap font-mono text-xs leading-5 text-toned"
                >
                  {{ message.content }}
                </p>
              </div>

              <DebateMarkdown
                v-else
                :content="message.content"
                :agents="agents"
                :tools="message.citations ?? message.tools"
                @agent-mention="emit('openAgent', $event)"
                @evidence-citation="openEvidenceCitation($event, message)"
              />
            </div>

            <div
              v-else-if="message.role === 'system'"
              class="min-w-0 rounded-md border border-primary/15 border-l-4 border-l-primary/45 bg-primary/5 px-3.5 py-3 text-sm text-toned shadow-sm shadow-primary/5 dark:bg-primary/10"
            >
              <div class="flex min-w-0 items-start gap-2.5">
                <div class="debate-system-icon mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary ring ring-primary/15">
                  <UIcon :name="systemIconName(message)" class="size-3.5" />
                </div>
                <div class="min-w-0 flex-1">
                  <div class="flex min-w-0 items-start justify-between gap-3">
                    <div class="min-w-0 flex-1">
                      <p
                        v-if="message.systemTitle"
                        class="mb-1 font-brand-serif text-sm font-semibold text-highlighted"
                      >
                        {{ message.systemTitle }}
                      </p>
                      <DebateMarkdown
                        :content="message.content"
                        :agents="agents"
                        :tools="message.citations ?? message.tools"
                        @agent-mention="emit('openAgent', $event)"
                        @evidence-citation="openEvidenceCitation($event, message)"
                      />
                    </div>
                    <time v-if="message.createdAt" class="mt-0.5 shrink-0 text-xs text-muted">
                      {{ message.createdAt }}
                    </time>
                  </div>

                  <DebateToolSections class="mt-2" :tools="message.tools" />
                </div>
              </div>
            </div>

            <div
              v-else-if="message.role === 'notice'"
              class="min-w-0 rounded-md border border-default bg-default/40 px-3.5 py-3 text-sm text-toned"
            >
              <div class="flex min-w-0 items-start justify-between gap-3">
                <DebateMarkdown
                  :content="message.content"
                  :agents="agents"
                  :tools="message.citations ?? message.tools"
                  @agent-mention="emit('openAgent', $event)"
                  @evidence-citation="openEvidenceCitation($event, message)"
                />
                <time v-if="message.createdAt" class="mt-0.5 shrink-0 text-xs text-muted">
                  {{ message.createdAt }}
                </time>
              </div>

              <DebateToolSections class="mt-2" :tools="message.tools" />
            </div>

            <div
              v-else
              class="grid gap-3"
            >
              <header class="flex min-w-0 items-center gap-2">
                <span
                  class="size-2.5 shrink-0 rounded-full ring-2 ring-default"
                  :class="agentColor(getMessageAccent(message)).swatchClass"
                />
                <div class="min-w-0 flex-1">
                  <div class="flex min-w-0 flex-wrap items-center gap-2">
                    <span
                      class="truncate font-brand-serif text-sm font-semibold"
                      :class="agentColor(getMessageAccent(message)).textClass"
                    >
                      {{ getDisplayName(message) }}
                    </span>
                    <UBadge
                      size="sm"
                      variant="soft"
                      color="neutral"
                      class="capitalize"
                    >
                      {{ getProvider(message) }}
                    </UBadge>
                    <UBadge
                      v-if="getFaction(message)"
                      size="sm"
                      variant="soft"
                      color="neutral"
                      class="capitalize"
                      :class="[getFactionColor(getFaction(message)).softClass, getFactionColor(getFaction(message)).textClass]"
                    >
                      {{ getFaction(message) }}
                    </UBadge>
                  </div>
                </div>
                <time v-if="message.createdAt" class="shrink-0 text-xs text-muted">
                  {{ message.createdAt }}
                </time>
              </header>

              <DebateMarkdown
                v-if="!message.streamPreview"
                :content="message.content"
                :agents="agents"
                :tools="message.citations ?? message.tools"
                @agent-mention="emit('openAgent', $event)"
                @evidence-citation="openEvidenceCitation($event, message)"
              />

              <div
                v-else
                class="grid h-16 min-w-0 grid-rows-[1rem_2.5rem] gap-1 overflow-hidden rounded-md bg-info/5 p-2 ring ring-info/15"
              >
                <div class="flex min-w-0 items-center gap-1.5 text-xs font-medium leading-4 text-info">
                  <UIcon
                    name="i-ph-spinner-gap"
                    class="size-3.5 shrink-0"
                    :class="message.createdAt === 'streaming' ? 'animate-spin' : ''"
                  />
                  <span class="truncate">{{ streamPreviewTitle(message) }}</span>
                </div>
                <p class="line-clamp-2 whitespace-pre-wrap font-mono text-xs leading-5 text-toned">
                  {{ message.content }}
                </p>
              </div>

              <DebateToolSections :tools="message.tools" />
            </div>
          </div>
        </div>
      </article>
    </div>

    <div class="debate-print-linear">
      <article
        v-for="message in messages"
        :id="message.systemKind === 'consensus_proposed' && message.consensusProposalId ? `print-${consensusArticleId(message)}` : undefined"
        :key="`print-${message.id}`"
        class="debate-print-message"
        :class="`debate-print-message-${message.role}`"
      >
        <header class="debate-print-message-header">
          <span
            v-if="message.role === 'system'"
            class="debate-print-system-icon"
          >
            <UIcon :name="systemIconName(message)" />
          </span>
          <span
            v-else-if="message.role === 'agent'"
            class="debate-print-agent-swatch"
            :class="agentColor(getMessageAccent(message)).swatchClass"
          />
          <strong
            class="debate-print-speaker"
            :class="message.role === 'agent' ? agentColor(getMessageAccent(message)).textClass : undefined"
          >
            {{ message.systemTitle || getDisplayName(message) }}
          </strong>
          <span
            v-if="message.role === 'agent'"
            class="debate-print-provider"
          >
            {{ getProvider(message) }}
          </span>
          <span
            v-if="getFaction(message)"
            class="debate-print-faction"
            :class="[getFactionColor(getFaction(message)).softClass, getFactionColor(getFaction(message)).textClass]"
          >
            {{ getFaction(message) }}
          </span>
          <time v-if="message.createdAt" class="debate-print-time">
            {{ message.createdAt }}
          </time>
        </header>

        <div class="debate-print-message-body">
          <DebateMarkdown
            :content="message.content"
            :agents="agents"
            :tools="message.citations ?? message.tools"
            @agent-mention="emit('openAgent', $event)"
            @evidence-citation="openEvidenceCitation($event, message)"
          />
        </div>
      </article>
    </div>

    <UModal
      :open="Boolean(selectedEvidence)"
      :title="selectedEvidence?.title ?? 'Evidence'"
      :description="selectedEvidence ? `${evidenceKindLabel(selectedEvidence)}${selectedEvidence.actor ? ` · ${selectedEvidence.actor}` : ''}` : undefined"
      :ui="{ content: 'max-w-3xl overflow-hidden' }"
      @update:open="selectedEvidence = $event ? selectedEvidence : null"
    >
      <template #body>
        <div v-if="selectedEvidence" class="grid min-w-0 gap-3">
          <p v-if="selectedEvidence.description" class="text-sm leading-6 text-default">
            {{ selectedEvidence.description }}
          </p>

          <div class="grid min-w-0 gap-2 text-sm">
            <div v-if="evidenceLineLabel(selectedEvidence)" class="flex min-w-0 items-center gap-2">
              <span class="w-20 shrink-0 text-muted">Location</span>
              <code class="min-w-0 truncate rounded bg-muted/70 px-1.5 py-0.5 font-mono text-highlighted ring ring-default">
                {{ evidenceLineLabel(selectedEvidence) }}
              </code>
            </div>
            <div v-if="selectedEvidence.command" class="flex min-w-0 items-center gap-2">
              <span class="w-20 shrink-0 text-muted">Command</span>
              <code class="min-w-0 overflow-x-auto rounded bg-muted/70 px-1.5 py-0.5 font-mono text-highlighted ring ring-default">
                {{ selectedEvidence.command }}
              </code>
            </div>
            <div v-if="typeof selectedEvidence.exitCode === 'number'" class="flex min-w-0 items-center gap-2">
              <span class="w-20 shrink-0 text-muted">Exit</span>
              <span class="text-highlighted">{{ selectedEvidence.exitCode }}</span>
            </div>
            <div v-if="selectedEvidence.url" class="flex min-w-0 items-center gap-2">
              <span class="w-20 shrink-0 text-muted">URL</span>
              <a
                :href="selectedEvidence.url"
                target="_blank"
                rel="noreferrer"
                class="min-w-0 truncate text-primary hover:underline"
              >
                {{ selectedEvidence.url }}
              </a>
            </div>
            <div v-if="selectedEvidence.query" class="flex min-w-0 items-center gap-2">
              <span class="w-20 shrink-0 text-muted">Query</span>
              <span class="min-w-0 truncate text-highlighted">{{ selectedEvidence.query }}</span>
            </div>
          </div>

          <div v-if="selectedEvidence.output" class="grid min-w-0 gap-2">
            <div class="text-sm font-semibold text-highlighted">
              Output
            </div>
            <pre class="max-h-[60vh] max-w-full overflow-auto whitespace-pre rounded-md border border-default bg-muted/35 p-3 font-mono text-xs leading-5 text-toned"><code>{{ selectedEvidence.output }}</code></pre>
          </div>
        </div>
      </template>
    </UModal>
  </section>
</template>
