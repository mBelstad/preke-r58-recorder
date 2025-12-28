<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'

const props = defineProps<{
  inputId: string
  protocol?: 'whep' | 'hls'
}>()

const videoRef = ref<HTMLVideoElement | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

// Get preview URL from capabilities or construct default
function getPreviewUrl(): string {
  const protocol = props.protocol || 'whep'
  const host = window.location.hostname
  const port = 8889 // MediaMTX WHEP port
  
  return `http://${host}:${port}/${props.inputId}/whep`
}

async function initWhepPlayback() {
  if (!videoRef.value) return
  
  loading.value = true
  error.value = null
  
  try {
    const url = getPreviewUrl()
    
    // Create peer connection for WHEP
    const pc = new RTCPeerConnection({
      iceServers: [] // Local network, no STUN/TURN needed
    })
    
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
</script>

<template>
  <div class="relative w-full h-full bg-black">
    <video
      ref="videoRef"
      autoplay
      muted
      playsinline
      class="w-full h-full object-cover"
    ></video>
    
    <!-- Loading overlay -->
    <div 
      v-if="loading"
      class="absolute inset-0 flex items-center justify-center bg-black/50"
    >
      <div class="animate-spin w-6 h-6 border-2 border-white border-t-transparent rounded-full"></div>
    </div>
    
    <!-- Error overlay -->
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

