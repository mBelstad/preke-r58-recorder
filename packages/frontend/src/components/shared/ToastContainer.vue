<script setup lang="ts">
/**
 * Toast Container Component
 * 
 * Renders toast notifications stacked from bottom-right.
 * Must be mounted at the app root level.
 */
import { computed } from 'vue'
import globalToast, { type Toast, type ToastType } from '@/composables/useToast'

const toasts = computed(() => globalToast.toasts.value)

function getIcon(type: ToastType): string {
  switch (type) {
    case 'success':
      return '✓'
    case 'error':
      return '✕'
    case 'warning':
      return '⚠'
    case 'info':
      return 'ℹ'
    default:
      return ''
  }
}

function getColorClasses(type: ToastType): string {
  const base = 'backdrop-blur-lg border '
  switch (type) {
    case 'success':
      return base + 'bg-preke-green/15 border-preke-green/50 text-preke-text'
    case 'error':
      return base + 'bg-preke-red/15 border-preke-red/50 text-preke-text'
    case 'warning':
      return base + 'bg-preke-gold/15 border-preke-gold/50 text-preke-text'
    case 'info':
      return base + 'bg-preke-surface border-preke-surface-border text-preke-text'
    default:
      return base + 'bg-preke-surface border-preke-surface-border text-preke-text'
  }
}

function getIconColorClass(type: ToastType): string {
  switch (type) {
    case 'success':
      return 'text-preke-green'
    case 'error':
      return 'text-preke-red'
    case 'warning':
      return 'text-preke-gold'
    case 'info':
      return 'text-preke-text-muted'
    default:
      return 'text-preke-text-muted'
  }
}
</script>

<template>
  <Teleport to="body">
    <div 
      class="fixed bottom-4 right-4 z-[9999] flex flex-col-reverse gap-2 pointer-events-none"
      aria-live="polite"
      aria-atomic="false"
    >
      <TransitionGroup
        name="toast"
        tag="div"
        class="flex flex-col-reverse gap-2"
      >
        <div
          v-for="toast in toasts"
          :key="toast.id"
          :class="[
            'pointer-events-auto min-w-[320px] max-w-[420px] rounded-xl border p-4 shadow-2xl',
            getColorClasses(toast.type)
          ]"
          role="alert"
        >
          <div class="flex items-start gap-3">
            <!-- Icon -->
            <span 
              :class="['text-lg font-bold flex-shrink-0', getIconColorClass(toast.type)]"
            >
              {{ getIcon(toast.type) }}
            </span>
            
            <!-- Content -->
            <div class="flex-1 min-w-0">
              <p class="font-medium">{{ toast.title }}</p>
              <p v-if="toast.message" class="text-sm opacity-90 mt-0.5">
                {{ toast.message }}
              </p>
              
              <!-- Action button -->
              <button
                v-if="toast.action"
                @click="toast.action.onClick"
                class="mt-2 text-sm font-medium underline underline-offset-2 hover:no-underline"
              >
                {{ toast.action.label }}
              </button>
            </div>
            
            <!-- Dismiss button -->
            <button
              @click="globalToast.dismiss(toast.id)"
              class="flex-shrink-0 text-lg opacity-60 hover:opacity-100 transition-opacity"
              aria-label="Dismiss"
            >
              ×
            </button>
          </div>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped>
.toast-enter-active {
  transition: all 0.3s ease-out;
}
.toast-leave-active {
  transition: all 0.2s ease-in;
}
.toast-enter-from {
  transform: translateX(100%);
  opacity: 0;
}
.toast-leave-to {
  transform: translateX(100%);
  opacity: 0;
}
.toast-move {
  transition: transform 0.3s ease;
}
</style>

