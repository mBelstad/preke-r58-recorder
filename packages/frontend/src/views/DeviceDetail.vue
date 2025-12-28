<script setup lang="ts">
/**
 * Device Detail View
 * 
 * Shows detailed information about a single device including:
 * - Status and metrics
 * - Heartbeat history
 * - Command history
 * - Actions (update, restart, bundle)
 */
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { r58Api } from '@/lib/api'

// Types
interface Device {
  id: string
  device_id: string
  name: string
  status: string
  current_version?: string
  target_version?: string
  update_channel?: string
  last_heartbeat?: string
  cpu_percent?: number
  mem_percent?: number
  disk_free_gb?: number
  temperature_c?: number
  recording_active?: boolean
  mixer_active?: boolean
  uptime_seconds?: number
  platform?: string
  arch?: string
  location?: string
  tags?: string[]
  capabilities?: Record<string, any>
  pending_commands?: number
  active_alerts?: number
  created_at?: string
}

interface Command {
  id: string
  type: string
  status: string
  priority: number
  created_at: string
  completed_at?: string
  error?: string
}

interface Heartbeat {
  received_at: string
  cpu_percent: number
  mem_percent: number
  disk_free_gb: number
  temperature_c?: number
}

// State
const route = useRoute()
const router = useRouter()
const device = ref<Device | null>(null)
const commands = ref<Command[]>([])
const heartbeats = ref<Heartbeat[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const activeTab = ref<'overview' | 'commands' | 'metrics' | 'settings'>('overview')
const refreshInterval = ref<number | null>(null)

// Command modal
const showCommandModal = ref(false)
const commandType = ref('')
const commandPayload = ref('')
const commandSending = ref(false)

// Computed
const deviceId = computed(() => route.params.deviceId as string)

const uptimeFormatted = computed(() => {
  if (!device.value?.uptime_seconds) return 'Unknown'
  const seconds = device.value.uptime_seconds
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const mins = Math.floor((seconds % 3600) / 60)
  
  if (days > 0) return `${days}d ${hours}h`
  if (hours > 0) return `${hours}h ${mins}m`
  return `${mins}m`
})

// Methods
async function fetchDevice() {
  try {
    device.value = await r58Api.fleet?.device(deviceId.value)
    error.value = null
  } catch (e) {
    error.value = 'Failed to load device'
    console.error('Device fetch error:', e)
  } finally {
    loading.value = false
  }
}

async function fetchCommands() {
  try {
    const response = await r58Api.fleet?.deviceCommands(deviceId.value)
    commands.value = response?.items || []
  } catch (e) {
    console.error('Commands fetch error:', e)
  }
}

async function fetchHeartbeats() {
  try {
    const response = await r58Api.fleet?.deviceHeartbeats(deviceId.value)
    heartbeats.value = response?.items || []
  } catch (e) {
    console.error('Heartbeats fetch error:', e)
  }
}

async function sendCommand() {
  if (!commandType.value) return
  
  commandSending.value = true
  try {
    let payload = {}
    if (commandPayload.value) {
      payload = JSON.parse(commandPayload.value)
    }
    
    await r58Api.fleet?.sendCommand(deviceId.value, {
      type: commandType.value,
      payload,
    })
    
    showCommandModal.value = false
    commandType.value = ''
    commandPayload.value = ''
    await fetchCommands()
  } catch (e) {
    console.error('Command send error:', e)
    alert('Failed to send command')
  } finally {
    commandSending.value = false
  }
}

async function requestBundle() {
  try {
    await r58Api.fleet?.requestBundle(deviceId.value, {
      include_logs: true,
      include_config: true,
      include_recordings: false,
    })
    alert('Support bundle requested')
  } catch (e) {
    console.error('Bundle request error:', e)
    alert('Failed to request bundle')
  }
}

function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    online: 'bg-emerald-500',
    offline: 'bg-zinc-500',
    updating: 'bg-amber-500',
    error: 'bg-red-500',
    maintenance: 'bg-blue-500',
    pending: 'bg-zinc-500',
    sent: 'bg-blue-500',
    acked: 'bg-amber-500',
    running: 'bg-purple-500',
    completed: 'bg-emerald-500',
    failed: 'bg-red-500',
  }
  return colors[status] || 'bg-zinc-400'
}

function formatDate(timestamp?: string): string {
  if (!timestamp) return '-'
  return new Date(timestamp).toLocaleString()
}

// Lifecycle
onMounted(async () => {
  await fetchDevice()
  await Promise.all([fetchCommands(), fetchHeartbeats()])
  refreshInterval.value = window.setInterval(fetchDevice, 10000)
})

onUnmounted(() => {
  if (refreshInterval.value) {
    clearInterval(refreshInterval.value)
  }
})

watch(deviceId, async () => {
  loading.value = true
  await fetchDevice()
  await Promise.all([fetchCommands(), fetchHeartbeats()])
})
</script>

<template>
  <div class="device-detail p-6">
    <!-- Back Button -->
    <button 
      @click="router.push('/fleet')"
      class="flex items-center gap-2 text-zinc-400 hover:text-zinc-200 transition-colors mb-4"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
      </svg>
      Back to Fleet
    </button>

    <!-- Loading -->
    <div v-if="loading" class="text-center py-12">
      <div class="animate-spin w-8 h-8 border-2 border-zinc-600 border-t-emerald-500 rounded-full mx-auto"></div>
      <p class="text-zinc-400 mt-4">Loading device...</p>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="p-4 bg-red-900/20 border border-red-800 rounded-lg text-red-400">
      {{ error }}
    </div>

    <!-- Device Content -->
    <template v-else-if="device">
      <!-- Header -->
      <div class="flex items-start justify-between mb-6">
        <div>
          <div class="flex items-center gap-3">
            <h1 class="text-2xl font-semibold text-zinc-100">{{ device.name }}</h1>
            <span 
              :class="['flex items-center gap-1 px-2 py-1 rounded text-sm', getStatusColor(device.status), 'bg-opacity-20']"
            >
              <span :class="['w-2 h-2 rounded-full', getStatusColor(device.status)]"></span>
              {{ device.status }}
            </span>
          </div>
          <p class="text-zinc-500 font-mono text-sm mt-1">{{ device.device_id }}</p>
        </div>
        <div class="flex items-center gap-2">
          <button 
            @click="requestBundle"
            class="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 rounded-lg transition-colors"
          >
            Request Bundle
          </button>
          <button 
            @click="showCommandModal = true"
            class="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg transition-colors"
          >
            Send Command
          </button>
        </div>
      </div>

      <!-- Tabs -->
      <div class="flex gap-1 mb-6 border-b border-zinc-800">
        <button
          v-for="tab in ['overview', 'commands', 'metrics', 'settings']"
          :key="tab"
          @click="activeTab = tab as any"
          :class="[
            'px-4 py-2 text-sm font-medium transition-colors capitalize',
            activeTab === tab 
              ? 'text-emerald-400 border-b-2 border-emerald-400' 
              : 'text-zinc-400 hover:text-zinc-200'
          ]"
        >
          {{ tab }}
        </button>
      </div>

      <!-- Overview Tab -->
      <div v-if="activeTab === 'overview'" class="space-y-6">
        <!-- Metrics Grid -->
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div class="p-4 bg-zinc-900/50 border border-zinc-800 rounded-lg">
            <div class="text-sm text-zinc-500">CPU Usage</div>
            <div class="text-2xl font-semibold" :class="device.cpu_percent && device.cpu_percent > 80 ? 'text-red-400' : 'text-zinc-100'">
              {{ device.cpu_percent?.toFixed(0) || '-' }}%
            </div>
          </div>
          <div class="p-4 bg-zinc-900/50 border border-zinc-800 rounded-lg">
            <div class="text-sm text-zinc-500">Memory Usage</div>
            <div class="text-2xl font-semibold" :class="device.mem_percent && device.mem_percent > 80 ? 'text-red-400' : 'text-zinc-100'">
              {{ device.mem_percent?.toFixed(0) || '-' }}%
            </div>
          </div>
          <div class="p-4 bg-zinc-900/50 border border-zinc-800 rounded-lg">
            <div class="text-sm text-zinc-500">Disk Free</div>
            <div class="text-2xl font-semibold" :class="device.disk_free_gb && device.disk_free_gb < 2 ? 'text-red-400' : 'text-zinc-100'">
              {{ device.disk_free_gb?.toFixed(1) || '-' }} GB
            </div>
          </div>
          <div class="p-4 bg-zinc-900/50 border border-zinc-800 rounded-lg">
            <div class="text-sm text-zinc-500">Temperature</div>
            <div class="text-2xl font-semibold" :class="device.temperature_c && device.temperature_c > 70 ? 'text-red-400' : 'text-zinc-100'">
              {{ device.temperature_c?.toFixed(0) || '-' }}°C
            </div>
          </div>
        </div>

        <!-- Info Cards -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <!-- Version Info -->
          <div class="p-4 bg-zinc-900/50 border border-zinc-800 rounded-lg">
            <h3 class="text-sm font-medium text-zinc-400 mb-3">Version Info</h3>
            <div class="space-y-2">
              <div class="flex justify-between">
                <span class="text-zinc-500">Current Version</span>
                <span class="text-zinc-100 font-mono">v{{ device.current_version || 'unknown' }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-zinc-500">Target Version</span>
                <span :class="device.target_version ? 'text-amber-400' : 'text-zinc-400'" class="font-mono">
                  {{ device.target_version ? `v${device.target_version}` : 'None' }}
                </span>
              </div>
              <div class="flex justify-between">
                <span class="text-zinc-500">Update Channel</span>
                <span class="text-zinc-100 capitalize">{{ device.update_channel || 'stable' }}</span>
              </div>
            </div>
          </div>

          <!-- System Info -->
          <div class="p-4 bg-zinc-900/50 border border-zinc-800 rounded-lg">
            <h3 class="text-sm font-medium text-zinc-400 mb-3">System Info</h3>
            <div class="space-y-2">
              <div class="flex justify-between">
                <span class="text-zinc-500">Platform</span>
                <span class="text-zinc-100">{{ device.platform || 'Unknown' }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-zinc-500">Architecture</span>
                <span class="text-zinc-100">{{ device.arch || 'arm64' }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-zinc-500">Uptime</span>
                <span class="text-zinc-100">{{ uptimeFormatted }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-zinc-500">Last Heartbeat</span>
                <span class="text-zinc-100">{{ formatDate(device.last_heartbeat) }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Activity Status -->
        <div v-if="device.recording_active || device.mixer_active" class="p-4 bg-zinc-900/50 border border-zinc-800 rounded-lg">
          <h3 class="text-sm font-medium text-zinc-400 mb-3">Current Activity</h3>
          <div class="flex items-center gap-4">
            <div v-if="device.recording_active" class="flex items-center gap-2 px-3 py-1.5 bg-red-500/20 text-red-400 rounded-lg">
              <span class="w-2 h-2 bg-red-500 rounded-full animate-pulse"></span>
              Recording Active
            </div>
            <div v-if="device.mixer_active" class="flex items-center gap-2 px-3 py-1.5 bg-emerald-500/20 text-emerald-400 rounded-lg">
              <span class="w-2 h-2 bg-emerald-500 rounded-full"></span>
              Mixer Active
            </div>
          </div>
        </div>
      </div>

      <!-- Commands Tab -->
      <div v-if="activeTab === 'commands'" class="space-y-4">
        <div v-if="commands.length === 0" class="text-center py-8 text-zinc-500">
          No commands sent to this device yet
        </div>
        <div 
          v-for="cmd in commands" 
          :key="cmd.id"
          class="p-4 bg-zinc-900/50 border border-zinc-800 rounded-lg"
        >
          <div class="flex items-center justify-between mb-2">
            <div class="flex items-center gap-2">
              <span class="font-medium text-zinc-100 capitalize">{{ cmd.type }}</span>
              <span 
                :class="['px-2 py-0.5 text-xs rounded', getStatusColor(cmd.status), 'bg-opacity-20']"
              >
                {{ cmd.status }}
              </span>
            </div>
            <span class="text-sm text-zinc-500">{{ formatDate(cmd.created_at) }}</span>
          </div>
          <div v-if="cmd.error" class="text-sm text-red-400 mt-2">
            Error: {{ cmd.error }}
          </div>
        </div>
      </div>

      <!-- Metrics Tab -->
      <div v-if="activeTab === 'metrics'" class="space-y-4">
        <p class="text-zinc-400">Metrics history visualization coming soon...</p>
        <div class="text-sm text-zinc-500">
          Recent heartbeats: {{ heartbeats.length }}
        </div>
      </div>

      <!-- Settings Tab -->
      <div v-if="activeTab === 'settings'" class="space-y-4">
        <div class="p-4 bg-zinc-900/50 border border-zinc-800 rounded-lg">
          <h3 class="text-sm font-medium text-zinc-400 mb-3">Device Settings</h3>
          <div class="space-y-4">
            <div>
              <label class="block text-sm text-zinc-500 mb-1">Device Name</label>
              <input 
                :value="device.name"
                class="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-zinc-200"
              />
            </div>
            <div>
              <label class="block text-sm text-zinc-500 mb-1">Location</label>
              <input 
                :value="device.location || ''"
                class="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-zinc-200"
                placeholder="e.g., Studio A, Main Hall"
              />
            </div>
            <div>
              <label class="block text-sm text-zinc-500 mb-1">Update Channel</label>
              <select class="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-zinc-200">
                <option value="stable">Stable</option>
                <option value="beta">Beta</option>
                <option value="dev">Dev</option>
              </select>
            </div>
          </div>
          <button class="mt-4 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg">
            Save Changes
          </button>
        </div>
      </div>
    </template>

    <!-- Command Modal -->
    <div v-if="showCommandModal" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div class="bg-zinc-900 border border-zinc-800 rounded-xl p-6 w-full max-w-md">
        <h2 class="text-lg font-semibold text-zinc-100 mb-4">Send Command</h2>
        
        <div class="space-y-4">
          <div>
            <label class="block text-sm text-zinc-400 mb-1">Command Type</label>
            <select 
              v-model="commandType"
              class="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-zinc-200"
            >
              <option value="">Select command...</option>
              <option value="reboot">Reboot Device</option>
              <option value="restart_service">Restart Service</option>
              <option value="bundle">Request Support Bundle</option>
              <option value="config">Update Config</option>
              <option value="update">Trigger Update</option>
            </select>
          </div>
          
          <div>
            <label class="block text-sm text-zinc-400 mb-1">Payload (JSON)</label>
            <textarea 
              v-model="commandPayload"
              class="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-zinc-200 font-mono text-sm h-24"
              placeholder="{}"
            ></textarea>
          </div>
        </div>
        
        <div class="flex justify-end gap-2 mt-6">
          <button 
            @click="showCommandModal = false"
            class="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 rounded-lg"
          >
            Cancel
          </button>
          <button 
            @click="sendCommand"
            :disabled="!commandType || commandSending"
            class="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg disabled:opacity-50"
          >
            {{ commandSending ? 'Sending...' : 'Send Command' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

