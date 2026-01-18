<script setup lang="ts">
/**
 * InputPreview - Displays a WHEP video stream for a camera
 * 
 * Uses the shared WHEP connection manager to prevent duplicate
 * connections to the same camera. This ensures each camera has
 * at most ONE active WebRTC connection per browser context.
 */
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRecorderStore } from '@/stores/recorder'
import { getDeviceUrl } from '@/lib/api'
import { 
  acquireConnection, 
  releaseConnection, 
  forceReconnect,
  getHlsUrl,
  forceHlsFallback,
  type WHEPConnection,
  type ConnectionQuality
} from '@/lib/whepConnectionManager'
import Hls from 'hls.js'

const props = defineProps<{
  inputId: string
  protocol?: 'whep' | 'hls'
  isPreview?: boolean
}>()

const emit = defineEmits<{
  (e: 'videoReady'): void
  (e: 'aspectRatio', ratio: number): void
}>()

const recorderStore = useRecorderStore()
let videoReadyEmitted = false
const isRecording = computed(() => recorderStore.status === 'recording')

const videoRef = ref<HTMLVideoElement | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const connectionType = ref<'p2p' | 'relay' | 'unknown' | 'hls'>('unknown')
const isReconnecting = ref(false)
const reconnectAttempts = ref(0)
const connectionQuality = ref<ConnectionQuality | null>(null)
const hlsPlayer = ref<Hls | null>(null)
const usingHLS = ref(false)

// Track the onChange callback for cleanup
let currentOnChange: ((conn: WHEPConnection) => void) | null = null

/**
 * Handle connection state changes from the manager
 */
function handleConnectionChange(conn: WHEPConnection) {
  console.log(`[InputPreview ${props.inputId}] Connection update:`, {
    state: conn.state,
    type: conn.connectionType,
    hasStream: !!conn.mediaStream
  })
  
  connectionType.value = conn.connectionType
  reconnectAttempts.value = conn.reconnectAttempts
  connectionQuality.value = conn.quality
  usingHLS.value = conn.state === 'hls-fallback' || conn.shouldUseHLS
  
  // If connection suggests HLS fallback, switch to HLS
  if (conn.shouldUseHLS && conn.hlsUrl && !usingHLS.value) {
    console.log(`[InputPreview ${props.inputId}] Switching to HLS fallback`)
    switchToHLS(conn.hlsUrl)
  }
  
  switch (conn.state) {
    case 'connecting':
      loading.value = true
      error.value = null
      isReconnecting.value = conn.reconnectAttempts > 0
      break
      
    case 'connected':
      loading.value = false
      error.value = null
      isReconnecting.value = false
      
      // Attach stream to video element
      if (conn.mediaStream && videoRef.value) {
        if (videoRef.value.srcObject !== conn.mediaStream) {
          videoRef.value.srcObject = conn.mediaStream
          
          // Explicitly play the video (required in some Electron/browser contexts)
          videoRef.value.play().catch((e) => {
            console.warn(`[InputPreview ${props.inputId}] Autoplay prevented:`, e)
          })
          
          // Emit videoReady and aspectRatio when first frame is displayed
          if (!videoReadyEmitted) {
            videoRef.value.onloadeddata = () => {
              if (!videoReadyEmitted && videoRef.value) {
                videoReadyEmitted = true
                const w = videoRef.value.videoWidth
                const h = videoRef.value.videoHeight
                const ratio = w && h ? w / h : 16/9
                console.log(`[InputPreview ${props.inputId}] Video ready (${w}x${h}, ratio: ${ratio.toFixed(3)})`)
                emit('aspectRatio', ratio)
                emit('videoReady')
              }
            }
          }
        }
      }
      break
      
    case 'disconnected':
      isReconnecting.value = true
      error.value = `Reconnecting... (${conn.reconnectAttempts}/5)`
      break
      
    case 'failed':
      loading.value = false
      isReconnecting.value = false
      error.value = 'Connection failed after multiple attempts'
      break
  }
}

/**
 * Initialize connection via the manager
 */
async function initConnection() {
  if (!videoRef.value) return
  
  // In preview mode without device, show placeholder
  if (props.isPreview) {
    const deviceUrl = typeof window !== 'undefined' && (window as any).__R58_DEVICE_URL__
    if (!deviceUrl && !getDeviceUrl()) {
      loading.value = false
      error.value = null
      return
    }
  }
  
  // Release any existing connection first
  cleanup()
  
  loading.value = true
  error.value = null
  
  // Create the onChange callback
  currentOnChange = handleConnectionChange
  
  // Acquire shared connection
  try {
    await acquireConnection(props.inputId, currentOnChange)
  } catch (e) {
    console.error(`[InputPreview ${props.inputId}] Failed to acquire connection:`, e)
    // In preview mode, show friendly placeholder instead of error
    if (props.isPreview) {
      error.value = null
      loading.value = false
    } else {
      error.value = e instanceof Error ? e.message : 'Failed to connect'
      loading.value = false
    }
  }
}

/**
 * Switch to HLS playback (fallback for poor connections)
 */
async function switchToHLS(hlsUrl: string) {
  if (!videoRef.value) return
  
  // Cleanup existing HLS player
  if (hlsPlayer.value) {
    hlsPlayer.value.destroy()
    hlsPlayer.value = null
  }
  
  // Cleanup WebRTC connection
  releaseConnection(props.inputId, currentOnChange!)
  
  usingHLS.value = true
  loading.value = true
  error.value = null
  
  try {
    if (Hls.isSupported()) {
      const hls = new Hls({
        enableWorker: true,
        lowLatencyMode: true,
        backBufferLength: 90
      })
      
      hls.loadSource(hlsUrl)
      hls.attachMedia(videoRef.value)
      
      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        console.log(`[InputPreview ${props.inputId}] HLS manifest loaded`)
        videoRef.value?.play().catch(e => {
          console.warn(`[InputPreview ${props.inputId}] HLS autoplay prevented:`, e)
        })
      })
      
      hls.on(Hls.Events.ERROR, (event, data) => {
        if (data.fatal) {
          console.error(`[InputPreview ${props.inputId}] HLS fatal error:`, data)
          error.value = 'HLS playback failed'
          loading.value = false
        }
      })
      
      hlsPlayer.value = hls
      loading.value = false
    } else if (videoRef.value.canPlayType('application/vnd.apple.mpegurl')) {
      // Native HLS support (Safari)
      videoRef.value.src = hlsUrl
      videoRef.value.play().catch(e => {
        console.warn(`[InputPreview ${props.inputId}] HLS autoplay prevented:`, e)
      })
      loading.value = false
    } else {
      throw new Error('HLS not supported in this browser')
    }
  } catch (e) {
    console.error(`[InputPreview ${props.inputId}] Failed to switch to HLS:`, e)
    error.value = 'Failed to load HLS stream'
    loading.value = false
  }
}

/**
 * Manual retry - triggers force reconnect in manager
 */
function manualRetry() {
  if (usingHLS.value) {
    // Retry WHEP connection
    usingHLS.value = false
    if (hlsPlayer.value) {
      hlsPlayer.value.destroy()
      hlsPlayer.value = null
    }
    initConnection()
  } else {
    forceReconnect(props.inputId)
  }
}

/**
 * Force HLS fallback manually
 */
async function forceHLS() {
  const hlsUrl = await getHlsUrl(props.inputId)
  switchToHLS(hlsUrl)
  forceHlsFallback(props.inputId)
}

/**
 * Cleanup connection reference
 */
function cleanup() {
  if (currentOnChange && !usingHLS.value) {
    releaseConnection(props.inputId, currentOnChange)
    currentOnChange = null
  }
  
  // Cleanup HLS player
  if (hlsPlayer.value) {
    hlsPlayer.value.destroy()
    hlsPlayer.value = null
  }
}

onMounted(() => {
  initConnection()
})

// Re-initialize when input changes
watch(() => props.inputId, () => {
  initConnection()
})

// Handle recording state changes
watch(isRecording, (recording, wasRecording) => {
  if (wasRecording && !recording && error.value) {
    console.log('[InputPreview] Recording stopped, reconnecting preview...')
    forceReconnect(props.inputId)
  } else if (!wasRecording && recording) {
    console.log('[InputPreview] Recording started, will try to reconnect preview after delay...')
    setTimeout(() => {
      if (isRecording.value) {
        console.log('[InputPreview] Attempting to reconnect preview during recording...')
        forceReconnect(props.inputId)
      }
    }, 2000)
  }
})

// Cleanup on unmount
onUnmounted(() => {
  cleanup()
})
</script>

<template>
  <div class="relative w-full h-full bg-black">
    <video
      ref="videoRef"
      autoplay
      muted
      playsinline
      class="w-full h-full object-contain"
    ></video>
    
    <!-- Connection type indicator (P2P vs Relay vs HLS) -->
    <div 
      v-if="!loading && !error && connectionType !== 'unknown'"
      class="absolute top-1 right-1 flex gap-1"
    >
      <div 
        class="px-1.5 py-0.5 text-[10px] font-medium rounded"
        :class="connectionType === 'p2p' 
          ? 'bg-emerald-500/80 text-white' 
          : connectionType === 'hls'
          ? 'bg-purple-500/80 text-white'
          : 'bg-amber-500/80 text-white'"
        :title="connectionType === 'p2p' ? 'Direct P2P connection' : connectionType === 'hls' ? 'HLS fallback (stable but higher latency)' : 'Relay connection (FRP)'"
      >
        {{ connectionType === 'p2p' ? 'P2P' : connectionType === 'hls' ? 'HLS' : 'RELAY' }}
      </div>
      <!-- Connection quality indicator -->
      <div 
        v-if="connectionQuality && connectionType !== 'hls'"
        class="px-1.5 py-0.5 text-[10px] font-medium rounded"
        :class="{
          'bg-emerald-500/80 text-white': connectionQuality.quality === 'excellent' || connectionQuality.quality === 'good',
          'bg-yellow-500/80 text-white': connectionQuality.quality === 'fair',
          'bg-red-500/80 text-white': connectionQuality.quality === 'poor' || connectionQuality.quality === 'very-poor'
        }"
        :title="`RTT: ${connectionQuality.rtt}ms, Loss: ${connectionQuality.packetLoss}%, Jitter: ${connectionQuality.jitter}ms`"
      >
        {{ connectionQuality.rtt }}ms
      </div>
    </div>
    
    <!-- Loading overlay -->
    <div 
      v-if="loading && !isReconnecting"
      class="absolute inset-0 flex items-center justify-center bg-black/50"
    >
      <div class="animate-spin w-6 h-6 border-2 border-white border-t-transparent rounded-full"></div>
    </div>
    
    <!-- Reconnecting overlay (click to force reconnect) -->
    <div 
      v-if="isReconnecting"
      class="absolute inset-0 flex items-center justify-center bg-black/70 cursor-pointer"
      @click="manualRetry"
      title="Click to force reconnect"
    >
      <div class="text-center">
        <div class="animate-spin w-5 h-5 border-2 border-amber-400 border-t-transparent rounded-full mx-auto mb-2"></div>
        <p class="text-xs text-amber-400">{{ error || 'Reconnecting...' }}</p>
        <p class="text-xs text-amber-400/60 mt-1">Tap to retry</p>
      </div>
    </div>
    
    <!-- Preview mode placeholder (no device) -->
    <div 
      v-if="isPreview && !loading && !error && !getDeviceUrl()"
      class="absolute inset-0 flex items-center justify-center bg-black/60"
    >
      <div class="text-center text-preke-text-dim">
        <svg class="w-16 h-16 mx-auto mb-3 text-preke-text-subtle" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
        </svg>
        <p class="text-sm">Camera preview</p>
        <p class="text-xs mt-1">Connect device to view</p>
      </div>
    </div>
    
    <!-- Error overlay with retry button -->
    <div 
      v-else-if="error && !loading"
      class="absolute inset-0 flex items-center justify-center bg-black/80"
    >
      <div class="text-center text-preke-text-dim">
        <p class="text-sm">{{ error }}</p>
        <div class="flex gap-2 mt-2 justify-center">
          <button 
            @click="manualRetry"
            class="px-3 py-1 text-xs text-preke-gold hover:underline border border-preke-gold/30 rounded"
          >
            Retry WHEP
          </button>
          <button 
            v-if="!usingHLS"
            @click="forceHLS"
            class="px-3 py-1 text-xs text-purple-400 hover:underline border border-purple-400/30 rounded"
          >
            Use HLS
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
