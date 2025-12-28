<script setup lang="ts">
import { onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useCapabilitiesStore } from '@/stores/capabilities'

const capabilitiesStore = useCapabilitiesStore()
const { capabilities } = storeToRefs(capabilitiesStore)

onMounted(() => {
  capabilitiesStore.fetchCapabilities()
})
</script>

<template>
  <div class="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
    <!-- Device Info -->
    <div class="card">
      <h3 class="text-sm font-semibold text-r58-text-secondary uppercase tracking-wide mb-4">Device Info</h3>
      <div class="space-y-3">
        <div class="flex justify-between">
          <span class="text-r58-text-secondary">Device ID</span>
          <span class="font-mono text-sm">{{ capabilities?.device_id || 'Loading...' }}</span>
        </div>
        <div class="flex justify-between">
          <span class="text-r58-text-secondary">Platform</span>
          <span class="capitalize">{{ capabilities?.platform || '-' }}</span>
        </div>
        <div class="flex justify-between">
          <span class="text-r58-text-secondary">API Version</span>
          <span>{{ capabilities?.api_version || '-' }}</span>
        </div>
      </div>
    </div>
    
    <!-- Features -->
    <div class="card">
      <h3 class="text-sm font-semibold text-r58-text-secondary uppercase tracking-wide mb-4">Features</h3>
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
            {{ capabilitiesStore.mixerEnabled ? 'Enabled' : 'Disabled' }}
          </span>
        </div>
        <div class="flex justify-between items-center">
          <span>Recorder</span>
          <span 
            class="badge"
            :class="capabilitiesStore.recorderEnabled ? 'badge-success' : 'badge-warning'"
          >
            {{ capabilitiesStore.recorderEnabled ? 'Enabled' : 'Disabled' }}
          </span>
        </div>
      </div>
    </div>
    
    <!-- Storage -->
    <div class="card">
      <h3 class="text-sm font-semibold text-r58-text-secondary uppercase tracking-wide mb-4">Storage</h3>
      <div class="space-y-4">
        <div>
          <div class="flex justify-between text-sm mb-2">
            <span class="text-r58-text-secondary">Used</span>
            <span>{{ capabilitiesStore.storagePercent }}%</span>
          </div>
          <div class="w-full h-3 bg-r58-bg-tertiary rounded-full overflow-hidden">
            <div 
              class="h-full rounded-full transition-all"
              :class="[
                capabilitiesStore.storagePercent > 90 ? 'bg-r58-accent-danger' :
                capabilitiesStore.storagePercent > 70 ? 'bg-r58-accent-warning' :
                'bg-r58-accent-success'
              ]"
              :style="{ width: `${capabilitiesStore.storagePercent}%` }"
            ></div>
          </div>
        </div>
        <div class="flex justify-between text-sm">
          <span class="text-r58-text-secondary">Available</span>
          <span>{{ capabilities?.storage_available_gb?.toFixed(1) || '0' }} GB</span>
        </div>
        <div class="flex justify-between text-sm">
          <span class="text-r58-text-secondary">Total</span>
          <span>{{ capabilities?.storage_total_gb?.toFixed(1) || '0' }} GB</span>
        </div>
      </div>
    </div>
    
    <!-- Inputs -->
    <div class="card md:col-span-2 lg:col-span-3">
      <h3 class="text-sm font-semibold text-r58-text-secondary uppercase tracking-wide mb-4">Hardware Inputs</h3>
      <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div 
          v-for="input in capabilities?.inputs || []"
          :key="input.id"
          class="p-4 rounded-lg bg-r58-bg-tertiary"
        >
          <div class="flex items-center gap-2 mb-2">
            <span class="w-2 h-2 rounded-full bg-r58-accent-success"></span>
            <span class="font-medium">{{ input.label }}</span>
          </div>
          <div class="space-y-1 text-sm text-r58-text-secondary">
            <p>Type: {{ input.type.toUpperCase() }}</p>
            <p>Max: {{ input.max_resolution }}</p>
            <p>Audio: {{ input.supports_audio ? 'Yes' : 'No' }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

