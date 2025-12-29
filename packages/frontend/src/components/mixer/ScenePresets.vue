<script setup lang="ts">
/**
 * ScenePresets Component
 * 
 * Manage scene presets for quick switching:
 * - Save current layout/scene as preset
 * - Load saved presets
 * - Edit preset names
 * - Delete presets
 * - Quick-switch buttons for saved presets
 */
import { ref, computed, onMounted } from 'vue'
import { useMixerStore } from '@/stores/mixer'
import { toast } from '@/composables/useToast'
import type { VdoScenePreset, VdoScenePresetsStorage } from '@/types/vdoninja'

// Storage key
const STORAGE_KEY = 'r58-scene-presets'
const STORAGE_VERSION = 1

// Props
const props = defineProps<{
  vdoEmbed?: {
    setScene: (sceneId: string) => void
    sendCommand: (action: string, target?: string, value?: unknown) => void
  }
}>()

const mixerStore = useMixerStore()

// Local state
const presets = ref<VdoScenePreset[]>([])
const isModalOpen = ref(false)
const editingPreset = ref<VdoScenePreset | null>(null)
const newPresetName = ref('')

// Layout type options
const layoutTypes = [
  { id: 'grid', name: 'Grid', icon: '⊞' },
  { id: 'solo', name: 'Solo', icon: '◻' },
  { id: 'pip', name: 'Picture-in-Picture', icon: '▫◻' },
  { id: 'custom', name: 'Custom', icon: '⊡' },
] as const

// Load presets from localStorage
function loadPresets() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      const data: VdoScenePresetsStorage = JSON.parse(saved)
      if (data.version === STORAGE_VERSION) {
        presets.value = data.presets
      }
    }
  } catch (e) {
    console.warn('[ScenePresets] Failed to load presets:', e)
  }
}

// Save presets to localStorage
function savePresets() {
  try {
    const data: VdoScenePresetsStorage = {
      version: STORAGE_VERSION,
      presets: presets.value,
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data))
  } catch (e) {
    console.warn('[ScenePresets] Failed to save presets:', e)
  }
}

// Create a new preset from current state
function createPreset() {
  if (!newPresetName.value.trim()) {
    toast.error('Please enter a preset name')
    return
  }
  
  const preset: VdoScenePreset = {
    id: `preset-${Date.now()}`,
    name: newPresetName.value.trim(),
    sceneId: mixerStore.activeScene || 'scene-1',
    layoutType: 'grid', // Default, could be detected from VDO.ninja
    sourceOrder: mixerStore.sources.map(s => s.id),
    createdAt: new Date().toISOString(),
  }
  
  presets.value.push(preset)
  savePresets()
  
  toast.success(`Preset "${preset.name}" saved`)
  newPresetName.value = ''
}

// Apply a preset
function applyPreset(preset: VdoScenePreset) {
  // Update last used
  preset.lastUsedAt = new Date().toISOString()
  savePresets()
  
  // Set scene in VDO.ninja
  if (props.vdoEmbed) {
    props.vdoEmbed.setScene(preset.sceneId)
    
    // Set layout type
    props.vdoEmbed.sendCommand('layout', undefined, preset.layoutType)
    
    // Apply slot configuration if custom
    if (preset.slots) {
      props.vdoEmbed.sendCommand('setSlots', undefined, preset.slots)
    }
  }
  
  // Update store
  mixerStore.setScene(preset.sceneId)
  
  toast.info(`Applied "${preset.name}"`)
}

// Delete a preset
function deletePreset(preset: VdoScenePreset) {
  if (confirm(`Delete preset "${preset.name}"?`)) {
    presets.value = presets.value.filter(p => p.id !== preset.id)
    savePresets()
    toast.info('Preset deleted')
  }
}

// Start editing a preset
function startEditing(preset: VdoScenePreset) {
  editingPreset.value = { ...preset }
}

// Save preset edits
function savePresetEdit() {
  if (!editingPreset.value) return
  
  const index = presets.value.findIndex(p => p.id === editingPreset.value!.id)
  if (index !== -1) {
    presets.value[index] = editingPreset.value
    savePresets()
    toast.success('Preset updated')
  }
  
  editingPreset.value = null
}

// Cancel editing
function cancelEditing() {
  editingPreset.value = null
}

// Update preset with current scene
function updatePresetWithCurrentScene(preset: VdoScenePreset) {
  preset.sceneId = mixerStore.activeScene || 'scene-1'
  preset.sourceOrder = mixerStore.sources.map(s => s.id)
  savePresets()
  toast.success(`Updated "${preset.name}" with current scene`)
}

// Quick presets for the sidebar
const quickPresets = computed(() => presets.value.slice(0, 4))

// Open/close modal
function openModal() {
  isModalOpen.value = true
}

function closeModal() {
  isModalOpen.value = false
  editingPreset.value = null
}

// Format date
function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString()
}

// Initialize
onMounted(() => {
  loadPresets()
})

// Expose methods
defineExpose({ openModal })
</script>

<template>
  <div class="scene-presets" data-testid="scene-presets">
    <!-- Quick preset buttons (for sidebar) -->
    <div class="space-y-2">
      <!-- Quick presets -->
      <div v-if="quickPresets.length > 0" class="grid grid-cols-2 gap-2">
        <button
          v-for="preset in quickPresets"
          :key="preset.id"
          @click="applyPreset(preset)"
          class="btn btn-sm text-left truncate"
          :class="{ 'btn-primary': mixerStore.activeScene === preset.sceneId }"
          :title="preset.name"
        >
          {{ preset.name }}
        </button>
      </div>
      
      <div v-else class="text-xs text-r58-text-secondary py-2">
        No presets saved yet.
      </div>
      
      <!-- Quick save current -->
      <div class="flex gap-2">
        <input
          v-model="newPresetName"
          type="text"
          placeholder="Preset name..."
          class="flex-1 px-2 py-1 bg-r58-bg-tertiary border border-r58-bg-tertiary rounded text-sm focus:border-r58-accent-primary focus:outline-none"
          @keyup.enter="createPreset"
        />
        <button
          @click="createPreset"
          class="btn btn-sm btn-primary"
          :disabled="!newPresetName.trim()"
          title="Save current scene as preset"
        >
          +
        </button>
      </div>
      
      <!-- Manage presets link -->
      <button
        v-if="presets.length > 0"
        @click="openModal"
        class="text-xs text-r58-accent-primary hover:underline w-full text-left"
      >
        Manage all presets ({{ presets.length }})
      </button>
    </div>
    
    <!-- Presets management modal -->
    <Teleport to="body">
      <div v-if="isModalOpen" class="fixed inset-0 z-50 flex items-center justify-center">
        <!-- Backdrop -->
        <div class="absolute inset-0 bg-black/60" @click="closeModal"></div>
        
        <!-- Modal content -->
        <div class="relative bg-r58-bg-secondary border border-r58-bg-tertiary rounded-xl w-full max-w-2xl max-h-[80vh] overflow-hidden shadow-2xl">
          <!-- Header -->
          <div class="flex items-center justify-between px-6 py-4 border-b border-r58-bg-tertiary">
            <h2 class="text-xl font-semibold">Scene Presets</h2>
            <button @click="closeModal" class="text-r58-text-secondary hover:text-r58-text-primary text-2xl">
              ×
            </button>
          </div>

          <!-- Content -->
          <div class="p-6 overflow-y-auto max-h-[60vh]">
            <!-- Create new preset -->
            <div class="mb-6 p-4 bg-r58-bg-tertiary rounded-lg">
              <h3 class="text-sm font-semibold mb-3">Save Current Scene</h3>
              <div class="flex gap-2">
                <input
                  v-model="newPresetName"
                  type="text"
                  placeholder="Enter preset name..."
                  class="flex-1 px-3 py-2 bg-r58-bg-secondary border border-r58-bg-tertiary rounded-lg focus:border-r58-accent-primary focus:outline-none"
                  @keyup.enter="createPreset"
                />
                <button
                  @click="createPreset"
                  class="btn btn-primary"
                  :disabled="!newPresetName.trim()"
                >
                  Save Preset
                </button>
              </div>
            </div>

            <!-- Presets list -->
            <div v-if="presets.length === 0" class="text-center py-12 text-r58-text-secondary">
              <div class="text-4xl mb-4">🎬</div>
              <p>No presets saved yet.</p>
              <p class="text-sm">Save your current scene configuration to quickly switch between layouts.</p>
            </div>

            <div v-else class="space-y-3">
              <div
                v-for="preset in presets"
                :key="preset.id"
                class="flex items-center justify-between p-4 bg-r58-bg-tertiary rounded-lg"
              >
                <!-- Editing mode -->
                <template v-if="editingPreset?.id === preset.id">
                  <div class="flex-1 space-y-3">
                    <input
                      v-model="editingPreset.name"
                      type="text"
                      class="w-full px-3 py-2 bg-r58-bg-secondary border border-r58-bg-tertiary rounded-lg focus:border-r58-accent-primary focus:outline-none"
                    />
                    
                    <div class="flex gap-2">
                      <select
                        v-model="editingPreset.layoutType"
                        class="px-3 py-2 bg-r58-bg-secondary border border-r58-bg-tertiary rounded-lg focus:border-r58-accent-primary focus:outline-none"
                      >
                        <option v-for="lt in layoutTypes" :key="lt.id" :value="lt.id">
                          {{ lt.icon }} {{ lt.name }}
                        </option>
                      </select>
                      
                      <button @click="savePresetEdit" class="btn btn-sm btn-primary">Save</button>
                      <button @click="cancelEditing" class="btn btn-sm">Cancel</button>
                    </div>
                  </div>
                </template>

                <!-- Display mode -->
                <template v-else>
                  <div class="flex items-center gap-4">
                    <!-- Layout icon -->
                    <div class="w-10 h-10 rounded bg-r58-bg-secondary flex items-center justify-center text-lg">
                      {{ layoutTypes.find(l => l.id === preset.layoutType)?.icon || '⊡' }}
                    </div>
                    
                    <div>
                      <div class="font-medium">{{ preset.name }}</div>
                      <div class="text-xs text-r58-text-secondary">
                        {{ layoutTypes.find(l => l.id === preset.layoutType)?.name || 'Custom' }}
                        • Created {{ formatDate(preset.createdAt) }}
                      </div>
                    </div>
                  </div>

                  <div class="flex items-center gap-2">
                    <button
                      @click="applyPreset(preset)"
                      class="btn btn-sm btn-primary"
                    >
                      Apply
                    </button>
                    <button
                      @click="updatePresetWithCurrentScene(preset)"
                      class="btn btn-sm"
                      title="Update with current scene"
                    >
                      Update
                    </button>
                    <button
                      @click="startEditing(preset)"
                      class="text-xs text-r58-accent-primary hover:underline"
                    >
                      Edit
                    </button>
                    <button
                      @click="deletePreset(preset)"
                      class="text-xs text-r58-accent-danger hover:underline"
                    >
                      Delete
                    </button>
                  </div>
                </template>
              </div>
            </div>
          </div>

          <!-- Footer -->
          <div class="flex items-center justify-between px-6 py-4 border-t border-r58-bg-tertiary">
            <div class="text-sm text-r58-text-secondary">
              {{ presets.length }} preset{{ presets.length !== 1 ? 's' : '' }} saved
            </div>
            <button @click="closeModal" class="btn">Close</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

