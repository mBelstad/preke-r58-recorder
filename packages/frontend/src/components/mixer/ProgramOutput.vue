<script setup lang="ts">
/**
 * Program Output Component
 * 
 * Pushes the VDO.ninja mixed program output to MediaMTX via WHIP.
 * This allows the program feed to be recorded or streamed externally.
 */
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useMixerStore } from '@/stores/mixer'
import { buildProgramOutputUrl } from '@/lib/vdoninja'

const mixerStore = useMixerStore()

const isActive = ref(false)
const status = ref<'idle' | 'connecting' | 'live' | 'error'>('idle')
const iframeSrc = ref('')

// MediaMTX WHIP endpoint for program output
function getWhipUrl(): string {
  const origin = window.location.origin
  return `${origin}/api/v1/whip/program/whip`
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
    case 'live': return 'Program live on MediaMTX'
    case 'connecting': return 'Connecting...'
    case 'error': return 'Output failed'
    default: return 'Program output off'
  }
}
</script>

<template>
  <div class="program-output">
    <!-- Status indicator -->
    <div class="flex items-center gap-2 px-3 py-2 bg-r58-bg-tertiary rounded-lg">
      <span :class="['w-2 h-2 rounded-full', getStatusColor()]"></span>
      <span class="text-sm">Program Output</span>
      <span class="text-xs text-r58-text-secondary">{{ getStatusText() }}</span>
      
      <!-- Manual toggle -->
      <button
        v-if="!mixerStore.isLive"
        @click="isActive ? stopProgramOutput() : startProgramOutput()"
        class="ml-auto text-xs text-r58-accent-primary hover:underline"
      >
        {{ isActive ? 'Stop' : 'Start' }}
      </button>
      
      <!-- Retry button -->
      <button
        v-if="status === 'error'"
        @click="startProgramOutput()"
        class="ml-2 text-xs text-r58-accent-primary hover:underline"
      >
        Retry
      </button>
    </div>
    
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

