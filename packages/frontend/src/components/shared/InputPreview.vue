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
        // Detect and log connection type (P2P vs relay)
        connectionType.value = await detectConnectionType(pc)
        console.log(`[WHEP ${props.inputId}] Connection type: ${connectionType.value}`)
      } else if (state === 'failed' || state === 'disconnected') {
        error.value = 'Connection lost'
        connectionType.value = 'unknown'
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
    error.value = e instanceof Error ? e.message : 'Failed to connect'
    loading.value = false
  }
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
    
    <!-- Error overlay with retry button -->
    <div 
      v-if="error"
      class="absolute inset-0 flex items-center justify-center bg-black/80"
    >
      <div class="text-center text-r58-text-secondary">
        <p class="text-sm">{{ error }}</p>
        <button 
          @click="initWhepPlayback"
          class="mt-2 text-xs text-r58-accent-primary hover:underline"
        >
          Retry
        </button>
      </div>
    </div>
  </div>
</template>

