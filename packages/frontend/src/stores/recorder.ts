import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

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

  // Actions
  async function startRecording(sessionName?: string) {
    status.value = 'starting'
    
    try {
      // TODO: Call API to start recording
      // const response = await fetch('/api/v1/recorder/start', { method: 'POST', ... })
      
      currentSession.value = {
        id: crypto.randomUUID(),
        name: sessionName || null,
        startedAt: new Date(),
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
    } catch (error) {
      console.error('Failed to start recording:', error)
      status.value = 'idle'
    }
  }

  async function stopRecording() {
    status.value = 'stopping'
    
    try {
      // TODO: Call API to stop recording
      // const response = await fetch('/api/v1/recorder/stop', { method: 'POST', ... })
      
      // Stop all inputs
      inputs.value.forEach(input => {
        input.isRecording = false
      })
      
      currentSession.value = null
      duration.value = 0
      status.value = 'idle'
    } catch (error) {
      console.error('Failed to stop recording:', error)
      status.value = 'recording'
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
    
    // Computed
    isRecording,
    formattedDuration,
    activeInputs,
    
    // Actions
    startRecording,
    stopRecording,
    updateFromEvent,
    updateInputSignal,
  }
})

