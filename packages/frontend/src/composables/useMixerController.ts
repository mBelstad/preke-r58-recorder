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
import { ref, computed, watch, onMounted, onUnmounted, type Ref } from 'vue'
import { useMixerStore, type MixerSource } from '@/stores/mixer'
import { useScenesStore, type Scene, type SceneSlot } from '@/stores/scenes'
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
   */
  function isVdoReady(): boolean {
    const vdo = getVdo()
    return vdo?.isReady?.value === true
  }
  
  /**
   * Convert our scene to VDO.ninja layout format
   * VDO.ninja uses percentage-based positions: x, y, w, h (0-100)
   */
  function sceneToVdoLayout(scene: Scene): VdoLayoutSlot[] {
    return scene.slots.map((slot, index) => ({
      x: slot.position.x,
      y: slot.position.y,
      w: slot.position.w,
      h: slot.position.h,
      slot: index,
      z: slot.zIndex,
      c: true  // Crop to fit
    }))
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
   */
  function applySceneToVdo(scene: Scene): void {
    const vdo = getVdo()
    if (!vdo || !isVdoReady()) {
      console.warn('[MixerController] VDO.ninja not ready, cannot apply scene')
      return
    }
    
    console.log('[MixerController] Applying scene to VDO:', scene.name)
    
    // Get layout slots
    const layout = sceneToVdoLayout(scene)
    
    // Get source IDs
    const sourceIds = getSceneSourceIds(scene)
    
    // Apply layout to VDO.ninja
    // If layout has no slots or is a simple full-screen, use preset
    if (scene.slots.length === 1 && 
        scene.slots[0].position.w === 100 && 
        scene.slots[0].position.h === 100) {
      // Full screen - use layout preset 1
      vdo.setLayout(1)
    } else if (scene.slots.length === 2) {
      // Side by side - check if it's split screen
      vdo.setLayout(2)
    } else if (scene.slots.length === 4) {
      // Quad view - use layout preset 0 (auto grid)
      vdo.setLayout(0)
    } else {
      // Custom layout
      vdo.setLayout(layout)
    }
    
    // Add sources to scene
    // VDO.ninja scene 1 is the default output scene
    const sceneNumber = 1
    
    // First, clear existing sources from scene (by setting them to scene 0)
    // This would require tracking previous sources
    
    // Add each source to the scene
    for (const sourceId of sourceIds) {
      vdo.addToScene(sourceId, sceneNumber)
    }
    
    lastAppliedSceneId.value = scene.id
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
   * Add a source to the current scene
   */
  function addSourceToScene(sourceId: string, slotIndex?: number): void {
    const vdo = getVdo()
    if (!vdo || !isVdoReady()) return
    
    // Add to VDO.ninja scene 1
    vdo.addToScene(sourceId, 1)
    
    // Also update our scene store if we have a preview scene
    if (mixerStore.previewSceneId) {
      scenesStore.updateSlot(
        mixerStore.previewSceneId, 
        slotIndex || 0, 
        { sourceId }
      )
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
   * Admit a guest from greenroom to main room
   */
  function admitFromGreenroom(sourceId: string): void {
    const vdo = getVdo()
    if (vdo && isVdoReady()) {
      // In VDO.ninja, this would be done by adding them to a scene
      vdo.addToScene(sourceId, 1)
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

