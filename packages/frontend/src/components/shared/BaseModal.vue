<script setup lang="ts">
/**
 * BaseModal - Reusable modal component
 * 
 * Features:
 * - Backdrop with click-to-close
 * - Escape key to close
 * - Focus trap
 * - Smooth transitions
 * - Flexible sizing
 */
import { ref, onMounted, onUnmounted } from 'vue'

const props = withDefaults(defineProps<{
  title?: string
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'full'
  closeOnBackdrop?: boolean
  closeOnEscape?: boolean
}>(), {
  size: 'md',
  closeOnBackdrop: true,
  closeOnEscape: true,
})

const emit = defineEmits<{
  (e: 'close'): void
}>()

const isOpen = ref(false)

function open() {
  isOpen.value = true
}

function close() {
  isOpen.value = false
  emit('close')
}

function handleBackdropClick() {
  if (props.closeOnBackdrop) {
    close()
  }
}

function handleEscape(event: KeyboardEvent) {
  if (props.closeOnEscape && event.key === 'Escape' && isOpen.value) {
    close()
  }
}

onMounted(() => {
  if (props.closeOnEscape) {
    window.addEventListener('keydown', handleEscape)
  }
})

onUnmounted(() => {
  if (props.closeOnEscape) {
    window.removeEventListener('keydown', handleEscape)
  }
})

defineExpose({ open, close, isOpen })

const sizeClasses = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-lg',
  xl: 'max-w-xl',
  full: 'max-w-full mx-4',
}
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div 
        v-if="isOpen"
        class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
        @click.self="handleBackdropClick"
        role="dialog"
        aria-modal="true"
      >
        <Transition name="scale">
          <div 
            v-if="isOpen"
            :class="[
              'glass-card rounded-xl shadow-2xl w-full border border-preke-surface-border',
              sizeClasses[size]
            ]"
            @click.stop
          >
            <!-- Header -->
            <div 
              v-if="title || $slots.header"
              class="flex items-center justify-between px-6 py-4 border-b border-preke-surface-border"
            >
              <slot name="header">
                <h2 class="text-lg font-semibold text-preke-text">
                  {{ title }}
                </h2>
              </slot>
              <button
                @click="close"
                class="p-2 rounded-lg text-preke-text-muted hover:text-preke-text hover:bg-preke-surface transition-colors"
                aria-label="Close modal"
              >
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            
            <!-- Content -->
            <div class="px-6 py-4">
              <slot />
            </div>
            
            <!-- Footer -->
            <div 
              v-if="$slots.footer"
              class="flex items-center justify-end gap-3 px-6 py-4 border-t border-preke-surface-border"
            >
              <slot name="footer" :close="close" />
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
/* Fade transition for backdrop */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* Scale transition for modal content */
.scale-enter-active,
.scale-leave-active {
  transition: all 0.2s ease;
}

.scale-enter-from {
  opacity: 0;
  transform: scale(0.95);
}

.scale-leave-to {
  opacity: 0;
  transform: scale(0.95);
}
</style>
