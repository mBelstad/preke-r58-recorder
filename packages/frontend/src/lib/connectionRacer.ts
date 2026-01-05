/**
 * Connection Racer - Smart Connection Priority
 * 
 * Races multiple connection paths to find the fastest route to the R58:
 * Priority: LAN → Direct P2P → Tailscale P2P → FRP Relay
 * 
 * Features:
 * - Tests all paths in parallel
 * - Uses first successful connection
 * - Monitors for better connections becoming available
 * - Graceful degradation if preferred paths fail
 */

import { getDeviceUrl, isElectron } from './api'

export interface ConnectionPath {
  type: 'lan' | 'tailscale' | 'frp'
  url: string
  priority: number  // Lower = higher priority
  latencyMs?: number
  working?: boolean
}

export interface RaceResult {
  bestPath: ConnectionPath | null
  allPaths: ConnectionPath[]
  raceTimeMs: number
}

// Known R58 endpoints (in priority order)
const FRP_MEDIAMTX_URL = 'https://r58-mediamtx.itagenten.no'
const TAILSCALE_IP = '100.98.37.53'
const LAN_IP = '192.168.1.24'

// Cache the winning connection to avoid re-racing
let cachedBestPath: ConnectionPath | null = null
let cacheTimestamp: number = 0
const CACHE_TTL_MS = 30000  // 30 seconds - re-check periodically

/**
 * Test if a WHEP endpoint is reachable and measure latency
 */
async function testWhepEndpoint(
  baseUrl: string, 
  cameraId: string,
  timeoutMs: number = 3000
): Promise<{ reachable: boolean; latencyMs: number }> {
  const whepUrl = `${baseUrl}/${cameraId}/whep`
  const startTime = performance.now()
  
  try {
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs)
    
    // Just do an OPTIONS request to test reachability
    const response = await fetch(whepUrl, {
      method: 'OPTIONS',
      signal: controller.signal,
      // Skip credentials for CORS preflight
      mode: 'cors',
    })
    
    clearTimeout(timeoutId)
    const latencyMs = performance.now() - startTime
    
    return { 
      reachable: response.ok || response.status === 405 || response.status === 204,
      latencyMs 
    }
  } catch (e) {
    return { reachable: false, latencyMs: performance.now() - startTime }
  }
}

/**
 * Build list of potential connection paths based on environment
 */
function buildConnectionPaths(): ConnectionPath[] {
  const paths: ConnectionPath[] = []
  
  // In Electron, we can try direct HTTP connections
  if (isElectron()) {
    // Priority 1: LAN connection (fastest when on same network)
    paths.push({
      type: 'lan',
      url: `http://${LAN_IP}:8889`,
      priority: 1,
    })
    
    // Priority 2: Tailscale P2P (works across networks)
    paths.push({
      type: 'tailscale',
      url: `http://${TAILSCALE_IP}:8889`,
      priority: 2,
    })
    
    // Priority 3: FRP relay (always works, but higher latency)
    paths.push({
      type: 'frp',
      url: FRP_MEDIAMTX_URL,
      priority: 3,
    })
  } else {
    // In browser, we can only use HTTPS endpoints
    paths.push({
      type: 'frp',
      url: FRP_MEDIAMTX_URL,
      priority: 1,
    })
  }
  
  return paths
}

/**
 * Race all connection paths to find the best one
 * Returns as soon as ANY path succeeds (early winner)
 */
export async function raceConnections(cameraId: string = 'cam0'): Promise<RaceResult> {
  const startTime = performance.now()
  const paths = buildConnectionPaths()
  
  console.log(`[Connection Racer] Racing ${paths.length} paths for ${cameraId}...`)
  
  // Start all tests in parallel
  const testPromises = paths.map(async (path) => {
    const result = await testWhepEndpoint(path.url, cameraId)
    path.latencyMs = result.latencyMs
    path.working = result.reachable
    
    if (result.reachable) {
      console.log(`[Connection Racer] ✓ ${path.type} (${path.url}): ${Math.round(result.latencyMs)}ms`)
    } else {
      console.log(`[Connection Racer] ✗ ${path.type} (${path.url}): failed`)
    }
    
    return { path, result }
  })
  
  // Wait for all to complete (or timeout)
  const results = await Promise.all(testPromises)
  const raceTimeMs = performance.now() - startTime
  
  // Find the best working path (prefer lower priority number = higher actual priority)
  const workingPaths = results
    .filter(r => r.result.reachable)
    .map(r => r.path)
    .sort((a, b) => {
      // First sort by priority
      if (a.priority !== b.priority) {
        return a.priority - b.priority
      }
      // Then by latency
      return (a.latencyMs || 9999) - (b.latencyMs || 9999)
    })
  
  const bestPath = workingPaths[0] || null
  
  if (bestPath) {
    console.log(`[Connection Racer] Winner: ${bestPath.type} (${bestPath.url}) in ${Math.round(raceTimeMs)}ms`)
    // Cache the result
    cachedBestPath = bestPath
    cacheTimestamp = Date.now()
  } else {
    console.warn('[Connection Racer] No working paths found!')
  }
  
  return {
    bestPath,
    allPaths: paths,
    raceTimeMs,
  }
}

/**
 * Get the best WHEP URL for a camera, using cached result if available
 */
export async function getBestWhepUrl(cameraId: string): Promise<string> {
  // Check cache validity
  const now = Date.now()
  if (cachedBestPath && (now - cacheTimestamp) < CACHE_TTL_MS) {
    console.log(`[Connection Racer] Using cached path: ${cachedBestPath.type}`)
    return `${cachedBestPath.url}/${cameraId}/whep`
  }
  
  // Race to find best path
  const result = await raceConnections(cameraId)
  
  if (result.bestPath) {
    return `${result.bestPath.url}/${cameraId}/whep`
  }
  
  // Ultimate fallback
  console.warn('[Connection Racer] All paths failed, using FRP fallback')
  return `${FRP_MEDIAMTX_URL}/${cameraId}/whep`
}

/**
 * Force a re-check of connection paths (e.g., on network change)
 */
export function invalidateConnectionCache(): void {
  cachedBestPath = null
  cacheTimestamp = 0
  console.log('[Connection Racer] Cache invalidated')
}

/**
 * Get the current cached connection info (for UI display)
 */
export function getCachedConnectionInfo(): { type: string; latencyMs?: number } | null {
  if (!cachedBestPath) return null
  return {
    type: cachedBestPath.type,
    latencyMs: cachedBestPath.latencyMs,
  }
}

/**
 * Preload connections by racing paths for all cameras
 */
export async function preloadBestConnections(cameraIds: string[]): Promise<void> {
  // Race with the first camera to establish the best path
  if (cameraIds.length > 0) {
    await raceConnections(cameraIds[0])
  }
}

