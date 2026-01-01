import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

// ==========================================
// TYPES
// ==========================================

export interface SceneSlot {
  id: string
  sourceId: string | null
  position: {
    x: number  // percentage 0-100
    y: number
    w: number
    h: number
  }
  zIndex: number
  style?: {
    borderRadius?: number
    border?: string
    shadow?: boolean
    crop?: { top: number; right: number; bottom: number; left: number }
  }
}

export interface TransitionConfig {
  type: 'cut' | 'fade' | 'wipe-left' | 'wipe-right' | 'wipe-up' | 'wipe-down'
  duration: number  // milliseconds
}

export interface AudioMixConfig {
  [sourceId: string]: {
    volume: number  // 0-100
    muted: boolean
    solo: boolean
  }
}

export interface Scene {
  id: string
  name: string
  thumbnail?: string
  resolution: { width: number; height: number }
  slots: SceneSlot[]
  transition?: TransitionConfig
  audio?: AudioMixConfig
  createdAt: string
  updatedAt: string
}

// ==========================================
// DEFAULT SCENES
// ==========================================

const defaultScenes: Scene[] = [
  {
    id: 'solo-1',
    name: 'Solo 1',
    resolution: { width: 1920, height: 1080 },
    slots: [
      { id: 'slot-1', sourceId: null, position: { x: 0, y: 0, w: 100, h: 100 }, zIndex: 0 }
    ],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString()
  },
  {
    id: 'solo-2',
    name: 'Solo 2',
    resolution: { width: 1920, height: 1080 },
    slots: [
      { id: 'slot-1', sourceId: null, position: { x: 0, y: 0, w: 100, h: 100 }, zIndex: 0 }
    ],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString()
  },
  {
    id: 'split',
    name: 'Split Screen',
    resolution: { width: 1920, height: 1080 },
    slots: [
      { id: 'slot-1', sourceId: null, position: { x: 0, y: 0, w: 50, h: 100 }, zIndex: 0 },
      { id: 'slot-2', sourceId: null, position: { x: 50, y: 0, w: 50, h: 100 }, zIndex: 0 }
    ],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString()
  },
  {
    id: 'pip',
    name: 'Picture in Picture',
    resolution: { width: 1920, height: 1080 },
    slots: [
      { id: 'slot-1', sourceId: null, position: { x: 0, y: 0, w: 100, h: 100 }, zIndex: 0 },
      { id: 'slot-2', sourceId: null, position: { x: 65, y: 60, w: 30, h: 35 }, zIndex: 1, style: { borderRadius: 8, shadow: true } }
    ],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString()
  },
  {
    id: 'quad',
    name: 'Quad View',
    resolution: { width: 1920, height: 1080 },
    slots: [
      { id: 'slot-1', sourceId: null, position: { x: 0, y: 0, w: 50, h: 50 }, zIndex: 0 },
      { id: 'slot-2', sourceId: null, position: { x: 50, y: 0, w: 50, h: 50 }, zIndex: 0 },
      { id: 'slot-3', sourceId: null, position: { x: 0, y: 50, w: 50, h: 50 }, zIndex: 0 },
      { id: 'slot-4', sourceId: null, position: { x: 50, y: 50, w: 50, h: 50 }, zIndex: 0 }
    ],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString()
  },
  {
    id: 'three-up',
    name: 'Three Up',
    resolution: { width: 1920, height: 1080 },
    slots: [
      { id: 'slot-1', sourceId: null, position: { x: 0, y: 0, w: 50, h: 100 }, zIndex: 0 },
      { id: 'slot-2', sourceId: null, position: { x: 50, y: 0, w: 50, h: 50 }, zIndex: 0 },
      { id: 'slot-3', sourceId: null, position: { x: 50, y: 50, w: 50, h: 50 }, zIndex: 0 }
    ],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString()
  },
  {
    id: 'interview',
    name: 'Interview',
    resolution: { width: 1920, height: 1080 },
    slots: [
      { id: 'slot-1', sourceId: null, position: { x: 5, y: 0, w: 42.5, h: 100 }, zIndex: 0 },
      { id: 'slot-2', sourceId: null, position: { x: 52.5, y: 0, w: 42.5, h: 100 }, zIndex: 0 }
    ],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString()
  },
  {
    id: 'presentation',
    name: 'Presentation',
    resolution: { width: 1920, height: 1080 },
    slots: [
      { id: 'slot-1', sourceId: null, position: { x: 0, y: 0, w: 75, h: 100 }, zIndex: 0 },
      { id: 'slot-2', sourceId: null, position: { x: 75, y: 50, w: 25, h: 50 }, zIndex: 1, style: { shadow: true } }
    ],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString()
  }
]

// ==========================================
// STORAGE
// ==========================================

const STORAGE_KEY = 'r58-mixer-scenes'

function loadScenesFromStorage(): Scene[] {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) {
      const parsed = JSON.parse(stored)
      return parsed.scenes || defaultScenes
    }
  } catch (e) {
    console.warn('[Scenes] Failed to load from storage:', e)
  }
  return [...defaultScenes]
}

function saveScenestoStorage(scenes: Scene[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ scenes, version: 1 }))
  } catch (e) {
    console.warn('[Scenes] Failed to save to storage:', e)
  }
}

// ==========================================
// STORE
// ==========================================

export const useScenesStore = defineStore('scenes', () => {
  // State
  const scenes = ref<Scene[]>(loadScenesFromStorage())
  const activeSceneId = ref<string | null>(null)
  
  // Computed
  const activeScene = computed(() => 
    scenes.value.find(s => s.id === activeSceneId.value) || null
  )
  
  const sceneCount = computed(() => scenes.value.length)
  
  // Actions
  function setActiveScene(sceneId: string | null) {
    activeSceneId.value = sceneId
  }
  
  function getScene(sceneId: string): Scene | undefined {
    return scenes.value.find(s => s.id === sceneId)
  }
  
  function createScene(scene: Omit<Scene, 'id' | 'createdAt' | 'updatedAt'>): Scene {
    const newScene: Scene = {
      ...scene,
      id: `scene-${Date.now()}`,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    }
    scenes.value.push(newScene)
    saveScenestoStorage(scenes.value)
    return newScene
  }
  
  function updateScene(sceneId: string, updates: Partial<Scene>) {
    const index = scenes.value.findIndex(s => s.id === sceneId)
    if (index !== -1) {
      scenes.value[index] = {
        ...scenes.value[index],
        ...updates,
        updatedAt: new Date().toISOString()
      }
      saveScenestoStorage(scenes.value)
    }
  }
  
  function deleteScene(sceneId: string) {
    const index = scenes.value.findIndex(s => s.id === sceneId)
    if (index !== -1) {
      scenes.value.splice(index, 1)
      if (activeSceneId.value === sceneId) {
        activeSceneId.value = null
      }
      saveScenestoStorage(scenes.value)
    }
  }
  
  function duplicateScene(sceneId: string): Scene | null {
    const original = getScene(sceneId)
    if (!original) return null
    
    const duplicate: Scene = {
      ...JSON.parse(JSON.stringify(original)),
      id: `scene-${Date.now()}`,
      name: `${original.name} (Copy)`,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    }
    scenes.value.push(duplicate)
    saveScenestoStorage(scenes.value)
    return duplicate
  }
  
  function updateSlot(sceneId: string, slotId: string, updates: Partial<SceneSlot>) {
    const scene = getScene(sceneId)
    if (!scene) return
    
    const slotIndex = scene.slots.findIndex(s => s.id === slotId)
    if (slotIndex !== -1) {
      scene.slots[slotIndex] = { ...scene.slots[slotIndex], ...updates }
      updateScene(sceneId, { slots: scene.slots })
    }
  }
  
  function assignSourceToSlot(sceneId: string, slotId: string, sourceId: string | null) {
    updateSlot(sceneId, slotId, { sourceId })
  }
  
  function exportScenes(): string {
    return JSON.stringify({ scenes: scenes.value, version: 1, exportedAt: new Date().toISOString() }, null, 2)
  }
  
  function importScenes(jsonString: string): { success: boolean; count: number; error?: string } {
    try {
      const parsed = JSON.parse(jsonString)
      if (!parsed.scenes || !Array.isArray(parsed.scenes)) {
        return { success: false, count: 0, error: 'Invalid format: missing scenes array' }
      }
      
      // Validate and import scenes
      const importedScenes: Scene[] = parsed.scenes.map((s: Partial<Scene>) => ({
        id: s.id || `scene-${Date.now()}-${Math.random().toString(36).slice(2)}`,
        name: s.name || 'Imported Scene',
        resolution: s.resolution || { width: 1920, height: 1080 },
        slots: s.slots || [],
        thumbnail: s.thumbnail,
        transition: s.transition,
        audio: s.audio,
        createdAt: s.createdAt || new Date().toISOString(),
        updatedAt: new Date().toISOString()
      }))
      
      scenes.value = [...scenes.value, ...importedScenes]
      saveScenestoStorage(scenes.value)
      
      return { success: true, count: importedScenes.length }
    } catch (e) {
      return { success: false, count: 0, error: String(e) }
    }
  }
  
  function resetToDefaults() {
    scenes.value = [...defaultScenes]
    activeSceneId.value = null
    saveScenestoStorage(scenes.value)
  }
  
  /**
   * Download scenes as JSON file
   */
  function downloadScenes(filename: string = 'scenes.json') {
    const json = exportScenes()
    const blob = new Blob([json], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }
  
  /**
   * Import scenes from uploaded file
   */
  function importFromFile(file: File): Promise<{ success: boolean; count: number; error?: string }> {
    return new Promise((resolve) => {
      const reader = new FileReader()
      reader.onload = (e) => {
        const content = e.target?.result as string
        const result = importScenes(content)
        resolve(result)
      }
      reader.onerror = () => {
        resolve({ success: false, count: 0, error: 'Failed to read file' })
      }
      reader.readAsText(file)
    })
  }
  
  return {
    // State
    scenes,
    activeSceneId,
    
    // Computed
    activeScene,
    sceneCount,
    
    // Actions
    setActiveScene,
    getScene,
    createScene,
    updateScene,
    deleteScene,
    duplicateScene,
    updateSlot,
    assignSourceToSlot,
    exportScenes,
    importScenes,
    resetToDefaults,
    downloadScenes,
    importFromFile
  }
})

