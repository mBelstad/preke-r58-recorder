<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { useCapabilitiesStore } from '@/stores/capabilities'
import { buildApiUrl } from '@/lib/api'

const capabilitiesStore = useCapabilitiesStore()
const { capabilities, loading, error } = storeToRefs(capabilitiesStore)

const switchingMode = ref(false)
const modeError = ref<string | null>(null)
let pollInterval: ReturnType<typeof setInterval> | null = null

async function switchMode(mode: 'recorder' | 'mixer') {
  if (switchingMode.value) return
  
  switchingMode.value = true
  modeError.value = null
  
  try {
    const response = await fetch(buildApiUrl(`/api/mode/${mode}`), { method: 'POST' })
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
  if (!hasSignal) return 'bg-r58-text-secondary'
  switch (status) {
    case 'streaming':
    case 'recording':
      return 'bg-r58-accent-success'
    case 'preview':
      return 'bg-r58-accent-info'
    case 'idle':
      return 'bg-r58-text-secondary'
    case 'error':
      return 'bg-r58-accent-danger'
    default:
      return 'bg-r58-text-secondary'
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
      <h3 class="text-sm font-semibold text-r58-text-secondary uppercase tracking-wide mb-4">Device Info</h3>
      <div v-if="loading && !capabilities" class="text-r58-text-secondary">
        Loading...
      </div>
      <div v-else-if="error && !capabilities" class="text-r58-accent-danger">
        {{ error }}
      </div>
      <div v-else class="space-y-3">
        <div class="flex justify-between">
          <span class="text-r58-text-secondary">Device Name</span>
          <span class="font-medium">{{ capabilities?.device_name || 'R58 Device' }}</span>
        </div>
        <div class="flex justify-between">
          <span class="text-r58-text-secondary">Platform</span>
          <span class="capitalize">{{ capabilities?.platform || '-' }}</span>
        </div>
        <div class="flex justify-between">
          <span class="text-r58-text-secondary">API Version</span>
          <span>{{ capabilities?.api_version || '-' }}</span>
        </div>
        <div class="flex justify-between">
          <span class="text-r58-text-secondary">GStreamer</span>
          <span class="badge badge-success">Initialized</span>
        </div>
      </div>
    </div>
    
    <!-- Mode Control -->
    <div class="card">
      <h3 class="text-sm font-semibold text-r58-text-secondary uppercase tracking-wide mb-4">Operating Mode</h3>
      <div class="space-y-4">
        <div class="flex items-center justify-between">
          <span class="text-r58-text-secondary">Current Mode</span>
          <span class="badge" :class="capabilities?.current_mode === 'mixer' ? 'badge-info' : 'badge-success'">
            {{ capabilities?.current_mode === 'mixer' ? 'Mixer' : 'Recorder' }}
          </span>
        </div>
        
        <div class="flex gap-2">
          <button
            class="btn btn-sm flex-1"
            :class="capabilities?.current_mode === 'recorder' ? 'btn-primary' : 'btn-secondary'"
            :disabled="switchingMode || capabilities?.current_mode === 'recorder'"
            @click="switchMode('recorder')"
          >
            <span v-if="switchingMode && capabilities?.current_mode !== 'recorder'" class="inline-block animate-spin mr-1">⟳</span>
            Recorder
          </button>
          <button
            class="btn btn-sm flex-1"
            :class="capabilities?.current_mode === 'mixer' ? 'btn-primary' : 'btn-secondary'"
            :disabled="switchingMode || capabilities?.current_mode === 'mixer'"
            @click="switchMode('mixer')"
          >
            <span v-if="switchingMode && capabilities?.current_mode !== 'mixer'" class="inline-block animate-spin mr-1">⟳</span>
            Mixer
          </button>
        </div>
        
        <div v-if="modeError" class="text-sm text-r58-accent-danger">
          {{ modeError }}
        </div>
      </div>
    </div>
    
    <!-- Features -->
    <div class="card">
      <h3 class="text-sm font-semibold text-r58-text-secondary uppercase tracking-wide mb-4">Available Features</h3>
      <div class="space-y-3">
        <div class="flex justify-between items-center">
          <div>
            <span>Mixer</span>
            <span class="text-xs text-r58-text-secondary ml-1">(VDO.ninja)</span>
          </div>
          <span 
            class="badge"
            :class="capabilitiesStore.mixerEnabled ? 'badge-success' : 'badge-warning'"
          >
            {{ capabilitiesStore.mixerEnabled ? 'Available' : 'Disabled' }}
          </span>
        </div>
        <div class="flex justify-between items-center">
          <span>Recorder</span>
          <span 
            class="badge"
            :class="capabilitiesStore.recorderEnabled ? 'badge-success' : 'badge-warning'"
          >
            {{ capabilitiesStore.recorderEnabled ? 'Available' : 'Disabled' }}
          </span>
        </div>
        <div class="flex justify-between items-center">
          <span>Graphics Overlay</span>
          <span class="badge badge-success">Available</span>
        </div>
        <div class="flex justify-between items-center">
          <span>WebRTC Preview</span>
          <span class="badge badge-success">Available</span>
        </div>
      </div>
    </div>
    
    <!-- Hardware Inputs -->
    <div class="card md:col-span-2 lg:col-span-3">
      <h3 class="text-sm font-semibold text-r58-text-secondary uppercase tracking-wide mb-4">Hardware Inputs</h3>
      <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div 
          v-for="input in capabilities?.inputs || []"
          :key="input.id"
          class="p-4 rounded-lg bg-r58-bg-tertiary border border-r58-border"
          :class="{ 'border-r58-accent-success/50': input.has_signal }"
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
                'bg-r58-accent-success/20 text-r58-accent-success': input.has_signal && (input.status === 'streaming' || input.status === 'recording'),
                'bg-r58-accent-info/20 text-r58-accent-info': input.has_signal && input.status === 'preview',
                'bg-r58-bg-tertiary text-r58-text-secondary': !input.has_signal || input.status === 'idle'
              }"
            >
              {{ getStatusLabel(input.status, input.has_signal) }}
            </span>
          </div>
          <div class="space-y-1 text-sm text-r58-text-secondary">
            <div class="flex justify-between">
              <span>Type</span>
              <span class="text-r58-text-primary">{{ input.type.toUpperCase() }}</span>
            </div>
            <div class="flex justify-between">
              <span>Resolution</span>
              <span class="text-r58-text-primary">{{ input.max_resolution || 'N/A' }}</span>
            </div>
            <div class="flex justify-between">
              <span>Device</span>
              <span class="text-r58-text-primary font-mono text-xs">{{ input.device_path?.split('/').pop() || 'N/A' }}</span>
            </div>
          </div>
        </div>
        
        <div v-if="!capabilities?.inputs?.length" class="col-span-full text-center text-r58-text-secondary py-8">
          No inputs detected
        </div>
      </div>
    </div>
  </div>
</template>

