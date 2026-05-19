<script setup lang="ts">
const title = defineModel<string>('title', { required: true })
const topic = defineModel<string>('topic', { required: true })
</script>

<template>
  <div class="flex h-full min-h-0 flex-col gap-3">
    <UFormField
      label="Topic title"
      class="shrink-0"
    >
      <UInput
        v-model="title"
        class="w-full"
        autocomplete="off"
        name="debate-title"
        placeholder="Update chat to accept user feedback"
      />
    </UFormField>

    <UFormField
      label="Prompt"
      class="flex min-h-0 flex-1 flex-col"
      :ui="{ container: 'mt-1 flex min-h-0 flex-1' }"
    >
      <UTextarea
        v-model="topic"
        :rows="8"
        class="h-full w-full"
        autocomplete="off"
        name="debate-prompt"
        :ui="{ root: 'h-full w-full', base: 'h-full resize-none overflow-auto' }"
        placeholder="Describe the engineering decision, product question, or implementation plan the agents should debate."
      />
    </UFormField>
  </div>
</template>
