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
  { id: 'goto-recorder', key: 'r', modifiers: ['alt'], description: 'Go to Recorder', context: 'global', category: 'Navigation', editable: true },
  { id: 'goto-mixer', key: 'm', modifiers: ['alt'], description: 'Go to Mixer', context: 'global', category: 'Navigation', editable: true },
  { id: 'escape', key: 'Escape', description: 'Close modal / Cancel', context: 'global', category: 'Navigation', editable: false },
  
  // Mixer - Scenes (Preview selection)
  { id: 'scene-1', key: '1', description: 'Select Scene 1 for preview', context: 'mixer', category: 'Scenes', editable: true },
  { id: 'scene-2', key: '2', description: 'Select Scene 2 for preview', context: 'mixer', category: 'Scenes', editable: true },
  { id: 'scene-3', key: '3', description: 'Select Scene 3 for preview', context: 'mixer', category: 'Scenes', editable: true },
  { id: 'scene-4', key: '4', description: 'Select Scene 4 for preview', context: 'mixer', category: 'Scenes', editable: true },
  { id: 'scene-5', key: '5', description: 'Select Scene 5 for preview', context: 'mixer', category: 'Scenes', editable: true },
  { id: 'scene-6', key: '6', description: 'Select Scene 6 for preview', context: 'mixer', category: 'Scenes', editable: true },
  { id: 'scene-7', key: '7', description: 'Select Scene 7 for preview', context: 'mixer', category: 'Scenes', editable: true },
  { id: 'scene-8', key: '8', description: 'Select Scene 8 for preview', context: 'mixer', category: 'Scenes', editable: true },
  
  // Mixer - Transitions (PVW/PGM workflow)
  { id: 'take', key: ' ', description: 'TAKE - Transition preview to program', context: 'mixer', category: 'Transitions', editable: false },
  { id: 'cut', key: 'Escape', description: 'CUT - Immediate switch to preview', context: 'mixer', category: 'Transitions', editable: false },
  { id: 'transition-cut', key: 't', description: 'Set transition: Cut', context: 'mixer', category: 'Transitions', editable: true },
  { id: 'transition-fade', key: 'f', description: 'Set transition: Fade', context: 'mixer', category: 'Transitions', editable: true },
  
  // Mixer - Control
  { id: 'go-live', key: 'g', description: 'Toggle Go Live', context: 'mixer', category: 'Control', editable: true },
  { id: 'toggle-recording', key: 'r', description: 'Toggle recording', context: 'mixer', category: 'Control', editable: true },
  { id: 'mute-all', key: 'm', modifiers: ['ctrl'], description: 'Mute all sources', context: 'mixer', category: 'Control', editable: true },
  { id: 'toggle-sidebar', key: 's', modifiers: ['ctrl'], description: 'Toggle sidebar', context: 'mixer', category: 'Control', editable: true },
  
  // Mixer - Audio
  { id: 'mute-1', key: 'F1', description: 'Toggle mute: Source 1', context: 'mixer', category: 'Audio', editable: true },
  { id: 'mute-2', key: 'F2', description: 'Toggle mute: Source 2', context: 'mixer', category: 'Audio', editable: true },
  { id: 'mute-3', key: 'F3', description: 'Toggle mute: Source 3', context: 'mixer', category: 'Audio', editable: true },
  { id: 'mute-4', key: 'F4', description: 'Toggle mute: Source 4', context: 'mixer', category: 'Audio', editable: true },
  
  // Recorder
  { id: 'start-stop-recording', key: ' ', description: 'Start/Stop recording', context: 'recorder', category: 'Recording', editable: true },
  { id: 'mark-chapter', key: 'c', description: 'Mark chapter point', context: 'recorder', category: 'Recording', editable: true },
  { id: 'select-all', key: 'a', modifiers: ['ctrl'], description: 'Select all cameras', context: 'recorder', category: 'Recording', editable: true },
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
      <div class="relative bg-preke-bg-elevated border border-preke-bg-surface rounded-xl w-full max-w-3xl max-h-[80vh] overflow-hidden shadow-2xl" data-testid="hotkey-settings-modal">
        <!-- Header -->
        <div class="flex items-center justify-between px-6 py-4 border-b border-preke-bg-surface">
          <h2 class="text-xl font-semibold">Keyboard Shortcuts</h2>
          <div class="flex items-center gap-4">
            <button 
              @click="resetAllHotkeys" 
              class="text-sm text-preke-text-dim hover:text-preke-text"
            >
              Reset All
            </button>
            <button @click="close" class="text-preke-text-dim hover:text-preke-text text-2xl">
              ×
            </button>
          </div>
        </div>

        <!-- Tabs -->
        <div class="flex border-b border-preke-bg-surface">
          <button
            v-for="tab in (['mixer', 'global', 'recorder'] as const)"
            :key="tab"
            @click="activeTab = tab"
            class="px-6 py-3 text-sm font-medium capitalize transition-colors"
            :class="activeTab === tab 
              ? 'text-preke-gold border-b-2 border-preke-gold' 
              : 'text-preke-text-dim hover:text-preke-text'"
          >
            {{ tab }}
          </button>
        </div>

        <!-- Content -->
        <div class="p-6 overflow-y-auto max-h-[55vh]">
          <!-- Empty state -->
          <div v-if="Object.keys(currentHotkeys).length === 0" class="text-center py-12 text-preke-text-dim">
            No shortcuts defined for this context.
          </div>

          <!-- Hotkeys by category -->
          <div v-else class="space-y-6">
            <div v-for="(hotkeys, category) in currentHotkeys" :key="category">
              <h3 class="text-sm font-semibold text-preke-text-dim uppercase tracking-wide mb-3">
                {{ category }}
              </h3>
              
              <div class="space-y-2">
                <div
                  v-for="hotkey in hotkeys"
                  :key="hotkey.id"
                  class="flex items-center justify-between p-3 bg-preke-bg-surface rounded-lg"
                  :class="{ 'ring-2 ring-preke-gold': editingHotkeyId === hotkey.id }"
                >
                  <!-- Description -->
                  <div class="flex-1">
                    <span class="text-sm">{{ hotkey.description }}</span>
                    <span v-if="isCustomized(hotkey.id)" class="ml-2 text-xs text-preke-gold">(customized)</span>
                  </div>
                  
                  <!-- Key binding -->
                  <div class="flex items-center gap-2">
                    <!-- Current or new key display -->
                    <div v-if="editingHotkeyId === hotkey.id" class="flex items-center gap-2">
                      <kbd v-if="newKeyCapture" class="px-3 py-1 bg-preke-gold text-white rounded text-sm font-mono">
                        {{ formatShortcutKey(newKeyCapture.key, newKeyCapture.modifiers) }}
                      </kbd>
                      <span v-else class="text-sm text-preke-text-dim animate-pulse">
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
                      <kbd class="px-3 py-1 bg-preke-bg-elevated border border-preke-bg-surface rounded text-sm font-mono">
                        {{ formatHotkey(hotkey) }}
                      </kbd>
                      
                      <button
                        v-if="hotkey.editable"
                        @click="startEditing(hotkey.id)"
                        class="text-xs text-preke-gold hover:underline"
                      >
                        Edit
                      </button>
                      
                      <button
                        v-if="isCustomized(hotkey.id)"
                        @click="resetHotkey(hotkey.id)"
                        class="text-xs text-preke-text-dim hover:text-preke-red"
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
        <div class="flex items-center justify-between px-6 py-4 border-t border-preke-bg-surface">
          <div class="text-sm text-preke-text-dim">
            Click "Edit" to customize a shortcut. Press any key combination to set.
          </div>
          <button @click="close" class="btn">Close</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

