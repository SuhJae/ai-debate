<script setup lang="ts">
import type { DebateToolEvent } from '~/types/debate-chat'

const props = defineProps<{
  tool: DebateToolEvent
}>()

const detailOpen = ref(false)

const iconName = computed(() => {
  if (props.tool.kind === 'file_evidence') return 'i-ph-file-text'
  if (props.tool.kind === 'terminal_probe') return 'i-ph-terminal-window'
  if (props.tool.kind === 'web_evidence') return 'i-ph-globe'
  if (props.tool.kind === 'consensus') return 'i-ph-handshake'
  return 'i-ph-book-open-text'
})

const statusColor = computed(() => {
  if (props.tool.status === 'succeeded') return 'success'
  if (props.tool.status === 'failed') return 'error'
  if (props.tool.status === 'running') return 'info'
  return 'warning'
})

const kindLabel = computed(() => {
  if (props.tool.kind === 'file_evidence') return 'File evidence'
  if (props.tool.kind === 'terminal_probe') return 'Terminal probe'
  if (props.tool.kind === 'web_evidence') return 'Web evidence'
  if (props.tool.kind === 'consensus') return 'Consensus'
  return 'Shared source'
})

const activityText = computed(() => {
  if (props.tool.kind === 'consensus') {
    const actor = props.tool.actor ? `@${props.tool.actor}` : 'An agent'
    if (props.tool.action === 'propose') {
      return props.tool.targetAgent
        ? `${actor} proposed @${props.tool.targetAgent} as final writer.`
        : `${actor} proposed consensus.`
    }
    if (props.tool.action === 'accept') return `${actor} accepted the proposal.`
    if (props.tool.action === 'reject') return `${actor} rejected the proposal.`
    if (props.tool.action === 'withdraw') return `${actor} withdrew the proposal.`
  }

  if (props.tool.kind === 'mcp_proposal' && props.tool.actor) {
    return `@${props.tool.actor} shared this source for the debate.`
  }

  return ''
})

const fileLineLabel = computed(() => {
  if (!props.tool.path) return ''
  if (!props.tool.lineStart) return props.tool.path
  if (!props.tool.lineEnd || props.tool.lineEnd === props.tool.lineStart) {
    return `${props.tool.path}:${props.tool.lineStart}`
  }
  return `${props.tool.path}:${props.tool.lineStart}-${props.tool.lineEnd}`
})

const hasDetail = computed(() =>
  Boolean(
    props.tool.description
    || activityText.value
    || fileLineLabel.value
    || props.tool.command
    || props.tool.url
    || props.tool.query
    || props.tool.proposalId
    || props.tool.output
  )
)

const detailTitle = computed(() => `${kindLabel.value}: ${props.tool.title}`)

const summaryLine = computed(() => {
  if (props.tool.command) return props.tool.command
  if (fileLineLabel.value) return fileLineLabel.value
  if (props.tool.url) return props.tool.url
  if (props.tool.query) return props.tool.query
  if (props.tool.proposalId) return props.tool.proposalId
  return activityText.value || props.tool.description || ''
})
</script>

<template>
  <div class="grid h-28 min-w-0 max-w-full grid-rows-[auto_minmax(0,1fr)_auto] overflow-hidden rounded-md border border-default bg-default/45 p-2.5">
    <div class="flex min-w-0 items-start gap-2">
      <div class="flex size-7 shrink-0 items-center justify-center rounded-md bg-muted/60 ring ring-default">
        <UIcon :name="iconName" class="size-4 text-muted" />
      </div>

      <div class="min-w-0 flex-1">
        <div class="min-w-0 truncate text-sm font-semibold leading-5 text-highlighted">
          {{ tool.title }}
        </div>
        <div class="mt-0.5 flex min-w-0 items-center gap-1.5">
          <UBadge
            size="sm"
            variant="soft"
            color="neutral"
            class="shrink-0"
          >
            {{ kindLabel }}
          </UBadge>
          <UBadge
            size="sm"
            variant="soft"
            :color="statusColor"
            class="shrink-0"
          >
            {{ tool.status }}
          </UBadge>
        </div>
      </div>
    </div>

    <div class="min-h-0 min-w-0 overflow-hidden pt-1.5">
      <p
        v-if="tool.description"
        class="line-clamp-1 text-xs leading-4 text-muted"
      >
        {{ tool.description }}
      </p>
      <p
        v-else-if="activityText"
        class="line-clamp-1 text-xs leading-4 text-toned"
      >
        {{ activityText }}
      </p>
    </div>

    <div class="flex h-6 min-w-0 items-center justify-between gap-2 text-xs text-toned">
      <div class="flex min-w-0 items-center gap-1.5">
        <UIcon
          v-if="summaryLine"
          :name="tool.command ? 'i-ph-terminal' : tool.url ? 'i-ph-arrow-square-out' : fileLineLabel ? 'i-ph-map-pin-line' : 'i-ph-hash'"
          class="size-3.5 shrink-0 text-dimmed"
        />
        <span class="min-w-0 truncate">
          {{ summaryLine }}
        </span>
      </div>

      <UTooltip v-if="hasDetail" text="View full details">
        <UButton
          type="button"
          icon="i-ph-arrows-out-simple"
          size="xs"
          color="neutral"
          variant="ghost"
          aria-label="View full evidence details"
          class="shrink-0"
          @click.stop="detailOpen = true"
        />
      </UTooltip>
    </div>

    <UModal
      :open="detailOpen"
      :title="detailTitle"
      :description="tool.actor ? `Recorded by @${tool.actor}` : undefined"
      :ui="{ content: 'max-w-3xl overflow-hidden' }"
      @update:open="detailOpen = $event"
    >
      <template #body>
        <div class="grid min-w-0 gap-3">
          <p v-if="activityText" class="text-sm leading-6 text-toned">
            {{ activityText }}
          </p>

          <p v-if="tool.description" class="text-sm leading-6 text-default">
            {{ tool.description }}
          </p>

          <div class="grid min-w-0 gap-2 text-sm">
            <div
              v-if="fileLineLabel"
              class="flex min-w-0 items-center gap-2"
            >
              <span class="w-20 shrink-0 text-muted">Location</span>
              <code class="min-w-0 truncate rounded bg-muted/70 px-1.5 py-0.5 font-mono text-highlighted ring ring-default">
                {{ fileLineLabel }}
              </code>
            </div>
            <div
              v-if="tool.command"
              class="flex min-w-0 items-center gap-2"
            >
              <span class="w-20 shrink-0 text-muted">Command</span>
              <code class="min-w-0 overflow-x-auto rounded bg-muted/70 px-1.5 py-0.5 font-mono text-highlighted ring ring-default">
                {{ tool.command }}
              </code>
            </div>
            <div
              v-if="typeof tool.exitCode === 'number'"
              class="flex min-w-0 items-center gap-2"
            >
              <span class="w-20 shrink-0 text-muted">Exit</span>
              <span class="text-highlighted">{{ tool.exitCode }}</span>
            </div>
            <div
              v-if="tool.url"
              class="flex min-w-0 items-center gap-2"
            >
              <span class="w-20 shrink-0 text-muted">URL</span>
              <a
                :href="tool.url"
                target="_blank"
                rel="noreferrer"
                class="min-w-0 truncate text-primary hover:underline"
              >
                {{ tool.url }}
              </a>
            </div>
            <div
              v-if="tool.query"
              class="flex min-w-0 items-center gap-2"
            >
              <span class="w-20 shrink-0 text-muted">Query</span>
              <span class="min-w-0 truncate text-highlighted">{{ tool.query }}</span>
            </div>
            <div
              v-if="tool.proposalId"
              class="flex min-w-0 items-center gap-2"
            >
              <span class="w-20 shrink-0 text-muted">ID</span>
              <code class="min-w-0 truncate rounded bg-muted/70 px-1.5 py-0.5 font-mono text-highlighted ring ring-default">
                {{ tool.proposalId }}
              </code>
            </div>
          </div>

          <div v-if="tool.output" class="grid min-w-0 gap-2">
            <div class="text-sm font-semibold text-highlighted">
              Output
            </div>
            <pre class="max-h-[60vh] max-w-full overflow-auto whitespace-pre rounded-md border border-default bg-muted/35 p-3 font-mono text-xs leading-5 text-toned"><code>{{ tool.output }}</code></pre>
          </div>
        </div>
      </template>
    </UModal>
  </div>
</template>
