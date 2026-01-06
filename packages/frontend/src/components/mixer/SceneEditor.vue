<script setup lang="ts">
/**
 * SceneEditor - Modal for creating and editing scenes
 * 
 * Features:
 * - Drag-and-drop slot positioning
 * - Source assignment to slots
 * - Layout presets
 * - Save/cancel workflow
 */
import { ref, computed, watch, nextTick } from 'vue'
import { useScenesStore, type Scene, type SceneSlot } from '@/stores/scenes'
import { useMixerStore } from '@/stores/mixer'
import { toast } from '@/composables/useToast'

// Stores
const scenesStore = useScenesStore()
const mixerStore = useMixerStore()

// State
const isOpen = ref(false)
const editingScene = ref<Scene | null>(null)
const isNewScene = ref(false)

// Form state
const sceneName = ref('')
const slots = ref<SceneSlot[]>([])
const selectedSlotId = ref<string | null>(null)

// Drag state
const isDragging = ref(false)
const dragSlotId = ref<string | null>(null)
const dragStart = ref({ x: 0, y: 0 })
const dragMode = ref<'move' | 'resize'>('move')

// Available sources
const availableSources = computed(() => mixerStore.connectedSources)

// Layout presets
const layoutPresets = [
  { id: 'solo', name: 'Solo', slots: [{ x: 0, y: 0, w: 100, h: 100 }] },
  { id: 'split', name: 'Split', slots: [{ x: 0, y: 0, w: 50, h: 100 }, { x: 50, y: 0, w: 50, h: 100 }] },
  { id: 'pip', name: 'PiP', slots: [{ x: 0, y: 0, w: 100, h: 100 }, { x: 65, y: 60, w: 30, h: 35 }] },
  { id: 'quad', name: 'Quad', slots: [{ x: 0, y: 0, w: 50, h: 50 }, { x: 50, y: 0, w: 50, h: 50 }, { x: 0, y: 50, w: 50, h: 50 }, { x: 50, y: 50, w: 50, h: 50 }] },
  { id: 'three-up', name: '3-Up', slots: [{ x: 0, y: 0, w: 50, h: 100 }, { x: 50, y: 0, w: 50, h: 50 }, { x: 50, y: 50, w: 50, h: 50 }] }
]

// Open for editing existing scene
function open(scene: Scene) {
  editingScene.value = scene
  isNewScene.value = false
  sceneName.value = scene.name
  slots.value = JSON.parse(JSON.stringify(scene.slots))
  selectedSlotId.value = null
  isOpen.value = true
}

// Open for creating new scene
function openNew() {
  editingScene.value = null
  isNewScene.value = true
  sceneName.value = 'New Scene'
  slots.value = [
    { id: 'slot-1', sourceId: null, position: { x: 0, y: 0, w: 100, h: 100 }, zIndex: 0 }
  ]
  selectedSlotId.value = null
  isOpen.value = true
}

// Close modal
function close() {
  isOpen.value = false
  editingScene.value = null
}

// Save scene
function save() {
  if (!sceneName.value.trim()) {
    toast.error('Scene name is required')
    return
  }
  
  if (isNewScene.value) {
    // Create new scene
    const newScene = scenesStore.createScene({
      name: sceneName.value.trim(),
      resolution: { width: 1920, height: 1080 },
      slots: slots.value
    })
    toast.success(`Created: ${newScene.name}`)
  } else if (editingScene.value) {
    // Update existing scene
    scenesStore.updateScene(editingScene.value.id, {
      name: sceneName.value.trim(),
      slots: slots.value
    })
    toast.success(`Updated: ${sceneName.value}`)
  }
  
  close()
}

// Apply layout preset
function applyPreset(preset: typeof layoutPresets[0]) {
  slots.value = preset.slots.map((s, i) => ({
    id: `slot-${i + 1}`,
    sourceId: slots.value[i]?.sourceId || null,
    position: { x: s.x, y: s.y, w: s.w, h: s.h },
    zIndex: i
  }))
  toast.info(`Applied: ${preset.name}`)
}

// Add new slot
function addSlot() {
  const newSlot: SceneSlot = {
    id: `slot-${Date.now()}`,
    sourceId: null,
    position: { x: 10, y: 10, w: 30, h: 30 },
    zIndex: slots.value.length
  }
  slots.value.push(newSlot)
  selectedSlotId.value = newSlot.id
}

// Remove slot
function removeSlot(slotId: string) {
  const index = slots.value.findIndex(s => s.id === slotId)
  if (index !== -1) {
    slots.value.splice(index, 1)
    if (selectedSlotId.value === slotId) {
      selectedSlotId.value = null
    }
  }
}

// Select slot
function selectSlot(slotId: string) {
  selectedSlotId.value = slotId
}

// Get selected slot
const selectedSlot = computed(() => 
  slots.value.find(s => s.id === selectedSlotId.value)
)

// Assign source to selected slot
function assignSource(sourceId: string | null) {
  if (!selectedSlotId.value) return
  
  const slot = slots.value.find(s => s.id === selectedSlotId.value)
  if (slot) {
    slot.sourceId = sourceId
  }
}

// Drag handlers for slot positioning
function startDrag(event: MouseEvent, slotId: string, mode: 'move' | 'resize' = 'move') {
  event.preventDefault()
  isDragging.value = true
  dragSlotId.value = slotId
  dragMode.value = mode
  dragStart.value = { x: event.clientX, y: event.clientY }
  
  window.addEventListener('mousemove', handleDrag)
  window.addEventListener('mouseup', stopDrag)
}

function handleDrag(event: MouseEvent) {
  if (!isDragging.value || !dragSlotId.value) return
  
  const slot = slots.value.find(s => s.id === dragSlotId.value)
  if (!slot) return
  
  const container = document.getElementById('scene-canvas')
  if (!container) return
  
  const rect = container.getBoundingClientRect()
  const dx = ((event.clientX - dragStart.value.x) / rect.width) * 100
  const dy = ((event.clientY - dragStart.value.y) / rect.height) * 100
  
  if (dragMode.value === 'move') {
    slot.position.x = Math.max(0, Math.min(100 - slot.position.w, slot.position.x + dx))
    slot.position.y = Math.max(0, Math.min(100 - slot.position.h, slot.position.y + dy))
  } else {
    slot.position.w = Math.max(10, Math.min(100 - slot.position.x, slot.position.w + dx))
    slot.position.h = Math.max(10, Math.min(100 - slot.position.y, slot.position.h + dy))
  }
  
  dragStart.value = { x: event.clientX, y: event.clientY }
}

function stopDrag() {
  isDragging.value = false
  dragSlotId.value = null
  window.removeEventListener('mousemove', handleDrag)
  window.removeEventListener('mouseup', stopDrag)
}

// Expose methods
defineExpose({ open, openNew })
</script>

<template>
  <Teleport to="body">
    <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center">
      <!-- Backdrop -->
      <div class="absolute inset-0 bg-black/70" @click="close"></div>
      
      <!-- Modal -->
      <div class="relative bg-preke-bg-elevated border border-preke-bg-surface rounded-xl w-full max-w-4xl max-h-[90vh] overflow-hidden shadow-2xl">
        <!-- Header -->
        <div class="flex items-center justify-between px-6 py-4 border-b border-preke-bg-surface">
          <h2 class="text-xl font-semibold">
            {{ isNewScene ? 'Create Scene' : 'Edit Scene' }}
          </h2>
          <button @click="close" class="text-preke-text-dim hover:text-preke-text text-2xl">
            ×
          </button>
        </div>
        
        <!-- Content -->
        <div class="p-6 overflow-y-auto max-h-[calc(90vh-140px)]">
          <div class="flex gap-6">
            <!-- Left: Canvas -->
            <div class="flex-1">
              <!-- Scene Name -->
              <div class="mb-4">
                <label class="block text-sm text-preke-text-dim mb-1">Scene Name</label>
                <input 
                  v-model="sceneName"
                  type="text"
                  class="w-full px-3 py-2 bg-preke-bg-surface border border-preke-bg-surface rounded-lg focus:border-preke-gold focus:outline-none"
                />
              </div>
              
              <!-- Layout Presets -->
              <div class="mb-4">
                <label class="block text-sm text-preke-text-dim mb-2">Quick Layouts</label>
                <div class="flex gap-2 flex-wrap">
                  <button
                    v-for="preset in layoutPresets"
                    :key="preset.id"
                    @click="applyPreset(preset)"
                    class="px-3 py-1 text-xs bg-preke-bg-surface hover:bg-preke-gold/20 rounded transition-colors"
                  >
                    {{ preset.name }}
                  </button>
                </div>
              </div>
              
              <!-- Canvas -->
              <div class="mb-4">
                <label class="block text-sm text-preke-text-dim mb-2">Layout</label>
                <div 
                  id="scene-canvas"
                  class="relative aspect-video bg-black rounded-lg overflow-hidden border border-preke-bg-surface"
                >
                  <!-- Slots -->
                  <div
                    v-for="slot in slots"
                    :key="slot.id"
                    @mousedown="startDrag($event, slot.id, 'move')"
                    @click.stop="selectSlot(slot.id)"
                    class="absolute cursor-move transition-colors"
                    :class="[
                      selectedSlotId === slot.id 
                        ? 'border-2 border-preke-gold' 
                        : 'border border-preke-bg-surface hover:border-preke-gold/50'
                    ]"
                    :style="{
                      left: `${slot.position.x}%`,
                      top: `${slot.position.y}%`,
                      width: `${slot.position.w}%`,
                      height: `${slot.position.h}%`,
                      zIndex: slot.zIndex,
                      backgroundColor: slot.sourceId ? 'var(--preke-bg-surface)' : 'var(--preke-bg-elevated)'
                    }"
                  >
                    <!-- Slot Content -->
                    <div class="absolute inset-0 flex items-center justify-center text-xs text-preke-text-dim">
                      {{ slot.sourceId || 'Empty' }}
                    </div>
                    
                    <!-- Resize Handle -->
                    <div 
                      v-if="selectedSlotId === slot.id"
                      @mousedown.stop="startDrag($event, slot.id, 'resize')"
                      class="absolute bottom-0 right-0 w-4 h-4 bg-preke-gold cursor-se-resize"
                    ></div>
                    
                    <!-- Remove Button -->
                    <button
                      v-if="selectedSlotId === slot.id && slots.length > 1"
                      @click.stop="removeSlot(slot.id)"
                      class="absolute -top-2 -right-2 w-5 h-5 bg-red-500 text-white rounded-full text-xs flex items-center justify-center hover:bg-red-400"
                    >
                      ×
                    </button>
                  </div>
                </div>
              </div>
              
              <!-- Add Slot Button -->
              <button @click="addSlot" class="btn btn-sm">
                + Add Slot
              </button>
            </div>
            
            <!-- Right: Slot Properties -->
            <div class="w-64 flex-shrink-0">
              <h3 class="text-sm font-medium mb-3">Slot Properties</h3>
              
              <div v-if="selectedSlot" class="space-y-4">
                <!-- Source Assignment -->
                <div>
                  <label class="block text-xs text-preke-text-dim mb-1">Source</label>
                  <select 
                    :value="selectedSlot.sourceId || ''"
                    @change="assignSource(($event.target as HTMLSelectElement).value || null)"
                    class="w-full px-3 py-2 text-sm bg-preke-bg-surface border border-preke-bg-surface rounded-lg"
                  >
                    <option value="">None (Empty)</option>
                    <option 
                      v-for="source in availableSources" 
                      :key="source.id" 
                      :value="source.id"
                    >
                      {{ source.label }}
                    </option>
                  </select>
                </div>
                
                <!-- Position -->
                <div class="grid grid-cols-2 gap-2">
                  <div>
                    <label class="block text-xs text-preke-text-dim mb-1">X %</label>
                    <input 
                      v-model.number="selectedSlot.position.x"
                      type="number"
                      min="0"
                      max="100"
                      class="w-full px-2 py-1 text-sm bg-preke-bg-surface rounded"
                    />
                  </div>
                  <div>
                    <label class="block text-xs text-preke-text-dim mb-1">Y %</label>
                    <input 
                      v-model.number="selectedSlot.position.y"
                      type="number"
                      min="0"
                      max="100"
                      class="w-full px-2 py-1 text-sm bg-preke-bg-surface rounded"
                    />
                  </div>
                  <div>
                    <label class="block text-xs text-preke-text-dim mb-1">Width %</label>
                    <input 
                      v-model.number="selectedSlot.position.w"
                      type="number"
                      min="1"
                      max="100"
                      class="w-full px-2 py-1 text-sm bg-preke-bg-surface rounded"
                    />
                  </div>
                  <div>
                    <label class="block text-xs text-preke-text-dim mb-1">Height %</label>
                    <input 
                      v-model.number="selectedSlot.position.h"
                      type="number"
                      min="1"
                      max="100"
                      class="w-full px-2 py-1 text-sm bg-preke-bg-surface rounded"
                    />
                  </div>
                </div>
                
                <!-- Z-Index -->
                <div>
                  <label class="block text-xs text-preke-text-dim mb-1">Layer (z-index)</label>
                  <input 
                    v-model.number="selectedSlot.zIndex"
                    type="number"
                    min="0"
                    max="10"
                    class="w-full px-2 py-1 text-sm bg-preke-bg-surface rounded"
                  />
                </div>
              </div>
              
              <div v-else class="text-sm text-preke-text-dim p-4 bg-preke-bg-surface rounded-lg">
                Click a slot to edit its properties
              </div>
            </div>
          </div>
        </div>
        
        <!-- Footer -->
        <div class="flex items-center justify-end gap-3 px-6 py-4 border-t border-preke-bg-surface">
          <button @click="close" class="btn">Cancel</button>
          <button @click="save" class="btn btn-primary">
            {{ isNewScene ? 'Create Scene' : 'Save Changes' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

