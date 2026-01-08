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
  { id: 'admin', label: 'Admin', path: '/admin', icon: 'admin' },
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
    
    const response = await fetch(await buildApiUrl(`/api/mode/${mode}`), { 
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
              'sidebar__nav-item--mixer': item.requiresMode === 'mixer',
              'sidebar__nav-item--admin': item.id === 'admin'
            }"
          >
            <!-- Glow effect for active -->
            <span v-if="isActive(item.path)" class="sidebar__nav-glow"></span>
            
            <!-- Icon wrapper -->
            <div class="sidebar__icon-wrapper">
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
                  <!-- Video camera with REC dot -->
                  <rect x="2" y="5" width="14" height="12" rx="2"/>
                  <path d="M16 9l4-2v8l-4-2"/>
                  <circle cx="6" cy="8" r="2" fill="currentColor" stroke="none"/>
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
                <svg v-else-if="item.icon === 'admin'" class="sidebar__icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
                </svg>
              </template>
            </div>
            
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
  position: relative;
  width: 72px;
  min-width: 72px;
  
  /* Glass effect - adapts to theme - softer, more 3D */
  background: linear-gradient(
    90deg,
    var(--preke-bg-elevated) 0%,
    var(--preke-bg-surface) 30%,
    var(--preke-bg-surface) 70%,
    var(--preke-bg-elevated) 100%
  );
  backdrop-filter: blur(20px) saturate(150%);
  -webkit-backdrop-filter: blur(20px) saturate(150%);
  
  /* Border and outside shadow - adapts to theme */
  border-right: 1px solid var(--preke-border);
  box-shadow: 
    /* Inner left highlight */
    inset 1px 0 0 var(--preke-border-light),
    /* Outside shadow for depth */
    4px 0 30px rgba(0, 0, 0, 0.2),
    8px 0 50px rgba(0, 0, 0, 0.1);
  
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 8px 0;
  z-index: 90;
}

/* Subtle left edge reflection - adapts to theme */
.sidebar::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  bottom: 0;
  width: 1px;
  background: linear-gradient(
    180deg,
    transparent 0%,
    var(--preke-border-light) 50%,
    transparent 100%
  );
  pointer-events: none;
}

/* Navigation */
.sidebar__nav {
  flex: 1;
  width: 100%;
  padding: 24px 8px 0 8px; /* Added top padding to move items lower */
  display: flex;
  justify-content: center;
}

.sidebar__nav-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px; /* Increased from 4px to 8px */
}

/* Premium buttons - refined design */
.sidebar__nav-item {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  width: 56px;
  height: 56px;
  padding: 6px;
  border-radius: 12px;
  color: var(--preke-text-muted);
  text-decoration: none;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: pointer;
  overflow: hidden;
  
  /* Premium design - refined borders and depth */
  background: linear-gradient(
    145deg,
    rgba(255, 255, 255, 0.1) 0%,
    rgba(255, 255, 255, 0.05) 50%,
    rgba(255, 255, 255, 0.02) 100%
  );
  border: 1.5px solid rgba(255, 255, 255, 0.12);
  box-shadow: 
    /* Depth shadow */
    0 4px 12px rgba(0, 0, 0, 0.3),
    0 2px 4px rgba(0, 0, 0, 0.2),
    /* Inner highlights */
    inset 0 1px 2px rgba(255, 255, 255, 0.15),
    inset 0 -1px 1px rgba(0, 0, 0, 0.1);
}

/* Hover effect - premium refined */
.sidebar__nav-item:hover {
  color: var(--preke-text);
  transform: translateY(-2px);
  background: linear-gradient(
    145deg,
    rgba(255, 255, 255, 0.15) 0%,
    rgba(255, 255, 255, 0.08) 50%,
    rgba(255, 255, 255, 0.04) 100%
  );
  border-color: rgba(255, 255, 255, 0.2);
  box-shadow: 
    0 6px 16px rgba(0, 0, 0, 0.4),
    0 3px 6px rgba(0, 0, 0, 0.3),
    inset 0 1px 2px rgba(255, 255, 255, 0.2),
    inset 0 -1px 1px rgba(0, 0, 0, 0.15);
}

.sidebar__nav-item:active {
  transform: translateY(0);
  box-shadow: 
    inset 0 1px 0 var(--preke-border),
    inset 0 2px 4px rgba(0, 0, 0, 0.1),
    var(--preke-shadow-xs);
}

/* Active state - premium with gold accent */
.sidebar__nav-item--active {
  color: var(--preke-gold);
  background: linear-gradient(
    145deg,
    rgba(224, 160, 48, 0.25) 0%,
    rgba(224, 160, 48, 0.18) 50%,
    rgba(224, 160, 48, 0.12) 100%
  );
  border: 1.5px solid rgba(224, 160, 48, 0.5);
  box-shadow: 
    /* Gold glow */
    0 0 30px rgba(224, 160, 48, 0.25),
    0 0 60px rgba(224, 160, 48, 0.1),
    /* Depth */
    0 4px 12px rgba(0, 0, 0, 0.3),
    0 2px 4px rgba(0, 0, 0, 0.2),
    /* Inner highlights */
    inset 0 1px 2px rgba(255, 255, 255, 0.2),
    inset 0 -1px 1px rgba(0, 0, 0, 0.1);
}

.sidebar__nav-item--active:hover {
  background: linear-gradient(
    145deg,
    rgba(224, 160, 48, 0.3) 0%,
    rgba(224, 160, 48, 0.22) 50%,
    rgba(224, 160, 48, 0.15) 100%
  );
  box-shadow: 
    0 0 40px rgba(224, 160, 48, 0.3),
    0 0 80px rgba(224, 160, 48, 0.15),
    0 6px 16px rgba(0, 0, 0, 0.4),
    0 3px 6px rgba(0, 0, 0, 0.3),
    inset 0 1px 2px rgba(255, 255, 255, 0.25),
    inset 0 -1px 1px rgba(0, 0, 0, 0.15);
  transform: translateY(-2px);
}

/* Recorder mode active state - premium with red accent */
.sidebar__nav-item--active.sidebar__nav-item--recorder {
  color: var(--preke-red);
  background: linear-gradient(
    145deg,
    rgba(212, 90, 90, 0.25) 0%,
    rgba(212, 90, 90, 0.18) 50%,
    rgba(212, 90, 90, 0.12) 100%
  );
  border: 1.5px solid rgba(212, 90, 90, 0.5);
  box-shadow: 
    0 0 30px rgba(212, 90, 90, 0.25),
    0 0 60px rgba(212, 90, 90, 0.1),
    0 4px 12px rgba(0, 0, 0, 0.3),
    0 2px 4px rgba(0, 0, 0, 0.2),
    inset 0 1px 2px rgba(255, 255, 255, 0.2),
    inset 0 -1px 1px rgba(0, 0, 0, 0.1);
}

.sidebar__nav-item--active.sidebar__nav-item--recorder:hover {
  background: linear-gradient(
    145deg,
    rgba(212, 90, 90, 0.3) 0%,
    rgba(212, 90, 90, 0.22) 50%,
    rgba(212, 90, 90, 0.15) 100%
  );
  box-shadow: 
    0 0 40px rgba(212, 90, 90, 0.3),
    0 0 80px rgba(212, 90, 90, 0.15),
    0 6px 16px rgba(0, 0, 0, 0.4),
    0 3px 6px rgba(0, 0, 0, 0.3),
    inset 0 1px 2px rgba(255, 255, 255, 0.25),
    inset 0 -1px 1px rgba(0, 0, 0, 0.15);
  transform: translateY(-2px);
}

/* Mixer mode active state - premium with violet accent */
.sidebar__nav-item--active.sidebar__nav-item--mixer {
  color: #a78bfa;
  background: linear-gradient(
    145deg,
    rgba(124, 58, 237, 0.25) 0%,
    rgba(124, 58, 237, 0.18) 50%,
    rgba(124, 58, 237, 0.12) 100%
  );
  border: 1.5px solid rgba(124, 58, 237, 0.5);
  box-shadow: 
    0 0 30px rgba(124, 58, 237, 0.25),
    0 0 60px rgba(124, 58, 237, 0.1),
    0 4px 12px rgba(0, 0, 0, 0.3),
    0 2px 4px rgba(0, 0, 0, 0.2),
    inset 0 1px 2px rgba(255, 255, 255, 0.2),
    inset 0 -1px 1px rgba(0, 0, 0, 0.1);
}

.sidebar__nav-item--active.sidebar__nav-item--mixer:hover {
  background: linear-gradient(
    145deg,
    rgba(124, 58, 237, 0.3) 0%,
    rgba(124, 58, 237, 0.22) 50%,
    rgba(124, 58, 237, 0.15) 100%
  );
  box-shadow: 
    0 0 40px rgba(124, 58, 237, 0.3),
    0 0 80px rgba(124, 58, 237, 0.15),
    0 6px 16px rgba(0, 0, 0, 0.4),
    0 3px 6px rgba(0, 0, 0, 0.3),
    inset 0 1px 2px rgba(255, 255, 255, 0.25),
    inset 0 -1px 1px rgba(0, 0, 0, 0.15);
  transform: translateY(-2px);
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

/* Admin active state - premium with cyan accent */
.sidebar__nav-item--active.sidebar__nav-item--admin {
  color: #06b6d4;
  background: linear-gradient(
    145deg,
    rgba(6, 182, 212, 0.25) 0%,
    rgba(6, 182, 212, 0.18) 50%,
    rgba(6, 182, 212, 0.12) 100%
  );
  border: 1.5px solid rgba(6, 182, 212, 0.5);
  box-shadow: 
    0 0 30px rgba(6, 182, 212, 0.25),
    0 0 60px rgba(6, 182, 212, 0.1),
    0 4px 12px rgba(0, 0, 0, 0.3),
    0 2px 4px rgba(0, 0, 0, 0.2),
    inset 0 1px 2px rgba(255, 255, 255, 0.2),
    inset 0 -1px 1px rgba(0, 0, 0, 0.1);
}

.sidebar__nav-item--active.sidebar__nav-item--admin:hover {
  background: linear-gradient(
    145deg,
    rgba(6, 182, 212, 0.3) 0%,
    rgba(6, 182, 212, 0.22) 50%,
    rgba(6, 182, 212, 0.15) 100%
  );
  box-shadow: 
    0 0 40px rgba(6, 182, 212, 0.3),
    0 0 80px rgba(6, 182, 212, 0.15),
    0 6px 16px rgba(0, 0, 0, 0.4),
    0 3px 6px rgba(0, 0, 0, 0.3),
    inset 0 1px 2px rgba(255, 255, 255, 0.25),
    inset 0 -1px 1px rgba(0, 0, 0, 0.15);
  transform: translateY(-2px);
}

.sidebar__nav-item--admin .sidebar__nav-glow {
  background: radial-gradient(
    ellipse at center,
    rgba(6, 182, 212, 0.2) 0%,
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
  width: 24px;
  height: 24px;
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
  position: absolute;
  bottom: 4px;
  left: 50%;
  transform: translateX(-50%) translateY(8px);
  font-size: 9px;
  font-weight: 500;
  letter-spacing: 0.01em;
  opacity: 0;
  white-space: nowrap;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  pointer-events: none;
  line-height: 1;
}

.sidebar__nav-item:hover .sidebar__nav-label {
  opacity: 1;
  transform: translateX(-50%) translateY(0);
}

.sidebar__nav-item:hover .sidebar__icon-wrapper {
  transform: translateY(-8px);
}

.sidebar__icon-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

/* Version - subtle glass pill - adapts to theme */
.sidebar__version {
  padding: 6px 12px;
  margin-bottom: 8px;
  font-size: 10px;
  color: var(--preke-text-subtle);
  letter-spacing: 0.03em;
  background: var(--preke-glass-light);
  border-radius: 8px;
  border: 1px solid var(--preke-border);
}
</style>
