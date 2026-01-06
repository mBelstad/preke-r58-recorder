<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
// Use v2 components for the new design system
import Sidebar from './SidebarV2.vue'
import StatusBar from './StatusBarV2.vue'

const route = useRoute()
const router = useRouter()

// Check if we should show minimal layout (e.g., guest page)
const isMinimalLayout = computed(() => route.meta.layout === 'minimal')
</script>

<template>
  <div v-if="isMinimalLayout" class="minimal-layout">
    <slot />
  </div>
  
  <div v-else class="app-shell">
    <!-- Full-width status bar at top -->
    <StatusBar />
    
    <!-- Sidebar + Content below -->
    <div class="app-shell__body">
      <!-- Sidebar -->
      <Sidebar />
      
      <!-- Page content -->
      <main class="app-shell__content">
        <slot />
      </main>
    </div>
  </div>
</template>

<style scoped>
/* Minimal layout - full screen for pages like device setup */
.minimal-layout {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.app-shell {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--preke-bg);
}

.app-shell__body {
  flex: 1;
  display: flex;
  min-height: 0; /* Important for flex children to scroll properly */
}

.app-shell__content {
  flex: 1;
  overflow: hidden;
  min-width: 0;
}
</style>
