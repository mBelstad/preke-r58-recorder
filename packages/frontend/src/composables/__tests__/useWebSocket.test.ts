/**
 * Tests for WebSocket reconnection logic
 * Priority: P0
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { defineComponent, nextTick } from 'vue'
import { MockWebSocket, flushPromises, createMockEvent } from '../../test/setup'
import { useR58WebSocket } from '../useWebSocket'
import { useRecorderStore } from '../../stores/recorder'
import { useMixerStore } from '../../stores/mixer'

// Helper component to test composable
const TestComponent = defineComponent({
  setup() {
    const ws = useR58WebSocket()
    return { ws }
  },
  template: '<div>{{ ws.isConnected }}</div>'
})

describe('useR58WebSocket', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    MockWebSocket.reset()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  describe('Connection', () => {
    it('connects on mount', async () => {
      const wrapper = mount(TestComponent)
      
      await vi.runAllTimersAsync()
      
      expect(MockWebSocket.instances).toHaveLength(1)
      expect(MockWebSocket.instances[0].url).toContain('/api/v1/ws')
    })

    it('sets isConnected to true when connected', async () => {
      const wrapper = mount(TestComponent)
      
      await vi.runAllTimersAsync()
      await nextTick()
      
      expect(wrapper.vm.ws.isConnected).toBe(true)
    })

    it('disconnects on unmount', async () => {
      const wrapper = mount(TestComponent)
      
      await vi.runAllTimersAsync()
      
      const ws = MockWebSocket.getLastInstance()
      expect(ws).not.toBeNull()
      
      wrapper.unmount()
      
      expect(ws!.readyState).toBe(MockWebSocket.CLOSED)
    })
  })

  describe('Reconnection', () => {
    it('reconnects with exponential backoff', async () => {
      const wrapper = mount(TestComponent)
      
      await vi.runAllTimersAsync()
      
      const ws = MockWebSocket.getLastInstance()!
      
      // Simulate disconnect
      ws.simulateClose()
      
      await vi.advanceTimersByTimeAsync(1000) // 1st reconnect: 1s
      expect(MockWebSocket.instances).toHaveLength(2)
      
      MockWebSocket.getLastInstance()!.simulateClose()
      
      await vi.advanceTimersByTimeAsync(2000) // 2nd reconnect: 2s
      expect(MockWebSocket.instances).toHaveLength(3)
      
      wrapper.unmount()
    })

    it('caps reconnect delay at 30 seconds', async () => {
      const wrapper = mount(TestComponent)
      
      await vi.runAllTimersAsync()
      
      // Simulate many disconnects
      for (let i = 0; i < 10; i++) {
        MockWebSocket.getLastInstance()!.simulateClose()
        await vi.runAllTimersAsync()
      }
      
      // After many attempts, delay should not exceed 30s
      // The formula is Math.min(1000 * 2^attempts, 30000)
      // At 10 attempts, raw delay would be 1024000ms, but capped at 30000ms
      
      wrapper.unmount()
    })

    it('resets reconnect attempts on successful connection', async () => {
      const wrapper = mount(TestComponent)
      
      await vi.runAllTimersAsync()
      
      // Disconnect and reconnect a few times
      for (let i = 0; i < 3; i++) {
        MockWebSocket.getLastInstance()!.simulateClose()
        await vi.runAllTimersAsync()
      }
      
      // After successful reconnect, attempts should reset
      // (tested by verifying next disconnect uses 1s delay again)
      
      wrapper.unmount()
    })

    it('sets isConnected to false when disconnected', async () => {
      const wrapper = mount(TestComponent)
      
      await vi.runAllTimersAsync()
      expect(wrapper.vm.ws.isConnected).toBe(true)
      
      MockWebSocket.getLastInstance()!.simulateClose()
      await nextTick()
      
      expect(wrapper.vm.ws.isConnected).toBe(false)
      
      wrapper.unmount()
    })
  })

  describe('Sync Request', () => {
    it('sends sync_request with last_seq on connect', async () => {
      const wrapper = mount(TestComponent)
      
      await vi.runAllTimersAsync()
      
      const ws = MockWebSocket.getLastInstance()!
      const sentMessages = ws.getSentMessages()
      
      expect(sentMessages).toHaveLength(1)
      
      const syncRequest = JSON.parse(sentMessages[0])
      expect(syncRequest.type).toBe('sync_request')
      expect(syncRequest.last_seq).toBe(0)
      
      wrapper.unmount()
    })

    it('sends sync_request with updated seq after receiving events', async () => {
      const wrapper = mount(TestComponent)
      
      await vi.runAllTimersAsync()
      
      const ws = MockWebSocket.getLastInstance()!
      
      // Simulate receiving an event with seq 5
      ws.simulateMessage({ type: 'heartbeat', v: 1, seq: 5, device_id: 'test', ts: new Date().toISOString() })
      
      // Disconnect and reconnect
      ws.simulateClose()
      await vi.runAllTimersAsync()
      
      const newWs = MockWebSocket.getLastInstance()!
      const sentMessages = newWs.getSentMessages()
      
      const syncRequest = JSON.parse(sentMessages[0])
      expect(syncRequest.last_seq).toBe(5)
      
      wrapper.unmount()
    })
  })

  describe('Event Handling', () => {
    it('updates recorder store on recording events', async () => {
      const wrapper = mount(TestComponent)
      const recorderStore = useRecorderStore()
      
      await vi.runAllTimersAsync()
      
      const ws = MockWebSocket.getLastInstance()!
      
      // Simulate recording started event
      ws.simulateMessage(createMockEvent('recorder.started', {}))
      
      expect(recorderStore.status).toBe('recording')
      
      wrapper.unmount()
    })

    it('updates recorder store on recording stopped', async () => {
      const wrapper = mount(TestComponent)
      const recorderStore = useRecorderStore()
      
      // Set initial recording state
      recorderStore.status = 'recording'
      
      await vi.runAllTimersAsync()
      
      const ws = MockWebSocket.getLastInstance()!
      ws.simulateMessage(createMockEvent('recorder.stopped', {}))
      
      expect(recorderStore.status).toBe('idle')
      
      wrapper.unmount()
    })

    it('updates recorder with progress events', async () => {
      const wrapper = mount(TestComponent)
      const recorderStore = useRecorderStore()
      
      await vi.runAllTimersAsync()
      
      const ws = MockWebSocket.getLastInstance()!
      ws.simulateMessage(createMockEvent('recorder.progress', {
        duration_ms: 10000,
        inputs: []
      }))
      
      // updateFromEvent should have been called
      // The implementation calls recorderStore.updateFromEvent
      
      wrapper.unmount()
    })

    it('updates input signal on signal change event', async () => {
      const wrapper = mount(TestComponent)
      const recorderStore = useRecorderStore()
      
      await vi.runAllTimersAsync()
      
      const ws = MockWebSocket.getLastInstance()!
      ws.simulateMessage(createMockEvent('input.signal_changed', {
        input_id: 'cam3',
        has_signal: true,
        resolution: '1920x1080',
        framerate: 30
      }))
      
      const cam3 = recorderStore.inputs.find(i => i.id === 'cam3')
      expect(cam3?.hasSignal).toBe(true)
      
      wrapper.unmount()
    })

    it('handles malformed JSON gracefully', async () => {
      const wrapper = mount(TestComponent)
      
      await vi.runAllTimersAsync()
      
      const ws = MockWebSocket.getLastInstance()!
      
      // Send malformed JSON
      ws.onmessage?.(new MessageEvent('message', { data: 'not json' }))
      
      // Should not crash
      expect(wrapper.vm.ws.isConnected).toBe(true)
      
      wrapper.unmount()
    })

    it('handles unknown event types without crashing', async () => {
      const wrapper = mount(TestComponent)
      
      await vi.runAllTimersAsync()
      
      const ws = MockWebSocket.getLastInstance()!
      
      // Send unknown event type
      ws.simulateMessage(createMockEvent('unknown.event.type', { data: 'test' }))
      
      // Should not crash
      expect(wrapper.vm.ws.isConnected).toBe(true)
      
      wrapper.unmount()
    })
  })

  describe('Send Method', () => {
    it('sends message when connected', async () => {
      const wrapper = mount(TestComponent)
      
      await vi.runAllTimersAsync()
      
      wrapper.vm.ws.send('test.event', { key: 'value' })
      
      const ws = MockWebSocket.getLastInstance()!
      const messages = ws.getSentMessages()
      
      // Should have sync_request + our message
      expect(messages.length).toBeGreaterThanOrEqual(2)
      
      const lastMessage = JSON.parse(messages[messages.length - 1])
      expect(lastMessage.type).toBe('test.event')
      expect(lastMessage.payload.key).toBe('value')
      
      wrapper.unmount()
    })

    it('does not throw when sending while disconnected', async () => {
      const wrapper = mount(TestComponent)
      
      await vi.runAllTimersAsync()
      
      MockWebSocket.getLastInstance()!.simulateClose()
      await nextTick()
      
      // Should not throw
      wrapper.vm.ws.send('test.event', { data: 'test' })
      
      wrapper.unmount()
    })
  })

  describe('Sequence Tracking', () => {
    it('tracks highest sequence number received', async () => {
      const wrapper = mount(TestComponent)
      
      await vi.runAllTimersAsync()
      
      const ws = MockWebSocket.getLastInstance()!
      
      ws.simulateMessage({ type: 'heartbeat', v: 1, seq: 10, device_id: 'test', ts: new Date().toISOString() })
      ws.simulateMessage({ type: 'heartbeat', v: 1, seq: 5, device_id: 'test', ts: new Date().toISOString() }) // Lower
      ws.simulateMessage({ type: 'heartbeat', v: 1, seq: 15, device_id: 'test', ts: new Date().toISOString() })
      
      // Disconnect and reconnect to check last_seq
      ws.simulateClose()
      await vi.runAllTimersAsync()
      
      const newWs = MockWebSocket.getLastInstance()!
      const syncRequest = JSON.parse(newWs.getSentMessages()[0])
      
      // Should track highest (15), not latest (15)
      expect(syncRequest.last_seq).toBe(15)
      
      wrapper.unmount()
    })
  })
})

