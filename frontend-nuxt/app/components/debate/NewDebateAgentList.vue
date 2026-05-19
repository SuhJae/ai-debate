<script setup lang="ts">
import type { DebateAgentDraft, DebateDiscussionSelectItem } from '~/types/debate'
import { agentColor } from '~/utils/debate-config'

type AgentDropPosition = 'before' | 'after'

defineProps<{
  agents: DebateAgentDraft[]
  selectedAgentId: string
  thesisAgentCount: number
  draggingAgentId: string | null
  dragOverAgentId: string | null
  dragOverPosition: AgentDropPosition
  modelCatalogDisabled: boolean
  importDiscussions: DebateDiscussionSelectItem[]
  selectedImportDiscussionId: string | null
  importPending: boolean
  importingAgents: boolean
}>()

const emit = defineEmits<{
  'add': []
  'update:selectedImportDiscussionId': [discussionId: string | null]
  'loadAgents': []
  'refreshImports': []
  'select': [agentId: string]
  'dragStart': [event: DragEvent, agentId: string]
  'dragOver': [agentId: string, position: AgentDropPosition]
  'dragLeave': [agentId: string]
  'drop': [agentId: string, position: AgentDropPosition]
  'dragEnd': []
}>()

function getDropPosition(event: DragEvent): AgentDropPosition {
  const target = event.currentTarget
  if (!(target instanceof HTMLElement)) return 'before'

  const rect = target.getBoundingClientRect()
  return event.clientY >= rect.top + rect.height / 2 ? 'after' : 'before'
}

function handleDragOver(event: DragEvent, agentId: string) {
  emit('dragOver', agentId, getDropPosition(event))
}

function handleDragLeave(event: DragEvent, agentId: string) {
  const target = event.currentTarget
  const relatedTarget = event.relatedTarget

  if (target instanceof HTMLElement && relatedTarget instanceof Node && target.contains(relatedTarget)) return

  emit('dragLeave', agentId)
}

function handleDrop(event: DragEvent, agentId: string) {
  emit('drop', agentId, getDropPosition(event))
}

function handleImportSelection(value: unknown) {
  if (!value) {
    emit('update:selectedImportDiscussionId', null)
    return
  }
  if (typeof value === 'string') {
    emit('update:selectedImportDiscussionId', value)
    return
  }
  if (typeof value === 'object' && 'value' in value) {
    emit('update:selectedImportDiscussionId', String(value.value))
  }
}
</script>

<template>
  <div class="min-w-0 rounded-md bg-elevated/45 ring ring-default">
    <div class="grid gap-1 border-b border-default px-3 py-2">
      <div class="flex min-w-0 items-center gap-2">
        <div class="min-w-0 flex-1">
          <div class="truncate text-sm font-semibold text-highlighted">
            Agents
          </div>
        </div>
        <UButton
          icon="i-ph-plus"
          color="neutral"
          variant="ghost"
          size="xs"
          aria-label="Add agent"
          :disabled="modelCatalogDisabled"
          @click="emit('add')"
        />
        <UPopover
          :content="{ align: 'end', sideOffset: 8 }"
          @update:open="open => open && emit('refreshImports')"
        >
          <UButton
            icon="i-ph-download-simple"
            color="neutral"
            variant="ghost"
            size="xs"
            label="Load"
            :disabled="importingAgents"
          />

          <template #content>
            <div class="grid w-80 gap-3 p-3">
              <div class="grid gap-0.5">
                <div class="text-sm font-semibold text-highlighted">
                  Load agent setup
                </div>
                <div class="text-xs text-muted">
                  Replace this setup with agents from an old discussion.
                </div>
              </div>
              <USelectMenu
                :model-value="selectedImportDiscussionId ?? undefined"
                :items="importDiscussions"
                value-key="value"
                label-key="label"
                description-key="description"
                :search-input="{ placeholder: 'Search discussions...' }"
                placeholder="Select discussion"
                class="w-full"
                :loading="importPending"
                :disabled="importingAgents"
                @update:model-value="handleImportSelection"
              />
              <UButton
                block
                icon="i-ph-copy"
                :loading="importingAgents"
                :disabled="!selectedImportDiscussionId || importingAgents"
                @click="emit('loadAgents')"
              >
                Clone agents
              </UButton>
            </div>
          </template>
        </UPopover>
      </div>
      <div class="min-w-0">
        <div class="truncate text-xs text-muted">
          {{ thesisAgentCount }} writing thesis · top to bottom turns
        </div>
      </div>
    </div>

    <div class="grid gap-1 p-2">
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
          draggable="true"
          class="group flex w-full min-w-0 items-center gap-2 rounded-md px-2.5 py-2 text-left text-sm transition-colors hover:bg-accented/70"
          :class="[
            selectedAgentId === agent.id ? [agentColor(agent.color).softClass, 'ring-1', agentColor(agent.color).ringClass] : '',
            draggingAgentId === agent.id ? 'opacity-45' : ''
          ]"
          @click="emit('select', agent.id)"
          @dragstart="emit('dragStart', $event, agent.id)"
          @dragover.prevent="handleDragOver($event, agent.id)"
          @dragleave="handleDragLeave($event, agent.id)"
          @drop.prevent="handleDrop($event, agent.id)"
          @dragend="emit('dragEnd')"
        >
          <UIcon
            name="i-ph-dots-six-vertical"
            class="size-4 shrink-0 text-dimmed opacity-0 transition-opacity group-hover:opacity-100"
          />
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
          <UBadge
            size="sm"
            variant="soft"
            color="neutral"
            class="shrink-0 capitalize"
          >
            {{ agent.provider }}
          </UBadge>
        </button>
      </div>
    </div>
  </div>
</template>
