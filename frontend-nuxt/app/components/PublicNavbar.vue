<template>
  <header class="public-navbar">
    <BrandIdentity to="/" />

    <div class="public-navbar-actions">
      <slot name="actions" />
      <UColorModeButton />
    </div>
  </header>
</template>

<style scoped>
.public-navbar {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 4rem;
  padding: 0 1rem;
  background: transparent;
}

.public-navbar-actions {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
}

@media (min-width: 640px) {
  .public-navbar {
    padding: 0 1.5rem;
  }
}
</style>
