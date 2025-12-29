<script setup lang="ts">
/**
 * HotkeySettings Component
 * 
 * Modal for viewing and customizing keyboard shortcuts:
 * - View all available shortcuts grouped by context
 * - Customize shortcut bindings
 * - Save/reset custom bindings
 * - Quick reference display
 */
import { ref, computed, watch, onMounted } from 'vue'
import { formatShortcutKey } from '@/composables/useKeyboardShortcuts'
import { toast } from '@/composables/useToast'

// Storage key for custom bindings
const STORAGE_KEY = 'r58-hotkey-customizations'

// Default hotkey definitions
export interface HotkeyDefinition {
  id: string
  key: string
  modifiers?: ('ctrl' | 'alt' | 'shift' | 'meta')[]
  description: string
  context: 'global' | 'mixer' | 'recorder'
  category: string
  editable: boolean
}

// Default hotkeys
const DEFAULT_HOTKEYS: HotkeyDefinition[] = [
  // Global
  { id: 'help', key: '?', modifiers: ['shift'], description: 'Show keyboard shortcuts', context: 'global', category: 'Navigation', editable: false },
  { id: 'goto-recorder', key: 'r', description: 'Go to Recorder', context: 'global', category: 'Navigation', editable: true },
  { id: 'goto-mixer', key: 'm', description: 'Go to Mixer', context: 'global', category: 'Navigation', editable: true },
  { id: 'escape', key: 'Escape', description: 'Close modal / Cancel', context: 'global', category: 'Navigation', editable: false },
  
  // Mixer - Scenes
  { id: 'scene-1', key: '1', description: 'Switch to Scene 1', context: 'mixer', category: 'Scenes', editable: true },
  { id: 'scene-2', key: '2', description: 'Switch to Scene 2', context: 'mixer', category: 'Scenes', editable: true },
  { id: 'scene-3', key: '3', description: 'Switch to Scene 3', context: 'mixer', category: 'Scenes', editable: true },
  { id: 'scene-4', key: '4', description: 'Switch to Scene 4', context: 'mixer', category: 'Scenes', editable: true },
  { id: 'scene-5', key: '5', description: 'Switch to Scene 5', context: 'mixer', category: 'Scenes', editable: true },
  { id: 'scene-6', key: '6', description: 'Switch to Scene 6', context: 'mixer', category: 'Scenes', editable: true },
  { id: 'scene-7', key: '7', description: 'Switch to Scene 7', context: 'mixer', category: 'Scenes', editable: true },
  { id: 'scene-8', key: '8', description: 'Switch to Scene 8', context: 'mixer', category: 'Scenes', editable: true },
  { id: 'scene-9', key: '9', description: 'Switch to Scene 9', context: 'mixer', category: 'Scenes', editable: true },
  
  // Mixer - Transitions
  { id: 'cut', key: 't', description: 'Cut transition', context: 'mixer', category: 'Transitions', editable: true },
  { id: 'fade', key: 'a', description: 'Auto-transition (fade)', context: 'mixer', category: 'Transitions', editable: true },
  { id: 'cycle-sources', key: 'Tab', description: 'Cycle through sources', context: 'mixer', category: 'Transitions', editable: true },
  
  // Mixer - Control
  { id: 'go-live', key: 'g', description: 'Toggle Go Live', context: 'mixer', category: 'Control', editable: true },
  { id: 'toggle-recording', key: 'r', modifiers: ['ctrl'], description: 'Toggle local recording', context: 'mixer', category: 'Control', editable: true },
  { id: 'mute-all', key: 'm', modifiers: ['ctrl'], description: 'Mute all sources', context: 'mixer', category: 'Control', editable: true },
  
  // Mixer - Sources
  { id: 'source-1', key: 'F1', description: 'Select source 1', context: 'mixer', category: 'Sources', editable: true },
  { id: 'source-2', key: 'F2', description: 'Select source 2', context: 'mixer', category: 'Sources', editable: true },
  { id: 'source-3', key: 'F3', description: 'Select source 3', context: 'mixer', category: 'Sources', editable: true },
  { id: 'source-4', key: 'F4', description: 'Select source 4', context: 'mixer', category: 'Sources', editable: true },
  
  // Recorder
  { id: 'start-stop-recording', key: ' ', description: 'Start/Stop recording', context: 'recorder', category: 'Recording', editable: true },
  { id: 'mark-chapter', key: 'c', description: 'Mark chapter point', context: 'recorder', category: 'Recording', editable: true },
]

// Local state
const isOpen = ref(false)
const activeTab = ref<'global' | 'mixer' | 'recorder'>('mixer')
const customizations = ref<Record<string, { key: string; modifiers?: string[] }>>({})
const editingHotkeyId = ref<string | null>(null)
const newKeyCapture = ref<{ key: string; modifiers: string[] } | null>(null)

// Load customizations from localStorage
function loadCustomizations() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      customizations.value = JSON.parse(saved)
    }
  } catch (e) {
    console.warn('[HotkeySettings] Failed to load customizations:', e)
  }
}

// Save customizations to localStorage
function saveCustomizations() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(customizations.value))
  } catch (e) {
    console.warn('[HotkeySettings] Failed to save customizations:', e)
  }
}

// Get hotkey with any customizations applied
function getHotkey(def: HotkeyDefinition): HotkeyDefinition {
  const custom = customizations.value[def.id]
  if (custom) {
    return {
      ...def,
      key: custom.key,
      modifiers: custom.modifiers as HotkeyDefinition['modifiers'],
    }
  }
  return def
}

// Get hotkeys grouped by category for a context
const hotkeysByContext = computed(() => {
  const groups: Record<string, Record<string, HotkeyDefinition[]>> = {
    global: {},
    mixer: {},
    recorder: {},
  }
  
  for (const def of DEFAULT_HOTKEYS) {
    const hotkey = getHotkey(def)
    if (!groups[def.context][hotkey.category]) {
      groups[def.context][hotkey.category] = []
    }
    groups[def.context][hotkey.category].push(hotkey)
  }
  
  return groups
})

// Current tab hotkeys
const currentHotkeys = computed(() => hotkeysByContext.value[activeTab.value] || {})

// Format a hotkey for display
function formatHotkey(hotkey: HotkeyDefinition): string {
  return formatShortcutKey(hotkey.key, hotkey.modifiers)
}

// Check if a hotkey is customized
function isCustomized(id: string): boolean {
  return !!customizations.value[id]
}

// Start editing a hotkey
function startEditing(id: string) {
  const def = DEFAULT_HOTKEYS.find(h => h.id === id)
  if (!def?.editable) return
  
  editingHotkeyId.value = id
  newKeyCapture.value = null
  
  // Focus will be handled by the key capture
  document.addEventListener('keydown', captureKey)
}

// Capture a new key
function captureKey(event: KeyboardEvent) {
  event.preventDefault()
  event.stopPropagation()
  
  // Ignore modifier-only presses
  if (['Control', 'Alt', 'Shift', 'Meta'].includes(event.key)) {
    return
  }
  
  const modifiers: string[] = []
  if (event.ctrlKey) modifiers.push('ctrl')
  if (event.altKey) modifiers.push('alt')
  if (event.shiftKey) modifiers.push('shift')
  if (event.metaKey) modifiers.push('meta')
  
  newKeyCapture.value = {
    key: event.key,
    modifiers,
  }
  
  document.removeEventListener('keydown', captureKey)
}

// Save the new key binding
function saveKeyBinding() {
  if (!editingHotkeyId.value || !newKeyCapture.value) return
  
  customizations.value[editingHotkeyId.value] = {
    key: newKeyCapture.value.key,
    modifiers: newKeyCapture.value.modifiers.length > 0 ? newKeyCapture.value.modifiers : undefined,
  }
  
  saveCustomizations()
  toast.success('Hotkey updated')
  
  editingHotkeyId.value = null
  newKeyCapture.value = null
}

// Cancel editing
function cancelEditing() {
  editingHotkeyId.value = null
  newKeyCapture.value = null
  document.removeEventListener('keydown', captureKey)
}

// Reset a single hotkey
function resetHotkey(id: string) {
  delete customizations.value[id]
  saveCustomizations()
  toast.info('Hotkey reset to default')
}

// Reset all hotkeys
function resetAllHotkeys() {
  if (confirm('Reset all hotkeys to defaults?')) {
    customizations.value = {}
    saveCustomizations()
    toast.info('All hotkeys reset to defaults')
  }
}

// Open modal
function open() {
  loadCustomizations()
  isOpen.value = true
}

// Close modal
function close() {
  cancelEditing()
  isOpen.value = false
}

// Initialize
onMounted(() => {
  loadCustomizations()
})

// Get custom bindings for use by other components
function getCustomBindings(): Record<string, { key: string; modifiers?: string[] }> {
  return { ...customizations.value }
}

// Expose methods
defineExpose({ open, getCustomBindings })
</script>

<template>
  <Teleport to="body">
    <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center">
      <!-- Backdrop -->
      <div class="absolute inset-0 bg-black/60" @click="close"></div>
      
      <!-- Modal content -->
      <div class="relative bg-r58-bg-secondary border border-r58-bg-tertiary rounded-xl w-full max-w-3xl max-h-[80vh] overflow-hidden shadow-2xl" data-testid="hotkey-settings-modal">
        <!-- Header -->
        <div class="flex items-center justify-between px-6 py-4 border-b border-r58-bg-tertiary">
          <h2 class="text-xl font-semibold">Keyboard Shortcuts</h2>
          <div class="flex items-center gap-4">
            <button 
              @click="resetAllHotkeys" 
              class="text-sm text-r58-text-secondary hover:text-r58-text-primary"
            >
              Reset All
            </button>
            <button @click="close" class="text-r58-text-secondary hover:text-r58-text-primary text-2xl">
              ×
            </button>
          </div>
        </div>

        <!-- Tabs -->
        <div class="flex border-b border-r58-bg-tertiary">
          <button
            v-for="tab in (['mixer', 'global', 'recorder'] as const)"
            :key="tab"
            @click="activeTab = tab"
            class="px-6 py-3 text-sm font-medium capitalize transition-colors"
            :class="activeTab === tab 
              ? 'text-r58-accent-primary border-b-2 border-r58-accent-primary' 
              : 'text-r58-text-secondary hover:text-r58-text-primary'"
          >
            {{ tab }}
          </button>
        </div>

        <!-- Content -->
        <div class="p-6 overflow-y-auto max-h-[55vh]">
          <!-- Empty state -->
          <div v-if="Object.keys(currentHotkeys).length === 0" class="text-center py-12 text-r58-text-secondary">
            No shortcuts defined for this context.
          </div>

          <!-- Hotkeys by category -->
          <div v-else class="space-y-6">
            <div v-for="(hotkeys, category) in currentHotkeys" :key="category">
              <h3 class="text-sm font-semibold text-r58-text-secondary uppercase tracking-wide mb-3">
                {{ category }}
              </h3>
              
              <div class="space-y-2">
                <div
                  v-for="hotkey in hotkeys"
                  :key="hotkey.id"
                  class="flex items-center justify-between p-3 bg-r58-bg-tertiary rounded-lg"
                  :class="{ 'ring-2 ring-r58-accent-primary': editingHotkeyId === hotkey.id }"
                >
                  <!-- Description -->
                  <div class="flex-1">
                    <span class="text-sm">{{ hotkey.description }}</span>
                    <span v-if="isCustomized(hotkey.id)" class="ml-2 text-xs text-r58-accent-primary">(customized)</span>
                  </div>
                  
                  <!-- Key binding -->
                  <div class="flex items-center gap-2">
                    <!-- Current or new key display -->
                    <div v-if="editingHotkeyId === hotkey.id" class="flex items-center gap-2">
                      <kbd v-if="newKeyCapture" class="px-3 py-1 bg-r58-accent-primary text-white rounded text-sm font-mono">
                        {{ formatShortcutKey(newKeyCapture.key, newKeyCapture.modifiers) }}
                      </kbd>
                      <span v-else class="text-sm text-r58-text-secondary animate-pulse">
                        Press a key...
                      </span>
                      
                      <button
                        v-if="newKeyCapture"
                        @click="saveKeyBinding"
                        class="btn btn-sm btn-primary"
                      >
                        Save
                      </button>
                      <button
                        @click="cancelEditing"
                        class="btn btn-sm"
                      >
                        Cancel
                      </button>
                    </div>
                    
                    <template v-else>
                      <kbd class="px-3 py-1 bg-r58-bg-secondary border border-r58-bg-tertiary rounded text-sm font-mono">
                        {{ formatHotkey(hotkey) }}
                      </kbd>
                      
                      <button
                        v-if="hotkey.editable"
                        @click="startEditing(hotkey.id)"
                        class="text-xs text-r58-accent-primary hover:underline"
                      >
                        Edit
                      </button>
                      
                      <button
                        v-if="isCustomized(hotkey.id)"
                        @click="resetHotkey(hotkey.id)"
                        class="text-xs text-r58-text-secondary hover:text-r58-accent-danger"
                      >
                        Reset
                      </button>
                    </template>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Footer -->
        <div class="flex items-center justify-between px-6 py-4 border-t border-r58-bg-tertiary">
          <div class="text-sm text-r58-text-secondary">
            Click "Edit" to customize a shortcut. Press any key combination to set.
          </div>
          <button @click="close" class="btn">Close</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

