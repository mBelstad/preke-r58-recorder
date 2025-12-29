/**
 * VDO.ninja iframe communication composable
 * 
 * Provides bidirectional communication with embedded VDO.ninja via postMessage API
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
  const activeScene = ref<string | null>(null)
  const isRecording = ref(false)
  const connectionState = ref<'disconnected' | 'connecting' | 'connected'>('disconnected')
  const lastError = ref<string | null>(null)
  const VDO_HOST = getVdoHost()
  
  // ==========================================
  // SENDING COMMANDS TO VDO.NINJA
  // ==========================================
  
  function sendCommand(action: string, target?: string, value?: unknown): void {
    if (!iframeRef.value?.contentWindow) {
      console.warn('[VDO.ninja] Cannot send command - iframe not ready')
      lastError.value = 'iframe not ready'
      return
    }
    
    const message: VdoMessage = { action }
    if (target) message.target = target
    if (value !== undefined) message.value = value
    
    // Log outgoing command
    logDebugEntry({
      timestamp: Date.now(),
      direction: 'outgoing',
      type: action,
      target,
      data: { action, target, value },
      raw: message
    })
    
    try {
      iframeRef.value.contentWindow.postMessage(message, '*')
    } catch (err) {
      console.error('[VDO.ninja] Failed to send command:', err)
      lastError.value = String(err)
    }
  }
  
  // --- Scene Control ---
  
  /** Switch to a different scene/layout */
  function setScene(sceneId: string): void {
    sendCommand('changeScene', undefined, sceneId)
    activeScene.value = sceneId
  }
  
  /** Set source to program output */
  function setProgram(streamId: string): void {
    sendCommand('soloVideo', streamId)
  }
  
  /** Toggle picture-in-picture for a source */
  function togglePiP(streamId: string, enabled: boolean): void {
    sendCommand('pip', streamId, enabled ? 'enable' : 'disable')
  }
  
  // --- Audio Control ---
  
  /** Mute/unmute a specific source */
  function setMute(streamId: string, muted: boolean): void {
    sendCommand('mute', streamId, muted)
    const source = sources.value.get(streamId)
    if (source) {
      source.muted = muted
    }
  }
  
  /** Set volume for a source (0-100) */
  function setVolume(streamId: string, volume: number): void {
    sendCommand('volume', streamId, Math.max(0, Math.min(100, volume)))
  }
  
  /** Mute all sources except one */
  function soloAudio(streamId: string): void {
    sendCommand('soloChat', streamId)
  }
  
  // --- Source Control ---
  
  /** Highlight a source (visual indicator) */
  function highlightSource(streamId: string): void {
    sendCommand('highlight', streamId)
  }
  
  /** Send message to a specific guest */
  function sendToGuest(streamId: string, message: string): void {
    sendCommand('sendChat', streamId, message)
  }
  
  /** Kick a guest from the room */
  function kickGuest(streamId: string): void {
    sendCommand('hangup', streamId)
    sources.value.delete(streamId)
  }
  
  /** Request guest to share screen */
  function requestScreenShare(streamId: string): void {
    sendCommand('requestScreen', streamId)
  }
  
  /** Accept a guest into the room */
  function acceptGuest(streamId: string): void {
    sendCommand('addToScene', streamId)
  }
  
  /** Remove guest from scene (but keep in room) */
  function removeFromScene(streamId: string): void {
    sendCommand('removeFromScene', streamId)
  }
  
  // --- Recording/Streaming ---
  
  /** Start local recording in VDO.ninja */
  function startRecording(): void {
    sendCommand('record', undefined, true)
    isRecording.value = true
  }
  
  /** Stop local recording */
  function stopRecording(): void {
    sendCommand('record', undefined, false)
    isRecording.value = false
  }
  
  // --- Layout/Display ---
  
  /** Set layout mode */
  function setLayout(layout: 'grid' | 'solo' | 'pip' | 'custom'): void {
    sendCommand('layout', undefined, layout)
  }
  
  /** Force refresh a source */
  function refreshSource(streamId: string): void {
    sendCommand('reload', streamId)
  }
  
  /** Set custom slot positions (for custom layouts) */
  function setSlots(slotsConfig: Record<string, unknown>): void {
    sendCommand('setSlots', undefined, slotsConfig)
  }
  
  /** Toggle full screen for a source */
  function toggleFullscreen(streamId: string): void {
    sendCommand('fullscreen', streamId)
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
      case 'loaded':
      case 'ready':
      case 'started':
        isReady.value = true
        connectionState.value = 'connected'
        lastError.value = null
        break
        
      case 'new-guest':
      case 'guest-connected':
      case 'push':
      case 'view':
      case 'joined': {
        // New source joined
        if (streamId) {
          const eventData = data.data as Record<string, unknown> | undefined
          const sourceInfo: SourceInfo = {
            id: streamId,
            label: (eventData?.label as string) || data.label || streamId,
            type: (eventData?.type as SourceInfo['type']) || 'guest',
            hasVideo: eventData?.video !== false,
            hasAudio: eventData?.audio !== false,
            muted: false,
            audioLevel: 0,
          }
          sources.value.set(streamId, sourceInfo)
        }
        break
      }
        
      case 'guest-left':
      case 'guest-disconnected':
      case 'left':
      case 'disconnect':
        if (streamId) {
          sources.value.delete(streamId)
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
        activeScene.value = (eventData?.scene as string) || (data.value as string) || null
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
    activeScene,
    isRecording,
    connectionState,
    lastError,
    
    // Scene control
    setScene,
    setProgram,
    togglePiP,
    setLayout,
    setSlots,
    toggleFullscreen,
    
    // Audio control
    setMute,
    setVolume,
    soloAudio,
    
    // Source control
    highlightSource,
    sendToGuest,
    kickGuest,
    requestScreenShare,
    acceptGuest,
    removeFromScene,
    refreshSource,
    
    // Recording
    startRecording,
    stopRecording,
    
    // Low-level
    sendCommand,
    
    // Debug
    getEventHistory: getVdoEventHistory,
    getEventStats: getVdoEventStats,
  }
}
