<script setup lang="ts">
import { onMounted } from 'vue'
import { RouterView } from 'vue-router'
import AppShell from '@/components/layout/AppShell.vue'
import ToastContainer from '@/components/shared/ToastContainer.vue'
import ShortcutsHelpModal from '@/components/shared/ShortcutsHelpModal.vue'
import { useKeyboardShortcuts } from '@/composables/useKeyboardShortcuts'

// Initialize global keyboard shortcuts
const { registerDefaults } = useKeyboardShortcuts()

onMounted(() => {
  registerDefaults()
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

