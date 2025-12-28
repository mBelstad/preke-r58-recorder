import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface MixerSource {
  id: string
  label: string
  type: 'camera' | 'guest' | 'screen' | 'media'
  hasVideo: boolean
  hasAudio: boolean
  muted: boolean
  audioLevel: number
}

export const useMixerStore = defineStore('mixer', () => {
  // State
  const isLive = ref(false)
  const activeScene = ref<string | null>(null)
  const programSource = ref<string | null>(null)
  const previewSource = ref<string | null>(null)
  const sources = ref<MixerSource[]>([])

  // Computed
  const activeSources = computed(() => sources.value.filter(s => s.hasVideo || s.hasAudio))

  // Actions
  function toggleLive() {
    isLive.value = !isLive.value
  }

  function setScene(sceneId: string) {
    activeScene.value = sceneId
  }

  function setProgram(sourceId: string) {
    programSource.value = sourceId
  }

  function setPreview(sourceId: string) {
    previewSource.value = sourceId
  }

  function updateSourcesFromVdo(vdoSources: MixerSource[]) {
    sources.value = vdoSources
  }

  function setSourceMute(sourceId: string, muted: boolean) {
    const source = sources.value.find(s => s.id === sourceId)
    if (source) {
      source.muted = muted
    }
  }

  function updateAudioLevel(sourceId: string, level: number) {
    const source = sources.value.find(s => s.id === sourceId)
    if (source) {
      source.audioLevel = level
    }
  }

  return {
    // State
    isLive,
    activeScene,
    programSource,
    previewSource,
    sources,
    
    // Computed
    activeSources,
    
    // Actions
    toggleLive,
    setScene,
    setProgram,
    setPreview,
    updateSourcesFromVdo,
    setSourceMute,
    updateAudioLevel,
  }
})

