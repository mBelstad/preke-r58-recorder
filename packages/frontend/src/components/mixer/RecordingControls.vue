<script setup lang="ts">
/**
 * RecordingControls Component
 * 
 * Controls for VDO.ninja local/cloud recording:
 * - Start/stop recording
 * - Recording status indicator
 * - Duration timer
 * - Download link when available
 */
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { toast } from '@/composables/useToast'

// Props from parent (VdoNinjaEmbed)
const props = defineProps<{
  vdoEmbed?: {
    isRecording: { value: boolean }
    startRecording: () => void
    stopRecording: () => void
    sendCommand: (action: string, target?: string, value?: unknown) => void
  }
}>()

// Local state
const isRecording = ref(false)
const recordingStartTime = ref<number | null>(null)
const recordingDuration = ref(0)
const downloadUrl = ref<string | null>(null)
const isProcessing = ref(false)

// Sync with VDO.ninja state
watch(() => props.vdoEmbed?.isRecording?.value, (newValue) => {
  if (newValue !== undefined) {
    isRecording.value = newValue
    if (newValue && !recordingStartTime.value) {
      recordingStartTime.value = Date.now()
    } else if (!newValue && recordingStartTime.value) {
      recordingStartTime.value = null
    }
  }
})

// Duration timer
let durationInterval: number | null = null

function startDurationTimer() {
  if (durationInterval) clearInterval(durationInterval)
  durationInterval = window.setInterval(() => {
    if (recordingStartTime.value) {
      recordingDuration.value = Date.now() - recordingStartTime.value
    }
  }, 100)
}

function stopDurationTimer() {
  if (durationInterval) {
    clearInterval(durationInterval)
    durationInterval = null
  }
}

onMounted(() => {
  startDurationTimer()
})

onUnmounted(() => {
  stopDurationTimer()
})

// Formatted duration
const formattedDuration = computed(() => {
  const totalSeconds = Math.floor(recordingDuration.value / 1000)
  const hours = Math.floor(totalSeconds / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = totalSeconds % 60
  
  if (hours > 0) {
    return `${hours}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`
  }
  return `${minutes}:${seconds.toString().padStart(2, '0')}`
})

// Start recording
async function startRecording() {
  if (!props.vdoEmbed) {
    toast.error('VDO.ninja not connected')
    return
  }
  
  isProcessing.value = true
  
  try {
    props.vdoEmbed.startRecording()
    isRecording.value = true
    recordingStartTime.value = Date.now()
    recordingDuration.value = 0
    downloadUrl.value = null
    toast.success('Recording started')
  } catch (err) {
    toast.error('Failed to start recording')
    console.error('[RecordingControls] Start recording error:', err)
  } finally {
    isProcessing.value = false
  }
}

// Stop recording
async function stopRecording() {
  if (!props.vdoEmbed) {
    toast.error('VDO.ninja not connected')
    return
  }
  
  isProcessing.value = true
  
  try {
    props.vdoEmbed.stopRecording()
    isRecording.value = false
    recordingStartTime.value = null
    
    toast.success(`Recording stopped (${formattedDuration.value})`)
    
    // Note: Download URL would come from VDO.ninja postMessage event
    // For now, show a message about accessing the recording
  } catch (err) {
    toast.error('Failed to stop recording')
    console.error('[RecordingControls] Stop recording error:', err)
  } finally {
    isProcessing.value = false
  }
}

// Toggle recording
function toggleRecording() {
  if (isRecording.value) {
    stopRecording()
  } else {
    startRecording()
  }
}

// Get status color
function getStatusColor() {
  if (isRecording.value) return 'bg-r58-accent-danger animate-pulse'
  return 'bg-r58-bg-tertiary'
}

// Get status text
function getStatusText() {
  if (isProcessing.value) return 'Processing...'
  if (isRecording.value) return `Recording • ${formattedDuration.value}`
  return 'Ready to record'
}
</script>

<template>
  <div class="recording-controls space-y-3" data-testid="recording-controls">
    <!-- Status display -->
    <div class="flex items-center gap-3 px-3 py-2 bg-r58-bg-tertiary rounded-lg">
      <!-- Status indicator -->
      <span 
        class="w-3 h-3 rounded-full"
        :class="getStatusColor()"
        data-testid="recording-indicator"
      ></span>
      
      <!-- Status text -->
      <span class="text-sm font-medium flex-1" data-testid="recording-status">
        {{ getStatusText() }}
      </span>
      
      <!-- Duration (when recording) -->
      <span 
        v-if="isRecording" 
        class="text-lg font-mono font-bold text-r58-accent-danger"
        data-testid="recording-duration"
      >
        {{ formattedDuration }}
      </span>
    </div>
    
    <!-- Control buttons -->
    <div class="flex gap-2">
      <button
        @click="toggleRecording"
        :disabled="isProcessing"
        class="btn flex-1 justify-center"
        :class="isRecording ? 'btn-danger' : 'btn-primary'"
        data-testid="recording-toggle-button"
      >
        <template v-if="isProcessing">
          <svg class="animate-spin w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
          </svg>
          Processing...
        </template>
        <template v-else-if="isRecording">
          <svg class="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 24 24">
            <rect x="6" y="6" width="12" height="12" rx="1" />
          </svg>
          Stop Recording
        </template>
        <template v-else>
          <svg class="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="8" />
          </svg>
          Start Recording
        </template>
      </button>
    </div>
    
    <!-- Download link (when available) -->
    <div v-if="downloadUrl" class="px-3 py-2 bg-r58-accent-success/10 border border-r58-accent-success/30 rounded-lg">
      <div class="flex items-center justify-between">
        <span class="text-sm text-r58-accent-success">Recording ready!</span>
        <a 
          :href="downloadUrl" 
          download 
          class="text-sm text-r58-accent-primary hover:underline"
        >
          Download
        </a>
      </div>
    </div>
    
    <!-- Info text -->
    <p class="text-xs text-r58-text-secondary px-1">
      Records the mixed output locally in your browser. Recording is saved when stopped.
    </p>
  </div>
</template>

<style scoped>
.btn-danger {
  @apply bg-r58-accent-danger hover:bg-red-600;
}
</style>

