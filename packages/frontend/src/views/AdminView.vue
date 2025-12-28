<script setup lang="ts">
import { ref, onMounted } from 'vue'
import DeviceStatus from '@/components/admin/DeviceStatus.vue'
import LogViewer from '@/components/admin/LogViewer.vue'
import FleetOverview from '@/components/admin/FleetOverview.vue'

const activeTab = ref('status')

const tabs = [
  { id: 'status', label: 'Device Status' },
  { id: 'logs', label: 'Logs' },
  { id: 'fleet', label: 'Fleet' },
  { id: 'settings', label: 'Settings' },
]

async function downloadSupportBundle() {
  try {
    const response = await fetch('/api/v1/support/bundle', { method: 'POST' })
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `r58-support-bundle-${new Date().toISOString().slice(0, 10)}.zip`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    console.error('Failed to download support bundle:', e)
  }
}
</script>

<template>
  <div class="h-full flex flex-col">
    <!-- Header -->
    <header class="px-6 py-4 border-b border-r58-bg-tertiary bg-r58-bg-secondary">
      <h1 class="text-xl font-semibold mb-4">Admin</h1>
      
      <!-- Tabs -->
      <div class="flex gap-2">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          @click="activeTab = tab.id"
          class="px-4 py-2 rounded-t-lg transition-colors"
          :class="[
            activeTab === tab.id 
              ? 'bg-r58-bg-primary text-r58-text-primary' 
              : 'text-r58-text-secondary hover:text-r58-text-primary'
          ]"
        >
          {{ tab.label }}
        </button>
      </div>
    </header>
    
    <!-- Content -->
    <div class="flex-1 p-6 overflow-y-auto">
      <DeviceStatus v-if="activeTab === 'status'" />
      
      <div v-else-if="activeTab === 'logs'" class="card">
        <h2 class="text-lg font-semibold mb-4">System Logs</h2>
        <LogViewer />
      </div>
      
      <div v-else-if="activeTab === 'fleet'" class="card">
        <FleetOverview />
      </div>
      
      <div v-else-if="activeTab === 'settings'" class="card space-y-6">
        <div>
          <h2 class="text-lg font-semibold mb-4">Settings</h2>
          <p class="text-r58-text-secondary">Settings configuration coming soon.</p>
        </div>
        
        <div class="pt-4 border-t border-r58-bg-tertiary">
          <h3 class="font-medium mb-3">Support</h3>
          <button @click="downloadSupportBundle" class="btn">
            Download Support Bundle
          </button>
          <p class="text-sm text-r58-text-secondary mt-2">
            Downloads a ZIP file containing logs, configuration, and diagnostic information.
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

