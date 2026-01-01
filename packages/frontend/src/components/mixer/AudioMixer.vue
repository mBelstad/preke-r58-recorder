<script setup lang="ts">
/**
 * AudioMixer - Per-source volume and mute controls
 * 
 * Provides audio level meters, volume sliders, and mute/solo toggles
 * for all connected sources.
 */
import { computed } from 'vue'
import { useMixerStore, type MixerSource } from '@/stores/mixer'
import VdoNinjaEmbed from './VdoNinjaEmbed.vue'

const props = defineProps<{
  vdoEmbed?: InstanceType<typeof VdoNinjaEmbed> | null
}>()

const mixerStore = useMixerStore()

// Computed
const sources = computed(() => mixerStore.connectedSources.filter(s => s.hasAudio))

// Actions
function handleVolumeChange(source: MixerSource, volume: number) {
  mixerStore.setSourceVolume(source.id, volume)
  
  // Send to VDO.ninja (VDO uses 0-200 scale, 100 = normal)
  if (props.vdoEmbed) {
    // Convert our 0-100 scale to VDO's 0-200 scale
    const vdoVolume = Math.round(volume * 2)
    props.vdoEmbed.setVolume?.(source.id, vdoVolume)
  }
}

function toggleMute(source: MixerSource) {
  const newMuted = !source.muted
  mixerStore.setSourceMute(source.id, newMuted)
  
  // Send to VDO.ninja
  if (props.vdoEmbed) {
    props.vdoEmbed.setMute?.(source.id, newMuted)
  }
}

function toggleSolo(source: MixerSource) {
  const newSolo = !source.solo
  mixerStore.setSourceSolo(source.id, newSolo)
  
  // Send to VDO.ninja - solo mutes all others
  if (props.vdoEmbed && newSolo) {
    // VDO.ninja soloChat API
    props.vdoEmbed.sendCommand?.('soloChat', source.id)
  }
}

function toggleMasterMute() {
  mixerStore.setMasterMuted(!mixerStore.masterMuted)
}

function handleMasterVolumeChange(volume: number) {
  mixerStore.setMasterVolume(volume)
}

function getAudioLevelColor(level: number): string {
  if (level > 80) return 'bg-red-500'
  if (level > 60) return 'bg-amber-500'
  return 'bg-emerald-500'
}
</script>

<template>
  <div class="audio-mixer space-y-4" data-testid="audio-mixer">
    <!-- Master Volume -->
    <div class="master-volume p-3 bg-r58-bg-tertiary rounded-lg">
      <div class="flex items-center justify-between mb-2">
        <span class="text-xs font-medium">Master</span>
        <button 
          @click="toggleMasterMute"
          class="p-1 rounded hover:bg-r58-bg-secondary transition-colors"
          :class="{ 'text-red-400': mixerStore.masterMuted }"
        >
          <svg v-if="mixerStore.masterMuted" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2" />
          </svg>
          <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
          </svg>
        </button>
      </div>
      <input 
        type="range"
        :value="mixerStore.masterVolume"
        @input="handleMasterVolumeChange(($event.target as HTMLInputElement).valueAsNumber)"
        min="0"
        max="100"
        class="w-full h-2 bg-r58-bg-secondary rounded-lg appearance-none cursor-pointer accent-r58-accent-primary"
      />
      <div class="text-xs text-r58-text-secondary text-center mt-1">
        {{ mixerStore.masterVolume }}%
      </div>
    </div>
    
    <!-- Source Channels -->
    <div v-if="sources.length > 0" class="space-y-2">
      <div 
        v-for="source in sources" 
        :key="source.id"
        class="source-channel p-2 bg-r58-bg-tertiary/50 rounded-lg"
      >
        <div class="flex items-center gap-2 mb-2">
          <!-- Source Label -->
          <span class="text-xs font-medium truncate flex-1">{{ source.label }}</span>
          
          <!-- Solo Button -->
          <button 
            @click="toggleSolo(source)"
            class="w-6 h-6 text-xs font-bold rounded transition-colors"
            :class="source.solo 
              ? 'bg-amber-500 text-black' 
              : 'bg-r58-bg-secondary text-r58-text-secondary hover:text-r58-text-primary'"
            title="Solo"
          >
            S
          </button>
          
          <!-- Mute Button -->
          <button 
            @click="toggleMute(source)"
            class="w-6 h-6 text-xs font-bold rounded transition-colors"
            :class="source.muted 
              ? 'bg-red-500 text-white' 
              : 'bg-r58-bg-secondary text-r58-text-secondary hover:text-r58-text-primary'"
            title="Mute"
          >
            M
          </button>
        </div>
        
        <!-- Audio Level Meter -->
        <div class="h-1.5 bg-r58-bg-secondary rounded-full overflow-hidden mb-2">
          <div 
            class="h-full transition-all duration-75 rounded-full"
            :class="source.muted ? 'bg-r58-bg-tertiary' : getAudioLevelColor(source.audioLevel)"
            :style="{ width: `${source.audioLevel}%` }"
          ></div>
        </div>
        
        <!-- Volume Slider -->
        <input 
          type="range"
          :value="source.volume || 100"
          @input="handleVolumeChange(source, ($event.target as HTMLInputElement).valueAsNumber)"
          min="0"
          max="100"
          :disabled="source.muted"
          class="w-full h-1.5 bg-r58-bg-secondary rounded-lg appearance-none cursor-pointer accent-r58-accent-primary disabled:opacity-50"
        />
      </div>
    </div>
    
    <!-- Empty State -->
    <div v-else class="text-center py-4 text-r58-text-secondary">
      <svg class="w-6 h-6 mx-auto mb-2 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
      </svg>
      <p class="text-xs">No audio sources</p>
    </div>
  </div>
</template>

<style scoped>
input[type="range"]::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 12px;
  height: 12px;
  background: var(--r58-accent-primary);
  border-radius: 50%;
  cursor: pointer;
}

input[type="range"]::-moz-range-thumb {
  width: 12px;
  height: 12px;
  background: var(--r58-accent-primary);
  border-radius: 50%;
  cursor: pointer;
  border: none;
}
</style>

