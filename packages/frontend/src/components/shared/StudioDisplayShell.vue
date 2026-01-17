<script setup lang="ts">
import AnimatedBackground from '@/components/shared/AnimatedBackground.vue'
import PrekeStudioLogo from '@/components/shared/PrekeStudioLogo.vue'

type Accent = 'gold' | 'red' | 'purple' | 'blue'

withDefaults(defineProps<{
  title?: string
  subtitle?: string
  accent?: Accent
  showHeader?: boolean
  showFooter?: boolean
  mainClass?: string
}>(), {
  accent: 'gold',
  showHeader: true,
  showFooter: true,
  mainClass: ''
})
</script>

<template>
  <div class="display-shell" :class="`display-shell--${accent}`">
    <AnimatedBackground :accent="accent" :show-beams="true" :show-orbs="true" />

    <div class="display-shell__content">
      <header v-if="showHeader" class="display-shell__header glass-card">
        <div class="display-shell__header-left">
          <PrekeStudioLogo />
          <div class="display-shell__titles">
            <div class="display-shell__title">{{ title }}</div>
            <div v-if="subtitle" class="display-shell__subtitle">{{ subtitle }}</div>
          </div>
        </div>
        <div class="display-shell__header-right">
          <slot name="header-right" />
        </div>
      </header>

      <main class="display-shell__main" :class="mainClass">
        <slot />
      </main>

      <footer v-if="showFooter" class="display-shell__footer glass-panel">
        <slot name="footer" />
      </footer>
    </div>
  </div>
</template>

<style scoped>
@import '@/styles/design-system-v2.css';

.display-shell {
  position: relative;
  width: 100vw;
  height: 100vh;
  background: var(--preke-bg-base);
  color: var(--preke-text-primary);
  overflow: hidden;
}

.display-shell__content {
  position: relative;
  z-index: 1;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: var(--preke-space-xl);
  padding: 2.5rem 3rem;
  box-sizing: border-box;
}

.display-shell__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.75rem 2.25rem;
  border-radius: var(--preke-radius-xl);
}

.display-shell__header-left {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.display-shell__titles {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.display-shell__title {
  font-size: clamp(1.75rem, 2vw, 2.5rem);
  font-weight: 700;
  letter-spacing: -0.01em;
}

.display-shell__subtitle {
  font-size: clamp(1rem, 1.4vw, 1.25rem);
  color: var(--preke-text-dim);
}

.display-shell__header-right {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  font-size: 1.125rem;
  color: var(--preke-text-muted);
}

.display-shell__main {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 0;
}

.display-shell__footer {
  padding: 1rem 1.5rem;
  border-radius: var(--preke-radius-lg);
  font-size: 1rem;
  color: var(--preke-text-muted);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

@media (max-width: 1100px) {
  .display-shell__content {
    padding: 2rem;
  }

  .display-shell__header {
    padding: 1.5rem;
  }
}
</style>
