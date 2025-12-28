/**
 * API client with retry logic and error handling for R58
 */

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
        } else if (e instanceof TypeError) {
          // Network error
          lastError = createApiError('Network error: ' + e.message)
          lastError.retryable = true
        } else {
          throw e
        }
      }

      // Wait before retry (if not last attempt)
      if (attempt < retries) {
        const delay = RETRY_DELAYS[Math.min(attempt, RETRY_DELAYS.length - 1)]
        // Add jitter (±20%)
        const jitter = delay * 0.2 * (Math.random() * 2 - 1)
        console.log(`[API] Retry ${attempt + 1}/${retries} for ${url} in ${Math.round(delay + jitter)}ms`)
        await sleep(delay + jitter)
      }

    } catch (e) {
      // Non-retryable error, throw immediately
      throw e
    }
  }

  // All retries exhausted
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
 * Build API URL from base path
 * 
 * When accessed via reverse proxy (standard ports 80/443), use same-origin API.
 * When accessed directly (e.g., localhost:5173 for dev), connect to API port 8000.
 */
export function buildApiUrl(path: string): string {
  const host = window.location.hostname
  const currentPort = window.location.port
  const protocol = window.location.protocol
  
  // If accessed via standard port (no port in URL, or 80/443), API is same-origin
  if (!currentPort || currentPort === '80' || currentPort === '443') {
    return path // Same-origin API (frontend + backend served together)
  }
  
  // Dev mode: connect to API on port 8000
  const apiPort = 8000
  return `${protocol}//${host}:${apiPort}${path}`
}

/**
 * R58 API client with typed methods
 */
export const r58Api = {
  // Health
  async getHealth() {
    return apiGet<{ status: string; message?: string }>(buildApiUrl('/api/v1/health'))
  },

  async getDetailedHealth() {
    return apiGet<{
      status: string
      timestamp: string
      services: Array<{ name: string; status: string; message?: string }>
      storage: { total_gb: number; available_gb: number; used_percent: number }
      uptime_seconds: number
    }>(buildApiUrl('/api/v1/health/detailed'))
  },

  // Recorder
  async getRecorderStatus() {
    return apiGet<{
      status: string
      session_id?: string
      duration_ms: number
      inputs: string[]
    }>(buildApiUrl('/api/v1/recorder/status'))
  },

  async startRecording(options?: { name?: string; inputs?: string[] }) {
    return apiPost<{
      session_id: string
      name?: string
      started_at: string
      inputs: string[]
      status: string
    }>(
      buildApiUrl('/api/v1/recorder/start'),
      options,
      { idempotent: true }
    )
  },

  async stopRecording(sessionId?: string) {
    return apiPost<{
      session_id: string
      duration_ms: number
      files: Record<string, string>
      status: string
    }>(
      buildApiUrl('/api/v1/recorder/stop'),
      sessionId ? { session_id: sessionId } : undefined,
      { idempotent: true }
    )
  },

  // Capabilities
  async getCapabilities() {
    return apiGet<{
      device_id: string
      inputs: Array<{
        id: string
        label: string
        type: string
        device_path?: string
        has_signal: boolean
      }>
      codecs: Array<{ id: string; name: string; hardware_accelerated: boolean }>
      preview_modes: Array<{ id: string; name: string }>
      vdoninja?: { enabled: boolean; port: number; room: string }
    }>(buildApiUrl('/api/v1/capabilities'))
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
    }>(buildApiUrl('/api/v1/degradation'))
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
    }>(buildApiUrl(`/api/v1/alerts${query ? '?' + query : ''}`))
  },

  async resolveAlert(alertId: string) {
    return apiPost<{ status: string; alert_id: string }>(
      buildApiUrl(`/api/v1/alerts/${alertId}/resolve`)
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
      }>>(buildApiUrl('/api/v1/lan-devices'))
    },

    async scan() {
      return apiPost<Array<{
        id: string
        name: string
        ip: string
        status: string
      }>>(buildApiUrl('/api/v1/lan-devices/scan'))
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
      }>(buildApiUrl(`/api/v1/lan-devices/${deviceId}`))
    },

    async connect(deviceId: string) {
      return apiPost<{
        connected: boolean
        device?: { id: string; name: string; ip: string }
        error?: string
      }>(buildApiUrl(`/api/v1/lan-devices/${deviceId}/connect`))
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
}

