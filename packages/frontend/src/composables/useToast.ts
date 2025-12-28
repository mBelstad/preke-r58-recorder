/**
 * Toast Notification System
 * 
 * Provides feedback for user actions and system events.
 * Follows the UX polish plan for professional operators.
 */
import { ref, computed } from 'vue'

export type ToastType = 'success' | 'error' | 'warning' | 'info'

export interface Toast {
  id: string
  type: ToastType
  title: string
  message?: string
  duration: number // 0 = sticky (manual dismiss required)
  action?: {
    label: string
    onClick: () => void
  }
  createdAt: number
}

const toasts = ref<Toast[]>([])
const MAX_VISIBLE = 3

let toastId = 0

function generateId(): string {
  return `toast-${++toastId}-${Date.now()}`
}

function getDefaultDuration(type: ToastType): number {
  switch (type) {
    case 'success':
      return 3000
    case 'info':
      return 4000
    case 'warning':
      return 5000
    case 'error':
      return 0 // Sticky - requires manual dismiss
    default:
      return 4000
  }
}

export function useToast() {
  const visibleToasts = computed(() => toasts.value.slice(-MAX_VISIBLE))

  function addToast(options: {
    type: ToastType
    title: string
    message?: string
    duration?: number
    action?: { label: string; onClick: () => void }
  }): string {
    const id = generateId()
    const duration = options.duration ?? getDefaultDuration(options.type)

    const toast: Toast = {
      id,
      type: options.type,
      title: options.title,
      message: options.message,
      duration,
      action: options.action,
      createdAt: Date.now(),
    }

    toasts.value.push(toast)

    // Auto-dismiss after duration (if not sticky)
    if (duration > 0) {
      setTimeout(() => {
        dismiss(id)
      }, duration)
    }

    return id
  }

  function dismiss(id: string) {
    const index = toasts.value.findIndex(t => t.id === id)
    if (index !== -1) {
      toasts.value.splice(index, 1)
    }
  }

  function dismissAll() {
    toasts.value = []
  }

  // Convenience methods
  function success(title: string, message?: string) {
    return addToast({ type: 'success', title, message })
  }

  function error(title: string, message?: string, action?: { label: string; onClick: () => void }) {
    return addToast({ type: 'error', title, message, action })
  }

  function warning(title: string, message?: string) {
    return addToast({ type: 'warning', title, message })
  }

  function info(title: string, message?: string) {
    return addToast({ type: 'info', title, message })
  }

  return {
    toasts: visibleToasts,
    addToast,
    dismiss,
    dismissAll,
    success,
    error,
    warning,
    info,
  }
}

// Global singleton instance
const globalToast = useToast()
export const toast = {
  success: globalToast.success,
  error: globalToast.error,
  warning: globalToast.warning,
  info: globalToast.info,
  dismiss: globalToast.dismiss,
  dismissAll: globalToast.dismissAll,
}

export default globalToast

