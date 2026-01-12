/**
 * Keyboard Shortcuts System
 * 
 * Provides keyboard-driven workflows for professional operators.
 * Shortcuts are context-aware and can be customized.
 * 
 * Uses lazy initialization to avoid TDZ issues in minified builds.
 */
import { ref, onMounted, onUnmounted, computed, type Ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'

export interface Shortcut {
  key: string
  modifiers?: ('ctrl' | 'alt' | 'shift' | 'meta')[]
  description: string
  action: () => void | Promise<void>
  context?: string // 'recorder', 'mixer', 'global', etc.
  enabled?: () => boolean
}

// Lazy singleton initialization to avoid TDZ issues
interface ShortcutsState {
  registeredShortcuts: Ref<Map<string, Shortcut>>
  isHelpModalOpen: Ref<boolean>
  currentContext: Ref<string>
}

let _singleton: ShortcutsState | null = null

function getSingleton(): ShortcutsState {
  if (!_singleton) {
    _singleton = {
      registeredShortcuts: ref<Map<string, Shortcut>>(new Map()),
      isHelpModalOpen: ref(false),
      currentContext: ref<string>('global'),
    }
  }
  return _singleton
}

function getShortcutKey(key: string, modifiers?: string[]): string {
  const mods = modifiers?.sort().join('+') || ''
  return mods ? `${mods}+${key.toLowerCase()}` : key.toLowerCase()
}

export function useKeyboardShortcuts() {
  // Get singleton state (lazy initialization)
  const { registeredShortcuts, isHelpModalOpen, currentContext } = getSingleton()
  
  const router = useRouter()
  const route = useRoute()

  // Update context based on route
  const updateContext = () => {
    const routeName = route.name as string || ''
    if (routeName.toLowerCase().includes('recorder')) {
      currentContext.value = 'recorder'
    } else if (routeName.toLowerCase().includes('mixer')) {
      currentContext.value = 'mixer'
    } else if (routeName.toLowerCase().includes('admin')) {
      currentContext.value = 'admin'
    } else {
      currentContext.value = 'global'
    }
  }

  // Get all shortcuts for help display
  const allShortcuts = computed(() => {
    const shortcuts: { key: string; shortcut: Shortcut }[] = []
    registeredShortcuts.value.forEach((shortcut, key) => {
      shortcuts.push({ key, shortcut })
    })
    return shortcuts
  })

  // Get shortcuts grouped by context
  const shortcutsByContext = computed(() => {
    const groups: Record<string, { key: string; shortcut: Shortcut }[]> = {
      global: [],
      recorder: [],
      mixer: [],
      admin: [],
    }
    
    registeredShortcuts.value.forEach((shortcut, key) => {
      const context = shortcut.context || 'global'
      if (!groups[context]) groups[context] = []
      groups[context].push({ key, shortcut })
    })
    
    return groups
  })

  function register(shortcut: Shortcut) {
    const key = getShortcutKey(shortcut.key, shortcut.modifiers)
    registeredShortcuts.value.set(key, shortcut)
    return () => unregister(key)
  }

  function unregister(key: string) {
    registeredShortcuts.value.delete(key)
  }

  function handleKeyDown(event: KeyboardEvent) {
    // Don't trigger shortcuts when typing in inputs
    const target = event.target as HTMLElement
    if (
      target.tagName === 'INPUT' ||
      target.tagName === 'TEXTAREA' ||
      target.isContentEditable
    ) {
      // Allow Escape to blur inputs
      if (event.key === 'Escape') {
        target.blur()
      }
      return
    }

    // Build the key identifier
    const modifiers: string[] = []
    if (event.ctrlKey) modifiers.push('ctrl')
    if (event.altKey) modifiers.push('alt')
    if (event.shiftKey) modifiers.push('shift')
    if (event.metaKey) modifiers.push('meta')

    const key = getShortcutKey(event.key, modifiers)
    const shortcut = registeredShortcuts.value.get(key)

    if (shortcut) {
      // Check context
      const context = shortcut.context || 'global'
      if (context !== 'global' && context !== currentContext.value) {
        return // Shortcut not active in current context
      }

      // Check if enabled
      if (shortcut.enabled && !shortcut.enabled()) {
        return
      }

      event.preventDefault()
      shortcut.action()
    }
  }

  function openHelpModal() {
    isHelpModalOpen.value = true
  }

  function closeHelpModal() {
    isHelpModalOpen.value = false
  }

  // Register default shortcuts
  function registerDefaults() {
    // Help modal
    register({
      key: '?',
      modifiers: ['shift'],
      description: 'Show keyboard shortcuts',
      action: openHelpModal,
      context: 'global',
    })

    // Navigation
    register({
      key: 'r',
      description: 'Go to Recorder',
      action: () => { router.push({ name: 'recorder' }) },
      context: 'global',
    })

    register({
      key: 'm',
      description: 'Go to Mixer',
      action: () => { router.push({ name: 'mixer' }) },
      context: 'global',
    })

    // Escape to close modals
    register({
      key: 'Escape',
      description: 'Close modal / Cancel',
      action: () => {
        if (isHelpModalOpen.value) {
          closeHelpModal()
        }
        // Other modal closing logic can be added here
      },
      context: 'global',
    })
  }

  onMounted(() => {
    updateContext()
    window.addEventListener('keydown', handleKeyDown)
  })

  onUnmounted(() => {
    window.removeEventListener('keydown', handleKeyDown)
  })

  return {
    register,
    unregister,
    currentContext,
    allShortcuts,
    shortcutsByContext,
    isHelpModalOpen,
    openHelpModal,
    closeHelpModal,
    registerDefaults,
  }
}

// Format shortcut key for display
export function formatShortcutKey(key: string, modifiers?: string[]): string {
  const isMac = typeof navigator !== 'undefined' && navigator.platform.includes('Mac')
  
  const modLabels: Record<string, string> = {
    ctrl: isMac ? '⌃' : 'Ctrl',
    alt: isMac ? '⌥' : 'Alt',
    shift: isMac ? '⇧' : 'Shift',
    meta: isMac ? '⌘' : 'Win',
  }
  
  const parts: string[] = []
  modifiers?.forEach(mod => {
    parts.push(modLabels[mod] || mod)
  })
  
  // Format the key itself
  const keyLabels: Record<string, string> = {
    ' ': 'Space',
    'Escape': 'Esc',
    'ArrowUp': '↑',
    'ArrowDown': '↓',
    'ArrowLeft': '←',
    'ArrowRight': '→',
  }
  
  parts.push(keyLabels[key] || key.toUpperCase())
  
  return parts.join(isMac ? '' : '+')
}

