<script setup lang="ts">
/**
 * StatusBar v2 - Full-width header with logo and clean status display
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

// Active inputs count
const activeInputs = computed(() => {
  return recorderStore.inputs.filter(input => input.hasSignal).length
})

// Total inputs
const totalInputs = computed(() => recorderStore.inputs.length)

// Storage info from capabilities
const storageInfo = computed(() => {
  const caps = capabilitiesStore.capabilities
  if (!caps) return null
  
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

// Unified status - single source of truth
const statusInfo = computed(() => {
  const isConnected = state.value === 'connected'
  const isConnecting = state.value === 'connecting'
  const isDegraded = state.value === 'degraded'
  const isDisconnected = state.value === 'disconnected'
  
  if (isConnected) {
    // Show connection method and latency
    let text = 'Connected'
    if (connectionMethod.value !== 'unknown') {
      text = connectionLabel.value
    }
    if (latencyMs.value && latencyMs.value >= 100) {
      text += ` · ${latencyMs.value}ms`
    }
    return {
      dot: 'bg-green',
      text,
      icon: connectionIcon.value,
      showDetails: true
    }
  }
  
  if (isConnecting) {
    return {
      dot: 'bg-amber pulse',
      text: reconnectAttempts.value > 0 ? `Reconnecting (${reconnectAttempts.value})...` : 'Connecting...',
      icon: '',
      showDetails: false
    }
  }
  
  if (isDegraded) {
    return {
      dot: 'bg-amber',
      text: `Slow connection · ${latencyMs.value}ms`,
      icon: '⚠️',
      showDetails: true
    }
  }
  
  // Disconnected
  return {
    dot: 'bg-red pulse',
    text: 'Offline',
    icon: '',
    showDetails: false
  }
})
</script>

<template>
  <header class="header">
    <!-- macOS window controls spacer -->
    <div class="header__traffic-lights"></div>
    
    <!-- Logo -->
    <div class="header__logo">
      <img :src="logoHorizontal" alt="Preke Studio" />
    </div>
    
    <!-- Center: Status indicators -->
    <div class="header__center">
      <!-- Connection status -->
      <div class="header__status" :title="statusInfo.text">
        <span :class="['header__dot', statusInfo.dot]"></span>
        <span class="header__status-text">{{ statusInfo.text }}</span>
      </div>
      
      <!-- Quick stats when connected -->
      <template v-if="statusInfo.showDetails">
        <div class="header__divider"></div>
        
        <!-- Inputs -->
        <div class="header__stat" :title="`${activeInputs} of ${totalInputs} inputs active`">
          <span class="header__stat-icon">📹</span>
          <span class="header__stat-value" :class="{ 'text-amber': activeInputs === 0 && totalInputs > 0 }">
            {{ activeInputs }}/{{ totalInputs }}
          </span>
        </div>
        
        <!-- Storage -->
        <div v-if="storageInfo" class="header__stat" :title="`${storageInfo.freeGB} GB free`">
          <span class="header__stat-icon">💾</span>
          <div class="header__storage">
            <div class="header__storage-track">
              <div 
                class="header__storage-fill"
                :class="{
                  'bg-green': !storageInfo.isLow,
                  'bg-amber': storageInfo.isLow && !storageInfo.isCritical,
                  'bg-red': storageInfo.isCritical
                }"
                :style="{ width: `${storageInfo.percent}%` }"
              ></div>
            </div>
            <span class="header__stat-value">{{ storageInfo.freeGB }}GB</span>
          </div>
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
  height: 56px;
  min-height: 56px;
  background: var(--preke-surface);
  border-bottom: 1px solid var(--preke-surface-border);
  display: flex;
  align-items: center;
  padding: 0 20px;
  gap: 20px;
  /* Make it draggable for Electron window */
  -webkit-app-region: drag;
}

/* Make interactive elements not draggable */
.header__status,
.header__stat {
  -webkit-app-region: no-drag;
}

/* macOS traffic lights spacer */
.header__traffic-lights {
  width: 0;
  flex-shrink: 0;
}

:global(.electron-app) .header__traffic-lights {
  width: 60px;
}

:global(.electron-app.is-windows) .header__traffic-lights {
  width: 0;
}

/* Logo */
.header__logo {
  flex-shrink: 0;
}

.header__logo img {
  height: 36px;
  width: auto;
}

/* Center section */
.header__center {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
}

/* Connection status */
.header__status {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.header__dot.bg-green { background: var(--preke-green); }
.header__dot.bg-amber { background: var(--preke-amber); }
.header__dot.bg-red { background: var(--preke-red); }

.header__dot.pulse {
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.header__status-text {
  font-size: 13px;
  font-weight: 500;
  color: var(--preke-text-muted);
}

/* Divider */
.header__divider {
  width: 1px;
  height: 20px;
  background: var(--preke-border);
}

/* Stats */
.header__stat {
  display: flex;
  align-items: center;
  gap: 6px;
}

.header__stat-icon {
  font-size: 14px;
  opacity: 0.7;
}

.header__stat-value {
  font-size: 13px;
  color: var(--preke-text-muted);
  font-weight: 500;
}

.header__stat-value.text-amber {
  color: var(--preke-amber);
}

/* Storage */
.header__storage {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header__storage-track {
  width: 50px;
  height: 5px;
  background: var(--preke-bg);
  border-radius: 3px;
  overflow: hidden;
}

.header__storage-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.3s ease;
}

.header__storage-fill.bg-green { background: var(--preke-green); }
.header__storage-fill.bg-amber { background: var(--preke-amber); }
.header__storage-fill.bg-red { background: var(--preke-red); }

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
