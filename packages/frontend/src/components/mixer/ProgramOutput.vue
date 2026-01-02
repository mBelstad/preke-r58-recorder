<script setup lang="ts">
/**
 * Program Output Component
 * 
 * Status-only display showing the health of the program output stream.
 * Automatically pushes the VDO.ninja mixed program output to MediaMTX via WHIP
 * when the mixer goes live (controlled by "Go Live" button in header).
 */
import { ref, watch } from 'vue'
import { useMixerStore } from '@/stores/mixer'
import { useStreamingStore } from '@/stores/streaming'
import { buildProgramOutputUrl } from '@/lib/vdoninja'
import { toast } from '@/composables/useToast'

const mixerStore = useMixerStore()
const streamingStore = useStreamingStore()

const isActive = ref(false)
const status = ref<'idle' | 'connecting' | 'live' | 'error'>('idle')
const iframeSrc = ref('')

// MediaMTX WHIP endpoint for program output
function getWhipUrl(): string {
  // MediaMTX WHIP format: https://host/{stream_name}/whip
  return `https://r58-mediamtx.itagenten.no/mixer_program/whip`
}

function startProgramOutput() {
  if (isActive.value) return
  
  status.value = 'connecting'
  iframeSrc.value = buildProgramOutputUrl(getWhipUrl())
  isActive.value = true
  
  console.log('[ProgramOutput] Starting WHIP push to MediaMTX')
}

function stopProgramOutput() {
  if (!isActive.value) return
  
  isActive.value = false
  iframeSrc.value = ''
  status.value = 'idle'
  
  console.log('[ProgramOutput] Stopped WHIP push')
}

function handleIframeLoad() {
  if (isActive.value) {
    status.value = 'live'
    console.log('[ProgramOutput] WHIP push connected')
  }
}

function handleIframeError() {
  status.value = 'error'
  console.error('[ProgramOutput] WHIP push failed')
}

function retryConnection() {
  stopProgramOutput()
  setTimeout(() => startProgramOutput(), 500)
}

// Auto-start when mixer goes live
watch(() => mixerStore.isLive, (live) => {
  if (live) {
    startProgramOutput()
  } else {
    stopProgramOutput()
  }
})

// Status color helper
function getStatusColor(): string {
  switch (status.value) {
    case 'live': return 'bg-emerald-500'
    case 'connecting': return 'bg-amber-500 animate-pulse'
    case 'error': return 'bg-red-500'
    default: return 'bg-gray-500'
  }
}

function getStatusText(): string {
  switch (status.value) {
    case 'live': return 'MediaMTX connected'
    case 'connecting': return 'Connecting...'
    case 'error': return 'Connection failed'
    default: return 'Inactive'
  }
}

// Quick copy SRT URL
function copySrtUrl() {
  const srtUrl = streamingStore.programOutputUrls.srt
  navigator.clipboard.writeText(srtUrl)
  toast.success('SRT URL copied')
}
</script>

<template>
  <div class="program-output space-y-3" data-testid="program-output">
    <!-- Status indicator -->
    <div class="flex items-center gap-2 px-3 py-2 bg-r58-bg-tertiary rounded-lg" data-testid="program-output-status">
      <span :class="['w-2 h-2 rounded-full', getStatusColor()]" data-testid="program-output-indicator"></span>
      <span class="text-sm font-medium" data-testid="program-output-text">{{ getStatusText() }}</span>
      
      <!-- Retry button for errors -->
      <button
        v-if="status === 'error'"
        @click="retryConnection()"
        class="ml-auto text-xs text-r58-accent-primary hover:underline"
      >
        Retry
      </button>
    </div>

    <!-- Stream Health Details (when live) -->
    <div v-if="status === 'live'" class="space-y-2">
      <!-- Quick SRT URL -->
      <div class="flex items-center gap-2 px-3 py-2 bg-r58-bg-tertiary/50 rounded-lg">
        <span class="text-xs text-r58-text-secondary">🔴 SRT:</span>
        <code class="flex-1 text-xs truncate text-r58-text-secondary">{{ streamingStore.programOutputUrls.srt }}</code>
        <button @click="copySrtUrl" class="text-xs text-r58-accent-primary hover:underline">Copy</button>
      </div>
      
      <!-- Streaming destinations indicator -->
      <div v-if="streamingStore.enabledDestinations.length > 0" class="flex items-center gap-2 px-3 py-2 bg-r58-bg-tertiary/50 rounded-lg">
        <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
        <span class="text-xs text-r58-text-secondary">
          {{ streamingStore.enabledDestinations.length }} streaming destination{{ streamingStore.enabledDestinations.length > 1 ? 's' : '' }} active
        </span>
      </div>
    </div>
    
    <!-- Idle state hint -->
    <p v-if="status === 'idle'" class="text-xs text-r58-text-secondary px-3">
      Program output will start automatically when you go live.
    </p>
    
    <!-- Hidden iframe for WHIP output -->
    <div class="hidden">
      <iframe
        v-if="isActive && iframeSrc"
        :src="iframeSrc"
        @load="handleIframeLoad"
        @error="handleIframeError"
        allow="camera; microphone; autoplay"
        class="w-0 h-0"
      ></iframe>
    </div>
  </div>
</template>
