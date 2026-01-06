<script setup lang="ts">
/**
 * Sidebar v2 - Clean navigation with square buttons
 * Logo and mode indicator are in the top bar
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
</script>

<template>
  <aside class="sidebar">
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
              'sidebar__nav-item--switching': switching && item.requiresMode,
              'sidebar__nav-item--recorder': item.requiresMode === 'recorder',
              'sidebar__nav-item--mixer': item.requiresMode === 'mixer'
            }"
          >
            <!-- Glow effect for active -->
            <span v-if="isActive(item.path)" class="sidebar__nav-glow"></span>
            
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
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/>
              </svg>
              <svg v-else-if="item.icon === 'record'" class="sidebar__icon" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.8">
                <!-- Multi-track recording bars -->
                <rect x="2" y="4" width="14" height="4" rx="1"/>
                <rect x="2" y="10" width="14" height="4" rx="1"/>
                <rect x="2" y="16" width="14" height="4" rx="1"/>
                <!-- Recording indicator circle -->
                <circle cx="20" cy="6" r="3" fill="currentColor" stroke="none"/>
                <!-- Camera lens element -->
                <circle cx="20" cy="15" r="3"/>
                <circle cx="20" cy="15" r="1.5" fill="currentColor" stroke="none"/>
              </svg>
              <!-- Video Mixer Icon (grid layout with broadcast symbol) -->
              <svg v-else-if="item.icon === 'mixer'" class="sidebar__icon" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.8">
                <rect x="2" y="2" width="9" height="6" rx="1"/>
                <rect x="13" y="2" width="9" height="6" rx="1"/>
                <rect x="2" y="10" width="9" height="6" rx="1"/>
                <rect x="13" y="10" width="9" height="6" rx="1"/>
                <circle cx="12" cy="20" r="2" fill="currentColor"/>
                <path d="M9 19.5a4 4 0 0 1 6 0" stroke-linecap="round"/>
              </svg>
              <svg v-else-if="item.icon === 'folder'" class="sidebar__icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/>
              </svg>
              <svg v-else-if="item.icon === 'settings'" class="sidebar__icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
              </svg>
            </template>
            
            <span class="sidebar__nav-label">{{ item.label }}</span>
          </router-link>
        </li>
      </ul>
    </nav>
    
    <!-- Version at bottom -->
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
.sidebar {
  width: 72px;
  min-width: 72px;
  background: var(--preke-surface);
  border-right: 1px solid var(--preke-surface-border);
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 8px 0;
}

/* Navigation */
.sidebar__nav {
  flex: 1;
  width: 100%;
  padding: 0 8px;
}

.sidebar__nav-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

/* Square 1:1 buttons */
.sidebar__nav-item {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  width: 56px;
  height: 56px;
  border-radius: 12px;
  color: var(--preke-text-muted);
  text-decoration: none;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: pointer;
  overflow: hidden;
}

/* Hover effect - glass highlight */
.sidebar__nav-item:hover {
  color: var(--preke-text);
  background: linear-gradient(
    135deg,
    rgba(255, 255, 255, 0.08) 0%,
    rgba(255, 255, 255, 0.03) 100%
  );
  box-shadow: 
    inset 0 1px 0 rgba(255, 255, 255, 0.1),
    0 4px 12px rgba(0, 0, 0, 0.15);
  transform: translateY(-1px);
}

.sidebar__nav-item:active {
  transform: translateY(0);
  box-shadow: 
    inset 0 1px 0 rgba(255, 255, 255, 0.05),
    0 2px 4px rgba(0, 0, 0, 0.1);
}

/* Active state - default gold accent */
.sidebar__nav-item--active {
  color: var(--preke-gold);
  background: linear-gradient(
    135deg,
    rgba(224, 160, 48, 0.15) 0%,
    rgba(224, 160, 48, 0.08) 100%
  );
  border: 1px solid rgba(224, 160, 48, 0.2);
  box-shadow: 
    0 0 20px rgba(224, 160, 48, 0.12),
    inset 0 1px 0 rgba(255, 255, 255, 0.08);
}

.sidebar__nav-item--active:hover {
  background: linear-gradient(
    135deg,
    rgba(224, 160, 48, 0.2) 0%,
    rgba(224, 160, 48, 0.1) 100%
  );
  box-shadow: 
    0 0 25px rgba(224, 160, 48, 0.18),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
}

/* Recorder mode active state - red accent (matches top bar) */
.sidebar__nav-item--active.sidebar__nav-item--recorder {
  color: var(--preke-red);
  background: linear-gradient(
    135deg,
    rgba(212, 90, 90, 0.15) 0%,
    rgba(212, 90, 90, 0.08) 100%
  );
  border: 1px solid rgba(212, 90, 90, 0.3);
  box-shadow: 
    0 0 20px rgba(212, 90, 90, 0.12),
    inset 0 1px 0 rgba(255, 255, 255, 0.08);
}

.sidebar__nav-item--active.sidebar__nav-item--recorder:hover {
  background: linear-gradient(
    135deg,
    rgba(212, 90, 90, 0.2) 0%,
    rgba(212, 90, 90, 0.1) 100%
  );
  box-shadow: 
    0 0 25px rgba(212, 90, 90, 0.18),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
}

/* Mixer mode active state - violet accent (matches top bar) */
.sidebar__nav-item--active.sidebar__nav-item--mixer {
  color: #a78bfa;
  background: linear-gradient(
    135deg,
    rgba(124, 58, 237, 0.15) 0%,
    rgba(124, 58, 237, 0.08) 100%
  );
  border: 1px solid rgba(124, 58, 237, 0.3);
  box-shadow: 
    0 0 20px rgba(124, 58, 237, 0.12),
    inset 0 1px 0 rgba(255, 255, 255, 0.08);
}

.sidebar__nav-item--active.sidebar__nav-item--mixer:hover {
  background: linear-gradient(
    135deg,
    rgba(124, 58, 237, 0.2) 0%,
    rgba(124, 58, 237, 0.1) 100%
  );
  box-shadow: 
    0 0 25px rgba(124, 58, 237, 0.18),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
}

/* Glow effect behind active item */
.sidebar__nav-glow {
  position: absolute;
  inset: 0;
  background: radial-gradient(
    ellipse at center,
    rgba(224, 160, 48, 0.2) 0%,
    transparent 70%
  );
  pointer-events: none;
  animation: glow-pulse 3s ease-in-out infinite;
}

/* Recorder glow */
.sidebar__nav-item--recorder .sidebar__nav-glow {
  background: radial-gradient(
    ellipse at center,
    rgba(212, 90, 90, 0.2) 0%,
    transparent 70%
  );
}

/* Mixer glow */
.sidebar__nav-item--mixer .sidebar__nav-glow {
  background: radial-gradient(
    ellipse at center,
    rgba(124, 58, 237, 0.2) 0%,
    transparent 70%
  );
}

@keyframes glow-pulse {
  0%, 100% { opacity: 0.5; }
  50% { opacity: 1; }
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
  transition: transform 0.2s ease;
}

.sidebar__nav-item:hover .sidebar__icon {
  transform: scale(1.1);
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
  letter-spacing: 0.01em;
}

/* Version */
.sidebar__version {
  padding: 12px;
  font-size: 10px;
  color: var(--preke-text-subtle);
  letter-spacing: 0.03em;
  opacity: 0.5;
}
</style>
