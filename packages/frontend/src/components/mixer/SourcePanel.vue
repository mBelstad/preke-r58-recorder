<script setup lang="ts">
/**
 * SourcePanel - Enhanced source management panel
 * 
 * Displays all available sources (HDMI cameras, VDO.ninja guests, screens)
 * with controls for muting, volume, and adding to scenes.
 */
import { computed, ref } from 'vue'
import { useMixerStore, type MixerSource } from '@/stores/mixer'
import { useScenesStore } from '@/stores/scenes'
import { useRecorderStore } from '@/stores/recorder'
import VdoNinjaEmbed from './VdoNinjaEmbed.vue'

// Custom names stored in localStorage
const CUSTOM_NAMES_KEY = 'preke-source-names'

function getCustomNames(): Record<string, string> {
  try {
    const stored = localStorage.getItem(CUSTOM_NAMES_KEY)
    return stored ? JSON.parse(stored) : {}
  } catch {
    return {}
  }
}

function setCustomName(sourceId: string, name: string): void {
  const names = getCustomNames()
  names[sourceId] = name
  localStorage.setItem(CUSTOM_NAMES_KEY, JSON.stringify(names))
}

const customNames = ref<Record<string, string>>(getCustomNames())
const editingSource = ref<string | null>(null)
const editName = ref('')

// Props
const props = defineProps<{
  vdoEmbed?: InstanceType<typeof VdoNinjaEmbed> | null
  controller?: {
    addSourceToScene: (sourceId: string, slotIndex?: number) => void
    setMute: (sourceId: string, muted: boolean) => void
    toggleMute: (sourceId: string) => void
  }
}>()

// Stores
const mixerStore = useMixerStore()
const scenesStore = useScenesStore()
const recorderStore = useRecorderStore()

// Camera label mapping
const cameraLabels: Record<string, { name: string; subtitle: string }> = {
  'cam0': { name: 'HDMI 1', subtitle: 'Connected to device' },
  'cam1': { name: 'HDMI 2', subtitle: 'Connected to device' },
  'cam2': { name: 'HDMI 3', subtitle: 'Connected to device' },
  'cam3': { name: 'HDMI 4', subtitle: 'Connected to device' },
}

// VDO.ninja sources from the mixer store with proper names
const vdoSources = computed(() => {
  return mixerStore.sources.map(source => {
    let displayLabel = source.label
    let subtitle = 'VDO.ninja'
    
    const hdmiMatch = source.id.match(/cam(\d+)/i) || source.id.match(/hdmi[_-]?(\d+)/i)
    if (hdmiMatch) {
      const camNum = parseInt(hdmiMatch[1]) + 1
      displayLabel = `HDMI ${camNum}`
      subtitle = 'Connected to device'
    } else if (source.type === 'guest') {
      subtitle = 'Remote guest'
      if (!source.label || source.label.length > 20 || source.label.match(/^[a-z0-9]{8,}$/i)) {
        displayLabel = 'Guest'
      }
    } else if (source.type === 'screen') {
      subtitle = 'Screen share'
    }
    
    return { ...source, label: displayLabel, subtitle }
  })
})

// HDMI sources from recorder (fallback)
const hdmiSources = computed((): (MixerSource & { subtitle?: string })[] => {
  return recorderStore.inputs
    .filter(input => input.hasSignal)
    .map(input => {
      const labelInfo = cameraLabels[input.id] || { name: input.label, subtitle: 'HDMI Input' }
      return {
        id: input.id,
        label: labelInfo.name,
        subtitle: labelInfo.subtitle,
        type: 'camera' as const,
        hasVideo: true,
        hasAudio: true,
        muted: false,
        audioLevel: 0,
      }
    })
})

// Combined sources - merge both VDO and HDMI sources
// This ensures HDMI cameras always appear, even if VDO.ninja detection is delayed
const sources = computed(() => {
  const sourceMap = new Map<string, MixerSource & { subtitle?: string }>()
  
  // First, add HDMI sources (from recorder API - always reliable)
  for (const source of hdmiSources.value) {
    sourceMap.set(source.id, source)
  }
  
  // Then, add/overlay VDO.ninja sources (may have more info like audio levels)
  for (const source of vdoSources.value) {
    const existing = sourceMap.get(source.id)
    if (existing) {
      // Merge VDO info into existing HDMI source
      sourceMap.set(source.id, { ...existing, ...source, subtitle: source.subtitle || existing.subtitle })
    } else {
      // New source from VDO (guest, screen share, etc.)
      sourceMap.set(source.id, source)
    }
  }
  
  return Array.from(sourceMap.values())
})

const usingHdmiFallback = computed(() => vdoSources.value.length === 0 && hdmiSources.value.length > 0)

// Check if source is in current preview scene
function isInPreviewScene(sourceId: string): boolean {
  const scene = scenesStore.getScene(mixerStore.previewSceneId || '')
  return scene?.slots.some(s => s.sourceId === sourceId) || false
}

// Check if source is in program scene
function isInProgramScene(sourceId: string): boolean {
  return mixerStore.liveSourceIds.includes(sourceId)
}

// Actions
function toggleMute(source: MixerSource) {
  // Use controller if available (syncs with VDO.ninja)
  if (props.controller) {
    props.controller.toggleMute(source.id)
  } else if (props.vdoEmbed) {
    props.vdoEmbed.toggleMute?.(source.id)
    mixerStore.setSourceMute(source.id, !source.muted)
  } else {
  mixerStore.setSourceMute(source.id, !source.muted)
}
}

function addToPreviewScene(source: MixerSource) {
  const previewScene = scenesStore.getScene(mixerStore.previewSceneId || '')
  if (!previewScene) return
  
  // Use controller if available (syncs with VDO.ninja)
  if (props.controller) {
    props.controller.addSourceToScene(source.id)
  }
  
  // Also update our scene store
  const emptySlot = previewScene.slots.find(s => !s.sourceId)
  if (emptySlot) {
    scenesStore.assignSourceToSlot(previewScene.id, emptySlot.id, source.id)
  }
}

function getDisplayName(source: MixerSource & { subtitle?: string }): string {
  return customNames.value[source.id] || source.label
}

function startRename(source: MixerSource) {
  editingSource.value = source.id
  editName.value = customNames.value[source.id] || source.label
}

function saveRename() {
  if (editingSource.value && editName.value.trim()) {
    setCustomName(editingSource.value, editName.value.trim())
    customNames.value = getCustomNames()
  }
  editingSource.value = null
}

function cancelRename() {
  editingSource.value = null
  editName.value = ''
}

function getSourceIcon(source: MixerSource): string {
  switch (source.type) {
    case 'camera': return 'camera'
    case 'guest': return 'user'
    case 'screen': return 'screen'
    default: return 'media'
  }
}
</script>

<template>
  <div class="source-panel space-y-4" data-testid="source-panel">
    <!-- HDMI fallback hint -->
    <div v-if="usingHdmiFallback" class="px-3 py-2 bg-amber-500/10 border border-amber-500/30 rounded-lg text-xs text-amber-400">
      Showing HDMI cameras. VDO.ninja sources will appear when connected.
    </div>
    
    <!-- Empty state -->
    <div v-if="sources.length === 0" class="text-center py-6 text-preke-text-dim">
      <svg class="w-8 h-8 mx-auto mb-2 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
      </svg>
      <p class="text-sm">No sources connected</p>
      <p class="text-xs mt-1 opacity-75">Connect HDMI or invite guests</p>
    </div>
    
    <!-- Source list -->
    <div v-else class="space-y-2">
      <div
        v-for="source in sources"
        :key="source.id"
        class="source-card p-3 rounded-lg transition-all"
        :class="[
          isInProgramScene(source.id) 
            ? 'bg-red-500/10 border border-red-500/30' 
            : isInPreviewScene(source.id)
              ? 'bg-amber-500/10 border border-amber-500/30'
              : 'bg-preke-bg-surface hover:bg-preke-bg-surface/80 border border-transparent'
        ]"
      >
        <div class="flex items-center gap-3">
          <!-- Source icon -->
          <div 
            class="w-10 h-10 rounded-lg bg-preke-bg-base flex items-center justify-center flex-shrink-0"
            :class="{ 
              'ring-2 ring-red-500': isInProgramScene(source.id),
              'ring-2 ring-amber-500': isInPreviewScene(source.id) && !isInProgramScene(source.id)
            }"
          >
            <svg v-if="source.type === 'camera'" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
            </svg>
            <svg v-else-if="source.type === 'guest'" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/>
            </svg>
            <svg v-else-if="source.type === 'screen'" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
            </svg>
            <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 4v16M17 4v16M3 8h4m10 0h4M3 12h18M3 16h4m10 0h4M4 20h16a1 1 0 001-1V5a1 1 0 00-1-1H4a1 1 0 00-1 1v14a1 1 0 001 1z"/>
            </svg>
          </div>
          
          <!-- Source info -->
          <div class="flex-1 min-w-0">
            <!-- Editing mode -->
            <div v-if="editingSource === source.id" class="flex items-center gap-1">
              <input 
                v-model="editName"
                @keyup.enter="saveRename"
                @keyup.escape="cancelRename"
                @blur="saveRename"
                class="input text-sm py-0.5 px-1 w-full"
                autofocus
              />
            </div>
            <!-- Display mode -->
            <p 
              v-else
              @dblclick="startRename(source)"
              class="font-medium text-sm truncate cursor-pointer hover:text-preke-gold"
              title="Double-click to rename"
            >
              {{ getDisplayName(source) }}
            </p>
            <div class="flex items-center gap-2 text-xs text-preke-text-dim">
              <span>{{ source.subtitle }}</span>
              <span v-if="isInProgramScene(source.id)" class="text-red-400 font-bold">LIVE</span>
              <span v-else-if="isInPreviewScene(source.id)" class="text-amber-400">PVW</span>
        </div>
          </div>
          
          <!-- Controls -->
          <div class="flex items-center gap-1 flex-shrink-0">
            <!-- Add to scene button -->
            <button
              v-if="mixerStore.previewSceneId && !isInPreviewScene(source.id)"
              @click="addToPreviewScene(source)"
              class="p-1.5 rounded hover:bg-preke-bg-base transition-colors text-preke-text-dim hover:text-preke-gold"
              title="Add to preview scene"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
              </svg>
            </button>
            
            <!-- Mute button -->
          <button
            v-if="source.hasAudio"
            @click="toggleMute(source)"
              class="p-1.5 rounded transition-colors"
              :class="source.muted 
                ? 'bg-red-500/20 text-red-400' 
                : 'hover:bg-preke-bg-base text-preke-text-dim'"
              :title="source.muted ? 'Unmute' : 'Mute'"
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
        
        <!-- Audio level meter -->
        <div v-if="source.hasAudio" class="mt-2">
          <div class="h-1 bg-preke-bg-base rounded-full overflow-hidden">
            <div 
              class="h-full transition-all duration-75 rounded-full"
              :class="source.muted ? 'bg-preke-bg-surface' : (source.audioLevel > 80 ? 'bg-red-500' : source.audioLevel > 60 ? 'bg-amber-500' : 'bg-emerald-500')"
              :style="{ width: `${source.audioLevel || 0}%` }"
            ></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.source-card {
  user-select: none;
}
</style>
