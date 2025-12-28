<script setup lang="ts">
/**
 * LAN Device Discovery Component
 * 
 * Discovers and lists R58 devices on the local network (same subnet).
 * Uses /api/v1/lan-devices endpoints on the local R58 device.
 * 
 * Note: For centralized fleet management (cloud), see /fleet routes.
 */
import { ref, onMounted } from 'vue'

interface Device {
  id: string
  name: string
  ip: string
  status: 'online' | 'offline' | 'unknown'
  lastSeen: string
  version: string
}

const devices = ref<Device[]>([])
const loading = ref(true)
const scanning = ref(false)

async function fetchDevices() {
  loading.value = true
  try {
    const response = await fetch('/api/v1/lan-devices')
    if (response.ok) {
      const data = await response.json()
      devices.value = data.map((d: any) => ({
        id: d.id,
        name: d.name,
        ip: d.ip,
        status: d.status,
        lastSeen: d.last_seen,
        version: d.api_version || 'unknown',
      }))
    }
  } catch (e) {
    console.error('Failed to fetch LAN devices:', e)
  } finally {
    loading.value = false
  }
}

onMounted(fetchDevices)

async function scanNetwork() {
  scanning.value = true
  try {
    const response = await fetch('/api/v1/lan-devices/scan', { method: 'POST' })
    if (response.ok) {
      const data = await response.json()
      // Add newly discovered devices
      for (const d of data) {
        const existing = devices.value.find(dev => dev.id === d.id)
        if (!existing) {
          devices.value.push({
            id: d.id,
            name: d.name,
            ip: d.ip,
            status: d.status,
            lastSeen: d.last_seen,
            version: d.api_version || 'unknown',
          })
        }
      }
    }
  } catch (e) {
    console.error('LAN network scan failed:', e)
  } finally {
    scanning.value = false
  }
}

async function connectToDevice(device: Device) {
  try {
    const response = await fetch(`/api/v1/lan-devices/${device.id}/connect`, { method: 'POST' })
    const data = await response.json()
    
    if (data.connected) {
      // Open device in new tab/window
      window.open(`http://${device.ip}:8000`, '_blank')
    } else {
      alert(`Failed to connect: ${data.error || 'Unknown error'}`)
    }
  } catch (e) {
    console.error('Failed to connect to device:', e)
  }
}
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <h2 class="text-lg font-semibold">LAN Devices</h2>
      <button @click="scanNetwork" :disabled="scanning" class="btn">
        <span v-if="scanning">Scanning...</span>
        <span v-else>Scan Network</span>
      </button>
    </div>
    
    <!-- Device list -->
    <div v-if="loading" class="flex items-center justify-center py-12">
      <div class="animate-spin w-8 h-8 border-2 border-r58-accent-primary border-t-transparent rounded-full"></div>
    </div>
    
    <div v-else-if="devices.length === 0" class="text-center py-12 text-r58-text-secondary">
      <p>No devices found</p>
      <p class="text-sm mt-2">Click "Scan Network" to discover R58 devices</p>
    </div>
    
    <div v-else class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      <div 
        v-for="device in devices"
        :key="device.id"
        class="card hover:border-r58-accent-primary/50 transition-colors cursor-pointer"
        @click="connectToDevice(device)"
      >
        <div class="flex items-start justify-between mb-4">
          <div>
            <h3 class="font-semibold">{{ device.name }}</h3>
            <p class="text-sm text-r58-text-secondary">{{ device.id }}</p>
          </div>
          <span 
            class="badge"
            :class="{
              'badge-success': device.status === 'online',
              'badge-danger': device.status === 'offline',
              'badge-warning': device.status === 'unknown',
            }"
          >
            {{ device.status }}
          </span>
        </div>
        
        <div class="space-y-2 text-sm">
          <div class="flex justify-between">
            <span class="text-r58-text-secondary">IP Address</span>
            <span class="font-mono">{{ device.ip }}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-r58-text-secondary">Version</span>
            <span>{{ device.version }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

