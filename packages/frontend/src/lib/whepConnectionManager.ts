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
 */
function buildWhepUrl(cameraId: string): string {
  const deviceUrl = getDeviceUrl()
  
  // Prefer direct connection if available
  if (deviceUrl && !isUsingFrpFallback()) {
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
 */
async function detectConnectionType(pc: RTCPeerConnection, cameraId: string): Promise<'p2p' | 'relay' | 'unknown'> {
  for (let attempt = 0; attempt < 3; attempt++) {
    if (attempt > 0) {
      await new Promise(r => setTimeout(r, 200))
    }
    
    try {
      const stats = await pc.getStats()
      for (const report of stats.values()) {
        if (report.type === 'candidate-pair' && report.state === 'succeeded') {
          const remoteCandidate = stats.get(report.remoteCandidateId)
          const remoteIP = remoteCandidate?.address
          
          // Check candidate types
          if (remoteCandidate?.candidateType === 'relay') return 'relay'
          
          // Check known IPs
          if (remoteIP && RELAY_IPS.includes(remoteIP)) return 'relay'
          if (remoteIP && P2P_IPS.includes(remoteIP)) return 'p2p'
          
          // Check IP ranges
          if (remoteIP) {
            if (remoteIP.startsWith('100.')) return 'p2p'  // Tailscale
            if (remoteIP.startsWith('192.168.') || remoteIP.startsWith('10.') || remoteIP.startsWith('172.')) return 'p2p'
          }
          
          return 'relay'  // Default to relay for unknown
        }
      }
    } catch (e) {
      console.warn(`[WHEP Manager ${cameraId}] Failed to detect connection type:`, e)
    }
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
  
  const whepUrl = buildWhepUrl(cameraId)
  console.log(`[WHEP Manager ${cameraId}] Creating new connection: ${whepUrl}`)
  
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
    }
    connections.set(cameraId, conn)
  } else {
    conn.peerConnection = pc
    conn.state = 'connecting'
    conn.whepUrl = whepUrl
    conn.mediaStream = null
    conn.connectionType = 'unknown'
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
      console.log(`[WHEP Manager ${cameraId}] Connected (${conn!.connectionType})`)
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

