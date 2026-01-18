/**
 * Tailscale Status Composable
 * 
 * Monitors Tailscale P2P connection status for Electron app.
 * Only active when running in Electron with Tailscale available.
 * 
 * FIXED: State is now lazily initialized to avoid TDZ issues
 * in minified builds.
 */
import { ref, computed, onMounted, onUnmounted, type Ref } from 'vue'
import { isElectron, getDeviceUrl } from '@/lib/api'

export interface TailscaleStatus {
  installed: boolean
  running: boolean
  loggedIn: boolean
  selfIp?: string
  selfHostname?: string
  version?: string
  error?: string
}

export interface TailscaleDevice {
  id: string
  name: string
  hostname: string
  tailscaleIp: string
  online: boolean
  os?: string
  isP2P: boolean
}

export type ConnectionMethod = 'tailscale-p2p' | 'tailscale-relay' | 'lan' | 'frp' | 'unknown'

// Singleton state (lazily initialized)
let _status: Ref<TailscaleStatus | null> | null = null
let _connectedDevice: Ref<TailscaleDevice | null> | null = null
let _connectionMethod: Ref<ConnectionMethod> | null = null
let _isAvailable: Ref<boolean> | null = null
let _isChecking: Ref<boolean> | null = null
let _lastCheck: Ref<Date | null> | null = null

function getStatus(): Ref<TailscaleStatus | null> {
  if (!_status) _status = ref<TailscaleStatus | null>(null)
  return _status
}

function getConnectedDevice(): Ref<TailscaleDevice | null> {
  if (!_connectedDevice) _connectedDevice = ref<TailscaleDevice | null>(null)
  return _connectedDevice
}

function getConnectionMethod(): Ref<ConnectionMethod> {
  if (!_connectionMethod) _connectionMethod = ref<ConnectionMethod>('unknown')
  return _connectionMethod
}

function getIsAvailable(): Ref<boolean> {
  if (!_isAvailable) _isAvailable = ref(false)
  return _isAvailable
}

function getIsChecking(): Ref<boolean> {
  if (!_isChecking) _isChecking = ref(false)
  return _isChecking
}

function getLastCheck(): Ref<Date | null> {
  if (!_lastCheck) _lastCheck = ref<Date | null>(null)
  return _lastCheck
}

const CHECK_INTERVAL = 30000 // 30 seconds

let checkInterval: number | null = null

export function useTailscaleStatus() {
  const status = getStatus()
  const connectedDevice = getConnectedDevice()
  const connectionMethod = getConnectionMethod()
  const isAvailable = getIsAvailable()
  const isChecking = getIsChecking()
  const lastCheck = getLastCheck()
  const isTailscaleP2P = computed(() => connectionMethod.value === 'tailscale-p2p')
  const isTailscaleRelay = computed(() => connectionMethod.value === 'tailscale-relay')
  const isTailscale = computed(() => isTailscaleP2P.value || isTailscaleRelay.value)
  
  const connectionLabel = computed(() => {
    switch (connectionMethod.value) {
      case 'tailscale-p2p':
        return 'P2P'
      case 'tailscale-relay':
        return 'Relay'
      case 'lan':
        return 'LAN'
      case 'frp':
        return 'VPS'
      default:
        return ''
    }
  })

  const connectionIcon = computed(() => {
    switch (connectionMethod.value) {
      case 'tailscale-p2p':
        return '⚡' // Lightning for P2P
      case 'tailscale-relay':
        return '🔀' // Shuffle for relay
      case 'lan':
        return '🏠' // House for local
      case 'frp':
        return '☁️' // Cloud for VPS
      default:
        return ''
    }
  })

  const connectionColor = computed(() => {
    switch (connectionMethod.value) {
      case 'tailscale-p2p':
        return 'text-emerald-400' // Green for P2P (best)
      case 'tailscale-relay':
        return 'text-blue-400' // Blue for relay
      case 'lan':
        return 'text-cyan-400' // Cyan for LAN
      case 'frp':
        return 'text-orange-400' // Orange for VPS (less optimal)
      default:
        return 'text-zinc-400'
    }
  })

  /**
   * Determine connection method based on device URL and Tailscale status
   */
  function detectConnectionMethod(): ConnectionMethod {
    const deviceUrl = getDeviceUrl()
    
    if (!deviceUrl) return 'unknown'

    // Check for Tailscale IP patterns (100.x.x.x or fd7a:115c:)
    const tailscaleIPv4 = /100\.\d{1,3}\.\d{1,3}\.\d{1,3}/
    const tailscaleIPv6 = /fd7a:115c:/
    const tailscaleHostname = /\.ts\.net/

    if (tailscaleIPv4.test(deviceUrl) || tailscaleIPv6.test(deviceUrl) || tailscaleHostname.test(deviceUrl)) {
      // Using Tailscale - check if P2P or relay
      if (connectedDevice.value?.isP2P) {
        return 'tailscale-p2p'
      }
      return 'tailscale-relay'
    }

    // Check for FRP/VPS (goes through itagenten.no)
    if (deviceUrl.includes('itagenten.no') || deviceUrl.includes('r58-api')) {
      return 'frp'
    }

    // Check for local IPs
    const localPatterns = [
      /192\.168\./,
      /10\.\d{1,3}\./,
      /172\.(1[6-9]|2[0-9]|3[01])\./,
      /localhost/,
      /127\.0\.0\.1/,
    ]
    
    if (localPatterns.some(p => p.test(deviceUrl))) {
      return 'lan'
    }

    return 'unknown'
  }

  async function checkTailscaleStatus() {
    // Only check in Electron
    if (!isElectron() || !window.electronAPI?.getTailscaleStatus) {
      isAvailable.value = false
      return
    }

    if (isChecking.value) return
    isChecking.value = true

    try {
      status.value = await window.electronAPI.getTailscaleStatus()
      isAvailable.value = status.value.installed && status.value.running && status.value.loggedIn
      lastCheck.value = new Date()

      // If Tailscale is available, check for connected device
      if (isAvailable.value && window.electronAPI.findTailscaleDevices) {
        const devices = await window.electronAPI.findTailscaleDevices()
        
        // Find device matching current connection
        const deviceUrl = getDeviceUrl()
        if (deviceUrl) {
          connectedDevice.value = devices.find((d: TailscaleDevice) => 
            deviceUrl.includes(d.tailscaleIp) || deviceUrl.includes(d.hostname)
          ) || null
        }
      }

      // Update connection method
      connectionMethod.value = detectConnectionMethod()

    } catch (error) {
      console.error('[TailscaleStatus] Check failed:', error)
      isAvailable.value = false
    } finally {
      isChecking.value = false
    }
  }

  function startMonitoring() {
    // Initial check
    checkTailscaleStatus()

    // Periodic checks
    if (!checkInterval) {
      checkInterval = window.setInterval(checkTailscaleStatus, CHECK_INTERVAL)
    }
  }

  function stopMonitoring() {
    if (checkInterval) {
      clearInterval(checkInterval)
      checkInterval = null
    }
  }

  // Auto-start in Electron
  onMounted(() => {
    if (isElectron()) {
      startMonitoring()
    }
  })

  onUnmounted(() => {
    // Keep running for other components
  })

  return {
    status,
    connectedDevice,
    connectionMethod,
    isAvailable,
    isTailscale,
    isTailscaleP2P,
    isTailscaleRelay,
    connectionLabel,
    connectionIcon,
    connectionColor,
    checkTailscaleStatus,
    startMonitoring,
    stopMonitoring,
  }
}


