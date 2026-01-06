<script setup lang="ts">
/**
 * StatusBar v2 - Full-width header with logo properly positioned
 */
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useConnectionStatus } from '@/composables/useConnectionStatus'
import { useTailscaleStatus } from '@/composables/useTailscaleStatus'
import { useRecorderStore } from '@/stores/recorder'
import { useCapabilitiesStore } from '@/stores/capabilities'
import logoHorizontal from '@/assets/logo-studio-horizontal.svg'

const { state, latencyMs, reconnectAttempts } = useConnectionStatus()
const { connectionMethod, connectionLabel } = useTailscaleStatus()
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

// Current mode
const currentMode = computed(() => capabilitiesStore.capabilities?.current_mode || 'idle')

// Camera inputs - array of 4 slots
const cameraSlots = computed(() => {
  const inputs = recorderStore.inputs
  const slots = []
  for (let i = 0; i < 4; i++) {
    const input = inputs[i]
    slots.push({
      id: i + 1,
      hasSignal: input?.hasSignal || false,
      isRecording: input?.isRecording || false,
      label: input?.label || `CAM ${i + 1}`
    })
  }
  return slots
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

// Unified status - add "Mode" to connection type labels
const statusInfo = computed(() => {
  const isConnected = state.value === 'connected'
  const isConnecting = state.value === 'connecting'
  const isDegraded = state.value === 'degraded'
  
  if (isConnected) {
    let text = 'Connected'
    if (connectionMethod.value !== 'unknown') {
      // Add "Mode" to make it clearer (e.g., "Relay Mode", "P2P Mode")
      const method = connectionMethod.value
      if (method === 'relay') {
        text = 'Relay Mode'
      } else if (method === 'p2p') {
        text = 'P2P Mode'
      } else if (method === 'local') {
        text = 'Local Mode'
      } else {
        text = connectionLabel.value
      }
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

// Mode info for display - Full labels, no pulse (not live indicator)
const modeInfo = computed(() => {
  if (currentMode.value === 'recorder') {
    return { label: 'RECORDER', color: 'red' }
  }
  if (currentMode.value === 'mixer') {
    return { label: 'MIXER', color: 'violet' }
  }
  return null
})
</script>

<template>
  <header class="header">
    <!-- Spacer for macOS traffic lights (only in Electron) -->
    <div class="header__spacer"></div>
    
    <!-- Logo - positioned after spacer, not constrained -->
    <img :src="logoHorizontal" alt="Preke Studio" class="header__logo" />
    
    <!-- Center: Status indicators -->
    <div class="header__center">
      <!-- Mode indicator (if active) - no pulse, just shows current mode -->
      <div v-if="modeInfo" class="header__mode" :class="`header__mode--${modeInfo.color}`">
        <span class="header__mode-dot"></span>
        <span class="header__mode-label">{{ modeInfo.label }}</span>
      </div>
      
      <div v-if="modeInfo" class="header__divider"></div>
      
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
        <div class="header__divider"></div>
        
        <!-- Camera slots (4 numbered placeholders with camera icon) -->
        <div class="header__cameras" :title="`Camera inputs`">
          <!-- Camera icon label -->
          <svg class="header__cameras-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <path stroke-linecap="round" stroke-linejoin="round" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
          </svg>
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
            <span class="header__camera-num">{{ slot.id }}</span>
          </div>
        </div>
        
        <div class="header__divider"></div>
        
        <!-- Storage bar -->
        <div class="header__storage" :title="`${storageInfo.freeGB} GB free`">
          <svg class="header__storage-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <rect x="4" y="4" width="16" height="16" rx="2"/>
            <path d="M4 14h16"/>
            <circle cx="17" cy="17" r="1" fill="currentColor"/>
          </svg>
          <div class="header__storage-track">
            <div 
              class="header__storage-fill"
              :class="{
                'header__storage-fill--ok': !storageInfo.isLow,
                'header__storage-fill--low': storageInfo.isLow && !storageInfo.isCritical,
                'header__storage-fill--critical': storageInfo.isCritical
              }"
              :style="{ width: `${100 - storageInfo.percent}%` }"
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
  width: 100%;
  height: 56px;
  min-height: 56px;
  flex-shrink: 0;
  background: var(--preke-surface);
  border-bottom: 1px solid var(--preke-surface-border);
  display: flex;
  align-items: center;
  padding: 0 20px;
  gap: 20px;
  -webkit-app-region: drag;
}

.header__status,
.header__cameras,
.header__storage,
.header__mode {
  -webkit-app-region: no-drag;
}

/* Spacer for macOS traffic lights - dynamically sized */
.header__spacer {
  width: 0;
  flex-shrink: 0;
}

/* In Electron on macOS, make space for traffic light buttons */
/* Use multiple selectors to ensure it works in all contexts */
:global(.electron-app) .header__spacer {
  width: 70px; /* Space for traffic lights */
}

:global(html.electron-app) .header__spacer {
  width: 70px;
}

:global(body.electron-app) .header__spacer {
  width: 70px;
}

/* Also check for data attribute */
:global([data-electron="true"]) .header__spacer {
  width: 70px;
}

/* On Windows, no spacer needed */
:global(.electron-app.is-windows) .header__spacer,
:global(html.electron-app.is-windows) .header__spacer,
:global(.is-windows) .header__spacer {
  width: 0;
}

/* Logo - sized appropriately, never cut off */
.header__logo {
  height: 36px;
  width: auto;
  flex-shrink: 0;
  object-fit: contain;
}

/* Center section */
.header__center {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
}

/* Mode indicator */
.header__mode {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  border-radius: 8px;
}

.header__mode--red {
  background: rgba(212, 90, 90, 0.15);
  border: 1px solid rgba(212, 90, 90, 0.3);
}

.header__mode--violet {
  background: rgba(124, 58, 237, 0.15);
  border: 1px solid rgba(124, 58, 237, 0.3);
}

.header__mode-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.header__mode--red .header__mode-dot {
  background: var(--preke-red);
  box-shadow: 0 0 8px var(--preke-red);
}

.header__mode--violet .header__mode-dot {
  background: #7c3aed;
  box-shadow: 0 0 8px #7c3aed;
}

/* Mode dot no longer pulses - it's not a "live" indicator */

.header__mode-label {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.1em;
}

.header__mode--red .header__mode-label {
  color: var(--preke-red);
}

.header__mode--violet .header__mode-label {
  color: #a78bfa;
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
  font-size: 13px;
  font-weight: 500;
  color: var(--preke-text-muted);
}

/* Divider */
.header__divider {
  width: 1px;
  height: 24px;
  background: var(--preke-border);
}

/* Camera slots */
.header__cameras {
  display: flex;
  align-items: center;
  gap: 6px;
}

.header__cameras-icon {
  width: 18px;
  height: 18px;
  color: var(--preke-text-muted);
  flex-shrink: 0;
}

.header__camera {
  width: 22px;
  height: 22px;
  border-radius: 4px;
  background: var(--preke-bg);
  border: 1px solid var(--preke-border);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.header__camera-num {
  font-size: 10px;
  font-weight: 600;
  color: var(--preke-text-subtle);
}

.header__camera--active {
  background: var(--preke-green-bg);
  border-color: var(--preke-green);
}

.header__camera--active .header__camera-num {
  color: var(--preke-green);
}

.header__camera--recording {
  background: var(--preke-red-bg);
  border-color: var(--preke-red);
  animation: camera-recording 1.5s ease-in-out infinite;
}

.header__camera--recording .header__camera-num {
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
  gap: 8px;
}

.header__storage-icon {
  width: 16px;
  height: 16px;
  color: var(--preke-text-subtle);
}

.header__storage-track {
  width: 50px;
  height: 6px;
  background: var(--preke-bg);
  border-radius: 3px;
  overflow: hidden;
  border: 1px solid var(--preke-border);
}

.header__storage-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.5s ease;
}

.header__storage-fill--ok {
  background: linear-gradient(90deg, var(--preke-green), var(--preke-green-light, var(--preke-green)));
}

.header__storage-fill--low {
  background: linear-gradient(90deg, var(--preke-amber), #f59e0b);
}

.header__storage-fill--critical {
  background: linear-gradient(90deg, var(--preke-red), var(--preke-red-light, var(--preke-red)));
}

.header__storage-text {
  font-size: 11px;
  font-weight: 600;
  color: var(--preke-text-muted);
  min-width: 32px;
}

/* Right section */
.header__right {
  flex-shrink: 0;
}

.header__time {
  font-family: var(--preke-font-mono);
  font-size: 14px;
  font-weight: 600;
  color: var(--preke-text-muted);
  letter-spacing: 0.05em;
}
</style>
