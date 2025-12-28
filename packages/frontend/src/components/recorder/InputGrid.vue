<script setup lang="ts">
/**
 * Input Grid Component
 * 
 * Displays video inputs in a 2x2 grid with signal quality indicators.
 * Visual feedback includes:
 * - Border colors based on signal status
 * - Recording indicator with bytes written
 * - Signal quality tooltip
 */
import { computed } from 'vue'
import { useRecorderStore, type InputStatus } from '@/stores/recorder'
import InputPreview from '@/components/shared/InputPreview.vue'

const recorderStore = useRecorderStore()
const inputs = computed(() => recorderStore.inputs)

/**
 * Get border color class based on input state
 */
function getBorderClass(input: InputStatus): string {
  if (input.isRecording) {
    return 'border-r58-accent-danger ring-2 ring-r58-accent-danger/20'
  }
  if (!input.hasSignal) {
    return 'border-r58-bg-tertiary/50 opacity-60'
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
    case 'none': return 'text-r58-text-secondary'
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
  <div class="h-full grid grid-cols-2 gap-4">
    <div
      v-for="input in inputs"
      :key="input.id"
      class="relative rounded-lg overflow-hidden border-2 transition-all cursor-pointer"
      :class="getBorderClass(input)"
      :title="getInputTooltip(input)"
    >
      <!-- Video preview -->
      <InputPreview
        v-if="input.hasSignal"
        :input-id="input.id"
        class="w-full h-full object-cover"
      />
      
      <!-- No signal placeholder -->
      <div
        v-else
        class="w-full h-full bg-r58-bg-secondary flex items-center justify-center"
      >
        <div class="text-center text-r58-text-secondary">
          <svg class="w-12 h-12 mx-auto mb-2 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
          </svg>
          <p>No Signal</p>
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
                'bg-r58-text-secondary': getSignalQuality(input) === 'none',
              }"
            ></span>
            <span class="font-medium">{{ input.label }}</span>
          </div>
          
          <div v-if="input.hasSignal" class="flex items-center gap-2 text-sm">
            <span class="text-r58-text-secondary">{{ input.resolution }}</span>
            <span :class="getSignalQualityColor(input)">{{ input.framerate }}fps</span>
          </div>
        </div>
        
        <!-- Recording indicator -->
        <div v-if="input.isRecording" class="mt-2 flex items-center justify-between">
          <div class="flex items-center gap-2 text-r58-accent-danger">
            <span class="w-2 h-2 rounded-full bg-r58-accent-danger animate-recording"></span>
            <span class="text-sm font-medium">REC</span>
          </div>
          <span class="text-sm font-mono text-r58-text-secondary">
            {{ formatBytes(input.bytesWritten) }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

