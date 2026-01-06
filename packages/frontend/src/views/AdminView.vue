<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import DeviceStatus from '@/components/admin/DeviceStatus.vue'
import LogViewer from '@/components/admin/LogViewer.vue'
import FleetOverview from '@/components/admin/FleetOverview.vue'
import SystemMonitor from '@/components/admin/SystemMonitor.vue'
import SettingsPanel from '@/components/admin/SettingsPanel.vue'

const route = useRoute()
const activeTab = ref('system')

const tabs = [
  { id: 'system', label: 'System' },
  { id: 'status', label: 'Device Status' },
  { id: 'logs', label: 'Logs' },
  { id: 'fleet', label: 'Fleet' },
  { id: 'settings', label: 'Settings' },
]

// Handle tab query parameter
onMounted(() => {
  const tabParam = route.query.tab as string | undefined
  if (tabParam && tabs.some(t => t.id === tabParam)) {
    activeTab.value = tabParam
  }
})

async function downloadSupportBundle() {
  // Support bundle endpoint not available on device
  // Could be implemented in Electron's main process instead
  alert('Support bundle download not available in this version. Use the Electron app menu: Help > Export Support Bundle')
}
</script>

<template>
  <div class="h-full flex flex-col bg-preke-bg">
    <!-- Header -->
    <header class="px-6 py-4 border-b border-preke-surface-border bg-preke-surface/50 backdrop-blur-sm">
      <h1 class="text-xl font-semibold text-preke-text mb-4">Settings</h1>
      
      <!-- Tabs -->
      <div class="flex gap-1">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          @click="activeTab = tab.id"
          class="px-4 py-2 rounded-lg transition-all duration-200 font-medium text-sm"
          :class="[
            activeTab === tab.id 
              ? 'bg-preke-gold/20 text-preke-gold border border-preke-gold/30' 
              : 'text-preke-text-muted hover:text-preke-text hover:bg-preke-surface'
          ]"
        >
          {{ tab.label }}
        </button>
      </div>
    </header>
    
    <!-- Content -->
    <div class="flex-1 p-6 overflow-y-auto">
      <SystemMonitor v-if="activeTab === 'system'" />
      
      <DeviceStatus v-else-if="activeTab === 'status'" />
      
      <div v-else-if="activeTab === 'logs'" class="glass-card p-6 rounded-xl">
        <h2 class="text-lg font-semibold text-preke-text mb-4">System Logs</h2>
        <LogViewer />
      </div>
      
      <div v-else-if="activeTab === 'fleet'" class="glass-card p-6 rounded-xl">
        <FleetOverview />
      </div>
      
      <SettingsPanel v-else-if="activeTab === 'settings'" />
    </div>
  </div>
</template>

