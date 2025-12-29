/**
 * WebSocket connection composable for real-time events
 */
import { ref, onMounted, onUnmounted } from 'vue'
import { useRecorderStore } from '@/stores/recorder'
import { useMixerStore } from '@/stores/mixer'
import { buildWsUrl, getDeviceUrl } from '@/lib/api'

interface BaseEvent {
  v: number
  type: string
  ts: string
  seq: number
  device_id: string
  payload?: any
}

export function useR58WebSocket() {
  const isConnected = ref(false)
  const lastSeq = ref(0)
  const reconnectAttempts = ref(0)
  
  let ws: WebSocket | null = null
  let reconnectTimeout: number | null = null
  
  const recorderStore = useRecorderStore()
  const mixerStore = useMixerStore()
  
  function getWsUrl(): string {
    // Use the centralized URL builder that supports Electron device configuration
    return buildWsUrl('/api/v1/ws')
  }
  
  function connect() {
    if (ws?.readyState === WebSocket.OPEN) return
    
    const url = getWsUrl()
    console.log('[WebSocket] Connecting to', url)
    
    ws = new WebSocket(url)
    
    ws.onopen = () => {
      console.log('[WebSocket] Connected')
      isConnected.value = true
      reconnectAttempts.value = 0
      
      // Request state sync from last known sequence
      ws?.send(JSON.stringify({
        type: 'sync_request',
        last_seq: lastSeq.value
      }))
    }
    
    ws.onmessage = (msg) => {
      try {
        const event: BaseEvent = JSON.parse(msg.data)
        
        // Update sequence tracker
        if (event.seq > lastSeq.value) {
          lastSeq.value = event.seq
        }
        
        handleEvent(event)
      } catch (e) {
        console.error('[WebSocket] Failed to parse message:', e)
      }
    }
    
    ws.onclose = () => {
      console.log('[WebSocket] Disconnected')
      isConnected.value = false
      scheduleReconnect()
    }
    
    ws.onerror = (error) => {
      console.error('[WebSocket] Error:', error)
    }
  }
  
  function scheduleReconnect() {
    if (reconnectTimeout) {
      clearTimeout(reconnectTimeout)
    }
    
    // Exponential backoff: 1s, 2s, 4s, 8s, 16s, max 30s
    const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.value), 30000)
    reconnectAttempts.value++
    
    console.log(`[WebSocket] Reconnecting in ${delay}ms (attempt ${reconnectAttempts.value})`)
    
    reconnectTimeout = window.setTimeout(() => {
      connect()
    }, delay)
  }
  
  function disconnect() {
    if (reconnectTimeout) {
      clearTimeout(reconnectTimeout)
    }
    ws?.close()
    ws = null
  }
  
  function handleEvent(event: BaseEvent) {
    switch (event.type) {
      // Sync response - restore full state on reconnect
      case 'sync_response':
        handleSyncResponse(event.payload)
        break
        
      // Recorder events
      case 'recorder.started':
        recorderStore.status = 'recording'
        if (event.payload?.session_id) {
          recorderStore.sessionId = event.payload.session_id
        }
        break
        
      case 'recorder.stopped':
        recorderStore.status = 'idle'
        recorderStore.sessionId = null
        break
        
      case 'recorder.progress':
        console.log('[WebSocket] Received recorder.progress:', event.payload)
        recorderStore.updateFromEvent(event.payload)
        break
        
      // Input events
      case 'input.signal_changed':
        recorderStore.updateInputSignal(
          event.payload.input_id,
          event.payload.has_signal,
          event.payload.resolution,
          event.payload.framerate
        )
        break
        
      // Mixer events
      case 'mixer.scene_changed':
        mixerStore.setScene(event.payload.scene)
        break
        
      case 'mixer.source_updated':
        // Update source from event
        break
        
      // System events
      case 'health.changed':
        console.log('[Health]', event.payload)
        break
        
      case 'storage.warning':
        console.warn('[Storage Warning]', event.payload)
        break
        
      case 'connected':
        console.log('[WebSocket] Connected to device:', event.device_id)
        break
        
      case 'heartbeat':
        // Keep-alive events - silent
        break
        
      default:
        console.log('[WebSocket] Unknown event:', event.type, event.payload)
    }
  }
  
  function handleSyncResponse(payload: any) {
    /**
     * Handle sync response from server.
     * This restores full state after a reconnection.
     */
    const { state, events, can_replay, missed_event_count, current_seq } = payload
    
    console.log(`[WebSocket] Sync response: ${missed_event_count} missed events, can_replay=${can_replay}`)
    
    // Update our sequence to match server
    if (current_seq) {
      lastSeq.value = current_seq
    }
    
    // Restore authoritative state
    if (state) {
      // Restore mode
      if (state.mode === 'recording' && state.recording) {
        recorderStore.status = 'recording'
        recorderStore.sessionId = state.recording.session_id
        recorderStore.durationMs = state.recording.duration_ms || 0
      } else {
        recorderStore.status = 'idle'
        recorderStore.sessionId = null
      }
      
      // Restore input states
      if (state.inputs) {
        for (const [inputId, inputState] of Object.entries(state.inputs as Record<string, any>)) {
          recorderStore.updateInputSignal(
            inputId,
            inputState.has_signal,
            inputState.resolution,
            inputState.framerate
          )
        }
      }
    }
    
    // Replay missed events in order
    if (events && events.length > 0) {
      console.log(`[WebSocket] Replaying ${events.length} missed events`)
      for (const event of events) {
        // Skip sync_response to avoid infinite loop
        if (event.type !== 'sync_response') {
          handleEvent(event)
        }
      }
    }
    
    console.log('[WebSocket] State sync complete')
  }
  
  function send(type: string, payload?: any) {
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type, payload }))
    }
  }
  
  onMounted(() => {
    connect()
  })
  
  onUnmounted(() => {
    disconnect()
  })
  
  return {
    isConnected,
    connect,
    disconnect,
    send,
  }
}

