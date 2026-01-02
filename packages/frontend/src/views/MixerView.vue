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
import { useRecorderStore } from '@/stores/recorder'
import { getVdoHost, getVdoProtocol, VDO_ROOM, VDO_DIRECTOR_PASSWORD } from '@/lib/vdoninja'

// Components
import ModeLoadingScreen from '@/components/shared/ModeLoadingScreen.vue'

const recorderStore = useRecorderStore()

// State
const isLoading = ref(true)
const iframeLoaded = ref(false)

// Active cameras with signal
const activeCameras = computed(() => 
  recorderStore.inputs.filter(i => i.hasSignal)
)

// Build the VDO.ninja mixer URL
// The mixer.html is the director interface with scene controls
const mixerUrl = computed(() => {
  const VDO_HOST = getVdoHost()
  const VDO_PROTOCOL = getVdoProtocol()
  
  const url = new URL(`${VDO_PROTOCOL}://${VDO_HOST}/mixer.html`)
  url.searchParams.set('room', VDO_ROOM)
  url.searchParams.set('password', VDO_DIRECTOR_PASSWORD)
  
  return url.toString()
})

function handleIframeLoad() {
  console.log('[Mixer] VDO.ninja mixer iframe loaded')
  iframeLoaded.value = true
}

function handleLoadingReady() {
  isLoading.value = false
}

// Fetch inputs on mount
onMounted(async () => {
  await recorderStore.fetchInputs()
})
</script>

<template>
  <!-- Loading Screen -->
  <Transition name="fade">
    <ModeLoadingScreen
      v-if="isLoading"
      mode="mixer"
      :content-ready="iframeLoaded"
      :min-time="1500"
      :max-time="10000"
      @ready="handleLoadingReady"
    />
  </Transition>
  
  <div class="h-full flex flex-col bg-r58-bg-primary">
    <!-- Minimal Header -->
    <header class="flex items-center justify-between px-4 py-2 border-b border-r58-bg-tertiary bg-r58-bg-secondary">
      <div class="flex items-center gap-3">
        <span class="text-lg font-semibold text-r58-mixer">Mixer</span>
        <span class="text-sm text-r58-text-secondary">
          {{ activeCameras.length }} camera{{ activeCameras.length !== 1 ? 's' : '' }} detected
        </span>
      </div>
      
      <div class="flex items-center gap-2 text-xs text-r58-text-secondary">
        <span class="px-2 py-1 bg-r58-bg-tertiary rounded">Room: {{ VDO_ROOM }}</span>
      </div>
    </header>
    
    <!-- VDO.ninja Mixer (full height) -->
    <div class="flex-1 relative">
      <iframe
        :src="mixerUrl"
        @load="handleIframeLoad"
        class="absolute inset-0 w-full h-full border-0"
        allow="camera; microphone; autoplay; display-capture"
        allowfullscreen
      ></iframe>
      
      <!-- Loading overlay -->
      <div 
        v-if="!iframeLoaded"
        class="absolute inset-0 flex items-center justify-center bg-r58-bg-primary"
      >
        <div class="flex flex-col items-center gap-4">
          <div class="w-8 h-8 border-2 border-r58-accent-primary border-t-transparent rounded-full animate-spin"></div>
          <span class="text-r58-text-secondary">Loading VDO.ninja mixer...</span>
          <span class="text-xs text-r58-text-secondary/60">Cameras will appear when bridge is running</span>
        </div>
      </div>
    </div>
  </div>
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
</style>
