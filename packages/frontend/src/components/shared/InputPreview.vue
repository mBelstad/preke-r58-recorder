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

// Get preview URL from API proxy (same origin, avoids mixed content issues)
function getPreviewUrl(): string {
  // Use API proxy endpoint for WHEP - served over same HTTPS origin
  const origin = window.location.origin
  return `${origin}/api/v1/whep/${props.inputId}/whep`
}

// Track peer connection for cleanup
let peerConnection: RTCPeerConnection | null = null

async function initWhepPlayback() {
  if (!videoRef.value) return
  
  // Clean up existing connection
  if (peerConnection) {
    peerConnection.close()
    peerConnection = null
  }
  
  loading.value = true
  error.value = null
  
  try {
    const url = getPreviewUrl()
    
    // Create peer connection for WHEP
    // Use Google STUN server for remote access NAT traversal
    const pc = new RTCPeerConnection({
      iceServers: [
        { urls: 'stun:stun.l.google.com:19302' },
        { urls: 'stun:stun1.l.google.com:19302' },
      ]
    })
    peerConnection = pc
    
    pc.ontrack = (event) => {
      if (videoRef.value && event.streams[0]) {
        videoRef.value.srcObject = event.streams[0]
        loading.value = false
      }
    }
    
    pc.oniceconnectionstatechange = () => {
      if (pc.iceConnectionState === 'failed' || pc.iceConnectionState === 'disconnected') {
        error.value = 'Connection lost'
      }
    }
    
    // Add transceiver for receiving video
    pc.addTransceiver('video', { direction: 'recvonly' })
    pc.addTransceiver('audio', { direction: 'recvonly' })
    
    // Create offer
    const offer = await pc.createOffer()
    await pc.setLocalDescription(offer)
    
    // Send offer to WHEP endpoint
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
    console.error('WHEP playback error:', e)
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

