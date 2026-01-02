import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

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
   */
  const programOutputUrls = computed(() => {
    const host = window.location.hostname
    const isLocal = host === 'localhost' || host === '127.0.0.1'
    const apiHost = isLocal ? 'localhost' : host.replace('r58-api', 'r58-mediamtx')
    
    return {
      rtmp: `rtmp://${apiHost}:1935/mixer_program`,
      rtsp: `rtsp://${apiHost}:8554/mixer_program`,
      srt: `srt://${apiHost}:8890?streamid=read:mixer_program`,
      hls: `https://${host}/hls/mixer_program/index.m3u8`,
      whep: `${window.location.origin}/api/v1/whep/mixer_program/whep`
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
   */
  function getSrtOutputUrl(): string {
    const host = window.location.hostname
    const isLocal = host === 'localhost' || host === '127.0.0.1'
    const srtHost = isLocal ? 'localhost' : host.replace('r58-api', 'r58-mediamtx')
    
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
        srtOutput: srtOutput.value
      }))
    } catch (e) {
      console.warn('Failed to save streaming destinations:', e)
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
    buildRtmpUrl,
    getSrtOutputUrl,
    saveDestinations,
    loadSavedDestinations
  }
})




