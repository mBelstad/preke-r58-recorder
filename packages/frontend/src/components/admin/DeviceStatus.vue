<script setup lang="ts">
import { onMounted, onUnmounted, ref, computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useCapabilitiesStore } from '@/stores/capabilities'
import { buildApiUrl } from '@/lib/api'

const capabilitiesStore = useCapabilitiesStore()
const { capabilities, loading, error } = storeToRefs(capabilitiesStore)

// Computed properties for reveal.js URLs (buildApiUrl is async, so we need to handle it)
const revealDemoUrl = ref<string>('')
const revealGraphicsUrl = ref<string>('')
const testTools = ref<Array<{ label: string; url: string; description?: string }>>([])

// Initialize URLs when component mounts
onMounted(async () => {
  try {
    revealDemoUrl.value = await buildApiUrl('/reveal')
    revealGraphicsUrl.value = await buildApiUrl('/reveal/graphics')
    const baseUrl = window.location.origin
    testTools.value = [
      {
        label: 'Stream Test',
        url: `${baseUrl}/#/stream-test`,
        description: 'MediaMTX stream monitor and URL helpers'
      },
      {
        label: 'RTMP Test',
        url: await buildApiUrl('/static/rtmp_test.html'),
        description: 'RTMP relay test and status checks'
      },
      {
        label: 'WHEP to Room Bridge',
        url: await buildApiUrl('/static/whep-to-room-bridge.html'),
        description: 'Pull WHEP into a VDO.ninja room'
      },
      {
        label: 'Camera Bridge',
        url: await buildApiUrl('/static/camera-bridge.html'),
        description: 'Bridge HDMI cameras into VDO.ninja'
      },
      {
        label: 'VDO Guest Bridge',
        url: await buildApiUrl('/static/vdoninja-guest-bridge.html'),
        description: 'Guest bridge utilities for VDO.ninja'
      },
      {
        label: 'MediaMTX Mixer',
        url: await buildApiUrl('/static/mediamtx_mixer.html'),
        description: 'MediaMTX mixer test page'
      },
      {
        label: 'Test Cameras',
        url: await buildApiUrl('/static/test_cameras.html'),
        description: 'Camera preview test page'
      },
      {
        label: 'VDO Manager',
        url: await buildApiUrl('/static/vdoninja-manager.html'),
        description: 'VDO.ninja manager utilities'
      }
    ]
  } catch (e) {
    console.error('Failed to build reveal.js URLs:', e)
  }
})

const switchingMode = ref(false)
const modeError = ref<string | null>(null)
const clearingCache = ref(false)
let pollInterval: ReturnType<typeof setInterval> | null = null

async function switchMode(mode: 'recorder' | 'mixer') {
  if (switchingMode.value) return
  
  switchingMode.value = true
  modeError.value = null
  
  try {
    const response = await fetch(await buildApiUrl(`/api/mode/${mode}`), { method: 'POST' })
    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      throw new Error(data.detail || `Failed to switch to ${mode} mode`)
    }
    // Refresh capabilities to get new mode
    await capabilitiesStore.fetchCapabilities()
  } catch (e) {
    modeError.value = e instanceof Error ? e.message : 'Failed to switch mode'
    console.error('Mode switch error:', e)
  } finally {
    switchingMode.value = false
  }
}

function getStatusColor(status: string, hasSignal: boolean): string {
  if (!hasSignal) return 'bg-preke-text-dim'
  switch (status) {
    case 'streaming':
    case 'recording':
      return 'bg-preke-green'
    case 'preview':
      return 'bg-preke-blue'
    case 'idle':
      return 'bg-preke-text-dim'
    case 'error':
      return 'bg-preke-red'
    default:
      return 'bg-preke-text-dim'
  }
}

function getStatusLabel(status: string, hasSignal: boolean): string {
  if (!hasSignal) return 'No Signal'
  switch (status) {
    case 'streaming': return 'Streaming'
    case 'recording': return 'Recording'
    case 'preview': return 'Preview'
    case 'idle': return 'Idle'
    case 'error': return 'Error'
    default: return status
  }
}

async function clearPWACache() {
  if (clearingCache.value) return
  
  clearingCache.value = true
  
  try {
    // Clear all caches
    if ('caches' in window) {
      const cacheNames = await caches.keys()
      await Promise.all(cacheNames.map(name => caches.delete(name)))
      console.log('[PWA] Cleared caches:', cacheNames)
    }
    
    // Unregister service worker
    if ('serviceWorker' in navigator) {
      const registrations = await navigator.serviceWorker.getRegistrations()
      await Promise.all(registrations.map(reg => reg.unregister()))
      console.log('[PWA] Unregistered service workers:', registrations.length)
    }
    
    // Clear localStorage (optional - only cache-related keys)
    try {
      const keysToRemove: string[] = []
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i)
        if (key && (key.startsWith('workbox-') || key.startsWith('sw-'))) {
          keysToRemove.push(key)
        }
      }
      keysToRemove.forEach(key => localStorage.removeItem(key))
      console.log('[PWA] Cleared cache-related localStorage keys')
    } catch (e) {
      console.warn('[PWA] Failed to clear localStorage:', e)
    }
    
    // Reload page after a short delay
    setTimeout(() => {
      window.location.reload()
    }, 500)
  } catch (e) {
    console.error('[PWA] Failed to clear cache:', e)
    clearingCache.value = false
    alert('Failed to clear PWA cache. Please try manually: DevTools > Application > Clear Storage')
  }
}

onMounted(() => {
  capabilitiesStore.fetchCapabilities()
  // Poll every 10 seconds
  pollInterval = setInterval(() => {
    capabilitiesStore.fetchCapabilities()
  }, 10000)
})

onUnmounted(() => {
  if (pollInterval) {
    clearInterval(pollInterval)
  }
})
</script>

<template>
  <div class="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
    <!-- Device Info -->
    <div class="card">
      <h3 class="text-sm font-semibold text-preke-text-dim uppercase tracking-wide mb-4">Device Info</h3>
      <div v-if="error && !capabilities" class="text-preke-red">
        {{ error }}
      </div>
      <div v-else class="space-y-3">
        <div class="flex justify-between items-center">
          <span class="text-preke-text-dim">Device Name</span>
          <div v-if="loading && !capabilities" class="skeleton w-24 h-5"></div>
          <span v-else class="font-medium">{{ capabilities?.device_name || 'R58 Device' }}</span>
        </div>
        <div class="flex justify-between items-center">
          <span class="text-preke-text-dim">Platform</span>
          <div v-if="loading && !capabilities" class="skeleton w-16 h-5"></div>
          <span v-else class="capitalize">{{ capabilities?.platform || '-' }}</span>
        </div>
        <div class="flex justify-between items-center">
          <span class="text-preke-text-dim">API Version</span>
          <div v-if="loading && !capabilities" class="skeleton w-12 h-5"></div>
          <span v-else>{{ capabilities?.api_version || '-' }}</span>
        </div>
        <div class="flex justify-between items-center">
          <span class="text-preke-text-dim">GStreamer</span>
          <div v-if="loading && !capabilities" class="skeleton w-20 h-5"></div>
          <span v-else class="badge badge-success">Initialized</span>
        </div>
        <div v-if="capabilities?.reveal_js?.available" class="flex flex-col gap-2 pt-2 border-t border-preke-border">
          <div class="flex justify-between items-center">
            <span class="text-preke-text-dim text-xs">Reveal.js</span>
            <span class="badge badge-success text-xs">Available</span>
          </div>
          <div class="flex flex-col gap-1 text-xs">
            <a 
              v-if="revealDemoUrl"
              :href="revealDemoUrl" 
              target="_blank"
              class="text-preke-blue hover:text-preke-gold transition-colors truncate"
              title="Open Reveal.js Demo"
            >
              Demo Presentation
            </a>
            <a 
              v-if="revealGraphicsUrl"
              :href="revealGraphicsUrl" 
              target="_blank"
              class="text-preke-blue hover:text-preke-gold transition-colors truncate"
              title="Open Reveal.js Graphics"
            >
              Graphics Presentation
            </a>
          </div>
        </div>
      </div>
    </div>

    <!-- Test Tools -->
    <div class="card">
      <h3 class="text-sm font-semibold text-preke-text-dim uppercase tracking-wide mb-4">Test Tools</h3>
      <div class="space-y-3">
        <div v-for="tool in testTools" :key="tool.label" class="flex flex-col gap-1">
          <a
            :href="tool.url"
            target="_blank"
            class="text-preke-blue hover:text-preke-gold transition-colors truncate"
            :title="tool.label"
          >
            {{ tool.label }}
          </a>
          <span v-if="tool.description" class="text-xs text-preke-text-dim">
            {{ tool.description }}
          </span>
        </div>
        <div v-if="testTools.length === 0" class="text-preke-text-dim text-sm">
          Test tools not available.
        </div>
      </div>
    </div>

    <!-- PWA Cache Control -->
    <div class="card">
      <h3 class="text-sm font-semibold text-preke-text-dim uppercase tracking-wide mb-4">PWA Cache</h3>
      <div class="space-y-3">
        <p class="text-xs text-preke-text-dim">
          Clear service worker cache and reload to see latest changes in web app.
        </p>
        <button
          @click="clearPWACache"
          :disabled="clearingCache"
          class="btn btn-sm w-full"
          :class="clearingCache ? 'btn-secondary' : 'btn-warning'"
        >
          <span v-if="clearingCache" class="inline-block animate-spin mr-1">⟳</span>
          {{ clearingCache ? 'Clearing...' : 'Clear PWA Cache & Reload' }}
        </button>
        <p class="text-xs text-preke-text-dim">
          This will unregister service workers, clear all caches, and reload the page.
        </p>
      </div>
    </div>
    
    <!-- Mode Control -->
    <div class="card">
      <h3 class="text-sm font-semibold text-preke-text-dim uppercase tracking-wide mb-4">Operating Mode</h3>
      <div class="space-y-4">
        <div class="flex items-center justify-between">
          <span class="text-preke-text-dim">Current Mode</span>
          <div v-if="loading && !capabilities" class="skeleton w-20 h-5 rounded-full"></div>
          <span v-else class="badge" :class="capabilities?.current_mode === 'mixer' ? 'badge-info' : 'badge-success'">
            {{ capabilities?.current_mode === 'mixer' ? 'Mixer' : 'Recorder' }}
          </span>
        </div>
        
        <div class="flex gap-2">
          <button
            class="btn btn-sm flex-1"
            :class="capabilities?.current_mode === 'recorder' ? 'btn-primary' : 'btn-secondary'"
            :disabled="switchingMode || capabilities?.current_mode === 'recorder' || (loading && !capabilities)"
            @click="switchMode('recorder')"
          >
            <span v-if="switchingMode && capabilities?.current_mode !== 'recorder'" class="inline-block animate-spin mr-1">⟳</span>
            Recorder
          </button>
          <button
            class="btn btn-sm flex-1"
            :class="capabilities?.current_mode === 'mixer' ? 'btn-primary' : 'btn-secondary'"
            :disabled="switchingMode || capabilities?.current_mode === 'mixer' || (loading && !capabilities)"
            @click="switchMode('mixer')"
          >
            <span v-if="switchingMode && capabilities?.current_mode !== 'mixer'" class="inline-block animate-spin mr-1">⟳</span>
            Mixer
          </button>
        </div>
        
        <div v-if="modeError" class="text-sm text-preke-red">
          {{ modeError }}
        </div>
      </div>
    </div>
    
    <!-- Features -->
    <div class="card">
      <h3 class="text-sm font-semibold text-preke-text-dim uppercase tracking-wide mb-4">Available Features</h3>
      <div class="space-y-3">
        <div class="flex justify-between items-center">
          <div>
            <span>Mixer</span>
            <span class="text-xs text-preke-text-dim ml-1">(VDO.ninja)</span>
          </div>
          <div v-if="loading && !capabilities" class="skeleton w-20 h-5 rounded-full"></div>
          <span 
            v-else
            class="badge"
            :class="capabilitiesStore.mixerEnabled ? 'badge-success' : 'badge-warning'"
          >
            {{ capabilitiesStore.mixerEnabled ? 'Available' : 'Disabled' }}
          </span>
        </div>
        <div class="flex justify-between items-center">
          <span>Recorder</span>
          <div v-if="loading && !capabilities" class="skeleton w-20 h-5 rounded-full"></div>
          <span 
            v-else
            class="badge"
            :class="capabilitiesStore.recorderEnabled ? 'badge-success' : 'badge-warning'"
          >
            {{ capabilitiesStore.recorderEnabled ? 'Available' : 'Disabled' }}
          </span>
        </div>
        <div class="flex justify-between items-center">
          <span>Graphics Overlay</span>
          <div v-if="loading && !capabilities" class="skeleton w-20 h-5 rounded-full"></div>
          <span v-else class="badge badge-success">Available</span>
        </div>
        <div class="flex justify-between items-center">
          <span>WebRTC Preview</span>
          <div v-if="loading && !capabilities" class="skeleton w-20 h-5 rounded-full"></div>
          <span v-else class="badge badge-success">Available</span>
        </div>
      </div>
    </div>
    
    <!-- Hardware Inputs -->
    <div class="card md:col-span-2 lg:col-span-3">
      <h3 class="text-sm font-semibold text-preke-text-dim uppercase tracking-wide mb-4">Hardware Inputs</h3>
      <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <!-- Skeleton loading state -->
        <template v-if="loading && !capabilities">
          <div 
            v-for="i in 4"
            :key="i"
            class="p-4 rounded-lg bg-preke-bg-surface border border-preke-border"
          >
            <div class="flex items-center justify-between mb-3">
              <div class="flex items-center gap-2">
                <div class="skeleton w-2 h-2 rounded-full"></div>
                <div class="skeleton w-16 h-5"></div>
              </div>
              <div class="skeleton w-16 h-4 rounded-full"></div>
            </div>
            <div class="space-y-2">
              <div class="flex justify-between">
                <div class="skeleton w-8 h-4"></div>
                <div class="skeleton w-12 h-4"></div>
              </div>
              <div class="flex justify-between">
                <div class="skeleton w-16 h-4"></div>
                <div class="skeleton w-20 h-4"></div>
              </div>
              <div class="flex justify-between">
                <div class="skeleton w-10 h-4"></div>
                <div class="skeleton w-14 h-4"></div>
              </div>
            </div>
          </div>
        </template>
        
        <!-- Actual data -->
        <template v-else>
          <div 
            v-for="input in capabilities?.inputs || []"
            :key="input.id"
            class="p-4 rounded-lg bg-preke-bg-surface border border-preke-border"
            :class="{ 'border-preke-green/50': input.has_signal }"
          >
            <div class="flex items-center justify-between mb-3">
              <div class="flex items-center gap-2">
                <span 
                  class="w-2 h-2 rounded-full animate-pulse"
                  :class="getStatusColor(input.status, input.has_signal)"
                ></span>
                <span class="font-medium">{{ input.label }}</span>
              </div>
              <span 
                class="text-xs px-2 py-0.5 rounded-full"
                :class="{
                  'bg-preke-green/20 text-preke-green': input.has_signal && (input.status === 'streaming' || input.status === 'recording'),
                  'bg-preke-blue/20 text-preke-blue': input.has_signal && input.status === 'preview',
                  'bg-preke-bg-surface text-preke-text-dim': !input.has_signal || input.status === 'idle'
                }"
              >
                {{ getStatusLabel(input.status, input.has_signal) }}
              </span>
            </div>
            <div class="space-y-1 text-sm text-preke-text-dim">
              <div class="flex justify-between">
                <span>Type</span>
                <span class="text-preke-text">{{ input.type.toUpperCase() }}</span>
              </div>
              <div class="flex justify-between">
                <span>Resolution</span>
                <span class="text-preke-text">{{ input.max_resolution || 'N/A' }}</span>
              </div>
              <div class="flex justify-between">
                <span>Device</span>
                <span class="text-preke-text font-mono text-xs">{{ input.device_path?.split('/').pop() || 'N/A' }}</span>
              </div>
            </div>
          </div>
        
          <div v-if="!capabilities?.inputs?.length" class="col-span-full text-center text-preke-text-dim py-8">
            No inputs detected
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped>
.skeleton {
  @apply bg-preke-bg-surface animate-pulse rounded;
}
</style>

