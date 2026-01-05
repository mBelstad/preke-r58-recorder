<script setup lang="ts">
/**
 * StatusBar v2 - Clean, professional status display
 * Shows only real/meaningful data, no duplicates
 */
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useConnectionStatus } from '@/composables/useConnectionStatus'
import { useTailscaleStatus } from '@/composables/useTailscaleStatus'
import { useRecorderStore } from '@/stores/recorder'
import { useCapabilitiesStore } from '@/stores/capabilities'

const { state, latencyMs, reconnectAttempts } = useConnectionStatus()
const { connectionMethod, connectionLabel, connectionIcon, connectionColor } = useTailscaleStatus()
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

// Format time as HH:MM:SS
const formattedTime = computed(() => {
  return currentTime.value.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  })
})

// Active inputs - only show inputs with signal
const activeInputs = computed(() => {
  return recorderStore.inputs.filter(input => input.hasSignal)
})

// Total inputs detected
const totalInputs = computed(() => recorderStore.inputs.length)

// Inputs summary text
const inputsSummary = computed(() => {
  const active = activeInputs.value.length
  const total = totalInputs.value
  if (total === 0) return 'No inputs'
  if (active === 0) return 'No signal'
  return `${active}/${total} active`
})

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
    totalGB: Math.round(totalGB),
    percent,
    isLow: percent > 85,
    isCritical: percent > 95
  }
})

// Connection status styling
const connectionClass = computed(() => {
  switch (state.value) {
    case 'connected':
      return 'text-preke-green'
    case 'degraded':
      return 'text-preke-amber animate-pulse'
    case 'connecting':
      return 'text-preke-amber'
    case 'disconnected':
      return 'text-preke-red animate-pulse'
    default:
      return 'text-preke-text-muted'
  }
})

// Connection dot class
const connectionDotClass = computed(() => {
  switch (state.value) {
    case 'connected':
      return 'bg-preke-green'
    case 'degraded':
    case 'connecting':
      return 'bg-preke-amber animate-pulse'
    case 'disconnected':
      return 'bg-preke-red animate-pulse'
    default:
      return 'bg-preke-text-muted'
  }
})

// Connection status text
const connectionText = computed(() => {
  if (state.value === 'connected' && latencyMs.value) {
    return latencyMs.value < 100 ? 'Live' : `${latencyMs.value}ms`
  }
  if (state.value === 'connecting') return 'Connecting...'
  if (state.value === 'disconnected') {
    return reconnectAttempts.value > 0 ? `Retry ${reconnectAttempts.value}` : 'Offline'
  }
  if (state.value === 'degraded') return 'Slow'
  return 'Unknown'
})

// Connection tooltip
const connectionTooltip = computed(() => {
  if (state.value === 'connected' && latencyMs.value) {
    return `Connected • ${latencyMs.value}ms latency`
  }
  if (state.value === 'degraded' && latencyMs.value) {
    return `High latency: ${latencyMs.value}ms`
  }
  if (state.value === 'connecting') return 'Attempting to connect...'
  if (state.value === 'disconnected') return 'Connection lost'
  return ''
})

// Storage bar color
const storageBarClass = computed(() => {
  if (!storageInfo.value) return 'bg-preke-green'
  if (storageInfo.value.isCritical) return 'bg-preke-red'
  if (storageInfo.value.isLow) return 'bg-preke-amber'
  return 'bg-preke-green'
})
</script>

<template>
  <header class="status-bar">
    <!-- Left: Connection Status -->
    <div class="status-bar__section">
      <div 
        class="status-bar__connection"
        :title="connectionTooltip"
      >
        <span :class="['status-bar__dot', connectionDotClass]"></span>
        <span :class="['status-bar__label', connectionClass]">
          {{ connectionText }}
        </span>
        
        <!-- Connection method (P2P/Relay/LAN) - only show if not unknown -->
        <span 
          v-if="connectionMethod !== 'unknown' && state === 'connected'"
          class="status-bar__badge"
          :class="connectionColor"
        >
          {{ connectionIcon }} {{ connectionLabel }}
        </span>
      </div>
    </div>
    
    <!-- Center: Inputs & Storage (only if connected) -->
    <div v-if="state === 'connected'" class="status-bar__section status-bar__section--center">
      <!-- Active Inputs -->
      <div class="status-bar__item" :title="`${activeInputs.length} inputs with signal`">
        <span class="status-bar__item-icon">📹</span>
        <span class="status-bar__item-value" :class="{ 'text-preke-amber': activeInputs.length === 0 }">
          {{ inputsSummary }}
        </span>
      </div>
      
      <!-- Storage (only if we have data) -->
      <template v-if="storageInfo">
        <div class="status-bar__divider"></div>
        <div 
          class="status-bar__item"
          :title="`${storageInfo.freeGB} GB free of ${storageInfo.totalGB} GB`"
        >
          <span class="status-bar__item-icon">💾</span>
          <div class="status-bar__storage">
            <div class="status-bar__storage-bar">
              <div 
                :class="['status-bar__storage-fill', storageBarClass]"
                :style="{ width: `${storageInfo.percent}%` }"
              ></div>
            </div>
            <span 
              class="status-bar__item-value"
              :class="{ 'text-preke-amber': storageInfo.isLow, 'text-preke-red': storageInfo.isCritical }"
            >
              {{ storageInfo.freeGB }} GB
            </span>
          </div>
        </div>
      </template>
    </div>
    
    <!-- Placeholder when disconnected -->
    <div v-else class="status-bar__section status-bar__section--center">
      <span class="status-bar__placeholder">Waiting for connection...</span>
    </div>
    
    <!-- Right: Time -->
    <div class="status-bar__section status-bar__section--right">
      <span class="status-bar__time">{{ formattedTime }}</span>
    </div>
  </header>
</template>

<style scoped>
/* Import design system v2 variables */
@import '@/styles/design-system-v2.css';

.status-bar {
  height: 32px;
  background: var(--preke-bg-surface);
  border-bottom: 1px solid var(--preke-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--preke-space-md);
  font-size: var(--preke-text-sm);
  font-family: var(--preke-font-sans);
}

.status-bar__section {
  display: flex;
  align-items: center;
  gap: var(--preke-space-sm);
}

.status-bar__section--center {
  flex: 1;
  justify-content: center;
  gap: var(--preke-space-lg);
}

.status-bar__section--right {
  justify-content: flex-end;
}

/* Connection status */
.status-bar__connection {
  display: flex;
  align-items: center;
  gap: var(--preke-space-sm);
  cursor: help;
}

.status-bar__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-bar__label {
  font-weight: 500;
  font-size: var(--preke-text-xs);
}

.status-bar__badge {
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 2px 6px;
  font-size: 10px;
  font-weight: 500;
  border-radius: var(--preke-radius-sm);
  background: var(--preke-glass-bg-light);
  border: 1px solid var(--preke-border);
}

/* Status items */
.status-bar__item {
  display: flex;
  align-items: center;
  gap: var(--preke-space-xs);
}

.status-bar__item-icon {
  font-size: 12px;
  opacity: 0.7;
}

.status-bar__item-value {
  color: var(--preke-text-dim);
  font-size: var(--preke-text-xs);
}

.status-bar__divider {
  width: 1px;
  height: 12px;
  background: var(--preke-border);
}

/* Storage bar */
.status-bar__storage {
  display: flex;
  align-items: center;
  gap: var(--preke-space-xs);
}

.status-bar__storage-bar {
  width: 48px;
  height: 4px;
  background: var(--preke-bg-base);
  border-radius: 2px;
  overflow: hidden;
}

.status-bar__storage-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.3s ease;
}

/* Time */
.status-bar__time {
  font-family: var(--preke-font-mono);
  font-size: var(--preke-text-xs);
  color: var(--preke-text-muted);
  letter-spacing: 0.02em;
}

/* Placeholder */
.status-bar__placeholder {
  color: var(--preke-text-subtle);
  font-size: var(--preke-text-xs);
  font-style: italic;
}

/* Color utilities from design system */
.text-preke-green { color: var(--preke-green); }
.text-preke-amber { color: var(--preke-amber); }
.text-preke-red { color: var(--preke-red); }
.text-preke-text-muted { color: var(--preke-text-muted); }
.bg-preke-green { background-color: var(--preke-green); }
.bg-preke-amber { background-color: var(--preke-amber); }
.bg-preke-red { background-color: var(--preke-red); }
.bg-preke-text-muted { background-color: var(--preke-text-muted); }

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.animate-pulse {
  animation: pulse 2s ease-in-out infinite;
}
</style>

