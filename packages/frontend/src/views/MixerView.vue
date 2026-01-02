<script setup lang="ts">
/**
 * MixerView - VDO.ninja native mixer with R58 theme
 * 
 * Simplified approach: Embed the native VDO.ninja mixer.html which is
 * proven to work, and apply custom CSS to match R58 design.
 * 
 * Camera sources are pushed via CameraPushBar using &whepplay= parameter.
 */
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRecorderStore } from '@/stores/recorder'
import { getVdoCssUrl, VDO_ROOM, VDO_DIRECTOR_PASSWORD } from '@/lib/vdoninja'

// Components
import CameraPushBar from '@/components/mixer/CameraPushBar.vue'
import ModeLoadingScreen from '@/components/shared/ModeLoadingScreen.vue'

const recorderStore = useRecorderStore()

// State
const isLoading = ref(true)
const iframeLoaded = ref(false)
const iframeRef = ref<HTMLIFrameElement | null>(null)

// Build the native director URL (not mixer.html) 
// Director view works better with our camera push approach
const mixerUrl = computed(() => {
  const VDO_HOST = 'r58-vdo.itagenten.no'
  const url = new URL(`https://${VDO_HOST}/`)
  
  // Director mode with room
  url.searchParams.set('director', VDO_ROOM)
  url.searchParams.set('password', VDO_DIRECTOR_PASSWORD)
  
  // Dark mode for better integration
  url.searchParams.set('darkmode', '')
  
  // Hide branding and clean up UI
  url.searchParams.set('nologo', '')
  url.searchParams.set('hideheader', '')
  
  // Enable API for future integration
  url.searchParams.set('api', '')
  
  // Custom CSS for R58 theme
  const cssUrl = getVdoCssUrl()
  if (cssUrl) {
    url.searchParams.set('css', cssUrl)
  }
  
  return url.toString()
})

// Connected cameras count
const connectedCameras = computed(() => 
  recorderStore.inputs.filter(i => i.hasSignal).length
)

function handleIframeLoad() {
  console.log('[Mixer] Native mixer iframe loaded')
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
          {{ connectedCameras }} camera{{ connectedCameras !== 1 ? 's' : '' }} connected
        </span>
      </div>
      
      <div class="flex items-center gap-2 text-xs text-r58-text-secondary">
        <span class="px-2 py-1 bg-r58-bg-tertiary rounded">Room: {{ VDO_ROOM }}</span>
      </div>
    </header>
    
    <!-- Native VDO.ninja Mixer (full height) -->
    <div class="flex-1 relative">
      <iframe
        ref="iframeRef"
        :src="mixerUrl"
        @load="handleIframeLoad"
        class="absolute inset-0 w-full h-full border-0"
        allow="camera; microphone; autoplay; display-capture"
        allowfullscreen
      ></iframe>
      
      <!-- Loading overlay while iframe loads -->
      <div 
        v-if="!iframeLoaded"
        class="absolute inset-0 flex items-center justify-center bg-r58-bg-primary"
      >
        <div class="flex flex-col items-center gap-4">
          <div class="w-8 h-8 border-2 border-r58-accent-primary border-t-transparent rounded-full animate-spin"></div>
          <span class="text-r58-text-secondary">Loading VDO.ninja mixer...</span>
        </div>
      </div>
    </div>
    
    <!-- Camera Push Bar (feeds cameras to VDO.ninja room) -->
    <CameraPushBar />
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
