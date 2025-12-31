<script setup lang="ts">
/**
 * MixerView - Hybrid approach with real VDO.ninja mixer.html
 * 
 * Uses VDO.ninja's actual mixer.html for:
 * - Transitions (real animations)
 * - Layouts (real drag-drop)
 * - Guest management (real waiting room)
 * - Scene control (real scene switching)
 * 
 * R58 sidebar provides:
 * - Camera push status (WHEP to VDO.ninja)
 * - Program output status (WHIP to MediaMTX)
 * - Local recording controls (using verified API)
 * - Quick scene buttons
 */
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useMixerStore } from '@/stores/mixer'
import { useRecorderStore } from '@/stores/recorder'
import { useStreamingStore } from '@/stores/streaming'
import { useKeyboardShortcuts } from '@/composables/useKeyboardShortcuts'
import { toast } from '@/composables/useToast'
import VdoNinjaEmbed from '@/components/mixer/VdoNinjaEmbed.vue'
import SourcePanel from '@/components/mixer/SourcePanel.vue'
import CameraPushBar from '@/components/mixer/CameraPushBar.vue'
import ProgramOutput from '@/components/mixer/ProgramOutput.vue'
import StreamingSettings from '@/components/mixer/StreamingSettings.vue'
import RecordingControls from '@/components/mixer/RecordingControls.vue'
import HotkeySettings from '@/components/mixer/HotkeySettings.vue'
import ConnectionStatus from '@/components/mixer/ConnectionStatus.vue'
import ModeLoadingScreen from '@/components/shared/ModeLoadingScreen.vue'

const mixerStore = useMixerStore()
const recorderStore = useRecorderStore()
const streamingStore = useStreamingStore()
const { register } = useKeyboardShortcuts()
const vdoEmbedRef = ref<InstanceType<typeof VdoNinjaEmbed> | null>(null)
const streamingSettingsRef = ref<InstanceType<typeof StreamingSettings> | null>(null)
const hotkeySettingsRef = ref<InstanceType<typeof HotkeySettings> | null>(null)

const isLive = computed(() => mixerStore.isLive)
const enabledDestinationsCount = computed(() => streamingStore.enabledDestinations.length)

// Loading state
const isLoading = ref(true)
const contentReady = ref(false)

function handleLoadingReady() {
  isLoading.value = false
}

// Mark content ready when inputs are loaded OR iframe is ready
function markContentReady() {
  contentReady.value = true
}

// Refresh inputs interval - adaptive based on recording state
let inputsRefreshInterval: number | null = null

// Polling interval: 5s when recording, 15s when idle (saves resources)
function getPollingInterval(): number {
  return recorderStore.isRecording ? 5000 : 15000
}

function startInputsPolling() {
  if (inputsRefreshInterval) {
    clearInterval(inputsRefreshInterval)
  }
  inputsRefreshInterval = window.setInterval(() => {
    recorderStore.fetchInputs()
  }, getPollingInterval())
}

// Track registered shortcuts for cleanup
const unregisterFns: (() => void)[] = []

// Watch for recording state changes to adjust polling rate
watch(() => recorderStore.isRecording, () => {
  startInputsPolling()
})

onMounted(async () => {
  // Fetch initial HDMI inputs status
  await recorderStore.fetchInputs()
  
  // Mark content as ready once inputs are fetched
  markContentReady()
  
  // Set up interval to refresh inputs (adaptive rate)
  startInputsPolling()
  
  // Register quick scene shortcuts (1-4) using verified API
  for (let i = 1; i <= 4; i++) {
    const unregister = register({
      key: String(i),
      description: `Switch to scene ${i}`,
      action: () => switchToScene(i),
      context: 'mixer',
    })
    unregisterFns.push(unregister)
  }
  
  // G for Go Live toggle
  unregisterFns.push(register({
    key: 'g',
    description: 'Toggle Go Live',
    action: () => toggleGoLive(),
    context: 'mixer',
  }))
  
  // R for recording toggle
  unregisterFns.push(register({
    key: 'r',
    description: 'Toggle recording',
    action: () => toggleRecording(),
    context: 'mixer',
  }))
})

onUnmounted(() => {
  unregisterFns.forEach(fn => fn())
  if (inputsRefreshInterval) {
    clearInterval(inputsRefreshInterval)
    inputsRefreshInterval = null
  }
})

/**
 * Switch to scene using VERIFIED VDO.ninja API
 * API: action: "addScene", target: "*" (all sources), value: sceneNumber
 */
function switchToScene(sceneNumber: number) {
  if (vdoEmbedRef.value) {
    // Use the verified addToScene API
    vdoEmbedRef.value.sendCommand('addScene', '*', sceneNumber)
  }
  mixerStore.setScene(`scene-${sceneNumber}`)
  toast.info(`Scene ${sceneNumber}`)
}

/**
 * Toggle local recording using VERIFIED VDO.ninja API
 * API: action: "record", value: true/false
 */
function toggleRecording() {
  if (!vdoEmbedRef.value) return
  
  if (vdoEmbedRef.value.isRecording?.value) {
    vdoEmbedRef.value.stopRecording()
    toast.info('Recording stopped')
  } else {
    vdoEmbedRef.value.startRecording()
    toast.success('Recording started')
  }
}

function toggleGoLive() {
  if (mixerStore.isLive) {
    // Ending session
    mixerStore.toggleLive()
    streamingStore.stopStreaming()
    toast.info('Session ended')
  } else {
    // Starting session
    mixerStore.toggleLive()
    streamingStore.startStreaming()
    
    const destCount = streamingStore.enabledDestinations.length
    if (destCount > 0) {
      toast.success(`Live! Streaming to ${destCount} destination${destCount > 1 ? 's' : ''}`)
    } else {
      toast.info('Live! (No streaming destinations configured)')
    }
  }
}

function openStreamingSettings() {
  streamingSettingsRef.value?.open()
}

function openHotkeySettings() {
  hotkeySettingsRef.value?.open()
}
</script>

<template>
  <!-- Loading Screen -->
  <Transition name="fade">
    <ModeLoadingScreen
      v-if="isLoading"
      mode="mixer"
      :content-ready="contentReady"
      :min-time="1500"
      :max-time="8000"
      @ready="handleLoadingReady"
    />
  </Transition>
  
  <div class="h-full flex flex-col">
    <!-- Header -->
    <header class="flex items-center justify-between px-6 py-4 border-b border-r58-bg-tertiary bg-r58-bg-secondary" data-testid="mixer-header">
      <div class="flex items-center gap-4">
        <div class="flex items-center gap-2">
          <span 
            class="w-3 h-3 rounded-full"
            :class="isLive ? 'bg-r58-accent-danger animate-recording' : 'bg-r58-bg-tertiary'"
            data-testid="live-indicator"
          ></span>
          <span class="text-xl font-semibold text-r58-mixer" data-testid="mixer-title">Mixer</span>
        </div>
        <span v-if="isLive" class="badge badge-danger" data-testid="on-air-badge">ON AIR</span>
        <span v-if="isLive && enabledDestinationsCount > 0" class="text-xs text-r58-text-secondary">
          Streaming to {{ enabledDestinationsCount }} platform{{ enabledDestinationsCount > 1 ? 's' : '' }}
        </span>
        
        <!-- Connection Status -->
        <ConnectionStatus :vdo-embed="vdoEmbedRef" />
      </div>
      
      <div class="flex items-center gap-4">
        <!-- Hotkey Settings Button -->
        <button 
          class="btn btn-sm" 
          @click="openHotkeySettings"
          title="Keyboard Shortcuts (Shift+?)"
          data-testid="hotkey-settings-button"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
          </svg>
        </button>
        
        <!-- Streaming Settings Button -->
        <button 
          class="btn btn-sm" 
          @click="openStreamingSettings"
          title="Streaming Settings"
          data-testid="streaming-settings-button"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </button>
        
        <!-- Go Live Button -->
        <button 
          class="btn"
          :class="isLive ? 'btn-danger' : 'btn-primary'"
          @click="toggleGoLive"
          data-testid="go-live-button"
        >
          {{ isLive ? 'End Session' : 'Go Live' }}
        </button>
      </div>
    </header>
    
    <!-- Main content -->
    <div class="flex-1 flex overflow-hidden">
      <!-- VDO.ninja MIXER embed (real mixer.html with transitions/layouts/guest management) -->
      <div class="flex-1 p-4">
        <VdoNinjaEmbed 
          ref="vdoEmbedRef"
          profile="director"
          class="h-full"
        />
      </div>
      
      <!-- R58 Sidebar - Only real, working features -->
      <aside class="w-80 border-l border-r58-bg-tertiary bg-r58-bg-secondary p-4 overflow-y-auto">
        <!-- Quick Scene Buttons -->
        <div class="mb-6">
          <h3 class="text-sm font-semibold text-r58-text-secondary uppercase tracking-wide mb-3">Quick Scenes</h3>
          <div class="grid grid-cols-4 gap-2">
            <button 
              v-for="i in 4" 
              :key="i"
              class="btn btn-sm"
              :class="mixerStore.currentScene === `scene-${i}` ? 'btn-primary' : ''"
              @click="switchToScene(i)"
              :data-testid="`scene-btn-${i}`"
            >
              {{ i }}
            </button>
          </div>
          <p class="text-xs text-r58-text-secondary mt-2">
            Press 1-4 for quick switch. Full layout control is in the mixer above.
          </p>
        </div>
        
        <!-- Source Status (read-only from VDO) -->
        <div class="mb-6 pt-4 border-t border-r58-bg-tertiary">
          <SourcePanel :vdo-embed="vdoEmbedRef" />
        </div>
        
        <!-- Program Output control -->
        <div class="mb-6 pt-4 border-t border-r58-bg-tertiary">
          <h3 class="text-sm font-semibold text-r58-text-secondary uppercase tracking-wide mb-3">Program Output</h3>
          <ProgramOutput />
        </div>
        
        <!-- Local Recording control (using VERIFIED record API) -->
        <div class="pt-4 border-t border-r58-bg-tertiary">
          <h3 class="text-sm font-semibold text-r58-text-secondary uppercase tracking-wide mb-3">Local Recording</h3>
          <RecordingControls :vdo-embed="vdoEmbedRef" />
        </div>
      </aside>
    </div>
    
    <!-- Camera Push Bar (auto-pushes HDMI sources to VDO.ninja room) -->
    <CameraPushBar />
    
    <!-- Streaming Settings Modal (rendered via Teleport) -->
    <StreamingSettings ref="streamingSettingsRef" />
    
    <!-- Hotkey Settings Modal -->
    <HotkeySettings ref="hotkeySettingsRef" />
  </div>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
