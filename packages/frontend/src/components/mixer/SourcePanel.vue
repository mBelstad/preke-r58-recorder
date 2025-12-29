<script setup lang="ts">
import { computed } from 'vue'
import { useMixerStore, type MixerSource } from '@/stores/mixer'
import { useRecorderStore } from '@/stores/recorder'

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

const activeSources = computed(() => sources.value.filter(s => s.hasVideo || s.hasAudio))

// Show hint when using HDMI fallback
const usingHdmiFallback = computed(() => vdoSources.value.length === 0 && hdmiSources.value.length > 0)
</script>

<template>
  <div class="space-y-6">
    <!-- Sources -->
    <div class="card">
      <h3 class="text-sm font-semibold text-r58-text-secondary uppercase tracking-wide mb-3">Sources</h3>
      
      <!-- HDMI fallback hint -->
      <div v-if="usingHdmiFallback" class="mb-3 px-3 py-2 bg-amber-500/10 border border-amber-500/30 rounded-lg text-xs text-amber-400">
        Showing HDMI cameras. VDO.ninja sources will appear when guests join.
      </div>
      
      <div v-if="sources.length === 0" class="text-center py-8 text-r58-text-secondary">
        <p>No sources connected</p>
        <p class="text-sm mt-1">Connect HDMI sources or have guests join the room</p>
      </div>
      
      <div v-else class="space-y-2">
        <div
          v-for="source in sources"
          :key="source.id"
          class="flex items-center justify-between p-3 rounded-lg bg-r58-bg-tertiary"
        >
          <div class="flex items-center gap-3">
            <div 
              class="w-10 h-10 rounded bg-r58-bg-primary flex items-center justify-center"
              :class="{ 'ring-2 ring-r58-accent-primary': mixerStore.programSource === source.id }"
            >
              <svg v-if="source.type === 'camera'" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
              </svg>
              <svg v-else-if="source.type === 'guest'" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/>
              </svg>
              <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
              </svg>
            </div>
            
            <div>
              <p class="font-medium">{{ source.label }}</p>
              <p class="text-xs text-r58-text-secondary capitalize">{{ source.type }}</p>
            </div>
          </div>
          
          <div class="flex items-center gap-2">
            <!-- Audio level indicator -->
            <div class="w-16 h-2 bg-r58-bg-primary rounded-full overflow-hidden">
              <div 
                class="h-full bg-r58-accent-success rounded-full transition-all duration-100"
                :style="{ width: `${source.audioLevel}%` }"
              ></div>
            </div>
            
            <!-- Mute button -->
            <button
              @click="mixerStore.setSourceMute(source.id, !source.muted)"
              class="p-2 rounded hover:bg-r58-bg-primary transition-colors"
              :class="{ 'text-r58-accent-danger': source.muted }"
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
    </div>
    
    <!-- Quick actions -->
    <div class="card">
      <h3 class="text-sm font-semibold text-r58-text-secondary uppercase tracking-wide mb-3">Guest Invite</h3>
      <button class="btn w-full justify-center">
        Generate Invite Link
      </button>
    </div>
    
    <!-- Scene buttons -->
    <div class="card">
      <h3 class="text-sm font-semibold text-r58-text-secondary uppercase tracking-wide mb-3">Scenes</h3>
      <div class="grid grid-cols-2 gap-2">
        <button 
          @click="mixerStore.setScene('scene1')"
          class="btn"
          :class="{ 'btn-primary': mixerStore.activeScene === 'scene1' }"
        >
          Scene 1
        </button>
        <button 
          @click="mixerStore.setScene('scene2')"
          class="btn"
          :class="{ 'btn-primary': mixerStore.activeScene === 'scene2' }"
        >
          Scene 2
        </button>
        <button 
          @click="mixerStore.setScene('pip')"
          class="btn"
          :class="{ 'btn-primary': mixerStore.activeScene === 'pip' }"
        >
          PiP
        </button>
        <button 
          @click="mixerStore.setScene('grid')"
          class="btn"
          :class="{ 'btn-primary': mixerStore.activeScene === 'grid' }"
        >
          Grid
        </button>
      </div>
    </div>
  </div>
</template>

