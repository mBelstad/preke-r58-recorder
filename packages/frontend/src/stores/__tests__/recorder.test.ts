/**
 * Tests for recorder store state transitions
 * Priority: P0
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useRecorderStore } from '../recorder'
import { mockFetch, mockFetchResponse, mockFetchError, flushPromises } from '../../test/setup'

// Helper to mock a successful start recording response
function mockStartRecordingSuccess(sessionId = 'test-session-123') {
  mockFetchResponse({
    session_id: sessionId,
    name: 'Test Session',
    started_at: new Date().toISOString(),
    inputs: ['cam1', 'cam2'],
    status: 'recording',
  })
}

// Helper to mock a successful stop recording response  
function mockStopRecordingSuccess(sessionId = 'test-session-123', durationMs = 10000) {
  mockFetchResponse({
    session_id: sessionId,
    duration_ms: durationMs,
    files: { cam1: '/recordings/cam1.mp4', cam2: '/recordings/cam2.mp4' },
    status: 'stopped',
  })
}

// Default test inputs to populate the store
const DEFAULT_TEST_INPUTS = [
  { id: 'cam1', label: 'HDMI 1', hasSignal: true, isRecording: false, bytesWritten: 0, resolution: '1920x1080', framerate: 30 },
  { id: 'cam2', label: 'HDMI 2', hasSignal: true, isRecording: false, bytesWritten: 0, resolution: '1920x1080', framerate: 30 },
  { id: 'cam3', label: 'HDMI 3', hasSignal: false, isRecording: false, bytesWritten: 0, resolution: '', framerate: 0 },
  { id: 'cam4', label: 'HDMI 4', hasSignal: false, isRecording: false, bytesWritten: 0, resolution: '', framerate: 0 },
]

// Helper to set up the store with default inputs
function setupStoreWithInputs() {
  const store = useRecorderStore()
  // Populate inputs directly (simulating fetchInputs() result)
  store.inputs.push(...DEFAULT_TEST_INPUTS.map(i => ({ ...i })))
  return store
}

describe('RecorderStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    mockFetch.mockReset()
  })

  describe('Initial State', () => {
    it('has correct default values', () => {
      const store = useRecorderStore()
      
      expect(store.status).toBe('idle')
      expect(store.currentSession).toBeNull()
      expect(store.duration).toBe(0)
      // Store starts empty - inputs are fetched from API
      expect(store.inputs).toHaveLength(0)
    })

    it('has inputs after setup', () => {
      const store = setupStoreWithInputs()
      
      expect(store.inputs).toHaveLength(4)
      const inputIds = store.inputs.map(i => i.id)
      expect(inputIds).toContain('cam1')
      expect(inputIds).toContain('cam2')
      expect(inputIds).toContain('cam3')
      expect(inputIds).toContain('cam4')
    })

    it('isRecording computed is false initially', () => {
      const store = useRecorderStore()
      
      expect(store.isRecording).toBe(false)
    })

    it('formattedDuration is 00:00:00 initially', () => {
      const store = useRecorderStore()
      
      expect(store.formattedDuration).toBe('00:00:00')
    })
  })

  describe('startRecording', () => {
    it('transitions from idle to starting to recording', async () => {
      const store = useRecorderStore()
      mockStartRecordingSuccess()
      
      expect(store.status).toBe('idle')
      
      const startPromise = store.startRecording('Test Session')
      
      // Should immediately be starting
      expect(store.status).toBe('starting')
      
      await startPromise
      
      // Should be recording after success
      expect(store.status).toBe('recording')
    })

    it('creates a session on successful start', async () => {
      const store = useRecorderStore()
      mockStartRecordingSuccess()
      
      await store.startRecording('My Recording')
      
      expect(store.currentSession).not.toBeNull()
      expect(store.currentSession?.name).toBe('My Recording')
      expect(store.currentSession?.id).toBeDefined()
      expect(store.currentSession?.startedAt).toBeInstanceOf(Date)
    })

    it('marks inputs with signal as recording', async () => {
      const store = setupStoreWithInputs()
      mockStartRecordingSuccess()
      
      // cam1 and cam2 have signal by default
      await store.startRecording()
      
      const cam1 = store.inputs.find(i => i.id === 'cam1')
      const cam2 = store.inputs.find(i => i.id === 'cam2')
      const cam3 = store.inputs.find(i => i.id === 'cam3')
      
      expect(cam1?.isRecording).toBe(true)
      expect(cam2?.isRecording).toBe(true)
      expect(cam3?.isRecording).toBe(false) // No signal
    })

    it('handles start failure gracefully', async () => {
      const store = useRecorderStore()
      
      // Mock network error - fetch will fail after 4 retries
      mockFetch.mockRejectedValue(new TypeError('Network error'))
      
      try {
        await store.startRecording()
      } catch (e) {
        // Expected to throw
      }
      
      // Status should return to idle on failure
      expect(store.status).toBe('idle')
      expect(store.lastError).toBeTruthy()
    })

    it('can start without a session name', async () => {
      const store = useRecorderStore()
      mockStartRecordingSuccess()
      
      await store.startRecording()
      
      expect(store.currentSession).not.toBeNull()
      expect(store.currentSession?.name).toBeNull()
    })
  })

  describe('stopRecording', () => {
    it('transitions from recording to stopping to idle', async () => {
      const store = useRecorderStore()
      
      mockStartRecordingSuccess()
      await store.startRecording()
      expect(store.status).toBe('recording')
      
      mockStopRecordingSuccess()
      const stopPromise = store.stopRecording()
      
      // Should immediately be stopping
      expect(store.status).toBe('stopping')
      
      await stopPromise
      
      // Should be idle after success
      expect(store.status).toBe('idle')
    })

    it('clears session on stop', async () => {
      const store = useRecorderStore()
      
      mockStartRecordingSuccess()
      await store.startRecording('To Be Stopped')
      expect(store.currentSession).not.toBeNull()
      
      mockStopRecordingSuccess()
      await store.stopRecording()
      
      expect(store.currentSession).toBeNull()
    })

    it('resets duration on stop', async () => {
      const store = useRecorderStore()
      
      mockStartRecordingSuccess()
      await store.startRecording()
      store.duration = 5000 // Simulate some duration
      
      mockStopRecordingSuccess()
      await store.stopRecording()
      
      expect(store.duration).toBe(0)
    })

    it('marks all inputs as not recording', async () => {
      const store = setupStoreWithInputs()
      
      mockStartRecordingSuccess()
      await store.startRecording()
      
      // Verify some are recording
      expect(store.inputs.some(i => i.isRecording)).toBe(true)
      
      mockStopRecordingSuccess()
      await store.stopRecording()
      
      // All should be stopped
      expect(store.inputs.every(i => !i.isRecording)).toBe(true)
    })
  })

  describe('updateFromEvent', () => {
    it('updates duration from WebSocket event', async () => {
      const store = useRecorderStore()
      
      mockStartRecordingSuccess()
      await store.startRecording()
      
      store.updateFromEvent({ duration_ms: 10000 })
      
      expect(store.duration).toBe(10000)
    })

    it('updates input statuses from event', async () => {
      const store = setupStoreWithInputs()
      
      mockStartRecordingSuccess()
      await store.startRecording()
      
      store.updateFromEvent({
        duration_ms: 5000,
        inputs: [
          { id: 'cam1', bytesWritten: 1024000 } as any
        ]
      })
      
      const cam1 = store.inputs.find(i => i.id === 'cam1')
      expect(cam1?.bytesWritten).toBe(1024000)
    })

    it('handles event with missing inputs gracefully', async () => {
      const store = useRecorderStore()
      
      mockStartRecordingSuccess()
      await store.startRecording()
      
      // Should not throw
      store.updateFromEvent({ duration_ms: 5000 })
      
      expect(store.duration).toBe(5000)
    })

    it('ignores updates for unknown inputs', async () => {
      const store = useRecorderStore()
      
      mockStartRecordingSuccess()
      await store.startRecording()
      
      // Should not throw
      store.updateFromEvent({
        duration_ms: 5000,
        inputs: [
          { id: 'unknown-input', bytesWritten: 1000 } as any
        ]
      })
      
      expect(store.duration).toBe(5000)
    })
  })

  describe('updateInputSignal', () => {
    it('updates signal status for an input', () => {
      const store = setupStoreWithInputs()
      
      // cam3 starts with no signal
      let cam3 = store.inputs.find(i => i.id === 'cam3')
      expect(cam3?.hasSignal).toBe(false)
      
      store.updateInputSignal('cam3', true, '1920x1080', 30)
      
      cam3 = store.inputs.find(i => i.id === 'cam3')
      expect(cam3?.hasSignal).toBe(true)
      expect(cam3?.resolution).toBe('1920x1080')
      expect(cam3?.framerate).toBe(30)
    })

    it('handles signal loss', () => {
      const store = setupStoreWithInputs()
      
      // cam1 starts with signal
      let cam1 = store.inputs.find(i => i.id === 'cam1')
      expect(cam1?.hasSignal).toBe(true)
      
      store.updateInputSignal('cam1', false)
      
      cam1 = store.inputs.find(i => i.id === 'cam1')
      expect(cam1?.hasSignal).toBe(false)
    })

    it('ignores unknown input ids', () => {
      const store = setupStoreWithInputs()
      
      // Should not throw
      store.updateInputSignal('unknown-cam', true)
      
      // No input should have been affected
      expect(store.inputs.every(i => i.id !== 'unknown-cam')).toBe(true)
    })

    it('updates only provided optional fields', () => {
      const store = setupStoreWithInputs()
      
      const cam1 = store.inputs.find(i => i.id === 'cam1')
      const originalResolution = cam1?.resolution
      
      // Update only signal status
      store.updateInputSignal('cam1', true)
      
      // Resolution should be unchanged
      expect(cam1?.resolution).toBe(originalResolution)
    })
  })

  describe('Computed Properties', () => {
    it('activeInputs returns only inputs with signal', () => {
      const store = setupStoreWithInputs()
      
      // Default: cam1 and cam2 have signal
      expect(store.activeInputs).toHaveLength(2)
      expect(store.activeInputs.map(i => i.id)).toContain('cam1')
      expect(store.activeInputs.map(i => i.id)).toContain('cam2')
    })

    it('activeInputs updates when signal changes', () => {
      const store = setupStoreWithInputs()
      
      expect(store.activeInputs).toHaveLength(2)
      
      store.updateInputSignal('cam3', true, '1920x1080', 30)
      
      expect(store.activeInputs).toHaveLength(3)
      expect(store.activeInputs.map(i => i.id)).toContain('cam3')
    })

    it('formattedDuration formats correctly', async () => {
      const store = useRecorderStore()
      
      mockStartRecordingSuccess()
      await store.startRecording()
      
      // Test various durations
      store.duration = 0
      expect(store.formattedDuration).toBe('00:00:00')
      
      store.duration = 1000 // 1 second
      expect(store.formattedDuration).toBe('00:00:01')
      
      store.duration = 60000 // 1 minute
      expect(store.formattedDuration).toBe('00:01:00')
      
      store.duration = 3661000 // 1 hour, 1 minute, 1 second
      expect(store.formattedDuration).toBe('01:01:01')
    })
  })
})

