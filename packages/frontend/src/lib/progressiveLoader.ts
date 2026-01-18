/**
 * Progressive Camera Loader
 * 
 * Loads cameras one at a time on poor connections to prevent network crashes.
 * Waits for each camera to stabilize before loading the next one.
 */

import { acquireConnection, getConnectionState, type WHEPConnection } from './whepConnectionManager'

interface LoadProgress {
  cameraId: string
  status: 'pending' | 'loading' | 'stable' | 'failed'
  startTime: number | null
  stableTime: number | null
}

const loadQueue: string[] = []
const loadProgress = new Map<string, LoadProgress>()
let isLoading = false

// Configuration
const STABILITY_WAIT_MS = 2000  // Wait 2 seconds for connection to stabilize
const MAX_LOAD_TIME_MS = 10000  // Max 10 seconds per camera before giving up

/**
 * Check if a connection is stable (connected for at least STABILITY_WAIT_MS)
 */
function isConnectionStable(cameraId: string): boolean {
  const conn = getConnectionState(cameraId)
  if (!conn || conn.state !== 'connected') return false
  
  if (!conn.lastConnectedAt) return false
  
  const connectedDuration = Date.now() - conn.lastConnectedAt
  return connectedDuration >= STABILITY_WAIT_MS
}

/**
 * Load next camera in queue
 */
async function loadNextCamera() {
  if (isLoading || loadQueue.length === 0) return
  
  const cameraId = loadQueue.shift()!
  const progress = loadProgress.get(cameraId)
  if (!progress) return
  
  isLoading = true
  progress.status = 'loading'
  progress.startTime = Date.now()
  
  console.log(`[ProgressiveLoader] Loading camera ${cameraId} (${loadQueue.length} remaining)`)
  
  try {
    // Acquire connection (this will create it if needed)
    await acquireConnection(cameraId, () => {
      // Connection state changed - check if stable
      const conn = getConnectionState(cameraId)
      if (conn && conn.state === 'connected' && isConnectionStable(cameraId)) {
        if (progress.status === 'loading') {
          progress.status = 'stable'
          progress.stableTime = Date.now()
          console.log(`[ProgressiveLoader] Camera ${cameraId} is stable`)
          
          // Load next camera after a short delay
          setTimeout(() => {
            isLoading = false
            loadNextCamera()
          }, 500)
        }
      }
    })
    
    // Wait for stability or timeout
    const startTime = Date.now()
    while (progress.status === 'loading') {
      if (isConnectionStable(cameraId)) {
        progress.status = 'stable'
        progress.stableTime = Date.now()
        console.log(`[ProgressiveLoader] Camera ${cameraId} stabilized after ${Date.now() - startTime}ms`)
        break
      }
      
      if (Date.now() - startTime > MAX_LOAD_TIME_MS) {
        progress.status = 'failed'
        console.warn(`[ProgressiveLoader] Camera ${cameraId} failed to stabilize within ${MAX_LOAD_TIME_MS}ms`)
        break
      }
      
      await new Promise(resolve => setTimeout(resolve, 100))
    }
    
  } catch (e) {
    console.error(`[ProgressiveLoader] Failed to load camera ${cameraId}:`, e)
    progress.status = 'failed'
  }
  
  isLoading = false
  
  // Load next camera if queue not empty
  if (loadQueue.length > 0) {
    setTimeout(() => loadNextCamera(), 500)
  }
}

/**
 * Load cameras progressively (one at a time)
 * 
 * @param cameraIds Array of camera IDs to load
 * @param useProgressive If false, load all at once (for good connections)
 */
export async function loadCamerasProgressive(
  cameraIds: string[],
  useProgressive: boolean = true
): Promise<void> {
  // Clear existing queue
  loadQueue.length = 0
  loadProgress.clear()
  
  if (!useProgressive) {
    // Load all at once for good connections
    console.log(`[ProgressiveLoader] Loading all ${cameraIds.length} cameras simultaneously`)
    await Promise.all(
      cameraIds.map(async (cameraId) => {
        try {
          await acquireConnection(cameraId, () => {})
        } catch (e) {
          console.warn(`[ProgressiveLoader] Failed to load ${cameraId}:`, e)
        }
      })
    )
    return
  }
  
  // Progressive loading for poor connections
  console.log(`[ProgressiveLoader] Loading ${cameraIds.length} cameras progressively`)
  
  // Initialize progress tracking
  cameraIds.forEach(cameraId => {
    loadProgress.set(cameraId, {
      cameraId,
      status: 'pending',
      startTime: null,
      stableTime: null
    })
  })
  
  // Add to queue
  loadQueue.push(...cameraIds)
  
  // Start loading
  loadNextCamera()
}

/**
 * Check if progressive loading is recommended based on connection quality
 */
export function shouldUseProgressiveLoading(connectionType: 'p2p' | 'relay' | 'unknown' | 'hls'): boolean {
  // Use progressive loading for relay connections (FRP) or unknown
  // P2P connections are fast enough to load all at once
  return connectionType === 'relay' || connectionType === 'unknown'
}

/**
 * Get loading progress for a camera
 */
export function getLoadProgress(cameraId: string): LoadProgress | null {
  return loadProgress.get(cameraId) || null
}

/**
 * Get all loading progress
 */
export function getAllLoadProgress(): Map<string, LoadProgress> {
  return new Map(loadProgress)
}
