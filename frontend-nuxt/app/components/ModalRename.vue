<script setup lang="ts">
const props = defineProps<{
  title?: string
}>()

const emit = defineEmits<{ close: [string | false] }>()

const value = ref(props.title ?? '')

const trimmed = computed(() => value.value.trim())

function submit() {
  if (!trimmed.value) return
  emit('close', trimmed.value)
}
</script>

<template>
  <UModal
    title="대화 이름 바꾸기"
    description="이 대화에 사용할 새 제목을 입력하세요."
    :ui="{
      footer: 'flex-row-reverse justify-start'
    }"
    :close="false"
  >
    <template #body>
      <UInput
        v-model="value"
        autofocus
        size="lg"
        placeholder="대화 제목"
        class="w-full"
        :ui="{ root: 'w-full' }"
        @keydown.enter.prevent="submit"
      />
    </template>

    <template #footer>
      <UButton label="저장" :disabled="!trimmed" @click="submit" />
      <UButton
        color="neutral"
        variant="ghost"
        label="취소"
        @click="emit('close', false)"
      />
    </template>
  </UModal>
</template>
