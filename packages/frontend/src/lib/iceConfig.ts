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
 * Returns STUN servers + TURN servers (if available)
 */
export async function getIceServers(): Promise<RTCIceServer[]> {
  const turnServers = await getTurnCredentials()
  return [...DEFAULT_STUN_SERVERS, ...(turnServers || [])]
}
