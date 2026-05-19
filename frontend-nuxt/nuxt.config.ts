// https://nuxt.com/docs/api/configuration/nuxt-config

export default defineNuxtConfig({
  modules: [
    '@nuxt/eslint',
    '@nuxt/ui',
    '@comark/nuxt'
  ],

  devtools: {
    enabled: true
  },

  css: ['~/assets/css/main.css'],

  runtimeConfig: {
    public: {
      siteUrl: process.env.NUXT_PUBLIC_SITE_URL
        || process.env.SITE_URL
        || 'http://localhost:3000',
      aiDebateApiUrl: process.env.NUXT_PUBLIC_AI_DEBATE_API_URL
        || 'http://127.0.0.1:8000/api',
      aiDebateWsUrl: process.env.NUXT_PUBLIC_AI_DEBATE_WS_URL
        || 'ws://127.0.0.1:8000/ws',
      aiDebateDefaultWorkspace: process.env.NUXT_PUBLIC_AI_DEBATE_DEFAULT_WORKSPACE
        || process.env.AI_DEBATE_WORKSPACE
        || ''
    }
  },

  compatibilityDate: '2024-07-11',

  nitro: {
    experimental: {
      openAPI: true
    }
  },

  vite: {
    optimizeDeps: {
      include: [
        'striptags',
        '@vueuse/core',
        'date-fns',
        '@shikijs/langs/html',
        '@shikijs/langs/css',
        '@shikijs/langs/python',
        '@shikijs/langs/sql',
        '@shikijs/langs/go',
        '@shikijs/langs/rust',
        '@shikijs/langs/java',
        '@shikijs/langs/c',
        '@shikijs/langs/cpp',
        '@shikijs/langs/ruby',
        '@shikijs/langs/php',
        '@shikijs/langs/swift',
        '@shikijs/langs/kotlin',
        '@shikijs/langs/diff',
        '@shikijs/langs/dockerfile',
        '@shikijs/langs/xml',
        '@shikijs/langs/toml',
        '@shikijs/langs/graphql'
      ]
    }
  },

  eslint: {
    config: {
      stylistic: {
        commaDangle: 'never',
        braceStyle: '1tbs'
      }
    }
  },

  icon: {
    clientBundle: {
      scan: {
        // default glob excludes .ts — extend it so app.config.ts is scanned
        globInclude: ['**/*.{vue,jsx,tsx,ts,md,mdc,mdx,yml,yaml}']
      },
      // icons resolved at runtime from appConfig or computed properties
      // that the scanner cannot statically detect
      icons: [
        'ph:caret-left', // panelClose — resolved from appConfig.ui.icons at runtime
        'ph:caret-right', // panelOpen  — resolved from appConfig.ui.icons at runtime
        'ph:sign-out',
        'ph:user',
        'ph:chat-circle',
        'ph:pencil',
        'ph:trash'
      ]
    }
  }
})
