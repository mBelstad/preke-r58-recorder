<script setup lang="ts">
/**
 * Recording Health Indicator
 * 
 * Shows real-time recording health metrics:
 * - Write speed (MB/s)
 * - Buffer status (OK/Warning/Critical)
 * - Frames dropped counter
 */
import { ref, computed, watch, onUnmounted } from 'vue'
import { useRecorderStore } from '@/stores/recorder'

const recorderStore = useRecorderStore()

// Track bytes over time to calculate write speed
const previousBytes = ref<Record<string, number>>({})
const writeSpeedMBps = ref(0)
const bufferPercent = ref(0)
const framesDropped = ref(0)

let speedInterval: number | null = null

// Calculate write speed from bytes written changes
function calculateWriteSpeed() {
  const currentBytes: Record<string, number> = {}
  let totalDelta = 0
  
  recorderStore.inputs.forEach(input => {
    currentBytes[input.id] = input.bytesWritten
    const prevBytes = previousBytes.value[input.id] || 0
    totalDelta += (input.bytesWritten - prevBytes)
  })
  
  // Convert to MB/s (interval is 1 second)
  writeSpeedMBps.value = Math.round((totalDelta / (1024 * 1024)) * 10) / 10
  previousBytes.value = currentBytes
}

// Start monitoring when recording
watch(() => recorderStore.isRecording, (isRecording) => {
  if (isRecording) {
    // Reset metrics
    previousBytes.value = {}
    writeSpeedMBps.value = 0
    bufferPercent.value = 0
    framesDropped.value = 0
    
    // Start speed calculation
    speedInterval = window.setInterval(calculateWriteSpeed, 1000)
  } else {
    if (speedInterval) {
      clearInterval(speedInterval)
      speedInterval = null
    }
  }
}, { immediate: true })

onUnmounted(() => {
  if (speedInterval) {
    clearInterval(speedInterval)
  }
})

// Health status
const healthStatus = computed(() => {
  if (!recorderStore.isRecording) return 'idle'
  
  // Check for problems
  if (framesDropped.value > 0 || bufferPercent.value > 90) return 'critical'
  if (writeSpeedMBps.value < 1 || bufferPercent.value > 70) return 'warning'
  return 'healthy'
})

const statusColor = computed(() => {
  switch (healthStatus.value) {
    case 'healthy': return 'emerald'
    case 'warning': return 'amber'
    case 'critical': return 'red'
    default: return 'zinc'
  }
})

const statusLabel = computed(() => {
  switch (healthStatus.value) {
    case 'healthy': return 'Healthy'
    case 'warning': return 'Warning'
    case 'critical': return 'Critical'
    default: return 'Idle'
  }
})

// Tooltip text
const tooltip = computed(() => {
  if (!recorderStore.isRecording) return 'Not recording'
  
  const lines = [
    `Write speed: ${writeSpeedMBps.value} MB/s`,
    `Buffer: ${bufferPercent.value}%`,
  ]
  
  if (framesDropped.value > 0) {
    lines.push(`Frames dropped: ${framesDropped.value}`)
  }
  
  return lines.join('\n')
})

// Update from WebSocket events (can be called from store)
function updateFromMetrics(metrics: { buffer_percent?: number; frames_dropped?: number }) {
  if (metrics.buffer_percent !== undefined) {
    bufferPercent.value = metrics.buffer_percent
  }
  if (metrics.frames_dropped !== undefined) {
    framesDropped.value = metrics.frames_dropped
  }
}

defineExpose({ updateFromMetrics })
</script>

<template>
  <div 
    v-if="recorderStore.isRecording"
    class="flex items-center gap-3 px-3 py-1.5 rounded-lg transition-colors cursor-help"
    :class="{
      'bg-emerald-500/10': statusColor === 'emerald',
      'bg-amber-500/10': statusColor === 'amber',
      'bg-red-500/10': statusColor === 'red',
    }"
    :title="tooltip"
  >
    <!-- Status dot -->
    <span 
      :class="[
        'w-2 h-2 rounded-full',
        statusColor === 'emerald' ? 'bg-emerald-500' : '',
        statusColor === 'amber' ? 'bg-amber-500 animate-pulse' : '',
        statusColor === 'red' ? 'bg-red-500 animate-pulse' : '',
      ]"
    ></span>
    
    <!-- Write speed -->
    <div class="flex items-center gap-1.5 text-sm">
      <svg class="w-3.5 h-3.5 text-r58-text-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
      </svg>
      <span 
        :class="[
          'font-mono',
          statusColor === 'emerald' ? 'text-emerald-400' : '',
          statusColor === 'amber' ? 'text-amber-400' : '',
          statusColor === 'red' ? 'text-red-400' : '',
        ]"
      >
        {{ writeSpeedMBps }} MB/s
      </span>
    </div>
    
    <!-- Buffer indicator (only show if non-zero) -->
    <div v-if="bufferPercent > 0" class="flex items-center gap-1.5 text-sm">
      <span class="text-r58-text-secondary">Buf:</span>
      <span 
        :class="[
          'font-mono',
          bufferPercent < 50 ? 'text-emerald-400' : '',
          bufferPercent >= 50 && bufferPercent < 80 ? 'text-amber-400' : '',
          bufferPercent >= 80 ? 'text-red-400' : '',
        ]"
      >
        {{ bufferPercent }}%
      </span>
    </div>
    
    <!-- Frames dropped (only show if non-zero) -->
    <div v-if="framesDropped > 0" class="flex items-center gap-1.5 text-sm text-red-400">
      <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
      <span class="font-mono">{{ framesDropped }} dropped</span>
    </div>
  </div>
</template>

