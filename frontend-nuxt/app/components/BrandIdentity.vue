<script setup lang="ts">
withDefaults(defineProps<{
  to?: string
  size?: 'sm' | 'md'
  subtitle?: string
}>(), {
  size: 'sm'
})
</script>

<template>
  <NuxtLink
    v-if="to"
    :to="to"
    :class="['brand-identity', `brand-identity-${size}`]"
  >
    <Logo class="brand-identity-logo" />

    <span class="brand-identity-copy">
      <BrandLockup :size="size" />
      <span v-if="subtitle || $slots.subtitle" class="brand-identity-subtitle">
        <slot name="subtitle">
          {{ subtitle }}
        </slot>
      </span>
    </span>
  </NuxtLink>

  <span v-else :class="['brand-identity', `brand-identity-${size}`]">
    <Logo class="brand-identity-logo" />

    <span class="brand-identity-copy">
      <BrandLockup :size="size" />
      <span v-if="subtitle || $slots.subtitle" class="brand-identity-subtitle">
        <slot name="subtitle">
          {{ subtitle }}
        </slot>
      </span>
    </span>
  </span>
</template>

<style scoped>
.brand-identity {
  --brand-identity-logo-height: 2rem;
  --brand-identity-gap: 0.625rem;
  --logo-height: var(--brand-identity-logo-height);

  display: inline-flex;
  align-items: center;
  min-width: 0;
  gap: var(--brand-identity-gap);
  color: var(--ui-text-highlighted);
  font-weight: 700;
  text-decoration: none;
}

.brand-identity-md {
  --brand-identity-logo-height: 2.25rem;
  --brand-identity-gap: 0.7rem;
}

.brand-identity-logo {
  flex: 0 0 auto;
}

.brand-identity-copy {
  display: inline-flex;
  min-width: 0;
  flex-direction: column;
}

.brand-identity-subtitle {
  margin-top: 0.25rem;
  color: var(--ui-text-muted);
  font-size: 0.75rem;
  font-weight: 500;
  line-height: 1;
}
</style>
