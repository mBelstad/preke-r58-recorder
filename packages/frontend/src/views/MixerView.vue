<script setup lang="ts">
/**
 * MixerView - Direct WHEP multiview with VDO.ninja playback
 * 
 * IMPORTANT: VDO.ninja room P2P does NOT work through FRP tunnels.
 * Instead, this view uses direct &whepplay= URLs to display each camera
 * in individual iframes. This approach is confirmed working.
 * 
 * Each camera is displayed via VDO.ninja's &whepplay= parameter which
 * pulls the WHEP stream directly from MediaMTX through the nginx proxy.
 */
import { ref, computed, onMounted } from 'vue'
import { useRecorderStore } from '@/stores/recorder'
import { getVdoHost, getVdoProtocol, getPublicWhepUrl } from '@/lib/vdoninja'

// Components
import ModeLoadingScreen from '@/components/shared/ModeLoadingScreen.vue'

const recorderStore = useRecorderStore()

// State
const isLoading = ref(true)
const loadedIframes = ref<Record<string, boolean>>({})

// Active cameras with signal
const activeCameras = computed(() => 
  recorderStore.inputs.filter(i => i.hasSignal)
)

// Build WHEP playback URL for a camera
function buildWhepPlaybackUrl(cameraId: string, label: string): string {
  const VDO_HOST = getVdoHost()
  const VDO_PROTOCOL = getVdoProtocol()
  const whepUrl = getPublicWhepUrl(cameraId)
  
  const url = new URL(`${VDO_PROTOCOL}://${VDO_HOST}/`)
  url.searchParams.set('whepplay', whepUrl)
  url.searchParams.set('label', label)
  url.searchParams.set('cleanoutput', '')
  url.searchParams.set('hideheader', '')
  url.searchParams.set('nologo', '')
  url.searchParams.set('cover', '')
  
  return url.toString()
}

// Track iframe load state
function handleIframeLoad(cameraId: string) {
  console.log(`[Mixer] Camera ${cameraId} iframe loaded`)
  loadedIframes.value[cameraId] = true
}

// Check if all iframes are loaded
const allIframesLoaded = computed(() => {
  if (activeCameras.value.length === 0) return false
  return activeCameras.value.every(cam => loadedIframes.value[cam.id])
})

function handleLoadingReady() {
  isLoading.value = false
}

// Selected camera for program output
const selectedCamera = ref<string | null>(null)

function selectCamera(cameraId: string) {
  selectedCamera.value = cameraId
  console.log(`[Mixer] Selected camera: ${cameraId}`)
}

// Fetch inputs on mount
onMounted(async () => {
  await recorderStore.fetchInputs()
  // Auto-select first camera
  if (activeCameras.value.length > 0) {
    selectedCamera.value = activeCameras.value[0].id
  }
})
</script>

<template>
  <!-- Loading Screen -->
  <Transition name="fade">
    <ModeLoadingScreen
      v-if="isLoading"
      mode="mixer"
      :content-ready="allIframesLoaded || activeCameras.length === 0"
      :min-time="1500"
      :max-time="8000"
      @ready="handleLoadingReady"
    />
  </Transition>
  
  <div class="h-full flex flex-col bg-r58-bg-primary">
    <!-- Minimal Header -->
    <header class="flex items-center justify-between px-4 py-2 border-b border-r58-bg-tertiary bg-r58-bg-secondary">
      <div class="flex items-center gap-3">
        <span class="text-lg font-semibold text-r58-mixer">Mixer</span>
        <span class="text-sm text-r58-text-secondary">
          {{ activeCameras.length }} camera{{ activeCameras.length !== 1 ? 's' : '' }} connected
        </span>
      </div>
      
      <div class="flex items-center gap-2 text-xs text-r58-text-secondary">
        <span class="px-2 py-1 bg-r58-bg-tertiary rounded">Direct WHEP Playback</span>
      </div>
    </header>
    
    <!-- Main Content Area -->
    <div class="flex-1 flex">
      <!-- Program Output (selected camera) -->
      <div class="flex-1 relative bg-black">
        <template v-if="selectedCamera">
          <iframe
            :key="selectedCamera"
            :src="buildWhepPlaybackUrl(selectedCamera, 'Program')"
            class="absolute inset-0 w-full h-full border-0"
            allow="autoplay"
            allowfullscreen
          ></iframe>
          <div class="absolute top-2 left-2 px-2 py-1 bg-red-600 text-white text-xs font-bold rounded">
            PGM
          </div>
        </template>
        <div v-else class="absolute inset-0 flex items-center justify-center text-r58-text-secondary">
          No camera selected
        </div>
      </div>
      
      <!-- Camera Multiview (right sidebar) -->
      <div class="w-80 bg-r58-bg-secondary border-l border-r58-bg-tertiary flex flex-col">
        <div class="px-3 py-2 border-b border-r58-bg-tertiary">
          <span class="text-sm font-medium text-r58-text-primary">Sources</span>
        </div>
        
        <div class="flex-1 overflow-y-auto p-2 space-y-2">
          <template v-if="activeCameras.length === 0">
            <div class="flex items-center justify-center h-32 text-r58-text-secondary text-sm">
              No cameras detected
            </div>
          </template>
          
          <template v-for="camera in activeCameras" :key="camera.id">
            <div 
              class="relative aspect-video bg-black rounded overflow-hidden cursor-pointer transition-all"
              :class="{ 'ring-2 ring-red-500': selectedCamera === camera.id }"
              @click="selectCamera(camera.id)"
            >
              <iframe
                :src="buildWhepPlaybackUrl(camera.id, camera.name)"
                @load="handleIframeLoad(camera.id)"
                class="absolute inset-0 w-full h-full border-0 pointer-events-none"
                allow="autoplay"
              ></iframe>
              
              <!-- Camera Label -->
              <div class="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-2">
                <span class="text-white text-xs font-medium">{{ camera.name }}</span>
              </div>
              
              <!-- Selected indicator -->
              <div 
                v-if="selectedCamera === camera.id"
                class="absolute top-1 right-1 px-1.5 py-0.5 bg-red-600 text-white text-[10px] font-bold rounded"
              >
                ON AIR
              </div>
            </div>
          </template>
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
