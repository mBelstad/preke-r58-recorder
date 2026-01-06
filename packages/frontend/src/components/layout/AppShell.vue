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
  <div v-if="isMinimalLayout" class="h-full">
    <slot />
  </div>
  
  <div v-else class="h-full flex bg-preke-bg">
    <!-- Sidebar -->
    <Sidebar />
    
    <!-- Main content area -->
    <div class="flex-1 flex flex-col min-w-0">
      <!-- Status bar -->
      <StatusBar />
      
      <!-- Page content -->
      <main class="flex-1 overflow-hidden">
        <slot />
      </main>
    </div>
  </div>
</template>

