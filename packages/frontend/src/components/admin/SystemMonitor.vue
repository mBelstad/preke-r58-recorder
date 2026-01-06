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
    const { buildApiUrl } = await import('@/lib/api')
    
    // Fetch all data in parallel
    const [healthRes, ingestRes, systemInfoRes] = await Promise.all([
      fetch(buildApiUrl('/health')),
      fetch(buildApiUrl('/api/ingest/status')),
      fetch(buildApiUrl('/api/system/info'))
    ])
    
    const health = healthRes.ok ? await healthRes.json() : { status: 'unknown' }
    const ingest = ingestRes.ok ? await ingestRes.json() : { cameras: {} }
    const systemInfo = systemInfoRes.ok ? await systemInfoRes.json() : null
    
    // Build a compatible systemStatus object
    systemStatus.value = {
      info: {
        hostname: systemInfo?.hostname || 'R58 Device',
        platform: health.platform || 'R58',
        gstreamer: health.gstreamer,
        load_average: systemInfo?.load_average || [0, 0, 0],
        memory_percent: systemInfo?.memory_percent || 0,
        memory_total_mb: systemInfo?.memory_total_mb || 0,
        memory_used_mb: systemInfo?.memory_used_mb || 0,
        uptime_seconds: systemInfo?.uptime_seconds || 0,
        temperatures: systemInfo?.temperatures || [],
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
  try {
    const { buildApiUrl } = await import('@/lib/api')
    const response = await fetch(buildApiUrl(`/api/system/restart-service/${service}`), {
      method: 'POST'
    })
    const data = await response.json()
    
    if (data.success) {
      toast.success(data.message || `Service ${service} restarted`)
      // Refresh status after a short delay
      setTimeout(fetchStatus, 2000)
    } else {
      toast.error(data.message || `Failed to restart ${service}`)
    }
  } catch (e: any) {
    toast.error(`Restart failed: ${e.message}`)
  }
}

async function rebootDevice() {
  if (!confirm('Are you sure you want to reboot the device? This will interrupt all recordings and streams.')) {
    return
  }
  
  try {
    const { buildApiUrl } = await import('@/lib/api')
    const response = await fetch(buildApiUrl('/api/system/reboot'), {
      method: 'POST'
    })
    const data = await response.json()
    
    if (data.success) {
      toast.success('Device is rebooting...')
    } else {
      toast.error(data.message || 'Failed to reboot device')
    }
  } catch (e: any) {
    toast.error(`Reboot failed: ${e.message}`)
  }
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
  if (service.active) return 'bg-preke-green'
  return 'bg-preke-red'
}

function getPipelineStateColor(state: string) {
  switch (state) {
    case 'running': return 'text-preke-green'
    case 'starting': return 'text-preke-gold'
    case 'stopping': return 'text-preke-gold'
    default: return 'text-preke-text-muted'
  }
}

function getGaugeColor(percent: number) {
  if (percent > 90) return 'bg-preke-red'
  if (percent > 70) return 'bg-preke-gold'
  return 'bg-preke-green'
}

function getTempColor(celsius: number) {
  if (celsius > 80) return 'text-preke-red'
  if (celsius > 65) return 'text-preke-gold'
  return 'text-preke-green'
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
      <div class="animate-spin w-8 h-8 border-2 border-preke-gold border-t-transparent rounded-full"></div>
    </div>
    
    <div v-else-if="error" class="glass-card p-4 bg-preke-red/10 border border-preke-red/30 rounded-xl">
      <p class="text-preke-red">Error loading system status: {{ error }}</p>
      <button @click="fetchStatus" class="btn-v2 btn-v2--secondary mt-4">Retry</button>
    </div>
    
    <template v-else>
      <!-- System Info Row -->
      <div class="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <!-- CPU Load -->
        <div class="glass-card p-4 rounded-xl">
          <h3 class="text-xs font-semibold text-preke-text-muted uppercase tracking-wide mb-4">CPU Load</h3>
          <div v-if="systemStatus?.info?.load_average?.some((l: number) => l > 0)" class="space-y-3">
            <div class="relative w-full h-3 bg-preke-bg rounded-full overflow-hidden">
              <div 
                class="absolute left-0 top-0 h-full rounded-full transition-all duration-500"
                :class="getGaugeColor(cpuPercent)"
                :style="{ width: `${cpuPercent}%` }"
              ></div>
            </div>
            <div class="flex justify-between text-sm">
              <span class="text-preke-text-muted">Load Average</span>
              <span class="font-mono text-preke-text">
                {{ systemStatus?.info?.load_average?.map((l: number) => l.toFixed(2)).join(' / ') }}
              </span>
            </div>
          </div>
          <div v-else class="flex items-center justify-center py-4">
            <span class="text-preke-text-muted">N/A</span>
          </div>
        </div>
        
        <!-- Memory -->
        <div class="glass-card p-4 rounded-xl">
          <h3 class="text-xs font-semibold text-preke-text-muted uppercase tracking-wide mb-4">Memory</h3>
          <div v-if="memoryPercent > 0" class="space-y-3">
            <div class="relative w-full h-3 bg-preke-bg rounded-full overflow-hidden">
              <div 
                class="absolute left-0 top-0 h-full rounded-full transition-all duration-500"
                :class="getGaugeColor(memoryPercent)"
                :style="{ width: `${memoryPercent}%` }"
              ></div>
            </div>
            <div class="flex justify-between text-sm">
              <span class="text-preke-text-muted">Used</span>
              <span class="text-preke-text">{{ memoryPercent.toFixed(1) }}%</span>
            </div>
          </div>
          <div v-else class="flex items-center justify-center py-4">
            <span class="text-preke-text-muted">N/A</span>
          </div>
        </div>
        
        <!-- Temperature -->
        <div class="glass-card p-4 rounded-xl">
          <h3 class="text-xs font-semibold text-preke-text-muted uppercase tracking-wide mb-4">Temperature</h3>
          <div class="flex items-center justify-center py-2">
            <span 
              v-if="primaryTemp"
              class="text-3xl font-bold"
              :class="getTempColor(primaryTemp.temp_celsius)"
            >
              {{ primaryTemp.temp_celsius.toFixed(1) }}°C
            </span>
            <span v-else class="text-preke-text-muted">N/A</span>
          </div>
          <p v-if="primaryTemp?.type" class="text-center text-xs text-preke-text-muted">
            {{ primaryTemp.type }}
          </p>
        </div>
        
        <!-- Uptime -->
        <div class="glass-card p-4 rounded-xl">
          <h3 class="text-xs font-semibold text-preke-text-muted uppercase tracking-wide mb-4">Uptime</h3>
          <div class="flex items-center justify-center py-2">
            <span v-if="systemStatus?.info?.uptime_seconds > 0" class="text-3xl font-bold text-preke-gold">
              {{ uptimeFormatted }}
            </span>
            <span v-else class="text-preke-text-muted">N/A</span>
          </div>
          <p class="text-center text-xs text-preke-text-muted">
            {{ systemStatus?.info?.hostname || 'R58 Device' }}
          </p>
        </div>
      </div>
      
      <!-- Services -->
      <div class="glass-card p-4 rounded-xl">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-xs font-semibold text-preke-text-muted uppercase tracking-wide">Services</h3>
          <div class="flex gap-2">
            <button 
              @click="restartServices('preke-recorder')"
              class="btn-v2 btn-v2--secondary text-sm"
              title="Restart the main service"
            >
              Restart Service
            </button>
            <button 
              @click="rebootDevice"
              class="btn-v2 btn-v2--danger text-sm"
              title="Reboot the device"
            >
              Reboot Device
            </button>
          </div>
        </div>
        
        <div class="grid gap-3 sm:grid-cols-3">
          <div 
            v-for="service in services"
            :key="service.name"
            class="flex items-center justify-between p-3 rounded-lg bg-preke-surface border border-preke-surface-border"
          >
            <div class="flex items-center gap-3">
              <span 
                class="w-2.5 h-2.5 rounded-full"
                :class="getServiceStatusColor(service)"
              ></span>
              <div>
                <p class="font-medium text-preke-text">{{ service.name }}</p>
                <p class="text-xs text-preke-text-muted">
                  {{ service.status }}
                  <span v-if="service.memory_mb"> · {{ service.memory_mb.toFixed(0) }} MB</span>
                </p>
              </div>
            </div>
            <button 
              v-if="service.name !== 'vdo.ninja'"
              @click="restartServices(service.name)"
              class="text-preke-text-muted hover:text-preke-gold transition-colors"
              title="Restart service"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>
            <span v-else class="text-xs text-preke-text-muted">External</span>
          </div>
        </div>
      </div>
      
      <!-- Pipelines -->
      <div class="glass-card p-4 rounded-xl">
        <h3 class="text-xs font-semibold text-preke-text-muted uppercase tracking-wide mb-4">
          Active Pipelines
          <span class="ml-2 text-preke-gold">({{ pipelines.length }})</span>
        </h3>
        
        <div v-if="pipelines.length === 0" class="text-center py-8 text-preke-text-muted">
          No active pipelines
        </div>
        
        <div v-else class="space-y-2">
          <div 
            v-for="pipeline in pipelines"
            :key="pipeline.pipeline_id"
            class="flex items-center justify-between p-3 rounded-lg bg-preke-surface border border-preke-surface-border"
          >
            <div class="flex items-center gap-4">
              <div>
                <p class="font-mono text-sm text-preke-text">{{ pipeline.pipeline_id }}</p>
                <p class="text-xs text-preke-text-muted">
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
                class="btn-v2 btn-v2--danger text-sm"
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

