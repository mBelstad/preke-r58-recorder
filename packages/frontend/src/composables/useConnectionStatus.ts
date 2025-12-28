/**
 * Connection Status Composable
 * 
 * Monitors API connection health and latency.
 * Provides real-time feedback for operators.
 */
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { r58Api } from '@/lib/api'

export type ConnectionState = 'connected' | 'connecting' | 'degraded' | 'disconnected'

const state = ref<ConnectionState>('connecting')
const latencyMs = ref<number | null>(null)
const lastCheck = ref<Date | null>(null)
const consecutiveFailures = ref(0)
const reconnectAttempts = ref(0)
const isChecking = ref(false)
const lastError = ref<string | null>(null)

const PING_INTERVAL = 5000 // 5 seconds
const DEGRADED_THRESHOLD = 500 // 500ms
const MAX_FAILURES_BEFORE_DISCONNECT = 3

let pingInterval: number | null = null

export function useConnectionStatus() {
  const statusLabel = computed(() => {
    switch (state.value) {
      case 'connected':
        return latencyMs.value && latencyMs.value > 200 
          ? `${latencyMs.value}ms` 
          : 'Live'
      case 'connecting':
        return 'Connecting...'
      case 'degraded':
        return `Slow (${latencyMs.value}ms)`
      case 'disconnected':
        return 'Offline'
      default:
        return 'Unknown'
    }
  })

  const statusColor = computed(() => {
    switch (state.value) {
      case 'connected':
        return 'emerald'
      case 'connecting':
        return 'amber'
      case 'degraded':
        return 'orange'
      case 'disconnected':
        return 'red'
      default:
        return 'zinc'
    }
  })

  const isConnected = computed(() => 
    state.value === 'connected' || state.value === 'degraded'
  )

  async function checkConnection() {
    if (isChecking.value) return
    isChecking.value = true

    const startTime = performance.now()
    
    try {
      await r58Api.getHealth()
      const endTime = performance.now()
      const roundTrip = Math.round(endTime - startTime)
      
      latencyMs.value = roundTrip
      lastCheck.value = new Date()
      consecutiveFailures.value = 0
      lastError.value = null
      
      // Reset reconnect attempts on successful connection
      if (reconnectAttempts.value > 0) {
        reconnectAttempts.value = 0
      }

      if (roundTrip > DEGRADED_THRESHOLD) {
        state.value = 'degraded'
      } else {
        state.value = 'connected'
      }
    } catch (error: any) {
      consecutiveFailures.value++
      lastError.value = error.message || 'Connection failed'
      
      if (consecutiveFailures.value >= MAX_FAILURES_BEFORE_DISCONNECT) {
        state.value = 'disconnected'
        latencyMs.value = null
        reconnectAttempts.value++
      } else {
        state.value = 'connecting'
      }
    } finally {
      isChecking.value = false
    }
  }

  function startMonitoring() {
    // Initial check
    checkConnection()
    
    // Periodic checks
    pingInterval = window.setInterval(checkConnection, PING_INTERVAL)
  }

  function stopMonitoring() {
    if (pingInterval) {
      clearInterval(pingInterval)
      pingInterval = null
    }
  }

  // Auto-start on first use
  onMounted(() => {
    if (!pingInterval) {
      startMonitoring()
    }
  })

  onUnmounted(() => {
    // Don't stop - other components may still need it
  })

  return {
    state,
    latencyMs,
    lastCheck,
    reconnectAttempts,
    lastError,
    statusLabel,
    statusColor,
    isConnected,
    checkConnection,
    startMonitoring,
    stopMonitoring,
  }
}

// Start monitoring globally on import
if (typeof window !== 'undefined') {
  const { startMonitoring } = useConnectionStatus()
  startMonitoring()
}

