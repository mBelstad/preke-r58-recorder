/**
 * Performance Mode
 * 
 * Reduces UI updates during recording to minimize CPU usage.
 * Useful for low-power devices or when recording many inputs.
 * 
 * When enabled:
 * - Reduces animation frame rate
 * - Throttles non-critical UI updates
 * - Disables decorative animations
 */
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRecorderStore } from '@/stores/recorder'

// Performance mode state
const enabled = ref(localStorage.getItem('r58_performance_mode') === 'true')
const autoEnable = ref(localStorage.getItem('r58_performance_mode_auto') !== 'false')

// Auto-enable threshold (number of recording inputs)
const AUTO_ENABLE_INPUTS = 3

// Throttle intervals (in ms)
const NORMAL_UPDATE_INTERVAL = 100  // 10 FPS for UI updates
const PERFORMANCE_UPDATE_INTERVAL = 500  // 2 FPS in performance mode

export function usePerformanceMode() {
  const recorderStore = useRecorderStore()
  
  // Determine if we should be in performance mode
  const isActive = computed(() => {
    if (enabled.value) return true
    
    // Auto-enable when recording many inputs
    if (autoEnable.value && recorderStore.isRecording) {
      const activeInputs = recorderStore.inputs.filter(i => i.isRecording).length
      return activeInputs >= AUTO_ENABLE_INPUTS
    }
    
    return false
  })
  
  // Current update interval based on mode
  const updateInterval = computed(() => 
    isActive.value ? PERFORMANCE_UPDATE_INTERVAL : NORMAL_UPDATE_INTERVAL
  )
  
  // Apply/remove performance class on body
  watch(isActive, (active) => {
    if (active) {
      document.body.classList.add('performance-mode')
    } else {
      document.body.classList.remove('performance-mode')
    }
  }, { immediate: true })
  
  function setEnabled(value: boolean) {
    enabled.value = value
    localStorage.setItem('r58_performance_mode', String(value))
  }
  
  function setAutoEnable(value: boolean) {
    autoEnable.value = value
    localStorage.setItem('r58_performance_mode_auto', String(value))
  }
  
  function toggle() {
    setEnabled(!enabled.value)
  }
  
  /**
   * Create a throttled function that respects performance mode
   */
  function throttle<T extends (...args: any[]) => void>(fn: T, minInterval?: number): T {
    let lastCall = 0
    let timeoutId: number | null = null
    
    return ((...args: any[]) => {
      const now = Date.now()
      const interval = minInterval ?? updateInterval.value
      const timeSinceLastCall = now - lastCall
      
      if (timeSinceLastCall >= interval) {
        lastCall = now
        fn(...args)
      } else if (!timeoutId) {
        // Schedule for later
        timeoutId = window.setTimeout(() => {
          lastCall = Date.now()
          timeoutId = null
          fn(...args)
        }, interval - timeSinceLastCall)
      }
    }) as T
  }
  
  /**
   * Debounce a function (only call after delay with no new calls)
   */
  function debounce<T extends (...args: any[]) => void>(fn: T, delay?: number): T {
    let timeoutId: number | null = null
    
    return ((...args: any[]) => {
      if (timeoutId) {
        clearTimeout(timeoutId)
      }
      timeoutId = window.setTimeout(() => {
        fn(...args)
        timeoutId = null
      }, delay ?? updateInterval.value)
    }) as T
  }
  
  /**
   * Request animation frame that respects performance mode
   * In performance mode, uses setTimeout with lower frequency
   */
  function requestFrame(callback: FrameRequestCallback): number {
    if (isActive.value) {
      // Use setTimeout in performance mode (lower priority)
      return window.setTimeout(() => callback(performance.now()), updateInterval.value) as unknown as number
    }
    return requestAnimationFrame(callback)
  }
  
  function cancelFrame(id: number) {
    if (isActive.value) {
      clearTimeout(id)
    } else {
      cancelAnimationFrame(id)
    }
  }

  return {
    enabled,
    autoEnable,
    isActive,
    updateInterval,
    setEnabled,
    setAutoEnable,
    toggle,
    throttle,
    debounce,
    requestFrame,
    cancelFrame,
  }
}

// Export singleton for direct use
let _instance: ReturnType<typeof usePerformanceMode> | null = null

export function getPerformanceMode() {
  if (!_instance) {
    _instance = usePerformanceMode()
  }
  return _instance
}

