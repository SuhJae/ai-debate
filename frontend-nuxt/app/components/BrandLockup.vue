<script setup lang="ts">
withDefaults(
  defineProps<{
    size?: 'sm' | 'md' | 'hero'
  }>(),
  {
    size: 'sm'
  }
)
</script>

<template>
  <span :class="['brand-lockup', `brand-lockup-${size}`]">
    <span class="brand-lockup-ko">AI Debate</span>
    <span class="brand-lockup-sub">
      Multi-agent workspace
    </span>
  </span>
</template>

<style scoped>
.brand-lockup {
  display: inline-flex;
  flex-direction: column;
  color: var(--ui-text-highlighted);
}

.brand-lockup-ko {
  font-family: var(--font-serif);
  line-height: 1.04;
}

.brand-lockup-sub {
  font-family: var(--font-sans);
  font-weight: 650;
  letter-spacing: 0;
  color: var(--ui-text-toned);
  line-height: 1.12;
}

.brand-lockup-alpha {
  display: inline-block;
  margin-inline-start: 0.18em;
  color: var(--color-joseon-700);
  font-weight: 800;
}

.brand-lockup-sm {
  gap: 0.24rem;
}

.brand-lockup-sm .brand-lockup-ko {
  font-size: 1.0625rem;
  font-weight: 700;
}

.brand-lockup-sm .brand-lockup-sub {
  font-size: 0.625rem;
}

.brand-lockup-md {
  gap: 0.26rem;
}

.brand-lockup-md .brand-lockup-ko {
  font-size: 1.125rem;
  font-weight: 700;
}

.brand-lockup-md .brand-lockup-sub {
  font-size: 0.6875rem;
}

.brand-lockup-hero {
  align-items: center;
  gap: 0.28rem;
}

.brand-lockup-hero .brand-lockup-ko {
  font-size: clamp(3.25rem, 9vw, 5.75rem);
  font-weight: 900;
}

.brand-lockup-hero .brand-lockup-sub {
  font-size: clamp(1.25rem, 3vw, 2rem);
}
</style>
