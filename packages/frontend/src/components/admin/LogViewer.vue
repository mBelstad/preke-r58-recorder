<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { buildApiUrl } from '@/lib/api'

const props = defineProps<{
  service?: string
}>()

const logs = ref('')
const loading = ref(false)
const selectedService = ref(props.service || 'preke-recorder')
const lineCount = ref(100)
const autoRefresh = ref(false)

const services = [
  { id: 'preke-recorder', label: 'Preke Recorder' },
  { id: 'mediamtx', label: 'MediaMTX' },
]

let refreshInterval: number | null = null

async function fetchLogs() {
  loading.value = true
  try {
    const response = await fetch(buildApiUrl(`/api/system/logs?service=${selectedService.value}&lines=${lineCount.value}`))
    const data = await response.json()
    logs.value = data.logs || 'No logs available'
  } catch (e) {
    logs.value = `Error fetching logs: ${e}`
  } finally {
    loading.value = false
  }
}

function startAutoRefresh() {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
  refreshInterval = window.setInterval(fetchLogs, 5000)
}

function stopAutoRefresh() {
  if (refreshInterval) {
    clearInterval(refreshInterval)
    refreshInterval = null
  }
}

watch(autoRefresh, (enabled) => {
  if (enabled) {
    startAutoRefresh()
  } else {
    stopAutoRefresh()
  }
})

watch([selectedService, lineCount], () => {
  fetchLogs()
})

onMounted(() => {
  fetchLogs()
})

onUnmounted(() => {
  stopAutoRefresh()
})
</script>

<template>
  <div class="space-y-4">
    <!-- Controls -->
    <div class="flex items-center gap-4 flex-wrap">
      <select v-model="selectedService" class="input">
        <option v-for="svc in services" :key="svc.id" :value="svc.id">
          {{ svc.label }}
        </option>
      </select>
      
      <select v-model="lineCount" class="input">
        <option :value="50">50 lines</option>
        <option :value="100">100 lines</option>
        <option :value="250">250 lines</option>
        <option :value="500">500 lines</option>
      </select>
      
      <label class="flex items-center gap-2 cursor-pointer">
        <input type="checkbox" v-model="autoRefresh" class="w-4 h-4 rounded" />
        <span class="text-sm">Auto-refresh</span>
      </label>
      
      <button @click="fetchLogs" :disabled="loading" class="btn">
        <span v-if="loading">Loading...</span>
        <span v-else>Refresh</span>
      </button>
    </div>
    
    <!-- Log output -->
    <pre 
      class="bg-r58-bg-primary rounded-lg p-4 font-mono text-sm text-r58-text-secondary h-[500px] overflow-auto whitespace-pre-wrap"
    >{{ logs || 'No logs available' }}</pre>
  </div>
</template>

