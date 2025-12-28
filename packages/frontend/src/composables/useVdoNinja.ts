/**
 * VDO.ninja iframe communication composable
 * 
 * Provides bidirectional communication with embedded VDO.ninja via postMessage API
 */
import { ref, onMounted, onUnmounted, type Ref } from 'vue'
import { getVdoHost } from '@/lib/vdoninja'

export interface SourceInfo {
  id: string
  label: string
  type: 'camera' | 'guest' | 'screen' | 'media'
  hasVideo: boolean
  hasAudio: boolean
  muted: boolean
  audioLevel?: number
}

interface VdoMessage {
  action: string
  target?: string
  value?: any
}

interface VdoEvent {
  type: string
  streamID?: string
  data?: any
}

export function useVdoNinja(iframeRef: Ref<HTMLIFrameElement | null>) {
  const isReady = ref(false)
  const sources = ref<Map<string, SourceInfo>>(new Map())
  const activeScene = ref<string | null>(null)
  const VDO_HOST = getVdoHost()
  
  // ==========================================
  // SENDING COMMANDS TO VDO.NINJA
  // ==========================================
  
  function sendCommand(action: string, target?: string, value?: any) {
    if (!iframeRef.value?.contentWindow) {
      console.warn('VDO.ninja iframe not ready')
      return
    }
    
    const message: VdoMessage = { action }
    if (target) message.target = target
    if (value !== undefined) message.value = value
    
    iframeRef.value.contentWindow.postMessage(message, '*')
  }
  
  // --- Scene Control ---
  
  /** Switch to a different scene/layout */
  function setScene(sceneId: string) {
    sendCommand('changeScene', undefined, sceneId)
    activeScene.value = sceneId
  }
  
  /** Set source to program output */
  function setProgram(streamId: string) {
    sendCommand('soloVideo', streamId)
  }
  
  /** Toggle picture-in-picture for a source */
  function togglePiP(streamId: string, enabled: boolean) {
    sendCommand('pip', streamId, enabled ? 'enable' : 'disable')
  }
  
  // --- Audio Control ---
  
  /** Mute/unmute a specific source */
  function setMute(streamId: string, muted: boolean) {
    sendCommand('mute', streamId, muted)
    const source = sources.value.get(streamId)
    if (source) {
      source.muted = muted
    }
  }
  
  /** Set volume for a source (0-100) */
  function setVolume(streamId: string, volume: number) {
    sendCommand('volume', streamId, Math.max(0, Math.min(100, volume)))
  }
  
  /** Mute all sources except one */
  function soloAudio(streamId: string) {
    sendCommand('soloChat', streamId)
  }
  
  // --- Source Control ---
  
  /** Highlight a source (visual indicator) */
  function highlightSource(streamId: string) {
    sendCommand('highlight', streamId)
  }
  
  /** Send message to a specific guest */
  function sendToGuest(streamId: string, message: string) {
    sendCommand('sendChat', streamId, message)
  }
  
  /** Kick a guest from the room */
  function kickGuest(streamId: string) {
    sendCommand('hangup', streamId)
    sources.value.delete(streamId)
  }
  
  /** Request guest to share screen */
  function requestScreenShare(streamId: string) {
    sendCommand('requestScreen', streamId)
  }
  
  // --- Recording/Streaming ---
  
  /** Start local recording in VDO.ninja */
  function startRecording() {
    sendCommand('record', undefined, true)
  }
  
  /** Stop local recording */
  function stopRecording() {
    sendCommand('record', undefined, false)
  }
  
  // --- Layout/Display ---
  
  /** Set layout mode */
  function setLayout(layout: 'grid' | 'solo' | 'pip' | 'custom') {
    sendCommand('layout', undefined, layout)
  }
  
  /** Force refresh a source */
  function refreshSource(streamId: string) {
    sendCommand('reload', streamId)
  }
  
  // ==========================================
  // RECEIVING EVENTS FROM VDO.NINJA
  // ==========================================
  
  function handleMessage(event: MessageEvent) {
    // Validate origin - accept from VDO.ninja host
    const origin = event.origin
    if (!origin.includes(VDO_HOST.split(':')[0]) && 
        !origin.includes('vdo.ninja') &&
        !origin.includes('localhost')) {
      return
    }
    
    const data = event.data as VdoEvent
    if (!data || typeof data !== 'object') return
    
    switch (data.type) {
      case 'director-ready':
      case 'loaded':
      case 'ready':
        isReady.value = true
        break
        
      case 'new-guest':
      case 'guest-connected':
        // New source joined
        if (data.streamID) {
          sources.value.set(data.streamID, {
            id: data.streamID,
            label: data.data?.label || data.streamID,
            type: data.data?.type || 'guest',
            hasVideo: true,
            hasAudio: true,
            muted: false,
            audioLevel: 0,
          })
        }
        break
        
      case 'guest-left':
      case 'guest-disconnected':
        if (data.streamID) {
          sources.value.delete(data.streamID)
        }
        break
        
      case 'audio-level':
        // Audio meter update
        if (data.streamID) {
          const source = sources.value.get(data.streamID)
          if (source) {
            source.audioLevel = data.data?.level || 0
          }
        }
        break
        
      case 'mute-state':
        if (data.streamID) {
          const src = sources.value.get(data.streamID)
          if (src) {
            src.muted = data.data?.muted || false
          }
        }
        break
        
      case 'scene-changed':
        activeScene.value = data.data?.scene || null
        break
        
      case 'error':
        console.error('[VDO.ninja Error]', data.data)
        break
    }
  }
  
  onMounted(() => {
    window.addEventListener('message', handleMessage)
    
    // Set a timeout to mark as ready if no explicit ready event
    setTimeout(() => {
      if (!isReady.value && iframeRef.value) {
        isReady.value = true
      }
    }, 5000)
  })
  
  onUnmounted(() => {
    window.removeEventListener('message', handleMessage)
  })
  
  return {
    // State
    isReady,
    sources,
    activeScene,
    
    // Scene control
    setScene,
    setProgram,
    togglePiP,
    setLayout,
    
    // Audio control
    setMute,
    setVolume,
    soloAudio,
    
    // Source control
    highlightSource,
    sendToGuest,
    kickGuest,
    requestScreenShare,
    refreshSource,
    
    // Recording
    startRecording,
    stopRecording,
    
    // Low-level
    sendCommand,
  }
}

