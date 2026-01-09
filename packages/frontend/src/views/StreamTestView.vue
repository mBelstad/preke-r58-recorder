<script setup lang="ts">
/**
 * StreamTestView - Test page for viewing MediaMTX RTMP/SRT streams
 * 
 * This view provides test playback for:
 * - Individual camera WHEP streams
 * - Mixed program output
 * - RTMP/SRT stream URLs for external players
 * - Stream health monitoring
 */
import { ref, computed, onMounted, onUnmounted } from 'vue'

// MediaMTX API base URL (same-domain proxy)
// When accessed from app.itagenten.no, requests go through nginx proxy
const isProduction = typeof window !== 'undefined' && window.location.hostname === 'app.itagenten.no'
const MEDIAMTX_API = isProduction ? '' : 'https://app.itagenten.no'
const MEDIAMTX_LOCAL = 'http://localhost:9997'

// Available streams
const streams = ref<Array<{
  name: string
  label: string
  available: boolean
  viewers: number
  bytesReceived: number
  bytesSent: number
}>>([])

// Selected stream for preview
const selectedStream = ref<string | null>(null)

// Loading state
const loading = ref(true)
const error = ref<string | null>(null)

// Polling interval
let pollInterval: ReturnType<typeof setInterval> | null = null

/**
 * Fetch available streams from MediaMTX API
 */
async function fetchStreams() {
  try {
    const response = await fetch(`${MEDIAMTX_API}/v3/paths/list`)
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`)
    }
    const data = await response.json()
    
    if (data.items) {
      streams.value = data.items.map((item: any) => ({
        name: item.name,
        label: item.name.replace('cam', 'Camera ').replace('mixer_program', 'Program Output'),
        available: item.ready || false,
        viewers: item.readers?.length || 0,
        bytesReceived: item.bytesReceived || 0,
        bytesSent: item.bytesSent || 0
      }))
    }
    error.value = null
  } catch (err) {
    console.error('[StreamTest] Failed to fetch streams:', err)
    error.value = 'Failed to connect to MediaMTX API'
    
    // Show default streams even if API fails
    streams.value = [
      { name: 'cam0', label: 'Camera 0 (HDMI-IN0)', available: false, viewers: 0, bytesReceived: 0, bytesSent: 0 },
      { name: 'cam2', label: 'Camera 2 (HDMI-IN11)', available: false, viewers: 0, bytesReceived: 0, bytesSent: 0 },
      { name: 'cam3', label: 'Camera 3 (HDMI-IN21)', available: false, viewers: 0, bytesReceived: 0, bytesSent: 0 },
      { name: 'mixer_program', label: 'Program Output', available: false, viewers: 0, bytesReceived: 0, bytesSent: 0 }
    ]
  } finally {
    loading.value = false
  }
}

// Stream URL generators
const getWhepUrl = (streamName: string) => `${MEDIAMTX_API}/${streamName}/whep`
const getRtspUrl = (streamName: string) => `rtsp://app.itagenten.no:8554/${streamName}`
const getSrtUrl = (streamName: string) => `srt://app.itagenten.no:8890?streamid=read:${streamName}`
const getHlsUrl = (streamName: string) => `${MEDIAMTX_API}/${streamName}/index.m3u8`
const getWebRtcUrl = (streamName: string) => `${MEDIAMTX_API}/${streamName}/`

// Local URLs (for testing on R58 device)
const getLocalWhepUrl = (streamName: string) => `http://localhost:8889/${streamName}/whep`
const getLocalRtspUrl = (streamName: string) => `rtsp://localhost:8554/${streamName}`
const getLocalSrtUrl = (streamName: string) => `srt://localhost:8890?streamid=read:${streamName}`

// Copy to clipboard
async function copyToClipboard(text: string, label: string) {
  try {
    await navigator.clipboard.writeText(text)
    alert(`Copied ${label} URL to clipboard!`)
  } catch (err) {
    console.error('Failed to copy:', err)
    // Fallback for older browsers
    const textArea = document.createElement('textarea')
    textArea.value = text
    document.body.appendChild(textArea)
    textArea.select()
    document.execCommand('copy')
    document.body.removeChild(textArea)
    alert(`Copied ${label} URL to clipboard!`)
  }
}

// Open stream in new window (for WHEP preview)
function openPreview(streamName: string) {
  const url = `https://r58-vdo.itagenten.no/?view=${streamName}&solo&room=studio&password=preke-r58-2024`
  window.open(url, `preview_${streamName}`, 'width=1280,height=720,menubar=no,toolbar=no')
}

// Open MediaMTX WebRTC player
function openWebRtcPlayer(streamName: string) {
  const url = getWebRtcUrl(streamName)
  window.open(url, `webrtc_${streamName}`, 'width=1280,height=720,menubar=no,toolbar=no')
}

// Format bytes for display
function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

onMounted(() => {
  fetchStreams()
  // Poll every 5 seconds
  pollInterval = setInterval(fetchStreams, 5000)
})

onUnmounted(() => {
  if (pollInterval) {
    clearInterval(pollInterval)
  }
})
</script>

<template>
  <div class="h-full flex flex-col bg-slate-900 text-white overflow-auto">
    <!-- Header -->
    <header class="flex items-center justify-between px-6 py-4 border-b border-slate-700 bg-slate-800">
      <div class="flex items-center gap-4">
        <h1 class="text-2xl font-bold text-emerald-400">Stream Test Page</h1>
        <span class="text-sm text-slate-400">MediaMTX Stream Monitor</span>
      </div>
      <div class="flex items-center gap-3">
        <span v-if="loading" class="text-amber-400">Loading...</span>
        <span v-else-if="error" class="text-red-400">{{ error }}</span>
        <span v-else class="text-emerald-400">{{ streams.length }} streams found</span>
        <button 
          @click="fetchStreams"
          class="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 rounded text-sm transition"
        >
          Refresh
        </button>
      </div>
    </header>

    <!-- Main Content -->
    <main class="flex-1 p-6 overflow-auto">
      <!-- Stream Cards Grid -->
      <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        <div 
          v-for="stream in streams" 
          :key="stream.name"
          class="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden shadow-lg"
        >
          <!-- Stream Header -->
          <div class="px-4 py-3 bg-slate-700/50 border-b border-slate-600 flex items-center justify-between">
            <div class="flex items-center gap-3">
              <div 
                :class="[
                  'w-3 h-3 rounded-full',
                  stream.available ? 'bg-emerald-500 animate-pulse' : 'bg-slate-500'
                ]"
              ></div>
              <h2 class="font-semibold text-lg">{{ stream.label }}</h2>
            </div>
            <span class="text-xs text-slate-400 font-mono">{{ stream.name }}</span>
          </div>

          <!-- Stream Status -->
          <div class="p-4 space-y-4">
            <div class="flex items-center gap-4 text-sm">
              <span :class="stream.available ? 'text-emerald-400' : 'text-red-400'">
                {{ stream.available ? '● Live' : '○ Offline' }}
              </span>
              <span class="text-slate-400">
                {{ stream.viewers }} viewer{{ stream.viewers !== 1 ? 's' : '' }}
              </span>
            </div>

            <!-- Traffic Stats -->
            <div class="grid grid-cols-2 gap-2 text-xs text-slate-400">
              <div>
                <span class="text-slate-500">↓ Received:</span>
                <span class="ml-1 text-slate-300">{{ formatBytes(stream.bytesReceived) }}</span>
              </div>
              <div>
                <span class="text-slate-500">↑ Sent:</span>
                <span class="ml-1 text-slate-300">{{ formatBytes(stream.bytesSent) }}</span>
              </div>
            </div>

            <!-- Preview Button -->
            <button
              @click="openPreview(stream.name)"
              :disabled="!stream.available"
              :class="[
                'w-full py-2 rounded-lg font-medium transition',
                stream.available 
                  ? 'bg-emerald-600 hover:bg-emerald-500 text-white' 
                  : 'bg-slate-700 text-slate-500 cursor-not-allowed'
              ]"
            >
              {{ stream.available ? '▶ Watch Preview' : 'Not Available' }}
            </button>

            <!-- Stream URLs Section -->
            <div class="space-y-2 pt-2 border-t border-slate-600">
              <h3 class="text-sm font-medium text-slate-300">Stream URLs</h3>
              
              <!-- WHEP (WebRTC) -->
              <div class="flex items-center gap-2">
                <span class="text-xs text-emerald-400 w-16">WHEP:</span>
                <code class="flex-1 text-xs bg-slate-700 px-2 py-1 rounded truncate">
                  {{ getWhepUrl(stream.name) }}
                </code>
                <button 
                  @click="copyToClipboard(getWhepUrl(stream.name), 'WHEP')"
                  class="px-2 py-1 text-xs bg-slate-600 hover:bg-slate-500 rounded"
                >
                  Copy
                </button>
              </div>

              <!-- RTSP -->
              <div class="flex items-center gap-2">
                <span class="text-xs text-blue-400 w-16">RTSP:</span>
                <code class="flex-1 text-xs bg-slate-700 px-2 py-1 rounded truncate">
                  {{ getRtspUrl(stream.name) }}
                </code>
                <button 
                  @click="copyToClipboard(getRtspUrl(stream.name), 'RTSP')"
                  class="px-2 py-1 text-xs bg-slate-600 hover:bg-slate-500 rounded"
                >
                  Copy
                </button>
              </div>

              <!-- SRT -->
              <div class="flex items-center gap-2">
                <span class="text-xs text-amber-400 w-16">SRT:</span>
                <code class="flex-1 text-xs bg-slate-700 px-2 py-1 rounded truncate">
                  {{ getSrtUrl(stream.name) }}
                </code>
                <button 
                  @click="copyToClipboard(getSrtUrl(stream.name), 'SRT')"
                  class="px-2 py-1 text-xs bg-slate-600 hover:bg-slate-500 rounded"
                >
                  Copy
                </button>
              </div>

              <!-- HLS (if available) -->
              <div class="flex items-center gap-2">
                <span class="text-xs text-purple-400 w-16">HLS:</span>
                <code class="flex-1 text-xs bg-slate-700 px-2 py-1 rounded truncate">
                  {{ getHlsUrl(stream.name) }}
                </code>
                <button 
                  @click="copyToClipboard(getHlsUrl(stream.name), 'HLS')"
                  class="px-2 py-1 text-xs bg-slate-600 hover:bg-slate-500 rounded"
                >
                  Copy
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Usage Instructions -->
      <div class="mt-8 bg-slate-800 rounded-xl border border-slate-700 p-6">
        <h2 class="text-xl font-semibold mb-4 text-emerald-400">How to Use These Streams</h2>
        
        <div class="grid md:grid-cols-2 gap-6">
          <!-- VLC / FFplay -->
          <div>
            <h3 class="font-medium text-slate-200 mb-2">VLC / FFplay</h3>
            <div class="space-y-2 text-sm">
              <p class="text-slate-400">For RTSP:</p>
              <code class="block bg-slate-700 p-2 rounded text-xs">
                vlc rtsp://app.itagenten.no:8554/cam0
              </code>
              <p class="text-slate-400 mt-2">For SRT:</p>
              <code class="block bg-slate-700 p-2 rounded text-xs">
                ffplay "srt://app.itagenten.no:8890?streamid=read:cam0"
              </code>
            </div>
          </div>

          <!-- OBS Studio -->
          <div>
            <h3 class="font-medium text-slate-200 mb-2">OBS Studio</h3>
            <div class="space-y-2 text-sm text-slate-400">
              <p>Add a "Media Source" with these settings:</p>
              <ul class="list-disc list-inside space-y-1 text-slate-300">
                <li>Uncheck "Local File"</li>
                <li>Input: Use the RTSP or SRT URL</li>
                <li>Network Buffering: 100-300ms</li>
                <li>Restart on activation: ✓</li>
              </ul>
            </div>
          </div>

          <!-- YouTube Streaming -->
          <div>
            <h3 class="font-medium text-slate-200 mb-2">Stream to YouTube</h3>
            <div class="space-y-2 text-sm text-slate-400">
              <p>MediaMTX can relay to YouTube via RTMP. Configure with:</p>
              <code class="block bg-slate-700 p-2 rounded text-xs break-all">
                runOnReady: ffmpeg -i rtsp://localhost:8554/mixer_program -c copy -f flv rtmp://a.rtmp.youtube.com/live2/YOUR-KEY
              </code>
            </div>
          </div>

          <!-- Browser Playback -->
          <div>
            <h3 class="font-medium text-slate-200 mb-2">Browser Playback</h3>
            <div class="space-y-2 text-sm text-slate-400">
              <p>Use WHEP URLs with compatible players:</p>
              <ul class="list-disc list-inside space-y-1 text-slate-300">
                <li>VDO.ninja with &whepshare parameter</li>
                <li>MediaMTX built-in WebRTC player</li>
                <li>Any WHEP-compatible player</li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      <!-- Program Output Section -->
      <div class="mt-8 bg-gradient-to-r from-emerald-900/30 to-slate-800 rounded-xl border border-emerald-700/50 p-6">
        <h2 class="text-xl font-semibold mb-4 text-emerald-400">Program Output (mixer_program)</h2>
        <p class="text-slate-300 mb-4">
          This stream contains the mixed output from VDO.ninja. When a camera is "sent to scene" in the mixer,
          it appears in this program output.
        </p>
        <div class="flex flex-wrap gap-3">
          <button
            @click="openPreview('mixer_program')"
            class="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 rounded-lg font-medium transition"
          >
            Watch Program Output
          </button>
          <button
            @click="openWebRtcPlayer('mixer_program')"
            class="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg font-medium transition"
          >
            MediaMTX WebRTC Player
          </button>
          <button
            @click="copyToClipboard(getRtspUrl('mixer_program'), 'Program RTSP')"
            class="px-4 py-2 bg-slate-600 hover:bg-slate-500 rounded-lg transition"
          >
            Copy RTSP URL
          </button>
          <button
            @click="copyToClipboard(getSrtUrl('mixer_program'), 'Program SRT')"
            class="px-4 py-2 bg-slate-600 hover:bg-slate-500 rounded-lg transition"
          >
            Copy SRT URL
          </button>
        </div>
      </div>
    </main>
  </div>
</template>

