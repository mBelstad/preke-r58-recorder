<script setup lang="ts">
/**
 * MixerLiteView - Lightweight mixer for on-device usage
 * 
 * This view is shown when running directly on the R58 device.
 * It provides essential mixer controls WITHOUT the VDO.ninja iframe,
 * which would cause excessive CPU usage from WebRTC video decoding.
 * 
 * Features:
 * - Scene switching (1-4)
 * - Input status display
 * - Recording controls
 * - Go Live button
 * - Option to enable full mode (with warning)
 */
import { computed, onMounted, onUnmounted } from 'vue'
import { useRecorderStore } from '@/stores/recorder'
import { useMixerStore } from '@/stores/mixer'
import { useStreamingStore } from '@/stores/streaming'
import { useKeyboardShortcuts } from '@/composables/useKeyboardShortcuts'
import { toast } from '@/composables/useToast'

const emit = defineEmits<{
  (e: 'enable-full-mode'): void
}>()

const recorderStore = useRecorderStore()
const mixerStore = useMixerStore()
const streamingStore = useStreamingStore()
const { register } = useKeyboardShortcuts()

const isLive = computed(() => mixerStore.isLive)
const inputs = computed(() => recorderStore.inputs)
const activeInputs = computed(() => inputs.value.filter(i => i.hasSignal))

// Polling for input status
let pollInterval: number | null = null

onMounted(() => {
  recorderStore.fetchInputs()
  pollInterval = window.setInterval(() => {
    recorderStore.fetchInputs()
  }, 5000)
  
  // Register keyboard shortcuts
  for (let i = 1; i <= 4; i++) {
    register({
      key: String(i),
      description: `Switch to scene ${i}`,
      action: () => switchToScene(i),
      context: 'mixer-lite',
    })
  }
})

onUnmounted(() => {
  if (pollInterval) {
    clearInterval(pollInterval)
  }
})

function switchToScene(sceneNumber: number) {
  mixerStore.setScene(`scene-${sceneNumber}`)
  toast.info(`Scene ${sceneNumber}`)
  // Note: In lite mode, we can't actually switch VDO.ninja scenes
  // This is just for UI state. Full scene control requires VDO.ninja iframe.
}

function toggleGoLive() {
  if (mixerStore.isLive) {
    mixerStore.toggleLive()
    streamingStore.stopStreaming()
    toast.info('Session ended')
  } else {
    mixerStore.toggleLive()
    streamingStore.startStreaming()
    toast.success('Going live!')
  }
}

async function toggleRecording() {
  try {
    if (recorderStore.isRecording) {
      await recorderStore.stopRecording()
      toast.info('Recording stopped')
    } else {
      await recorderStore.startRecording()
      toast.success('Recording started')
    }
  } catch (error) {
    toast.error('Recording action failed')
  }
}

function enableFullMode() {
  if (confirm('Full Mixer mode loads VDO.ninja which uses significant CPU/GPU resources. This may cause lag on the device. Continue?')) {
    emit('enable-full-mode')
  }
}
</script>

<template>
  <div class="h-full flex flex-col bg-preke-bg-base">
    <!-- Header -->
    <header class="flex items-center justify-between px-6 py-4 border-b border-preke-bg-surface bg-preke-bg-elevated">
      <div class="flex items-center gap-4">
        <div class="flex items-center gap-2">
          <span 
            class="w-3 h-3 rounded-full"
            :class="isLive ? 'bg-preke-red animate-pulse' : 'bg-preke-bg-surface'"
          ></span>
          <span class="text-xl font-semibold text-preke-purple">Mixer</span>
          <span class="text-xs px-2 py-0.5 rounded bg-amber-500/20 text-amber-400 font-medium">
            LITE MODE
          </span>
        </div>
        <span v-if="isLive" class="badge badge-danger">ON AIR</span>
      </div>
      
      <div class="flex items-center gap-4">
        <button 
          class="btn btn-sm btn-secondary"
          @click="enableFullMode"
          title="Enable full VDO.ninja mixer (high CPU usage)"
        >
          <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
          </svg>
          Full Mode
        </button>
        
        <button 
          class="btn"
          :class="isLive ? 'btn-danger' : 'btn-primary'"
          @click="toggleGoLive"
        >
          {{ isLive ? 'End Session' : 'Go Live' }}
        </button>
      </div>
    </header>
    
    <!-- Main Content -->
    <main class="flex-1 p-6 overflow-auto">
      <!-- Info Banner -->
      <div class="mb-6 p-4 rounded-lg bg-amber-500/10 border border-amber-500/30">
        <div class="flex items-start gap-3">
          <svg class="w-5 h-5 text-amber-400 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div>
            <h3 class="font-medium text-amber-400">Local Device Mode</h3>
            <p class="text-sm text-preke-text-dim mt-1">
              VDO.ninja previews are disabled to save CPU. Scene switching and guest management 
              should be done from a remote browser or the Electron app.
            </p>
          </div>
        </div>
      </div>
      
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- Scene Control -->
        <div class="card p-6">
          <h2 class="text-lg font-semibold mb-4">Scene Control</h2>
          <div class="grid grid-cols-4 gap-3">
            <button 
              v-for="i in 4" 
              :key="i"
              class="aspect-video flex items-center justify-center text-2xl font-bold rounded-lg transition-all"
              :class="mixerStore.currentScene === `scene-${i}` 
                ? 'bg-preke-purple text-white ring-2 ring-preke-purple ring-offset-2 ring-offset-preke-bg-base' 
                : 'bg-preke-bg-surface hover:bg-preke-bg-elevated text-preke-text'"
              @click="switchToScene(i)"
            >
              {{ i }}
            </button>
          </div>
          <p class="text-xs text-preke-text-dim mt-3">
            Press 1-4 to switch scenes. Full transitions require VDO.ninja (Full Mode).
          </p>
        </div>
        
        <!-- Input Status -->
        <div class="card p-6">
          <h2 class="text-lg font-semibold mb-4">
            Inputs 
            <span class="text-sm font-normal text-preke-text-dim">({{ activeInputs.length }}/{{ inputs.length }} active)</span>
          </h2>
          <div class="space-y-3">
            <div 
              v-for="input in inputs" 
              :key="input.id"
              class="flex items-center justify-between p-3 rounded-lg"
              :class="input.hasSignal ? 'bg-preke-bg-surface' : 'bg-preke-bg-elevated opacity-50'"
            >
              <div class="flex items-center gap-3">
                <div 
                  class="w-2 h-2 rounded-full"
                  :class="input.hasSignal ? 'bg-green-500' : 'bg-gray-500'"
                ></div>
                <div>
                  <span class="font-medium">{{ input.name }}</span>
                  <span v-if="input.resolution" class="text-xs text-preke-text-dim ml-2">
                    {{ input.resolution }}
                  </span>
                </div>
              </div>
              <div v-if="input.framerate" class="text-sm text-preke-text-dim">
                {{ input.framerate.toFixed(1) }} fps
              </div>
            </div>
          </div>
        </div>
        
        <!-- Recording Control -->
        <div class="card p-6">
          <h2 class="text-lg font-semibold mb-4">Device Recording</h2>
          <div class="flex items-center gap-4">
            <button 
              class="btn flex-1"
              :class="recorderStore.isRecording ? 'btn-danger' : 'btn-primary'"
              @click="toggleRecording"
            >
              <span 
                v-if="recorderStore.isRecording"
                class="w-2 h-2 rounded-full bg-white animate-pulse mr-2"
              ></span>
              {{ recorderStore.isRecording ? 'Stop Recording' : 'Start Recording' }}
            </button>
          </div>
          <div v-if="recorderStore.isRecording" class="mt-3 text-sm text-preke-text-dim">
            Duration: {{ recorderStore.formattedDuration }}
          </div>
        </div>
        
        <!-- Quick Stats -->
        <div class="card p-6">
          <h2 class="text-lg font-semibold mb-4">System Status</h2>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <div class="text-2xl font-bold text-preke-text">{{ activeInputs.length }}</div>
              <div class="text-sm text-preke-text-dim">Active Inputs</div>
            </div>
            <div>
              <div class="text-2xl font-bold" :class="isLive ? 'text-red-500' : 'text-preke-text'">
                {{ isLive ? 'LIVE' : 'Offline' }}
              </div>
              <div class="text-sm text-preke-text-dim">Stream Status</div>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.card {
  @apply bg-preke-bg-elevated rounded-xl border border-preke-bg-surface;
}
</style>

