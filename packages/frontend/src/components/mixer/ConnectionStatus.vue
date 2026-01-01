<script setup lang="ts">
/**
 * ConnectionStatus Component
 * 
 * Displays connection health and provides recovery options:
 * - VDO.ninja iframe connection state
 * - MediaMTX connection status
 * - Network quality indicators
 * - Reconnect functionality
 * - Error messages and recovery actions
 */
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useMixerStore } from '@/stores/mixer'
import { toast } from '@/composables/useToast'

// Props
const props = defineProps<{
  vdoEmbed?: {
    isReady: { value: boolean }
    connectionState: { value: 'disconnected' | 'connecting' | 'connected' }
    lastError: { value: string | null }
    sendCommand: (action: string, target?: string, value?: unknown) => void
    getEventStats: () => { total: number; lastActivity: number | null }
  }
}>()

const mixerStore = useMixerStore()

// Local state
const showDetails = ref(false)
const lastActivityAgo = ref<string>('never')
const reconnectAttempts = ref(0)
const isReconnecting = ref(false)
const refreshTrigger = ref(0)  // Trigger for reactive updates

// Connection state from VDO embed
const connectionState = computed(() => props.vdoEmbed?.connectionState?.value || 'disconnected')
const isReady = computed(() => props.vdoEmbed?.isReady?.value || false)
const lastError = computed(() => props.vdoEmbed?.lastError?.value || null)

// Overall health status
type HealthStatus = 'healthy' | 'degraded' | 'error' | 'disconnected'

const healthStatus = computed<HealthStatus>(() => {
  // Access refreshTrigger to make this computed reactive to timer updates
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const _trigger = refreshTrigger.value
  
  // Check if we've received VDO.ninja events (more reliable than state)
  // Use global debug stats directly since it's more reliable
  const globalStats = (window as unknown as Record<string, { getStats?: () => { lastActivity: number | null } }>).__VDO_DEBUG__?.getStats?.()
  const hasRecentActivity = globalStats?.lastActivity && (Date.now() - globalStats.lastActivity < 30000)
  
  // If we have recent activity, consider it connected
  if (hasRecentActivity) return 'healthy'
  
  // Also check component-exposed stats as fallback
  const stats = props.vdoEmbed?.getEventStats?.()
  const hasComponentActivity = stats?.lastActivity && (Date.now() - stats.lastActivity < 30000)
  if (hasComponentActivity) return 'healthy'
  
  // Otherwise fall back to state-based check
  if (connectionState.value === 'disconnected' || !isReady.value) return 'disconnected'
  if (lastError.value) return 'error'
  if (connectionState.value === 'connecting') return 'degraded'
  return 'healthy'
})

// Status color
const statusColor = computed(() => {
  switch (healthStatus.value) {
    case 'healthy': return 'bg-r58-accent-success'
    case 'degraded': return 'bg-amber-500'
    case 'error': return 'bg-r58-accent-danger'
    case 'disconnected': return 'bg-r58-text-secondary'
    default: return 'bg-r58-text-secondary'
  }
})

// Status text
const statusText = computed(() => {
  switch (healthStatus.value) {
    case 'healthy': return 'Connected'
    case 'degraded': return 'Connecting...'
    case 'error': return 'Error'
    case 'disconnected': return 'Disconnected'
    default: return 'Unknown'
  }
})

// Update last activity timer
let activityInterval: number | null = null

function updateLastActivity() {
  // Increment refresh trigger to force computed properties to re-evaluate
  refreshTrigger.value++
  
  if (props.vdoEmbed) {
    const stats = props.vdoEmbed.getEventStats()
    if (stats.lastActivity) {
      const ago = Date.now() - stats.lastActivity
      if (ago < 1000) {
        lastActivityAgo.value = 'just now'
      } else if (ago < 60000) {
        lastActivityAgo.value = `${Math.floor(ago / 1000)}s ago`
      } else if (ago < 3600000) {
        lastActivityAgo.value = `${Math.floor(ago / 60000)}m ago`
      } else {
        lastActivityAgo.value = 'over 1h ago'
      }
    }
  }
}

onMounted(() => {
  updateLastActivity()
  activityInterval = window.setInterval(updateLastActivity, 1000)
})

onUnmounted(() => {
  if (activityInterval) {
    clearInterval(activityInterval)
  }
})

// Reconnect logic
async function attemptReconnect() {
  if (isReconnecting.value) return
  
  isReconnecting.value = true
  reconnectAttempts.value++
  
  toast.info('Attempting to reconnect...')
  
  try {
    // Refresh the iframe by sending a ping command
    if (props.vdoEmbed) {
      props.vdoEmbed.sendCommand('ping')
    }
    
    // Wait a moment for response
    await new Promise(resolve => setTimeout(resolve, 2000))
    
    if (isReady.value && !lastError.value) {
      toast.success('Reconnected successfully')
      reconnectAttempts.value = 0
    } else {
      toast.error('Reconnection failed. Try refreshing the page.')
    }
  } catch (err) {
    toast.error('Reconnection error')
    console.error('[ConnectionStatus] Reconnect error:', err)
  } finally {
    isReconnecting.value = false
  }
}

// Refresh page (last resort)
function refreshPage() {
  if (confirm('This will refresh the page and may interrupt active streams. Continue?')) {
    window.location.reload()
  }
}

// Toggle details panel
function toggleDetails() {
  showDetails.value = !showDetails.value
}

// Get stats for display
const eventStats = computed(() => {
  if (props.vdoEmbed) {
    return props.vdoEmbed.getEventStats()
  }
  return { total: 0, incoming: 0, outgoing: 0, lastActivity: null }
})
</script>

<template>
  <div class="connection-status" data-testid="connection-status">
    <!-- Compact status indicator -->
    <div 
      class="flex items-center gap-2 cursor-pointer"
      @click="toggleDetails"
    >
      <!-- Status dot -->
      <span 
        class="w-2 h-2 rounded-full"
        :class="[statusColor, { 'animate-pulse': healthStatus === 'degraded' }]"
        data-testid="status-indicator"
      ></span>
      
      <!-- Status text -->
      <span class="text-xs text-r58-text-secondary">
        {{ statusText }}
      </span>
      
      <!-- Error indicator -->
      <span 
        v-if="lastError" 
        class="text-xs text-r58-accent-danger"
        title="Click for details"
      >
        ⚠️
      </span>
      
      <!-- Expand/collapse -->
      <svg 
        class="w-3 h-3 text-r58-text-secondary transition-transform"
        :class="{ 'rotate-180': showDetails }"
        fill="none" stroke="currentColor" viewBox="0 0 24 24"
      >
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
      </svg>
    </div>
    
    <!-- Expanded details panel -->
    <div v-if="showDetails" class="mt-2 p-3 bg-r58-bg-tertiary rounded-lg text-xs space-y-2">
      <!-- Connection details -->
      <div class="grid grid-cols-2 gap-2">
        <div>
          <span class="text-r58-text-secondary">VDO.ninja:</span>
          <span class="ml-1 font-medium" :class="isReady ? 'text-r58-accent-success' : 'text-r58-accent-danger'">
            {{ isReady ? 'Ready' : 'Not Ready' }}
          </span>
        </div>
        
        <div>
          <span class="text-r58-text-secondary">State:</span>
          <span class="ml-1 font-medium">{{ connectionState }}</span>
        </div>
        
        <div>
          <span class="text-r58-text-secondary">Last activity:</span>
          <span class="ml-1">{{ lastActivityAgo }}</span>
        </div>
        
        <div>
          <span class="text-r58-text-secondary">Events:</span>
          <span class="ml-1">{{ eventStats.total }}</span>
        </div>
      </div>
      
      <!-- Error message -->
      <div v-if="lastError" class="p-2 bg-r58-accent-danger/10 border border-r58-accent-danger/30 rounded text-r58-accent-danger">
        <strong>Error:</strong> {{ lastError }}
      </div>
      
      <!-- Actions -->
      <div class="flex gap-2 pt-2 border-t border-r58-bg-tertiary">
        <button
          @click="attemptReconnect"
          :disabled="isReconnecting"
          class="btn btn-sm flex-1"
          :class="{ 'opacity-50': isReconnecting }"
        >
          {{ isReconnecting ? 'Reconnecting...' : '🔄 Reconnect' }}
        </button>
        
        <button
          @click="refreshPage"
          class="btn btn-sm"
          title="Refresh the page (last resort)"
        >
          🔃 Refresh
        </button>
      </div>
      
      <!-- Reconnect attempts -->
      <div v-if="reconnectAttempts > 0" class="text-r58-text-secondary text-center">
        Reconnect attempts: {{ reconnectAttempts }}
      </div>
    </div>
  </div>
</template>

