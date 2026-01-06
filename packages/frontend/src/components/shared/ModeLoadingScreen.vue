<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import AnimatedBackground from './AnimatedBackground.vue'

const props = withDefaults(defineProps<{
  mode: 'recorder' | 'mixer'
  /** Minimum time to show loading screen (ms) */
  minTime?: number
  /** Maximum time before auto-dismissing (ms) */
  maxTime?: number
  /** Signal from parent that content is ready */
  contentReady?: boolean
  /** Show cancel button */
  showCancel?: boolean
}>(), {
  minTime: 1500,
  maxTime: 8000,
  contentReady: false,
  showCancel: false
})

const emit = defineEmits<{
  (e: 'ready'): void
  (e: 'cancel'): void
}>()

function handleCancel() {
  emit('cancel')
}

const minTimePassed = ref(false)
let minTimeoutId: ReturnType<typeof setTimeout> | null = null
let maxTimeoutId: ReturnType<typeof setTimeout> | null = null

function checkAndDismiss() {
  if (minTimePassed.value && props.contentReady) {
    emit('ready')
  }
}

watch(() => props.contentReady, (ready) => {
  if (ready) checkAndDismiss()
})

// Mode-specific styling
const modeColor = computed(() => props.mode === 'recorder' ? '#d45a5a' : '#7c3aed')
const modeName = computed(() => props.mode === 'recorder' ? 'Recorder' : 'Mixer')
const modeTagline = computed(() => props.mode === 'recorder' ? 'Multi-cam ISO Recording' : 'Live Switching & Streaming')
const bgAccent = computed(() => props.mode === 'recorder' ? 'red' : 'purple')

onMounted(() => {
  minTimeoutId = setTimeout(() => {
    minTimePassed.value = true
    checkAndDismiss()
  }, props.minTime)
  
  maxTimeoutId = setTimeout(() => {
    emit('ready')
  }, props.maxTime)
})

onUnmounted(() => {
  if (minTimeoutId) clearTimeout(minTimeoutId)
  if (maxTimeoutId) clearTimeout(maxTimeoutId)
})
</script>

<template>
  <div class="loading-screen">
    <!-- Animated background with mode-specific color -->
    <AnimatedBackground :accent="bgAccent" :show-beams="true" :show-pattern="true" />
    
    <!-- Content -->
    <div class="loading-content">
      <!-- Mode Icon - clean, no box -->
      <div class="loading-icon" :style="{ color: modeColor }">
        <!-- Recorder icon -->
        <svg v-if="mode === 'recorder'" viewBox="0 0 24 24" fill="currentColor">
          <circle cx="12" cy="12" r="8"/>
        </svg>
        
        <!-- Mixer icon -->
        <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
          <rect x="2" y="2" width="9" height="6" rx="1"/>
          <rect x="13" y="2" width="9" height="6" rx="1"/>
          <rect x="2" y="10" width="9" height="6" rx="1"/>
          <rect x="13" y="10" width="9" height="6" rx="1"/>
          <circle cx="12" cy="20" r="2" fill="currentColor"/>
          <path d="M9 19.5a4 4 0 0 1 6 0" stroke-linecap="round"/>
        </svg>
        
        <!-- Glow effect -->
        <div class="loading-icon__glow" :style="{ background: modeColor }"></div>
      </div>
      
      <!-- Mode title -->
      <div class="loading-text">
        <h2 class="loading-title" :style="{ color: modeColor }">
          {{ modeName }}
        </h2>
        <p class="loading-tagline">
          {{ modeTagline }}
        </p>
      </div>
      
      <!-- Animated loading dots -->
      <div class="loading-dots">
        <div 
          v-for="i in 3"
          :key="i"
          class="loading-dot"
          :style="{ 
            backgroundColor: modeColor,
            animationDelay: `${(i - 1) * 0.15}s`
          }"
        ></div>
      </div>
      
      <!-- Cancel button -->
      <button 
        v-if="showCancel"
        @click="handleCancel"
        class="loading-cancel"
      >
        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.8">
          <path stroke-linecap="round" stroke-linejoin="round" d="M10 19l-7-7m0 0l7-7m-7 7h18"/>
        </svg>
        Go back
      </button>
    </div>
  </div>
</template>

<style scoped>
.loading-screen {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: var(--preke-bg);
  overflow: hidden;
}

.loading-content {
  position: relative;
  z-index: 10;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2.5rem;
}

/* Icon - clean without box */
.loading-icon {
  position: relative;
  width: 80px;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.loading-icon svg {
  width: 64px;
  height: 64px;
  animation: icon-pulse 2s ease-in-out infinite;
}

.loading-icon__glow {
  position: absolute;
  inset: -20px;
  border-radius: 50%;
  filter: blur(40px);
  opacity: 0.3;
  animation: glow-pulse 2s ease-in-out infinite;
}

@keyframes icon-pulse {
  0%, 100% { 
    transform: scale(1);
    filter: drop-shadow(0 0 10px currentColor);
  }
  50% { 
    transform: scale(1.05);
    filter: drop-shadow(0 0 25px currentColor);
  }
}

@keyframes glow-pulse {
  0%, 100% { opacity: 0.2; transform: scale(1); }
  50% { opacity: 0.4; transform: scale(1.1); }
}

/* Text */
.loading-text {
  text-align: center;
}

.loading-title {
  font-size: 2.5rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
  letter-spacing: -0.02em;
}

.loading-tagline {
  font-size: 1.125rem;
  color: var(--preke-text-muted);
}

/* Loading dots */
.loading-dots {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.loading-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  animation: dot-bounce 1.2s ease-in-out infinite;
}

@keyframes dot-bounce {
  0%, 80%, 100% { transform: translateY(0); opacity: 0.4; }
  40% { transform: translateY(-10px); opacity: 1; }
}

/* Cancel button */
.loading-cancel {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 1rem;
  padding: 10px 20px;
  font-size: 14px;
  font-weight: 500;
  color: var(--preke-text-muted);
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--preke-border);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.loading-cancel:hover {
  color: var(--preke-text);
  background: rgba(255, 255, 255, 0.1);
  border-color: var(--preke-border-light);
}

.loading-cancel svg {
  width: 16px;
  height: 16px;
}
</style>
