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
  switch (type) {
    case 'success':
      return 'bg-emerald-900/90 border-emerald-500 text-emerald-100'
    case 'error':
      return 'bg-red-900/90 border-red-500 text-red-100'
    case 'warning':
      return 'bg-amber-900/90 border-amber-500 text-amber-100'
    case 'info':
      return 'bg-blue-900/90 border-blue-500 text-blue-100'
    default:
      return 'bg-zinc-800/90 border-zinc-600 text-zinc-100'
  }
}

function getIconColorClass(type: ToastType): string {
  switch (type) {
    case 'success':
      return 'text-emerald-400'
    case 'error':
      return 'text-red-400'
    case 'warning':
      return 'text-amber-400'
    case 'info':
      return 'text-blue-400'
    default:
      return 'text-zinc-400'
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
            'pointer-events-auto min-w-[320px] max-w-[420px] rounded-lg border-l-4 p-4 shadow-xl backdrop-blur-sm',
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

