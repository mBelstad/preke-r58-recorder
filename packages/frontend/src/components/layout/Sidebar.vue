<script setup lang="ts">
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
const switchingTo = ref<'recorder' | 'mixer' | null>(null) // Track which mode we're switching to
const confirmDialogRef = ref<InstanceType<typeof ConfirmDialog> | null>(null)
const pendingMode = ref<'recorder' | 'mixer' | null>(null)

// Periodic mode polling interval
let modePollingInterval: number | null = null
const MODE_POLL_INTERVAL = 15000 // 15 seconds

interface NavItem {
  id: string
  label: string
  path: string
  icon: string
  requiresMode?: 'recorder' | 'mixer'  // If set, requires mode switch
}

const navItems: NavItem[] = [
  { id: 'studio', label: 'Studio', path: '/', icon: 'home' },
  { id: 'recorder', label: 'Recorder', path: '/recorder', icon: 'record', requiresMode: 'recorder' },
  { id: 'mixer', label: 'Mixer', path: '/mixer', icon: 'mixer', requiresMode: 'mixer' },
  { id: 'library', label: 'Library', path: '/library', icon: 'folder' },
  { id: 'admin', label: 'Admin', path: '/admin', icon: 'settings' },
]

const currentPath = computed(() => route.path)
const currentMode = computed(() => capabilitiesStore.capabilities?.current_mode || 'idle')
const isRecording = computed(() => recorderStore.status === 'recording')

function isActive(path: string): boolean {
  return currentPath.value === path
}

// Check if nav item is the current mode
function isModeActive(item: NavItem): boolean {
  if (!item.requiresMode) return false
  return item.requiresMode === currentMode.value
}

// Handle nav item click with mode switching
async function handleNavClick(item: NavItem, event: Event) {
  // If no mode required, let router-link handle it
  if (!item.requiresMode) return
  
  // Prevent default navigation
  event.preventDefault()
  
  // If already in this mode, just navigate
  if (item.requiresMode === currentMode.value) {
    router.push(item.path)
    return
  }
  
  // If switching to mixer and currently recording, show confirmation
  if (item.requiresMode === 'mixer' && isRecording.value) {
    pendingMode.value = 'mixer'
    confirmDialogRef.value?.open()
    return
  }
  
  // Otherwise, switch mode and navigate
  await switchModeAndNavigate(item.requiresMode, item.path)
}

// Confirm mode switch (called from dialog)
async function confirmModeSwitch() {
  if (pendingMode.value) {
    const path = pendingMode.value === 'mixer' ? '/mixer' : '/recorder'
    await switchModeAndNavigate(pendingMode.value, path)
  }
  pendingMode.value = null
}

// Cancel mode switch
function cancelModeSwitch() {
  pendingMode.value = null
}

// Switch mode via API then navigate
async function switchModeAndNavigate(mode: 'recorder' | 'mixer', path: string) {
  if (switching.value) return
  
  // Skip if no device configured
  if (!hasDeviceConfigured()) {
    router.push(path)
    return
  }
  
  switching.value = true
  switchingTo.value = mode
  
  try {
    // Use timeout to prevent hanging
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 10000) // 10 second timeout
    
    const response = await fetch(buildApiUrl(`/api/mode/${mode}`), { 
      method: 'POST',
      signal: controller.signal
    }).finally(() => clearTimeout(timeoutId))
    
    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      throw new Error(data.detail || `Failed to switch to ${mode} mode`)
    }
    
    // Refresh capabilities to get updated mode
    await capabilitiesStore.fetchCapabilities()
    
    // Show success toast
    const modeLabel = mode === 'mixer' ? 'Mixer' : 'Recorder'
    toast.success(`Switched to ${modeLabel} mode`)
    
    // Navigate to the mode view
    router.push(path)
  } catch (e) {
    // If it's a timeout/abort, still navigate but warn
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

// Fetch initial mode and start polling
onMounted(async () => {
  await capabilitiesStore.fetchCapabilities()
  
  // Start periodic polling to keep mode indicator in sync
  // Only poll if device is configured
  if (hasDeviceConfigured()) {
    modePollingInterval = window.setInterval(async () => {
      // Don't poll while switching
      if (switching.value) return
      await capabilitiesStore.fetchCapabilities()
    }, MODE_POLL_INTERVAL)
  }
})

// Cleanup polling on unmount
onUnmounted(() => {
  if (modePollingInterval) {
    clearInterval(modePollingInterval)
    modePollingInterval = null
  }
})
</script>

<template>
  <aside class="w-20 bg-preke-bg-elevated border-r border-preke-bg-surface flex flex-col">
    <!-- Logo -->
    <div class="h-16 flex items-center justify-center border-b border-preke-bg-surface">
      <img src="/favicon.svg" alt="Preke" class="w-10 h-10 drop-shadow-[0_0_8px_rgba(255,255,255,0.35)]" />
    </div>
    
    <!-- Navigation -->
    <nav class="flex-1 py-4">
      <ul class="space-y-2 px-2">
        <li v-for="item in navItems" :key="item.id">
          <router-link
            :to="item.path"
            @click="handleNavClick(item, $event)"
            class="relative flex flex-col items-center gap-1 py-3 px-2 rounded-lg transition-colors"
            :class="[
              isActive(item.path)
                ? 'bg-preke-gold/10 text-preke-gold'
                : 'text-preke-text-dim hover:text-preke-text hover:bg-preke-bg-surface',
              switching && item.requiresMode ? 'opacity-60 cursor-wait' : ''
            ]"
          >
            <!-- Mode indicator dot -->
            <span 
              v-if="isModeActive(item)"
              class="absolute top-1 right-1 w-2 h-2 rounded-full"
              :class="item.requiresMode === 'recorder' ? 'bg-red-500' : 'bg-blue-500'"
              :title="item.requiresMode === 'recorder' ? 'Recorder mode active' : 'Mixer mode active'"
            ></span>
            
            <!-- Loading spinner when switching -->
            <svg 
              v-if="switching && switchingTo === item.requiresMode" 
              class="w-6 h-6 animate-spin" 
              fill="none" 
              viewBox="0 0 24 24"
            >
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            
            <!-- Icons -->
            <template v-else>
            <svg v-if="item.icon === 'home'" class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/>
            </svg>
            <svg v-else-if="item.icon === 'record'" class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.8">
              <rect x="2" y="5" width="14" height="12" rx="2"/>
              <path d="M16 9l4-2v8l-4-2"/>
              <circle cx="6" cy="8" r="2" fill="currentColor" stroke="none"/>
            </svg>
            <svg v-else-if="item.icon === 'mixer'" class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"/>
            </svg>
            <svg v-else-if="item.icon === 'folder'" class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/>
            </svg>
            <svg v-else-if="item.icon === 'settings'" class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
            </svg>
            </template>
            
            <span class="text-xs font-medium">{{ item.label }}</span>
          </router-link>
        </li>
      </ul>
    </nav>
    
    <!-- Version -->
    <div class="p-2 text-center text-xs text-preke-text-dim">
      v2.0.0
    </div>
  </aside>
  
  <!-- Confirmation dialog for stopping recording -->
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

