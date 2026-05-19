<script setup lang="ts">
import DebateToolCard from '~/components/debate/DebateToolCard.vue'
import type { DebateToolEvent } from '~/types/debate-chat'

const props = defineProps<{
  tools?: DebateToolEvent[]
}>()

const evidenceTools = computed(() =>
  (props.tools ?? []).filter(tool => tool.kind !== 'terminal_probe')
)
const commandTools = computed(() =>
  (props.tools ?? []).filter(tool => tool.kind === 'terminal_probe')
)
const toolGridClass = 'grid min-w-0 gap-2 sm:grid-cols-2 xl:grid-cols-3'
</script>

<template>
  <div v-if="tools?.length" class="debate-tool-sections grid min-w-0 gap-2">
    <div v-if="evidenceTools.length" class="grid min-w-0 gap-1.5">
      <div class="flex h-5 min-w-0 items-center gap-2">
        <div class="text-xs font-semibold uppercase tracking-wide text-muted">
          Evidence
        </div>
        <UBadge size="sm" variant="soft" color="neutral">
          {{ evidenceTools.length }}
        </UBadge>
      </div>
      <div :class="toolGridClass">
        <DebateToolCard
          v-for="tool in evidenceTools"
          :key="tool.id"
          :tool="tool"
        />
      </div>
    </div>

    <details
      v-if="commandTools.length"
      class="group min-w-0 rounded-md border border-default bg-default/30"
    >
      <summary
        class="flex h-9 min-w-0 cursor-pointer list-none items-center gap-2 px-2.5 text-xs font-semibold uppercase tracking-wide text-muted [&::-webkit-details-marker]:hidden"
      >
        <UIcon
          name="i-ph-caret-right"
          class="size-3.5 shrink-0 transition-transform group-open:rotate-90"
        />
        <span class="min-w-0 flex-1 truncate">Command Log</span>
        <UBadge size="sm" variant="soft" color="neutral">
          {{ commandTools.length }}
        </UBadge>
      </summary>
      <div class="border-t border-default p-2" :class="toolGridClass">
        <DebateToolCard
          v-for="tool in commandTools"
          :key="tool.id"
          :tool="tool"
        />
      </div>
    </details>
  </div>
</template>
