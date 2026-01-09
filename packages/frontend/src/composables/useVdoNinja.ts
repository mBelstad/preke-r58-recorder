/**
 * VDO.ninja iframe communication composable
 * 
 * Provides bidirectional communication with embedded VDO.ninja via postMessage API
 * 
 * API Reference: https://docs.vdo.ninja/guides/iframe-api-documentation/iframe-api-for-directors
 * 
 * Debug Mode:
 * - Enable via localStorage: localStorage.setItem('vdo-debug', 'true')
 * - Access event history: window.__VDO_DEBUG__.getHistory()
 * - Clear history: window.__VDO_DEBUG__.clearHistory()
 */
import { ref, onMounted, onUnmounted, type Ref } from 'vue'
import { getVdoHost } from '@/lib/vdoninja'

// ==========================================
// TYPE DEFINITIONS
// ==========================================

export interface SourceInfo {
  id: string
  label: string
  type: 'camera' | 'guest' | 'screen' | 'media'
  hasVideo: boolean
  hasAudio: boolean
  muted: boolean
  audioLevel?: number
}

export interface VdoMessage {
  action: string
  target?: string
  value?: unknown
  value2?: unknown
  // For DOM manipulation
  add?: boolean
  remove?: boolean
  replace?: boolean
  settings?: Record<string, unknown>
}

export interface VdoEvent {
  type: string
  streamID?: string
  data?: unknown
  action?: string
  value?: unknown
  UUID?: string
  streamId?: string
  label?: string
}

export interface VdoDebugEntry {
  timestamp: number
  direction: 'incoming' | 'outgoing'
  type: string
  target?: string
  data: unknown
  raw?: unknown
}

/** Custom layout slot position */
export interface VdoLayoutSlot {
  x: number      // X position (0-100%)
  y: number      // Y position (0-100%)
  w: number      // Width (0-100%)
  h: number      // Height (0-100%)
  slot: number   // Slot index
  c?: boolean    // Crop to fit
  z?: number     // Z-index
}

// ==========================================
// DEBUG INSTRUMENTATION
// ==========================================

const DEBUG_KEY = 'vdo-debug'
const MAX_HISTORY_SIZE = 500

// Event history for debugging
const eventHistory: VdoDebugEntry[] = []
let debugEnabled = typeof localStorage !== 'undefined' && localStorage.getItem(DEBUG_KEY) === 'true'

/**
 * Check if debug mode is enabled
 */
export function isVdoDebugEnabled(): boolean {
  return debugEnabled
}

/**
 * Enable/disable debug mode
 */
export function setVdoDebugEnabled(enabled: boolean): void {
  debugEnabled = enabled
  if (typeof localStorage !== 'undefined') {
    if (enabled) {
      localStorage.setItem(DEBUG_KEY, 'true')
    } else {
      localStorage.removeItem(DEBUG_KEY)
    }
  }
  console.log(`[VDO.ninja Debug] ${enabled ? 'Enabled' : 'Disabled'}`)
}

/**
 * Log a debug entry
 */
function logDebugEntry(entry: VdoDebugEntry): void {
  // Add to history
  eventHistory.push(entry)
  if (eventHistory.length > MAX_HISTORY_SIZE) {
    eventHistory.shift()
  }
  
  // Console output when debug mode is enabled
  if (debugEnabled) {
    const time = new Date(entry.timestamp).toISOString().split('T')[1].slice(0, -1)
    const direction = entry.direction === 'outgoing' ? '➡️ OUT' : '⬅️ IN'
    const style = entry.direction === 'outgoing' 
      ? 'color: #3b82f6; font-weight: bold' 
      : 'color: #22c55e; font-weight: bold'
    
    console.groupCollapsed(
      `%c[VDO.ninja ${direction}] %c${entry.type}`,
      style,
      'color: inherit'
    )
    console.log('Time:', time)
    if (entry.target) console.log('Target:', entry.target)
    console.log('Data:', entry.data)
    if (entry.raw && entry.raw !== entry.data) {
      console.log('Raw:', entry.raw)
    }
    console.groupEnd()
  }
}

/**
 * Get the debug event history
 */
export function getVdoEventHistory(): VdoDebugEntry[] {
  return [...eventHistory]
}

/**
 * Clear the debug event history
 */
export function clearVdoEventHistory(): void {
  eventHistory.length = 0
  console.log('[VDO.ninja Debug] Event history cleared')
}

/**
 * Get statistics about VDO.ninja events
 */
export function getVdoEventStats(): {
  total: number
  incoming: number
  outgoing: number
  byType: Record<string, number>
  lastActivity: number | null
} {
  const stats = {
    total: eventHistory.length,
    incoming: 0,
    outgoing: 0,
    byType: {} as Record<string, number>,
    lastActivity: eventHistory.length > 0 ? eventHistory[eventHistory.length - 1].timestamp : null
  }
  
  for (const entry of eventHistory) {
    if (entry.direction === 'incoming') stats.incoming++
    else stats.outgoing++
    
    stats.byType[entry.type] = (stats.byType[entry.type] || 0) + 1
  }
  
  return stats
}

// Expose debug utilities on window for developer console access
if (typeof window !== 'undefined') {
  (window as unknown as Record<string, unknown>).__VDO_DEBUG__ = {
    getHistory: getVdoEventHistory,
    clearHistory: clearVdoEventHistory,
    getStats: getVdoEventStats,
    enable: () => setVdoDebugEnabled(true),
    disable: () => setVdoDebugEnabled(false),
    isEnabled: () => debugEnabled,
  }
}

// ==========================================
// MAIN COMPOSABLE
// ==========================================

export function useVdoNinja(iframeRef: Ref<HTMLIFrameElement | null>) {
  const isReady = ref(false)
  const sources = ref<Map<string, SourceInfo>>(new Map())
  // Version counter to trigger reactivity when Map is mutated
  // Vue's deep watch doesn't reliably detect Map.set()/delete() calls
  const sourcesVersion = ref(0)
  const activeScene = ref<number | null>(null)
  const isRecording = ref(false)
  const connectionState = ref<'disconnected' | 'connecting' | 'connected'>('disconnected')
  const lastError = ref<string | null>(null)
  const VDO_HOST = getVdoHost()
  
  // Map UUID to stream ID - VDO.ninja scene operations require stream IDs, not UUIDs
  const uuidToStreamId = new Map<string, string>()
  
  // ==========================================
  // SENDING COMMANDS TO VDO.NINJA
  // ==========================================
  
  /**
   * Send a raw postMessage command to VDO.ninja
   * See: https://docs.vdo.ninja/guides/iframe-api-documentation/iframe-api-for-directors
   */
  function sendCommand(action: string, target?: string, value?: unknown, value2?: unknown): void {
    if (!iframeRef.value?.contentWindow) {
      console.warn('[VDO.ninja] Cannot send command - iframe not ready')
      lastError.value = 'iframe not ready'
      return
    }
    
    const message: VdoMessage = { action }
    if (target) message.target = target
    if (value !== undefined) message.value = value
    if (value2 !== undefined) message.value2 = value2
    
    // Log outgoing command
    logDebugEntry({
      timestamp: Date.now(),
      direction: 'outgoing',
      type: action,
      target,
      data: { action, target, value, value2 },
      raw: message
    })
    
    try {
      iframeRef.value.contentWindow.postMessage(message, '*')
    } catch (err) {
      console.error('[VDO.ninja] Failed to send command:', err)
      lastError.value = String(err)
    }
  }
  
  /**
   * Send a DOM manipulation command (add/remove/replace video elements)
   */
  function sendDomCommand(target: string, options: { add?: boolean; remove?: boolean; replace?: boolean; settings?: Record<string, unknown> }): void {
    if (!iframeRef.value?.contentWindow) {
      console.warn('[VDO.ninja] Cannot send DOM command - iframe not ready')
      return
    }
    
    const message: VdoMessage = { action: '', target, ...options }
    
    logDebugEntry({
      timestamp: Date.now(),
      direction: 'outgoing',
      type: 'dom-manipulation',
      target,
      data: options,
      raw: message
    })
    
    try {
      iframeRef.value.contentWindow.postMessage(message, '*')
    } catch (err) {
      console.error('[VDO.ninja] Failed to send DOM command:', err)
    }
  }
  
  // --- Scene Control ---
  
  /**
   * Add a guest to a scene (director command)
   * API: action: "addScene", target: streamID/slot, value: sceneNumber
   */
  function addToScene(targetId: string, sceneNumber: number = 1): void {
    // Resolve UUID to stream ID if we have a mapping (VDO.ninja scenes require stream IDs)
    const resolvedId = uuidToStreamId.get(targetId) || targetId
    if (resolvedId !== targetId) {
      console.log(`[VDO.ninja] Resolved UUID ${targetId} to stream ID ${resolvedId} for addToScene`)
    }
    
    // VDO.ninja API uses shorthand format: { addToScene: sceneNumber, target: streamId }
    // This is different from the standard { action: 'addToScene', target: ..., value: ... } format
    if (!iframeRef.value?.contentWindow) {
      console.warn('[VDO.ninja] Cannot send addToScene - iframe not ready')
      return
    }
    
    const message = { 
      addToScene: sceneNumber,
      target: resolvedId
    }
    
    logDebugEntry({
      timestamp: Date.now(),
      direction: 'outgoing',
      type: 'addToScene',
      target: resolvedId,
      data: { sceneNumber },
      raw: message
    })
    
    try {
      iframeRef.value.contentWindow.postMessage(message, '*')
      activeScene.value = sceneNumber
    } catch (err) {
      console.error('[VDO.ninja] Failed to send addToScene:', err)
    }
  }
  
  /**
   * Remove a guest from a scene
   * Note: This keeps them in the room but removes from the scene view
   */
  function removeFromScene(targetId: string, sceneNumber: number = 1): void {
    // Resolve UUID to stream ID if we have a mapping
    const resolvedId = uuidToStreamId.get(targetId) || targetId
    
    // VDO.ninja API uses shorthand format: { removeFromScene: sceneNumber, target: streamId }
    if (!iframeRef.value?.contentWindow) {
      console.warn('[VDO.ninja] Cannot send removeFromScene - iframe not ready')
      return
    }
    
    const message = { 
      removeFromScene: sceneNumber,
      target: resolvedId
    }
    
    logDebugEntry({
      timestamp: Date.now(),
      direction: 'outgoing',
      type: 'removeFromScene',
      target: resolvedId,
      data: { sceneNumber },
      raw: message
    })
    
    try {
      iframeRef.value.contentWindow.postMessage(message, '*')
    } catch (err) {
      console.error('[VDO.ninja] Failed to send removeFromScene:', err)
    }
  }
  
  /**
   * Set source as the solo/program output (replaces all others)
   * Uses DOM manipulation: target with replace: true
   */
  function setProgram(streamId: string): void {
    sendDomCommand(streamId, { replace: true })
  }
  
  /**
   * Add a source to the current view
   */
  function addSource(streamId: string): void {
    sendDomCommand(streamId, { add: true })
  }
  
  /**
   * Remove a source from the current view
   */
  function removeSource(streamId: string): void {
    sendDomCommand(streamId, { remove: true })
  }
  
  // --- Audio Control ---
  
  /**
   * Mute/unmute a specific source's microphone
   * API: action: "mic", target: streamID/slot, value: true/false/"toggle"
   */
  function setMute(streamId: string, muted: boolean): void {
    // VDO.ninja uses "mic" action, value false = muted, true = unmuted
    sendCommand('mic', streamId, !muted)
    const source = sources.value.get(streamId)
    if (source) {
      source.muted = muted
    }
  }
  
  /**
   * Toggle microphone for a source
   */
  function toggleMute(streamId: string): void {
    sendCommand('mic', streamId, 'toggle')
    const source = sources.value.get(streamId)
    if (source) {
      source.muted = !source.muted
    }
  }
  
  /**
   * Set volume for a source (0-200, 100 = normal)
   * API: action: "volume", target: streamID/slot, value: 0-200
   */
  function setVolume(streamId: string, volume: number): void {
    // VDO.ninja uses 0-200 scale (100 = normal, 200 = 2x gain)
    sendCommand('volume', streamId, Math.max(0, Math.min(200, volume)))
  }
  
  /**
   * Solo chat with a guest (only hear this guest)
   * API: action: "soloChat", target: streamID/slot
   */
  function soloAudio(streamId: string): void {
    sendCommand('soloChat', streamId)
  }
  
  /**
   * Two-way solo chat (private conversation)
   */
  function soloChatBidirectional(streamId: string): void {
    sendCommand('soloChatBidirectional', streamId)
  }
  
  // --- Source Control ---
  
  /**
   * Send chat message to a specific guest
   * API: action: "sendChat", target: streamID/slot, value: message
   */
  function sendToGuest(streamId: string, message: string): void {
    sendCommand('sendChat', streamId, message)
  }
  
  /**
   * Send overlay message to guest's screen (director notification)
   * API: action: "sendDirectorChat", target: streamID/slot, value: message
   */
  function sendDirectorMessage(streamId: string, message: string): void {
    sendCommand('sendDirectorChat', streamId, message)
  }
  
  /**
   * Kick a guest from the room
   * API: action: "hangup", target: streamID/slot
   */
  function kickGuest(streamId: string): void {
    sendCommand('hangup', streamId)
    sources.value.delete(streamId)
  }
  
  /**
   * Toggle screen share for a guest
   * API: action: "togglescreenshare" (self) or with target for director
   */
  function toggleScreenShare(streamId?: string): void {
    if (streamId) {
      sendCommand('togglescreenshare', streamId)
    } else {
      sendCommand('togglescreenshare')
    }
  }
  
  /**
   * Transfer guest to another room
   * API: action: "forward", target: streamID/slot, value: roomName
   */
  function transferGuest(streamId: string, roomName: string): void {
    sendCommand('forward', streamId, roomName)
  }
  
  /**
   * Get list of guests in room
   * API: action: "getGuestList", cib: callbackId
   */
  function getGuestList(callbackId: string = 'guests'): void {
    sendCommand('getGuestList', undefined, undefined)
  }
  
  // --- Recording/Streaming ---
  
  /**
   * Start local recording in VDO.ninja
   * API: action: "record", value: true
   */
  function startRecording(): void {
    sendCommand('record', undefined, true)
    isRecording.value = true
  }
  
  /**
   * Stop local recording
   * API: action: "record", value: false
   */
  function stopRecording(): void {
    sendCommand('record', undefined, false)
    isRecording.value = false
  }
  
  // --- Layout/Display ---
  
  /**
   * Set layout mode (preset number or custom array)
   * API: action: "layout", value: number | VdoLayoutSlot[]
   * 
   * Preset numbers:
   * - 0: Auto grid
   * - 1: Solo (first source fullscreen)
   * - 2: Side by side
   * - etc.
   * 
   * Custom: Array of {x, y, w, h, slot} objects (percentages)
   */
  function setLayout(layout: number | VdoLayoutSlot[]): void {
    sendCommand('layout', undefined, layout)
  }
  
  /**
   * Force refresh/reload a source
   * API: action: "reload", target: streamID (optional, self if omitted)
   */
  function refreshSource(streamId?: string): void {
    if (streamId) {
      sendCommand('reload', streamId)
    } else {
      sendCommand('reload')
    }
  }
  
  /**
   * Change mix order position for a guest
   * API: action: "mixorder", target: streamID/slot, value: -1 (up) or 1 (down)
   */
  function changeMixOrder(streamId: string, direction: 'up' | 'down'): void {
    sendCommand('mixorder', streamId, direction === 'up' ? -1 : 1)
  }
  
  // --- Camera Control ---
  
  /**
   * Control camera (self)
   * API: action: "camera", value: true/false/"toggle"
   */
  function setCamera(enabled: boolean | 'toggle'): void {
    sendCommand('camera', undefined, enabled)
  }
  
  /**
   * Control guest's camera (director command)
   */
  function setGuestCamera(streamId: string, enabled: boolean | 'toggle'): void {
    sendCommand('camera', streamId, enabled)
  }
  
  // --- PTZ Control ---
  
  /**
   * Zoom camera (requires &ptz on sender)
   * API: action: "zoom", value: relative (-1 to 1) or absolute with value2: "abs"
   */
  function zoom(amount: number, absolute: boolean = false): void {
    if (absolute) {
      sendCommand('zoom', undefined, amount, 'abs')
    } else {
      sendCommand('zoom', undefined, amount)
    }
  }
  
  /**
   * Pan camera
   */
  function pan(amount: number): void {
    sendCommand('pan', undefined, amount)
  }
  
  /**
   * Tilt camera
   */
  function tilt(amount: number): void {
    sendCommand('tilt', undefined, amount)
  }
  
  // ==========================================
  // RECEIVING EVENTS FROM VDO.NINJA
  // ==========================================
  
  function handleMessage(event: MessageEvent): void {
    // Validate origin - accept from VDO.ninja host
    const origin = event.origin
    if (!origin.includes(VDO_HOST.split(':')[0]) && 
        !origin.includes('vdo.ninja') &&
        !origin.includes('vdo.itagenten') &&
        !origin.includes('localhost')) {
      return
    }
    
    const data = event.data as VdoEvent
    if (!data || typeof data !== 'object') return
    
    // Handle various message formats (VDO.ninja has inconsistent API)
    const messageType = data.type || data.action || 'unknown'
    const streamId = data.streamID || data.UUID || data.streamId
    
    // Log incoming event
    logDebugEntry({
      timestamp: Date.now(),
      direction: 'incoming',
      type: messageType,
      target: streamId,
      data: data.data || data.value,
      raw: data
    })
    
    switch (messageType) {
      case 'director-ready':
      case 'mixer-ready':     // mixer.html sends this when ready
      case 'loaded':
      case 'ready':
      case 'started':
      case 'director':        // VDO.ninja sends this when director mode is active
      case 'joined-room-complete':  // VDO.ninja sends this when room join is complete
      case 'seeding-started': // VDO.ninja sends this when room is ready to accept connections
        isReady.value = true
        connectionState.value = 'connected'
        lastError.value = null
        console.log('[VDO.ninja] Ready event received:', messageType)
        break
        
      case 'stream-id-detected': {
        // VDO.ninja sends this to provide the short stream ID (e.g., "4v6AX33")
        // This is the ID that must be used for scene operations
        const detectedStreamId = (data.value as string) || (data.data as string)
        const uuid = data.UUID as string | undefined
        
        if (detectedStreamId) {
          // Store UUID -> streamID mapping if we have both
          if (uuid) {
            uuidToStreamId.set(uuid, detectedStreamId)
            console.log(`[VDO.ninja] Stream ID mapping: ${uuid} -> ${detectedStreamId}`)
            
            // If we have a source registered with UUID, update it to use stream ID
            const existingSource = sources.value.get(uuid)
            if (existingSource) {
              sources.value.delete(uuid)
              existingSource.id = detectedStreamId
              sources.value.set(detectedStreamId, existingSource)
              sourcesVersion.value++
              console.log(`[VDO.ninja] Updated source ID from UUID to stream ID: ${detectedStreamId}`)
            }
          }
          
          // Create source entry if it doesn't exist
          if (!sources.value.has(detectedStreamId)) {
            const sourceInfo: SourceInfo = {
              id: detectedStreamId,
              label: (data.label as string) || detectedStreamId,
              type: 'guest',
              hasVideo: true,
              hasAudio: true,
              muted: false,
              audioLevel: 0,
            }
            sources.value.set(detectedStreamId, sourceInfo)
            sourcesVersion.value++
            console.log(`[VDO.ninja] Source added via stream-id-detected: ${detectedStreamId}`)
          }
        }
        break
      }
      
      case 'new-guest':
      case 'guest-connected':
      case 'push':
      case 'view':
      case 'joined':
      case 'new-push-connection':   // VDO.ninja sends this when a guest starts pushing
      case 'push-connection':       // VDO.ninja sends this when push connection established
      case 'new-view-connection':   // VDO.ninja sends this when viewing starts
      case 'view-connection': {     // VDO.ninja sends this when view connection established
        // New source joined - prefer streamID over UUID for scene operations
        const uuid = data.UUID as string | undefined
        const actualStreamId = data.streamID as string | undefined
        
        // Use stream ID if available, otherwise UUID (will be updated later by stream-id-detected)
        const sourceId = actualStreamId || uuid || streamId
        
        if (sourceId) {
          // If we have UUID, store the mapping for later
          if (uuid && actualStreamId) {
            uuidToStreamId.set(uuid, actualStreamId)
          }
          
          const eventData = data.data as Record<string, unknown> | undefined
          const sourceInfo: SourceInfo = {
            id: sourceId,
            label: (eventData?.label as string) || data.label || sourceId,
            type: (eventData?.type as SourceInfo['type']) || 'guest',
            hasVideo: eventData?.video !== false,
            hasAudio: eventData?.audio !== false,
            muted: false,
            audioLevel: 0,
          }
          sources.value.set(sourceId, sourceInfo)
          sourcesVersion.value++  // Trigger reactivity for watchers
          console.log(`[VDO.ninja] Source added: ${sourceId} (${sourceInfo.label})${uuid && !actualStreamId ? ' (UUID, awaiting stream ID)' : ''}`)
        }
        break
      }
        
      case 'guest-left':
      case 'guest-disconnected':
      case 'left':
      case 'disconnect':
        if (streamId) {
          sources.value.delete(streamId)
          sourcesVersion.value++  // Trigger reactivity for watchers
        }
        break
        
      case 'audio-level':
      case 'loudness': {
        // Audio meter update
        if (streamId) {
          const source = sources.value.get(streamId)
          if (source) {
            const eventData = data.data as Record<string, unknown> | undefined
            source.audioLevel = (eventData?.level as number) || (data.value as number) || 0
          }
        }
        break
      }
        
      case 'mute-state':
      case 'muted': {
        if (streamId) {
          const src = sources.value.get(streamId)
          if (src) {
            const eventData = data.data as Record<string, unknown> | undefined
            src.muted = (eventData?.muted as boolean) ?? (data.value as boolean) ?? false
          }
        }
        break
      }
        
      case 'scene-changed':
      case 'scene': {
        const eventData = data.data as Record<string, unknown> | undefined
        const sceneValue = (eventData?.scene as number) || (data.value as number)
        activeScene.value = typeof sceneValue === 'number' ? sceneValue : null
        break
      }
      
      case 'recording-started':
        isRecording.value = true
        break
        
      case 'recording-stopped':
        isRecording.value = false
        break
        
      case 'error':
        console.error('[VDO.ninja Error]', data.data)
        lastError.value = String(data.data)
        break
        
      default:
        // Unhandled message types are still logged via logDebugEntry
        break
    }
  }
  
  onMounted(() => {
    connectionState.value = 'connecting'
    window.addEventListener('message', handleMessage)
    
    // Set a timeout to mark as ready if no explicit ready event
    setTimeout(() => {
      if (!isReady.value && iframeRef.value) {
        isReady.value = true
        connectionState.value = 'connected'
      }
    }, 5000)
  })
  
  onUnmounted(() => {
    window.removeEventListener('message', handleMessage)
    connectionState.value = 'disconnected'
  })
  
  return {
    // State
    isReady,
    sources,
    sourcesVersion,  // For triggering watchers on Map mutations
    activeScene,
    isRecording,
    connectionState,
    lastError,
    
    // Scene control (VERIFIED API)
    addToScene,
    removeFromScene,
    setProgram,
    addSource,
    removeSource,
    setLayout,
    changeMixOrder,
    
    // Audio control (VERIFIED API)
    setMute,
    toggleMute,
    setVolume,
    soloAudio,
    soloChatBidirectional,
    
    // Source control (VERIFIED API)
    sendToGuest,
    sendDirectorMessage,
    kickGuest,
    toggleScreenShare,
    transferGuest,
    getGuestList,
    refreshSource,
    
    // Camera control (VERIFIED API)
    setCamera,
    setGuestCamera,
    
    // PTZ (VERIFIED API - requires &ptz)
    zoom,
    pan,
    tilt,
    
    // Recording (VERIFIED API)
    startRecording,
    stopRecording,
    
    // Low-level
    sendCommand,
    sendDomCommand,
    
    // Debug
    getEventHistory: getVdoEventHistory,
    getEventStats: getVdoEventStats,
  }
}
