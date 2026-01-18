/**
 * Shared ICE Server Configuration
 * 
 * Centralized configuration for STUN/TURN servers used across the application.
 * This ensures consistency between MediaMTX and frontend WebRTC connections.
 */

import { getTurnCredentials } from './api'

/**
 * Default STUN servers (synchronized with MediaMTX configuration)
 */
export const DEFAULT_STUN_SERVERS: RTCIceServer[] = [
  { urls: 'stun:stun.l.google.com:19302' },
  { urls: 'stun:stun1.l.google.com:19302' },
  { urls: 'stun:stun.cloudflare.com:3478' }
]

/**
 * Get complete ICE server configuration including TURN
 * 
 * Returns STUN servers immediately, TURN is fetched in background
 * TURN is optional - connections work fine with just STUN in most cases
 */
export async function getIceServers(): Promise<RTCIceServer[]> {
  // Try to get TURN with a very short timeout - don't block on it
  try {
    const turnPromise = getTurnCredentials()
    const timeoutPromise = new Promise<null>((resolve) => setTimeout(() => resolve(null), 500))
    
    const turnServers = await Promise.race([turnPromise, timeoutPromise])
    if (turnServers) {
      return [...DEFAULT_STUN_SERVERS, ...turnServers]
    }
  } catch (e) {
    // TURN failed - continue with STUN only
  }
  
  return DEFAULT_STUN_SERVERS
}

/**
 * Get STUN-only servers (synchronous, no TURN)
 * Use when you need ICE servers immediately without waiting
 */
export function getStunServers(): RTCIceServer[] {
  return DEFAULT_STUN_SERVERS
}
