<script setup lang="ts">
/**
 * MixerView - VDO.ninja mixer with HDMI cameras as guests
 * 
 * Uses VDO.ninja's mixer.html which provides:
 * - Director controls for managing sources
 * - Scene buttons for switching layouts
 * - Guest management (cameras join via &whepshare bridge)
 * 
 * IMPORTANT: Cameras are pushed to the VDO.ninja room by the
 * vdoninja-bridge service running on the R58. The bridge uses
 * &whepshare to redirect video playback to MediaMTX WHEP URLs.
 */
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useRecorderStore } from '@/stores/recorder'
import { useCapabilitiesStore } from '@/stores/capabilities'
import { getVdoHost, getVdoProtocol, VDO_ROOM, VDO_DIRECTOR_PASSWORD, buildMixerUrl, getMediaMtxHost } from '@/lib/vdoninja'
import { buildApiUrl, hasDeviceConfigured } from '@/lib/api'
import { toast } from '@/composables/useToast'
import { platform } from '@/lib/platform'

// Components
import ModeLoadingScreen from '@/components/shared/ModeLoadingScreen.vue'
import StreamingControlPanel from '@/components/mixer/StreamingControlPanel.vue'
import MixerControlPanel from '@/components/mixer/MixerControlPanel.vue'
import CameraPushBar from '@/components/mixer/CameraPushBar.vue'

const router = useRouter()
const recorderStore = useRecorderStore()
const capabilitiesStore = useCapabilitiesStore()

// Handle loading screen cancel - navigate back to studio
function handleLoadingCancel() {
  router.push('/')
}

// State
const isLoading = ref(true)
const iframeLoaded = ref(false)
const bridgeReady = ref(false)
const loadingStatus = ref('Starting mixer...')
const iframeRef = ref<HTMLIFrameElement | null>(null)
const showControls = ref(true)
const isElectronApp = computed(() => platform.isElectron())
const useLocalBridge = ref(true)
const showCameraPushBar = computed(() => isElectronApp.value && useLocalBridge.value)

function loadLocalBridgePreference() {
  if (typeof window === 'undefined') return
  const stored = window.localStorage.getItem('preke_mixer_use_local_bridge')
  if (stored !== null) {
    useLocalBridge.value = stored === 'true'
  } else {
    // Default to true (use local bridge) for Electron
    useLocalBridge.value = true
  }
  console.log('[Mixer] Local bridge preference:', useLocalBridge.value)
}

async function toggleLocalBridge() {
  useLocalBridge.value = !useLocalBridge.value
  if (typeof window !== 'undefined') {
    window.localStorage.setItem('preke_mixer_use_local_bridge', String(useLocalBridge.value))
  }
  iframeLoaded.value = false
  await initializeMixerUrl()
}

// Active cameras with signal
const activeCameras = computed(() => 
  recorderStore.inputs.filter(i => i.hasSignal)
)

// Build the VDO.ninja mixer URL
// Uses mixer.html which provides full mixer interface with:
// - Sidebar for stream IDs and slots
// - Top menu for layout buttons
// - Chat module
// - Director iframe with video cards
const mixerUrl = ref<string>('')

// Initialize mixer URL on mount (getVdoHost is async)
async function initializeMixerUrl() {
  const useMediamtx = !(isElectronApp.value && useLocalBridge.value)
  const mediamtxHost = useMediamtx ? await getMediaMtxHost() : null
  const url = await buildMixerUrl({
    mediamtxHost: mediamtxHost || undefined,
    room: VDO_ROOM,
    useMediamtx,
  })
  
  if (url) {
    mixerUrl.value = url
    console.log('[Mixer] Mixer URL initialized with API key')
  } else {
    // Fallback if buildMixerUrl fails
    const VDO_HOST = await getVdoHost() || 'app.itagenten.no'
    const VDO_PROTOCOL = getVdoProtocol()
    const fallbackUrl = new URL(`${VDO_PROTOCOL}://${VDO_HOST}/mixer.html`)
    fallbackUrl.searchParams.set('room', VDO_ROOM)
    fallbackUrl.searchParams.set('password', VDO_DIRECTOR_PASSWORD)
    fallbackUrl.searchParams.set('css', `${VDO_PROTOCOL}://${VDO_HOST}/css/preke-colors.css`)
    mixerUrl.value = fallbackUrl.toString()
    console.warn('[Mixer] Using fallback URL without API key')
  }
}

function handleIframeLoad() {
  console.log('[Mixer] VDO.ninja mixer iframe loaded')
  iframeLoaded.value = true
  loadingStatus.value = 'Waiting for cameras...'
}

function handleLoadingReady() {
  isLoading.value = false
  }
  
// Check if bridge has started by checking mode manager status
async function waitForBridge(): Promise<void> {
  const startTime = performance.now()
  loadingStatus.value = 'Starting camera bridge...'
  
  // Poll for bridge to be ready (max 20 seconds)
  for (let i = 0; i < 40; i++) {
    try {
      const response = await fetch(await buildApiUrl('/api/mode/status'))
      const data = await response.json()
      
      // Check if bridge service is running via ingest services
      if (data.current_mode === 'mixer') {
        const elapsed = Math.round((performance.now() - startTime) / 1000)
        if (elapsed >= 5) {
          // Bridge needs ~15s to start, but after 5s in mixer mode, it's likely running
          console.log(`[Mixer] Bridge likely ready after ${elapsed}s`)
          bridgeReady.value = true
          loadingStatus.value = 'Cameras connecting...'
          return
        }
      }
    } catch (e) {
      // Ignore errors during polling
    }
    await new Promise(r => setTimeout(r, 500))
    loadingStatus.value = `Starting camera bridge... (${Math.round((performance.now() - startTime) / 1000)}s)`
  }
  
  console.log('[Mixer] Bridge wait timeout - continuing anyway')
  bridgeReady.value = true
}

// Auto-switch to mixer mode if not already in it
async function ensureMixerMode() {
  if (!hasDeviceConfigured()) return
  
  loadingStatus.value = 'Checking mode...'
  
  // Fetch current capabilities to get mode
  await capabilitiesStore.fetchCapabilities()
  
  const currentMode = capabilitiesStore.capabilities?.current_mode
  if (currentMode && currentMode !== 'mixer') {
    console.log('[Mixer] Not in mixer mode, switching...')
    loadingStatus.value = 'Switching to mixer mode...'
    try {
      const response = await fetch(await buildApiUrl('/api/mode/mixer'), { method: 'POST' })
      if (response.ok) {
        await capabilitiesStore.fetchCapabilities()
        toast.success('Switched to Mixer mode')
      }
    } catch (e) {
      console.warn('[Mixer] Failed to switch mode:', e)
    }
  }
}

// Fetch inputs on mount - parallelized for speed
onMounted(async () => {
  const startTime = performance.now()
  
  if (isElectronApp.value) {
    loadLocalBridgePreference()
    console.log('[Mixer] Electron app detected, useLocalBridge:', useLocalBridge.value, 'showCameraPushBar:', showCameraPushBar.value)
  }

  // Initialize mixer URL first
  await initializeMixerUrl()
  
  // Phase 1: Mode switch and data fetch in parallel
  await Promise.all([
    ensureMixerMode(),
    recorderStore.fetchInputs()
  ])
  
  // Phase 2: Wait for bridge to start (gives cameras time to join)
  await waitForBridge()
  
  console.log(`[Mixer] Total load time: ${Math.round(performance.now() - startTime)}ms`)
})
</script>

<template>
  <!-- Loading Screen -->
  <Transition name="fade">
    <ModeLoadingScreen
      v-if="isLoading"
      mode="mixer"
      :content-ready="iframeLoaded && bridgeReady"
      :min-time="2000"
      :max-time="20000"
      :show-cancel="true"
      @ready="handleLoadingReady"
      @cancel="handleLoadingCancel"
    />
  </Transition>
  
  <!-- Content fades in when loading complete -->
  <Transition name="content-fade">
    <div v-show="!isLoading" class="h-full flex flex-col bg-preke-bg">
    <!-- Streaming Control Panel (with room info integrated) -->
    <StreamingControlPanel :room-name="VDO_ROOM" :camera-count="activeCameras.length" />
    <div v-if="isElectronApp" class="px-4 py-2 bg-preke-bg-elevated border-b border-preke-bg-surface flex items-center justify-between text-xs text-preke-text-dim">
      <span>Camera sources: {{ useLocalBridge ? 'Local bridge' : 'External bridge' }}</span>
      <button
        class="text-preke-gold hover:underline"
        @click="toggleLocalBridge"
        :title="useLocalBridge ? 'Disable local bridge to use external fallback' : 'Enable local bridge for Electron'"
      >
        {{ useLocalBridge ? 'Use fallback' : 'Use local bridge' }}
      </button>
    </div>
    
    <!-- VDO.ninja Mixer (full height) -->
    <div class="flex-1 relative">
      <iframe
        ref="iframeRef"
        :src="mixerUrl"
        @load="handleIframeLoad"
        class="absolute inset-0 w-full h-full border-0"
        allow="camera; microphone; autoplay; display-capture"
        allowfullscreen
      ></iframe>
      
      <!-- Loading overlay -->
      <div 
        v-if="!iframeLoaded"
        class="absolute inset-0 flex items-center justify-center bg-preke-bg"
      >
        <div class="flex flex-col items-center gap-4">
          <div class="w-8 h-8 border-2 border-preke-gold border-t-transparent rounded-full animate-spin"></div>
          <span class="text-preke-text-muted">Loading VDO.ninja mixer...</span>
          <span class="text-xs text-preke-text-subtle">Cameras will appear when bridge is running</span>
        </div>
      </div>
      
      <!-- Control Panel Toggle Button -->
      <button
        v-if="iframeLoaded"
        @click="showControls = !showControls"
        class="absolute top-4 left-4 z-40 p-2 bg-preke-bg-surface border border-preke-border rounded-lg shadow-lg hover:bg-preke-bg-elevated transition-colors"
        :title="showControls ? 'Hide Controls' : 'Show Controls'"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
        </svg>
      </button>
      
      <!-- Mixer Control Panel -->
      <MixerControlPanel
        v-if="showControls && iframeLoaded"
        :iframe-ref="iframeRef"
        :key="iframeLoaded ? 'ready' : 'loading'"
      />
    </div>
    <!-- Electron-only: push cameras to room via WHEP -->
    <CameraPushBar v-if="showCameraPushBar" />
    </div>
  </Transition>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* Content fade in animation */
.content-fade-enter-active {
  transition: opacity 0.4s ease-out, transform 0.4s ease-out;
}

.content-fade-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.content-fade-enter-to {
  opacity: 1;
  transform: translateY(0);
}
</style>
