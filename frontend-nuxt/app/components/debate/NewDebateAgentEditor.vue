<script setup lang="ts">
import type { DebateAgentDraft } from '~/types/debate'
import { agentColor, agentColorOptions, debateStyleItems, isPoliticalFaction, isTechnicalPreference, politicalFactionItems, technicalPreferenceItems } from '~/utils/debate-config'

const props = defineProps<{
  agent: DebateAgentDraft
  agentsCount: number
  providerItems: { label: string, value: string }[]
  modelItems: { label: string, value: string }[]
  modelLoading: boolean
  modelCatalogDisabled: boolean
}>()

const emit = defineEmits<{
  'update:agent': [agent: DebateAgentDraft]
  'providerChange': [value: unknown]
  'remove': [agentId: string]
}>()

const isPoliticianMode = computed(() => props.agent.debateStyle === 'politician')
const preferenceLabel = computed(() => isPoliticianMode.value ? 'Political party' : 'Technical preference')
const preferenceItems = computed(() => isPoliticianMode.value ? politicalFactionItems : technicalPreferenceItems)

function updateAgent(changes: Partial<DebateAgentDraft>) {
  emit('update:agent', { ...props.agent, ...changes })
}

function setDebateStyle(value: unknown) {
  const debateStyle = String(value)
  let technicalPreference = props.agent.technicalPreference

  if (debateStyle === 'politician' && !isPoliticalFaction(technicalPreference)) {
    technicalPreference = 'independent'
  } else if (debateStyle !== 'politician' && !isTechnicalPreference(technicalPreference)) {
    technicalPreference = 'neutral'
  }

  updateAgent({ debateStyle, technicalPreference })
}
</script>

<template>
  <div class="grid min-w-0 gap-4 rounded-md bg-elevated/45 p-4 ring ring-default">
    <div class="flex min-w-0 flex-wrap items-center gap-2">
      <span
        class="size-3 shrink-0 rounded-full ring-2 ring-default"
        :class="agentColor(agent.color).swatchClass"
      />
      <div class="min-w-0 flex-1">
        <div
          class="truncate text-sm font-semibold"
          :class="agentColor(agent.color).textClass"
        >
          {{ agent.displayName }}
        </div>
        <div class="truncate text-xs text-muted">
          @{{ agent.mentionName }} · {{ agent.model }}
        </div>
      </div>
      <UButton
        color="error"
        variant="ghost"
        icon="i-ph-trash"
        size="sm"
        :disabled="agentsCount <= 1"
        @click="emit('remove', agent.id)"
      />
    </div>

    <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      <UFormField label="Display name">
        <UInput
          :model-value="agent.displayName"
          class="w-full"
          @update:model-value="updateAgent({ displayName: String($event) })"
        />
      </UFormField>
      <UFormField label="Mention name">
        <UInput
          :model-value="agent.mentionName"
          class="w-full"
          @update:model-value="updateAgent({ mentionName: String($event) })"
        />
      </UFormField>
      <UFormField label="Provider">
        <USelect
          :model-value="agent.provider"
          :items="providerItems"
          :disabled="modelCatalogDisabled"
          class="w-full"
          @update:model-value="emit('providerChange', $event)"
        />
      </UFormField>
      <UFormField label="Model">
        <USelect
          :model-value="agent.model"
          :items="modelItems"
          :loading="modelLoading"
          :disabled="modelCatalogDisabled"
          class="w-full"
          @update:model-value="updateAgent({ model: String($event) })"
        />
      </UFormField>
      <UFormField label="Debate style">
        <USelect
          :model-value="agent.debateStyle"
          :items="debateStyleItems"
          class="w-full"
          @update:model-value="setDebateStyle"
        />
      </UFormField>
      <UFormField :label="preferenceLabel">
        <USelect
          :model-value="agent.technicalPreference"
          :items="preferenceItems"
          class="w-full"
          @update:model-value="updateAgent({ technicalPreference: String($event) })"
        />
      </UFormField>
    </div>

    <UFormField label="Agent color">
      <div class="grid gap-2 sm:grid-cols-3 xl:grid-cols-4">
        <button
          v-for="color in agentColorOptions"
          :key="color.value"
          type="button"
          class="flex min-w-0 items-center gap-2 rounded-md border px-2.5 py-2 text-left text-sm transition-colors"
          :class="agent.color === color.value
            ? ['ring-2', color.softClass, color.textClass, color.borderClass, color.ringClass]
            : 'border-default hover:bg-elevated'"
          :aria-pressed="agent.color === color.value"
          @click="updateAgent({ color: color.value })"
        >
          <span
            class="size-4 shrink-0 rounded-full ring-2 ring-default"
            :class="color.swatchClass"
          />
          <span class="truncate font-medium">{{ color.label }}</span>
        </button>
      </div>
    </UFormField>

    <div class="grid gap-3 sm:grid-cols-[14rem_minmax(0,1fr)]">
      <UCheckbox
        :model-value="agent.writeThesis"
        label="Write initial thesis"
        description="Disable for judge/reviewer agents."
        @update:model-value="updateAgent({ writeThesis: Boolean($event) })"
      />
      <UFormField label="Private behavior note">
        <UTextarea
          :model-value="agent.note"
          :rows="3"
          class="w-full"
          placeholder="Private behavior notes for this agent..."
          @update:model-value="updateAgent({ note: String($event) })"
        />
      </UFormField>
    </div>
  </div>
</template>
