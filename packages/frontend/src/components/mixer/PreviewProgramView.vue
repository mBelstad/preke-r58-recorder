<script setup lang="ts">
/**
 * PreviewProgramView - Dual monitor PVW/PGM layout
 * 
 * The heart of the broadcast-style mixer interface.
 * Shows Preview (what's next) and Program (what's live) side by side
 * with transition controls between them.
 * 
 * Uses VDO.ninja scene iframes to display actual video:
 * - PVW: Shows the scene currently selected for preview (muted, lower quality)
 * - PGM: Shows the live program output (scene 1, full quality)
 */
import { ref, computed, watch } from 'vue'
import { useMixerStore } from '@/stores/mixer'
import { useScenesStore } from '@/stores/scenes'
import { buildPreviewUrl, buildProgramUrl } from '@/lib/vdoninja'
import VdoNinjaEmbed from './VdoNinjaEmbed.vue'
import type { MixerController } from '@/composables/useMixerController'

const props = defineProps<{
  vdoEmbed?: InstanceType<typeof VdoNinjaEmbed> | null
  controller?: MixerController
}>()

const emit = defineEmits<{
  (e: 'take'): void
  (e: 'cut'): void
}>()

const mixerStore = useMixerStore()
const scenesStore = useScenesStore()

// Local transition state
const selectedTransition = ref(mixerStore.transition.type)
const transitionDuration = ref(mixerStore.transition.duration)

// Refs for iframe containers
const pvwIframeReady = ref(false)
const pgmIframeReady = ref(false)

// Computed
const previewScene = computed(() => 
  scenesStore.getScene(mixerStore.previewSceneId || '')
)

const programScene = computed(() => 
  scenesStore.getScene(mixerStore.programSceneId || '')
)

const canTake = computed(() => 
  mixerStore.previewSceneId !== null && 
  mixerStore.previewSceneId !== mixerStore.programSceneId &&
  !mixerStore.isTransitioning
)

const isLive = computed(() => mixerStore.isLive)

// VDO.ninja scene iframe URLs
// Preview uses the scene's vdoSceneNumber, Program always uses scene 1
const previewIframeSrc = computed(() => {
  if (!previewScene.value) return null
  return buildPreviewUrl(previewScene.value.vdoSceneNumber)
})

const programIframeSrc = computed(() => {
  // Program always shows VDO.ninja scene 1 (the live output)
  return buildProgramUrl(1)
})

// Watch for transition changes
watch([selectedTransition, transitionDuration], ([type, duration]) => {
  mixerStore.setTransition({ type: type as any, duration })
})

// Actions
function handleTake() {
  if (!canTake.value) return
  
  // Use controller if available (syncs with VDO.ninja)
  if (props.controller) {
    props.controller.takeToProgram()
  } else {
    mixerStore.take()
  }
  emit('take')
}

function handleCut() {
  if (!mixerStore.previewSceneId) return
  
  // Use controller if available (syncs with VDO.ninja)
  if (props.controller) {
    props.controller.cutToProgram()
  } else {
    mixerStore.cut()
  }
  emit('cut')
}

// Transition options
const transitionOptions = [
  { value: 'cut', label: 'CUT' },
  { value: 'fade', label: 'FADE' },
  { value: 'wipe-left', label: 'WIPE L' },
  { value: 'wipe-right', label: 'WIPE R' }
]

const durationOptions = [
  { value: 100, label: '0.1s' },
  { value: 300, label: '0.3s' },
  { value: 500, label: '0.5s' },
  { value: 1000, label: '1.0s' }
]
</script>

<template>
  <div class="preview-program-view h-full flex flex-col" data-testid="preview-program-view">
    <!-- Dual Monitor Layout -->
    <div class="flex-1 flex gap-4 min-h-0">
      <!-- Preview Monitor (PVW) -->
      <div class="flex-1 flex flex-col min-w-0">
        <div class="flex items-center justify-between mb-2">
          <div class="flex items-center gap-2">
            <span class="text-xs font-bold uppercase tracking-wider text-amber-400">PVW</span>
            <span class="text-xs text-r58-text-secondary">Preview</span>
          </div>
          <span v-if="previewScene" class="text-xs text-r58-text-secondary">
            {{ previewScene.name }}
          </span>
        </div>
        
        <div 
          class="flex-1 bg-black rounded-lg overflow-hidden border-2 transition-colors relative"
          :class="previewScene ? 'border-amber-500/50' : 'border-r58-bg-tertiary'"
        >
          <!-- VDO.ninja Scene Preview (live video) -->
          <iframe
            v-if="previewIframeSrc"
            :src="previewIframeSrc"
            class="absolute inset-0 w-full h-full border-0"
            :class="{ 'opacity-0': !pvwIframeReady }"
            allow="autoplay; fullscreen"
            @load="pvwIframeReady = true"
          ></iframe>
          
          <!-- Scene Info Overlay -->
          <div 
            v-if="previewScene" 
            class="absolute bottom-2 left-2 right-2 flex items-center justify-between pointer-events-none"
          >
            <span class="px-2 py-1 bg-black/70 rounded text-xs text-white">
              Scene {{ previewScene.vdoSceneNumber }}: {{ previewScene.name }}
            </span>
            <span class="px-2 py-1 bg-black/70 rounded text-xs text-amber-400">
              {{ previewScene.slots.filter(s => s.sourceId).length }}/{{ previewScene.slots.length }} sources
            </span>
          </div>
          
          <!-- Loading State -->
          <div 
            v-if="previewScene && !pvwIframeReady" 
            class="absolute inset-0 flex items-center justify-center bg-r58-bg-secondary"
          >
            <div class="animate-spin w-6 h-6 border-2 border-amber-400 border-t-transparent rounded-full"></div>
          </div>
          
          <!-- Empty State -->
          <div v-if="!previewScene" class="absolute inset-0 flex items-center justify-center text-r58-text-secondary">
            <div class="text-center">
              <svg class="w-8 h-8 mx-auto mb-2 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
              <p class="text-sm">Select a scene to preview</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Transition Controls (Center) -->
      <div class="flex flex-col items-center justify-center gap-3 px-2">
        <!-- TAKE Button -->
        <button 
          @click="handleTake"
          :disabled="!canTake"
          class="take-button w-20 h-16 rounded-lg font-bold text-lg transition-all"
          :class="canTake 
            ? 'bg-red-600 hover:bg-red-500 text-white shadow-lg shadow-red-500/30' 
            : 'bg-r58-bg-tertiary text-r58-text-secondary cursor-not-allowed'"
          data-testid="take-button"
        >
          <span v-if="mixerStore.isTransitioning" class="animate-pulse">...</span>
          <span v-else>TAKE</span>
        </button>
        
        <!-- CUT Button -->
        <button 
          @click="handleCut"
          :disabled="!mixerStore.previewSceneId"
          class="w-20 h-10 rounded-lg font-bold text-sm transition-all"
          :class="mixerStore.previewSceneId 
            ? 'bg-r58-bg-tertiary hover:bg-r58-accent-primary text-r58-text-primary' 
            : 'bg-r58-bg-tertiary/50 text-r58-text-secondary cursor-not-allowed'"
          data-testid="cut-button"
        >
          CUT
        </button>
        
        <!-- Transition Type Selector -->
        <div class="flex flex-col gap-1 mt-2">
          <select 
            v-model="selectedTransition"
            class="w-20 px-2 py-1 text-xs bg-r58-bg-tertiary border border-r58-bg-tertiary rounded text-center"
          >
            <option v-for="opt in transitionOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </option>
          </select>
          
          <select 
            v-model.number="transitionDuration"
            class="w-20 px-2 py-1 text-xs bg-r58-bg-tertiary border border-r58-bg-tertiary rounded text-center"
          >
            <option v-for="opt in durationOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </option>
          </select>
        </div>
      </div>

      <!-- Program Monitor (PGM) -->
      <div class="flex-1 flex flex-col min-w-0">
        <div class="flex items-center justify-between mb-2">
          <div class="flex items-center gap-2">
            <span 
              class="text-xs font-bold uppercase tracking-wider"
              :class="isLive ? 'text-red-500' : 'text-r58-text-secondary'"
            >
              PGM
            </span>
            <span class="text-xs text-r58-text-secondary">Program</span>
            <span 
              v-if="isLive" 
              class="px-2 py-0.5 bg-red-600 text-white text-xs font-bold rounded animate-pulse"
            >
              LIVE
            </span>
          </div>
          <span v-if="programScene" class="text-xs text-r58-text-secondary">
            {{ programScene.name }}
          </span>
        </div>
        
        <div 
          class="flex-1 bg-black rounded-lg overflow-hidden border-2 transition-colors relative"
          :class="isLive ? 'border-red-500' : (programScene ? 'border-emerald-500/50' : 'border-r58-bg-tertiary')"
        >
          <!-- VDO.ninja Program Output (live video from scene 1) -->
          <iframe
            v-if="programIframeSrc"
            :src="programIframeSrc"
            class="absolute inset-0 w-full h-full border-0"
            :class="{ 'opacity-0': !pgmIframeReady }"
            allow="autoplay; fullscreen"
            @load="pgmIframeReady = true"
          ></iframe>
          
          <!-- Scene Info Overlay -->
          <div 
            v-if="programScene" 
            class="absolute bottom-2 left-2 right-2 flex items-center justify-between pointer-events-none"
          >
            <span class="px-2 py-1 bg-black/70 rounded text-xs text-white">
              {{ programScene.name }}
            </span>
            <span v-if="isLive" class="px-2 py-1 bg-red-600/90 rounded text-xs text-white font-bold">
              ON AIR
            </span>
          </div>
          
          <!-- Loading State -->
          <div 
            v-if="!pgmIframeReady" 
            class="absolute inset-0 flex items-center justify-center bg-r58-bg-secondary"
          >
            <div class="animate-spin w-6 h-6 border-2 border-emerald-400 border-t-transparent rounded-full"></div>
          </div>
          
          <!-- Live indicator overlay -->
          <div v-if="isLive" class="absolute top-2 left-2 flex items-center gap-2 pointer-events-none">
            <div class="w-3 h-3 rounded-full bg-red-500 animate-recording"></div>
          </div>
          
          <!-- Empty State (only when no program scene AND iframe not loaded) -->
          <div v-if="!programScene && !pgmIframeReady" class="absolute inset-0 flex items-center justify-center text-r58-text-secondary">
            <div class="text-center">
              <svg class="w-8 h-8 mx-auto mb-2 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p class="text-sm">Waiting for program...</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.take-button:not(:disabled):active {
  transform: scale(0.95);
}

@keyframes recording {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.animate-recording {
  animation: recording 1s ease-in-out infinite;
}
</style>

