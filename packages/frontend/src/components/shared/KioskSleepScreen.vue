<script setup lang="ts">
/**
 * KioskSleepScreen - Power-saving sleep mode for on-device kiosk
 * 
 * When running locally on the R58 device, this component:
 * - Shows a minimal black screen with subtle branding
 * - Stops all polling and network requests
 * - Wakes on touch/click/keypress
 * - Auto-sleeps after inactivity timeout
 * 
 * This saves significant CPU/GPU by not rendering the full UI.
 * 
 * NOTE: Sleep mode is currently disabled on localhost until further
 * development is complete. Only activates on actual R58 device (ARM Linux).
 */
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useLocalDeviceMode } from '@/composables/useLocalDeviceMode'

const props = defineProps<{
  idleTimeout?: number // ms before auto-sleep (default: 5 minutes)
}>()

const emit = defineEmits<{
  (e: 'wake'): void
  (e: 'sleep'): void
}>()

const { isOnDevice } = useLocalDeviceMode()
const isSleeping = ref(false)

// Check if we're on localhost (disable sleep mode on localhost for now)
const isLocalhost = computed(() => {
  if (typeof window === 'undefined') return false
  const host = window.location.hostname
  return host === 'localhost' || host === '127.0.0.1'
})

// Sleep mode is only enabled on actual device, NOT on localhost
const sleepModeEnabled = computed(() => isOnDevice.value && !isLocalhost.value)
const showWakeHint = ref(false)

// Default 5 minute idle timeout
const timeout = props.idleTimeout ?? 5 * 60 * 1000

let idleTimer: ReturnType<typeof setTimeout> | null = null
let hintTimer: ReturnType<typeof setTimeout> | null = null

function resetIdleTimer() {
  if (idleTimer) {
    clearTimeout(idleTimer)
  }
  
  // Only auto-sleep when sleep mode is enabled (device, not localhost)
  if (sleepModeEnabled.value) {
    idleTimer = setTimeout(() => {
      sleep()
    }, timeout)
  }
}

function sleep() {
  if (isSleeping.value) return
  
  isSleeping.value = true
  emit('sleep')
  console.log('[Kiosk] Entering sleep mode')
  
  // Show wake hint after a short delay
  hintTimer = setTimeout(() => {
    showWakeHint.value = true
  }, 2000)
}

function wake() {
  if (!isSleeping.value) return
  
  isSleeping.value = false
  showWakeHint.value = false
  emit('wake')
  console.log('[Kiosk] Waking from sleep')
  
  if (hintTimer) {
    clearTimeout(hintTimer)
  }
  
  resetIdleTimer()
}

function handleActivity() {
  if (isSleeping.value) {
    wake()
  } else {
    resetIdleTimer()
  }
}

// Start in sleep mode if on device (but not on localhost)
function initializeSleepState() {
  if (sleepModeEnabled.value) {
    // Start sleeping immediately on device
    sleep()
  }
}

onMounted(() => {
  // Activity listeners
  window.addEventListener('click', handleActivity)
  window.addEventListener('touchstart', handleActivity)
  window.addEventListener('keydown', handleActivity)
  window.addEventListener('mousemove', handleActivity)
  
  // Check if we should start in sleep mode
  initializeSleepState()
})

onUnmounted(() => {
  window.removeEventListener('click', handleActivity)
  window.removeEventListener('touchstart', handleActivity)
  window.removeEventListener('keydown', handleActivity)
  window.removeEventListener('mousemove', handleActivity)
  
  if (idleTimer) clearTimeout(idleTimer)
  if (hintTimer) clearTimeout(hintTimer)
})

// Watch for sleep mode enabled changes
watch(sleepModeEnabled, (enabled) => {
  if (enabled) {
    sleep()
  } else {
    wake()
  }
})

// Expose sleep/wake for external control
defineExpose({
  sleep,
  wake,
  isSleeping,
})
</script>

<template>
  <Transition name="fade-slow">
    <div 
      v-if="isSleeping"
      class="fixed inset-0 z-[100] bg-black flex flex-col items-center justify-center cursor-pointer"
      @click="wake"
      @touchstart="wake"
    >
      <!-- Subtle logo -->
      <div class="opacity-20 mb-8">
        <img 
          src="/logo-white.svg" 
          alt="Preke" 
          class="h-16"
        />
      </div>
      
      <!-- Wake hint (appears after delay) -->
      <Transition name="fade">
        <div v-if="showWakeHint" class="text-center">
          <div class="text-white/30 text-lg mb-2">
            Touch to wake
          </div>
          <div class="flex justify-center gap-1">
            <span class="w-2 h-2 rounded-full bg-white/20 animate-pulse"></span>
            <span class="w-2 h-2 rounded-full bg-white/20 animate-pulse" style="animation-delay: 0.2s"></span>
            <span class="w-2 h-2 rounded-full bg-white/20 animate-pulse" style="animation-delay: 0.4s"></span>
          </div>
        </div>
      </Transition>
      
      <!-- Clock (subtle) -->
      <div class="absolute bottom-8 text-white/10 text-sm font-mono">
        {{ new Date().toLocaleTimeString() }}
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.fade-slow-enter-active,
.fade-slow-leave-active {
  transition: opacity 0.5s ease;
}

.fade-slow-enter-from,
.fade-slow-leave-to {
  opacity: 0;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>

