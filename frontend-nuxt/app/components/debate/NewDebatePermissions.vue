<script setup lang="ts">
type WorkspaceValidationState = 'idle' | 'checking' | 'valid' | 'invalid'

const workingDirectory = defineModel<string>('workingDirectory', { required: true })
const allowFileRead = defineModel<boolean>('allowFileRead', { required: true })
const allowProbeCommands = defineModel<boolean>('allowProbeCommands', { required: true })
const allowWebEvidence = defineModel<boolean>('allowWebEvidence', { required: true })

const config = useRuntimeConfig()
const validationState = ref<WorkspaceValidationState>('idle')
const validationMessage = ref('')
const hasMounted = ref(false)
let validationTimer: ReturnType<typeof setTimeout> | undefined
let validationRun = 0

const validationIcon = computed(() => {
  if (validationState.value === 'checking') return 'i-ph-spinner-gap'
  if (validationState.value === 'valid') return 'i-ph-check-circle'
  if (validationState.value === 'invalid') return 'i-ph-warning-circle'
  return ''
})

const validationIconClass = computed(() => {
  if (validationState.value === 'checking') return 'animate-spin text-muted'
  if (validationState.value === 'valid') return 'text-success'
  if (validationState.value === 'invalid') return 'text-error'
  return 'text-muted'
})

onMounted(() => {
  hasMounted.value = true
  scheduleValidation()
})

onBeforeUnmount(() => {
  if (validationTimer) clearTimeout(validationTimer)
})

watch(workingDirectory, () => {
  if (!hasMounted.value) return
  scheduleValidation()
})

watch(allowFileRead, (enabled) => {
  if (!enabled) {
    allowProbeCommands.value = false
  }
})

function scheduleValidation() {
  if (validationTimer) clearTimeout(validationTimer)
  const run = ++validationRun
  const value = workingDirectory.value.trim()
  if (!value) {
    validationState.value = 'idle'
    validationMessage.value = ''
    return
  }
  validationState.value = 'checking'
  validationMessage.value = 'Checking directory...'
  validationTimer = setTimeout(() => {
    void validateWorkingDirectory(value, run)
  }, 250)
}

async function validateWorkingDirectory(path: string, run: number) {
  try {
    const result = await $fetch<{
      valid: boolean
      normalized_path: string | null
      message: string
    }>(`${config.public.aiDebateApiUrl}/workspace/validate`, {
      method: 'POST',
      body: { path }
    })
    if (run !== validationRun) return
    validationState.value = result.valid ? 'valid' : 'invalid'
    validationMessage.value = result.message
  } catch {
    if (run !== validationRun) return
    validationState.value = 'invalid'
    validationMessage.value = 'Validation unavailable.'
  }
}
</script>

<template>
  <div class="grid content-start gap-3 rounded-md bg-elevated/45 p-3 ring ring-default">
    <div class="text-sm font-semibold text-highlighted">
      Permissions
    </div>
    <UFormField label="Working directory">
      <UInput
        v-model="workingDirectory"
        class="w-full"
        placeholder="Select a project directory"
      >
        <template #trailing>
          <UTooltip
            v-if="validationIcon"
            :text="validationMessage"
          >
            <UIcon
              :name="validationIcon"
              class="size-4"
              :class="validationIconClass"
            />
          </UTooltip>
        </template>
      </UInput>
    </UFormField>
    <UCheckbox
      v-model="allowFileRead"
      label="Allow file read"
      description="Agents may inspect files in the working project."
    />
    <UCheckbox
      v-model="allowProbeCommands"
      label="Allow probe commands"
      :disabled="!allowFileRead"
      :description="allowFileRead ? 'Agents may run read-only terminal probes.' : 'Requires file read access.'"
    />
    <UCheckbox
      v-model="allowWebEvidence"
      label="Allow web evidence"
      description="Agents may share documentation/search evidence."
    />
  </div>
</template>
