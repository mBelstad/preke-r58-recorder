import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { buildApiUrl } from '@/lib/api'

/**
 * Streaming platform presets
 */
export interface StreamingPlatform {
  id: string
  name: string
  icon: string
  rtmpBaseUrl: string
  streamKeyPlaceholder: string
  helpUrl?: string
}

export interface StreamingDestination {
  id: string
  platformId: string
  name: string
  streamKey: string
  enabled: boolean
}

export interface SrtOutput {
  enabled: boolean
  host: string
  port: number
  streamId: string
}

/**
 * Built-in streaming platform presets
 */
export const STREAMING_PLATFORMS: StreamingPlatform[] = [
  {
    id: 'youtube',
    name: 'YouTube Live',
    icon: '▶️',
    rtmpBaseUrl: 'rtmp://a.rtmp.youtube.com/live2/',
    streamKeyPlaceholder: 'xxxx-xxxx-xxxx-xxxx-xxxx',
    helpUrl: 'https://support.google.com/youtube/answer/2907883'
  },
  {
    id: 'twitch',
    name: 'Twitch',
    icon: '📺',
    rtmpBaseUrl: 'rtmp://live.twitch.tv/app/',
    streamKeyPlaceholder: 'live_xxxxxxxxxx_xxxxxxxxxxxxxx',
    helpUrl: 'https://help.twitch.tv/s/article/twitch-stream-key-faq'
  },
  {
    id: 'facebook',
    name: 'Facebook Live',
    icon: '📘',
    rtmpBaseUrl: 'rtmps://live-api-s.facebook.com:443/rtmp/',
    streamKeyPlaceholder: 'FB-xxxxxxxxxx-x',
    helpUrl: 'https://www.facebook.com/help/587160588142067'
  },
  {
    id: 'restream',
    name: 'Restream',
    icon: '🔄',
    rtmpBaseUrl: 'rtmp://live.restream.io/live/',
    streamKeyPlaceholder: 're_xxxxxx_xxxxxxxxxx',
    helpUrl: 'https://support.restream.io/en/'
  },
  {
    id: 'custom',
    name: 'Custom RTMP',
    icon: '⚙️',
    rtmpBaseUrl: '',
    streamKeyPlaceholder: 'your-stream-key',
  }
]

export const useStreamingStore = defineStore('streaming', () => {
  // State
  const destinations = ref<StreamingDestination[]>([])
  const isStreaming = ref(false)
  const activeDestinationId = ref<string | null>(null)
  const programOutputMode = ref<'alpha' | 'whipout'>('alpha')
  const streamStartTime = ref<number | null>(null)
  const streamStatus = ref<any | null>(null)
  const streamStats = ref<any | null>(null)
  
  // SRT Output configuration
  const srtOutput = ref<SrtOutput>({
    enabled: false,
    host: '',
    port: 8890,
    streamId: 'mixer_program'
  })

  // Computed
  const activeDestination = computed(() => 
    destinations.value.find(d => d.id === activeDestinationId.value)
  )

  const enabledDestinations = computed(() => 
    destinations.value.filter(d => d.enabled)
  )

  const platforms = computed(() => STREAMING_PLATFORMS)

  /**
   * Get the MediaMTX program output URLs
   * Uses same-domain architecture with app.itagenten.no
   */
  const programOutputUrls = computed(() => {
    const host = window.location.hostname
    const isLocal = host === 'localhost' || host === '127.0.0.1'
    
    // For remote access, use app.itagenten.no (same-domain architecture)
    // RTMP/RTSP/SRT still need to go directly to MediaMTX ports on R58
    const mediaHost = isLocal ? 'localhost' : 'app.itagenten.no'
    
    return {
      rtmp: isLocal ? 'rtmp://localhost:1935/mixer_program' : 'rtmp://app.itagenten.no:1935/mixer_program',
      rtsp: isLocal ? 'rtsp://localhost:8554/mixer_program' : 'rtsp://app.itagenten.no:8554/mixer_program',
      srt: isLocal ? 'srt://localhost:8890?streamid=read:mixer_program' : 'srt://app.itagenten.no:8890?streamid=read:mixer_program',
      hls: `https://${mediaHost}/hls/mixer_program/index.m3u8`,
      whep: `https://${mediaHost}/mixer_program/whep`
    }
  })

  // Actions
  function addDestination(platformId: string, name?: string): StreamingDestination {
    const platform = STREAMING_PLATFORMS.find(p => p.id === platformId)
    if (!platform) throw new Error(`Unknown platform: ${platformId}`)

    const destination: StreamingDestination = {
      id: `dest-${Date.now()}`,
      platformId,
      name: name || platform.name,
      streamKey: '',
      enabled: false
    }

    destinations.value.push(destination)
    return destination
  }

  function updateDestination(id: string, updates: Partial<StreamingDestination>) {
    const index = destinations.value.findIndex(d => d.id === id)
    if (index !== -1) {
      destinations.value[index] = { ...destinations.value[index], ...updates }
    }
  }

  function removeDestination(id: string) {
    const index = destinations.value.findIndex(d => d.id === id)
    if (index !== -1) {
      destinations.value.splice(index, 1)
    }
    if (activeDestinationId.value === id) {
      activeDestinationId.value = null
    }
  }

  function setActiveDestination(id: string | null) {
    activeDestinationId.value = id
  }

  function toggleSrtOutput(enabled: boolean) {
    srtOutput.value.enabled = enabled
  }

  function updateSrtConfig(config: Partial<SrtOutput>) {
    srtOutput.value = { ...srtOutput.value, ...config }
  }

  function startStreaming() {
    isStreaming.value = true
  }

  function stopStreaming() {
    isStreaming.value = false
  }

  /**
   * Build RTMP URL for a destination
   */
  function buildRtmpUrl(destination: StreamingDestination): string {
    const platform = STREAMING_PLATFORMS.find(p => p.id === destination.platformId)
    if (!platform) return ''

    if (destination.platformId === 'custom') {
      // For custom, the rtmpBaseUrl is stored in name field and key separately
      return `${destination.name}${destination.streamKey}`
    }

    return `${platform.rtmpBaseUrl}${destination.streamKey}`
  }

  /**
   * Get SRT output URL for external consumption
   * Note: SRT protocol requires direct connection to MediaMTX port
   */
  function getSrtOutputUrl(): string {
    const host = window.location.hostname
    const isLocal = host === 'localhost' || host === '127.0.0.1'
    // SRT needs direct port access to MediaMTX via FRP tunnel
    const srtHost = isLocal ? 'localhost' : 'app.itagenten.no'
    
    return `srt://${srtHost}:${srtOutput.value.port}?streamid=read:${srtOutput.value.streamId}`
  }

  // Load saved destinations from localStorage
  function loadSavedDestinations() {
    try {
      const saved = localStorage.getItem('r58-streaming-destinations')
      if (saved) {
        const parsed = JSON.parse(saved)
        destinations.value = parsed.destinations || []
        if (parsed.srtOutput) {
          srtOutput.value = { ...srtOutput.value, ...parsed.srtOutput }
        }
        if (parsed.programOutputMode) {
          programOutputMode.value = parsed.programOutputMode
        }
      }
    } catch (e) {
      console.warn('Failed to load saved streaming destinations:', e)
    }
  }

  // Save destinations to localStorage
  function saveDestinations() {
    try {
      localStorage.setItem('r58-streaming-destinations', JSON.stringify({
        destinations: destinations.value,
        srtOutput: srtOutput.value,
        programOutputMode: programOutputMode.value
      }))
    } catch (e) {
      console.warn('Failed to save streaming destinations:', e)
    }
  }

  /**
   * Start RTMP relay to enabled destinations via backend API
   * 
   * Uses MediaMTX's runOnReady hook to automatically spawn FFmpeg
   * when the mixer_program stream becomes ready. MediaMTX manages
   * the process lifecycle including automatic restart on failure.
   */
  async function startRtmpRelay(): Promise<{ success: boolean; message: string }> {
    try {
      const enabled = enabledDestinations.value
      if (enabled.length === 0) {
        console.warn('[Streaming] No enabled destinations to stream to')
        return { success: false, message: 'No destinations configured' }
      }

      const rtmpDestinations = enabled.map(dest => ({
        platform: dest.platformId,
        rtmp_url: STREAMING_PLATFORMS.find(p => p.id === dest.platformId)?.rtmpBaseUrl || '',
        stream_key: dest.streamKey,
        enabled: true
      }))

      const response = await fetch(await buildApiUrl('/api/streaming/rtmp/start'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ destinations: rtmpDestinations })
      })

      const data = await response.json()
      
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to start RTMP relay')
      }

      console.log('[Streaming] RTMP relay configured via MediaMTX runOnReady:', data)
      return { 
        success: true, 
        message: data.message || `Streaming to ${enabled.length} destination(s)` 
      }
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Failed to start RTMP relay'
      console.error('[Streaming] Failed to start RTMP relay:', e)
      return { success: false, message }
    }
  }

  /**
   * Stop RTMP relay via backend API
   * 
   * Removes the runOnReady hook from MediaMTX, which stops any
   * running FFmpeg processes.
   */
  async function stopRtmpRelay(): Promise<{ success: boolean; message: string }> {
    try {
      const response = await fetch(await buildApiUrl('/api/streaming/rtmp/stop'), {
        method: 'POST'
      })

      const data = await response.json()
      
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to stop RTMP relay')
      }

      console.log('[Streaming] RTMP relay stopped')
      return { success: true, message: 'RTMP relay stopped' }
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Failed to stop RTMP relay'
      console.error('[Streaming] Failed to stop RTMP relay:', e)
      return { success: false, message }
    }
  }

  /**
   * Get streaming status from backend
   * 
   * Returns:
   * - active: Whether mixer_program stream is active in MediaMTX
   * - rtmp_relay_configured: Whether runOnReady hook is set
   * - run_on_ready: The current FFmpeg command if configured
   */
  async function getStreamingStatus(): Promise<{
    active: boolean
    mixer_program_active: boolean
    rtmp_relay_configured: boolean
    run_on_ready: string | null
    error?: string
  } | null> {
    try {
      const response = await fetch(await buildApiUrl('/api/streaming/status'))
      if (!response.ok) {
        throw new Error('Failed to get streaming status')
      }
      return await response.json()
    } catch (e) {
      console.error('[Streaming] Failed to get streaming status:', e)
      return null
    }
  }

  async function getStreamingStats(): Promise<Record<string, any> | null> {
    try {
      const response = await fetch(await buildApiUrl('/api/streaming/stats'))
      if (!response.ok) {
        throw new Error('Failed to get streaming stats')
      }
      return await response.json()
    } catch (e) {
      console.error('[Streaming] Failed to get streaming stats:', e)
      return null
    }
  }

  function setProgramOutputMode(mode: 'alpha' | 'whipout') {
    programOutputMode.value = mode
    saveDestinations()
  }

  function markStreamActive(isActive: boolean) {
    if (isActive) {
      if (!streamStartTime.value) {
        streamStartTime.value = Date.now()
      }
    } else {
      streamStartTime.value = null
    }
  }

  // Initialize
  loadSavedDestinations()

  return {
    // State
    destinations,
    isStreaming,
    activeDestinationId,
    srtOutput,
    programOutputMode,
    streamStartTime,
    streamStatus,
    streamStats,

    // Computed
    activeDestination,
    enabledDestinations,
    platforms,
    programOutputUrls,

    // Actions
    addDestination,
    updateDestination,
    removeDestination,
    setActiveDestination,
    toggleSrtOutput,
    updateSrtConfig,
    startStreaming,
    stopStreaming,
    setProgramOutputMode,
    markStreamActive,
    buildRtmpUrl,
    getSrtOutputUrl,
    saveDestinations,
    loadSavedDestinations,
    
    // RTMP Relay API
    startRtmpRelay,
    stopRtmpRelay,
    getStreamingStatus,
    getStreamingStats
  }
})




