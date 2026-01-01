<script setup lang="ts">
/**
 * MixerView - Complete mixer interface with PVW/PGM workflow
 * 
 * Features:
 * - Preview/Program dual-monitor layout
 * - Scene management with thumbnails
 * - Source panel with audio controls
 * - Transition controls (Cut/Fade/Wipe)
 * - VDO.ninja integration for WebRTC
 * - MediaMTX output for streaming
 * 
 * Keyboard shortcuts:
 * - 1-8: Select scene for preview
 * - Space: Take (transition preview to program)
 * - Escape: Cut (immediate switch)
 * - G: Toggle Go Live
 * - R: Toggle recording
 */
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useMixerStore } from '@/stores/mixer'
import { useScenesStore, type Scene } from '@/stores/scenes'
import { useRecorderStore } from '@/stores/recorder'
import { useStreamingStore } from '@/stores/streaming'
import { useKeyboardShortcuts } from '@/composables/useKeyboardShortcuts'
import { useLocalDeviceMode } from '@/composables/useLocalDeviceMode'
import { toast } from '@/composables/useToast'

// Components
import MixerWorkspace from '@/components/mixer/MixerWorkspace.vue'
import VdoNinjaEmbed from '@/components/mixer/VdoNinjaEmbed.vue'
import CameraPushBar from '@/components/mixer/CameraPushBar.vue'
import ProgramOutput from '@/components/mixer/ProgramOutput.vue'
import StreamingSettings from '@/components/mixer/StreamingSettings.vue'
import HotkeySettings from '@/components/mixer/HotkeySettings.vue'
import ConnectionStatus from '@/components/mixer/ConnectionStatus.vue'
import RecordingControls from '@/components/mixer/RecordingControls.vue'
import AudioMixer from '@/components/mixer/AudioMixer.vue'
import TransitionSettings from '@/components/mixer/TransitionSettings.vue'
import InviteLinks from '@/components/mixer/InviteLinks.vue'
import SceneEditor from '@/components/mixer/SceneEditor.vue'
import ModeLoadingScreen from '@/components/shared/ModeLoadingScreen.vue'
import MixerLiteView from '@/components/mixer/MixerLiteView.vue'

// Stores
const mixerStore = useMixerStore()
const scenesStore = useScenesStore()
const recorderStore = useRecorderStore()
const streamingStore = useStreamingStore()

// Composables
const { register } = useKeyboardShortcuts()
const { isLiteMode } = useLocalDeviceMode()

// Refs
const vdoEmbedRef = ref<InstanceType<typeof VdoNinjaEmbed> | null>(null)
const streamingSettingsRef = ref<InstanceType<typeof StreamingSettings> | null>(null)
const hotkeySettingsRef = ref<InstanceType<typeof HotkeySettings> | null>(null)
const sceneEditorRef = ref<InstanceType<typeof SceneEditor> | null>(null)

// State
const forceFullMode = ref(false)
const showFullMixer = computed(() => !isLiteMode.value || forceFullMode.value)
const isLoading = ref(true)
const contentReady = ref(false)
const sidebarCollapsed = ref(false)

// Computed
const isLive = computed(() => mixerStore.isLive)
const enabledDestinationsCount = computed(() => streamingStore.enabledDestinations.length)
const currentSceneName = computed(() => {
  const scene = scenesStore.getScene(mixerStore.programSceneId || '')
  return scene?.name || 'No Scene'
})

// ==========================================
// LIFECYCLE
// ==========================================

function handleLoadingReady() {
  isLoading.value = false
}

// Watch for VDO.ninja ready state
watch(() => vdoEmbedRef.value?.isReady?.value, (ready) => {
  if (ready) {
    console.log('[Mixer] VDO.ninja ready')
    contentReady.value = true
  }
}, { immediate: true })

// Polling for inputs (adaptive rate)
let inputsRefreshInterval: number | null = null

function getPollingInterval(): number {
  return recorderStore.isRecording ? 10000 : 30000
}

function startInputsPolling() {
  if (inputsRefreshInterval) {
    clearInterval(inputsRefreshInterval)
  }
  inputsRefreshInterval = window.setInterval(() => {
    recorderStore.fetchInputs()
  }, getPollingInterval())
}

watch(() => recorderStore.isRecording, () => {
  startInputsPolling()
})

// Track registered shortcuts
const unregisterFns: (() => void)[] = []

onMounted(async () => {
  // Fetch initial inputs
  await recorderStore.fetchInputs()
  startInputsPolling()
  
  // Register scene shortcuts (1-8)
  for (let i = 1; i <= 8; i++) {
    const sceneIndex = i - 1
    const unregister = register({
      key: String(i),
      description: `Select scene ${i} for preview`,
      action: () => {
        const scene = scenesStore.scenes[sceneIndex]
        if (scene) {
          mixerStore.setPreviewScene(scene.id)
          toast.info(`Preview: ${scene.name}`)
        }
      },
      context: 'mixer'
    })
    unregisterFns.push(unregister)
  }
  
  // Space for Take
  unregisterFns.push(register({
    key: ' ',
    description: 'Take (transition preview to program)',
    action: () => {
      if (mixerStore.previewSceneId && mixerStore.previewSceneId !== mixerStore.programSceneId) {
        mixerStore.take()
        toast.success('Take!')
      }
    },
    context: 'mixer'
  }))
  
  // Escape for Cut
  unregisterFns.push(register({
    key: 'Escape',
    description: 'Cut (immediate switch)',
    action: () => {
      if (mixerStore.previewSceneId) {
        mixerStore.cut()
        toast.info('Cut')
      }
    },
    context: 'mixer'
  }))
  
  // G for Go Live
  unregisterFns.push(register({
    key: 'g',
    description: 'Toggle Go Live',
    action: toggleGoLive,
    context: 'mixer'
  }))
  
  // R for recording
  unregisterFns.push(register({
    key: 'r',
    description: 'Toggle recording',
    action: toggleRecording,
    context: 'mixer'
  }))
})

onUnmounted(() => {
  unregisterFns.forEach(fn => fn())
  if (inputsRefreshInterval) {
    clearInterval(inputsRefreshInterval)
    inputsRefreshInterval = null
  }
})

// ==========================================
// ACTIONS
// ==========================================

function toggleGoLive() {
  if (mixerStore.isLive) {
    mixerStore.toggleLive()
    streamingStore.stopStreaming()
    toast.info('Session ended')
  } else {
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

function openStreamingSettings() {
  streamingSettingsRef.value?.open()
}

function openHotkeySettings() {
  hotkeySettingsRef.value?.open()
}

function handleEditScene(scene: Scene) {
  sceneEditorRef.value?.open(scene)
}

function handleAddScene() {
  sceneEditorRef.value?.openNew()
}

function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value
}
</script>

<template>
  <!-- Lite Mode for on-device usage -->
  <MixerLiteView 
    v-if="!showFullMixer"
    @enable-full-mode="forceFullMode = true"
  />
  
  <!-- Full Mode -->
  <template v-else>
    <!-- Loading Screen -->
    <Transition name="fade">
      <ModeLoadingScreen
        v-if="isLoading"
        mode="mixer"
        :content-ready="contentReady"
        :min-time="2000"
        :max-time="15000"
        @ready="handleLoadingReady"
      />
    </Transition>
    
    <div class="h-full flex flex-col bg-r58-bg-primary">
      <!-- Header -->
      <header 
        class="flex items-center justify-between px-6 py-3 border-b border-r58-bg-tertiary bg-r58-bg-secondary"
        data-testid="mixer-header"
      >
        <div class="flex items-center gap-4">
          <!-- Live Indicator -->
          <div class="flex items-center gap-2">
            <span 
              class="w-3 h-3 rounded-full transition-colors"
              :class="isLive ? 'bg-red-500 animate-pulse' : 'bg-r58-bg-tertiary'"
            ></span>
            <span class="text-xl font-semibold text-r58-mixer">Mixer</span>
          </div>
          
          <!-- On Air Badge -->
          <span 
            v-if="isLive" 
            class="px-3 py-1 bg-red-600 text-white text-xs font-bold uppercase tracking-wider rounded"
          >
            ON AIR
          </span>
          
          <!-- Current Scene -->
          <span class="text-sm text-r58-text-secondary">
            {{ currentSceneName }}
          </span>
          
          <!-- Streaming Destinations -->
          <span 
            v-if="isLive && enabledDestinationsCount > 0" 
            class="text-xs text-r58-text-secondary"
          >
            → {{ enabledDestinationsCount }} platform{{ enabledDestinationsCount > 1 ? 's' : '' }}
          </span>
          
          <!-- Connection Status -->
          <ConnectionStatus :vdo-embed="vdoEmbedRef" />
        </div>
        
        <div class="flex items-center gap-3">
          <!-- Mode Toggle (Simple / PVW-PGM) -->
          <div class="flex items-center gap-1 bg-r58-bg-tertiary rounded-lg p-1">
            <button 
              @click="mixerStore.setMode('simple')"
              class="px-3 py-1 text-xs rounded transition-colors"
              :class="mixerStore.mode === 'simple' 
                ? 'bg-r58-accent-primary text-white' 
                : 'text-r58-text-secondary hover:text-r58-text-primary'"
            >
              Simple
            </button>
            <button 
              @click="mixerStore.setMode('pvw-pgm')"
              class="px-3 py-1 text-xs rounded transition-colors"
              :class="mixerStore.mode === 'pvw-pgm' 
                ? 'bg-r58-accent-primary text-white' 
                : 'text-r58-text-secondary hover:text-r58-text-primary'"
            >
              PVW/PGM
            </button>
          </div>
          
          <!-- Hotkeys Button -->
          <button 
            class="btn btn-sm" 
            @click="openHotkeySettings"
            title="Keyboard Shortcuts (Shift+?)"
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
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </button>
          
          <!-- Go Live Button -->
          <button 
            class="btn px-6"
            :class="isLive ? 'btn-danger' : 'btn-primary'"
            @click="toggleGoLive"
          >
            {{ isLive ? 'End Session' : 'Go Live' }}
          </button>
        </div>
      </header>
      
      <!-- Main Content -->
      <div class="flex-1 flex overflow-hidden">
        <!-- Workspace (Sources + PVW/PGM + Scenes) -->
        <div class="flex-1 min-w-0">
          <MixerWorkspace 
            :vdo-embed="vdoEmbedRef"
            @edit-scene="handleEditScene"
            @add-scene="handleAddScene"
          />
        </div>
        
        <!-- Sidebar (collapsible) -->
        <aside 
          class="flex-shrink-0 border-l border-r58-bg-tertiary bg-r58-bg-secondary overflow-y-auto transition-all duration-300"
          :class="sidebarCollapsed ? 'w-12' : 'w-72'"
        >
          <!-- Collapse Toggle -->
          <button 
            @click="toggleSidebar"
            class="w-full p-3 flex items-center justify-between border-b border-r58-bg-tertiary hover:bg-r58-bg-tertiary/50 transition-colors"
          >
            <span v-if="!sidebarCollapsed" class="text-sm font-medium">Controls</span>
            <svg 
              class="w-4 h-4 transition-transform"
              :class="{ 'rotate-180': sidebarCollapsed }"
              fill="none" stroke="currentColor" viewBox="0 0 24 24"
            >
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
            </svg>
          </button>
          
          <!-- Sidebar Content -->
          <div v-show="!sidebarCollapsed" class="p-4 space-y-6">
            <!-- Transition Settings -->
            <section>
              <h3 class="text-xs font-semibold text-r58-text-secondary uppercase tracking-wide mb-3">
                Transitions
              </h3>
              <TransitionSettings />
            </section>
            
            <!-- Audio Mixer -->
            <section>
              <h3 class="text-xs font-semibold text-r58-text-secondary uppercase tracking-wide mb-3">
                Audio
              </h3>
              <AudioMixer :vdo-embed="vdoEmbedRef" />
            </section>
            
            <!-- Program Output -->
            <section>
              <h3 class="text-xs font-semibold text-r58-text-secondary uppercase tracking-wide mb-3">
                Program Output
              </h3>
              <ProgramOutput />
            </section>
            
            <!-- Recording Controls -->
            <section>
              <h3 class="text-xs font-semibold text-r58-text-secondary uppercase tracking-wide mb-3">
                Recording
              </h3>
              <RecordingControls :vdo-embed="vdoEmbedRef" />
            </section>
            
            <!-- Invite Links -->
            <section>
              <h3 class="text-xs font-semibold text-r58-text-secondary uppercase tracking-wide mb-3">
                Invite Guests
              </h3>
              <InviteLinks />
            </section>
          </div>
          
          <!-- Collapsed Icons -->
          <div v-show="sidebarCollapsed" class="p-2 space-y-4">
            <button 
              class="w-8 h-8 mx-auto flex items-center justify-center rounded hover:bg-r58-bg-tertiary"
              title="Transitions"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
              </svg>
            </button>
            <button 
              class="w-8 h-8 mx-auto flex items-center justify-center rounded hover:bg-r58-bg-tertiary"
              title="Audio"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
              </svg>
            </button>
            <button 
              class="w-8 h-8 mx-auto flex items-center justify-center rounded hover:bg-r58-bg-tertiary"
              title="Recording"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
            </button>
          </div>
        </aside>
      </div>
      
      <!-- Camera Push Bar -->
      <CameraPushBar />
      
      <!-- Hidden VDO.ninja Embed for API Control -->
      <div class="hidden">
        <VdoNinjaEmbed 
          ref="vdoEmbedRef"
          profile="director"
        />
      </div>
      
      <!-- Modals -->
      <StreamingSettings ref="streamingSettingsRef" />
      <HotkeySettings ref="hotkeySettingsRef" />
      <SceneEditor ref="sceneEditorRef" />
    </div>
  </template>
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
