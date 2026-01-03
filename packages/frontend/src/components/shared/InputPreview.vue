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
import { 
  acquireConnection, 
  releaseConnection, 
  forceReconnect,
  type WHEPConnection 
} from '@/lib/whepConnectionManager'

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
const isReconnecting = ref(false)
const reconnectAttempts = ref(0)

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
    error.value = e instanceof Error ? e.message : 'Failed to connect'
    loading.value = false
  }
}

/**
 * Manual retry - triggers force reconnect in manager
 */
function manualRetry() {
  forceReconnect(props.inputId)
}

/**
 * Cleanup connection reference
 */
function cleanup() {
  if (currentOnChange) {
    releaseConnection(props.inputId, currentOnChange)
    currentOnChange = null
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
      v-if="loading && !isReconnecting"
      class="absolute inset-0 flex items-center justify-center bg-black/50"
    >
      <div class="animate-spin w-6 h-6 border-2 border-white border-t-transparent rounded-full"></div>
    </div>
    
    <!-- Reconnecting overlay -->
    <div 
      v-if="isReconnecting"
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
