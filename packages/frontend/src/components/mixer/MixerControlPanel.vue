<script setup lang="ts">
/**
 * MixerControlPanel - Simple overlay control panel for VDO.ninja mixer
 * 
 * Provides quick access to:
 * - Scene switching (1-9)
 * - Audio controls (mute/volume per source)
 * - Recording control
 * - Camera controls integration
 * 
 * Uses existing useVdoNinja composable (iframe postMessage API)
 */
import { ref, computed, watch, onMounted } from 'vue'
import { useVdoNinja } from '@/composables/useVdoNinja'
import { useCameraControls } from '@/composables/useCameraControls'
import CameraControlModal from '@/components/camera/CameraControlModal.vue'
import type { Ref } from 'vue'

const props = defineProps<{
  iframeRef?: Ref<HTMLIFrameElement | null>
}>()

const emit = defineEmits<{
  (e: 'close'): void
}>()

// VDO.ninja composable - create a dummy ref first, then update when iframe is available
const dummyIframeRef = ref<HTMLIFrameElement | null>(null)
const vdo = useVdoNinja(dummyIframeRef)

// Watch for iframe ref changes and update the dummy ref
watch(() => props.iframeRef?.value, (newIframe) => {
  if (newIframe) {
    console.log('[MixerControlPanel] Iframe ref available, updating:', newIframe)
    dummyIframeRef.value = newIframe
  } else {
    dummyIframeRef.value = null
  }
}, { immediate: true })

// Also check on mount
onMounted(() => {
  if (props.iframeRef?.value) {
    console.log('[MixerControlPanel] On mount, iframe ref:', props.iframeRef.value)
    dummyIframeRef.value = props.iframeRef.value
  }
})

const vdoSources = computed(() => vdo.sources.value)
const isRecording = computed(() => vdo.isRecording.value)
const setLayout = vdo.setLayout
const setMute = vdo.setMute
const toggleMute = vdo.toggleMute
const setVolume = vdo.setVolume
const startRecording = vdo.startRecording
const stopRecording = vdo.stopRecording

// Camera controls
const { cameras, getCamera } = useCameraControls()
const selectedCamera = ref<string | null>(null)
const showCameraModal = ref(false)

// Scene selection
const currentScene = ref<number | null>(null)

// Collapsed state
const collapsed = ref(false)

// Actions
function switchScene(sceneNumber: number) {
  console.log('[MixerControlPanel] Switching to scene', sceneNumber, 'setLayout:', setLayout, 'iframeRef:', props.iframeRef?.value, 'dummyRef:', dummyIframeRef.value, 'vdo.isReady:', vdo.isReady.value)
  
  if (!setLayout) {
    console.warn('[MixerControlPanel] setLayout not available')
    return
  }
  
  if (!vdo.isReady.value) {
    console.warn('[MixerControlPanel] VDO.ninja not ready yet (isReady:', vdo.isReady.value, 'connectionState:', vdo.connectionState.value, ')')
    console.warn('[MixerControlPanel] Attempting anyway - VDO.ninja might queue the command')
  }
  
  // Check if iframe is actually available
  if (!props.iframeRef?.value?.contentWindow) {
    console.error('[MixerControlPanel] Iframe contentWindow not available!')
    return
  }
  
  // VDO.ninja mixer uses layout numbers 0-8 for preset layouts
  // Layout 0 = auto grid, 1 = solo, 2 = side-by-side, etc.
  // For user-friendly UI, we map 1-9 to 0-8
  const vdoLayoutNumber = sceneNumber - 1
  console.log('[MixerControlPanel] Calling setLayout with layout number', vdoLayoutNumber, 'for scene', sceneNumber)
  console.log('[MixerControlPanel] Iframe:', props.iframeRef.value, 'ContentWindow:', props.iframeRef.value.contentWindow)
  
  try {
    setLayout(vdoLayoutNumber)
    currentScene.value = sceneNumber
    console.log('[MixerControlPanel] setLayout called successfully')
  } catch (error) {
    console.error('[MixerControlPanel] Error calling setLayout:', error)
  }
}

function handleToggleMute(sourceId: string) {
  console.log('[MixerControlPanel] Toggling mute for', sourceId, 'toggleMute:', toggleMute)
  if (toggleMute) {
    toggleMute(sourceId)
  } else {
    console.warn('[MixerControlPanel] toggleMute not available')
  }
}

function handleSetVolume(sourceId: string, volume: number) {
  if (setVolume) {
    setVolume(sourceId, volume)
  }
}

function handleRecording() {
  console.log('[MixerControlPanel] Recording toggle, current:', isRecording.value, 'startRecording:', startRecording, 'stopRecording:', stopRecording)
  if (isRecording.value) {
    if (stopRecording) {
      stopRecording()
    } else {
      console.warn('[MixerControlPanel] stopRecording not available')
    }
  } else {
    if (startRecording) {
      startRecording()
    } else {
      console.warn('[MixerControlPanel] startRecording not available')
    }
  }
}

function openCameraControl(cameraName: string) {
  selectedCamera.value = cameraName
  showCameraModal.value = true
}

function closeCameraModal() {
  showCameraModal.value = false
  selectedCamera.value = null
}

// Source list (convert Map to array)
const sourcesList = computed(() => {
  return Array.from(vdoSources.value.values())
})

// Filter cameras that match source IDs
const cameraSources = computed(() => {
  return cameras.value.filter(cam => {
    // Check if camera name matches any source label
    return sourcesList.value.some(source => 
      source.label?.toLowerCase().includes(cam.name.toLowerCase()) ||
      source.id === cam.name
    )
  })
})
</script>

<template>
  <div 
    class="mixer-control-panel fixed top-4 right-4 z-50 bg-preke-bg-surface border border-preke-border rounded-lg shadow-lg transition-all duration-300"
    :class="collapsed ? 'w-12' : 'w-80'"
  >
    <!-- Header -->
    <div class="flex items-center justify-between p-3 border-b border-preke-border">
      <h3 v-if="!collapsed" class="text-sm font-semibold text-preke-text">Mixer Controls</h3>
      <button
        @click="collapsed = !collapsed"
        class="p-1 rounded hover:bg-preke-bg-elevated transition-colors"
        :title="collapsed ? 'Expand' : 'Collapse'"
      >
        <svg 
          class="w-4 h-4 transition-transform"
          :class="{ 'rotate-180': collapsed }"
          fill="none" 
          stroke="currentColor" 
          viewBox="0 0 24 24"
        >
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
        </svg>
      </button>
    </div>

    <!-- Content -->
    <div v-if="!collapsed" class="p-3 space-y-4 max-h-[calc(100vh-200px)] overflow-y-auto">
      <!-- Scene Buttons -->
      <div>
        <label class="text-xs font-medium text-preke-text-dim mb-2 block">Scenes</label>
        <div class="grid grid-cols-3 gap-2">
          <button
            v-for="i in 9"
            :key="i"
            @click="switchScene(i)"
            class="aspect-square flex items-center justify-center text-sm font-bold rounded transition-all"
            :class="currentScene === i 
              ? 'bg-preke-purple text-white ring-2 ring-preke-purple' 
              : 'bg-preke-bg-elevated hover:bg-preke-bg-elevated/80 text-preke-text'"
          >
            {{ i }}
          </button>
        </div>
      </div>

      <!-- Recording Control -->
      <div>
        <label class="text-xs font-medium text-preke-text-dim mb-2 block">Recording</label>
        <button
          @click="handleRecording"
          class="w-full px-4 py-2 rounded transition-all"
            :class="isRecording.value
              ? 'bg-red-600 hover:bg-red-700 text-white'
              : 'bg-preke-bg-elevated hover:bg-preke-bg-elevated/80 text-preke-text'"
        >
          <span class="flex items-center justify-center gap-2">
            <svg 
              v-if="isRecording.value"
              class="w-4 h-4" 
              fill="currentColor" 
              viewBox="0 0 24 24"
            >
              <circle cx="12" cy="12" r="6" />
            </svg>
            <svg 
              v-else
              class="w-4 h-4" 
              fill="currentColor" 
              viewBox="0 0 24 24"
            >
              <circle cx="12" cy="12" r="10" />
            </svg>
            {{ isRecording.value ? 'Stop Recording' : 'Start Recording' }}
          </span>
        </button>
      </div>

      <!-- Sources / Audio Controls -->
      <div v-if="sourcesList.length > 0">
        <label class="text-xs font-medium text-preke-text-dim mb-2 block">Sources</label>
        <div class="space-y-2">
          <div
            v-for="source in sourcesList"
            :key="source.id"
            class="p-2 bg-preke-bg-elevated rounded"
          >
            <div class="flex items-center justify-between mb-1">
              <span class="text-xs text-preke-text">{{ source.label || source.id }}</span>
              <button
                @click="handleToggleMute(source.id)"
                class="p-1 rounded hover:bg-preke-bg-surface transition-colors"
                :class="source.muted ? 'text-red-400' : 'text-preke-text-dim'"
                :title="source.muted ? 'Unmute' : 'Mute'"
              >
                <svg 
                  v-if="source.muted"
                  class="w-4 h-4" 
                  fill="none" 
                  stroke="currentColor" 
                  viewBox="0 0 24 24"
                >
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2" />
                </svg>
                <svg 
                  v-else
                  class="w-4 h-4" 
                  fill="none" 
                  stroke="currentColor" 
                  viewBox="0 0 24 24"
                >
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                </svg>
              </button>
            </div>
            <input
              v-if="source.hasAudio"
              type="range"
              :value="source.audioLevel || 100"
              @input="handleSetVolume(source.id, Number(($event.target as HTMLInputElement).value))"
              min="0"
              max="200"
              class="w-full h-1 bg-preke-bg-base rounded-lg appearance-none cursor-pointer accent-preke-gold"
            />
          </div>
        </div>
      </div>

      <!-- Camera Controls -->
      <div v-if="cameras.length > 0">
        <label class="text-xs font-medium text-preke-text-dim mb-2 block">Camera Controls</label>
        <div class="space-y-1">
          <button
            v-for="camera in cameras"
            :key="camera.name"
            @click="openCameraControl(camera.name)"
            class="w-full px-3 py-2 text-left text-xs bg-preke-bg-elevated hover:bg-preke-bg-elevated/80 rounded transition-colors"
          >
            <span class="flex items-center justify-between">
              <span>{{ camera.name }}</span>
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
              </svg>
            </span>
          </button>
        </div>
      </div>
    </div>

    <!-- Collapsed View -->
    <div v-else class="p-2 space-y-2">
      <button
        @click="switchScene(1)"
        class="w-full aspect-square flex items-center justify-center text-xs font-bold rounded bg-preke-bg-elevated hover:bg-preke-bg-elevated/80"
        title="Scene 1"
      >
        1
      </button>
      <button
        @click="handleRecording"
        class="w-full aspect-square flex items-center justify-center rounded"
        :class="isRecording.value ? 'bg-red-600 text-white' : 'bg-preke-bg-elevated hover:bg-preke-bg-elevated/80'"
        :title="isRecording.value ? 'Stop Recording' : 'Start Recording'"
      >
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
          <circle cx="12" cy="12" r="6" />
        </svg>
      </button>
    </div>

    <!-- Camera Control Modal -->
    <CameraControlModal
      v-if="showCameraModal && selectedCamera"
      :camera-name="selectedCamera"
      @close="closeCameraModal"
    />
  </div>
</template>

<style scoped>
.mixer-control-panel {
  backdrop-filter: blur(10px);
}
</style>
