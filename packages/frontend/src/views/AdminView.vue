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
  { id: 'design', label: 'Design' },
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
      
      <div v-else-if="activeTab === 'design'" class="design-panel">
        <h2 class="text-lg font-semibold text-preke-text mb-4">Design Resources</h2>
        <p class="text-preke-text-muted mb-6">Access design documentation, style guides, and archived designs.</p>
        
        <div class="design-links">
          <router-link to="/design-archive" class="design-link">
            <div class="design-link__icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4"/>
              </svg>
            </div>
            <div class="design-link__content">
              <h3>Design Archive</h3>
              <p>All past, current, and proposed design variations</p>
            </div>
            <svg class="design-link__arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 5l7 7-7 7"/>
            </svg>
          </router-link>
          
          <router-link to="/style-guide" class="design-link">
            <div class="design-link__icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01"/>
              </svg>
            </div>
            <div class="design-link__content">
              <h3>Style Guide</h3>
              <p>Colors, typography, and UI components</p>
            </div>
            <svg class="design-link__arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 5l7 7-7 7"/>
            </svg>
          </router-link>
          
          <router-link to="/style-guide-v2" class="design-link">
            <div class="design-link__icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
              </svg>
            </div>
            <div class="design-link__content">
              <h3>Style Guide V2</h3>
              <p>Glassmorphism design system</p>
            </div>
            <svg class="design-link__arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 5l7 7-7 7"/>
            </svg>
          </router-link>
          
          <router-link to="/proposals" class="design-link">
            <div class="design-link__icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z"/>
              </svg>
            </div>
            <div class="design-link__content">
              <h3>Design Proposals</h3>
              <p>Interactive preview of proposed designs</p>
            </div>
            <svg class="design-link__arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 5l7 7-7 7"/>
            </svg>
          </router-link>
          
          <router-link to="/experiments" class="design-link">
            <div class="design-link__icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"/>
              </svg>
            </div>
            <div class="design-link__content">
              <h3>Background Experiments</h3>
              <p>Experimental background animations</p>
            </div>
            <svg class="design-link__arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 5l7 7-7 7"/>
            </svg>
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.design-panel {
  background: var(--preke-surface);
  border: 1px solid var(--preke-border);
  border-radius: 16px;
  padding: 1.5rem;
}

.design-links {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.design-link {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem 1.25rem;
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid var(--preke-border);
  border-radius: 12px;
  text-decoration: none;
  transition: all 0.2s ease;
}

.design-link:hover {
  border-color: var(--preke-gold);
  background: rgba(224, 160, 48, 0.05);
  transform: translateX(4px);
}

.design-link__icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  background: rgba(224, 160, 48, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.design-link__icon svg {
  width: 22px;
  height: 22px;
  color: var(--preke-gold);
}

.design-link__content {
  flex: 1;
}

.design-link__content h3 {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--preke-text);
  margin-bottom: 0.125rem;
}

.design-link__content p {
  font-size: 0.8rem;
  color: var(--preke-text-muted);
}

.design-link__arrow {
  width: 20px;
  height: 20px;
  color: var(--preke-text-muted);
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.design-link:hover .design-link__arrow {
  color: var(--preke-gold);
  transform: translateX(4px);
}
</style>
