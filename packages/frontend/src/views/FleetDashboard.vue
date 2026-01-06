<script setup lang="ts">
/**
 * Fleet Dashboard - Device management overview
 * 
 * Shows all registered devices with status, metrics, and quick actions.
 */
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { r58Api } from '@/lib/api'

// Types
interface Device {
  id: string
  device_id: string
  name: string
  status: 'online' | 'offline' | 'updating' | 'error' | 'maintenance'
  current_version?: string
  target_version?: string
  last_heartbeat?: string
  cpu_percent?: number
  mem_percent?: number
  disk_free_gb?: number
  temperature_c?: number
  recording_active?: boolean
  mixer_active?: boolean
  location?: string
  tags?: string[]
  pending_commands?: number
  active_alerts?: number
}

// State
const router = useRouter()
const devices = ref<Device[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const searchQuery = ref('')
const statusFilter = ref<string>('')
const refreshInterval = ref<number | null>(null)

// Computed
const filteredDevices = computed(() => {
  let result = devices.value

  // Filter by status
  if (statusFilter.value) {
    result = result.filter(d => d.status === statusFilter.value)
  }

  // Filter by search
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(d =>
      d.device_id.toLowerCase().includes(query) ||
      d.name.toLowerCase().includes(query) ||
      d.location?.toLowerCase().includes(query)
    )
  }

  return result
})

const statusCounts = computed(() => {
  const counts = { online: 0, offline: 0, updating: 0, error: 0, maintenance: 0 }
  devices.value.forEach(d => {
    if (d.status in counts) {
      counts[d.status as keyof typeof counts]++
    }
  })
  return counts
})

// Methods
async function fetchDevices() {
  try {
    const response = await r58Api.fleet?.devices() || { items: [] }
    devices.value = response.items || []
    error.value = null
  } catch (e) {
    error.value = 'Failed to load devices'
    console.error('Fleet fetch error:', e)
  } finally {
    loading.value = false
  }
}

    function getStatusColor(status: string): string {
      const colors: Record<string, string> = {
        online: 'bg-preke-green',
        offline: 'bg-preke-text-muted',
        updating: 'bg-preke-amber',
        error: 'bg-preke-red',
        maintenance: 'bg-preke-gold',
      }
      return colors[status] || 'bg-preke-text-muted'
    }

    function getStatusTextColor(status: string): string {
      const colors: Record<string, string> = {
        online: 'text-preke-green',
        offline: 'text-preke-text-muted',
        updating: 'text-preke-amber',
        error: 'text-preke-red',
        maintenance: 'text-preke-gold',
      }
      return colors[status] || 'text-preke-text-muted'
    }

function formatLastSeen(timestamp?: string): string {
  if (!timestamp) return 'Never'
  const date = new Date(timestamp)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  
  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins}m ago`
  const diffHours = Math.floor(diffMins / 60)
  if (diffHours < 24) return `${diffHours}h ago`
  const diffDays = Math.floor(diffHours / 24)
  return `${diffDays}d ago`
}

function openDevice(deviceId: string) {
  router.push(`/fleet/devices/${deviceId}`)
}

// Lifecycle
onMounted(() => {
  fetchDevices()
  refreshInterval.value = window.setInterval(fetchDevices, 30000) // Refresh every 30s
})

onUnmounted(() => {
  if (refreshInterval.value) {
    clearInterval(refreshInterval.value)
  }
})
</script>

<template>
  <div class="fleet-dashboard">
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-2xl font-semibold text-preke-text">Fleet Dashboard</h1>
        <p class="text-sm text-preke-text-dim mt-1">Manage and monitor all R58 devices</p>
      </div>
      <div class="flex items-center gap-3">
        <button 
          @click="fetchDevices"
          class="btn"
          :disabled="loading"
        >
          <span v-if="loading">Refreshing...</span>
          <span v-else>Refresh</span>
        </button>
        <button class="btn btn-success">
          + Add Device
        </button>
      </div>
    </div>

    <!-- Status Overview -->
    <div class="grid grid-cols-5 gap-4 mb-6">
      <button
        v-for="(count, status) in statusCounts"
        :key="status"
        @click="statusFilter = statusFilter === status ? '' : status"
        class="p-4 rounded-r58 border transition-colors"
        :class="statusFilter === status 
          ? 'bg-preke-bg-surface border-preke-gold' 
          : 'bg-preke-bg-elevated border-preke-bg-surface hover:border-preke-text-dim'"
      >
        <div class="flex items-center gap-2">
          <div :class="['w-2 h-2 rounded-full', getStatusColor(status)]"></div>
          <span class="text-sm text-preke-text-dim capitalize">{{ status }}</span>
        </div>
        <div class="text-2xl font-semibold text-preke-text mt-1">{{ count }}</div>
      </button>
    </div>

    <!-- Search and Filters -->
    <div class="flex items-center gap-4 mb-6">
      <div class="flex-1 relative">
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search devices..."
          class="input w-full pl-10"
        />
        <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-preke-text-dim" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
      </div>
    </div>

    <!-- Error State -->
    <div v-if="error" class="p-4 bg-preke-red/20 border border-preke-red rounded-lg text-preke-red mb-6">
      {{ error }}
    </div>

    <!-- Loading State -->
    <div v-if="loading && devices.length === 0" class="text-center py-12">
      <div class="animate-spin w-8 h-8 border-2 border-preke-bg-surface border-t-preke-gold rounded-full mx-auto"></div>
      <p class="text-preke-text-dim mt-4">Loading devices...</p>
    </div>

    <!-- Empty State -->
    <div v-else-if="filteredDevices.length === 0" class="text-center py-12">
      <div class="w-16 h-16 bg-preke-bg-elevated rounded-full flex items-center justify-center mx-auto mb-4">
        <svg class="w-8 h-8 text-preke-text-dim" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2z" />
        </svg>
      </div>
      <h3 class="text-lg font-medium text-preke-text mb-2">No devices found</h3>
      <p class="text-preke-text-dim">
        {{ searchQuery ? 'Try adjusting your search or filters' : 'Register your first device to get started' }}
      </p>
    </div>

    <!-- Device Grid -->
    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <div
        v-for="device in filteredDevices"
        :key="device.id"
        @click="openDevice(device.device_id)"
        class="card hover:border-preke-text-dim cursor-pointer transition-all group"
      >
        <!-- Header -->
        <div class="flex items-start justify-between mb-3">
          <div>
            <h3 class="font-medium text-preke-text group-hover:text-preke-gold transition-colors">
              {{ device.name }}
            </h3>
            <p class="text-sm text-preke-text-dim font-mono">{{ device.device_id }}</p>
          </div>
          <div class="flex items-center gap-2">
            <span 
              v-if="device.pending_commands && device.pending_commands > 0"
              class="badge badge-warning"
            >
              {{ device.pending_commands }} pending
            </span>
            <span 
              :class="['flex items-center gap-1 text-xs', getStatusTextColor(device.status)]"
            >
              <span :class="['w-1.5 h-1.5 rounded-full', getStatusColor(device.status)]"></span>
              {{ device.status }}
            </span>
          </div>
        </div>

        <!-- Version -->
        <div class="flex items-center gap-2 text-sm text-preke-text-dim mb-3">
          <span>v{{ device.current_version || 'unknown' }}</span>
          <span v-if="device.target_version" class="text-preke-amber">
            → v{{ device.target_version }}
          </span>
        </div>

        <!-- Metrics -->
        <div v-if="device.status === 'online'" class="grid grid-cols-4 gap-2 text-center">
          <div class="p-2 bg-preke-bg-surface rounded">
            <div class="text-xs text-preke-text-dim">CPU</div>
            <div class="text-sm font-medium" :class="device.cpu_percent && device.cpu_percent > 80 ? 'text-preke-red' : 'text-preke-text'">
              {{ device.cpu_percent?.toFixed(0) || '-' }}%
            </div>
          </div>
          <div class="p-2 bg-preke-bg-surface rounded">
            <div class="text-xs text-preke-text-dim">MEM</div>
            <div class="text-sm font-medium" :class="device.mem_percent && device.mem_percent > 80 ? 'text-preke-red' : 'text-preke-text'">
              {{ device.mem_percent?.toFixed(0) || '-' }}%
            </div>
          </div>
          <div class="p-2 bg-preke-bg-surface rounded">
            <div class="text-xs text-preke-text-dim">DISK</div>
            <div class="text-sm font-medium" :class="device.disk_free_gb && device.disk_free_gb < 2 ? 'text-preke-red' : 'text-preke-text'">
              {{ device.disk_free_gb?.toFixed(1) || '-' }}G
            </div>
          </div>
          <div class="p-2 bg-preke-bg-surface rounded">
            <div class="text-xs text-preke-text-dim">TEMP</div>
            <div class="text-sm font-medium" :class="device.temperature_c && device.temperature_c > 70 ? 'text-preke-red' : 'text-preke-text'">
              {{ device.temperature_c?.toFixed(0) || '-' }}°
            </div>
          </div>
        </div>

        <!-- Activity Indicators -->
        <div v-if="device.recording_active || device.mixer_active" class="flex items-center gap-2 mt-3">
          <span v-if="device.recording_active" class="badge badge-danger flex items-center gap-1">
            <span class="w-1.5 h-1.5 bg-current rounded-full animate-pulse"></span>
            Recording
          </span>
          <span v-if="device.mixer_active" class="badge badge-success">
            Mixer Active
          </span>
        </div>

        <!-- Footer -->
        <div class="flex items-center justify-between mt-3 pt-3 border-t border-preke-bg-surface text-xs text-preke-text-dim">
          <span v-if="device.location">{{ device.location }}</span>
          <span v-else>-</span>
          <span>{{ formatLastSeen(device.last_heartbeat) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.fleet-dashboard {
  @apply p-6;
}
</style>

