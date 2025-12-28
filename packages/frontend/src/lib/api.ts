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
 */
export function buildApiUrl(path: string): string {
  // Use current host with API port
  const host = window.location.hostname
  const port = 8000 // API port
  const protocol = window.location.protocol
  return `${protocol}//${host}:${port}${path}`
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
}

