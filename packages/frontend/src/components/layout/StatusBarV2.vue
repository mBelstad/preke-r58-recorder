<script setup lang="ts">
/**
 * StatusBar v2 - Full-width header with logo and professional status display
 */
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useConnectionStatus } from '@/composables/useConnectionStatus'
import { useTailscaleStatus } from '@/composables/useTailscaleStatus'
import { useRecorderStore } from '@/stores/recorder'
import { useCapabilitiesStore } from '@/stores/capabilities'
import logoHorizontal from '@/assets/logo-studio-horizontal.svg'

const { state, latencyMs, reconnectAttempts } = useConnectionStatus()
const { connectionMethod, connectionLabel, connectionIcon } = useTailscaleStatus()
const recorderStore = useRecorderStore()
const capabilitiesStore = useCapabilitiesStore()

const currentTime = ref(new Date())
let timeInterval: number | null = null

onMounted(() => {
  timeInterval = window.setInterval(() => {
    currentTime.value = new Date()
  }, 1000)
})

onUnmounted(() => {
  if (timeInterval) clearInterval(timeInterval)
})

// Format time as HH:MM
const formattedTime = computed(() => {
  return currentTime.value.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  })
})

// Camera inputs - array of 4 slots
const cameraSlots = computed(() => {
  const inputs = recorderStore.inputs
  const slots = []
  for (let i = 0; i < 4; i++) {
    const input = inputs[i]
    slots.push({
      id: i,
      hasSignal: input?.hasSignal || false,
      isRecording: input?.isRecording || false,
      label: input?.label || `CAM ${i + 1}`
    })
  }
  return slots
})

// Active inputs count
const activeInputs = computed(() => {
  return recorderStore.inputs.filter(input => input.hasSignal).length
})

// Storage info from capabilities
const storageInfo = computed(() => {
  const caps = capabilitiesStore.capabilities
  if (!caps) return { percent: 0, freeGB: 0, isLow: false, isCritical: false }
  
  const usedGB = caps.storage_used_gb || 0
  const totalGB = caps.storage_total_gb || 1
  const freeGB = totalGB - usedGB
  const percent = Math.round((usedGB / totalGB) * 100)
  
  return {
    freeGB: Math.round(freeGB),
    percent,
    isLow: percent > 85,
    isCritical: percent > 95
  }
})

// Unified status
const statusInfo = computed(() => {
  const isConnected = state.value === 'connected'
  const isConnecting = state.value === 'connecting'
  const isDegraded = state.value === 'degraded'
  
  if (isConnected) {
    let text = 'Connected'
    if (connectionMethod.value !== 'unknown') {
      text = connectionLabel.value
    }
    if (latencyMs.value && latencyMs.value >= 100) {
      text += ` · ${latencyMs.value}ms`
    }
    return { dot: 'green', text, showDetails: true }
  }
  
  if (isConnecting) {
    const text = reconnectAttempts.value > 0 
      ? `Reconnecting (${reconnectAttempts.value})...` 
      : 'Connecting...'
    return { dot: 'amber', text, showDetails: false, pulse: true }
  }
  
  if (isDegraded) {
    return { 
      dot: 'amber', 
      text: `Slow · ${latencyMs.value}ms`, 
      showDetails: true 
    }
  }
  
  return { dot: 'red', text: 'Offline', showDetails: false, pulse: true }
})
</script>

<template>
  <header class="header">
    <!-- macOS traffic lights spacer - larger gap -->
    <div class="header__traffic-lights"></div>
    
    <!-- Logo -->
    <div class="header__logo">
      <img :src="logoHorizontal" alt="Preke Studio" />
    </div>
    
    <!-- Center: Status indicators -->
    <div class="header__center">
      <!-- Connection status -->
      <div class="header__status" :title="statusInfo.text">
        <span 
          class="header__dot"
          :class="[
            `header__dot--${statusInfo.dot}`,
            { 'header__dot--pulse': statusInfo.pulse }
          ]"
        ></span>
        <span class="header__status-text">{{ statusInfo.text }}</span>
      </div>
      
      <!-- Stats when connected -->
      <template v-if="statusInfo.showDetails">
        <!-- Divider -->
        <div class="header__divider"></div>
        
        <!-- Camera slots (4 placeholders) -->
        <div class="header__cameras" :title="`${activeInputs} of 4 inputs active`">
          <div 
            v-for="slot in cameraSlots" 
            :key="slot.id"
            class="header__camera"
            :class="{
              'header__camera--active': slot.hasSignal,
              'header__camera--recording': slot.isRecording
            }"
            :title="slot.label"
          >
            <svg viewBox="0 0 24 24" fill="currentColor">
              <path d="M17 10.5V7c0-.55-.45-1-1-1H4c-.55 0-1 .45-1 1v10c0 .55.45 1 1 1h12c.55 0 1-.45 1-1v-3.5l4 4v-11l-4 4z"/>
            </svg>
          </div>
        </div>
        
        <!-- Divider -->
        <div class="header__divider"></div>
        
        <!-- Storage bar -->
        <div class="header__storage" :title="`${storageInfo.freeGB} GB free`">
          <svg class="header__storage-icon" viewBox="0 0 24 24" fill="currentColor">
            <path d="M20 6H4c-1.1 0-2 .9-2 2v8c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2zm0 10H4V8h16v8zM6 10h9v4H6z"/>
          </svg>
          <div class="header__storage-track">
            <div 
              class="header__storage-fill"
              :class="{
                'header__storage-fill--ok': !storageInfo.isLow,
                'header__storage-fill--low': storageInfo.isLow && !storageInfo.isCritical,
                'header__storage-fill--critical': storageInfo.isCritical
              }"
              :style="{ width: `${storageInfo.percent}%` }"
            ></div>
          </div>
          <span class="header__storage-text">{{ storageInfo.freeGB }}GB</span>
        </div>
      </template>
    </div>
    
    <!-- Right: Time -->
    <div class="header__right">
      <span class="header__time">{{ formattedTime }}</span>
    </div>
  </header>
</template>

<style scoped>
.header {
  height: 64px;
  min-height: 64px;
  background: var(--preke-surface);
  border-bottom: 1px solid var(--preke-surface-border);
  display: flex;
  align-items: center;
  padding: 0 24px;
  gap: 24px;
  -webkit-app-region: drag;
}

.header__status,
.header__cameras,
.header__storage {
  -webkit-app-region: no-drag;
}

/* macOS traffic lights - extra wide for visibility */
.header__traffic-lights {
  width: 0;
  flex-shrink: 0;
}

:global(.electron-app) .header__traffic-lights {
  width: 80px; /* Extra space to not cover buttons */
}

:global(.electron-app.is-windows) .header__traffic-lights {
  width: 0;
}

/* Logo - bigger */
.header__logo {
  flex-shrink: 0;
}

.header__logo img {
  height: 44px;
  width: auto;
}

/* Center section */
.header__center {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 20px;
}

/* Connection status */
.header__status {
  display: flex;
  align-items: center;
  gap: 10px;
}

.header__dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.header__dot--green { background: var(--preke-green); box-shadow: 0 0 8px var(--preke-green); }
.header__dot--amber { background: var(--preke-amber); box-shadow: 0 0 8px var(--preke-amber); }
.header__dot--red { background: var(--preke-red); box-shadow: 0 0 8px var(--preke-red); }

.header__dot--pulse {
  animation: dot-pulse 2s ease-in-out infinite;
}

@keyframes dot-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(0.85); }
}

.header__status-text {
  font-size: 14px;
  font-weight: 500;
  color: var(--preke-text-muted);
}

/* Divider */
.header__divider {
  width: 1px;
  height: 28px;
  background: var(--preke-border);
}

/* Camera slots */
.header__cameras {
  display: flex;
  gap: 6px;
}

.header__camera {
  width: 28px;
  height: 22px;
  border-radius: 4px;
  background: var(--preke-bg);
  border: 1px solid var(--preke-border);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.header__camera svg {
  width: 14px;
  height: 14px;
  color: var(--preke-text-subtle);
  transition: all 0.2s ease;
}

.header__camera--active {
  background: var(--preke-green-bg);
  border-color: var(--preke-green);
}

.header__camera--active svg {
  color: var(--preke-green);
}

.header__camera--recording {
  background: var(--preke-red-bg);
  border-color: var(--preke-red);
  animation: camera-recording 1.5s ease-in-out infinite;
}

.header__camera--recording svg {
  color: var(--preke-red);
}

@keyframes camera-recording {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

/* Storage */
.header__storage {
  display: flex;
  align-items: center;
  gap: 10px;
}

.header__storage-icon {
  width: 18px;
  height: 18px;
  color: var(--preke-text-subtle);
}

.header__storage-track {
  width: 80px;
  height: 8px;
  background: var(--preke-bg);
  border-radius: 4px;
  overflow: hidden;
  border: 1px solid var(--preke-border);
}

.header__storage-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.5s ease;
}

.header__storage-fill--ok {
  background: linear-gradient(90deg, var(--preke-green), var(--preke-green-light));
}

.header__storage-fill--low {
  background: linear-gradient(90deg, var(--preke-amber), #f59e0b);
}

.header__storage-fill--critical {
  background: linear-gradient(90deg, var(--preke-red), var(--preke-red-light));
  animation: storage-critical 1s ease-in-out infinite;
}

@keyframes storage-critical {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

.header__storage-text {
  font-size: 13px;
  font-weight: 600;
  color: var(--preke-text-muted);
  min-width: 40px;
}

/* Right section */
.header__right {
  flex-shrink: 0;
}

.header__time {
  font-family: var(--preke-font-mono);
  font-size: 16px;
  font-weight: 600;
  color: var(--preke-text-muted);
  letter-spacing: 0.05em;
}
</style>
