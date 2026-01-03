/**
 * Local Device Mode Detection
 * 
 * Detects when the app is running directly on the R58 device
 * and enables optimizations to reduce CPU/GPU load.
 * 
 * Detection methods:
 * 1. URL is localhost or 127.0.0.1
 * 2. Hostname matches R58 patterns (linaro-alip, etc.)
 * 3. User agent indicates ARM/Linux
 */

import { ref, computed, onMounted } from 'vue'

// Singleton state
const isLocalDevice = ref<boolean | null>(null)
const detectionComplete = ref(false)
const deviceHostname = ref<string | null>(null)

// Check if URL indicates local access
function isLocalUrl(): boolean {
  // In Electron with file:// protocol, hostname is empty - NOT local device
  if (window.location.protocol === 'file:') {
    return false
  }
  
  const host = window.location.hostname
  return host === 'localhost' || 
         host === '127.0.0.1' ||
         host === '0.0.0.0' ||
         host.startsWith('192.168.') // Local network access to device
}

// Check user agent for ARM Linux indicators
function isArmLinux(): boolean {
  const ua = navigator.userAgent.toLowerCase()
  return (ua.includes('linux') && ua.includes('aarch64')) ||
         (ua.includes('linux') && ua.includes('arm'))
}

// Try to detect device hostname from API
async function detectDeviceHostname(): Promise<string | null> {
  try {
    const response = await fetch('/api/system/info')
    if (response.ok) {
      const data = await response.json()
      return data.hostname || null
    }
  } catch {
    // Ignore errors
  }
  return null
}

// Known R58 device hostnames
const R58_HOSTNAMES = ['linaro-alip', 'preke-r58', 'r58-']

function isR58Hostname(hostname: string | null): boolean {
  if (!hostname) return false
  const lower = hostname.toLowerCase()
  return R58_HOSTNAMES.some(pattern => lower.includes(pattern))
}

export function useLocalDeviceMode() {
  /**
   * Whether we're running on the R58 device itself
   */
  const isOnDevice = computed(() => {
    if (isLocalDevice.value !== null) {
      return isLocalDevice.value
    }
    // Fallback: if URL is localhost, assume we're on device
    return isLocalUrl()
  })

  /**
   * Whether heavy features should be disabled
   * (VDO.ninja previews, high-res video decoding, etc.)
   */
  const isLiteMode = computed(() => isOnDevice.value)

  /**
   * Human-readable mode description
   */
  const modeLabel = computed(() => {
    if (isOnDevice.value) {
      return 'Local Device Mode'
    }
    return 'Remote Mode'
  })

  /**
   * Run detection on mount
   */
  async function detect() {
    if (detectionComplete.value) return

    // Quick check: if not localhost, we're definitely remote
    if (!isLocalUrl()) {
      isLocalDevice.value = false
      detectionComplete.value = true
      return
    }

    // Check user agent for ARM Linux
    if (isArmLinux()) {
      isLocalDevice.value = true
      detectionComplete.value = true
      console.log('[LocalDeviceMode] Detected ARM Linux - enabling Lite Mode')
      return
    }

    // Try to get hostname from API
    deviceHostname.value = await detectDeviceHostname()
    if (isR58Hostname(deviceHostname.value)) {
      isLocalDevice.value = true
      console.log(`[LocalDeviceMode] Detected R58 hostname: ${deviceHostname.value} - enabling Lite Mode`)
    } else {
      // localhost but not R58 - probably dev environment
      isLocalDevice.value = false
      console.log('[LocalDeviceMode] localhost but not R58 - staying in Remote Mode')
    }

    detectionComplete.value = true
  }

  onMounted(() => {
    detect()
  })

  return {
    isOnDevice,
    isLiteMode,
    modeLabel,
    deviceHostname,
    detectionComplete,
    detect,
  }
}

// Export singleton getters for use outside of components
export function getIsLiteMode(): boolean {
  return isLocalDevice.value === true || isLocalUrl()
}

export function getIsOnDevice(): boolean {
  return isLocalDevice.value === true || (isLocalUrl() && isArmLinux())
}

