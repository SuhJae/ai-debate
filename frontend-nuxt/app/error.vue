<script setup lang="ts">
import type { NuxtError } from '#app'
import { ko } from '@nuxt/ui/locale'

const props = defineProps<{
  error: NuxtError
}>()

const displayError = computed(() => ({
  ...props.error,
  statusMessage: userFriendlyErrorMessage(props.error, props.error.statusCode === 404
    ? '요청하신 페이지를 찾을 수 없습니다.'
    : '페이지를 표시하지 못했습니다. 잠시 후 다시 시도해 주세요.')
}))

useSeoMeta({
  title: displayError.value.statusMessage,
  description: displayError.value.statusMessage
})

useHead({
  htmlAttrs: {
    lang: 'ko'
  }
})
</script>

<template>
  <UApp :locale="ko">
    <UError :error="displayError" />
  </UApp>
</template>
