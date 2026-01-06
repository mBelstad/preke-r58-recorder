<script setup lang="ts">
/**
 * Keyboard Shortcuts Help Modal
 * 
 * Shows all available keyboard shortcuts grouped by context.
 */
import { useKeyboardShortcuts, formatShortcutKey } from '@/composables/useKeyboardShortcuts'

const { isHelpModalOpen, closeHelpModal, shortcutsByContext, currentContext } = useKeyboardShortcuts()

const contextLabels: Record<string, string> = {
  global: 'Global',
  recorder: 'Recorder',
  mixer: 'Mixer',
  admin: 'Admin',
}
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div 
        v-if="isHelpModalOpen"
        class="fixed inset-0 z-[9998] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
        @click.self="closeHelpModal"
        @keydown.escape="closeHelpModal"
      >
        <div 
          class="bg-preke-bg-elevated rounded-xl shadow-2xl max-w-lg w-full max-h-[80vh] overflow-hidden"
          role="dialog"
          aria-labelledby="shortcuts-title"
        >
          <!-- Header -->
          <div class="flex items-center justify-between px-6 py-4 border-b border-preke-bg-surface">
            <h2 id="shortcuts-title" class="text-lg font-semibold">Keyboard Shortcuts</h2>
            <button 
              @click="closeHelpModal"
              class="text-preke-text-dim hover:text-preke-text transition-colors"
              aria-label="Close"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          
          <!-- Content -->
          <div class="p-6 overflow-y-auto max-h-[60vh]">
            <p class="text-sm text-preke-text-dim mb-4">
              Current context: <span class="font-medium text-preke-text">{{ contextLabels[currentContext] }}</span>
            </p>
            
            <div class="space-y-6">
              <div 
                v-for="(shortcuts, context) in shortcutsByContext" 
                :key="context"
                v-show="shortcuts.length > 0"
              >
                <h3 class="text-sm font-medium text-preke-text-dim uppercase tracking-wider mb-3">
                  {{ contextLabels[context] || context }}
                </h3>
                
                <div class="space-y-2">
                  <div 
                    v-for="{ key, shortcut } in shortcuts" 
                    :key="key"
                    class="flex items-center justify-between py-2 px-3 rounded-lg hover:bg-preke-bg-surface/50 transition-colors"
                  >
                    <span class="text-preke-text">{{ shortcut.description }}</span>
                    <kbd 
                      class="px-2 py-1 bg-preke-bg-surface rounded text-sm font-mono text-preke-text-dim"
                    >
                      {{ formatShortcutKey(shortcut.key, shortcut.modifiers) }}
                    </kbd>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <!-- Footer -->
          <div class="px-6 py-4 border-t border-preke-bg-surface bg-preke-bg-surface/30">
            <p class="text-xs text-preke-text-dim text-center">
              Press <kbd class="px-1.5 py-0.5 bg-preke-bg-surface rounded text-xs font-mono">?</kbd> anytime to show this help
            </p>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>

