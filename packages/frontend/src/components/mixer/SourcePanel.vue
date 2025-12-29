<script setup lang="ts">
/**
 * SourcePanel - Displays sources from VDO.ninja
 * 
 * This is a read-only status panel. Full source/guest management
 * is handled by the embedded mixer.html (VDO.ninja's real mixer).
 */
import { computed } from 'vue'
import { useMixerStore, type MixerSource } from '@/stores/mixer'
import { useRecorderStore } from '@/stores/recorder'

// Props from parent
const props = defineProps<{
  vdoEmbed?: {
    setMute: (id: string, muted: boolean) => void
    toggleMute: (id: string) => void
    sendCommand: (action: string, target?: string, value?: unknown) => void
  }
}>()

const mixerStore = useMixerStore()
const recorderStore = useRecorderStore()

// VDO.ninja sources from the mixer store
const vdoSources = computed(() => mixerStore.sources)

// HDMI camera sources from the recorder store (as fallback)
const hdmiSources = computed((): MixerSource[] => {
  return recorderStore.inputs
    .filter(input => input.hasSignal)
    .map(input => ({
      id: input.id,
      label: input.label,
      type: 'camera' as const,
      hasVideo: true,
      hasAudio: true,
      muted: false,
      audioLevel: 0,
    }))
})

// Combine sources: use VDO.ninja sources if available, otherwise show HDMI cameras
const sources = computed(() => {
  if (vdoSources.value.length > 0) {
    return vdoSources.value
  }
  return hdmiSources.value
})

// Show hint when using HDMI fallback
const usingHdmiFallback = computed(() => vdoSources.value.length === 0 && hdmiSources.value.length > 0)

/**
 * Toggle mute using VERIFIED VDO.ninja API
 * API: action: "mic", target: streamID, value: "toggle"
 */
function toggleMute(source: MixerSource) {
  if (props.vdoEmbed) {
    props.vdoEmbed.toggleMute(source.id)
  }
  // Also update local state
  mixerStore.setSourceMute(source.id, !source.muted)
}
</script>

<template>
  <div class="space-y-4" data-testid="source-panel">
    <!-- Sources Header -->
    <h3 class="text-sm font-semibold text-r58-text-secondary uppercase tracking-wide" data-testid="sources-heading">
      Sources
      <span v-if="sources.length > 0" class="ml-2 text-r58-accent-primary">({{ sources.length }})</span>
    </h3>
    
    <!-- HDMI fallback hint -->
    <div v-if="usingHdmiFallback" class="px-3 py-2 bg-amber-500/10 border border-amber-500/30 rounded-lg text-xs text-amber-400">
      Showing HDMI cameras. VDO.ninja sources will appear when guests join.
    </div>
    
    <!-- Empty state -->
    <div v-if="sources.length === 0" class="text-center py-6 text-r58-text-secondary">
      <svg class="w-8 h-8 mx-auto mb-2 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
      </svg>
      <p class="text-sm">No sources connected</p>
      <p class="text-xs mt-1 opacity-75">Connect HDMI sources or have guests join</p>
    </div>
    
    <!-- Source list -->
    <div v-else class="space-y-2">
      <div
        v-for="source in sources"
        :key="source.id"
        class="flex items-center justify-between p-3 rounded-lg bg-r58-bg-tertiary hover:bg-r58-bg-tertiary/80 transition-colors"
      >
        <div class="flex items-center gap-3 min-w-0">
          <!-- Source icon -->
          <div 
            class="w-8 h-8 rounded bg-r58-bg-primary flex items-center justify-center flex-shrink-0"
            :class="{ 'ring-2 ring-r58-accent-primary': mixerStore.programSource === source.id }"
          >
            <svg v-if="source.type === 'camera'" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
            </svg>
            <svg v-else-if="source.type === 'guest'" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/>
            </svg>
            <svg v-else-if="source.type === 'screen'" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
            </svg>
            <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 4v16M17 4v16M3 8h4m10 0h4M3 12h18M3 16h4m10 0h4M4 20h16a1 1 0 001-1V5a1 1 0 00-1-1H4a1 1 0 00-1 1v14a1 1 0 001 1z"/>
            </svg>
          </div>
          
          <!-- Source info -->
          <div class="min-w-0">
            <p class="font-medium text-sm truncate">{{ source.label }}</p>
            <p class="text-xs text-r58-text-secondary capitalize">{{ source.type }}</p>
          </div>
        </div>
        
        <div class="flex items-center gap-2 flex-shrink-0">
          <!-- Audio level indicator -->
          <div v-if="source.hasAudio" class="w-12 h-1.5 bg-r58-bg-primary rounded-full overflow-hidden">
            <div 
              class="h-full rounded-full transition-all duration-100"
              :class="source.muted ? 'bg-r58-accent-danger' : 'bg-r58-accent-success'"
              :style="{ width: `${source.audioLevel || 0}%` }"
            ></div>
          </div>
          
          <!-- Mute button (uses VERIFIED mic API) -->
          <button
            v-if="source.hasAudio"
            @click="toggleMute(source)"
            class="p-1.5 rounded hover:bg-r58-bg-primary transition-colors"
            :class="{ 'text-r58-accent-danger': source.muted }"
            :data-testid="`mute-button-${source.id}`"
            :title="source.muted ? 'Unmute ' + source.label : 'Mute ' + source.label"
          >
            <svg v-if="source.muted" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z"/>
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2"/>
            </svg>
            <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z"/>
            </svg>
          </button>
        </div>
      </div>
    </div>
    
    <!-- Hint about full management -->
    <p class="text-xs text-r58-text-secondary text-center pt-2">
      Full guest/source management available in the mixer above
    </p>
  </div>
</template>
