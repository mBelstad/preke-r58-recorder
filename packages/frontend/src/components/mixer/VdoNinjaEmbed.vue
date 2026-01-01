<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { buildVdoUrl, type embedProfiles } from '@/lib/vdoninja'
import { useVdoNinja } from '@/composables/useVdoNinja'
import { useMixerStore } from '@/stores/mixer'

const props = defineProps<{
  profile: keyof typeof embedProfiles
  sources?: string[]
  room?: string
  password?: string
}>()

const iframeRef = ref<HTMLIFrameElement | null>(null)
const mixerStore = useMixerStore()

const vdo = useVdoNinja(iframeRef)

const { 
  isReady, 
  sources: vdoSources, 
  sourcesVersion: vdoSourcesVersion,  // For triggering watchers
  addToScene,
  removeFromScene, 
  setMute, 
  toggleMute,
  setVolume,
  sendCommand,
  sendDomCommand,
  isRecording,
  connectionState,
  lastError,
  startRecording,
  stopRecording,
  kickGuest,
  toggleScreenShare,
  setLayout,
  setProgram,
  addSource,
  removeSource,
  getEventHistory,
  getEventStats,
} = vdo

// Build iframe URL
const iframeSrc = computed(() => {
  const vars: Record<string, string> = {}
  
  if (props.sources) {
    vars.source_ids = props.sources.join(',')
  }
  
  if (props.room) {
    vars.room = props.room
  }
  
  if (props.password) {
    vars.password = props.password
  }
  
  return buildVdoUrl(props.profile, vars)
})

// Whether we're using the real mixer.html
const isMixerEmbed = computed(() => props.profile === 'mixer')

// Sync VDO.ninja state to our store
watch(vdoSources, (newSources) => {
  mixerStore.updateSourcesFromVdo(Array.from(newSources.values()))
}, { deep: true })

// Expose controls to parent
defineExpose({
  isReady,
  isRecording,
  connectionState,
  lastError,
  
  // Sources state - needed for auto-add functionality
  sources: vdoSources,
  sourcesVersion: vdoSourcesVersion,  // For triggering watchers on Map mutations
  
  // Scene/layout control (VERIFIED API)
  addToScene,
  removeFromScene,
  setLayout,
  setProgram,
  addSource,
  removeSource,
  
  // Audio control (VERIFIED API)
  setMute,
  toggleMute,
  setVolume,
  
  // Recording (VERIFIED API)
  startRecording,
  stopRecording,
  
  // Guest control (VERIFIED API)
  kickGuest,
  toggleScreenShare,
  
  // Low-level
  sendCommand,
  sendDomCommand,
  
  // Debug
  getEventHistory,
  getEventStats,
})
</script>

<template>
  <div 
    class="vdo-embed-container relative w-full h-full bg-black rounded-lg overflow-hidden" 
    :class="{ 'mixer-mode': isMixerEmbed }"
    data-testid="vdo-embed-container"
  >
    <!-- Loading state -->
    <div 
      v-if="!isReady" 
      class="absolute inset-0 flex items-center justify-center bg-r58-bg-secondary z-10"
      data-testid="vdo-loading"
    >
      <div class="text-center">
        <div class="animate-spin w-8 h-8 border-2 border-r58-accent-primary border-t-transparent rounded-full mx-auto mb-4"></div>
        <p class="text-r58-text-secondary">Connecting to VDO.ninja...</p>
        <p class="text-xs text-r58-text-secondary mt-2">
          {{ isMixerEmbed ? 'Loading mixer controls...' : 'Local mixer on R58' }}
        </p>
      </div>
    </div>
    
    <!-- Error state -->
    <div 
      v-if="lastError" 
      class="absolute bottom-4 left-4 right-4 bg-red-500/90 text-white px-4 py-2 rounded-lg text-sm z-20"
    >
      <strong>Error:</strong> {{ lastError }}
    </div>
    
    <!-- VDO.ninja iframe -->
    <iframe
      ref="iframeRef"
      :src="iframeSrc"
      class="w-full h-full border-0"
      :class="{ 'opacity-0': !isReady }"
      allow="camera; microphone; display-capture; autoplay; clipboard-write"
      allowfullscreen
      data-testid="vdo-iframe"
      :title="isMixerEmbed ? 'VDO.ninja Mixer' : 'VDO.ninja'"
    ></iframe>
  </div>
</template>

<style scoped>
/* Mixer mode - full height for embedded mixer.html */
.mixer-mode {
  min-height: 500px;
}
</style>
