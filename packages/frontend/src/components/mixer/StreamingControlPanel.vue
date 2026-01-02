<script setup lang="ts">
/**
 * StreamingControlPanel - Controls for program output streaming
 * 
 * Features:
 * - Start/Stop streaming to MediaMTX (WHIP output)
 * - Watch program locally in popup window
 * - Configure streaming destinations (YouTube, Twitch, etc.)
 * - Status indicator showing connection state
 */
import { ref, computed } from 'vue'
import { useMixerStore } from '@/stores/mixer'
import { useStreamingStore } from '@/stores/streaming'
import { openProgramPopup } from '@/lib/vdoninja'
import { toast } from '@/composables/useToast'
import StreamingSettings from './StreamingSettings.vue'
import ProgramOutput from './ProgramOutput.vue'

const mixerStore = useMixerStore()
const streamingStore = useStreamingStore()

const streamingSettingsRef = ref<InstanceType<typeof StreamingSettings> | null>(null)
const programOutputRef = ref<InstanceType<typeof ProgramOutput> | null>(null)

// Local state
const isStreaming = computed(() => mixerStore.isLive)
const streamingStatus = computed(() => {
  if (!isStreaming.value) return 'idle'
  // Get status from ProgramOutput component if available
  return 'live'
})

// Actions
function toggleStreaming() {
  if (isStreaming.value) {
    stopStreaming()
  } else {
    startStreaming()
  }
}

async function startStreaming() {
  // Toggle mixer live state which triggers ProgramOutput to start WHIP push
  mixerStore.setLive(true)
  
  // If there are enabled destinations, configure RTMP relay via MediaMTX runOnReady hook
  if (streamingStore.enabledDestinations.length > 0) {
    const result = await streamingStore.startRtmpRelay()
    if (result.success) {
      toast.success(result.message)
    } else {
      toast.error(`RTMP relay failed: ${result.message}`)
    }
  } else {
    toast.success('Streaming started (no RTMP destinations configured)')
  }
}

async function stopStreaming() {
  mixerStore.setLive(false)
  
  // Stop RTMP relay (removes MediaMTX runOnReady hook)
  if (streamingStore.enabledDestinations.length > 0) {
    const result = await streamingStore.stopRtmpRelay()
    if (!result.success) {
      toast.warning(`Note: ${result.message}`)
    }
  }
  
  toast.info('Streaming stopped')
}

function watchProgram() {
  const popup = openProgramPopup(1)
  if (!popup) {
    toast.error('Popup blocked - please allow popups for this site')
  } else {
    toast.success('Program window opened')
  }
}

function openStreamingSettings() {
  streamingSettingsRef.value?.open()
}

// Status color helper
function getStatusColor(): string {
  switch (streamingStatus.value) {
    case 'live': return 'bg-red-500'
    case 'connecting': return 'bg-amber-500 animate-pulse'
    case 'error': return 'bg-red-500'
    default: return 'bg-gray-500'
  }
}

function getStatusText(): string {
  switch (streamingStatus.value) {
    case 'live': return 'LIVE'
    case 'connecting': return 'Connecting...'
    case 'error': return 'Error'
    default: return 'Offline'
  }
}
</script>

<template>
  <div class="streaming-control-panel flex items-center gap-3 px-4 py-2 bg-r58-bg-secondary border-b border-r58-bg-tertiary">
    <!-- Status Indicator -->
    <div class="flex items-center gap-2">
      <span :class="['w-2 h-2 rounded-full', getStatusColor()]"></span>
      <span class="text-sm font-medium">{{ getStatusText() }}</span>
    </div>
    
    <!-- Divider -->
    <div class="h-6 w-px bg-r58-bg-tertiary"></div>
    
    <!-- Start/Stop Streaming Button -->
    <button
      @click="toggleStreaming"
      :class="[
        'px-4 py-2 rounded-lg font-medium text-sm transition-all',
        isStreaming 
          ? 'bg-red-600 hover:bg-red-500 text-white' 
          : 'bg-emerald-600 hover:bg-emerald-500 text-white'
      ]"
    >
      {{ isStreaming ? '⏹ Stop Streaming' : '▶ Start Streaming' }}
    </button>
    
    <!-- Watch Program Button -->
    <button
      @click="watchProgram"
      class="px-4 py-2 rounded-lg font-medium text-sm bg-r58-bg-tertiary hover:bg-r58-accent-primary text-r58-text-primary transition-colors"
      title="Open program output in new window"
    >
      👁 Watch Program
    </button>
    
    <!-- Streaming Settings Button -->
    <button
      @click="openStreamingSettings"
      class="px-4 py-2 rounded-lg font-medium text-sm bg-r58-bg-tertiary hover:bg-r58-accent-primary text-r58-text-primary transition-colors"
      title="Configure streaming destinations"
    >
      ⚙️ Streaming Settings
    </button>
    
    <!-- Active Destinations Indicator -->
    <div v-if="streamingStore.enabledDestinations.length > 0" class="flex items-center gap-2 ml-auto">
      <span class="text-xs text-r58-text-secondary">
        Streaming to:
      </span>
      <div class="flex items-center gap-1">
        <span
          v-for="dest in streamingStore.enabledDestinations"
          :key="dest.id"
          class="px-2 py-1 bg-r58-bg-tertiary rounded text-xs"
          :title="dest.name"
        >
          {{ dest.platformId === 'youtube' ? '▶️' : dest.platformId === 'twitch' ? '📺' : '🔴' }}
          {{ dest.name }}
        </span>
      </div>
    </div>
    
    <!-- Hidden ProgramOutput component (handles WHIP push) -->
    <div class="hidden">
      <ProgramOutput ref="programOutputRef" />
    </div>
    
    <!-- Streaming Settings Modal -->
    <StreamingSettings ref="streamingSettingsRef" />
  </div>
</template>

<style scoped>
/* Additional styles if needed */
</style>

