<script setup lang="ts">
/**
 * StatusBar v2 - Full-width header with logo properly positioned
 */
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useConnectionStatus } from '@/composables/useConnectionStatus'
import { useTailscaleStatus } from '@/composables/useTailscaleStatus'
import { useRecorderStore } from '@/stores/recorder'
import { useCapabilitiesStore } from '@/stores/capabilities'
import { useTheme } from '@/composables/useTheme'
import { platform } from '@/lib/platform'
import PrekeStudioLogo from '@/components/shared/PrekeStudioLogo.vue'

// Platform detection for layout
const isElectron = platform.isElectron()
const isMacOS = platform.isMacOS()

const { state, latencyMs, reconnectAttempts } = useConnectionStatus()
const { connectionMethod, connectionLabel } = useTailscaleStatus()
const recorderStore = useRecorderStore()
const capabilitiesStore = useCapabilitiesStore()
const { theme, toggleTheme } = useTheme()

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
  if (!caps || !caps.storage_total_gb) return { percent: 0, freeGB: 0, isLow: false, isCritical: false }
  
  const totalGB = caps.storage_total_gb
  const freeGB = caps.storage_available_gb || 0
  const usedGB = totalGB - freeGB
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
  <header class="header" :class="{ 'header--recorder': currentMode === 'recorder', 'header--mixer': currentMode === 'mixer' }">
    <!-- Spacer for macOS traffic lights (only in Electron on macOS) -->
    <div v-if="isElectron && isMacOS" class="header__spacer"></div>
    
    <!-- Left: Status indicators -->
    <div class="header__left">
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
    </div>
    
    <!-- Center: Logo -->
    <div class="header__center">
      <PrekeStudioLogo class="header__logo" />
    </div>
    
    <!-- Right: Stats and time -->
    <div class="header__right">
      <!-- Stats when connected -->
      <template v-if="statusInfo.showDetails">
        <!-- Camera slots -->
        <div class="header__cameras" :title="`Camera inputs`">
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
        
        <div class="header__divider"></div>
      </template>
      
      <!-- Time -->
      <span class="header__time">{{ formattedTime }}</span>
      
      <!-- Theme Toggle -->
      <button
        @click="toggleTheme"
        class="header__theme-toggle"
        :title="theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'"
      >
        <svg v-if="theme === 'dark'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="header__theme-icon">
          <circle cx="12" cy="12" r="5"/>
          <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
        </svg>
        <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="header__theme-icon">
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
        </svg>
      </button>
    </div>
  </header>
</template>

<style scoped>
.header {
  position: relative;
  width: 100%;
  height: 64px; /* Increased from 56px to accommodate larger text and more padding */
  min-height: 64px;
  flex-shrink: 0;
  
  /* Darker glass effect */
  background: linear-gradient(
    180deg,
    rgba(18, 18, 20, 0.95) 0%,
    rgba(14, 14, 16, 0.98) 50%,
    rgba(12, 12, 14, 1) 100%
  );
  backdrop-filter: blur(20px) saturate(150%);
  -webkit-backdrop-filter: blur(20px) saturate(150%);
  
  /* Border and outside shadow for depth */
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  box-shadow: 
    /* Inner top highlight */
    inset 0 1px 0 rgba(255, 255, 255, 0.04),
    /* Outside shadow for depth and standout effect */
    0 4px 30px rgba(0, 0, 0, 0.5),
    0 8px 40px rgba(0, 0, 0, 0.3);
  
  display: flex;
  align-items: center;
  padding: 0 28px; /* Increased from 20px for more padding */
  gap: 20px;
  -webkit-app-region: drag;
  z-index: 100;
  transition: box-shadow 0.4s ease;
}

/* Mode glow - Recorder (red) */
.header--recorder {
  box-shadow: 
    inset 0 1px 0 rgba(255, 255, 255, 0.04),
    0 4px 30px rgba(0, 0, 0, 0.5),
    0 8px 40px rgba(0, 0, 0, 0.3),
    0 0 60px rgba(212, 90, 90, 0.15),
    0 0 100px rgba(212, 90, 90, 0.08);
}

/* Mode glow - Mixer (purple) */
.header--mixer {
  box-shadow: 
    inset 0 1px 0 rgba(255, 255, 255, 0.04),
    0 4px 30px rgba(0, 0, 0, 0.5),
    0 8px 40px rgba(0, 0, 0, 0.3),
    0 0 60px rgba(124, 58, 237, 0.15),
    0 0 100px rgba(124, 58, 237, 0.08);
}

/* Subtle top edge reflection */
.header::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(255, 255, 255, 0.06) 50%,
    transparent 100%
  );
  pointer-events: none;
}

.header__status,
.header__cameras,
.header__storage,
.header__mode {
  -webkit-app-region: no-drag;
}

/* Spacer for macOS traffic lights - only rendered in Electron on macOS via v-if */
.header__spacer {
  width: 70px;
  flex-shrink: 0;
}

/* Left section - status info */
.header__left {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 16px;
}

/* Center section - logo centered */
.header__center {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Logo */
.header__logo {
  flex-shrink: 0;
}

/* Right section - stats and time */
.header__right {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 16px;
}

/* Mode indicator - liquid glass pill */
.header__mode {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  border-radius: 10px;
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}

.header__mode--red {
  background: linear-gradient(
    135deg,
    rgba(212, 90, 90, 0.2) 0%,
    rgba(212, 90, 90, 0.1) 100%
  );
  border: 1px solid rgba(212, 90, 90, 0.35);
  box-shadow: 
    0 2px 10px rgba(212, 90, 90, 0.15),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
}

.header__mode--violet {
  background: linear-gradient(
    135deg,
    rgba(124, 58, 237, 0.2) 0%,
    rgba(124, 58, 237, 0.1) 100%
  );
  border: 1px solid rgba(124, 58, 237, 0.35);
  box-shadow: 
    0 2px 10px rgba(124, 58, 237, 0.15),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
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

/* Divider - subtle glass separator */
.header__divider {
  width: 1px;
  height: 24px;
  background: linear-gradient(
    180deg,
    transparent 0%,
    rgba(255, 255, 255, 0.1) 30%,
    rgba(255, 255, 255, 0.1) 70%,
    transparent 100%
  );
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
  border-radius: 6px;
  background: linear-gradient(
    145deg,
    rgba(0, 0, 0, 0.3) 0%,
    rgba(0, 0, 0, 0.2) 100%
  );
  border: 1px solid rgba(255, 255, 255, 0.06);
  box-shadow: 
    inset 0 1px 2px rgba(0, 0, 0, 0.2),
    0 1px 0 rgba(255, 255, 255, 0.03);
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
  background: linear-gradient(
    145deg,
    rgba(52, 211, 153, 0.25) 0%,
    rgba(52, 211, 153, 0.15) 100%
  );
  border-color: rgba(52, 211, 153, 0.5);
  box-shadow: 
    0 0 8px rgba(52, 211, 153, 0.2),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
}

.header__camera--active .header__camera-num {
  color: var(--preke-green);
}

.header__camera--recording {
  background: linear-gradient(
    145deg,
    rgba(212, 90, 90, 0.3) 0%,
    rgba(212, 90, 90, 0.2) 100%
  );
  border-color: rgba(212, 90, 90, 0.5);
  box-shadow: 
    0 0 10px rgba(212, 90, 90, 0.25),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
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
  background: linear-gradient(
    180deg,
    rgba(0, 0, 0, 0.4) 0%,
    rgba(0, 0, 0, 0.2) 100%
  );
  border-radius: 4px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.06);
  box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.2);
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

.header__time {
  font-family: var(--preke-font-mono);
  font-size: 14px;
  font-weight: 600;
  color: var(--preke-text);
}

/* Theme Toggle */
.header__theme-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  padding: 0;
  background: var(--preke-glass-light);
  border: 1px solid var(--preke-border);
  border-radius: var(--preke-radius-md);
  color: var(--preke-text-muted);
  cursor: pointer;
  transition: all var(--preke-transition-base);
  -webkit-app-region: no-drag;
  flex-shrink: 0;
}

.header__theme-toggle:hover {
  background: var(--preke-glass-hover);
  color: var(--preke-text);
  border-color: var(--preke-border-light);
}

.header__theme-toggle:active {
  transform: scale(0.95);
}

.header__theme-icon {
  width: 18px;
  height: 18px;
  stroke-width: 2;
}

/* Light mode styles for top bar */
[data-theme="light"] .header {
  /* Light glass effect */
  background: linear-gradient(
    180deg,
    rgba(255, 255, 255, 0.95) 0%,
    rgba(250, 250, 250, 0.98) 50%,
    rgba(245, 245, 245, 1) 100%
  );
  backdrop-filter: blur(20px) saturate(150%);
  -webkit-backdrop-filter: blur(20px) saturate(150%);
  
  /* Border and shadow for light mode */
  border-bottom: 1px solid rgba(0, 0, 0, 0.08);
  box-shadow: 
    /* Inner top highlight */
    inset 0 1px 0 rgba(255, 255, 255, 0.6),
    /* Outside shadow for depth */
    0 4px 30px rgba(0, 0, 0, 0.08),
    0 8px 40px rgba(0, 0, 0, 0.05);
}

[data-theme="light"] .header::before {
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(0, 0, 0, 0.04) 50%,
    transparent 100%
  );
}

/* Light mode - Recorder glow */
[data-theme="light"] .header--recorder {
  box-shadow: 
    inset 0 1px 0 rgba(255, 255, 255, 0.6),
    0 4px 30px rgba(0, 0, 0, 0.08),
    0 8px 40px rgba(0, 0, 0, 0.05),
    0 0 60px rgba(212, 90, 90, 0.12),
    0 0 100px rgba(212, 90, 90, 0.06);
}

/* Light mode - Mixer glow */
[data-theme="light"] .header--mixer {
  box-shadow: 
    inset 0 1px 0 rgba(255, 255, 255, 0.6),
    0 4px 30px rgba(0, 0, 0, 0.08),
    0 8px 40px rgba(0, 0, 0, 0.05),
    0 0 60px rgba(124, 58, 237, 0.12),
    0 0 100px rgba(124, 58, 237, 0.06);
}

/* Light mode - Active camera indicators (lighter background) */
[data-theme="light"] .header__camera--active {
  background: linear-gradient(
    145deg,
    rgba(52, 211, 153, 0.35) 0%,
    rgba(52, 211, 153, 0.25) 100%
  );
  border-color: rgba(52, 211, 153, 0.6);
  box-shadow: 
    0 0 8px rgba(52, 211, 153, 0.25),
    inset 0 1px 0 rgba(255, 255, 255, 0.3);
}

[data-theme="light"] .header__camera--recording {
  background: linear-gradient(
    145deg,
    rgba(212, 90, 90, 0.4) 0%,
    rgba(212, 90, 90, 0.3) 100%
  );
  border-color: rgba(212, 90, 90, 0.6);
  box-shadow: 
    0 0 10px rgba(212, 90, 90, 0.3),
    inset 0 1px 0 rgba(255, 255, 255, 0.3);
}
</style>
