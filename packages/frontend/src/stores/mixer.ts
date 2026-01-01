import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useScenesStore, type TransitionConfig } from './scenes'

// ==========================================
// TYPES
// ==========================================

export interface MixerSource {
  id: string
  label: string
  type: 'camera' | 'guest' | 'screen' | 'media'
  hasVideo: boolean
  hasAudio: boolean
  muted: boolean
  audioLevel: number
  volume?: number  // 0-100
  solo?: boolean
  inGreenroom?: boolean
  connectionQuality?: number  // 0-100
}

export interface AudioMix {
  volume: number  // 0-100
  muted: boolean
  solo: boolean
}

export interface GreenroomGuest {
  id: string
  label: string
  joinedAt: string
  hasVideo: boolean
  hasAudio: boolean
}

export type MixerMode = 'simple' | 'pvw-pgm' | 'director'

// ==========================================
// STORE
// ==========================================

export const useMixerStore = defineStore('mixer', () => {
  // ==========================================
  // STATE
  // ==========================================
  
  // Core state
  const isLive = ref(false)
  const mode = ref<MixerMode>('pvw-pgm')
  
  // Scene state (PVW/PGM workflow)
  const previewSceneId = ref<string | null>(null)
  const programSceneId = ref<string | null>(null)
  
  // Legacy compatibility
  const activeScene = ref<string | null>(null)
  const currentScene = computed(() => programSceneId.value || activeScene.value)
  
  // Source state
  const sources = ref<MixerSource[]>([])
  const programSource = ref<string | null>(null)
  const previewSource = ref<string | null>(null)
  
  // Audio state
  const audioMix = ref<Record<string, AudioMix>>({})
  const masterVolume = ref(100)
  const masterMuted = ref(false)
  
  // Transition state
  const transition = ref<TransitionConfig>({
    type: 'fade',
    duration: 300
  })
  const isTransitioning = ref(false)
  
  // Greenroom state
  const greenroom = ref<GreenroomGuest[]>([])
  
  // Connection state
  const vdoConnected = ref(false)
  const lastError = ref<string | null>(null)
  
  // ==========================================
  // COMPUTED
  // ==========================================
  
  const activeSources = computed(() => 
    sources.value.filter(s => s.hasVideo || s.hasAudio)
  )
  
  const connectedSources = computed(() => 
    sources.value.filter(s => !s.inGreenroom)
  )
  
  const greenroomSources = computed(() => 
    sources.value.filter(s => s.inGreenroom)
  )
  
  const liveSourceIds = computed(() => {
    const scenesStore = useScenesStore()
    const scene = scenesStore.getScene(programSceneId.value || '')
    if (!scene) return []
    return scene.slots.filter(s => s.sourceId).map(s => s.sourceId as string)
  })
  
  const hasPreview = computed(() => previewSceneId.value !== null)
  const hasProgram = computed(() => programSceneId.value !== null)
  
  // VDO.ninja scene numbers for PVW/PGM monitors
  // Used by PreviewProgramView to build iframe URLs
  const previewVdoSceneNumber = computed(() => {
    const scenesStore = useScenesStore()
    const scene = scenesStore.getScene(previewSceneId.value || '')
    return scene?.vdoSceneNumber || null
  })
  
  const programVdoSceneNumber = computed(() => {
    const scenesStore = useScenesStore()
    const scene = scenesStore.getScene(programSceneId.value || '')
    return scene?.vdoSceneNumber || 1  // Default to scene 1 for program
  })
  
  // ==========================================
  // ACTIONS
  // ==========================================
  
  // --- Live Control ---
  
  function toggleLive() {
    isLive.value = !isLive.value
  }
  
  function setLive(live: boolean) {
    isLive.value = live
  }
  
  function setMode(newMode: MixerMode) {
    mode.value = newMode
  }
  
  // --- Scene Control (PVW/PGM) ---
  
  function setPreviewScene(sceneId: string | null) {
    previewSceneId.value = sceneId
  }
  
  function setProgramScene(sceneId: string | null) {
    programSceneId.value = sceneId
    activeScene.value = sceneId  // Legacy compatibility
  }
  
  /**
   * Take - Transition preview to program
   * This is the core broadcast operation
   */
  async function take() {
    if (!previewSceneId.value || isTransitioning.value) return
    
    isTransitioning.value = true
    
    // In a real implementation, this would trigger VDO.ninja scene transition
    // For now, we do immediate cut with simulated transition time
    
    if (transition.value.type === 'cut') {
      // Immediate cut
      programSceneId.value = previewSceneId.value
      activeScene.value = previewSceneId.value
      isTransitioning.value = false
    } else {
      // Fade or other transition - wait for duration
      await new Promise(resolve => setTimeout(resolve, transition.value.duration))
      programSceneId.value = previewSceneId.value
      activeScene.value = previewSceneId.value
      isTransitioning.value = false
    }
  }
  
  /**
   * Cut - Immediate transition (no fade)
   */
  function cut() {
    if (!previewSceneId.value) return
    programSceneId.value = previewSceneId.value
    activeScene.value = previewSceneId.value
  }
  
  /**
   * Quick switch - Set both preview and program to same scene (simple mode)
   */
  function quickSwitch(sceneId: string) {
    if (mode.value === 'simple') {
      programSceneId.value = sceneId
      activeScene.value = sceneId
    } else {
      // In PVW/PGM mode, quick switch goes to preview first
      previewSceneId.value = sceneId
    }
  }
  
  // --- Legacy Scene Control ---
  
  function setScene(sceneId: string) {
    activeScene.value = sceneId
    programSceneId.value = sceneId
  }
  
  // --- Source Control ---
  
  function setProgram(sourceId: string) {
    programSource.value = sourceId
  }
  
  function setPreview(sourceId: string) {
    previewSource.value = sourceId
  }
  
  function updateSourcesFromVdo(vdoSources: MixerSource[]) {
    sources.value = vdoSources
    
    // Initialize audio mix for new sources
    for (const source of vdoSources) {
      if (!audioMix.value[source.id]) {
        audioMix.value[source.id] = {
          volume: 100,
          muted: source.muted,
          solo: false
        }
      }
    }
  }
  
  function addSource(source: MixerSource) {
    const existing = sources.value.find(s => s.id === source.id)
    if (!existing) {
      sources.value.push(source)
      audioMix.value[source.id] = {
        volume: 100,
        muted: source.muted,
        solo: false
      }
    }
  }
  
  function removeSource(sourceId: string) {
    const index = sources.value.findIndex(s => s.id === sourceId)
    if (index !== -1) {
      sources.value.splice(index, 1)
      delete audioMix.value[sourceId]
    }
  }
  
  // --- Audio Control ---
  
  function setSourceMute(sourceId: string, muted: boolean) {
    const source = sources.value.find(s => s.id === sourceId)
    if (source) {
      source.muted = muted
    }
    if (audioMix.value[sourceId]) {
      audioMix.value[sourceId].muted = muted
    }
  }
  
  function setSourceVolume(sourceId: string, volume: number) {
    const source = sources.value.find(s => s.id === sourceId)
    if (source) {
      source.volume = volume
    }
    if (audioMix.value[sourceId]) {
      audioMix.value[sourceId].volume = volume
    }
  }
  
  function setSourceSolo(sourceId: string, solo: boolean) {
    const source = sources.value.find(s => s.id === sourceId)
    if (source) {
      source.solo = solo
    }
    if (audioMix.value[sourceId]) {
      audioMix.value[sourceId].solo = solo
    }
  }
  
  function updateAudioLevel(sourceId: string, level: number) {
    const source = sources.value.find(s => s.id === sourceId)
    if (source) {
      source.audioLevel = level
    }
  }
  
  function setMasterVolume(volume: number) {
    masterVolume.value = volume
  }
  
  function setMasterMuted(muted: boolean) {
    masterMuted.value = muted
  }
  
  // --- Transition Control ---
  
  function setTransition(config: Partial<TransitionConfig>) {
    transition.value = { ...transition.value, ...config }
  }
  
  // --- Greenroom Control ---
  
  function addToGreenroom(guest: GreenroomGuest) {
    const existing = greenroom.value.find(g => g.id === guest.id)
    if (!existing) {
      greenroom.value.push(guest)
    }
  }
  
  function removeFromGreenroom(guestId: string) {
    const index = greenroom.value.findIndex(g => g.id === guestId)
    if (index !== -1) {
      greenroom.value.splice(index, 1)
    }
  }
  
  function admitFromGreenroom(guestId: string) {
    const guest = greenroom.value.find(g => g.id === guestId)
    if (guest) {
      removeFromGreenroom(guestId)
      // Guest should appear in sources via VDO.ninja event
    }
  }
  
  // --- Connection State ---
  
  function setVdoConnected(connected: boolean) {
    vdoConnected.value = connected
  }
  
  function setLastError(error: string | null) {
    lastError.value = error
  }
  
  // ==========================================
  // RETURN
  // ==========================================
  
  return {
    // State
    isLive,
    mode,
    previewSceneId,
    programSceneId,
    activeScene,
    currentScene,
    sources,
    programSource,
    previewSource,
    audioMix,
    masterVolume,
    masterMuted,
    transition,
    isTransitioning,
    greenroom,
    vdoConnected,
    lastError,
    
    // Computed
    activeSources,
    connectedSources,
    greenroomSources,
    liveSourceIds,
    hasPreview,
    hasProgram,
    previewVdoSceneNumber,
    programVdoSceneNumber,
    
    // Actions - Live
    toggleLive,
    setLive,
    setMode,
    
    // Actions - Scene (PVW/PGM)
    setPreviewScene,
    setProgramScene,
    take,
    cut,
    quickSwitch,
    setScene,
    
    // Actions - Source
    setProgram,
    setPreview,
    updateSourcesFromVdo,
    addSource,
    removeSource,
    
    // Actions - Audio
    setSourceMute,
    setSourceVolume,
    setSourceSolo,
    updateAudioLevel,
    setMasterVolume,
    setMasterMuted,
    
    // Actions - Transition
    setTransition,
    
    // Actions - Greenroom
    addToGreenroom,
    removeFromGreenroom,
    admitFromGreenroom,
    
    // Actions - Connection
    setVdoConnected,
    setLastError
  }
})
