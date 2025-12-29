<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { RouterView } from 'vue-router'
import AppShell from '@/components/layout/AppShell.vue'
import ToastContainer from '@/components/shared/ToastContainer.vue'
import ShortcutsHelpModal from '@/components/shared/ShortcutsHelpModal.vue'
import { useKeyboardShortcuts } from '@/composables/useKeyboardShortcuts'
import { useR58WebSocket } from '@/composables/useWebSocket'

// Initialize global keyboard shortcuts
const { registerDefaults } = useKeyboardShortcuts()

// Initialize WebSocket for real-time events
const { connect, disconnect, isConnected } = useR58WebSocket()

onMounted(() => {
  registerDefaults()
  // Connect WebSocket for real-time events
  connect()
})

onUnmounted(() => {
  disconnect()
})
</script>

<template>
  <AppShell>
    <RouterView />
  </AppShell>
  
  <!-- Global UI components -->
  <ToastContainer />
  <ShortcutsHelpModal />
</template>

