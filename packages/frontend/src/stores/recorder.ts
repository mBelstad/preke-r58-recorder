import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { r58Api } from '@/lib/api'

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
  const inputs = ref<InputStatus[]>([
    { id: 'cam1', label: 'HDMI 1', hasSignal: true, isRecording: false, bytesWritten: 0, resolution: '1920x1080', framerate: 30 },
    { id: 'cam2', label: 'HDMI 2', hasSignal: true, isRecording: false, bytesWritten: 0, resolution: '1920x1080', framerate: 30 },
    { id: 'cam3', label: 'HDMI 3', hasSignal: false, isRecording: false, bytesWritten: 0, resolution: '', framerate: 0 },
    { id: 'cam4', label: 'HDMI 4', hasSignal: false, isRecording: false, bytesWritten: 0, resolution: '', framerate: 0 },
  ])

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
      
      // Store final duration before clearing
      const finalDuration = duration.value
      
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
     */
    try {
      const response = await r58Api.getRecorderStatus()
      
      if (response.status === 'recording') {
        status.value = 'recording'
        sessionId.value = response.session_id || null
        duration.value = response.duration_ms
        durationMs.value = response.duration_ms
        
        // Mark inputs as recording
        response.inputs.forEach(inputId => {
          const input = inputs.value.find(i => i.id === inputId)
          if (input) {
            input.isRecording = true
          }
        })
        
        // Start duration timer
        startDurationTimer()
      } else {
        status.value = 'idle'
        sessionId.value = null
      }
    } catch (error) {
      console.error('Failed to fetch recorder status:', error)
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
    lastError,
    
    // Computed
    isRecording,
    formattedDuration,
    activeInputs,
    
    // Actions
    startRecording,
    stopRecording,
    fetchStatus,
    updateFromEvent,
    updateInputSignal,
  }
})

