/**
 * API client with retry logic and error handling for R58
 */

import { getCameraLabel } from '@/lib/cameraLabels'

// ============================================
// Electron Integration Types
// ============================================

declare global {
  interface Window {
    electronAPI?: {
      getDeviceUrl: () => Promise<string | null>
      getDevices: () => Promise<DeviceConfig[]>
      getActiveDevice: () => Promise<DeviceConfig | null>
      addDevice: (name: string, url: string, fallbackUrl?: string) => Promise<DeviceConfig>
      removeDevice: (deviceId: string) => Promise<boolean>
      setActiveDevice: (deviceId: string) => Promise<boolean>
      updateDevice: (deviceId: string, updates: { name?: string; url?: string; fallbackUrl?: string }) => Promise<DeviceConfig | null>
      onDeviceChanged: (callback: (device: DeviceConfig | null) => void) => () => void
      onNavigate: (callback: (path: string) => void) => () => void
      onExportSupportBundle: (callback: () => void) => () => void
      getAppInfo: () => Promise<AppInfo>
      exportSupportBundle: () => Promise<string | null>
      openExternal: (url: string) => Promise<boolean>
      log: {
        debug: (...args: unknown[]) => void
        info: (...args: unknown[]) => void
        warn: (...args: unknown[]) => void
        error: (...args: unknown[]) => void
      }
      isElectron: boolean
      platform: string
    }
    /** Runtime device URL set by Electron preload */
    __R58_DEVICE_URL__?: string
  }
}

interface DeviceConfig {
  id: string
  name: string
  url: string
  fallbackUrl?: string
  lastConnected?: string
  createdAt: string
}

interface AppInfo {
  version: string
  electron: string
  chrome: string
  node: string
  platform: string
  arch: string
}

// ============================================
// Device URL Management
// ============================================

/** Cached device URL for synchronous access */
let cachedDeviceUrl: string | null = null

/** Cached FRP fallback URL from device configuration */
let cachedFrpUrl: string | null = null

/** Cached secondary fallback URL (e.g. Tailscale) */
let cachedFallbackUrl: string | null = null

/** Whether we're currently using secondary fallback */
let usingFallbackUrl = false

/** Whether we're currently using FRP fallback (device unreachable) */
let usingFrpFallback = false

/** Track consecutive connection failures to trigger fallback */
let consecutiveFailures = 0
const FAILURES_BEFORE_FALLBACK = 2

/**
 * Get FRP fallback URL from device configuration
 * Returns null if device doesn't provide FRP URL
 */
async function getFrpUrl(): Promise<string | null> {
  // If already cached, return it
  if (cachedFrpUrl) {
    return cachedFrpUrl
  }

  const deviceUrl = getDeviceUrl()
  if (!deviceUrl) {
    return null
  }

  try {
    // Try to fetch FRP URL from device config endpoint
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), 3000)
    
    const response = await fetch(`${deviceUrl}/api/config`, {
      signal: controller.signal,
      mode: 'cors',
      cache: 'no-cache'
    })
    clearTimeout(timeout)
    
    if (response.ok) {
      const config = await response.json()
      if (config.frp_url || config.frp_api_url) {
        cachedFrpUrl = config.frp_url || config.frp_api_url
        console.log('[API] FRP URL configured:', cachedFrpUrl)
        return cachedFrpUrl
      }
    }
  } catch (e) {
    // Device doesn't support /api/config or not reachable
    console.log('[API] Device does not provide FRP URL configuration')
  }
  
  return null
}

/**
 * Initialize the device URL from Electron
 * Should be called early in app startup
 */
export async function initializeDeviceUrl(): Promise<string | null> {
  if (window.electronAPI) {
    try {
      const activeDevice = await window.electronAPI.getActiveDevice()
      cachedDeviceUrl = activeDevice?.url || await window.electronAPI.getDeviceUrl()
      cachedFallbackUrl = activeDevice?.fallbackUrl || null
      window.__R58_DEVICE_URL__ = cachedDeviceUrl || undefined
      console.log('[API] Device URL initialized:', cachedDeviceUrl)
      
      // Reset FRP fallback on startup - give direct connection a chance
      if (cachedDeviceUrl && usingFrpFallback) {
        console.log('[API] Resetting FRP fallback on startup to try direct connection first')
        usingFrpFallback = false
        consecutiveFailures = 0
      }
      
      return cachedDeviceUrl
    } catch (error) {
      console.error('[API] Failed to get device URL:', error)
    }
  }
  return null
}

/**
 * Set the device URL (called when user switches devices)
 */
export function setDeviceUrl(url: string | null): void {
  cachedDeviceUrl = url
  window.__R58_DEVICE_URL__ = url || undefined
  console.log('[API] Device URL set:', url)
}

/**
 * Set the secondary fallback URL (e.g. Tailscale)
 */
export function setDeviceFallbackUrl(url: string | null): void {
  cachedFallbackUrl = url ? url.replace(/\/+$/, '') : null
  if (!cachedFallbackUrl) {
    usingFallbackUrl = false
  }
  console.log('[API] Device fallback URL set:', cachedFallbackUrl)
}

function getFallbackUrl(): string | null {
  return cachedFallbackUrl
}

/**
 * Get the current device URL
 */
export function getDeviceUrl(): string | null {
  return cachedDeviceUrl || window.__R58_DEVICE_URL__ || null
}

/**
 * Check if running in Electron
 */
export function isElectron(): boolean {
  return !!window.electronAPI?.isElectron
}

// ============================================
// API Client
// ============================================

export interface ApiOptions extends RequestInit {
  /** Number of retry attempts (default: 3) */
  retries?: number
  /** Timeout in milliseconds (default: 10000) */
  timeout?: number
  /** Whether to include idempotency key for mutations */
  idempotent?: boolean
}

export interface ApiError extends Error {
  status?: number
  statusText?: string
  body?: unknown
  retryable: boolean
}

/**
 * Delay values for exponential backoff (in ms)
 */
const RETRY_DELAYS = [100, 300, 1000]

/**
 * HTTP status codes that should trigger a retry
 */
const RETRYABLE_STATUS_CODES = new Set([
  408, // Request Timeout
  429, // Too Many Requests
  500, // Internal Server Error
  502, // Bad Gateway
  503, // Service Unavailable
  504, // Gateway Timeout
])

/**
 * Create an API error with retry information
 */
function createApiError(
  message: string,
  status?: number,
  statusText?: string,
  body?: unknown
): ApiError {
  const error = new Error(message) as ApiError
  error.status = status
  error.statusText = statusText
  error.body = body
  error.retryable = status ? RETRYABLE_STATUS_CODES.has(status) : false
  return error
}

/**
 * Sleep for a given number of milliseconds
 */
function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms))
}

/**
 * Generate a unique idempotency key
 */
export function generateIdempotencyKey(): string {
  return crypto.randomUUID()
}

/**
 * Get the pending idempotency key from session storage
 */
export function getPendingIdempotencyKey(operation: string): string | null {
  return sessionStorage.getItem(`pending_${operation}_key`)
}

/**
 * Store a pending idempotency key in session storage
 */
export function setPendingIdempotencyKey(operation: string, key: string): void {
  sessionStorage.setItem(`pending_${operation}_key`, key)
}

/**
 * Clear a pending idempotency key from session storage
 */
export function clearPendingIdempotencyKey(operation: string): void {
  sessionStorage.removeItem(`pending_${operation}_key`)
}

// Network debug logging
const isNetworkDebugEnabled = (): boolean => {
  return import.meta.env.VITE_NETWORK_DEBUG === '1' || 
         (typeof window !== 'undefined' && (window as any).__NETWORK_DEBUG__ === true)
}

// Rate-limited logging (max 1 log per second per subsystem)
const apiLogThrottle = new Map<string, number>()
const API_LOG_THROTTLE_MS = 1000

function networkDebugLog(subsystem: string, message: string, ...args: any[]): void {
  if (!isNetworkDebugEnabled()) return
  
  const now = Date.now()
  const lastLog = apiLogThrottle.get(subsystem) || 0
  if (now - lastLog < API_LOG_THROTTLE_MS) return
  
  apiLogThrottle.set(subsystem, now)
  console.log(`[NETWORK DEBUG ${subsystem}] ${message}`, ...args)
}

// Track request count for rate monitoring
let apiRequestCount = 0
let apiRequestCountStartTime = Date.now()

function trackApiRequest(): void {
  apiRequestCount++
  const elapsed = Date.now() - apiRequestCountStartTime
  if (elapsed >= 60000) {  // Every minute
    networkDebugLog('API', `Request rate: ${apiRequestCount} requests/minute`)
    apiRequestCount = 0
    apiRequestCountStartTime = Date.now()
  }
}

/**
 * Make an API request with automatic retry and timeout.
 * 
 * Features:
 * - Automatic retry with exponential backoff
 * - Request timeout
 * - Idempotency key support for safe retries
 * - Structured error handling
 * 
 * @example
 * ```ts
 * // Simple GET
 * const data = await apiRequest<MyType>('/api/v1/status')
 * 
 * // POST with idempotency
 * const result = await apiRequest<Result>('/api/v1/recorder/start', {
 *   method: 'POST',
 *   body: JSON.stringify({ name: 'My Recording' }),
 *   idempotent: true,
 * })
 * ```
 */
export async function apiRequest<T>(
  url: string,
  options: ApiOptions = {}
): Promise<T> {
  const {
    retries = 3,
    timeout = 10000,
    idempotent = false,
    ...fetchOptions
  } = options

  // Build headers
  const headers = new Headers(fetchOptions.headers)
  
  if (!headers.has('Content-Type') && fetchOptions.body) {
    headers.set('Content-Type', 'application/json')
  }
  
  // Add idempotency key for mutations
  let idempotencyKey: string | null = null
  if (idempotent && fetchOptions.method && fetchOptions.method !== 'GET') {
    idempotencyKey = generateIdempotencyKey()
    headers.set('X-Idempotency-Key', idempotencyKey)
  }

  let lastError: ApiError | null = null
  
  trackApiRequest()
  networkDebugLog('API', `Request: ${fetchOptions.method || 'GET'} ${url}`)

  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      // Create abort controller for timeout
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), timeout)

      try {
        const response = await fetch(url, {
          ...fetchOptions,
          headers,
          signal: controller.signal,
        })

        clearTimeout(timeoutId)

        // Check for success
        if (response.ok) {
          // Record successful connection
          recordConnectionSuccess()
          
          // Reset fallback flags if we successfully connected to primary URL
          const deviceUrl = getDeviceUrl()
          const fallbackUrl = getFallbackUrl()
          if (deviceUrl) {
            // Check if this request was to the primary URL (not fallback)
            const isPrimaryUrl = url.startsWith(deviceUrl)
            const isFallbackUrl = fallbackUrl && url.startsWith(fallbackUrl)
            if (isPrimaryUrl && !isFallbackUrl && (usingFallbackUrl || usingFrpFallback)) {
              console.log('[API] Primary URL is working again, resetting fallback flags')
              usingFallbackUrl = false
              usingFrpFallback = false
              consecutiveFailures = 0
            }
          }
          
          networkDebugLog('API', `Request succeeded: ${fetchOptions.method || 'GET'} ${url}`)
          
          // Handle empty responses
          const text = await response.text()
          if (!text) {
            return {} as T
          }
          return JSON.parse(text) as T
        }

        // Handle error response
        let errorBody: unknown
        try {
          errorBody = await response.json()
        } catch {
          errorBody = await response.text()
        }

        const error = createApiError(
          `HTTP ${response.status}: ${response.statusText}`,
          response.status,
          response.statusText,
          errorBody
        )

        // Don't retry non-retryable errors
        if (!error.retryable) {
          throw error
        }

        lastError = error

      } catch (e) {
        clearTimeout(timeoutId)
        
        if (e instanceof Error && e.name === 'AbortError') {
          lastError = createApiError('Request timeout', 408, 'Request Timeout')
          lastError.retryable = true
          await recordConnectionFailure()
        } else if (e instanceof TypeError) {
          // Network error - likely device unreachable
          lastError = createApiError('Network error: ' + e.message)
          lastError.retryable = true
          await recordConnectionFailure()
        } else {
          throw e
        }
      }

      // Wait before retry (if not last attempt)
      if (attempt < retries) {
        const delay = RETRY_DELAYS[Math.min(attempt, RETRY_DELAYS.length - 1)]
        // Add jitter (±20%)
        const jitter = delay * 0.2 * (Math.random() * 2 - 1)
        const retryDelay = Math.round(delay + jitter)
        networkDebugLog('API', `Retry ${attempt + 1}/${retries} for ${url} in ${retryDelay}ms`)
        console.log(`[API] Retry ${attempt + 1}/${retries} for ${url} in ${retryDelay}ms`)
        await sleep(delay + jitter)
      }

    } catch (e) {
      // Non-retryable error, throw immediately
      throw e
    }
  }

  // All retries exhausted - try secondary fallback (Tailscale), then FRP
  if (lastError && isElectron() && !usingFallbackUrl && !usingFrpFallback) {
    const fallbackUrl = getFallbackUrl()
    if (fallbackUrl) {
      console.log('[API] Primary device unreachable, trying fallback URL...')
      usingFallbackUrl = true
      try {
        const urlObj = new URL(url)
        const fallbackFullUrl = `${fallbackUrl}${urlObj.pathname}${urlObj.search}`
        console.log('[API] Retrying with fallback URL:', fallbackFullUrl)
        return await apiRequest<T>(fallbackFullUrl, { ...options, retries: 0 })
      } catch (fallbackError) {
        console.error('[API] Fallback URL also failed:', fallbackError)
        usingFallbackUrl = false
      }
    } else {
      console.log('[API] No fallback URL configured')
    }
  }

  if (lastError && isElectron() && !usingFrpFallback) {
    console.log('[API] Primary device unreachable, trying FRP fallback...')
    
    // Get FRP URL from device configuration
    const frpUrl = await getFrpUrl()
    if (frpUrl) {
      enableFrpFallback()
      
      // Extract path from URL and rebuild with FRP
      try {
        const urlObj = new URL(url)
        const frpFullUrl = `${frpUrl}${urlObj.pathname}${urlObj.search}`
        console.log('[API] Retrying with FRP:', frpFullUrl)
        
        // Try once with FRP (no retries to avoid long delays)
        return await apiRequest<T>(frpFullUrl, { ...options, retries: 0 })
      } catch (frpError) {
        console.error('[API] FRP fallback also failed:', frpError)
        // Fall through to original error
      }
    } else {
      console.log('[API] No FRP fallback configured on device')
    }
  }

  if (lastError) {
    console.error(`[API] Failed after ${retries + 1} attempts: ${url}`, lastError)
    throw lastError
  }

  throw createApiError('Unknown error')
}

/**
 * Convenience method for GET requests
 */
export async function apiGet<T>(url: string, options?: Omit<ApiOptions, 'method'>): Promise<T> {
  return apiRequest<T>(url, { ...options, method: 'GET' })
}

/**
 * Convenience method for POST requests
 */
export async function apiPost<T>(
  url: string,
  body?: unknown,
  options?: Omit<ApiOptions, 'method' | 'body'>
): Promise<T> {
  return apiRequest<T>(url, {
    ...options,
    method: 'POST',
    body: body ? JSON.stringify(body) : undefined,
  })
}

/**
 * Convenience method for PUT requests
 */
export async function apiPut<T>(
  url: string,
  body?: unknown,
  options?: Omit<ApiOptions, 'method' | 'body'>
): Promise<T> {
  return apiRequest<T>(url, {
    ...options,
    method: 'PUT',
    body: body ? JSON.stringify(body) : undefined,
  })
}

/**
 * Convenience method for DELETE requests
 */
export async function apiDelete<T>(url: string, options?: Omit<ApiOptions, 'method'>): Promise<T> {
  return apiRequest<T>(url, { ...options, method: 'DELETE' })
}

/**
 * Check if a device URL is configured
 * Useful to skip API calls before device setup
 */
export function hasDeviceConfigured(): boolean {
  if (isElectron()) {
    return !!getDeviceUrl()
  }
  // Web mode: always consider "configured" as the URL is derived from browser location
  return true
}

/**
 * Build API URL from base path
 * 
 * Priority:
 * 1. Electron: Use configured device URL
 * 2. Web (reverse proxy on 80/443): Use same-origin API
 * 3. Dev mode (localhost:5173): Connect to API on port 8000
 * 
 * @throws Error if in Electron and no device URL is configured
 */
export async function buildApiUrl(path: string, useFallback: boolean = false): Promise<string> {
  // If explicitly using fallback or we've detected device is unreachable
  if (useFallback || usingFallbackUrl) {
    const fallbackUrl = getFallbackUrl()
    if (fallbackUrl) {
      return `${fallbackUrl}${path}`
    }
  }

  if (useFallback || usingFrpFallback) {
    const frpUrl = await getFrpUrl()
    if (frpUrl) {
      return `${frpUrl}${path}`
    }
    // No FRP configured - throw error instead of using hardcoded URL
    throw new Error('Device unreachable and no FRP fallback configured')
  }
  
  // Priority 1: Electron with configured device URL
  const deviceUrl = getDeviceUrl()
  if (deviceUrl) {
    // Remove trailing slash from device URL if present
    const baseUrl = deviceUrl.replace(/\/+$/, '')
    return `${baseUrl}${path}`
  }

  // In Electron without device URL, require device setup
  if (isElectron()) {
    throw new Error('No device configured. Please add a device in Settings.')
  }

  // Priority 2 & 3: Web browser access
  const host = window.location.hostname
  const currentPort = window.location.port
  const protocol = window.location.protocol
  
  // Same-domain proxy: app.itagenten.no serves both frontend AND proxies API
  // No CORS needed - all requests are same-origin
  if (host === 'app.itagenten.no') {
    return path // Same-origin (nginx proxies /api/* to R58)
  }
  
  // If accessed via standard port (no port in URL, or 80/443), API is same-origin
  if (!currentPort || currentPort === '80' || currentPort === '443') {
    return path // Same-origin API (frontend + backend served together)
  }
  
  // Dev mode: connect to API on port 8000
  const apiPort = 8000
  return `${protocol}//${host}:${apiPort}${path}`
}

/**
 * Enable FRP fallback mode (call when device is detected as unreachable)
 * Only works if device has FRP URL configured
 */
export async function enableFrpFallback(): Promise<boolean> {
  if (usingFrpFallback) {
    return true
  }
  
  const frpUrl = await getFrpUrl()
  if (frpUrl) {
    console.log('[API] Enabling FRP fallback - device unreachable')
    usingFrpFallback = true
    return true
  }
  
  console.log('[API] Cannot enable FRP fallback - no FRP URL configured')
  return false
}

/**
 * Disable FRP fallback mode (call when device becomes reachable again)
 */
export function disableFrpFallback(): void {
  if (usingFrpFallback) {
    console.log('[API] Disabling FRP fallback - using direct connection')
    usingFrpFallback = false
    consecutiveFailures = 0
  }
}

/**
 * Check if currently using FRP fallback
 */
export function isUsingFrpFallback(): boolean {
  return usingFrpFallback
}

/**
 * Record a connection failure (triggers fallback after threshold)
 */
export async function recordConnectionFailure(): Promise<void> {
  consecutiveFailures++
  if (consecutiveFailures >= FAILURES_BEFORE_FALLBACK && !usingFrpFallback) {
    await enableFrpFallback()
  }
}

/**
 * Record a successful connection (resets failure counter)
 */
export function recordConnectionSuccess(): void {
  consecutiveFailures = 0
}

/**
 * Try to reconnect directly to the device (bypassing FRP)
 * Call this periodically to check if direct connection is available again
 */
export async function tryDirectConnection(): Promise<boolean> {
  const deviceUrl = getDeviceUrl()
  if (!deviceUrl) {
    return false
  }
  
  try {
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), 3000) // 3s timeout
    
    const response = await fetch(`${deviceUrl}/health`, {
      signal: controller.signal,
      mode: 'cors',
      cache: 'no-cache'
    })
    clearTimeout(timeout)
    
    if (response.ok) {
      console.log('[API] Direct connection to device successful!')
      disableFrpFallback()
      return true
    }
  } catch (e) {
    // Direct connection failed, keep using FRP
    console.log('[API] Direct connection check failed, continuing with FRP')
  }
  
  return false
}

/**
 * Build WebSocket URL from device configuration
 * 
 * @throws Error if in Electron and no device URL is configured
 */
export function buildWsUrl(path: string): string {
  const deviceUrl = getDeviceUrl()
  
  if (deviceUrl) {
    // Convert HTTP(S) to WS(S)
    const wsUrl = deviceUrl
      .replace(/^https:/, 'wss:')
      .replace(/^http:/, 'ws:')
      .replace(/\/+$/, '')
    return `${wsUrl}${path}`
  }

  // In Electron without device URL, we can't make WebSocket connections
  if (isElectron()) {
    throw new Error('No device configured - cannot connect WebSocket')
  }

  // Fall back to browser-based URL construction
  const host = window.location.hostname
  const currentPort = window.location.port
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  
  // Same-domain proxy: WebSocket also goes through nginx
  if (host === 'app.itagenten.no') {
    return `wss://${host}${path}` // Same-origin WebSocket
  }
  
  // If on standard ports, use same host
  if (!currentPort || currentPort === '80' || currentPort === '443') {
    return `${protocol}//${host}${path}`
  }
  
  // Dev mode: API on port 8000
  return `${protocol}//${host}:8000${path}`
}

/**
 * R58 API client with typed methods
 * 
 * Device API endpoints (actual):
 * - /health - Health check
 * - /status - Camera status
 * - /api/ingest/status - Detailed ingest status
 * - /{cam_id}/whep - WHEP streaming endpoint
 */
export const r58Api = {
  // Health
  async getHealth() {
    return apiGet<{ 
      status: string
      platform?: string
      gstreamer?: string
      gstreamer_error?: string | null 
    }>(await buildApiUrl('/health'))
  },

  async getDetailedHealth() {
    // Use /health as fallback since /health/detailed may not exist
    return apiGet<{
      status: string
      platform?: string
      gstreamer?: string
      gstreamer_error?: string | null
    }>(await buildApiUrl('/health'))
  },

  // Camera/Recorder Status
  async getRecorderStatus() {
    // Device uses /status for camera status
    return apiGet<{
      cameras: Record<string, {
        status: string
        config: boolean
      }>
    }>(await buildApiUrl('/status'))
  },

  async getInputsStatus() {
    // Use /api/ingest/status for detailed input info
    try {
      return await apiGet<{
        cameras: Record<string, {
          status: string
          resolution?: { width: number; height: number; formatted: string }
          config: boolean
          has_signal?: boolean
        }>
        summary: {
          streaming: number
          error: number
          total: number
        }
      }>(await buildApiUrl('/api/ingest/status'))
    } catch {
      // Fallback to /status if /api/ingest/status fails
      const status = await this.getRecorderStatus()
      return {
        cameras: status.cameras,
        summary: {
          streaming: Object.values(status.cameras).filter(c => c.status === 'streaming' || c.status === 'preview').length,
          error: Object.values(status.cameras).filter(c => c.status === 'error').length,
          total: Object.keys(status.cameras).length
        }
      }
    }
  },

  async getFps() {
    // Get real FPS data from /api/fps endpoint
    return apiGet<{
      cameras: Record<string, {
        current_fps: number
        avg_fps: number
        min_fps: number
        max_fps: number
        total_frames: number
        uptime_seconds: number
      }>
      summary: {
        active_cameras: number
        average_fps: number
        all_at_target: boolean
        target_fps: number
        status: string
      }
    }>(await buildApiUrl('/api/fps'))
  },

  async startRecording(_options?: { name?: string; inputs?: string[] }) {
    // Device uses /record/start-all to start all cameras
    const response = await apiPost<{
      status: string
      cameras: Record<string, string>
    }>(
      await buildApiUrl('/record/start-all'),
      undefined,
      { idempotent: true }
    )
    
    // Convert to expected format
    const startedCameras = Object.entries(response.cameras)
      .filter(([_, status]) => status === 'started')
      .map(([id]) => id)
    
    return {
      session_id: `session-${Date.now()}`,
      started_at: new Date().toISOString(),
      inputs: startedCameras,
      status: response.status
    }
  },

  async stopRecording(_sessionId?: string) {
    // Device uses /record/stop-all to stop all cameras
    const response = await apiPost<{
      status: string
      cameras: Record<string, string>
    }>(
      await buildApiUrl('/record/stop-all'),
      undefined,
      { idempotent: true }
    )
    
    // Convert to expected format
    return {
      session_id: `session-${Date.now()}`,
      duration_ms: 0,
      files: response.cameras,
      status: response.status
    }
  },

  // Capabilities - construct from /status
  async getCapabilities() {
    const status = await this.getRecorderStatus()
    
    return {
      device_id: 'r58-device',
      inputs: Object.entries(status.cameras).map(([id, info]) => ({
        id,
        label: getCameraLabel(id),
        type: 'hdmi',
        has_signal: info.status === 'streaming' || info.status === 'preview'
      })),
      codecs: [{ id: 'h264', name: 'H.264', hardware_accelerated: true }],
      preview_modes: [{ id: 'whep', name: 'WHEP WebRTC' }],
      vdoninja: undefined
    }
  },

  // Degradation
  async getDegradation() {
    return apiGet<{
      level: number
      level_name: string
      resources: { cpu_percent: number; mem_percent: number; disk_free_gb: number }
      flags: {
        should_reduce_quality: boolean
        should_disable_previews: boolean
        can_start_recording: boolean
      }
    }>(await buildApiUrl('/api/v1/degradation'))
  },

  // Alerts
  async getAlerts(options?: { limit?: number; level?: string; unresolved_only?: boolean }) {
    const params = new URLSearchParams()
    if (options?.limit) params.set('limit', String(options.limit))
    if (options?.level) params.set('level', options.level)
    if (options?.unresolved_only) params.set('unresolved_only', 'true')
    
    const query = params.toString()
    return apiGet<{
      alerts: Array<{
        id: string
        level: string
        source: string
        message: string
        timestamp: string
        resolved: boolean
      }>
      counts: { critical: number; warning: number; info: number; total: number }
    }>(await buildApiUrl(`/api/v1/alerts${query ? '?' + query : ''}`))
  },

  async resolveAlert(alertId: string) {
    return apiPost<{ status: string; alert_id: string }>(
      await buildApiUrl(`/api/v1/alerts/${alertId}/resolve`)
    )
  },

  // LAN Discovery - Find R58 devices on local network
  lanDiscovery: {
    async list() {
      return apiGet<Array<{
        id: string
        name: string
        ip: string
        port: number
        status: string
        last_seen: string
        api_version?: string
        capabilities?: Record<string, unknown>
      }>>(await buildApiUrl('/api/v1/lan-devices'))
    },

    async scan() {
      return apiPost<Array<{
        id: string
        name: string
        ip: string
        status: string
      }>>(await buildApiUrl('/api/v1/lan-devices/scan'))
    },

    async getDevice(deviceId: string) {
      return apiGet<{
        id: string
        name: string
        ip: string
        port: number
        status: string
        last_seen: string
        api_version?: string
      }>(await buildApiUrl(`/api/v1/lan-devices/${deviceId}`))
    },

    async connect(deviceId: string) {
      return apiPost<{
        connected: boolean
        device?: { id: string; name: string; ip: string }
        error?: string
      }>(await buildApiUrl(`/api/v1/lan-devices/${deviceId}/connect`))
    },
  },

  // Fleet Management - Centralized device management (separate server)
  fleet: {
    // Get fleet API URL (may be different from device API)
    getFleetUrl(path: string): string {
      const fleetHost = import.meta.env.VITE_FLEET_URL || 'https://fleet.r58.itagenten.no'
      return `${fleetHost}${path}`
    },

    // Get auth token from storage
    getToken(): string | null {
      return localStorage.getItem('fleet_token')
    },

    // Set auth token
    setToken(token: string): void {
      localStorage.setItem('fleet_token', token)
    },

    // Clear auth token
    clearToken(): void {
      localStorage.removeItem('fleet_token')
    },

    // Get auth headers
    getAuthHeaders(): Record<string, string> {
      const token = this.getToken()
      return token ? { Authorization: `Bearer ${token}` } : {}
    },

    // Login
    async login(email: string, password: string) {
      const response = await apiPost<{
        access_token: string
        token_type: string
        expires_in: number
      }>(this.getFleetUrl('/api/v1/auth/login'), { email, password })
      this.setToken(response.access_token)
      return response
    },

    // Logout
    logout() {
      this.clearToken()
    },

    // List devices
    async devices(options?: { status?: string; search?: string; page?: number }) {
      const params = new URLSearchParams()
      if (options?.status) params.set('status', options.status)
      if (options?.search) params.set('search', options.search)
      if (options?.page) params.set('page', String(options.page))
      const query = params.toString()
      
      return apiGet<{
        items: Array<{
          id: string
          device_id: string
          name: string
          status: string
          current_version?: string
          target_version?: string
          last_heartbeat?: string
          cpu_percent?: number
          mem_percent?: number
          disk_free_gb?: number
          temperature_c?: number
          recording_active?: boolean
          mixer_active?: boolean
          location?: string
          tags?: string[]
          pending_commands?: number
          active_alerts?: number
        }>
        total: number
        page: number
        has_more: boolean
      }>(this.getFleetUrl(`/api/v1/devices${query ? '?' + query : ''}`), {
        headers: this.getAuthHeaders(),
      })
    },

    // Get single device
    async device(deviceId: string) {
      return apiGet<{
        id: string
        device_id: string
        name: string
        status: string
        current_version?: string
        target_version?: string
        update_channel?: string
        last_heartbeat?: string
        cpu_percent?: number
        mem_percent?: number
        disk_free_gb?: number
        temperature_c?: number
        recording_active?: boolean
        mixer_active?: boolean
        uptime_seconds?: number
        platform?: string
        arch?: string
        location?: string
        tags?: string[]
        capabilities?: Record<string, unknown>
        pending_commands?: number
        active_alerts?: number
        created_at?: string
      }>(this.getFleetUrl(`/api/v1/devices/${deviceId}`), {
        headers: this.getAuthHeaders(),
      })
    },

    // Update device
    async updateDevice(deviceId: string, data: {
      name?: string
      location?: string
      tags?: string[]
      update_channel?: string
      target_version?: string
    }) {
      return apiRequest<{ id: string; device_id: string }>(
        this.getFleetUrl(`/api/v1/devices/${deviceId}`),
        {
          method: 'PATCH',
          body: JSON.stringify(data),
          headers: { ...this.getAuthHeaders(), 'Content-Type': 'application/json' },
        }
      )
    },

    // Get device commands
    async deviceCommands(deviceId: string) {
      return apiGet<{
        items: Array<{
          id: string
          type: string
          status: string
          priority: number
          created_at: string
          completed_at?: string
          error?: string
        }>
        total: number
      }>(this.getFleetUrl(`/api/v1/devices/${deviceId}/commands`), {
        headers: this.getAuthHeaders(),
      })
    },

    // Send command to device
    async sendCommand(deviceId: string, command: {
      type: string
      payload?: Record<string, unknown>
      priority?: number
    }) {
      return apiPost<{ id: string; type: string; status: string }>(
        this.getFleetUrl(`/api/v1/devices/${deviceId}/commands`),
        command,
        { headers: this.getAuthHeaders() }
      )
    },

    // Get device heartbeats
    async deviceHeartbeats(deviceId: string, options?: { since?: string }) {
      const params = new URLSearchParams()
      if (options?.since) params.set('since', options.since)
      const query = params.toString()
      
      return apiGet<{
        items: Array<{
          received_at: string
          cpu_percent: number
          mem_percent: number
          disk_free_gb: number
          temperature_c?: number
        }>
        total: number
      }>(this.getFleetUrl(`/api/v1/devices/${deviceId}/heartbeats${query ? '?' + query : ''}`), {
        headers: this.getAuthHeaders(),
      })
    },

    // Request support bundle
    async requestBundle(deviceId: string, options: {
      include_logs?: boolean
      include_config?: boolean
      include_recordings?: boolean
    }) {
      return apiPost<{ id: string; status: string }>(
        this.getFleetUrl(`/api/v1/devices/${deviceId}/bundles`),
        options,
        { headers: this.getAuthHeaders() }
      )
    },

    // Get latest release
    async latestRelease(channel: string = 'stable') {
      return apiGet<{
        version: string
        channel: string
        download_url: string
        checksum_sha256: string
        changelog?: string
      }>(this.getFleetUrl(`/api/v1/releases/latest?channel=${channel}`))
    },
  },

  // Camera Control
  cameras: {
    async list() {
      return apiGet<string[]>(await buildApiUrl('/api/v1/cameras/'))
    },

    async getStatus(cameraName: string) {
      return apiGet<{
        name: string
        type: string
        connected: boolean
        settings?: Record<string, any>
      }>(await buildApiUrl(`/api/v1/cameras/${cameraName}/status`))
    },

    async getSettings(cameraName: string) {
      return apiGet<{
        name: string
        settings: Record<string, any>
      }>(await buildApiUrl(`/api/v1/cameras/${cameraName}/settings`))
    },

    async setFocus(cameraName: string, mode: 'auto' | 'manual', value?: number) {
      return apiPut<{ success: boolean; camera: string; parameter: string }>(
        await buildApiUrl(`/api/v1/cameras/${cameraName}/settings/focus`),
        { mode, value }
      )
    },

    async setWhiteBalance(cameraName: string, mode: 'auto' | 'manual' | 'preset', temperature?: number) {
      return apiPut<{ success: boolean; camera: string; parameter: string }>(
        await buildApiUrl(`/api/v1/cameras/${cameraName}/settings/whiteBalance`),
        { mode, temperature }
      )
    },

    async setExposure(cameraName: string, mode: 'auto' | 'manual', value?: number) {
      return apiPut<{ success: boolean; camera: string; parameter: string }>(
        await buildApiUrl(`/api/v1/cameras/${cameraName}/settings/exposure`),
        { mode, value }
      )
    },

    async setISO(cameraName: string, value: number) {
      return apiPut<{ success: boolean; camera: string; parameter: string; value: number }>(
        await buildApiUrl(`/api/v1/cameras/${cameraName}/settings/iso`),
        { value }
      )
    },

    async setShutter(cameraName: string, value: number) {
      return apiPut<{ success: boolean; camera: string; parameter: string; value: number }>(
        await buildApiUrl(`/api/v1/cameras/${cameraName}/settings/shutter`),
        { value }
      )
    },

    async setIris(cameraName: string, mode: 'auto' | 'manual', value?: number) {
      return apiPut<{ success: boolean; camera: string; parameter: string }>(
        await buildApiUrl(`/api/v1/cameras/${cameraName}/settings/iris`),
        { mode, value }
      )
    },

    async setGain(cameraName: string, value: number) {
      return apiPut<{ success: boolean; camera: string; parameter: string; value: number }>(
        await buildApiUrl(`/api/v1/cameras/${cameraName}/settings/gain`),
        { value }
      )
    },

    async setPTZ(cameraName: string, pan: number, tilt: number, zoom: number) {
      return apiPut<{ success: boolean; camera: string; parameter: string }>(
        await buildApiUrl(`/api/v1/cameras/${cameraName}/settings/ptz`),
        { pan, tilt, zoom }
      )
    },

    async recallPTZPreset(cameraName: string, presetId: number) {
      return apiPut<{ success: boolean; camera: string; preset_id: number }>(
        await buildApiUrl(`/api/v1/cameras/${cameraName}/settings/ptz/preset/${presetId}`),
        {}
      )
    },

    async setColorCorrection(cameraName: string, settings: {
      lift?: number[]
      gamma?: number[]
      gain?: number[]
      offset?: number[]
    }) {
      return apiPut<{ success: boolean; camera: string; parameter: string }>(
        await buildApiUrl(`/api/v1/cameras/${cameraName}/settings/colorCorrection`),
        settings
      )
    },

    async getConfig() {
      return apiGet<{
        cameras: Array<{
          name: string
          type: string
          ip: string
          port?: number
          enabled: boolean
        }>
        config_path: string
      }>(await buildApiUrl('/api/v1/cameras/config'))
    },

    async updateConfig(cameras: Array<{
      name: string
      type: string
      ip: string
      port?: number
      enabled: boolean
    }>) {
      return apiPut<{
        success: boolean
        cameras: Array<any>
        message: string
      }>(await buildApiUrl('/api/v1/cameras/config'), cameras)
    },
  },

  // PTZ Controller
  ptzController: {
    async listCameras() {
      return apiGet<{
        cameras: Array<{
          name: string
          type: string
          supports_focus: boolean
        }>
      }>(await buildApiUrl('/api/v1/ptz-controller/cameras'))
    },

    async sendCommand(cameraName: string, command: {
      pan: number
      tilt: number
      zoom: number
      focus?: number
      speed?: number
    }) {
      return apiPut<{
        success: boolean
        camera: string
        command: {
          pan: number
          tilt: number
          zoom: number
        }
      }>(await buildApiUrl(`/api/v1/ptz-controller/${cameraName}/ptz`), command)
    },
  },

  // WordPress/Booking Integration
  wordpress: {
    async getStatus() {
      return apiGet<{
        enabled: boolean
        connected: boolean
        wordpress_url: string
        last_sync?: string
        error?: string
      }>(await buildApiUrl('/api/v1/wordpress/status'))
    },

    async listAppointments(params?: {
      date_from?: string
      date_to?: string
      status?: string
      page?: number
      per_page?: number
    }) {
      const query = new URLSearchParams()
      if (params?.date_from) query.set('date_from', params.date_from)
      if (params?.date_to) query.set('date_to', params.date_to)
      if (params?.status) query.set('status', params.status)
      if (params?.page) query.set('page', String(params.page))
      if (params?.per_page) query.set('per_page', String(params.per_page))

      return apiGet<{
        bookings: Array<any>
        total: number
        page: number
        per_page: number
      }>(await buildApiUrl(`/api/v1/wordpress/appointments?${query}`))
    },

    async getTodaysAppointments() {
      return apiGet<{
        bookings: Array<any>
        total: number
      }>(await buildApiUrl('/api/v1/wordpress/appointments/today'))
    },

    async getAppointment(appointmentId: number) {
      return apiGet<{
        booking: any
        graphics: Array<any>
      }>(await buildApiUrl(`/api/v1/wordpress/appointments/${appointmentId}`))
    },

    async activateBooking(appointmentId: number, downloadGraphics: boolean = true) {
      return apiPost<{
        success: boolean
        booking: any
        recording_path: string
        graphics_downloaded: number
        message: string
      }>(
        await buildApiUrl(`/api/v1/wordpress/appointments/${appointmentId}/activate`),
        { booking_id: appointmentId, download_graphics: downloadGraphics },
        { idempotent: true }
      )
    },

    async completeBooking(appointmentId: number, uploadRecordings: boolean = true) {
      return apiPost<{
        success: boolean
        booking_id: number
        recordings_uploaded: number
        wordpress_status_updated: boolean
        message: string
      }>(
        await buildApiUrl(`/api/v1/wordpress/appointments/${appointmentId}/complete`),
        { booking_id: appointmentId, upload_recordings: uploadRecordings, update_status: true },
        { idempotent: true }
      )
    },

    async getCurrentBooking() {
      return apiGet<{
        active: boolean
        booking?: any
        recording_path?: string
        graphics_downloaded?: boolean
        graphics_paths?: string[]
        activated_at?: string
      }>(await buildApiUrl('/api/v1/wordpress/booking/current'))
    },

    // Customer Portal API
    async validateToken(token: string) {
      return apiPost<{
        valid: boolean
        booking?: any
        project?: any
        error?: string
      }>(await buildApiUrl('/api/v1/wordpress/customer/validate'), { token })
    },

    async getCustomerStatus(token: string) {
      return apiGet<{
        booking: any
        project: any
        recording_active: boolean
        recording_duration_ms: number
        current_slide_index: number
        total_slides: number
        disk_space_gb: number
        display_mode: string
        teleprompter_script?: string
        teleprompter_scroll_speed: number
      }>(await buildApiUrl(`/api/v1/wordpress/customer/${token}/status`))
    },

    async customerStartRecording(token: string) {
      return apiPost<{
        success: boolean
        message: string
        recording_path: string
      }>(await buildApiUrl(`/api/v1/wordpress/customer/${token}/recording/start`))
    },

    async customerStopRecording(token: string) {
      return apiPost<{
        success: boolean
        message: string
      }>(await buildApiUrl(`/api/v1/wordpress/customer/${token}/recording/stop`))
    },

    async customerGotoSlide(token: string, index: number) {
      return apiPost<{
        success: boolean
        current_index: number
        total_slides: number
      }>(await buildApiUrl(`/api/v1/wordpress/customer/${token}/presentation/goto/${index}`))
    },

    // Display Mode API
    async getDisplayMode(token: string) {
      return apiGet<{
        display_mode: string
        content_type?: string
      }>(await buildApiUrl(`/api/v1/wordpress/customer/${token}/display-mode`))
    },

    async updateTeleprompterScript(token: string, script: string) {
      return apiPost<{
        success: boolean
        script_length: number
      }>(await buildApiUrl(`/api/v1/wordpress/customer/${token}/teleprompter/script`), { script })
    },

    async setTeleprompterSpeed(token: string, speed: number) {
      return apiPost<{
        success: boolean
        speed: number
      }>(await buildApiUrl(`/api/v1/wordpress/customer/${token}/teleprompter/speed`), { speed })
    },

    async checkVdoNinjaStatus(token: string) {
      return apiGet<{
        available: boolean
        url?: string
        error?: string
      }>(await buildApiUrl(`/api/v1/wordpress/customer/${token}/vdoninja/status`))
    },

    // Client/Project API
    async listClients() {
      return apiGet<{
        clients: Array<any>
        total: number
      }>(await buildApiUrl('/api/v1/wordpress/clients'))
    },

    async listClientProjects(clientId: number) {
      return apiGet<{
        projects: Array<any>
        total: number
      }>(await buildApiUrl(`/api/v1/wordpress/clients/${clientId}/projects`))
    },

    async createProject(clientId: number, name: string, type: string) {
      return apiPost<{
        id: number
        name: string
        slug: string
        client_id: number
      }>(await buildApiUrl('/api/v1/wordpress/projects'), { client_id: clientId, name, type })
    },

    // Calendar API
    async getCalendarToday() {
      return apiGet<{
        date: string
        slots: Array<{
          start_time: string
          end_time: string
          available: boolean
          booking?: any
        }>
      }>(await buildApiUrl('/api/v1/wordpress/calendar/today'))
    },

    async createWalkInBooking(data: {
      slot_start: string
      slot_end: string
      customer_name: string
      customer_email: string
      customer_phone?: string
      recording_type: string
    }) {
      return apiPost<{
        success: boolean
        booking_id: number
        message: string
      }>(await buildApiUrl('/api/v1/wordpress/calendar/book'), data)
    },
  },
}

