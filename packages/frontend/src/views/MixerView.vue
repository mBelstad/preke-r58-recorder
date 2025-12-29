<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
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

const mixerStore = useMixerStore()
const recorderStore = useRecorderStore()
const streamingStore = useStreamingStore()
const { register } = useKeyboardShortcuts()
const vdoEmbedRef = ref<InstanceType<typeof VdoNinjaEmbed> | null>(null)
const streamingSettingsRef = ref<InstanceType<typeof StreamingSettings> | null>(null)

const isLive = computed(() => mixerStore.isLive)
const enabledDestinationsCount = computed(() => streamingStore.enabledDestinations.length)

// Refresh inputs interval
let inputsRefreshInterval: number | null = null

// Track registered shortcuts for cleanup
const unregisterFns: (() => void)[] = []

onMounted(() => {
  // Fetch initial HDMI inputs status
  recorderStore.fetchInputs()
  
  // Set up interval to refresh inputs every 5 seconds
  inputsRefreshInterval = window.setInterval(() => {
    recorderStore.fetchInputs()
  }, 5000)
  
  // Register scene shortcuts (1-9)
  for (let i = 1; i <= 9; i++) {
    const unregister = register({
      key: String(i),
      description: `Switch to scene ${i}`,
      action: () => switchToScene(i),
      context: 'mixer',
    })
    unregisterFns.push(unregister)
  }
  
  // T for transition/cut
  unregisterFns.push(register({
    key: 't',
    description: 'Cut to preview (transition)',
    action: () => performTransition(),
    context: 'mixer',
  }))
  
  // A for auto-transition
  unregisterFns.push(register({
    key: 'a',
    description: 'Auto-transition with fade',
    action: () => performAutoTransition(),
    context: 'mixer',
  }))
  
  // Tab to cycle sources
  unregisterFns.push(register({
    key: 'Tab',
    description: 'Cycle through sources',
    action: () => cyclePreviewSource(),
    context: 'mixer',
  }))
  
  // G for Go Live toggle
  unregisterFns.push(register({
    key: 'g',
    description: 'Toggle Go Live',
    action: () => toggleGoLive(),
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

function switchToScene(sceneNumber: number) {
  const sceneId = `scene-${sceneNumber}`
  mixerStore.setScene(sceneId)
  
  // Send command to VDO.ninja if embedded
  if (vdoEmbedRef.value) {
    vdoEmbedRef.value.sendCommand('changeScene', { scene: sceneNumber })
  }
  
  toast.info(`Scene ${sceneNumber}`)
}

function performTransition() {
  // Instant cut to preview
  if (mixerStore.previewSource) {
    mixerStore.setProgram(mixerStore.previewSource)
    toast.info('Cut')
  }
}

function performAutoTransition() {
  // Auto-transition with fade
  if (mixerStore.previewSource) {
    // Send transition command to VDO.ninja
    if (vdoEmbedRef.value) {
      vdoEmbedRef.value.sendCommand('transition', { type: 'fade', duration: 500 })
    }
    mixerStore.setProgram(mixerStore.previewSource)
    toast.info('Fade')
  }
}

function cyclePreviewSource() {
  const sources = mixerStore.activeSources
  if (sources.length === 0) return
  
  const currentIndex = sources.findIndex(s => s.id === mixerStore.previewSource)
  const nextIndex = (currentIndex + 1) % sources.length
  mixerStore.setPreview(sources[nextIndex].id)
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
</script>

<template>
  <div class="h-full flex flex-col">
    <!-- Header -->
    <header class="flex items-center justify-between px-6 py-4 border-b border-r58-bg-tertiary bg-r58-bg-secondary">
      <div class="flex items-center gap-4">
        <div class="flex items-center gap-2">
          <span 
            class="w-3 h-3 rounded-full"
            :class="isLive ? 'bg-r58-accent-danger animate-recording' : 'bg-r58-bg-tertiary'"
          ></span>
          <span class="text-xl font-semibold text-r58-mixer">Mixer</span>
        </div>
        <span v-if="isLive" class="badge badge-danger">ON AIR</span>
        <span v-if="isLive && enabledDestinationsCount > 0" class="text-xs text-r58-text-secondary">
          Streaming to {{ enabledDestinationsCount }} platform{{ enabledDestinationsCount > 1 ? 's' : '' }}
        </span>
      </div>
      
      <div class="flex items-center gap-4">
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
          class="btn"
          :class="isLive ? 'btn-danger' : 'btn-primary'"
          @click="toggleGoLive"
        >
          {{ isLive ? 'End Session' : 'Go Live' }}
        </button>
      </div>
    </header>
    
    <!-- Main content -->
    <div class="flex-1 flex overflow-hidden">
      <!-- VDO.ninja embed -->
      <div class="flex-1 p-4">
        <VdoNinjaEmbed 
          ref="vdoEmbedRef"
          profile="director"
          class="h-full"
        />
      </div>
      
      <!-- Source panel -->
      <aside class="w-80 border-l border-r58-bg-tertiary bg-r58-bg-secondary p-4 overflow-y-auto">
        <SourcePanel />
        
        <!-- Program Output control -->
        <div class="mt-6 pt-4 border-t border-r58-bg-tertiary">
          <h3 class="text-sm font-semibold text-r58-text-secondary uppercase tracking-wide mb-3">Program Output</h3>
          <ProgramOutput />
        </div>
      </aside>
    </div>
    
    <!-- Camera Push Bar (auto-pushes HDMI sources to VDO.ninja room) -->
    <CameraPushBar />
    
    <!-- Streaming Settings Modal (rendered via Teleport) -->
    <StreamingSettings ref="streamingSettingsRef" />
  </div>
</template>

