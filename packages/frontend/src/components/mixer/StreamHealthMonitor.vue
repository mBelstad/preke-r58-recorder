<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useStreamingStore } from '@/stores/streaming'
import { buildProgramOutputUrl, buildProgramOutputUrlAlpha } from '@/lib/vdoninja'

const streamingStore = useStreamingStore()

const now = ref(Date.now())
const localStatus = ref<any | null>(null)
const localStats = ref<any | null>(null)
let pollTimer: ReturnType<typeof setInterval> | null = null
let clockTimer: ReturnType<typeof setInterval> | null = null
const programOutputUrl = ref<string>('')

const isActive = computed(() => localStatus.value?.mixer_program_active === true)
const rtmpRelayActive = computed(() => localStatus.value?.rtmp_relay_configured === true)
const runOnReady = computed(() => localStatus.value?.run_on_ready || null)
const lastError = computed(() => localStatus.value?.error || localStats.value?.error || null)

const bitrateBps = computed(() => {
  const bps = localStats.value?.bitrate_bps || localStats.value?.bitrate || null
  return typeof bps === 'number' ? bps : null
})

const resolution = computed(() => localStats.value?.resolution || localStats.value?.source?.video?.resolution || null)
const fps = computed(() => localStats.value?.fps || localStats.value?.source?.video?.fps || null)

const streamDuration = computed(() => {
  const start = streamingStore.streamStartTime
  if (!start) return '—'
  const diffMs = now.value - start
  if (diffMs < 0) return '—'
  const totalSeconds = Math.floor(diffMs / 1000)
  const hours = Math.floor(totalSeconds / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = totalSeconds % 60
  if (hours > 0) {
    return `${hours}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`
  }
  return `${minutes}:${seconds.toString().padStart(2, '0')}`
})

const bitrateDisplay = computed(() => {
  if (!bitrateBps.value) return '—'
  const kbps = bitrateBps.value / 1000
  if (kbps < 1000) return `${kbps.toFixed(0)} kbps`
  const mbps = kbps / 1000
  return `${mbps.toFixed(2)} Mbps`
})

const connectionQuality = computed(() => {
  if (!isActive.value) return 'Offline'
  if (!bitrateBps.value) return 'Connecting'
  if (bitrateBps.value >= 2000000) return 'Good'
  if (bitrateBps.value >= 800000) return 'Fair'
  return 'Poor'
})

async function refreshStatus() {
  const status = await streamingStore.getStreamingStatus()
  if (status) {
    localStatus.value = status
    streamingStore.streamStatus = status
    streamingStore.markStreamActive(status.mixer_program_active === true)
  }
  const stats = await streamingStore.getStreamingStats()
  if (stats) {
    localStats.value = stats
    streamingStore.streamStats = stats
  }
}

async function refreshProgramOutputUrl() {
  const isAlpha = streamingStore.programOutputMode === 'alpha'
  const url = isAlpha
    ? await buildProgramOutputUrlAlpha()
    : await buildProgramOutputUrl('https://app.itagenten.no/mixer_program/whip')
  programOutputUrl.value = url || ''
}

function startPolling() {
  if (pollTimer) return
  pollTimer = setInterval(refreshStatus, 2000)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

onMounted(() => {
  refreshStatus()
  refreshProgramOutputUrl()
  startPolling()
  clockTimer = setInterval(() => {
    now.value = Date.now()
  }, 1000)
})

onBeforeUnmount(() => {
  stopPolling()
  if (clockTimer) {
    clearInterval(clockTimer)
    clockTimer = null
  }
})

watch(isActive, (active) => {
  streamingStore.markStreamActive(active)
})

watch(() => streamingStore.programOutputMode, () => {
  refreshProgramOutputUrl()
})
</script>

<template>
  <div class="stream-health space-y-3">
    <div class="flex items-center gap-2">
      <span :class="['w-2 h-2 rounded-full', isActive ? 'bg-emerald-500' : 'bg-gray-500']"></span>
      <span class="text-sm font-medium">
        {{ isActive ? 'Program output active' : 'Program output inactive' }}
      </span>
      <span v-if="rtmpRelayActive" class="text-xs text-preke-green">RTMP relay on</span>
    </div>

    <div class="grid grid-cols-2 gap-3 text-xs text-preke-text-dim">
      <div class="flex items-center justify-between bg-preke-bg-surface/50 rounded-md px-3 py-2">
        <span>Duration</span>
        <span class="text-preke-text">{{ streamDuration }}</span>
      </div>
      <div class="flex items-center justify-between bg-preke-bg-surface/50 rounded-md px-3 py-2">
        <span>Quality</span>
        <span class="text-preke-text">{{ connectionQuality }}</span>
      </div>
      <div class="flex items-center justify-between bg-preke-bg-surface/50 rounded-md px-3 py-2">
        <span>Bitrate</span>
        <span class="text-preke-text">{{ bitrateDisplay }}</span>
      </div>
      <div class="flex items-center justify-between bg-preke-bg-surface/50 rounded-md px-3 py-2">
        <span>Resolution</span>
        <span class="text-preke-text">{{ resolution || '—' }}</span>
      </div>
      <div class="flex items-center justify-between bg-preke-bg-surface/50 rounded-md px-3 py-2">
        <span>FPS</span>
        <span class="text-preke-text">{{ fps || '—' }}</span>
      </div>
    </div>

    <div v-if="runOnReady" class="text-xs text-preke-text-dim bg-preke-bg-surface/50 rounded-md px-3 py-2">
      <span class="block text-preke-text-muted">RTMP relay</span>
      <code class="block truncate text-preke-text">{{ runOnReady }}</code>
    </div>

    <div v-if="programOutputUrl" class="text-xs text-preke-text-dim bg-preke-bg-surface/50 rounded-md px-3 py-2">
      <div class="flex items-center justify-between gap-2">
        <span class="text-preke-text-muted">Program output URL</span>
        <button
          class="text-preke-gold hover:underline"
          @click="navigator.clipboard.writeText(programOutputUrl)"
        >
          Copy
        </button>
      </div>
      <code class="block truncate text-preke-text">{{ programOutputUrl }}</code>
    </div>

    <div v-if="lastError" class="text-xs text-preke-red bg-preke-bg-surface/50 rounded-md px-3 py-2">
      {{ lastError }}
    </div>
  </div>
</template>

<style scoped>
.stream-health {
  border-top: 1px solid var(--preke-border);
  padding-top: 12px;
}
</style>
