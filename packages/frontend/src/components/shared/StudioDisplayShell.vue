<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
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

const router = useRouter()

const isElectron = computed(() => {
  return typeof window !== 'undefined' && !!(window as any).electronAPI?.isElectron
})

function goBack() {
  router.push('/')
}

function handleEscape(e: KeyboardEvent) {
  if (e.key === 'Escape' && isElectron.value) {
    goBack()
  }
}

onMounted(() => {
  if (isElectron.value) {
    window.addEventListener('keydown', handleEscape)
  }
})

onUnmounted(() => {
  if (isElectron.value) {
    window.removeEventListener('keydown', handleEscape)
  }
})
</script>

<template>
  <div class="display-shell" :class="`display-shell--${accent}`">
    <AnimatedBackground :accent="accent" :show-beams="true" :show-orbs="true" />

    <div class="display-shell__content">
      <header v-if="showHeader" class="display-shell__header glass-card">
        <div class="display-shell__header-left">
          <button
            v-if="isElectron"
            @click="goBack"
            class="display-shell__back-btn"
            title="Go back (Esc)"
          >
            <svg class="display-shell__back-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"/>
            </svg>
          </button>
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
  gap: 1.5rem;
  padding: 2rem 2.5rem;
  box-sizing: border-box;
  overflow: hidden;
}

.display-shell__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.5rem 2rem;
  border-radius: var(--preke-radius-xl);
  flex-shrink: 0;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

.display-shell__header-left {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.display-shell__back-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.5rem;
  height: 2.5rem;
  border-radius: var(--preke-radius-md);
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--preke-border);
  color: var(--preke-text-dim);
  cursor: pointer;
  transition: all var(--preke-transition-base);
  flex-shrink: 0;
}

.display-shell__back-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: var(--preke-border-light);
  color: var(--preke-text-primary);
  transform: translateX(-2px);
}

.display-shell__back-icon {
  width: 1.25rem;
  height: 1.25rem;
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
  overflow: hidden;
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
  flex-shrink: 0;
  box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.2);
}

@media (max-width: 1100px) {
  .display-shell__content {
    padding: 1.5rem;
    gap: 1.25rem;
  }

  .display-shell__header {
    padding: 1.25rem 1.5rem;
  }
  
  .display-shell__footer {
    padding: 0.875rem 1.25rem;
  }
}
</style>
