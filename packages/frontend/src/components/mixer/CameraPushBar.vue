<script setup lang="ts">
/**
 * Camera Push Bar Component
 * 
 * Automatically pushes R58 HDMI cameras to the VDO.ninja room.
 * Each camera with signal gets a hidden iframe that shares its WHEP stream.
 */
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRecorderStore } from '@/stores/recorder'
import { buildCameraContributionUrl, getPublicWhepUrl } from '@/lib/vdoninja'

const recorderStore = useRecorderStore()

// Camera push status
interface CameraPushState {
  cameraId: string
  label: string
  status: 'idle' | 'connecting' | 'connected' | 'error'
  iframeSrc: string
}

const cameraPushStates = ref<Map<string, CameraPushState>>(new Map())
const expanded = ref(true)

// Get cameras with signal
const camerasWithSignal = computed(() => 
  recorderStore.inputs.filter(i => i.hasSignal)
)

// Build WHEP URL for a camera using the PUBLIC URL
// VDO.ninja (running remotely) needs a publicly accessible URL
function getWhepUrl(cameraId: string): string {
  return getPublicWhepUrl(cameraId)
}

// Initialize or update camera push states when cameras change
watch(camerasWithSignal, (cameras) => {
  // Add new cameras
  for (const camera of cameras) {
    if (!cameraPushStates.value.has(camera.id)) {
      const whepUrl = getWhepUrl(camera.id)
      const iframeSrc = buildCameraContributionUrl(
        camera.id,
        whepUrl,
        camera.label
      )
      cameraPushStates.value.set(camera.id, {
        cameraId: camera.id,
        label: camera.label,
        status: 'connecting',
        iframeSrc,
      })
    }
  }
  
  // Remove cameras that no longer have signal
  const currentIds = new Set(cameras.map(c => c.id))
  for (const [id] of cameraPushStates.value) {
    if (!currentIds.has(id)) {
      cameraPushStates.value.delete(id)
    }
  }
}, { immediate: true })

// Handle iframe load event
function handleIframeLoad(cameraId: string) {
  const state = cameraPushStates.value.get(cameraId)
  if (state) {
    state.status = 'connected'
    console.log(`[CameraPush] ${cameraId} connected to VDO.ninja`)
  }
}

// Handle iframe error
function handleIframeError(cameraId: string) {
  const state = cameraPushStates.value.get(cameraId)
  if (state) {
    state.status = 'error'
    console.error(`[CameraPush] ${cameraId} failed to connect`)
  }
}

// Retry connection for a camera
function retryConnection(cameraId: string) {
  const camera = recorderStore.inputs.find(i => i.id === cameraId)
  if (!camera || !camera.hasSignal) return
  
  const whepUrl = getWhepUrl(cameraId)
  const iframeSrc = buildCameraContributionUrl(
    cameraId,
    whepUrl,
    camera.label
  )
  
  // Force iframe reload by changing src
  cameraPushStates.value.set(cameraId, {
    cameraId,
    label: camera.label,
    status: 'connecting',
    iframeSrc: iframeSrc + `&_t=${Date.now()}`,
  })
}

// Status color helper
function getStatusColor(status: CameraPushState['status']): string {
  switch (status) {
    case 'connected': return 'bg-emerald-500'
    case 'connecting': return 'bg-amber-500 animate-pulse'
    case 'error': return 'bg-red-500'
    default: return 'bg-gray-500'
  }
}

function getStatusText(status: CameraPushState['status']): string {
  switch (status) {
    case 'connected': return 'Live in VDO.ninja'
    case 'connecting': return 'Connecting...'
    case 'error': return 'Failed to connect'
    default: return 'Idle'
  }
}
</script>

<template>
  <div class="camera-push-bar border-t border-preke-bg-surface bg-preke-bg-elevated" data-testid="camera-push-bar">
    <!-- Header (clickable to expand/collapse) -->
    <button 
      @click="expanded = !expanded"
      class="w-full px-4 py-2 flex items-center justify-between text-sm hover:bg-preke-bg-surface/50 transition-colors"
      data-testid="camera-push-toggle"
      aria-expanded="expanded"
    >
      <div class="flex items-center gap-2">
        <span class="font-medium">Camera Sources</span>
        <span class="text-preke-text-dim">({{ camerasWithSignal.length }} active)</span>
      </div>
      <svg 
        class="w-4 h-4 transition-transform"
        :class="{ 'rotate-180': expanded }"
        fill="none" stroke="currentColor" viewBox="0 0 24 24"
      >
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
      </svg>
    </button>
    
    <!-- Expanded content -->
    <div v-if="expanded" class="px-4 pb-3">
      <!-- Camera status cards -->
      <div v-if="cameraPushStates.size > 0" class="flex gap-3 flex-wrap">
        <div
          v-for="[cameraId, state] in cameraPushStates"
          :key="cameraId"
          class="flex items-center gap-2 px-3 py-2 bg-preke-bg-surface rounded-lg"
        >
          <!-- Status indicator -->
          <span :class="['w-2 h-2 rounded-full', getStatusColor(state.status)]"></span>
          
          <!-- Camera label -->
          <span class="text-sm font-medium">{{ state.label }}</span>
          
          <!-- Status text -->
          <span class="text-xs text-preke-text-dim">{{ getStatusText(state.status) }}</span>
          
          <!-- Retry button for errors -->
          <button
            v-if="state.status === 'error'"
            @click="retryConnection(cameraId)"
            class="ml-2 text-xs text-preke-gold hover:underline"
          >
            Retry
          </button>
        </div>
      </div>
      
      <!-- Empty state -->
      <div v-else class="text-sm text-preke-text-dim py-2">
        No cameras connected. Connect HDMI sources to push them to the mixer.
      </div>
    </div>
    
    <!-- Hidden iframes for camera push -->
    <div class="hidden">
      <iframe
        v-for="[cameraId, state] in cameraPushStates"
        :key="cameraId"
        :src="state.iframeSrc"
        @load="handleIframeLoad(cameraId)"
        @error="handleIframeError(cameraId)"
        allow="camera; microphone; autoplay"
        class="w-0 h-0"
      ></iframe>
    </div>
  </div>
</template>

