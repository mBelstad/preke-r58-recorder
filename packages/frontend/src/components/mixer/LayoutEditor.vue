<script setup lang="ts">
/**
 * LayoutEditor Component
 * 
 * Drag-and-drop editor for custom source layouts:
 * - Drag sources into layout slots
 * - Resize sources with handles
 * - Preset layouts (grid, PiP, split, etc.)
 * - Custom positioning with percentage-based coordinates
 */
import { ref, computed, onMounted, watch } from 'vue'
import { useMixerStore } from '@/stores/mixer'
import { toast } from '@/composables/useToast'
import type { VdoSlotConfig, VdoSlotPosition, VdoLayoutPreset } from '@/types/vdoninja'

// Props
const props = defineProps<{
  vdoEmbed?: {
    setLayout: (layout: string) => void
    setSlots: (config: VdoSlotConfig) => void
    sendCommand: (action: string, target?: string, value?: unknown) => void
  }
}>()

const mixerStore = useMixerStore()

// Local state
const isOpen = ref(false)
const activeLayoutType = ref<'grid' | 'solo' | 'pip' | 'split' | 'custom'>('grid')
const customSlots = ref<VdoSlotConfig>({})
const isDragging = ref(false)
const draggedSource = ref<string | null>(null)
const hoveredSlot = ref<number | null>(null)

// Preset layouts
const presetLayouts: VdoLayoutPreset[] = [
  { id: 'grid-2', name: '2 Sources', type: 'grid', slots: 2 },
  { id: 'grid-4', name: '4 Sources', type: 'grid', slots: 4 },
  { id: 'solo', name: 'Solo', type: 'solo', slots: 1 },
  { id: 'pip', name: 'Picture-in-Picture', type: 'pip', slots: 2 },
  { id: 'split-h', name: 'Split Horizontal', type: 'split', slots: 2 },
  { id: 'split-v', name: 'Split Vertical', type: 'split', slots: 2 },
]

// PiP preset configuration
const pipLayout: VdoSlotConfig = {
  slot0: { x: 0, y: 0, width: 100, height: 100, zIndex: 0 },
  slot1: { x: 70, y: 70, width: 28, height: 28, zIndex: 1, borderRadius: 8 },
}

// Split horizontal
const splitHLayout: VdoSlotConfig = {
  slot0: { x: 0, y: 0, width: 50, height: 100, zIndex: 0 },
  slot1: { x: 50, y: 0, width: 50, height: 100, zIndex: 0 },
}

// Split vertical
const splitVLayout: VdoSlotConfig = {
  slot0: { x: 0, y: 0, width: 100, height: 50, zIndex: 0 },
  slot1: { x: 0, y: 50, width: 100, height: 50, zIndex: 0 },
}

// Grid 4
const grid4Layout: VdoSlotConfig = {
  slot0: { x: 0, y: 0, width: 50, height: 50, zIndex: 0 },
  slot1: { x: 50, y: 0, width: 50, height: 50, zIndex: 0 },
  slot2: { x: 0, y: 50, width: 50, height: 50, zIndex: 0 },
  slot3: { x: 50, y: 50, width: 50, height: 50, zIndex: 0 },
}

// Get sources from mixer store
const sources = computed(() => mixerStore.sources)

// Current slots for display
const displaySlots = computed(() => {
  if (activeLayoutType.value === 'custom') {
    return customSlots.value
  }
  
  switch (activeLayoutType.value) {
    case 'pip': return pipLayout
    case 'split': return splitHLayout
    case 'grid': return grid4Layout
    case 'solo': return { slot0: { x: 0, y: 0, width: 100, height: 100, zIndex: 0 } }
    default: return {}
  }
})

// Apply a preset layout
function applyPreset(preset: VdoLayoutPreset) {
  let layoutConfig: VdoSlotConfig
  
  switch (preset.id) {
    case 'pip':
      layoutConfig = pipLayout
      activeLayoutType.value = 'pip'
      break
    case 'split-h':
      layoutConfig = splitHLayout
      activeLayoutType.value = 'split'
      break
    case 'split-v':
      layoutConfig = splitVLayout
      activeLayoutType.value = 'split'
      break
    case 'grid-4':
      layoutConfig = grid4Layout
      activeLayoutType.value = 'grid'
      break
    case 'grid-2':
      layoutConfig = {
        slot0: { x: 0, y: 0, width: 50, height: 100, zIndex: 0 },
        slot1: { x: 50, y: 0, width: 50, height: 100, zIndex: 0 },
      }
      activeLayoutType.value = 'grid'
      break
    case 'solo':
    default:
      layoutConfig = { slot0: { x: 0, y: 0, width: 100, height: 100, zIndex: 0 } }
      activeLayoutType.value = 'solo'
  }
  
  // Send to VDO.ninja
  if (props.vdoEmbed) {
    props.vdoEmbed.setLayout(preset.type)
    props.vdoEmbed.setSlots(layoutConfig)
  }
  
  toast.success(`Applied ${preset.name} layout`)
}

// Handle drag start
function onDragStart(event: DragEvent, sourceId: string) {
  isDragging.value = true
  draggedSource.value = sourceId
  
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move'
    event.dataTransfer.setData('text/plain', sourceId)
  }
}

// Handle drag end
function onDragEnd() {
  isDragging.value = false
  draggedSource.value = null
  hoveredSlot.value = null
}

// Handle drag over slot
function onDragOverSlot(event: DragEvent, slotIndex: number) {
  event.preventDefault()
  hoveredSlot.value = slotIndex
}

// Handle drop on slot
function onDropOnSlot(event: DragEvent, slotIndex: number) {
  event.preventDefault()
  
  const sourceId = event.dataTransfer?.getData('text/plain')
  if (sourceId) {
    // Assign source to slot
    assignSourceToSlot(sourceId, slotIndex)
  }
  
  hoveredSlot.value = null
  isDragging.value = false
  draggedSource.value = null
}

// Assign source to a slot
function assignSourceToSlot(sourceId: string, slotIndex: number) {
  // In VDO.ninja, we use addToScene with a slot parameter
  if (props.vdoEmbed) {
    props.vdoEmbed.sendCommand('addToScene', sourceId, { slot: slotIndex })
  }
  
  toast.info(`Assigned source to slot ${slotIndex + 1}`)
}

// Switch to custom layout mode
function enableCustomLayout() {
  activeLayoutType.value = 'custom'
  customSlots.value = { ...displaySlots.value }
}

// Update a custom slot
function updateSlot(slotId: string, updates: Partial<VdoSlotPosition>) {
  if (customSlots.value[slotId]) {
    customSlots.value[slotId] = { ...customSlots.value[slotId], ...updates }
    
    // Apply to VDO.ninja
    if (props.vdoEmbed) {
      props.vdoEmbed.setSlots(customSlots.value)
    }
  }
}

// Open/close modal
function open() {
  isOpen.value = true
}

function close() {
  isOpen.value = false
}

// Get CSS style for a slot
function getSlotStyle(slot: VdoSlotPosition) {
  return {
    left: `${slot.x}%`,
    top: `${slot.y}%`,
    width: `${slot.width}%`,
    height: `${slot.height}%`,
    zIndex: slot.zIndex || 0,
    borderRadius: slot.borderRadius ? `${slot.borderRadius}px` : undefined,
  }
}

// Expose methods
defineExpose({ open })
</script>

<template>
  <Teleport to="body">
    <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center">
      <!-- Backdrop -->
      <div class="absolute inset-0 bg-black/60" @click="close"></div>
      
      <!-- Modal content -->
      <div class="relative bg-r58-bg-secondary border border-r58-bg-tertiary rounded-xl w-full max-w-4xl max-h-[85vh] overflow-hidden shadow-2xl" data-testid="layout-editor-modal">
        <!-- Header -->
        <div class="flex items-center justify-between px-6 py-4 border-b border-r58-bg-tertiary">
          <h2 class="text-xl font-semibold">Layout Editor</h2>
          <button @click="close" class="text-r58-text-secondary hover:text-r58-text-primary text-2xl">
            ×
          </button>
        </div>

        <!-- Content -->
        <div class="flex h-[60vh]">
          <!-- Left sidebar - Sources -->
          <div class="w-64 border-r border-r58-bg-tertiary p-4 overflow-y-auto">
            <h3 class="text-sm font-semibold text-r58-text-secondary uppercase tracking-wide mb-3">Sources</h3>
            
            <div v-if="sources.length === 0" class="text-sm text-r58-text-secondary py-4">
              No sources available. Connect cameras or guests.
            </div>
            
            <div v-else class="space-y-2">
              <div
                v-for="source in sources"
                :key="source.id"
                draggable="true"
                @dragstart="onDragStart($event, source.id)"
                @dragend="onDragEnd"
                class="flex items-center gap-2 p-3 bg-r58-bg-tertiary rounded-lg cursor-grab active:cursor-grabbing hover:bg-r58-accent-primary/20 transition-colors"
                :class="{ 'opacity-50': draggedSource === source.id }"
              >
                <span class="text-lg">
                  {{ source.type === 'camera' ? '📹' : source.type === 'guest' ? '👤' : '🖥️' }}
                </span>
                <span class="text-sm truncate">{{ source.label }}</span>
              </div>
            </div>
            
            <!-- Layout presets -->
            <h3 class="text-sm font-semibold text-r58-text-secondary uppercase tracking-wide mt-6 mb-3">Presets</h3>
            <div class="space-y-2">
              <button
                v-for="preset in presetLayouts"
                :key="preset.id"
                @click="applyPreset(preset)"
                class="w-full text-left px-3 py-2 bg-r58-bg-tertiary rounded-lg hover:bg-r58-accent-primary/20 transition-colors text-sm"
              >
                {{ preset.name }}
              </button>
            </div>
          </div>

          <!-- Main area - Layout preview -->
          <div class="flex-1 p-6">
            <div class="mb-4 flex items-center justify-between">
              <h3 class="text-sm font-semibold text-r58-text-secondary uppercase tracking-wide">
                Layout Preview
              </h3>
              <div class="flex gap-2">
                <span class="text-xs text-r58-text-secondary px-2 py-1 bg-r58-bg-tertiary rounded">
                  {{ activeLayoutType }}
                </span>
                <button
                  v-if="activeLayoutType !== 'custom'"
                  @click="enableCustomLayout"
                  class="text-xs text-r58-accent-primary hover:underline"
                >
                  Customize
                </button>
              </div>
            </div>
            
            <!-- Layout preview area -->
            <div 
              class="relative w-full bg-black rounded-lg overflow-hidden"
              style="aspect-ratio: 16/9;"
            >
              <!-- Slots -->
              <div
                v-for="(slot, slotId, index) in displaySlots"
                :key="slotId"
                class="absolute transition-all duration-200 border-2"
                :class="[
                  hoveredSlot === index ? 'border-r58-accent-primary bg-r58-accent-primary/20' : 'border-r58-bg-tertiary border-dashed',
                  isDragging ? 'hover:border-r58-accent-primary hover:bg-r58-accent-primary/10' : ''
                ]"
                :style="getSlotStyle(slot)"
                @dragover="onDragOverSlot($event, index as number)"
                @drop="onDropOnSlot($event, index as number)"
              >
                <!-- Slot label -->
                <div class="absolute inset-0 flex items-center justify-center text-r58-text-secondary text-sm">
                  <span class="bg-r58-bg-secondary/80 px-2 py-1 rounded">
                    Slot {{ (index as number) + 1 }}
                  </span>
                </div>
                
                <!-- Resize handles (for custom mode) -->
                <template v-if="activeLayoutType === 'custom'">
                  <div class="absolute right-0 bottom-0 w-4 h-4 bg-r58-accent-primary cursor-se-resize rounded-tl"></div>
                </template>
              </div>
              
              <!-- Drop indicator -->
              <div 
                v-if="isDragging" 
                class="absolute inset-0 flex items-center justify-center pointer-events-none"
              >
                <div class="bg-r58-bg-secondary/90 px-4 py-2 rounded-lg text-sm">
                  Drop source in a slot
                </div>
              </div>
            </div>
            
            <!-- Slot controls (for custom mode) -->
            <div v-if="activeLayoutType === 'custom'" class="mt-4">
              <h4 class="text-xs font-semibold text-r58-text-secondary uppercase tracking-wide mb-2">
                Slot Positions
              </h4>
              <div class="grid grid-cols-2 gap-4">
                <div 
                  v-for="(slot, slotId, index) in customSlots" 
                  :key="slotId"
                  class="p-3 bg-r58-bg-tertiary rounded-lg"
                >
                  <div class="text-sm font-medium mb-2">Slot {{ (index as number) + 1 }}</div>
                  <div class="grid grid-cols-2 gap-2 text-xs">
                    <label class="flex items-center gap-1">
                      X:
                      <input 
                        type="number" 
                        :value="slot.x" 
                        @input="updateSlot(slotId as string, { x: Number(($event.target as HTMLInputElement).value) })"
                        class="w-14 px-1 py-0.5 bg-r58-bg-secondary rounded"
                        min="0" max="100"
                      />%
                    </label>
                    <label class="flex items-center gap-1">
                      Y:
                      <input 
                        type="number" 
                        :value="slot.y" 
                        @input="updateSlot(slotId as string, { y: Number(($event.target as HTMLInputElement).value) })"
                        class="w-14 px-1 py-0.5 bg-r58-bg-secondary rounded"
                        min="0" max="100"
                      />%
                    </label>
                    <label class="flex items-center gap-1">
                      W:
                      <input 
                        type="number" 
                        :value="slot.width" 
                        @input="updateSlot(slotId as string, { width: Number(($event.target as HTMLInputElement).value) })"
                        class="w-14 px-1 py-0.5 bg-r58-bg-secondary rounded"
                        min="1" max="100"
                      />%
                    </label>
                    <label class="flex items-center gap-1">
                      H:
                      <input 
                        type="number" 
                        :value="slot.height" 
                        @input="updateSlot(slotId as string, { height: Number(($event.target as HTMLInputElement).value) })"
                        class="w-14 px-1 py-0.5 bg-r58-bg-secondary rounded"
                        min="1" max="100"
                      />%
                    </label>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Footer -->
        <div class="flex items-center justify-between px-6 py-4 border-t border-r58-bg-tertiary">
          <div class="text-sm text-r58-text-secondary">
            Drag sources from the left panel to layout slots
          </div>
          <div class="flex gap-2">
            <button @click="close" class="btn">Close</button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

