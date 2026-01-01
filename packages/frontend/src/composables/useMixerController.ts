/**
 * Mixer Controller - Bridges mixer store with VDO.ninja
 * 
 * This composable connects the local mixer state (scenes, audio, sources)
 * with the VDO.ninja iframe for real broadcast control.
 * 
 * Features:
 * - Scene switching via VDO.ninja layout API
 * - Audio control (mute, volume, solo)
 * - Source management (add to scene, remove, kick)
 * - Recording control
 * - Greenroom management
 */
import { ref, watch, onMounted, type Ref } from 'vue'
import { useMixerStore, type MixerSource } from '@/stores/mixer'
import { useScenesStore, type Scene, type SceneSlot, VdoLayoutPreset } from '@/stores/scenes'
import { useRecorderStore } from '@/stores/recorder'
import type VdoNinjaEmbed from '@/components/mixer/VdoNinjaEmbed.vue'
import type { VdoLayoutSlot } from '@/composables/useVdoNinja'

// ==========================================
// TYPES
// ==========================================

export interface MixerController {
  // State
  isConnected: Ref<boolean>
  isInitialized: Ref<boolean>
  
  // Scene actions
  applySceneToVdo: (scene: Scene) => void
  switchToScene: (sceneId: string) => void
  takeToProgram: () => void
  cutToProgram: () => void
  
  // Source actions
  addSourceToScene: (sourceId: string, slotIndex?: number) => void
  removeSourceFromScene: (sourceId: string) => void
  setSourceAsProgram: (sourceId: string) => void
  
  // Audio actions
  setMute: (sourceId: string, muted: boolean) => void
  toggleMute: (sourceId: string) => void
  setVolume: (sourceId: string, volume: number) => void
  setSolo: (sourceId: string, solo: boolean) => void
  
  // Guest actions
  kickGuest: (sourceId: string) => void
  sendMessage: (sourceId: string, message: string) => void
  admitFromGreenroom: (sourceId: string) => void
  
  // Recording
  startRecording: () => void
  stopRecording: () => void
  
  // Director
  sendDirectorCommand: (action: string, target?: string, value?: unknown) => void
}

// ==========================================
// COMPOSABLE
// ==========================================

export function useMixerController(
  vdoEmbedRef: Ref<InstanceType<typeof VdoNinjaEmbed> | null | undefined>
): MixerController {
  const mixerStore = useMixerStore()
  const scenesStore = useScenesStore()
  const recorderStore = useRecorderStore()
  
  // State
  const isConnected = ref(false)
  const isInitialized = ref(false)
  const lastAppliedSceneId = ref<string | null>(null)
  
  // ==========================================
  // INTERNAL HELPERS
  // ==========================================
  
  /**
   * Get the VDO.ninja embed instance
   */
  function getVdo() {
    return vdoEmbedRef.value
  }
  
  /**
   * Check if VDO.ninja is ready
   * Uses multiple fallback checks for reliability
   */
  function isVdoReady(): boolean {
    const vdo = getVdo()
    if (!vdo) return false
    
    // Check isReady ref from useVdoNinja
    if (vdo.isReady?.value === true) return true
    
    // Check connectionState for 'connected'
    if (vdo.connectionState?.value === 'connected') return true
    
    // Fallback: check if the iframe element exists
    // The 5s timeout in useVdoNinja should have marked it ready
    return isInitialized.value
  }
  
  /**
   * Get source IDs that should be visible in a scene
   */
  function getSceneSourceIds(scene: Scene): string[] {
    return scene.slots
      .filter(slot => slot.sourceId)
      .map(slot => slot.sourceId as string)
  }
  
  // ==========================================
  // SCENE CONTROL
  // ==========================================
  
  /**
   * Apply a scene's layout and sources to VDO.ninja
   * Uses the scene's vdoSceneNumber and layoutPreset directly
   */
  function applySceneToVdo(scene: Scene): void {
    const vdo = getVdo()
    if (!vdo) {
      console.warn('[MixerController] VDO.ninja embed not available')
      return
    }
    
    // Allow applying even if not fully ready - VDO.ninja will queue commands
    if (!isVdoReady()) {
      console.log('[MixerController] VDO.ninja may not be fully ready, attempting anyway')
    }
    
    console.log('[MixerController] Applying scene to VDO:', scene.name, 
      '- VDO Scene:', scene.vdoSceneNumber, 
      '- Layout:', VdoLayoutPreset[scene.layoutPreset] || scene.layoutPreset)
    
    try {
      // Apply layout preset from scene definition
      // VDO.ninja layout presets: 0=auto, 1=solo, 2=split, 3=pip, etc.
      vdo.setLayout(scene.layoutPreset)
      
      // Get source IDs from scene slots
      const sourceIds = getSceneSourceIds(scene)
      
      // Add each source to the VDO.ninja scene
      // Use scene.vdoSceneNumber for proper scene assignment
      for (const sourceId of sourceIds) {
        vdo.addToScene(sourceId, scene.vdoSceneNumber)
      }
      
      lastAppliedSceneId.value = scene.id
      
      console.log('[MixerController] Scene applied successfully:', scene.name,
        '- Sources:', sourceIds.length)
    } catch (error) {
      console.error('[MixerController] Error applying scene to VDO:', error)
    }
  }
  
  /**
   * Switch to a scene by ID
   */
  function switchToScene(sceneId: string): void {
    const scene = scenesStore.getScene(sceneId)
    if (scene) {
      applySceneToVdo(scene)
    }
  }
  
  /**
   * Take - transition preview to program with VDO.ninja
   */
  async function takeToProgram(): Promise<void> {
    const previewId = mixerStore.previewSceneId
    if (!previewId) return
    
    const scene = scenesStore.getScene(previewId)
    if (!scene) return
    
    // Apply the scene to VDO.ninja
    applySceneToVdo(scene)
    
    // Update store (handles transition timing)
    await mixerStore.take()
  }
  
  /**
   * Cut - immediate switch to preview
   */
  function cutToProgram(): void {
    const previewId = mixerStore.previewSceneId
    if (!previewId) return
    
    const scene = scenesStore.getScene(previewId)
    if (!scene) return
    
    // Apply immediately
    applySceneToVdo(scene)
    
    // Update store
    mixerStore.cut()
  }
  
  // ==========================================
  // SOURCE CONTROL
  // ==========================================
  
  /**
   * Add a source to the current preview scene
   */
  function addSourceToScene(sourceId: string, slotIndex?: number): void {
    const vdo = getVdo()
    if (!vdo || !isVdoReady()) return
    
    // Get the current preview scene
    const previewScene = mixerStore.previewSceneId 
      ? scenesStore.getScene(mixerStore.previewSceneId) 
      : null
    
    // Add to VDO.ninja using the scene's vdoSceneNumber (or default to 1)
    const vdoSceneNumber = previewScene?.vdoSceneNumber || 1
    vdo.addToScene(sourceId, vdoSceneNumber)
    
    // Also update our scene store if we have a preview scene
    if (mixerStore.previewSceneId && previewScene) {
      // Find the first empty slot or use the specified slot
      const targetSlotIndex = slotIndex ?? previewScene.slots.findIndex(s => !s.sourceId)
      if (targetSlotIndex >= 0 && targetSlotIndex < previewScene.slots.length) {
        const slotId = previewScene.slots[targetSlotIndex].id
        scenesStore.updateSlot(mixerStore.previewSceneId, slotId, { sourceId })
      }
    }
  }
  
  /**
   * Remove a source from the scene
   */
  function removeSourceFromScene(sourceId: string): void {
    const vdo = getVdo()
    if (!vdo || !isVdoReady()) return
    
    // Remove from VDO.ninja scene (set to scene 0)
    vdo.removeFromScene(sourceId)
  }
  
  /**
   * Set a source as the solo/program output (replaces all others)
   */
  function setSourceAsProgram(sourceId: string): void {
    const vdo = getVdo()
    if (!vdo || !isVdoReady()) return
    
    vdo.setProgram(sourceId)
  }
  
  // ==========================================
  // AUDIO CONTROL
  // ==========================================
  
  /**
   * Set mute state for a source
   */
  function setMute(sourceId: string, muted: boolean): void {
    const vdo = getVdo()
    if (vdo && isVdoReady()) {
      vdo.setMute(sourceId, muted)
    }
    mixerStore.setSourceMute(sourceId, muted)
  }
  
  /**
   * Toggle mute for a source
   */
  function toggleMute(sourceId: string): void {
    const vdo = getVdo()
    if (vdo && isVdoReady()) {
      vdo.toggleMute(sourceId)
    }
    const source = mixerStore.sources.find(s => s.id === sourceId)
    if (source) {
      mixerStore.setSourceMute(sourceId, !source.muted)
    }
  }
  
  /**
   * Set volume for a source (0-100)
   */
  function setVolume(sourceId: string, volume: number): void {
    const vdo = getVdo()
    if (vdo && isVdoReady()) {
      // VDO.ninja uses 0-200 scale (100 = normal)
      vdo.setVolume(sourceId, volume * 2)
    }
    mixerStore.setSourceVolume(sourceId, volume)
  }
  
  /**
   * Set solo state for a source
   */
  function setSolo(sourceId: string, solo: boolean): void {
    const vdo = getVdo()
    if (vdo && isVdoReady() && solo) {
      // VDO.ninja only has "start solo" not "stop solo"
      vdo.sendCommand('soloChat', sourceId)
    }
    mixerStore.setSourceSolo(sourceId, solo)
  }
  
  // ==========================================
  // GUEST CONTROL
  // ==========================================
  
  /**
   * Kick a guest from the room
   */
  function kickGuest(sourceId: string): void {
    const vdo = getVdo()
    if (vdo && isVdoReady()) {
      vdo.kickGuest(sourceId)
    }
    mixerStore.removeSource(sourceId)
  }
  
  /**
   * Send a message to a guest
   */
  function sendMessage(sourceId: string, message: string): void {
    const vdo = getVdo()
    if (vdo && isVdoReady()) {
      vdo.sendCommand('sendChat', sourceId, message)
    }
  }
  
  /**
   * Admit a guest from greenroom to the current preview scene
   */
  function admitFromGreenroom(sourceId: string): void {
    const vdo = getVdo()
    if (vdo && isVdoReady()) {
      // Get the current preview scene
      const previewScene = mixerStore.previewSceneId 
        ? scenesStore.getScene(mixerStore.previewSceneId) 
        : null
      
      // Add to VDO.ninja scene (preview scene or default to 1)
      const vdoSceneNumber = previewScene?.vdoSceneNumber || 1
      vdo.addToScene(sourceId, vdoSceneNumber)
    }
    mixerStore.admitFromGreenroom(sourceId)
  }
  
  // ==========================================
  // RECORDING
  // ==========================================
  
  function startRecording(): void {
    const vdo = getVdo()
    if (vdo && isVdoReady()) {
      vdo.startRecording()
    }
  }
  
  function stopRecording(): void {
    const vdo = getVdo()
    if (vdo && isVdoReady()) {
      vdo.stopRecording()
    }
  }
  
  // ==========================================
  // DIRECTOR
  // ==========================================
  
  /**
   * Send a raw director command to VDO.ninja
   */
  function sendDirectorCommand(action: string, target?: string, value?: unknown): void {
    const vdo = getVdo()
    if (vdo && isVdoReady()) {
      vdo.sendCommand(action, target, value)
    }
  }
  
  // ==========================================
  // WATCHERS - Sync store changes to VDO.ninja
  // ==========================================
  
  // Watch for VDO.ninja connection state
  watch(
    () => vdoEmbedRef.value?.isReady?.value,
    (ready) => {
      isConnected.value = ready === true
      if (ready) {
        console.log('[MixerController] VDO.ninja connected')
        mixerStore.setVdoConnected(true)
        isInitialized.value = true
        
        // Apply current program scene if exists
        if (mixerStore.programSceneId) {
          const scene = scenesStore.getScene(mixerStore.programSceneId)
          if (scene && scene.id !== lastAppliedSceneId.value) {
            applySceneToVdo(scene)
          }
        }
      } else {
        mixerStore.setVdoConnected(false)
      }
    },
    { immediate: true }
  )
  
  // Fallback: Initialize after a delay if isReady never fires
  onMounted(() => {
    setTimeout(() => {
      if (!isInitialized.value && vdoEmbedRef.value) {
        console.log('[MixerController] Fallback initialization (timeout)')
        isInitialized.value = true
        isConnected.value = true
        mixerStore.setVdoConnected(true)
      }
    }, 6000) // 6s, after the 5s timeout in useVdoNinja
  })
  
  // Watch for program scene changes
  watch(
    () => mixerStore.programSceneId,
    (newSceneId) => {
      if (newSceneId && newSceneId !== lastAppliedSceneId.value) {
        const scene = scenesStore.getScene(newSceneId)
        if (scene && isVdoReady()) {
          applySceneToVdo(scene)
        }
      }
    }
  )
  
  // Watch for connection errors
  watch(
    () => vdoEmbedRef.value?.lastError?.value,
    (error) => {
      if (error) {
        mixerStore.setLastError(error)
      }
    }
  )
  
  // ==========================================
  // RETURN
  // ==========================================
  
  return {
    // State
    isConnected,
    isInitialized,
    
    // Scene actions
    applySceneToVdo,
    switchToScene,
    takeToProgram,
    cutToProgram,
    
    // Source actions
    addSourceToScene,
    removeSourceFromScene,
    setSourceAsProgram,
    
    // Audio actions
    setMute,
    toggleMute,
    setVolume,
    setSolo,
    
    // Guest actions
    kickGuest,
    sendMessage,
    admitFromGreenroom,
    
    // Recording
    startRecording,
    stopRecording,
    
    // Director
    sendDirectorCommand
  }
}

