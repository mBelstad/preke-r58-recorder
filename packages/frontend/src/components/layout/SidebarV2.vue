<script setup lang="ts">
/**
 * Sidebar v2 - Clean navigation with prominent mode indicator
 * Uses design-system-v2 tokens
 */
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useRecorderStore } from '@/stores/recorder'
import { useCapabilitiesStore } from '@/stores/capabilities'
import { buildApiUrl, hasDeviceConfigured } from '@/lib/api'
import { toast } from '@/composables/useToast'
import ConfirmDialog from '@/components/shared/ConfirmDialog.vue'

const route = useRoute()
const router = useRouter()
const recorderStore = useRecorderStore()
const capabilitiesStore = useCapabilitiesStore()

// Mode switching state
const switching = ref(false)
const switchingTo = ref<'recorder' | 'mixer' | null>(null)
const confirmDialogRef = ref<InstanceType<typeof ConfirmDialog> | null>(null)
const pendingMode = ref<'recorder' | 'mixer' | null>(null)

// Periodic mode polling
let modePollingInterval: number | null = null
const MODE_POLL_INTERVAL = 15000

interface NavItem {
  id: string
  label: string
  path: string
  icon: string
  requiresMode?: 'recorder' | 'mixer'
}

const navItems: NavItem[] = [
  { id: 'studio', label: 'Home', path: '/', icon: 'home' },
  { id: 'recorder', label: 'Recorder', path: '/recorder', icon: 'record', requiresMode: 'recorder' },
  { id: 'mixer', label: 'Mixer', path: '/mixer', icon: 'mixer', requiresMode: 'mixer' },
  { id: 'library', label: 'Library', path: '/library', icon: 'folder' },
  { id: 'admin', label: 'Settings', path: '/admin', icon: 'settings' },
]

const currentPath = computed(() => route.path)
const currentMode = computed(() => capabilitiesStore.capabilities?.current_mode || 'idle')
const isRecording = computed(() => recorderStore.status === 'recording')

function isActive(path: string): boolean {
  return currentPath.value === path
}

function isModeActive(item: NavItem): boolean {
  if (!item.requiresMode) return false
  return item.requiresMode === currentMode.value
}

async function handleNavClick(item: NavItem, event: Event) {
  if (!item.requiresMode) return
  
  event.preventDefault()
  
  if (item.requiresMode === currentMode.value) {
    router.push(item.path)
    return
  }
  
  if (item.requiresMode === 'mixer' && isRecording.value) {
    pendingMode.value = 'mixer'
    confirmDialogRef.value?.open()
    return
  }
  
  await switchModeAndNavigate(item.requiresMode, item.path)
}

async function confirmModeSwitch() {
  if (pendingMode.value) {
    const path = pendingMode.value === 'mixer' ? '/mixer' : '/recorder'
    await switchModeAndNavigate(pendingMode.value, path)
  }
  pendingMode.value = null
}

function cancelModeSwitch() {
  pendingMode.value = null
}

async function switchModeAndNavigate(mode: 'recorder' | 'mixer', path: string) {
  if (switching.value) return
  
  if (!hasDeviceConfigured()) {
    router.push(path)
    return
  }
  
  switching.value = true
  switchingTo.value = mode
  
  try {
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 10000)
    
    const response = await fetch(buildApiUrl(`/api/mode/${mode}`), { 
      method: 'POST',
      signal: controller.signal
    }).finally(() => clearTimeout(timeoutId))
    
    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      throw new Error(data.detail || `Failed to switch to ${mode} mode`)
    }
    
    await capabilitiesStore.fetchCapabilities()
    
    const modeLabel = mode === 'mixer' ? 'Mixer' : 'Recorder'
    toast.success(`Switched to ${modeLabel} mode`)
    
    router.push(path)
  } catch (e) {
    if (e instanceof Error && e.name === 'AbortError') {
      console.warn('Mode switch timed out, navigating anyway')
      router.push(path)
    } else {
      const message = e instanceof Error ? e.message : 'Failed to switch mode'
      toast.error(message)
      console.error('Mode switch error:', e)
    }
  } finally {
    switching.value = false
    switchingTo.value = null
  }
}

onMounted(async () => {
  await capabilitiesStore.fetchCapabilities()
  
  if (hasDeviceConfigured()) {
    modePollingInterval = window.setInterval(async () => {
      if (switching.value) return
      await capabilitiesStore.fetchCapabilities()
    }, MODE_POLL_INTERVAL)
  }
})

onUnmounted(() => {
  if (modePollingInterval) {
    clearInterval(modePollingInterval)
    modePollingInterval = null
  }
})

// Mode colors
const modeColor = computed(() => {
  if (currentMode.value === 'recorder') return 'recorder'
  if (currentMode.value === 'mixer') return 'mixer'
  return 'idle'
})
</script>

<template>
  <aside class="sidebar">
    <!-- Logo -->
    <div class="sidebar__logo">
      <img src="/favicon.svg" alt="Preke" class="sidebar__logo-img" />
    </div>
    
    <!-- Mode Indicator (prominent) -->
    <div 
      v-if="currentMode !== 'idle'"
      class="sidebar__mode"
      :class="`sidebar__mode--${modeColor}`"
    >
      <span class="sidebar__mode-dot"></span>
      <span class="sidebar__mode-label">{{ currentMode === 'recorder' ? 'REC' : 'MIX' }}</span>
    </div>
    
    <!-- Navigation -->
    <nav class="sidebar__nav">
      <ul class="sidebar__nav-list">
        <li v-for="item in navItems" :key="item.id">
          <router-link
            :to="item.path"
            @click="handleNavClick(item, $event)"
            class="sidebar__nav-item"
            :class="{
              'sidebar__nav-item--active': isActive(item.path),
              'sidebar__nav-item--mode-active': isModeActive(item),
              'sidebar__nav-item--switching': switching && item.requiresMode
            }"
          >
            <!-- Loading spinner when switching -->
            <svg 
              v-if="switching && switchingTo === item.requiresMode" 
              class="sidebar__icon sidebar__icon--spinner" 
              fill="none" 
              viewBox="0 0 24 24"
            >
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            
            <!-- Icons -->
            <template v-else>
              <svg v-if="item.icon === 'home'" class="sidebar__icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/>
              </svg>
              <svg v-else-if="item.icon === 'record'" class="sidebar__icon" fill="currentColor" viewBox="0 0 24 24">
                <circle cx="12" cy="12" r="8"/>
              </svg>
              <svg v-else-if="item.icon === 'mixer'" class="sidebar__icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"/>
              </svg>
              <svg v-else-if="item.icon === 'folder'" class="sidebar__icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/>
              </svg>
              <svg v-else-if="item.icon === 'settings'" class="sidebar__icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
              </svg>
            </template>
            
            <span class="sidebar__nav-label">{{ item.label }}</span>
          </router-link>
        </li>
      </ul>
    </nav>
    
    <!-- Version -->
    <div class="sidebar__version">v2.0</div>
  </aside>
  
  <!-- Confirmation dialog -->
  <ConfirmDialog
    ref="confirmDialogRef"
    title="Stop Recording?"
    message="Switching to Mixer mode will stop all active recordings. Are you sure you want to continue?"
    confirm-text="Stop & Switch"
    cancel-text="Cancel"
    :danger="true"
    @confirm="confirmModeSwitch"
    @cancel="cancelModeSwitch"
  />
</template>

<style scoped>
@import '@/styles/design-system-v2.css';

.sidebar {
  width: 72px;
  background: var(--preke-bg-elevated);
  border-right: 1px solid var(--preke-border);
  display: flex;
  flex-direction: column;
  align-items: center;
}

/* Logo */
.sidebar__logo {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid var(--preke-border);
  width: 100%;
}

.sidebar__logo-img {
  width: 36px;
  height: 36px;
  filter: drop-shadow(0 0 8px rgba(224, 160, 48, 0.3));
}

/* Mode indicator */
.sidebar__mode {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: var(--preke-space-sm) var(--preke-space-xs);
  margin: var(--preke-space-sm) 0;
  border-radius: var(--preke-radius-md);
  width: calc(100% - 16px);
}

.sidebar__mode--recorder {
  background: rgba(212, 90, 90, 0.15);
  border: 1px solid rgba(212, 90, 90, 0.3);
}

.sidebar__mode--mixer {
  background: rgba(124, 58, 237, 0.15);
  border: 1px solid rgba(124, 58, 237, 0.3);
}

.sidebar__mode--idle {
  display: none;
}

.sidebar__mode-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.sidebar__mode--recorder .sidebar__mode-dot {
  background: var(--preke-red);
  animation: pulse-mode 2s ease-in-out infinite;
}

.sidebar__mode--mixer .sidebar__mode-dot {
  background: #7c3aed;
}

@keyframes pulse-mode {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.sidebar__mode-label {
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.sidebar__mode--recorder .sidebar__mode-label {
  color: var(--preke-red);
}

.sidebar__mode--mixer .sidebar__mode-label {
  color: #a78bfa;
}

/* Navigation */
.sidebar__nav {
  flex: 1;
  width: 100%;
  padding: var(--preke-space-sm);
}

.sidebar__nav-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--preke-space-xs);
}

.sidebar__nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: var(--preke-space-sm) var(--preke-space-xs);
  border-radius: var(--preke-radius-md);
  color: var(--preke-text-muted);
  text-decoration: none;
  transition: all 0.15s ease;
  cursor: pointer;
}

.sidebar__nav-item:hover {
  color: var(--preke-text-primary);
  background: var(--preke-glass-bg-light);
}

.sidebar__nav-item--active {
  color: var(--preke-gold);
  background: rgba(224, 160, 48, 0.1);
}

.sidebar__nav-item--mode-active {
  position: relative;
}

.sidebar__nav-item--switching {
  opacity: 0.6;
  cursor: wait;
}

.sidebar__icon {
  width: 22px;
  height: 22px;
}

.sidebar__icon--spinner {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.sidebar__nav-label {
  font-size: 10px;
  font-weight: 500;
}

/* Version */
.sidebar__version {
  padding: var(--preke-space-sm);
  font-size: 10px;
  color: var(--preke-text-subtle);
  letter-spacing: 0.02em;
}
</style>

