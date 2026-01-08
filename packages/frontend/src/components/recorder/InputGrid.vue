<script setup lang="ts">
/**
 * Input Grid Component
 * 
 * Displays video inputs in a 2x2 grid with signal quality indicators.
 * Visual feedback includes:
 * - Border colors based on signal status
 * - Recording indicator with bytes written
 * - Signal quality tooltip
 * - Framerate mismatch warning
 * 
 * OPTIMIZATION: Only shows live video previews in Recorder mode.
 * In Mixer mode, shows static placeholders to avoid duplicate
 * WebRTC connections (VDO.ninja handles video in Mixer mode).
 */
import { ref, computed, watch } from 'vue'
import { useRecorderStore, type InputStatus } from '@/stores/recorder'
import { useCapabilitiesStore } from '@/stores/capabilities'
import InputPreview from '@/components/shared/InputPreview.vue'

const recorderStore = useRecorderStore()
const capabilitiesStore = useCapabilitiesStore()

const emit = defineEmits<{
  (e: 'allVideosReady'): void
}>()

// Track which cameras have video ready
const videosReady = ref<Set<string>>(new Set())

// Track aspect ratios per input (default to 16:9)
const aspectRatios = ref<Record<string, number>>({})

function handleVideoReady(inputId: string) {
  videosReady.value.add(inputId)
  console.log(`[InputGrid] Video ready: ${inputId} (${videosReady.value.size}/${inputs.value.length})`)
  
  // Check if all videos are ready
  if (videosReady.value.size >= inputs.value.length) {
    console.log('[InputGrid] All videos ready!')
    emit('allVideosReady')
  }
}

function handleAspectRatio(inputId: string, ratio: number) {
  aspectRatios.value[inputId] = ratio
  console.log(`[InputGrid] Aspect ratio for ${inputId}: ${ratio.toFixed(3)}`)
}

function getTileStyle(inputId: string) {
  const ratio = aspectRatios.value[inputId] || 16/9
  return { aspectRatio: `${ratio}` }
}

// Reset when inputs change
watch(() => inputs.value.length, () => {
  videosReady.value.clear()
})

// Only show live video in recorder mode to avoid duplicate WHEP connections
// VDO.ninja handles video streams in mixer mode
const isRecorderMode = computed(() => 
  capabilitiesStore.capabilities?.current_mode === 'recorder'
)

// Filter to show only inputs with signal (hides disconnected HDMI inputs)
const inputs = computed(() => recorderStore.inputs.filter(i => i.hasSignal))

// Framerate mismatch warning
const framerateMismatch = computed(() => recorderStore.framerateMismatch)

/**
 * Get border color class based on input state
 */
function getBorderClass(input: InputStatus): string {
  if (input.isRecording) {
    return 'border-preke-red ring-2 ring-preke-red/20'
  }
  if (!input.hasSignal) {
    return 'border-preke-bg-surface/50 opacity-60'
  }
  // Signal present but not recording
  return 'border-emerald-500/50 hover:border-emerald-500'
}

/**
 * Get signal quality indicator
 */
function getSignalQuality(input: InputStatus): 'excellent' | 'good' | 'unstable' | 'none' {
  if (!input.hasSignal) return 'none'
  // In a real implementation, this would check framerate variance
  if (input.framerate >= 29) return 'excellent'
  if (input.framerate >= 24) return 'good'
  return 'unstable'
}

/**
 * Get signal quality color
 */
function getSignalQualityColor(input: InputStatus): string {
  const quality = getSignalQuality(input)
  switch (quality) {
    case 'excellent': return 'text-emerald-400'
    case 'good': return 'text-emerald-400'
    case 'unstable': return 'text-amber-400'
    case 'none': return 'text-preke-text-dim'
  }
}

/**
 * Format bytes to human-readable size
 */
function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

/**
 * Generate tooltip for input
 */
function getInputTooltip(input: InputStatus): string {
  if (!input.hasSignal) {
    return `${input.label}: No signal detected`
  }
  
  const lines = [
    `${input.label}`,
    `Resolution: ${input.resolution}`,
    `Framerate: ${input.framerate} fps`,
    `Quality: ${getSignalQuality(input)}`,
  ]
  
  if (input.isRecording) {
    lines.push(`Written: ${formatBytes(input.bytesWritten)}`)
  }
  
  return lines.join('\n')
}
</script>

<template>
  <!-- Empty state when no inputs have signal -->
  <div v-if="inputs.length === 0" class="h-full flex items-center justify-center">
    <div class="text-center text-preke-text-dim">
      <svg class="w-16 h-16 mx-auto mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
      </svg>
      <p class="text-lg font-medium">No Video Sources Connected</p>
      <p class="text-sm mt-2">Connect HDMI cables to begin recording</p>
    </div>
  </div>
  
  <!-- Grid of active inputs - scales to fill without scroll -->
  <div v-else class="input-grid">
    <!-- Framerate mismatch warning banner (discreet) -->
    <div 
      v-if="framerateMismatch" 
      class="input-grid__warning"
    >
      <svg class="w-4 h-4 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
        <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
      </svg>
      <span>{{ framerateMismatch }}</span>
    </div>
    
    <div 
      class="input-grid__container" 
      :data-count="inputs.length"
    >
    <div
      v-for="input in inputs"
      :key="input.id"
      class="input-grid__tile"
      :class="getBorderClass(input)"
      :style="getTileStyle(input.id)"
      :title="getInputTooltip(input)"
    >
      <!-- Video preview - only in recorder mode to avoid duplicate WHEP connections -->
      <InputPreview
        v-if="isRecorderMode"
        :input-id="input.id"
        class="w-full h-full"
        @video-ready="handleVideoReady(input.id)"
        @aspect-ratio="(ratio) => handleAspectRatio(input.id, ratio)"
      />
      <!-- Static placeholder in mixer mode (VDO.ninja handles video) -->
      <div 
        v-else 
        class="w-full h-full flex items-center justify-center bg-preke-bg-surface"
      >
        <div class="text-center">
          <svg class="w-8 h-8 mx-auto mb-2 text-preke-text-dim/50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
          </svg>
          <span class="text-xs text-preke-text-dim/70">Mixer mode</span>
        </div>
      </div>
      
      <!-- Overlay info -->
      <div class="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 to-transparent p-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <!-- Signal quality indicator -->
            <span
              class="w-2 h-2 rounded-full transition-colors"
              :class="{
                'bg-emerald-500': getSignalQuality(input) === 'excellent' || getSignalQuality(input) === 'good',
                'bg-amber-500 animate-pulse': getSignalQuality(input) === 'unstable',
                'bg-preke-text-dim': getSignalQuality(input) === 'none',
              }"
            ></span>
            <span class="font-medium">{{ input.label }}</span>
          </div>
          
          <div v-if="input.hasSignal" class="flex items-center gap-2 text-sm">
            <span class="text-preke-text-dim">{{ input.resolution }}</span>
            <span :class="getSignalQualityColor(input)">{{ input.framerate }}fps</span>
          </div>
        </div>
      </div>
    </div>
    </div>
  </div>
</template>

<style scoped>
/* Input grid that fills available space without scrolling */
.input-grid {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  overflow: hidden;
}

.input-grid__warning {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.375rem 0.75rem;
  background: rgba(245, 158, 11, 0.1);
  border: 1px solid rgba(245, 158, 11, 0.3);
  border-radius: 6px;
  color: #fbbf24;
  font-size: 0.875rem;
}

/* Grid container - CSS Grid for proper sizing within bounds */
.input-grid__container {
  flex: 1;
  display: grid;
  gap: 0.5rem;
  min-height: 0;
  overflow: hidden;
  place-items: center;
  place-content: center;
  grid-auto-flow: row;
}

/* 1 camera - single tile, constrained to container */
.input-grid__container[data-count="1"] {
  grid-template-columns: 1fr;
  grid-template-rows: 1fr;
}

/* 2 cameras - side by side, wrap to single column on narrow screens */
.input-grid__container[data-count="2"] {
  grid-template-columns: repeat(2, 1fr);
  grid-template-rows: 1fr;
}

@media (max-width: 768px) {
  .input-grid__container[data-count="2"] {
    grid-template-columns: 1fr;
    grid-template-rows: repeat(2, 1fr);
  }
}

/* 3-4 cameras - 2x2 grid, wrap to single column on narrow screens */
.input-grid__container[data-count="3"],
.input-grid__container[data-count="4"] {
  grid-template-columns: repeat(2, 1fr);
  grid-template-rows: repeat(2, 1fr);
}

@media (max-width: 768px) {
  .input-grid__container[data-count="3"],
  .input-grid__container[data-count="4"] {
    grid-template-columns: 1fr;
    grid-template-rows: repeat(auto-fit, minmax(200px, 1fr));
  }
}

/* 5-6 cameras - 3x2 grid, wrap on narrow screens */
.input-grid__container[data-count="5"],
.input-grid__container[data-count="6"] {
  grid-template-columns: repeat(3, 1fr);
  grid-template-rows: repeat(2, 1fr);
}

@media (max-width: 1024px) {
  .input-grid__container[data-count="5"],
  .input-grid__container[data-count="6"] {
    grid-template-columns: repeat(2, 1fr);
    grid-template-rows: repeat(auto-fit, minmax(200px, 1fr));
  }
}

@media (max-width: 768px) {
  .input-grid__container[data-count="5"],
  .input-grid__container[data-count="6"] {
    grid-template-columns: 1fr;
    grid-template-rows: repeat(auto-fit, minmax(200px, 1fr));
  }
}

/* Video tile with dynamic aspect ratio (set via :style), constrained to grid cell */
.input-grid__tile {
  position: relative;
  border-radius: 6px;
  overflow: hidden;
  border-width: 2px;
  background: #000;
  transition: all 0.15s ease;
  cursor: pointer;
  /* aspect-ratio set dynamically via :style based on actual video dimensions */
  aspect-ratio: 16 / 9; /* Default fallback until video loads */
  width: 100%;
  max-width: 100%;
  max-height: 100%;
  /* Ensure tile fits within grid cell */
  justify-self: center;
  align-self: center;
}

/* Video fills tile completely (tile handles aspect ratio) */
.input-grid__tile :deep(video) {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
</style>
