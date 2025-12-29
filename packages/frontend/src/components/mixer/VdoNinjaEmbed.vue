<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { buildVdoUrl } from '@/lib/vdoninja'
import { useVdoNinja } from '@/composables/useVdoNinja'
import { useMixerStore } from '@/stores/mixer'

const props = defineProps<{
  profile: 'director' | 'scene' | 'multiview'
  sources?: string[]
}>()

const iframeRef = ref<HTMLIFrameElement | null>(null)
const mixerStore = useMixerStore()

const vdo = useVdoNinja(iframeRef)

const { 
  isReady, 
  sources: vdoSources, 
  setScene, 
  setMute, 
  setVolume,
  sendCommand,
  isRecording,
  connectionState,
  startRecording,
  stopRecording,
  kickGuest,
  requestScreenShare,
  acceptGuest,
  removeFromScene,
  getEventHistory,
  getEventStats,
} = vdo

// Build iframe URL
const iframeSrc = computed(() => {
  const vars: Record<string, string> = {}
  
  if (props.sources) {
    vars.source_ids = props.sources.join(',')
  }
  
  return buildVdoUrl(props.profile, vars)
})

// Sync VDO.ninja state to our store
watch(vdoSources, (newSources) => {
  mixerStore.updateSourcesFromVdo(Array.from(newSources.values()))
}, { deep: true })

// Expose controls to parent
defineExpose({
  isReady,
  isRecording,
  connectionState,
  setScene,
  setMute,
  setVolume,
  sendCommand,
  startRecording,
  stopRecording,
  kickGuest,
  requestScreenShare,
  acceptGuest,
  removeFromScene,
  getEventHistory,
  getEventStats,
})
</script>

<template>
  <div class="vdo-embed-container relative w-full h-full bg-black rounded-lg overflow-hidden" data-testid="vdo-embed-container">
    <!-- Loading state -->
    <div 
      v-if="!isReady" 
      class="absolute inset-0 flex items-center justify-center bg-r58-bg-secondary z-10"
      data-testid="vdo-loading"
    >
      <div class="text-center">
        <div class="animate-spin w-8 h-8 border-2 border-r58-accent-primary border-t-transparent rounded-full mx-auto mb-4"></div>
        <p class="text-r58-text-secondary">Connecting to VDO.ninja...</p>
        <p class="text-xs text-r58-text-secondary mt-2">Local mixer on R58</p>
      </div>
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
      title="VDO.ninja Mixer"
    ></iframe>
  </div>
</template>

