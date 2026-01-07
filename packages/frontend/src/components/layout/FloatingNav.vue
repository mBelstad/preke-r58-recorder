<script setup lang="ts">
/**
 * Floating Navigation - Icons with text on hover
 * Positioned on the left side, lower to avoid secondary headers
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
  return currentMode.value === item.requiresMode
}

function isVisible(item: NavItem): boolean {
  // Always show home, library, and admin
  if (!item.requiresMode) return true
  
  // Show mode-specific items only if device is configured
  if (!hasDeviceConfigured()) return false
  
  // Show if current mode matches or if switching to that mode
  return currentMode.value === item.requiresMode || switchingTo.value === item.requiresMode
}

async function handleNavClick(item: NavItem, event: MouseEvent) {
  event.preventDefault()
  
  // If already on this route, do nothing
  if (isActive(item.path)) return
  
  // If item requires a specific mode, check if we need to switch
  if (item.requiresMode && currentMode.value !== item.requiresMode) {
    // Check if we're currently recording
    if (isRecording.value && currentMode.value === 'recorder') {
      pendingMode.value = item.requiresMode
      confirmDialogRef.value?.open()
      return
    }
    
    // Switch mode
    await switchMode(item.requiresMode)
  }
  
  // Navigate
  router.push(item.path)
}

async function switchMode(mode: 'recorder' | 'mixer'): Promise<void> {
  if (switching.value) return
  
  switching.value = true
  switchingTo.value = mode
  
  try {
    const deviceUrl = buildApiUrl('/api/v1/mode')
    const response = await fetch(deviceUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode })
    })
    
    if (!response.ok) {
      throw new Error(`Failed to switch mode: ${response.statusText}`)
    }
    
    // Poll for mode change
    await pollModeChange(mode)
    
    toast.success(`Switched to ${mode} mode`)
  } catch (error) {
    console.error('Mode switch error:', error)
    toast.error(`Failed to switch to ${mode} mode`)
    switching.value = false
    switchingTo.value = null
  }
}

async function pollModeChange(targetMode: 'recorder' | 'mixer'): Promise<void> {
  return new Promise((resolve, reject) => {
    const startTime = Date.now()
    const timeout = 30000 // 30 second timeout
    
    const checkMode = async () => {
      try {
        const deviceUrl = buildApiUrl('/api/v1/capabilities')
        const response = await fetch(deviceUrl)
        
        if (!response.ok) {
          throw new Error('Failed to fetch capabilities')
        }
        
        const data = await response.json()
        const currentMode = data.current_mode
        
        if (currentMode === targetMode) {
          switching.value = false
          switchingTo.value = null
          capabilitiesStore.refreshCapabilities()
          resolve()
          return
        }
        
        // Timeout check
        if (Date.now() - startTime > timeout) {
          switching.value = false
          switchingTo.value = null
          reject(new Error('Mode switch timeout'))
          return
        }
        
        // Check again in 500ms
        setTimeout(checkMode, 500)
      } catch (error) {
        switching.value = false
        switchingTo.value = null
        reject(error)
      }
    }
    
    checkMode()
  })
}

async function confirmModeSwitch() {
  if (!pendingMode.value) return
  
  const mode = pendingMode.value
  pendingMode.value = null
  
  await switchMode(mode)
  
  // Navigate after mode switch
  const targetItem = navItems.find(item => item.requiresMode === mode)
  if (targetItem) {
    router.push(targetItem.path)
  }
}

function cancelModeSwitch() {
  pendingMode.value = null
}

// Start mode polling when component mounts
onMounted(() => {
  if (hasDeviceConfigured()) {
    modePollingInterval = window.setInterval(() => {
      capabilitiesStore.refreshCapabilities()
    }, MODE_POLL_INTERVAL)
  }
})

onUnmounted(() => {
  if (modePollingInterval) {
    clearInterval(modePollingInterval)
  }
})
</script>

<template>
  <nav class="floating-nav">
    <div class="floating-nav__container">
      <router-link
        v-for="item in navItems.filter(isVisible)"
        :key="item.id"
        :to="item.path"
        class="floating-nav__item"
        :class="{
          'floating-nav__item--active': isActive(item.path),
          'floating-nav__item--mode-active': isModeActive(item),
          'floating-nav__item--switching': switching && switchingTo === item.requiresMode
        }"
        @click="handleNavClick(item, $event)"
      >
        <!-- Icon -->
        <div class="floating-nav__icon-wrapper">
          <svg
            v-if="switching && switchingTo === item.requiresMode"
            class="floating-nav__icon floating-nav__icon--spinner" 
            fill="none" 
            viewBox="0 0 24 24"
          >
            <circle class="spinner-circle" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-dasharray="32" stroke-dashoffset="32">
              <animate attributeName="stroke-dasharray" dur="2s" values="0 32;16 16;0 32;0 32" repeatCount="indefinite"/>
              <animate attributeName="stroke-dashoffset" dur="2s" values="0;-16;-32;-32" repeatCount="indefinite"/>
            </circle>
          </svg>
          
          <svg v-else-if="item.icon === 'home'" class="floating-nav__icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/>
          </svg>
          <svg v-else-if="item.icon === 'record'" class="floating-nav__icon" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.8">
            <!-- Video camera with REC dot -->
            <rect x="2" y="5" width="14" height="12" rx="2"/>
            <path d="M16 9l4-2v8l-4-2"/>
            <circle cx="6" cy="8" r="2" fill="currentColor" stroke="none"/>
          </svg>
          <svg v-else-if="item.icon === 'mixer'" class="floating-nav__icon" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.8">
            <rect x="2" y="2" width="9" height="6" rx="1"/>
            <rect x="13" y="2" width="9" height="6" rx="1"/>
            <rect x="2" y="10" width="9" height="6" rx="1"/>
            <rect x="13" y="10" width="9" height="6" rx="1"/>
          </svg>
          <svg v-else-if="item.icon === 'folder'" class="floating-nav__icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/>
          </svg>
          <svg v-else-if="item.icon === 'admin'" class="floating-nav__icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
          </svg>
        </div>
        
        <!-- Text label (shown on hover) -->
        <span class="floating-nav__label">{{ item.label }}</span>
        
        <!-- Active indicator glow -->
        <div 
          v-if="isActive(item.path) || isModeActive(item)"
          class="floating-nav__glow"
          :class="{
            'floating-nav__glow--recorder': item.id === 'recorder',
            'floating-nav__glow--mixer': item.id === 'mixer',
            'floating-nav__glow--library': item.id === 'library',
            'floating-nav__glow--admin': item.id === 'admin'
          }"
        ></div>
      </router-link>
    </div>
    
    <!-- Mode switch confirmation dialog -->
    <ConfirmDialog
      ref="confirmDialogRef"
      title="Stop Recording?"
      message="Switching modes will stop the current recording. Are you sure you want to continue?"
      confirm-text="Stop & Switch"
      cancel-text="Cancel"
      :danger="true"
      @confirm="confirmModeSwitch"
      @cancel="cancelModeSwitch"
    />
  </nav>
</template>

<style scoped>
.floating-nav {
  position: fixed;
  left: 0;
  top: 120px; /* Position below main top bar and secondary headers */
  z-index: 100;
  pointer-events: none; /* Allow clicks to pass through container */
}

.floating-nav__container {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 0 12px;
  pointer-events: auto; /* Re-enable clicks on container */
}

.floating-nav__item {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 72px;
  height: 72px;
  padding: 0;
  border-radius: 16px;
  color: var(--preke-text-muted);
  text-decoration: none;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: pointer;
  overflow: visible;
  
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

/* Hover effect - icon moves up, text appears */
.floating-nav__item:hover {
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
    0 2px 8px rgba(0, 0, 0, 0.3),
    inset 0 1px 3px rgba(255, 255, 255, 0.2),
    inset 0 -1px 2px rgba(0, 0, 0, 0.15);
}

.floating-nav__item:hover .floating-nav__icon-wrapper {
  transform: translateY(-12px);
}

.floating-nav__item:hover .floating-nav__label {
  opacity: 1;
  transform: translateX(-50%) translateY(0);
}

/* Active state */
.floating-nav__item--active,
.floating-nav__item--mode-active {
  color: var(--preke-text);
  background: linear-gradient(
    145deg,
    rgba(255, 255, 255, 0.12) 0%,
    rgba(255, 255, 255, 0.06) 50%,
    rgba(255, 255, 255, 0.03) 100%
  );
  border-color: rgba(255, 255, 255, 0.25);
  box-shadow: 
    0 4px 16px rgba(0, 0, 0, 0.4),
    0 2px 8px rgba(0, 0, 0, 0.3),
    inset 0 1px 3px rgba(255, 255, 255, 0.2),
    inset 0 -1px 2px rgba(0, 0, 0, 0.15);
}

.floating-nav__item--switching {
  opacity: 0.6;
  cursor: wait;
}

.floating-nav__icon-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.floating-nav__icon {
  width: 32px;
  height: 32px;
  transition: transform 0.2s ease;
}

.floating-nav__icon--spinner {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.floating-nav__label {
  position: absolute;
  bottom: 6px;
  left: 50%;
  transform: translateX(-50%) translateY(12px);
  font-size: 10px;
  font-weight: 500;
  opacity: 0;
  white-space: nowrap;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  pointer-events: none;
  line-height: 1;
}

/* Active indicator glows */
.floating-nav__glow {
  position: absolute;
  inset: -2px;
  border-radius: 16px;
  opacity: 0;
  transition: opacity 0.3s ease;
  pointer-events: none;
  z-index: -1;
}

.floating-nav__item--active .floating-nav__glow,
.floating-nav__item--mode-active .floating-nav__glow {
  opacity: 1;
}

.floating-nav__glow--recorder {
  background: radial-gradient(
    ellipse at center,
    rgba(239, 68, 68, 0.2) 0%,
    transparent 70%
  );
}

.floating-nav__glow--mixer {
  background: radial-gradient(
    ellipse at center,
    rgba(139, 92, 246, 0.2) 0%,
    transparent 70%
  );
}

.floating-nav__glow--library {
  background: radial-gradient(
    ellipse at center,
    rgba(224, 160, 48, 0.2) 0%,
    transparent 70%
  );
}

.floating-nav__glow--admin {
  background: radial-gradient(
    ellipse at center,
    rgba(6, 182, 212, 0.2) 0%,
    transparent 70%
  );
}

/* Light mode */
[data-theme="light"] .floating-nav__item {
  background: linear-gradient(
    145deg,
    rgba(255, 255, 255, 0.8) 0%,
    rgba(255, 255, 255, 0.6) 50%,
    rgba(255, 255, 255, 0.4) 100%
  );
  border-color: rgba(0, 0, 0, 0.1);
  box-shadow: 
    0 4px 12px rgba(0, 0, 0, 0.1),
    0 2px 4px rgba(0, 0, 0, 0.05),
    inset 0 1px 2px rgba(255, 255, 255, 0.9),
    inset 0 -1px 1px rgba(0, 0, 0, 0.05);
}

[data-theme="light"] .floating-nav__item:hover {
  background: linear-gradient(
    145deg,
    rgba(255, 255, 255, 0.95) 0%,
    rgba(255, 255, 255, 0.8) 50%,
    rgba(255, 255, 255, 0.6) 100%
  );
  border-color: rgba(0, 0, 0, 0.15);
}

[data-theme="light"] .floating-nav__item--active,
[data-theme="light"] .floating-nav__item--mode-active {
  background: linear-gradient(
    145deg,
    rgba(255, 255, 255, 0.9) 0%,
    rgba(255, 255, 255, 0.7) 50%,
    rgba(255, 255, 255, 0.5) 100%
  );
  border-color: rgba(0, 0, 0, 0.2);
}
</style>

