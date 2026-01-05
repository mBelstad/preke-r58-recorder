/**
 * WHEP Connection Manager
 * 
 * Manages WebRTC WHEP connections to prevent duplicate connections
 * for the same camera stream. Each camera should have at most ONE
 * active WHEP connection per browser context.
 * 
 * Key features:
 * - Singleton per camera ID
 * - Connection sharing via reference counting
 * - Auto-cleanup when all references released
 * - Reconnection with exponential backoff
 */

import { getDeviceUrl, isUsingFrpFallback } from './api'

// Connection state for each camera
interface WHEPConnection {
  cameraId: string
  peerConnection: RTCPeerConnection
  mediaStream: MediaStream | null
  state: 'connecting' | 'connected' | 'disconnected' | 'failed'
  connectionType: 'p2p' | 'relay' | 'unknown'
  refCount: number  // Number of components using this connection
  whepUrl: string
  lastConnectedAt: number | null
  reconnectAttempts: number
  reconnectTimeout: ReturnType<typeof setTimeout> | null
  connectionStartTime: number | null  // For timing measurements
}

// Known IPs for connection type detection
const RELAY_IPS = ['65.109.32.111']
const P2P_IPS = ['100.98.37.53', '192.168.1.24']

// Reconnection configuration
const MAX_RECONNECT_ATTEMPTS = 5
const INITIAL_RECONNECT_DELAY = 1000  // 1 second
const MAX_RECONNECT_DELAY = 30000     // 30 seconds

// Active connections (singleton map)
const connections = new Map<string, WHEPConnection>()

// Event listeners per camera
const listeners = new Map<string, Set<(conn: WHEPConnection) => void>>()

/**
 * Build the WHEP URL for a camera
 * Prioritizes direct P2P connection over FRP tunnel
 */
function buildWhepUrl(cameraId: string): string {
  const deviceUrl = getDeviceUrl()
  const usingFrp = isUsingFrpFallback()
  
  // Use direct connection only if available AND FRP fallback not active
  // (FRP fallback means direct connection already failed)
  if (deviceUrl && !usingFrp) {
    try {
      const url = new URL(deviceUrl)
      return `http://${url.hostname}:8889/${cameraId}/whep`
    } catch (e) {
      console.warn(`[WHEP Manager] Invalid device URL, falling back to FRP`)
    }
  }
  
  // FRP fallback
  return `https://r58-mediamtx.itagenten.no/${cameraId}/whep`
}

/**
 * Detect connection type (P2P vs Relay)
 * 
 * With Tailscale userspace networking, the WebRTC remote candidate will show
 * 127.0.0.1 because tailscaled proxies locally. But the actual traffic goes
 * through Tailscale's P2P WireGuard tunnel.
 * 
 * Detection strategy:
 * 1. If WHEP URL uses Tailscale IP (100.x.x.x) -> P2P via Tailscale
 * 2. If WHEP URL uses LAN IP -> P2P via LAN  
 * 3. If WHEP URL uses FRP (itagenten.no) -> Relay
 */
async function detectConnectionType(pc: RTCPeerConnection, cameraId: string): Promise<'p2p' | 'relay' | 'unknown'> {
  const conn = connections.get(cameraId)
  if (!conn) return 'unknown'
  
  // Detection based on WHEP URL (most reliable with Tailscale userspace)
  try {
    const whepUrl = new URL(conn.whepUrl)
    const host = whepUrl.hostname
    
    // FRP tunnel = relay
    if (host.includes('itagenten.no')) {
      console.log(`[WHEP Manager ${cameraId}] Detected relay (FRP URL)`)
      return 'relay'
    }
    
    // Tailscale IP = P2P via Tailscale
    if (host.startsWith('100.')) {
      console.log(`[WHEP Manager ${cameraId}] Detected P2P (Tailscale IP: ${host})`)
      return 'p2p'
    }
    
    // LAN IP = P2P via LAN
    if (host.startsWith('192.168.') || host.startsWith('10.') || host.startsWith('172.')) {
      console.log(`[WHEP Manager ${cameraId}] Detected P2P (LAN IP: ${host})`)
      return 'p2p'
    }
  } catch (e) {
    console.warn(`[WHEP Manager ${cameraId}] Failed to parse WHEP URL:`, e)
  }
  
  // Fallback: check WebRTC stats (may be unreliable with Tailscale userspace)
  try {
    const stats = await pc.getStats()
    for (const report of stats.values()) {
      if (report.type === 'candidate-pair' && report.state === 'succeeded') {
        const remoteCandidate = stats.get(report.remoteCandidateId)
        
        // Explicit relay candidate type
        if (remoteCandidate?.candidateType === 'relay') {
          console.log(`[WHEP Manager ${cameraId}] Detected relay (TURN candidate)`)
          return 'relay'
        }
        
        // Check for VPS IP (explicit relay)
        const remoteIP = remoteCandidate?.address
        if (remoteIP && RELAY_IPS.includes(remoteIP)) {
          console.log(`[WHEP Manager ${cameraId}] Detected relay (VPS IP: ${remoteIP})`)
          return 'relay'
        }
      }
    }
  } catch (e) {
    console.warn(`[WHEP Manager ${cameraId}] Failed to get WebRTC stats:`, e)
  }
  
  // If we got here with a direct device URL, assume P2P
  const deviceUrl = getDeviceUrl()
  if (deviceUrl && !isUsingFrpFallback()) {
    console.log(`[WHEP Manager ${cameraId}] Assuming P2P (direct device URL configured)`)
    return 'p2p'
  }
  
  return 'unknown'
}

/**
 * Notify all listeners of a connection state change
 */
function notifyListeners(cameraId: string) {
  const conn = connections.get(cameraId)
  if (!conn) return
  
  const cameraListeners = listeners.get(cameraId)
  if (cameraListeners) {
    cameraListeners.forEach(listener => listener(conn))
  }
}

/**
 * Schedule a reconnection attempt with exponential backoff
 */
function scheduleReconnect(cameraId: string) {
  const conn = connections.get(cameraId)
  if (!conn) return
  
  if (conn.reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
    console.error(`[WHEP Manager ${cameraId}] Max reconnect attempts reached`)
    conn.state = 'failed'
    notifyListeners(cameraId)
    return
  }
  
  conn.reconnectAttempts++
  const delay = Math.min(
    INITIAL_RECONNECT_DELAY * Math.pow(2, conn.reconnectAttempts - 1),
    MAX_RECONNECT_DELAY
  )
  
  console.log(`[WHEP Manager ${cameraId}] Scheduling reconnect #${conn.reconnectAttempts} in ${delay}ms`)
  conn.state = 'connecting'
  notifyListeners(cameraId)
  
  if (conn.reconnectTimeout) {
    clearTimeout(conn.reconnectTimeout)
  }
  
  conn.reconnectTimeout = setTimeout(() => {
    createConnection(cameraId)
  }, delay)
}

/**
 * Create or reconnect a WHEP connection
 */
async function createConnection(cameraId: string): Promise<WHEPConnection> {
  let conn = connections.get(cameraId)
  
  // If connection exists and is active, just return it
  if (conn && (conn.state === 'connected' || conn.state === 'connecting')) {
    console.log(`[WHEP Manager ${cameraId}] Reusing existing connection (state: ${conn.state})`)
    return conn
  }
  
  // Wait for device URL to be set (handles race condition on startup)
  // Reduced wait time for faster loading
  let deviceUrl = getDeviceUrl()
  let attempts = 0
  while (!deviceUrl && attempts < 5) {
    console.log(`[WHEP Manager ${cameraId}] No device URL yet, waiting... (attempt ${attempts + 1})`)
    await new Promise(resolve => setTimeout(resolve, 100))
    deviceUrl = getDeviceUrl()
    attempts++
  }
  
  const startTime = performance.now()
  const whepUrl = buildWhepUrl(cameraId)
  console.log(`[WHEP Manager ${cameraId}] Creating connection to: ${whepUrl}`)
  console.log(`[WHEP Manager ${cameraId}] Device URL was: ${deviceUrl}`)
  
  // Clean up old connection if exists
  if (conn?.peerConnection) {
    conn.peerConnection.close()
  }
  
  // Create new peer connection
  const pc = new RTCPeerConnection({
    iceServers: [
      { urls: 'stun:stun.l.google.com:19302' },
      { urls: 'stun:stun1.l.google.com:19302' },
      { urls: 'stun:stun.cloudflare.com:3478' },
    ]
  })
  
  // Initialize or update connection record
  if (!conn) {
    conn = {
      cameraId,
      peerConnection: pc,
      mediaStream: null,
      state: 'connecting',
      connectionType: 'unknown',
      refCount: 0,
      whepUrl,
      lastConnectedAt: null,
      reconnectAttempts: conn?.reconnectAttempts || 0,
      reconnectTimeout: null,
      connectionStartTime: startTime,
    }
    connections.set(cameraId, conn)
  } else {
    conn.peerConnection = pc
    conn.state = 'connecting'
    conn.whepUrl = whepUrl
    conn.mediaStream = null
    conn.connectionType = 'unknown'
    conn.connectionStartTime = startTime
  }
  
  // Track events
  pc.ontrack = (event) => {
    if (event.streams[0]) {
      conn!.mediaStream = event.streams[0]
      console.log(`[WHEP Manager ${cameraId}] Received media stream`)
      notifyListeners(cameraId)
    }
  }
  
  pc.oniceconnectionstatechange = async () => {
    const state = pc.iceConnectionState
    console.log(`[WHEP Manager ${cameraId}] ICE state: ${state}`)
    
    if (state === 'connected' || state === 'completed') {
      conn!.state = 'connected'
      conn!.lastConnectedAt = Date.now()
      conn!.reconnectAttempts = 0  // Reset on success
      conn!.connectionType = await detectConnectionType(pc, cameraId)
      
      // Log connection time for performance analysis
      const elapsed = conn!.connectionStartTime 
        ? Math.round(performance.now() - conn!.connectionStartTime) 
        : 0
      console.log(`[WHEP Manager ${cameraId}] Connected (${conn!.connectionType}) in ${elapsed}ms`)
      notifyListeners(cameraId)
    } else if (state === 'failed') {
      conn!.state = 'failed'
      conn!.connectionType = 'unknown'
      notifyListeners(cameraId)
      
      // Only reconnect if there are still subscribers
      if (conn!.refCount > 0) {
        scheduleReconnect(cameraId)
      }
    } else if (state === 'disconnected') {
      // Wait for potential recovery
      setTimeout(() => {
        if (pc.iceConnectionState === 'disconnected' || pc.iceConnectionState === 'failed') {
          conn!.state = 'disconnected'
          notifyListeners(cameraId)
          
          if (conn!.refCount > 0) {
            scheduleReconnect(cameraId)
          }
        }
      }, 3000)
    }
  }
  
  // Add transceivers for receiving
  pc.addTransceiver('video', { direction: 'recvonly' })
  pc.addTransceiver('audio', { direction: 'recvonly' })
  
  try {
    // Create and send offer
    const offer = await pc.createOffer()
    await pc.setLocalDescription(offer)
    
    const response = await fetch(whepUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/sdp' },
      body: offer.sdp
    })
    
    if (!response.ok) {
      throw new Error(`WHEP request failed: ${response.status}`)
    }
    
    const answerSdp = await response.text()
    await pc.setRemoteDescription({ type: 'answer', sdp: answerSdp })
    
  } catch (e) {
    console.error(`[WHEP Manager ${cameraId}] Connection error:`, e)
    conn.state = 'failed'
    notifyListeners(cameraId)
    
    if (conn.refCount > 0) {
      scheduleReconnect(cameraId)
    }
  }
  
  return conn
}

/**
 * Acquire a connection to a camera
 * Increments reference count and creates connection if needed
 */
export async function acquireConnection(
  cameraId: string,
  onChange: (conn: WHEPConnection) => void
): Promise<WHEPConnection> {
  // Register listener
  if (!listeners.has(cameraId)) {
    listeners.set(cameraId, new Set())
  }
  listeners.get(cameraId)!.add(onChange)
  
  // Get or create connection
  let conn = connections.get(cameraId)
  if (!conn || conn.state === 'failed' || conn.state === 'disconnected') {
    conn = await createConnection(cameraId)
  }
  
  conn.refCount++
  console.log(`[WHEP Manager ${cameraId}] Acquired connection (refCount: ${conn.refCount})`)
  
  // Notify immediately with current state
  onChange(conn)
  
  return conn
}

/**
 * Release a connection reference
 * Decrements reference count and closes connection if no more references
 */
export function releaseConnection(
  cameraId: string,
  onChange: (conn: WHEPConnection) => void
): void {
  const conn = connections.get(cameraId)
  if (!conn) return
  
  // Remove listener
  const cameraListeners = listeners.get(cameraId)
  if (cameraListeners) {
    cameraListeners.delete(onChange)
    if (cameraListeners.size === 0) {
      listeners.delete(cameraId)
    }
  }
  
  // Decrement ref count
  conn.refCount = Math.max(0, conn.refCount - 1)
  console.log(`[WHEP Manager ${cameraId}] Released connection (refCount: ${conn.refCount})`)
  
  // Close connection if no more references
  if (conn.refCount === 0) {
    console.log(`[WHEP Manager ${cameraId}] Closing unused connection`)
    
    if (conn.reconnectTimeout) {
      clearTimeout(conn.reconnectTimeout)
    }
    
    conn.peerConnection.close()
    connections.delete(cameraId)
  }
}

/**
 * Get current connection state for a camera (read-only)
 */
export function getConnectionState(cameraId: string): WHEPConnection | undefined {
  return connections.get(cameraId)
}

/**
 * Force reconnect a camera (useful for manual retry)
 */
export function forceReconnect(cameraId: string): void {
  const conn = connections.get(cameraId)
  if (!conn) return
  
  console.log(`[WHEP Manager ${cameraId}] Force reconnecting...`)
  conn.reconnectAttempts = 0  // Reset attempts for manual retry
  createConnection(cameraId)
}

/**
 * Preload WHEP connections for multiple cameras
 * Starts connections without waiting, returns a promise that resolves when all have first frame
 */
export async function preloadConnections(cameraIds: string[]): Promise<void> {
  console.log(`[WHEP Manager] Preloading ${cameraIds.length} connections: ${cameraIds.join(', ')}`)
  const startTime = performance.now()
  
  // Start all connections in parallel (don't wait for each)
  const connectionPromises = cameraIds.map(async (cameraId) => {
    try {
      await createConnection(cameraId)
      
      // Wait for media stream to be available (with timeout)
      const conn = connections.get(cameraId)
      if (!conn) return
      
      // Wait up to 3 seconds for first frame
      for (let i = 0; i < 30; i++) {
        if (conn.mediaStream && conn.mediaStream.getVideoTracks().length > 0) {
          const track = conn.mediaStream.getVideoTracks()[0]
          if (track.readyState === 'live') {
            console.log(`[WHEP Manager ${cameraId}] Stream ready after ${Math.round(performance.now() - startTime)}ms`)
            return
          }
        }
        await new Promise(r => setTimeout(r, 100))
      }
      console.log(`[WHEP Manager ${cameraId}] Stream timeout (3s) - continuing anyway`)
    } catch (e) {
      console.warn(`[WHEP Manager ${cameraId}] Preload failed:`, e)
    }
  })
  
  await Promise.all(connectionPromises)
  console.log(`[WHEP Manager] All preloads complete in ${Math.round(performance.now() - startTime)}ms`)
}

/**
 * Check if a camera has video ready
 */
export function hasVideoReady(cameraId: string): boolean {
  const conn = connections.get(cameraId)
  if (!conn?.mediaStream) return false
  const tracks = conn.mediaStream.getVideoTracks()
  return tracks.length > 0 && tracks[0].readyState === 'live'
}

/**
 * Get all active connections (for debugging)
 */
export function getActiveConnections(): Map<string, { state: string; refCount: number; type: string }> {
  const result = new Map()
  connections.forEach((conn, id) => {
    result.set(id, {
      state: conn.state,
      refCount: conn.refCount,
      type: conn.connectionType
    })
  })
  return result
}

// Export types
export type { WHEPConnection }

