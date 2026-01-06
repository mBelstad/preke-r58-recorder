<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { buildApiUrl } from '@/lib/api'
import { toast } from '@/composables/useToast'
import { useCapabilitiesStore } from '@/stores/capabilities'

const router = useRouter()
const capabilitiesStore = useCapabilitiesStore()
const selectedMode = ref<'recorder' | 'mixer' | null>(null)
const switching = ref(false)
const switchError = ref<string | null>(null)

// AbortController to cancel in-flight mode switch requests
let switchAbortController: AbortController | null = null

// Switch to idle mode when entering Studio page (stops all camera processes)
onMounted(async () => {
  try {
    const response = await fetch(buildApiUrl('/api/mode/idle'), { method: 'POST' })
    if (response.ok) {
      console.log('[Studio] Switched to idle mode')
      // Refresh capabilities to update sidebar
      await capabilitiesStore.fetchCapabilities()
    }
  } catch (e) {
    console.warn('[Studio] Failed to switch to idle mode:', e)
  }
})

async function selectMode(mode: 'recorder' | 'mixer') {
  if (switching.value) return

  // Cancel any existing request
  if (switchAbortController) {
    switchAbortController.abort()
  }
  
  // Create new abort controller for this request
  switchAbortController = new AbortController()
  const currentController = switchAbortController // Capture reference for this request
  const signal = currentController.signal

  selectedMode.value = mode
  switching.value = true
  switchError.value = null
  
  try {
    // Call mode switch API to prepare device resources
    const response = await fetch(buildApiUrl(`/api/mode/${mode}`), { 
      method: 'POST',
      signal 
    })
    
    // Check if cancelled before proceeding
    if (signal.aborted) return
    
    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      throw new Error(data.detail || `Failed to switch to ${mode} mode`)
    }
    
    // Check again before navigation (in case cancelled during response parsing)
    if (signal.aborted) return
    
    // Navigate to the mode view
    router.push(`/${mode}`)
  } catch (e) {
    // Ignore abort errors - these are expected when user cancels
    if (e instanceof Error && e.name === 'AbortError') {
      console.log('[Studio] Mode switch cancelled by user')
      return
    }
    
    const message = e instanceof Error ? e.message : 'Failed to switch mode'
    switchError.value = message
    toast.error(message)
    console.error('Mode switch error:', e)
  } finally {
    // Only reset state if this request is still the current one
    // (prevents race condition when user cancels and quickly starts new request)
    if (switchAbortController === currentController) {
      switching.value = false
      switchAbortController = null
    }
  }
}

</script>

<template>
  <div class="studio">
    <!-- Ambient background effects -->
    <div class="studio__bg">
      <div class="studio__orb studio__orb--1"></div>
      <div class="studio__orb studio__orb--2"></div>
      <div class="studio__orb studio__orb--3"></div>
    </div>
    
    <div class="studio__content">
      <h1 class="studio__title">Preke Studio</h1>
      <p class="studio__subtitle">Select a mode to begin</p>
      
      <div class="studio__modes">
        <!-- Recorder Mode -->
        <button
          @click="selectMode('recorder')"
          :disabled="switching"
          class="studio__mode studio__mode--recorder"
          :class="{ 'studio__mode--selected': selectedMode === 'recorder' }"
        >
          <div class="studio__mode-icon">
            <svg v-if="switching && selectedMode === 'recorder'" class="animate-spin" fill="none" viewBox="0 0 24 24" width="32" height="32">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <!-- Recording circle icon -->
            <svg v-else fill="currentColor" viewBox="0 0 24 24" width="32" height="32">
              <circle cx="12" cy="12" r="8"/>
            </svg>
          </div>
          <div class="studio__mode-info">
            <h3 class="studio__mode-title">Recorder</h3>
            <p class="studio__mode-desc">
              {{ switching && selectedMode === 'recorder' ? 'Starting recorder...' : 'Multi-cam ISO recording' }}
            </p>
          </div>
        </button>
        
        <!-- Mixer Mode -->
        <button
          @click="selectMode('mixer')"
          :disabled="switching"
          class="studio__mode studio__mode--mixer"
          :class="{ 'studio__mode--selected': selectedMode === 'mixer' }"
        >
          <div class="studio__mode-icon">
            <svg v-if="switching && selectedMode === 'mixer'" class="animate-spin" fill="none" viewBox="0 0 24 24" width="32" height="32">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <!-- Video mixer icon (multi-screen layout) -->
            <svg v-else fill="none" stroke="currentColor" viewBox="0 0 24 24" width="32" height="32" stroke-width="1.8">
              <rect x="2" y="2" width="9" height="9" rx="1"/>
              <rect x="13" y="2" width="9" height="6" rx="1"/>
              <rect x="13" y="10" width="9" height="6" rx="1"/>
              <rect x="2" y="13" width="9" height="9" rx="1"/>
            </svg>
          </div>
          <div class="studio__mode-info">
            <h3 class="studio__mode-title">Mixer</h3>
            <p class="studio__mode-desc">
              {{ switching && selectedMode === 'mixer' ? 'Starting mixer...' : 'Live switching & streaming' }}
            </p>
          </div>
        </button>
      </div>
      
      <!-- Error message -->
      <div v-if="switchError" class="studio__error">
        {{ switchError }}
      </div>
    </div>
  </div>
</template>

<style scoped>
.studio {
  position: relative;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  overflow: hidden;
  background: var(--preke-bg);
}

/* Ambient background */
.studio__bg {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
}

.studio__orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(100px);
  opacity: 0.4;
  animation: orb-float 6s ease-in-out infinite;
}

.studio__orb--1 {
  width: 400px;
  height: 400px;
  top: -100px;
  right: -100px;
  background: radial-gradient(circle, rgba(224, 160, 48, 0.3) 0%, transparent 70%);
  animation-delay: 0s;
}

.studio__orb--2 {
  width: 300px;
  height: 300px;
  bottom: -50px;
  left: -50px;
  background: radial-gradient(circle, rgba(124, 58, 237, 0.2) 0%, transparent 70%);
  animation-delay: 2s;
}

.studio__orb--3 {
  width: 250px;
  height: 250px;
  top: 50%;
  left: 30%;
  background: radial-gradient(circle, rgba(212, 90, 90, 0.15) 0%, transparent 70%);
  animation-delay: 4s;
}

@keyframes orb-float {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50% { transform: translate(20px, -20px) scale(1.05); }
}

/* Content */
.studio__content {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.studio__title {
  font-size: 2.5rem;
  font-weight: 700;
  color: var(--preke-text);
  margin-bottom: 0.5rem;
}

.studio__subtitle {
  font-size: 1rem;
  color: var(--preke-text-muted);
  margin-bottom: 3rem;
}

/* Mode buttons */
.studio__modes {
  display: flex;
  gap: 1.5rem;
}

.studio__mode {
  width: 280px;
  height: 200px;
  border-radius: 1.25rem;
  border: 2px solid var(--preke-border);
  background: rgba(255, 255, 255, 0.03);
  backdrop-filter: blur(12px);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1.25rem;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.studio__mode:hover:not(:disabled) {
  transform: translateY(-4px);
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
}

.studio__mode:disabled {
  opacity: 0.7;
  cursor: wait;
}

/* Recorder styling */
.studio__mode--recorder {
  border-color: rgba(212, 90, 90, 0.3);
}

.studio__mode--recorder:hover:not(:disabled) {
  border-color: rgba(212, 90, 90, 0.6);
  background: rgba(212, 90, 90, 0.08);
  box-shadow: 
    0 20px 40px rgba(0, 0, 0, 0.3),
    0 0 30px rgba(212, 90, 90, 0.15);
}

.studio__mode--recorder.studio__mode--selected {
  border-color: var(--preke-red);
  background: rgba(212, 90, 90, 0.12);
  box-shadow: 
    0 0 40px rgba(212, 90, 90, 0.2),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
}

.studio__mode--recorder .studio__mode-icon {
  background: rgba(212, 90, 90, 0.2);
  color: var(--preke-red);
}

/* Mixer styling */
.studio__mode--mixer {
  border-color: rgba(124, 58, 237, 0.3);
}

.studio__mode--mixer:hover:not(:disabled) {
  border-color: rgba(124, 58, 237, 0.6);
  background: rgba(124, 58, 237, 0.08);
  box-shadow: 
    0 20px 40px rgba(0, 0, 0, 0.3),
    0 0 30px rgba(124, 58, 237, 0.15);
}

.studio__mode--mixer.studio__mode--selected {
  border-color: #7c3aed;
  background: rgba(124, 58, 237, 0.12);
  box-shadow: 
    0 0 40px rgba(124, 58, 237, 0.2),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
}

.studio__mode--mixer .studio__mode-icon {
  background: rgba(124, 58, 237, 0.2);
  color: #a78bfa;
}

/* Mode icon */
.studio__mode-icon {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.3s ease;
}

.studio__mode:hover .studio__mode-icon {
  transform: scale(1.1);
}

/* Mode info */
.studio__mode-info {
  text-align: center;
}

.studio__mode-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--preke-text);
  margin-bottom: 0.25rem;
}

.studio__mode-desc {
  font-size: 0.875rem;
  color: var(--preke-text-muted);
}

/* Error */
.studio__error {
  margin-top: 1.5rem;
  color: var(--preke-red);
  font-size: 0.875rem;
}

/* Spin animation */
.animate-spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
