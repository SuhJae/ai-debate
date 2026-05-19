<script setup lang="ts">
const colorMode = useColorMode()

const color = computed(() => colorMode.value === 'dark' ? '#090a0e' : '#fbfaf9')

useHead({
  meta: [
    { charset: 'utf-8' },
    { name: 'viewport', content: 'width=device-width, initial-scale=1' },
    { key: 'theme-color', name: 'theme-color', content: color }
  ],
  link: [
    { rel: 'icon', type: 'image/png', href: '/favicon.png' }
  ],
  htmlAttrs: {
    lang: 'en'
  }
})

const title = 'AI Debate'
const description = 'A local multi-agent engineering debate workspace.'
const requestUrl = useRequestURL()
const config = useRuntimeConfig()
const siteUrl = computed(() => String(config.public.siteUrl || requestUrl.origin).replace(/\/+$/, ''))
const defaultOgImage = computed(() => `${siteUrl.value}/api/og/default.svg`)

useSeoMeta({
  title,
  description,
  ogTitle: title,
  ogDescription: description,
  ogSiteName: 'AI Debate',
  ogType: 'website',
  ogUrl: siteUrl,
  ogImage: defaultOgImage,
  ogImageAlt: title,
  twitterCard: 'summary_large_image'
})
</script>

<template>
  <UApp :toaster="{ position: 'top-right' }" :tooltip="{ delayDuration: 200 }">
    <NuxtLoadingIndicator color="var(--ui-primary)" />

    <NuxtLayout>
      <NuxtPage />
    </NuxtLayout>
  </UApp>
</template>
