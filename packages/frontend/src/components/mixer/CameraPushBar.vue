<script setup lang="ts">
/**
 * Camera Push Bar Component
 * 
 * Automatically pushes R58 HDMI cameras to the VDO.ninja room.
 * Each camera with signal gets a hidden iframe that shares its WHEP stream.
 */
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRecorderStore } from '@/stores/recorder'
import { buildCameraContributionUrl, getPublicWhepUrl, VDO_ROOM, VDO_DIRECTOR_PASSWORD } from '@/lib/vdoninja'

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

// Log component mount and initial state
onMounted(() => {
  console.log('[CameraPush] Component mounted')
  console.log('[CameraPush] Initial inputs:', recorderStore.inputs.length)
  console.log('[CameraPush] Initial cameras with signal:', camerasWithSignal.value.length)
  console.log('[CameraPush] Inputs loaded:', recorderStore.inputsLoaded)
})

// Also watch for inputs to be loaded (in case watch runs before inputs are fetched)
watch(() => recorderStore.inputsLoaded, (loaded) => {
  if (loaded) {
    console.log('[CameraPush] Inputs loaded, checking for cameras with signal')
    const cameras = camerasWithSignal.value
    if (cameras.length > 0) {
      console.log(`[CameraPush] Found ${cameras.length} cameras with signal after inputs loaded`)
    }
  }
})

// Initialize or update camera push states when cameras change
watch(camerasWithSignal, async (cameras) => {
  console.log(`[CameraPush] Cameras with signal changed: ${cameras.length}`, cameras.map(c => c.id))
  // Add new cameras
  for (const camera of cameras) {
    if (!cameraPushStates.value.has(camera.id)) {
      try {
        console.log(`[CameraPush] Setting up ${camera.id} (${camera.label})`)
        // Both functions are async - need to await them
        const whepUrl = await getPublicWhepUrl(camera.id)
        if (!whepUrl) {
          console.error(`[CameraPush] No WHEP URL for ${camera.id}`)
          continue
        }
        console.log(`[CameraPush] WHEP URL for ${camera.id}:`, whepUrl)
        // IMPORTANT: Enable MediaMTX mode to use SFU instead of P2P
        // P2P exposes ICE candidates with Tailscale/LAN IPs causing Mixed Content errors
        const iframeSrc = await buildCameraContributionUrl(
          camera.id,
          whepUrl,
          camera.label,
          { useMediamtx: true }
        )
        if (!iframeSrc) {
          console.error(`[CameraPush] Failed to build contribution URL for ${camera.id}`)
          continue
        }
        console.log(`[CameraPush] Contribution URL for ${camera.id}:`, iframeSrc)
        console.log(`[CameraPush] Full URL breakdown:`, {
          cameraId: camera.id,
          label: camera.label,
          whepUrl,
          iframeSrc: iframeSrc.substring(0, 300) + '...',
          room: VDO_ROOM,
          password: VDO_DIRECTOR_PASSWORD.substring(0, 4) + '...'
        })
        cameraPushStates.value.set(camera.id, {
          cameraId: camera.id,
          label: camera.label,
          status: 'connecting',
          iframeSrc,
        })
      } catch (e) {
        console.error(`[CameraPush] Error setting up ${camera.id}:`, e)
      }
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
    console.log(`[CameraPush] ${cameraId} iframe loaded - URL:`, state.iframeSrc.substring(0, 200) + '...')
    
    // Try to verify connection by checking iframe content
    // Note: Cross-origin restrictions may prevent this in some cases
    setTimeout(() => {
      const iframe = document.querySelector(`iframe[title*="${state.label}"]`) as HTMLIFrameElement
      if (iframe) {
        try {
          // Check if iframe has loaded (may fail due to CORS)
          const iframeDoc = iframe.contentDocument || iframe.contentWindow?.document
          if (iframeDoc) {
            console.log(`[CameraPush] ${cameraId} iframe document accessible`)
          }
        } catch (e) {
          // Expected for cross-origin iframes - this is normal
          console.log(`[CameraPush] ${cameraId} iframe loaded (cross-origin, cannot inspect content)`)
        }
      }
    }, 2000)
  }
}

// Handle iframe error
function handleIframeError(cameraId: string) {
  const state = cameraPushStates.value.get(cameraId)
  if (state) {
    state.status = 'error'
    console.error(`[CameraPush] ${cameraId} iframe failed to load - URL:`, state.iframeSrc.substring(0, 200) + '...')
  }
}

// Retry connection for a camera
async function retryConnection(cameraId: string) {
  const camera = recorderStore.inputs.find(i => i.id === cameraId)
  if (!camera || !camera.hasSignal) return
  
  try {
    const whepUrl = await getPublicWhepUrl(cameraId)
    if (!whepUrl) {
      console.error(`[CameraPush] No WHEP URL for ${cameraId}`)
      return
    }
    // Enable MediaMTX mode to use SFU instead of P2P (avoids Mixed Content errors)
    const iframeSrc = await buildCameraContributionUrl(
      cameraId,
      whepUrl,
      camera.label,
      { useMediamtx: true }
    )
    if (!iframeSrc) {
      console.error(`[CameraPush] Failed to build contribution URL for ${cameraId}`)
      return
    }
    
    // Force iframe reload by changing src
    cameraPushStates.value.set(cameraId, {
      cameraId,
      label: camera.label,
      status: 'connecting',
      iframeSrc: iframeSrc + `&_t=${Date.now()}`,
    })
  } catch (e) {
    console.error(`[CameraPush] Error retrying ${cameraId}:`, e)
  }
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
    <!-- Use fixed positioning off-screen instead of hidden class to ensure iframes load in Electron -->
    <!-- Make iframes slightly larger (10x10px) to ensure they load in Electron -->
    <div class="fixed -left-[9999px] -top-[9999px] w-[10px] h-[10px] overflow-hidden pointer-events-none opacity-0">
      <iframe
        v-for="[cameraId, state] in cameraPushStates"
        :key="cameraId"
        :src="state.iframeSrc"
        @load="handleIframeLoad(cameraId)"
        @error="handleIframeError(cameraId)"
        allow="camera; microphone; autoplay; display-capture"
        class="w-full h-full border-0"
        :title="`Camera push for ${state.label}`"
        sandbox="allow-same-origin allow-scripts allow-forms allow-popups allow-popups-to-escape-sandbox"
      ></iframe>
    </div>
  </div>
</template>

