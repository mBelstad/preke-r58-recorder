<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useConnectionStatus } from '@/composables/useConnectionStatus'
import { useTailscaleStatus } from '@/composables/useTailscaleStatus'

const { state, latencyMs, reconnectAttempts, statusLabel, statusColor } = useConnectionStatus()
const { connectionMethod, connectionLabel, connectionIcon, connectionColor, isTailscaleP2P } = useTailscaleStatus()

const currentTime = ref(new Date())

let timeInterval: number | null = null

onMounted(() => {
  timeInterval = window.setInterval(() => {
    currentTime.value = new Date()
  }, 1000)
})

onUnmounted(() => {
  if (timeInterval) {
    clearInterval(timeInterval)
  }
})

const formattedTime = () => {
  return currentTime.value.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  })
}

const formattedDate = () => {
  return currentTime.value.toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric'
  })
}

const connectionDotClass = computed(() => {
  switch (statusColor.value) {
    case 'emerald':
      return 'bg-emerald-500'
    case 'amber':
      return 'bg-amber-500 animate-pulse'
    case 'orange':
      return 'bg-orange-500'
    case 'red':
      return 'bg-red-500 animate-pulse'
    default:
      return 'bg-zinc-500'
  }
})

const connectionTooltip = computed(() => {
  if (state.value === 'connected' && latencyMs.value) {
    return `API connected, latency: ${latencyMs.value}ms`
  }
  if (state.value === 'degraded' && latencyMs.value) {
    return `High latency detected: ${latencyMs.value}ms`
  }
  if (state.value === 'connecting') {
    return 'Attempting to connect to API...'
  }
  if (state.value === 'disconnected') {
    const attempts = reconnectAttempts.value
    return attempts > 0 
      ? `Connection lost. Reconnect attempt ${attempts}...`
      : 'Connection lost. Reconnecting...'
  }
  return 'API status'
})

// Show reconnect attempts in status label when disconnected
const displayStatusLabel = computed(() => {
  if (state.value === 'disconnected' && reconnectAttempts.value > 0) {
    return `Offline (retry ${reconnectAttempts.value})`
  }
  return statusLabel.value
})

// Tooltip for connection method
const connectionMethodTooltip = computed(() => {
  switch (connectionMethod.value) {
    case 'tailscale-p2p':
      return 'Tailscale P2P: Direct connection via hole punching (best performance, no VPS cost)'
    case 'tailscale-relay':
      return 'Tailscale DERP: Relayed via Tailscale servers (free, good performance)'
    case 'lan':
      return 'Local Network: Direct LAN connection'
    case 'frp':
      return 'VPS Tunnel: Routed through your VPS (costs bandwidth)'
    default:
      return ''
  }
})
</script>

<template>
  <header class="h-10 bg-r58-bg-secondary border-b border-r58-bg-tertiary flex items-center justify-between px-4 text-sm">
    <!-- Left: Device info + Connection status -->
    <div class="flex items-center gap-4">
      <div 
        class="flex items-center gap-2 cursor-help"
        :title="connectionTooltip"
      >
        <span 
          :class="['w-2 h-2 rounded-full transition-colors', connectionDotClass]"
        ></span>
        <img src="/favicon.svg" alt="Preke" class="w-4 h-4 drop-shadow-[0_0_4px_rgba(255,255,255,0.4)]" />
        <span 
          :class="[
            'text-xs px-1.5 py-0.5 rounded',
            state === 'connected' ? 'text-emerald-400' : '',
            state === 'degraded' ? 'text-orange-400 bg-orange-500/10' : '',
            state === 'connecting' ? 'text-amber-400' : '',
            state === 'disconnected' ? 'text-red-400 bg-red-500/10' : '',
          ]"
        >
          {{ displayStatusLabel }}
        </span>
        <!-- Connection Method Indicator (P2P/Relay/LAN/VPS) -->
        <span 
          v-if="connectionMethod !== 'unknown'"
          :class="[
            'text-xs px-1.5 py-0.5 rounded bg-zinc-800/50 flex items-center gap-1',
            connectionColor
          ]"
          :title="connectionMethodTooltip"
        >
          <span>{{ connectionIcon }}</span>
          <span>{{ connectionLabel }}</span>
        </span>
      </div>
    </div>
    
    <!-- Center: Status indicators -->
    <div class="flex items-center gap-6">
      <!-- Inputs -->
      <div class="flex items-center gap-2 text-r58-text-secondary">
        <span>Inputs:</span>
        <div class="flex gap-1">
          <span class="w-4 h-4 rounded bg-r58-accent-success text-[10px] flex items-center justify-center text-white font-bold">1</span>
          <span class="w-4 h-4 rounded bg-r58-accent-success text-[10px] flex items-center justify-center text-white font-bold">2</span>
          <span class="w-4 h-4 rounded bg-r58-bg-tertiary text-[10px] flex items-center justify-center text-r58-text-secondary font-bold">3</span>
          <span class="w-4 h-4 rounded bg-r58-bg-tertiary text-[10px] flex items-center justify-center text-r58-text-secondary font-bold">4</span>
        </div>
      </div>
      
      <!-- Storage -->
      <div class="flex items-center gap-2 text-r58-text-secondary">
        <span>Storage:</span>
        <div class="w-20 h-2 bg-r58-bg-tertiary rounded-full overflow-hidden">
          <div class="h-full bg-r58-accent-success rounded-full" style="width: 35%"></div>
        </div>
        <span class="text-xs">256 GB</span>
      </div>
    </div>
    
    <!-- Right: Time -->
    <div class="flex items-center gap-4 text-r58-text-secondary">
      <span>{{ formattedDate() }}</span>
      <span class="font-mono">{{ formattedTime() }}</span>
    </div>
  </header>
</template>

