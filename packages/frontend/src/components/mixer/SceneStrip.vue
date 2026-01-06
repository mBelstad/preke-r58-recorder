<script setup lang="ts">
/**
 * SceneStrip - Scene thumbnail bar for quick switching
 * 
 * Shows all available scenes as thumbnails.
 * Click to select for preview, double-click for quick switch.
 * Supports keyboard shortcuts 1-8.
 */
import { ref, computed } from 'vue'
import { useScenesStore, type Scene } from '@/stores/scenes'
import { useMixerStore } from '@/stores/mixer'
import { toast } from '@/composables/useToast'

const emit = defineEmits<{
  (e: 'edit-scene', scene: Scene): void
  (e: 'add-scene'): void
}>()

const scenesStore = useScenesStore()
const mixerStore = useMixerStore()

// Context menu state
const contextMenuScene = ref<Scene | null>(null)
const contextMenuPosition = ref({ x: 0, y: 0 })
const showContextMenu = ref(false)

// Computed
const scenes = computed(() => scenesStore.scenes)
const previewSceneId = computed(() => mixerStore.previewSceneId)
const programSceneId = computed(() => mixerStore.programSceneId)

// Actions
function selectScene(scene: Scene) {
  if (mixerStore.mode === 'simple') {
    // Simple mode: immediate switch
    mixerStore.setProgramScene(scene.id)
  } else {
    // PVW/PGM mode: select for preview
    mixerStore.setPreviewScene(scene.id)
  }
}

function quickSwitchScene(scene: Scene) {
  mixerStore.setProgramScene(scene.id)
  toast.info(`Scene: ${scene.name}`)
}

function handleContextMenu(event: MouseEvent, scene: Scene) {
  event.preventDefault()
  contextMenuScene.value = scene
  contextMenuPosition.value = { x: event.clientX, y: event.clientY }
  showContextMenu.value = true
  
  // Close on click outside
  const closeMenu = () => {
    showContextMenu.value = false
    document.removeEventListener('click', closeMenu)
  }
  setTimeout(() => document.addEventListener('click', closeMenu), 0)
}

function editScene(scene: Scene) {
  showContextMenu.value = false
  emit('edit-scene', scene)
}

function duplicateScene(scene: Scene) {
  showContextMenu.value = false
  const newScene = scenesStore.duplicateScene(scene.id)
  if (newScene) {
    toast.success(`Duplicated: ${newScene.name}`)
  }
}

function deleteScene(scene: Scene) {
  showContextMenu.value = false
  
  // Prevent deleting if it's the only scene
  if (scenes.value.length <= 1) {
    toast.error('Cannot delete the last scene')
    return
  }
  
  // Prevent deleting if it's on program
  if (scene.id === programSceneId.value) {
    toast.error('Cannot delete scene that is on program')
    return
  }
  
  scenesStore.deleteScene(scene.id)
  toast.info(`Deleted: ${scene.name}`)
}

function getSceneStateClass(scene: Scene): string {
  if (scene.id === programSceneId.value) {
    return 'ring-2 ring-red-500 ring-offset-2 ring-offset-preke-bg-base'
  }
  if (scene.id === previewSceneId.value) {
    return 'ring-2 ring-amber-500 ring-offset-1 ring-offset-preke-bg-base'
  }
  return 'hover:ring-2 hover:ring-preke-gold/50'
}

function getSceneLabel(scene: Scene, index: number): string {
  // Show keyboard shortcut number if within 1-8
  if (index < 8) {
    return `${index + 1}`
  }
  return ''
}
</script>

<template>
  <div class="scene-strip" data-testid="scene-strip">
    <!-- Scene Thumbnails -->
    <div class="flex gap-2 overflow-x-auto pb-2 scrollbar-thin">
      <div
        v-for="(scene, index) in scenes"
        :key="scene.id"
        class="scene-thumbnail flex-shrink-0 w-28 cursor-pointer transition-all"
        :class="getSceneStateClass(scene)"
        @click="selectScene(scene)"
        @dblclick="quickSwitchScene(scene)"
        @contextmenu="handleContextMenu($event, scene)"
        :data-testid="`scene-${scene.id}`"
      >
        <!-- Thumbnail Preview -->
        <div class="relative aspect-video bg-preke-bg-surface rounded-lg overflow-hidden">
          <!-- Mini layout preview -->
          <div class="absolute inset-0">
            <div 
              v-for="slot in scene.slots" 
              :key="slot.id"
              class="absolute bg-preke-bg-elevated border border-preke-bg-surface/30"
              :style="{
                left: `${slot.position.x}%`,
                top: `${slot.position.y}%`,
                width: `${slot.position.w}%`,
                height: `${slot.position.h}%`
              }"
            ></div>
          </div>
          
          <!-- Keyboard shortcut badge -->
          <div 
            v-if="index < 8"
            class="absolute top-1 left-1 w-5 h-5 flex items-center justify-center bg-preke-bg-base/80 rounded text-xs font-mono font-bold"
          >
            {{ index + 1 }}
          </div>
          
          <!-- On Program indicator -->
          <div 
            v-if="scene.id === programSceneId"
            class="absolute top-1 right-1 flex items-center gap-1 px-1.5 py-0.5 bg-red-600 rounded text-xs font-bold"
          >
            <div class="w-1.5 h-1.5 rounded-full bg-white animate-pulse"></div>
            PGM
          </div>
          
          <!-- On Preview indicator -->
          <div 
            v-else-if="scene.id === previewSceneId"
            class="absolute top-1 right-1 px-1.5 py-0.5 bg-amber-500 rounded text-xs font-bold text-black"
          >
            PVW
          </div>
        </div>
        
        <!-- Scene Name -->
        <p class="mt-1 text-xs text-center truncate text-preke-text-dim">
          {{ scene.name }}
        </p>
      </div>
      
      <!-- Add Scene Button -->
      <button
        @click="emit('add-scene')"
        class="flex-shrink-0 w-28 aspect-video bg-preke-bg-surface/50 hover:bg-preke-bg-surface rounded-lg border-2 border-dashed border-preke-bg-surface hover:border-preke-gold/50 flex items-center justify-center transition-colors"
        data-testid="add-scene-button"
      >
        <div class="text-center text-preke-text-dim">
          <svg class="w-6 h-6 mx-auto mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
          </svg>
          <span class="text-xs">Add Scene</span>
        </div>
      </button>
    </div>
    
    <!-- Context Menu -->
    <Teleport to="body">
      <div 
        v-if="showContextMenu && contextMenuScene"
        class="fixed z-50 bg-preke-bg-elevated border border-preke-bg-surface rounded-lg shadow-xl py-1 min-w-[140px]"
        :style="{ left: `${contextMenuPosition.x}px`, top: `${contextMenuPosition.y}px` }"
      >
        <button 
          @click="editScene(contextMenuScene!)"
          class="w-full px-3 py-2 text-left text-sm hover:bg-preke-bg-surface flex items-center gap-2"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
          </svg>
          Edit
        </button>
        
        <button 
          @click="duplicateScene(contextMenuScene!)"
          class="w-full px-3 py-2 text-left text-sm hover:bg-preke-bg-surface flex items-center gap-2"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
          Duplicate
        </button>
        
        <div class="border-t border-preke-bg-surface my-1"></div>
        
        <button 
          @click="deleteScene(contextMenuScene!)"
          class="w-full px-3 py-2 text-left text-sm hover:bg-red-500/20 text-red-400 flex items-center gap-2"
          :disabled="contextMenuScene?.id === programSceneId"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
          Delete
        </button>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.scrollbar-thin::-webkit-scrollbar {
  height: 4px;
}

.scrollbar-thin::-webkit-scrollbar-track {
  background: transparent;
}

.scrollbar-thin::-webkit-scrollbar-thumb {
  background: var(--preke-bg-surface);
  border-radius: 2px;
}
</style>

