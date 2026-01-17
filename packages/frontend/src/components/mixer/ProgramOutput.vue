<script setup lang="ts">
/**
 * Program Output Component
 * 
 * Status-only display showing the health of the program output stream.
 * Automatically pushes the VDO.ninja mixed program output to MediaMTX via WHIP
 * when the mixer goes live (controlled by "Go Live" button in header).
 */
import { ref, watch, onBeforeUnmount, computed } from 'vue'
import { useMixerStore } from '@/stores/mixer'
import { useStreamingStore } from '@/stores/streaming'
import { buildProgramOutputUrl, buildProgramOutputUrlAlpha } from '@/lib/vdoninja'
import { toast } from '@/composables/useToast'

const mixerStore = useMixerStore()
const streamingStore = useStreamingStore()

const isActive = ref(false)
const status = ref<'idle' | 'connecting' | 'live' | 'error'>('idle')
const iframeSrc = ref('')
const streamStatus = ref<any | null>(null)
const lastStatusError = ref<string | null>(null)
let statusPollTimer: ReturnType<typeof setInterval> | null = null

const useAlphaOutput = computed(() => streamingStore.programOutputMode === 'alpha')

// MediaMTX WHIP endpoint for program output
function getWhipUrl(): string {
  // Use app.itagenten.no (same-domain architecture) with CORS headers configured
  // VDO.ninja iframe (from app.itagenten.no/vdo) needs to POST here
  return 'https://app.itagenten.no/mixer_program/whip'
}

async function startProgramOutput() {
  if (isActive.value) return
  
  status.value = 'connecting'
  
  const url = useAlphaOutput.value
    ? await buildProgramOutputUrlAlpha()
    : await buildProgramOutputUrl(getWhipUrl())
  if (!url) {
    status.value = 'error'
    console.error('[ProgramOutput] Failed to build VDO.ninja URL - VDO.ninja not configured')
    return
  }
  
  iframeSrc.value = url
  isActive.value = true
  
  console.log('[ProgramOutput] Starting program output:', url)
}

function stopProgramOutput() {
  if (!isActive.value) return
  
  isActive.value = false
  iframeSrc.value = ''
  status.value = 'idle'
  streamStatus.value = null
  lastStatusError.value = null
  stopStatusPolling()
  
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

async function retryConnection() {
  stopProgramOutput()
  await new Promise(r => setTimeout(r, 500))
  await startProgramOutput()
}

// Auto-start when mixer goes live
watch(() => mixerStore.isLive, async (live) => {
  if (live) {
    await startProgramOutput()
    startStatusPolling()
  } else {
    stopProgramOutput()
  }
})

function startStatusPolling() {
  if (statusPollTimer) return
  statusPollTimer = setInterval(async () => {
    try {
      const statusResponse = await streamingStore.getStreamingStatus()
      if (!statusResponse) return
      streamStatus.value = statusResponse
      lastStatusError.value = statusResponse.error || null
      if (statusResponse.mixer_program_active) {
        status.value = 'live'
      } else if (statusResponse.error) {
        status.value = 'error'
      } else if (isActive.value) {
        status.value = 'connecting'
      }
    } catch (error) {
      lastStatusError.value = error instanceof Error ? error.message : 'Status polling failed'
    }
  }, 2000)
}

function stopStatusPolling() {
  if (statusPollTimer) {
    clearInterval(statusPollTimer)
    statusPollTimer = null
  }
}

onBeforeUnmount(() => {
  stopStatusPolling()
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
    <div class="flex items-center gap-2 px-3 py-2 bg-preke-bg-surface rounded-lg" data-testid="program-output-status">
      <span :class="['w-2 h-2 rounded-full', getStatusColor()]" data-testid="program-output-indicator"></span>
      <span class="text-sm font-medium" data-testid="program-output-text">{{ getStatusText() }}</span>
      
      <!-- Retry button for errors -->
      <button
        v-if="status === 'error'"
        @click="retryConnection()"
        class="ml-auto text-xs text-preke-gold hover:underline"
      >
        Retry
      </button>
    </div>

    <!-- Stream Health Details (when live) -->
    <div v-if="status === 'live'" class="space-y-2">
      <!-- Quick SRT URL -->
      <div class="flex items-center gap-2 px-3 py-2 bg-preke-bg-surface/50 rounded-lg">
        <span class="text-xs text-preke-text-dim">🔴 SRT:</span>
        <code class="flex-1 text-xs truncate text-preke-text-dim">{{ streamingStore.programOutputUrls.srt }}</code>
        <button @click="copySrtUrl" class="text-xs text-preke-gold hover:underline">Copy</button>
      </div>
      
      <!-- Streaming destinations indicator -->
      <div v-if="streamingStore.enabledDestinations.length > 0" class="flex items-center gap-2 px-3 py-2 bg-preke-bg-surface/50 rounded-lg">
        <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
        <span class="text-xs text-preke-text-dim">
          {{ streamingStore.enabledDestinations.length }} streaming destination{{ streamingStore.enabledDestinations.length > 1 ? 's' : '' }} active
        </span>
      </div>
    </div>
    
    <!-- Idle state hint -->
    <p v-if="status === 'idle'" class="text-xs text-preke-text-dim px-3">
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
