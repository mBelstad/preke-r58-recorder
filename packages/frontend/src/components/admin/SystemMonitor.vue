<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { r58Api } from '@/lib/api'
import { useToast } from '@/composables/useToast'

const toast = useToast()

// State
const loading = ref(true)
const error = ref<string | null>(null)
const systemStatus = ref<any>(null)
const refreshInterval = ref<number | null>(null)

// Computed
const cpuPercent = computed(() => {
  const load = systemStatus.value?.info?.load_average?.[0] ?? 0
  // Load average as percentage of cores (rough approximation)
  const cores = 8 // R58 has 8 cores
  return Math.min(100, (load / cores) * 100)
})

const memoryPercent = computed(() => {
  const mem = systemStatus.value?.info?.memory_percent
  if (mem !== undefined) return mem
  return 0
})

const primaryTemp = computed(() => {
  const temps = systemStatus.value?.info?.temperatures ?? []
  if (temps.length === 0) return null
  // Return first temperature or CPU temp if available
  const cpuTemp = temps.find((t: any) => t.type?.toLowerCase().includes('cpu'))
  return cpuTemp ?? temps[0]
})

const uptimeFormatted = computed(() => {
  const seconds = systemStatus.value?.info?.uptime_seconds ?? 0
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  
  if (days > 0) return `${days}d ${hours}h`
  if (hours > 0) return `${hours}h ${minutes}m`
  return `${minutes}m`
})

const services = computed(() => systemStatus.value?.services ?? [])
const pipelines = computed(() => systemStatus.value?.pipelines ?? [])

// Actions
async function fetchStatus() {
  try {
    // Use the health endpoint which exists on the device
    const { buildApiUrl } = await import('@/lib/api')
    const response = await fetch(buildApiUrl('/health'))
    if (!response.ok) throw new Error('Failed to fetch status')
    const health = await response.json()
    
    // Also get ingest status for pipeline info
    const ingestResponse = await fetch(buildApiUrl('/api/ingest/status'))
    const ingest = ingestResponse.ok ? await ingestResponse.json() : { cameras: {} }
    
    // Build a compatible systemStatus object from available data
    systemStatus.value = {
      info: {
        hostname: 'R58 Device',
        platform: health.platform || 'R58',
        gstreamer: health.gstreamer,
        load_average: [0, 0, 0], // Not available
        memory_percent: 0, // Not available
        uptime_seconds: 0, // Not available
        temperatures: [], // Not available
      },
      services: [
        { name: 'r58-recorder', active: health.status === 'healthy', status: health.status },
        { name: 'mediamtx', active: true, status: 'running' },
        { name: 'vdo.ninja', active: true, status: 'running', note: 'r58-vdo.itagenten.no' },
      ],
      pipelines: Object.entries(ingest.cameras || {}).map(([id, cam]: [string, any]) => ({
        pipeline_id: id,
        pipeline_type: 'ingest',
        device: cam.device,
        state: cam.status === 'streaming' ? 'running' : cam.status,
      })),
    }
    error.value = null
  } catch (e: any) {
    error.value = e.message
    console.error('Failed to fetch system status:', e)
  } finally {
    loading.value = false
  }
}

async function restartServices(service: string) {
  // Note: This endpoint may not exist on the device
  toast.info('Service restart not available in this version')
}

async function rebootDevice() {
  // Note: This endpoint may not exist on the device
  toast.info('Device reboot not available in this version')
}

async function stopPipeline(pipelineId: string) {
  try {
    const { buildApiUrl } = await import('@/lib/api')
    const response = await fetch(buildApiUrl(`/api/ingest/stop/${pipelineId}`), {
      method: 'POST'
    })
    const data = await response.json()
    
    if (response.ok) {
      toast.success(`Stopped pipeline: ${pipelineId}`)
      await fetchStatus()
    } else {
      toast.error(data.detail || 'Stop failed')
    }
  } catch (e: any) {
    toast.error(`Stop failed: ${e.message}`)
  }
}

function getServiceStatusColor(service: any) {
  if (service.active) return 'bg-r58-accent-success'
  return 'bg-r58-accent-danger'
}

function getPipelineStateColor(state: string) {
  switch (state) {
    case 'running': return 'text-r58-accent-success'
    case 'starting': return 'text-r58-accent-warning'
    case 'stopping': return 'text-r58-accent-warning'
    default: return 'text-r58-text-secondary'
  }
}

function getGaugeColor(percent: number) {
  if (percent > 90) return 'bg-r58-accent-danger'
  if (percent > 70) return 'bg-r58-accent-warning'
  return 'bg-r58-accent-success'
}

function getTempColor(celsius: number) {
  if (celsius > 80) return 'text-r58-accent-danger'
  if (celsius > 65) return 'text-r58-accent-warning'
  return 'text-r58-accent-success'
}

// Lifecycle
onMounted(() => {
  fetchStatus()
  // Refresh every 10 seconds (reduced from 5s to save resources)
  refreshInterval.value = window.setInterval(fetchStatus, 10000)
})

onUnmounted(() => {
  if (refreshInterval.value) {
    clearInterval(refreshInterval.value)
  }
})
</script>

<template>
  <div class="space-y-6">
    <!-- Loading/Error State -->
    <div v-if="loading" class="flex items-center justify-center py-12">
      <div class="animate-spin w-8 h-8 border-2 border-r58-accent-primary border-t-transparent rounded-full"></div>
    </div>
    
    <div v-else-if="error" class="card bg-r58-accent-danger/10 border border-r58-accent-danger/30">
      <p class="text-r58-accent-danger">Error loading system status: {{ error }}</p>
      <button @click="fetchStatus" class="btn btn-secondary mt-4">Retry</button>
    </div>
    
    <template v-else>
      <!-- System Info Row -->
      <div class="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <!-- CPU Load -->
        <div class="card">
          <h3 class="text-sm font-semibold text-r58-text-secondary uppercase tracking-wide mb-4">CPU Load</h3>
          <div v-if="systemStatus?.info?.load_average?.some((l: number) => l > 0)" class="space-y-3">
            <div class="relative w-full h-4 bg-r58-bg-tertiary rounded-full overflow-hidden">
              <div 
                class="absolute left-0 top-0 h-full rounded-full transition-all duration-500"
                :class="getGaugeColor(cpuPercent)"
                :style="{ width: `${cpuPercent}%` }"
              ></div>
            </div>
            <div class="flex justify-between text-sm">
              <span class="text-r58-text-secondary">Load Average</span>
              <span class="font-mono">
                {{ systemStatus?.info?.load_average?.map((l: number) => l.toFixed(2)).join(' / ') }}
              </span>
            </div>
          </div>
          <div v-else class="flex items-center justify-center py-4">
            <span class="text-r58-text-secondary">N/A</span>
          </div>
        </div>
        
        <!-- Memory -->
        <div class="card">
          <h3 class="text-sm font-semibold text-r58-text-secondary uppercase tracking-wide mb-4">Memory</h3>
          <div v-if="memoryPercent > 0" class="space-y-3">
            <div class="relative w-full h-4 bg-r58-bg-tertiary rounded-full overflow-hidden">
              <div 
                class="absolute left-0 top-0 h-full rounded-full transition-all duration-500"
                :class="getGaugeColor(memoryPercent)"
                :style="{ width: `${memoryPercent}%` }"
              ></div>
            </div>
            <div class="flex justify-between text-sm">
              <span class="text-r58-text-secondary">Used</span>
              <span>{{ memoryPercent.toFixed(1) }}%</span>
            </div>
          </div>
          <div v-else class="flex items-center justify-center py-4">
            <span class="text-r58-text-secondary">N/A</span>
          </div>
        </div>
        
        <!-- Temperature -->
        <div class="card">
          <h3 class="text-sm font-semibold text-r58-text-secondary uppercase tracking-wide mb-4">Temperature</h3>
          <div class="flex items-center justify-center py-2">
            <span 
              v-if="primaryTemp"
              class="text-3xl font-bold"
              :class="getTempColor(primaryTemp.temp_celsius)"
            >
              {{ primaryTemp.temp_celsius.toFixed(1) }}°C
            </span>
            <span v-else class="text-r58-text-secondary">N/A</span>
          </div>
          <p v-if="primaryTemp?.type" class="text-center text-xs text-r58-text-secondary">
            {{ primaryTemp.type }}
          </p>
        </div>
        
        <!-- Uptime -->
        <div class="card">
          <h3 class="text-sm font-semibold text-r58-text-secondary uppercase tracking-wide mb-4">Uptime</h3>
          <div class="flex items-center justify-center py-2">
            <span v-if="systemStatus?.info?.uptime_seconds > 0" class="text-3xl font-bold text-r58-accent-primary">
              {{ uptimeFormatted }}
            </span>
            <span v-else class="text-r58-text-secondary">N/A</span>
          </div>
          <p class="text-center text-xs text-r58-text-secondary">
            {{ systemStatus?.info?.hostname || 'R58 Device' }}
          </p>
        </div>
      </div>
      
      <!-- Services -->
      <div class="card">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-sm font-semibold text-r58-text-secondary uppercase tracking-wide">Services</h3>
          <div class="flex gap-2">
            <button 
              @click="restartServices('all')"
              class="btn btn-sm btn-secondary opacity-50 cursor-not-allowed"
              disabled
              title="Requires SSH access to device"
            >
              Restart All
            </button>
            <button 
              @click="rebootDevice"
              class="btn btn-sm btn-danger opacity-50 cursor-not-allowed"
              disabled
              title="Requires SSH access to device"
            >
              Reboot Device
            </button>
          </div>
        </div>
        
        <div class="grid gap-3 sm:grid-cols-3">
          <div 
            v-for="service in services"
            :key="service.name"
            class="flex items-center justify-between p-3 rounded-lg bg-r58-bg-tertiary"
          >
            <div class="flex items-center gap-3">
              <span 
                class="w-2.5 h-2.5 rounded-full"
                :class="getServiceStatusColor(service)"
              ></span>
              <div>
                <p class="font-medium">{{ service.name }}</p>
                <p class="text-xs text-r58-text-secondary">
                  {{ service.status }}
                  <span v-if="service.memory_mb"> · {{ service.memory_mb.toFixed(0) }} MB</span>
                </p>
              </div>
            </div>
            <button 
              class="text-r58-text-secondary opacity-50 cursor-not-allowed"
              disabled
              title="Requires SSH access"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>
          </div>
        </div>
      </div>
      
      <!-- Pipelines -->
      <div class="card">
        <h3 class="text-sm font-semibold text-r58-text-secondary uppercase tracking-wide mb-4">
          Active Pipelines
          <span class="ml-2 text-r58-accent-primary">({{ pipelines.length }})</span>
        </h3>
        
        <div v-if="pipelines.length === 0" class="text-center py-8 text-r58-text-secondary">
          No active pipelines
        </div>
        
        <div v-else class="space-y-2">
          <div 
            v-for="pipeline in pipelines"
            :key="pipeline.pipeline_id"
            class="flex items-center justify-between p-3 rounded-lg bg-r58-bg-tertiary"
          >
            <div class="flex items-center gap-4">
              <div>
                <p class="font-mono text-sm">{{ pipeline.pipeline_id }}</p>
                <p class="text-xs text-r58-text-secondary">
                  Type: {{ pipeline.pipeline_type }}
                  <span v-if="pipeline.device"> · {{ pipeline.device }}</span>
                </p>
              </div>
            </div>
            <div class="flex items-center gap-3">
              <span 
                class="text-sm font-medium capitalize"
                :class="getPipelineStateColor(pipeline.state)"
              >
                {{ pipeline.state }}
              </span>
              <button 
                v-if="pipeline.state === 'running'"
                @click="stopPipeline(pipeline.pipeline_id)"
                class="btn btn-sm btn-danger"
                title="Stop pipeline"
              >
                Stop
              </button>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

