/**
 * Connection Status Composable
 * 
 * Monitors API connection health and latency.
 * Provides real-time feedback for operators.
 * 
 * SINGLETON PATTERN: Uses lazy initialization to avoid TDZ issues in minified builds.
 * All module-level state is wrapped in getSingleton() to ensure refs are created
 * only when first accessed, not at module load time.
 */
import { ref, computed, onMounted, onUnmounted, watch, type Ref } from 'vue'
import { r58Api, hasDeviceConfigured } from '@/lib/api'

export type ConnectionState = 'connected' | 'connecting' | 'degraded' | 'disconnected'

// Lazy singleton initialization to avoid TDZ issues in minified builds
interface ConnectionStatusState {
  state: Ref<ConnectionState>
  latencyMs: Ref<number | null>
  lastCheck: Ref<Date | null>
  consecutiveFailures: Ref<number>
  reconnectAttempts: Ref<number>
  isChecking: Ref<boolean>
  lastError: Ref<string | null>
  pingInterval: number | null
}

let _singleton: ConnectionStatusState | null = null

function getSingleton(): ConnectionStatusState {
  if (!_singleton) {
    _singleton = {
      state: ref<ConnectionState>('connecting'),
      latencyMs: ref<number | null>(null),
      lastCheck: ref<Date | null>(null),
      consecutiveFailures: ref(0),
      reconnectAttempts: ref(0),
      isChecking: ref(false),
      lastError: ref<string | null>(null),
      pingInterval: null,
    }
  }
  return _singleton
}

const PING_INTERVAL_CONNECTED = 10000 // 10 seconds when connected
const PING_INTERVAL_DISCONNECTED = 30000 // 30 seconds when disconnected (slower to save bandwidth)
const DEGRADED_THRESHOLD = 500 // 500ms
const MAX_FAILURES_BEFORE_DISCONNECT = 3

// Network debug logging
const isNetworkDebugEnabled = (): boolean => {
  return import.meta.env.VITE_NETWORK_DEBUG === '1' || 
         (typeof window !== 'undefined' && (window as any).__NETWORK_DEBUG__ === true)
}

// Rate-limited logging (max 1 log per second per subsystem)
const logThrottle = new Map<string, number>()
const LOG_THROTTLE_MS = 1000

function networkDebugLog(subsystem: string, message: string, ...args: any[]): void {
  if (!isNetworkDebugEnabled()) return
  
  const now = Date.now()
  const lastLog = logThrottle.get(subsystem) || 0
  if (now - lastLog < LOG_THROTTLE_MS) return
  
  logThrottle.set(subsystem, now)
  console.log(`[NETWORK DEBUG ${subsystem}] ${message}`, ...args)
}

// Track request count for rate monitoring
let requestCount = 0
let requestCountStartTime = Date.now()

function trackRequest(): void {
  requestCount++
  const elapsed = Date.now() - requestCountStartTime
  if (elapsed >= 60000) {  // Every minute
    networkDebugLog('ConnectionStatus', `Request rate: ${requestCount} requests/minute`)
    requestCount = 0
    requestCountStartTime = Date.now()
  }
}

export function useConnectionStatus() {
  // Get singleton state (lazy initialization)
  const singleton = getSingleton()
  const { state, latencyMs, lastCheck, consecutiveFailures, reconnectAttempts, isChecking, lastError } = singleton

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
    // Don't check if no device is configured (Electron mode)
    if (!hasDeviceConfigured()) {
      state.value = 'disconnected'
      return
    }
    
    if (isChecking.value) return
    isChecking.value = true
    trackRequest()

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

      const newState = roundTrip > DEGRADED_THRESHOLD ? 'degraded' : 'connected'
      if (newState !== state.value) {
        networkDebugLog('ConnectionStatus', `State changed: ${state.value} -> ${newState} (latency: ${roundTrip}ms)`)
      }
      state.value = newState
    } catch (error: any) {
      consecutiveFailures.value++
      lastError.value = error.message || 'Connection failed'
      
      const newState = consecutiveFailures.value >= MAX_FAILURES_BEFORE_DISCONNECT 
        ? 'disconnected' 
        : 'connecting'
      
      if (newState !== state.value) {
        networkDebugLog('ConnectionStatus', `State changed: ${state.value} -> ${newState} (failures: ${consecutiveFailures.value})`)
      }
      
      if (newState === 'disconnected') {
        latencyMs.value = null
        reconnectAttempts.value++
      }
      state.value = newState
    } finally {
      isChecking.value = false
    }
  }

  function startMonitoring() {
    // Initial check
    checkConnection()
    
    // Use dynamic interval based on connection state
    updatePollingInterval()
  }

  function updatePollingInterval() {
    // Clear existing interval
    if (singleton.pingInterval) {
      clearInterval(singleton.pingInterval)
      singleton.pingInterval = null
    }
    
    // Choose interval based on connection state
    const interval = (state.value === 'disconnected' || state.value === 'connecting')
      ? PING_INTERVAL_DISCONNECTED  // 30s when offline
      : PING_INTERVAL_CONNECTED     // 10s when connected
    
    networkDebugLog('ConnectionStatus', `Setting polling interval to ${interval}ms (state: ${state.value})`)
    
    // Start new interval
    singleton.pingInterval = window.setInterval(checkConnection, interval)
  }

  function stopMonitoring() {
    if (singleton.pingInterval) {
      clearInterval(singleton.pingInterval)
      singleton.pingInterval = null
    }
  }
  
  // Watch state changes and update polling interval
  watch(state, () => {
    if (singleton.pingInterval) {
      updatePollingInterval()
    }
  })

  // Auto-start on first use
  onMounted(() => {
    if (!singleton.pingInterval) {
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

// Note: Monitoring is started when components use the composable via onMounted
// Don't auto-start here as it would run before device URL is initialized

