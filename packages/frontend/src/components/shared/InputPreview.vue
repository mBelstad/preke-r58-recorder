<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRecorderStore } from '@/stores/recorder'

const props = defineProps<{
  inputId: string
  protocol?: 'whep' | 'hls'
}>()

const recorderStore = useRecorderStore()
const isRecording = computed(() => recorderStore.status === 'recording')

const videoRef = ref<HTMLVideoElement | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const connectionType = ref<'p2p' | 'relay' | 'unknown'>('unknown')
const reconnectAttempts = ref(0)
const isReconnecting = ref(false)

// Auto-reconnect configuration
const MAX_RECONNECT_ATTEMPTS = 5
const INITIAL_RECONNECT_DELAY = 1000 // 1 second
const MAX_RECONNECT_DELAY = 30000 // 30 seconds

// Track reconnect timeout for cleanup
let reconnectTimeout: ReturnType<typeof setTimeout> | null = null

/**
 * Get preview URL - Always use FRP for WHEP signaling
 * 
 * Strategy: "FRP Signaling + ICE P2P"
 * - WHEP signaling always goes through FRP (reliable HTTPS)
 * - WebRTC ICE negotiation finds the best path (P2P when available)
 * - MediaMTX on R58 includes Tailscale/LAN IPs in ICE candidates
 * - Browser automatically picks fastest path
 * 
 * This approach works for both Electron and web, with automatic P2P
 * when the client can reach the device directly.
 */
function getPreviewUrl(): string {
  // Always use FRP-proxied MediaMTX for WHEP signaling
  // WebRTC ICE will find P2P path if device IPs are reachable
  return `https://r58-mediamtx.itagenten.no/${props.inputId}/whep`
}

// Track peer connection for cleanup
let peerConnection: RTCPeerConnection | null = null

/**
 * Schedule a reconnection attempt with exponential backoff
 */
function scheduleReconnect(reason: string) {
  if (isReconnecting.value) return
  
  if (reconnectAttempts.value >= MAX_RECONNECT_ATTEMPTS) {
    console.error(`[WHEP ${props.inputId}] Max reconnect attempts (${MAX_RECONNECT_ATTEMPTS}) reached`)
    error.value = 'Connection failed after multiple attempts'
    loading.value = false
    return
  }
  
  isReconnecting.value = true
  reconnectAttempts.value++
  
  // Exponential backoff: 1s, 2s, 4s, 8s, 16s (capped at 30s)
  const delay = Math.min(
    INITIAL_RECONNECT_DELAY * Math.pow(2, reconnectAttempts.value - 1),
    MAX_RECONNECT_DELAY
  )
  
  console.log(`[WHEP ${props.inputId}] Scheduling reconnect #${reconnectAttempts.value} in ${delay}ms (reason: ${reason})`)
  error.value = `Reconnecting... (${reconnectAttempts.value}/${MAX_RECONNECT_ATTEMPTS})`
  
  // Clear any existing reconnect timeout
  if (reconnectTimeout) {
    clearTimeout(reconnectTimeout)
  }
  
  reconnectTimeout = setTimeout(() => {
    isReconnecting.value = false
    initWhepPlayback()
  }, delay)
}

/**
 * Cancel any pending reconnect
 */
function cancelReconnect() {
  if (reconnectTimeout) {
    clearTimeout(reconnectTimeout)
    reconnectTimeout = null
  }
  isReconnecting.value = false
}

/**
 * Reset reconnect state (call after successful manual retry)
 */
function resetReconnectState() {
  reconnectAttempts.value = 0
  isReconnecting.value = false
  cancelReconnect()
}

/**
 * Detect if the connection is P2P or using a relay (TURN)
 */
async function detectConnectionType(pc: RTCPeerConnection): Promise<'p2p' | 'relay' | 'unknown'> {
  try {
    const stats = await pc.getStats()
    for (const report of stats.values()) {
      if (report.type === 'candidate-pair' && report.state === 'succeeded') {
        // Check if using relay
        const localCandidate = stats.get(report.localCandidateId)
        const remoteCandidate = stats.get(report.remoteCandidateId)
        
        if (localCandidate?.candidateType === 'relay' || remoteCandidate?.candidateType === 'relay') {
          return 'relay'
        }
        
        // Log the selected path for debugging
        console.log(`[WHEP ${props.inputId}] Connected via:`, {
          local: localCandidate?.candidateType,
          remote: remoteCandidate?.candidateType,
          localIP: localCandidate?.address,
          remoteIP: remoteCandidate?.address,
        })
        
        return 'p2p'
      }
    }
  } catch (e) {
    console.warn('[WHEP] Failed to detect connection type:', e)
  }
  return 'unknown'
}

async function initWhepPlayback() {
  if (!videoRef.value) return
  
  // Clean up existing connection
  if (peerConnection) {
    peerConnection.close()
    peerConnection = null
  }
  
  loading.value = true
  error.value = null
  connectionType.value = 'unknown'
  
  try {
    const url = getPreviewUrl()
    console.log(`[WHEP ${props.inputId}] Connecting via FRP signaling: ${url}`)
    
    // Create peer connection for WHEP
    // STUN servers help with NAT traversal for P2P discovery
    // Multiple servers increase chances of successful hole-punching
    const pc = new RTCPeerConnection({
      iceServers: [
        { urls: 'stun:stun.l.google.com:19302' },
        { urls: 'stun:stun1.l.google.com:19302' },
        { urls: 'stun:stun2.l.google.com:19302' },
        { urls: 'stun:stun3.l.google.com:19302' },
        { urls: 'stun:stun.cloudflare.com:3478' },
      ]
    })
    peerConnection = pc
    
    pc.ontrack = (event) => {
      if (videoRef.value && event.streams[0]) {
        videoRef.value.srcObject = event.streams[0]
        loading.value = false
      }
    }
    
    pc.oniceconnectionstatechange = async () => {
      const state = pc.iceConnectionState
      console.log(`[WHEP ${props.inputId}] ICE state: ${state}`)
      
      if (state === 'connected' || state === 'completed') {
        // Connection successful - reset reconnect attempts
        reconnectAttempts.value = 0
        isReconnecting.value = false
        
        // Detect and log connection type (P2P vs relay)
        connectionType.value = await detectConnectionType(pc)
        console.log(`[WHEP ${props.inputId}] Connection type: ${connectionType.value}`)
      } else if (state === 'failed') {
        // ICE failed - attempt to reconnect
        console.warn(`[WHEP ${props.inputId}] ICE failed, will attempt reconnect`)
        connectionType.value = 'unknown'
        scheduleReconnect('ICE negotiation failed')
      } else if (state === 'disconnected') {
        // Disconnected - wait a moment then check if it recovers
        console.warn(`[WHEP ${props.inputId}] ICE disconnected, waiting for recovery...`)
        
        // Give ICE 3 seconds to recover before reconnecting
        setTimeout(() => {
          if (pc.iceConnectionState === 'disconnected' || pc.iceConnectionState === 'failed') {
            console.warn(`[WHEP ${props.inputId}] ICE did not recover, reconnecting...`)
            scheduleReconnect('Connection lost')
          }
        }, 3000)
      }
    }
    
    // Add transceiver for receiving video
    pc.addTransceiver('video', { direction: 'recvonly' })
    pc.addTransceiver('audio', { direction: 'recvonly' })
    
    // Create offer
    const offer = await pc.createOffer()
    await pc.setLocalDescription(offer)
    
    // Send offer to WHEP endpoint (via FRP)
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/sdp'
      },
      body: offer.sdp
    })
    
    if (!response.ok) {
      throw new Error(`WHEP request failed: ${response.status}`)
    }
    
    const answerSdp = await response.text()
    await pc.setRemoteDescription({
      type: 'answer',
      sdp: answerSdp
    })
    
  } catch (e) {
    console.error(`[WHEP ${props.inputId}] Playback error:`, e)
    const errorMessage = e instanceof Error ? e.message : 'Failed to connect'
    
    // Schedule reconnect for network errors
    if (errorMessage.includes('fetch') || errorMessage.includes('network') || errorMessage.includes('WHEP')) {
      scheduleReconnect(errorMessage)
    } else {
      error.value = errorMessage
      loading.value = false
    }
  }
}

/**
 * Manual retry - resets reconnect counter
 */
function manualRetry() {
  resetReconnectState()
  initWhepPlayback()
}

onMounted(() => {
  initWhepPlayback()
})

// Re-initialize when input changes
watch(() => props.inputId, () => {
  initWhepPlayback()
})

// Auto-reconnect when recording state changes
watch(isRecording, (recording, wasRecording) => {
  if (wasRecording && !recording && error.value) {
    // Recording just stopped and we had an error - try to reconnect
    console.log('[InputPreview] Recording stopped, reconnecting preview...')
    initWhepPlayback()
  } else if (!wasRecording && recording) {
    // Recording just started - the preview pipeline was stopped, but the recording
    // pipeline uses a tee to stream to MediaMTX. Wait a bit then try to reconnect.
    console.log('[InputPreview] Recording started, will try to reconnect preview after delay...')
    setTimeout(() => {
      if (isRecording.value) {
        console.log('[InputPreview] Attempting to reconnect preview during recording...')
        initWhepPlayback()
      }
    }, 2000) // 2 second delay for pipeline to initialize
  }
})

// Cleanup on unmount
onUnmounted(() => {
  cancelReconnect()
  if (peerConnection) {
    peerConnection.close()
    peerConnection = null
  }
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
    
    <!-- Connection type indicator (P2P vs Relay) -->
    <div 
      v-if="!loading && !error && connectionType !== 'unknown'"
      class="absolute top-1 right-1 px-1.5 py-0.5 text-[10px] font-medium rounded"
      :class="connectionType === 'p2p' 
        ? 'bg-emerald-500/80 text-white' 
        : 'bg-amber-500/80 text-white'"
      :title="connectionType === 'p2p' ? 'Direct P2P connection' : 'Relay connection (FRP)'"
    >
      {{ connectionType === 'p2p' ? 'P2P' : 'RELAY' }}
    </div>
    
    <!-- Loading overlay -->
    <div 
      v-if="loading"
      class="absolute inset-0 flex items-center justify-center bg-black/50"
    >
      <div class="animate-spin w-6 h-6 border-2 border-white border-t-transparent rounded-full"></div>
    </div>
    
    <!-- Reconnecting overlay -->
    <div 
      v-if="isReconnecting && !loading"
      class="absolute inset-0 flex items-center justify-center bg-black/70"
    >
      <div class="text-center">
        <div class="animate-spin w-5 h-5 border-2 border-amber-400 border-t-transparent rounded-full mx-auto mb-2"></div>
        <p class="text-xs text-amber-400">{{ error || 'Reconnecting...' }}</p>
      </div>
    </div>
    
    <!-- Error overlay with retry button -->
    <div 
      v-else-if="error && !loading"
      class="absolute inset-0 flex items-center justify-center bg-black/80"
    >
      <div class="text-center text-r58-text-secondary">
        <p class="text-sm">{{ error }}</p>
        <button 
          @click="manualRetry"
          class="mt-2 text-xs text-r58-accent-primary hover:underline"
        >
          Retry
        </button>
      </div>
    </div>
  </div>
</template>

