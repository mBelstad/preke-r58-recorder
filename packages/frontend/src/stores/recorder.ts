import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { r58Api } from '@/lib/api'
import { getCameraLabel } from '@/lib/cameraLabels'

export interface RecordingSession {
  id: string
  name: string | null
  startedAt: Date
  duration: number // ms
  inputs: InputStatus[]
}

export interface InputStatus {
  id: string
  label: string
  hasSignal: boolean
  isRecording: boolean
  bytesWritten: number
  resolution: string
  framerate: number
}

export const useRecorderStore = defineStore('recorder', () => {
  // State
  const status = ref<'idle' | 'starting' | 'recording' | 'stopping'>('idle')
  const sessionId = ref<string | null>(null)
  const currentSession = ref<RecordingSession | null>(null)
  const duration = ref(0)
  const durationMs = ref(0)  // Alias for WebSocket updates
  const inputsLoaded = ref(false)
  const inputs = ref<InputStatus[]>([])

  // Computed
  const isRecording = computed(() => status.value === 'recording')
  const formattedDuration = computed(() => {
    const totalSeconds = Math.floor(duration.value / 1000)
    const hours = Math.floor(totalSeconds / 3600)
    const minutes = Math.floor((totalSeconds % 3600) / 60)
    const seconds = totalSeconds % 60
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`
  })
  const activeInputs = computed(() => inputs.value.filter(i => i.hasSignal))

  /**
   * Check if framerates are mismatched across active inputs.
   * Considers 2x multiples as compatible (e.g., 30fps and 60fps are OK).
   * Returns null if no mismatch, otherwise returns a warning message.
   */
  const framerateMismatch = computed(() => {
    const active = activeInputs.value
    if (active.length < 2) return null
    
    const framerates = active.map(i => i.framerate).filter(f => f > 0)
    if (framerates.length < 2) return null
    
    // Find the base framerate (lowest non-zero)
    const baseFps = Math.min(...framerates)
    
    // Check if all framerates are compatible (same or 2x multiple)
    const allCompatible = framerates.every(fps => {
      const ratio = fps / baseFps
      // Allow 1x or 2x (with 10% tolerance for real-world variance)
      return Math.abs(ratio - 1) < 0.1 || Math.abs(ratio - 2) < 0.1
    })
    
    if (allCompatible) return null
    
    // Build warning message
    const uniqueFps = [...new Set(framerates)].sort((a, b) => b - a)
    return `Mixed framerates: ${uniqueFps.map(f => `${Math.round(f)}fps`).join(', ')}`
  })

  // Error state
  const lastError = ref<string | null>(null)

  // Actions
  async function startRecording(sessionName?: string) {
    status.value = 'starting'
    lastError.value = null
    
    try {
      // Call API to start recording with retry support
      const response = await r58Api.startRecording({
        name: sessionName,
        inputs: activeInputs.value.map(i => i.id),
      })
      
      sessionId.value = response.session_id
      
      currentSession.value = {
        id: response.session_id,
        name: sessionName || null,
        startedAt: new Date(response.started_at),
        duration: 0,
        inputs: inputs.value.filter(i => i.hasSignal),
      }
      
      // Mark active inputs as recording
      inputs.value.forEach(input => {
        if (input.hasSignal) {
          input.isRecording = true
        }
      })
      
      status.value = 'recording'
      
      // Start duration timer
      startDurationTimer()
      
      console.log(`[Recorder] Started recording: ${response.session_id}`)
    } catch (error: any) {
      console.error('Failed to start recording:', error)
      lastError.value = error.message || 'Failed to start recording'
      status.value = 'idle'
      throw error
    }
  }

  async function stopRecording() {
    status.value = 'stopping'
    lastError.value = null
    
    try {
      // Call API to stop recording with retry support
      const response = await r58Api.stopRecording(sessionId.value || undefined)
      
      console.log(`[Recorder] Stopped recording: ${response.session_id}, duration: ${response.duration_ms}ms`)
      
      // Stop all inputs
      inputs.value.forEach(input => {
        input.isRecording = false
      })
      
      currentSession.value = null
      sessionId.value = null
      duration.value = 0
      durationMs.value = 0
      status.value = 'idle'
      
      // Stop duration timer
      if (durationInterval) {
        clearInterval(durationInterval)
        durationInterval = null
      }
      
      return { duration_ms: response.duration_ms, files: response.files }
    } catch (error: any) {
      console.error('Failed to stop recording:', error)
      lastError.value = error.message || 'Failed to stop recording'
      // Revert to recording state on failure
      status.value = 'recording'
      throw error
    }
  }

  async function fetchStatus() {
    /**
     * Fetch current recorder status from API.
     * Used to sync state on initial load or after disconnect.
     * 
     * Note: The /status endpoint returns camera status, not recording status.
     * Recording status would come from a separate endpoint if it exists.
     */
    try {
      const response = await r58Api.getRecorderStatus()
      
      // The /status endpoint returns cameras, not recording info
      // Check if any cameras are actively recording (status might indicate this)
      const cameras = response.cameras || {}
      const hasRecordingCameras = Object.values(cameras).some((cam: any) => 
        cam.status === 'recording'
      )
      
      if (hasRecordingCameras) {
        status.value = 'recording'
        // Start duration timer if recording
        startDurationTimer()
      } else {
        status.value = 'idle'
        sessionId.value = null
      }
    } catch (error) {
      console.error('Failed to fetch recorder status:', error)
    }
  }

  async function fetchInputs() {
    /**
     * Fetch real input status from pipeline manager via API.
     * This includes signal detection, resolution, and real FPS data.
     */
    try {
      // Fetch both ingest status and FPS data in parallel
      const [ingestResponse, fpsResponse] = await Promise.all([
        r58Api.getInputsStatus(),
        r58Api.getFps().catch(() => null) // FPS endpoint is optional
      ])
      
      // Use shared camera labels
      
      // Build FPS lookup from real data
      const fpsData: Record<string, number> = {}
      if (fpsResponse?.cameras) {
        for (const [id, fps] of Object.entries(fpsResponse.cameras)) {
          fpsData[id] = fps.current_fps
        }
      }
      
      // Map API response (cameras object) to InputStatus array
      inputs.value = Object.entries(ingestResponse.cameras).map(([id, cam]: [string, any]) => {
        // Use real FPS if available, otherwise estimate from resolution
        let framerate = fpsData[id]
        if (framerate === undefined || framerate === 0) {
          // Fallback: estimate based on resolution
          const height = cam.resolution?.height || 0
          framerate = height >= 2160 ? 30 : height > 0 ? 60 : 0
        }
        
        return {
          id,
          label: getCameraLabel(id),
          hasSignal: cam.has_signal || cam.status === 'streaming' || cam.status === 'preview',
          isRecording: cam.status === 'recording',
        bytesWritten: 0,
          resolution: cam.resolution?.formatted || '',
          framerate: Math.round(framerate * 10) / 10, // Round to 1 decimal
        }
      })
      
      inputsLoaded.value = true
      console.log(`[Recorder] Loaded ${inputs.value.length} inputs, ${inputs.value.filter(i => i.hasSignal).length} with signal`)
    } catch (error) {
      console.error('Failed to fetch inputs status:', error)
      // Keep existing inputs on error
    }
  }

  let durationInterval: number | null = null
  
  function startDurationTimer() {
    if (durationInterval) {
      clearInterval(durationInterval)
    }
    durationInterval = window.setInterval(() => {
      if (currentSession.value) {
        duration.value = Date.now() - currentSession.value.startedAt.getTime()
      }
    }, 100)
  }

  function updateFromEvent(event: { duration_ms?: number; bytes_written?: Record<string, number>; session_id?: string; inputs?: InputStatus[] }) {
    if (event.duration_ms !== undefined) {
      duration.value = event.duration_ms
      durationMs.value = event.duration_ms
    }
    if (event.session_id) {
      sessionId.value = event.session_id
    }
    if (event.bytes_written) {
      // Update bytes written per input
      for (const [inputId, bytes] of Object.entries(event.bytes_written)) {
        const input = inputs.value.find(i => i.id === inputId)
        if (input) {
          input.bytesWritten = bytes
        }
      }
    }
    if (event.inputs) {
      // Update input statuses from WebSocket event
      event.inputs.forEach(update => {
        const input = inputs.value.find(i => i.id === update.id)
        if (input) {
          Object.assign(input, update)
        }
      })
    }
  }

  function updateInputSignal(inputId: string, hasSignal: boolean, resolution?: string, framerate?: number) {
    const input = inputs.value.find(i => i.id === inputId)
    if (input) {
      input.hasSignal = hasSignal
      if (resolution) input.resolution = resolution
      if (framerate) input.framerate = framerate
    }
  }

  return {
    // State
    status,
    sessionId,
    currentSession,
    duration,
    durationMs,
    inputs,
    inputsLoaded,
    lastError,
    
    // Computed
    isRecording,
    formattedDuration,
    activeInputs,
    framerateMismatch,
    
    // Actions
    startRecording,
    stopRecording,
    fetchStatus,
    fetchInputs,
    updateFromEvent,
    updateInputSignal,
  }
})

