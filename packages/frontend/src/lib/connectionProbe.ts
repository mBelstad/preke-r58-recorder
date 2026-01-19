/**
 * Connection Probe
 * 
 * Detects the best available connection method (LAN, Tailscale, FRP) by racing
 * all methods in parallel. Used during loading screens to pre-select connection
 * method and preload camera streams before UI is shown.
 */

import { getDeviceUrl, getFallbackUrl, getFrpUrl, setDeviceUrl } from './api'
import { acquireConnection, getConnectionState, type WHEPConnection } from './whepConnectionManager'

export type ConnectionMethod = 'lan' | 'tailscale' | 'frp' | 'hls'

export interface ProbeResult {
  method: ConnectionMethod
  url: string
  latency: number  // ms
  success: boolean
}

// Aggressive timeouts for fast detection
const PROBE_TIMEOUTS = {
  lan: 2000,       // 2s - should be instant if on same network
  tailscale: 2000, // 2s - P2P should be fast
  frp: 3000,       // 3s - relay has more latency
  hls: 5000        // 5s - only as last resort
}

/**
 * Probe a single connection method
 * Returns latency in ms if successful, throws on failure
 */
async function probeMethod(
  method: ConnectionMethod,
  url: string,
  signal: AbortSignal
): Promise<ProbeResult> {
  const start = performance.now()
  
  try {
    const response = await fetch(`${url}/health`, {
      method: 'GET',
      signal,
      cache: 'no-store'
    })
    
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    
    const latency = performance.now() - start
    return { method, url, latency, success: true }
  } catch (e) {
    throw { method, url, error: e }
  }
}

/**
 * Get device configuration URLs for all connection methods
 * Prioritizes LAN over Tailscale when both are available
 */
async function getDeviceConfig(): Promise<{
  lanUrl?: string
  tailscaleUrl?: string
  frpUrl?: string
}> {
  const config: {
    lanUrl?: string
    tailscaleUrl?: string
    frpUrl?: string
  } = {}
  
  // Helper to check if hostname is a private/local IP
  const isPrivateIp = (hostname: string): boolean => {
    if (hostname === 'localhost' || hostname === '127.0.0.1') return true
    if (hostname.startsWith('192.168.')) return true
    if (hostname.startsWith('10.')) return true
    if (hostname.startsWith('172.')) {
      const second = parseInt(hostname.split('.')[1], 10)
      return second >= 16 && second <= 31
    }
    return false
  }
  
  const isTailscaleIp = (hostname: string): boolean => {
    return hostname.startsWith('100.') || hostname.endsWith('.ts.net')
  }
  
  // Get primary device URL (LAN or Tailscale only - NOT public URLs)
  const deviceUrl = getDeviceUrl()
  let discoveredLanIp: string | null = null
  
  // Try to discover LAN IP from device network info
  // IMPORTANT: Only attempt LAN discovery if we're NOT connected via Tailscale
  // If connected via Tailscale, the client and device are likely on different subnets
  // and the LAN IP won't be directly routable, causing connection failures
  const isConnectedViaTailscale = deviceUrl && (
    new URL(deviceUrl).hostname.startsWith('100.') || 
    new URL(deviceUrl).hostname.endsWith('.ts.net')
  )
  
  if (deviceUrl && !isConnectedViaTailscale) {
    try {
      const controller = new AbortController()
      const timeout = setTimeout(() => controller.abort(), 2000)
      
      const response = await fetch(`${deviceUrl}/api/network/info`, {
        signal: controller.signal,
        cache: 'no-store'
      })
      clearTimeout(timeout)
      
      if (response.ok) {
        const networkInfo = await response.json()
        if (networkInfo.lan_ip) {
          discoveredLanIp = networkInfo.lan_ip
          // Build LAN URL using same protocol and port as current device URL
          try {
            const currentUrl = new URL(deviceUrl)
            const lanUrl = `${currentUrl.protocol}//${discoveredLanIp}:${currentUrl.port || 8000}`
            config.lanUrl = lanUrl
            console.log(`[ConnectionProbe] Discovered LAN IP: ${discoveredLanIp}, using ${lanUrl}`)
          } catch (e) {
            console.warn('[ConnectionProbe] Failed to build LAN URL:', e)
          }
        }
      }
    } catch (e) {
      // Network info endpoint not available or failed - continue with existing logic
      console.debug('[ConnectionProbe] Could not fetch network info:', e)
    }
  } else if (isConnectedViaTailscale) {
    console.log(`[ConnectionProbe] Connected via Tailscale - skipping LAN discovery (different subnet likely)`)
  }
  
  // If we didn't discover LAN via network info, check the configured device URL
  if (!config.lanUrl && deviceUrl) {
    try {
      const url = new URL(deviceUrl)
      // Only treat as direct connection if it's a private IP or Tailscale
      if (isTailscaleIp(url.hostname)) {
        config.tailscaleUrl = deviceUrl
      } else if (isPrivateIp(url.hostname)) {
        config.lanUrl = deviceUrl
      }
      // Public hostnames (like app.itagenten.no) are NOT direct connections
      // They'll be handled as FRP below
    } catch (e) {
      console.warn('[ConnectionProbe] Invalid device URL:', deviceUrl)
    }
  }
  
  // Get fallback URL (usually Tailscale)
  // Use as Tailscale config if not already set
  const fallbackUrl = getFallbackUrl()
  if (fallbackUrl && !config.tailscaleUrl) {
    try {
      const url = new URL(fallbackUrl)
      if (isTailscaleIp(url.hostname)) {
        config.tailscaleUrl = fallbackUrl
      }
    } catch (e) {
      console.warn('[ConnectionProbe] Invalid fallback URL:', fallbackUrl)
    }
  }
  
  // Get FRP URL
  const frpUrl = await getFrpUrl()
  if (frpUrl) {
    config.frpUrl = frpUrl
  } else {
    // Fallback to app.itagenten.no if no FRP URL configured
    config.frpUrl = 'https://app.itagenten.no'
  }
  
  return config
}

/**
 * Race all connection methods in parallel
 * Returns the first successful method with lowest latency
 */
export async function probeConnections(
  onStatus?: (status: string) => void
): Promise<ProbeResult> {
  const deviceConfig = await getDeviceConfig()
  
  const probes: Promise<ProbeResult>[] = []
  const controllers: AbortController[] = []
  
  // Build probe list based on available URLs
  // IMPORTANT: Order matters - LAN first (highest priority), then Tailscale, then FRP
  const methodConfigs: { method: ConnectionMethod; url: string; timeout: number }[] = []
  
  // LAN has highest priority - probe it first
  if (deviceConfig.lanUrl) {
    methodConfigs.push({ method: 'lan', url: deviceConfig.lanUrl, timeout: PROBE_TIMEOUTS.lan })
  }
  // Tailscale is second priority (P2P but over internet)
  if (deviceConfig.tailscaleUrl) {
    methodConfigs.push({ method: 'tailscale', url: deviceConfig.tailscaleUrl, timeout: PROBE_TIMEOUTS.tailscale })
  }
  // FRP is lowest priority (relay through VPS)
  if (deviceConfig.frpUrl) {
    methodConfigs.push({ method: 'frp', url: deviceConfig.frpUrl, timeout: PROBE_TIMEOUTS.frp })
  }
  
  if (methodConfigs.length === 0) {
    console.warn('[ConnectionProbe] No connection methods available, using HLS fallback')
    return {
      method: 'hls',
      url: 'https://app.itagenten.no',
      latency: 0,
      success: false
    }
  }
  
  // Start all probes in parallel
  for (const config of methodConfigs) {
    const controller = new AbortController()
    controllers.push(controller)
    
    onStatus?.(`Testing ${config.method.toUpperCase()} connection...`)
    
    // Wrap with timeout
    const timeoutId = setTimeout(() => controller.abort(), config.timeout)
    
    probes.push(
      probeMethod(config.method, config.url, controller.signal)
        .then(result => {
          clearTimeout(timeoutId)
          return result
        })
        .catch(error => {
          clearTimeout(timeoutId)
          throw error
        })
    )
  }
  
  // Remember the original device URL - don't overwrite a working connection
  const originalDeviceUrl = getDeviceUrl()
  
  // Helper to check if URL is a direct connection
  const isDirectUrl = (url: string): boolean => {
    try {
      const parsed = new URL(url)
      // Tailscale IPs (100.x.x.x) or private IPs
      if (parsed.hostname.startsWith('100.') || parsed.hostname.endsWith('.ts.net')) return true
      if (parsed.hostname === 'localhost' || parsed.hostname === '127.0.0.1') return true
      if (parsed.hostname.startsWith('192.168.') || parsed.hostname.startsWith('10.')) return true
      if (parsed.hostname.startsWith('172.')) {
        const second = parseInt(parsed.hostname.split('.')[1], 10)
        return second >= 16 && second <= 31
      }
      return false
    } catch { return false }
  }
  
  // Race with Promise.any - first success wins
  // However, we prioritize LAN over Tailscale even if Tailscale responds faster
  try {
    const results = await Promise.allSettled(probes)
    
    // Cancel remaining probes
    controllers.forEach(c => c.abort())
    
    // Find all successful results
    const successful: ProbeResult[] = []
    for (const result of results) {
      if (result.status === 'fulfilled') {
        successful.push(result.value)
      }
    }
    
    if (successful.length === 0) {
      throw new Error('All probes failed')
    }
    
    // Prioritize: LAN > Tailscale > FRP
    // Even if Tailscale responds faster, prefer LAN if both succeed
    successful.sort((a, b) => {
      const priority: Record<ConnectionMethod, number> = {
        lan: 1,
        tailscale: 2,
        frp: 3,
        hls: 4
      }
      return priority[a.method] - priority[b.method]
    })
    
    const winner = successful[0]
    
    console.log(`[ConnectionProbe] Winner: ${winner.method.toUpperCase()} (${Math.round(winner.latency)}ms)`)
    if (successful.length > 1) {
      console.log(`[ConnectionProbe] Also available: ${successful.slice(1).map(r => r.method.toUpperCase()).join(', ')}`)
    }
    onStatus?.('Connection established')
    
    // IMPORTANT: Don't switch from direct connection (Tailscale/LAN) to FRP
    // If original URL is direct and WHEP can use it, keep it
    // FRP winning just means the /health endpoint is faster, not that WHEP needs it
    if (originalDeviceUrl && isDirectUrl(originalDeviceUrl) && winner.method === 'frp') {
      console.log(`[ConnectionProbe] Keeping direct device URL despite FRP winning:`, originalDeviceUrl)
      // Keep the original device URL, but report the result
      // This allows WHEP to use direct connections while API uses FRP as needed
      return {
        method: winner.method,  // Report what won
        url: originalDeviceUrl, // But keep the original direct URL
        latency: winner.latency,
        success: true
      }
    }
    
    // Set the device URL to the winning method
    setDeviceUrl(winner.url)
    
    return winner
  } catch (e) {
    // All probes failed
    console.warn('[ConnectionProbe] All methods failed')
    
    // IMPORTANT: Don't overwrite a working device URL!
    // If we had a device URL before (e.g., Tailscale), keep using it
    // The probe failure might be temporary or due to /health endpoint issues
    if (originalDeviceUrl) {
      console.log('[ConnectionProbe] Keeping original device URL:', originalDeviceUrl)
      onStatus?.('Using existing connection')
      
      // Determine the method from the original URL
      let method: ConnectionMethod = 'lan'
      try {
        const url = new URL(originalDeviceUrl)
        if (url.hostname.startsWith('100.') || url.hostname.endsWith('.ts.net')) {
          method = 'tailscale'
        } else if (url.hostname.includes('itagenten.no')) {
          method = 'frp'
        }
      } catch {}
      
      return {
        method,
        url: originalDeviceUrl,
        latency: 0,
        success: false  // Probe failed but we have a URL
      }
    }
    
    // No original device URL - use FRP fallback
    onStatus?.('Using HLS fallback')
    const hlsUrl = deviceConfig.frpUrl || 'https://app.itagenten.no'
    setDeviceUrl(hlsUrl)
    
    return {
      method: 'hls',
      url: hlsUrl,
      latency: 0,
      success: false
    }
  }
}

/**
 * Preload camera connections using the selected method
 */
export async function preloadCameras(
  cameraIds: string[],
  selectedMethod: ProbeResult,
  onProgress: (loaded: number, total: number, cameraId: string) => void
): Promise<void> {
  console.log(`[ConnectionProbe] Preloading ${cameraIds.length} cameras via ${selectedMethod.method}`)
  
  // Preload connections sequentially to avoid overwhelming network
  // But use short timeouts since we already know the connection works
  for (let i = 0; i < cameraIds.length; i++) {
    const cameraId = cameraIds[i]
    onProgress(i, cameraIds.length, cameraId)
    
    try {
      // Acquire connection (will use the device URL we set)
      await acquireConnection(cameraId, () => {})
      
      // Wait for first frame (max 2s per camera)
      const deadline = Date.now() + 2000
      while (Date.now() < deadline) {
        const conn = getConnectionState(cameraId)
        if (conn?.mediaStream) {
          const tracks = conn.mediaStream.getVideoTracks()
          if (tracks.length > 0 && tracks[0].readyState === 'live') {
            console.log(`[ConnectionProbe] ${cameraId} ready`)
            break
          }
        }
        await new Promise(r => setTimeout(r, 100))
      }
    } catch (e) {
      console.warn(`[ConnectionProbe] Failed to preload ${cameraId}:`, e)
    }
  }
  
  onProgress(cameraIds.length, cameraIds.length, 'done')
}
