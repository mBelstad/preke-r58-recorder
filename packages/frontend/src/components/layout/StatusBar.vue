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
      return 'bg-preke-green'
    case 'amber':
      return 'bg-preke-amber animate-pulse'
    case 'orange':
      return 'bg-preke-amber'
    case 'red':
      return 'bg-preke-red animate-pulse'
    default:
      return 'bg-preke-text-dim'
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
  <header class="h-10 bg-preke-bg-elevated border-b border-preke-bg-surface flex items-center justify-between px-4 text-sm">
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
            state === 'connected' ? 'text-preke-green' : '',
            state === 'degraded' ? 'text-preke-amber bg-preke-amber/10' : '',
            state === 'connecting' ? 'text-preke-amber' : '',
            state === 'disconnected' ? 'text-preke-red bg-preke-red/10' : '',
          ]"
        >
          {{ displayStatusLabel }}
        </span>
        <!-- Connection Method Indicator (P2P/Relay/LAN/VPS) -->
        <span 
          v-if="connectionMethod !== 'unknown'"
          :class="[
            'text-xs px-1.5 py-0.5 rounded bg-preke-bg-surface/50 flex items-center gap-1',
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
      <div class="flex items-center gap-2 text-preke-text-dim">
        <span>Inputs:</span>
        <div class="flex gap-1">
          <span class="w-4 h-4 rounded bg-preke-green text-[10px] flex items-center justify-center text-white font-bold">1</span>
          <span class="w-4 h-4 rounded bg-preke-green text-[10px] flex items-center justify-center text-white font-bold">2</span>
          <span class="w-4 h-4 rounded bg-preke-bg-surface text-[10px] flex items-center justify-center text-preke-text-dim font-bold">3</span>
          <span class="w-4 h-4 rounded bg-preke-bg-surface text-[10px] flex items-center justify-center text-preke-text-dim font-bold">4</span>
        </div>
      </div>
      
      <!-- Storage -->
      <div class="flex items-center gap-2 text-preke-text-dim">
        <span>Storage:</span>
        <div class="w-20 h-2 bg-preke-bg-surface rounded-full overflow-hidden">
          <div class="h-full bg-preke-green rounded-full" style="width: 35%"></div>
        </div>
        <span class="text-xs">256 GB</span>
      </div>
    </div>
    
    <!-- Right: Time -->
    <div class="flex items-center gap-4 text-preke-text-dim">
      <span>{{ formattedDate() }}</span>
      <span class="font-mono">{{ formattedTime() }}</span>
    </div>
  </header>
</template>

