<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { RouterView } from 'vue-router'
import AppShell from '@/components/layout/AppShell.vue'
import ToastContainer from '@/components/shared/ToastContainer.vue'
import ShortcutsHelpModal from '@/components/shared/ShortcutsHelpModal.vue'
import KioskSleepScreen from '@/components/shared/KioskSleepScreen.vue'
import SplashScreen from '@/components/shared/SplashScreen.vue'
import UpdateNotification from '@/components/shared/UpdateNotification.vue'
import { isElectron } from '@/lib/api'
import { useKeyboardShortcuts } from '@/composables/useKeyboardShortcuts'
import { useR58WebSocket } from '@/composables/useWebSocket'
import { useLocalDeviceMode } from '@/composables/useLocalDeviceMode'

// Initialize global keyboard shortcuts
const { registerDefaults } = useKeyboardShortcuts()

// Initialize WebSocket for real-time events
const { connect, disconnect } = useR58WebSocket()

// Local device mode detection
const { isOnDevice } = useLocalDeviceMode()

// Track if app is active (not sleeping)
const isActive = ref(false)

function handleWake() {
  isActive.value = true
  // Reconnect WebSocket when waking
  connect()
}

function handleSleep() {
  isActive.value = false
  // Disconnect WebSocket to save resources
  disconnect()
}

onMounted(() => {
  registerDefaults()
  
  // Only connect WebSocket if not on device (device starts sleeping)
  if (!isOnDevice.value) {
    connect()
    isActive.value = true
  }
})

onUnmounted(() => {
  disconnect()
})
</script>

<template>
  <!-- Splash Screen - 3 second opening animation -->
  <SplashScreen v-if="isElectron()" />
  
  <!-- Kiosk Sleep Screen (only active on device) -->
  <KioskSleepScreen 
    :idle-timeout="300000"
    @wake="handleWake"
    @sleep="handleSleep"
  />
  
  <AppShell>
    <RouterView />
  </AppShell>
  
  <!-- Global UI components -->
  <UpdateNotification />
  <ToastContainer />
  <ShortcutsHelpModal />
</template>

