<script setup lang="ts">
/**
 * Streaming Settings Component
 * 
 * Provides UI for configuring streaming destinations including:
 * - Platform presets (YouTube, Twitch, Facebook, Restream)
 * - Custom RTMP destinations
 * - SRT output configuration
 */
import { ref, computed, watch } from 'vue'
import { useStreamingStore, STREAMING_PLATFORMS, type StreamingDestination } from '@/stores/streaming'
import { toast } from '@/composables/useToast'

const streamingStore = useStreamingStore()

const isOpen = ref(false)
const editingDestination = ref<StreamingDestination | null>(null)
const showAddPlatform = ref(false)

// Quick setup fields
const quickSetupPlatform = ref('youtube')
const quickSetupStreamKey = ref('')

// Form fields for custom RTMP
const customRtmpUrl = ref('')
const customStreamKey = ref('')

// Computed
const destinations = computed(() => streamingStore.destinations)
const platforms = computed(() => STREAMING_PLATFORMS)
const programUrls = computed(() => streamingStore.programOutputUrls)
const programOutputMode = computed(() => streamingStore.programOutputMode)

function openSettings() {
  isOpen.value = true
}

function closeSettings() {
  isOpen.value = false
  editingDestination.value = null
  showAddPlatform.value = false
}

function addPlatform(platformId: string) {
  const dest = streamingStore.addDestination(platformId)
  editingDestination.value = dest
  showAddPlatform.value = false
  streamingStore.saveDestinations()
}

function saveDestination() {
  if (editingDestination.value) {
    streamingStore.updateDestination(editingDestination.value.id, editingDestination.value)
    streamingStore.saveDestinations()
    editingDestination.value = null
    toast.success('Streaming destination saved')
  }
}

function removeDestination(id: string) {
  streamingStore.removeDestination(id)
  streamingStore.saveDestinations()
  toast.info('Destination removed')
}

function toggleDestination(dest: StreamingDestination) {
  streamingStore.updateDestination(dest.id, { enabled: !dest.enabled })
  streamingStore.saveDestinations()
}

function copyToClipboard(text: string, label: string) {
  navigator.clipboard.writeText(text)
  toast.success(`${label} copied to clipboard`)
}

function getPlatformIcon(platformId: string): string {
  const platform = STREAMING_PLATFORMS.find(p => p.id === platformId)
  return platform?.icon || '📡'
}

function getPlatformName(platformId: string): string {
  const platform = STREAMING_PLATFORMS.find(p => p.id === platformId)
  return platform?.name || 'Unknown'
}

// Quick setup functions
function getQuickSetupPlaceholder(): string {
  const platform = STREAMING_PLATFORMS.find(p => p.id === quickSetupPlatform.value)
  return platform?.streamKeyPlaceholder || 'Enter stream key'
}

function getStreamKeyHelpUrl(): string {
  switch (quickSetupPlatform.value) {
    case 'youtube': return 'https://support.google.com/youtube/answer/2907883'
    case 'twitch': return 'https://help.twitch.tv/s/article/twitch-stream-key-faq'
    case 'facebook': return 'https://www.facebook.com/help/587160588142067'
    case 'restream': return 'https://support.restream.io/en/'
    default: return '#'
  }
}

function quickAddAndSave() {
  if (!quickSetupStreamKey.value.trim()) {
    toast.error('Please enter your stream key')
    return
  }
  
  const dest = streamingStore.addDestination(quickSetupPlatform.value)
  streamingStore.updateDestination(dest.id, {
    streamKey: quickSetupStreamKey.value,
    enabled: true
  })
  streamingStore.saveDestinations()
  
  quickSetupStreamKey.value = ''
  toast.success(`${getPlatformName(quickSetupPlatform.value)} configured and enabled!`)
}

function setOutputMode(mode: 'alpha' | 'whipout') {
  streamingStore.setProgramOutputMode(mode)
  toast.success(`Program output mode set to ${mode === 'alpha' ? 'Alpha publish' : 'WHIP output'}`)
}

// Expose open method
defineExpose({ open: openSettings })
</script>

<template>
  <!-- Modal (no trigger button - opened via .open() from parent) -->
  <Teleport to="body">
      <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center">
        <!-- Backdrop -->
        <div class="absolute inset-0 bg-black/60" @click="closeSettings"></div>
        
        <!-- Modal content -->
        <div class="relative bg-preke-bg-elevated border border-preke-bg-surface rounded-xl w-full max-w-2xl max-h-[80vh] overflow-hidden shadow-2xl">
          <!-- Header -->
          <div class="flex items-center justify-between px-6 py-4 border-b border-preke-bg-surface">
            <h2 class="text-xl font-semibold">Streaming Settings</h2>
            <button @click="closeSettings" class="text-preke-text-dim hover:text-preke-text text-2xl">
              ×
            </button>
          </div>

          <!-- Content -->
          <div class="p-6 overflow-y-auto max-h-[60vh]">
            <!-- Quick Stream Key Entry (when no destinations) -->
            <section v-if="destinations.length === 0" class="mb-8 p-6 bg-gradient-to-br from-amber-600/20 to-red-600/20 rounded-xl border border-amber-500/30">
              <h3 class="text-xl font-semibold mb-2 flex items-center gap-2">
                🔴 Quick Setup: Stream to YouTube
              </h3>
              <p class="text-sm text-preke-text-dim mb-4">
                Get streaming in seconds! Just paste your stream key below.
              </p>
              
              <div class="flex gap-3 mb-4">
                <select
                  v-model="quickSetupPlatform"
                  class="px-4 py-3 bg-preke-bg-elevated border border-preke-bg-surface rounded-lg text-base"
                >
                  <option value="youtube">▶️ YouTube Live</option>
                  <option value="twitch">📺 Twitch</option>
                  <option value="facebook">📘 Facebook</option>
                  <option value="restream">🔄 Restream</option>
                </select>
                
                <input
                  v-model="quickSetupStreamKey"
                  type="password"
                  :placeholder="getQuickSetupPlaceholder()"
                  class="flex-1 px-4 py-3 bg-preke-bg-elevated border border-preke-bg-surface rounded-lg font-mono text-base focus:border-amber-500 focus:outline-none"
                />
                
                <button
                  @click="quickAddAndSave"
                  class="px-6 py-3 bg-red-600 hover:bg-red-500 text-white rounded-lg font-semibold transition-colors"
                >
                  Save & Enable
                </button>
              </div>
              
              <p class="text-xs text-preke-text-dim">
                🔒 Your stream key is stored locally on this device and never sent to any server.
                <a :href="getStreamKeyHelpUrl()" target="_blank" class="text-amber-400 hover:underline ml-2">
                  Where do I find my stream key? →
                </a>
              </p>
            </section>

            <!-- Destinations Section -->
            <section class="mb-8">
              <div class="flex items-center justify-between mb-4">
                <h3 class="text-lg font-medium">Streaming Destinations</h3>
                <button 
                  @click="showAddPlatform = !showAddPlatform" 
                  class="btn btn-sm btn-primary"
                >
                  + Add Platform
                </button>
              </div>

              <!-- Add Platform Dropdown -->
              <div v-if="showAddPlatform" class="mb-4 p-4 bg-preke-bg-surface rounded-lg">
                <p class="text-sm text-preke-text-dim mb-3">Select a streaming platform:</p>
                <div class="grid grid-cols-2 gap-2">
                  <button
                    v-for="platform in platforms"
                    :key="platform.id"
                    @click="addPlatform(platform.id)"
                    class="flex items-center gap-2 p-3 bg-preke-bg-elevated hover:bg-preke-gold/20 rounded-lg transition-colors text-left"
                  >
                    <span class="text-xl">{{ platform.icon }}</span>
                    <span>{{ platform.name }}</span>
                  </button>
                </div>
              </div>

              <!-- Destination List -->
              <div v-if="destinations.length > 0" class="space-y-3">
                <div
                  v-for="dest in destinations"
                  :key="dest.id"
                  class="flex items-center gap-3 p-3 bg-preke-bg-surface rounded-lg"
                >
                  <!-- Enable toggle -->
                  <button
                    @click="toggleDestination(dest)"
                    :class="[
                      'w-10 h-6 rounded-full transition-colors relative',
                      dest.enabled ? 'bg-preke-green' : 'bg-preke-bg-elevated'
                    ]"
                  >
                    <span
                      :class="[
                        'absolute top-1 w-4 h-4 rounded-full bg-white transition-transform',
                        dest.enabled ? 'left-5' : 'left-1'
                      ]"
                    ></span>
                  </button>

                  <!-- Platform icon and name -->
                  <span class="text-xl">{{ getPlatformIcon(dest.platformId) }}</span>
                  <div class="flex-1">
                    <div class="font-medium">{{ dest.name }}</div>
                    <div class="text-xs text-preke-text-dim">
                      {{ dest.streamKey ? '••••••••' + dest.streamKey.slice(-4) : 'No stream key' }}
                    </div>
                  </div>

                  <!-- Actions -->
                  <button
                    @click="editingDestination = { ...dest }"
                    class="text-preke-gold hover:underline text-sm"
                  >
                    Edit
                  </button>
                  <button
                    @click="removeDestination(dest.id)"
                    class="text-preke-red hover:underline text-sm"
                  >
                    Remove
                  </button>
                </div>
              </div>

              <p v-else class="text-preke-text-dim text-sm">
                No streaming destinations configured. Add a platform above.
              </p>
            </section>

            <!-- Edit Destination Form -->
            <section v-if="editingDestination" class="mb-8 p-4 bg-preke-bg-surface rounded-lg">
              <h3 class="text-lg font-medium mb-4">
                Edit {{ getPlatformName(editingDestination.platformId) }}
              </h3>

              <div class="space-y-4">
                <!-- Name -->
                <div>
                  <label class="block text-sm text-preke-text-dim mb-1">Display Name</label>
                  <input
                    v-model="editingDestination.name"
                    type="text"
                    class="w-full px-3 py-2 bg-preke-bg-elevated border border-preke-bg-surface rounded-lg focus:border-preke-gold focus:outline-none"
                  />
                </div>

                <!-- Stream Key -->
                <div>
                  <label class="block text-sm text-preke-text-dim mb-1">Stream Key</label>
                  <input
                    v-model="editingDestination.streamKey"
                    type="password"
                    :placeholder="STREAMING_PLATFORMS.find(p => p.id === editingDestination!.platformId)?.streamKeyPlaceholder"
                    class="w-full px-3 py-2 bg-preke-bg-elevated border border-preke-bg-surface rounded-lg focus:border-preke-gold focus:outline-none font-mono"
                  />
                  <p class="text-xs text-preke-text-dim mt-1">
                    Your stream key is stored locally and never sent to our servers.
                  </p>
                </div>

                <!-- Custom RTMP URL (for custom platform) -->
                <div v-if="editingDestination.platformId === 'custom'">
                  <label class="block text-sm text-preke-text-dim mb-1">RTMP URL</label>
                  <input
                    v-model="editingDestination.name"
                    type="text"
                    placeholder="rtmp://your-server.com/live/"
                    class="w-full px-3 py-2 bg-preke-bg-elevated border border-preke-bg-surface rounded-lg focus:border-preke-gold focus:outline-none font-mono"
                  />
                </div>

                <div class="flex gap-2">
                  <button @click="saveDestination" class="btn btn-primary">
                    Save
                  </button>
                  <button @click="editingDestination = null" class="btn">
                    Cancel
                  </button>
                </div>
              </div>
            </section>

            <!-- Output URLs Section -->
            <section class="mb-8">
              <h3 class="text-lg font-medium mb-4">Program Output URLs</h3>
              <p class="text-sm text-preke-text-dim mb-4">
                Use these URLs to consume the program feed from MediaMTX:
              </p>

              <div class="space-y-3">
                <!-- SRT Output -->
                <div class="p-3 bg-preke-bg-surface rounded-lg">
                  <div class="flex items-center justify-between mb-1">
                    <span class="font-medium">🔴 SRT Output</span>
                    <button
                      @click="copyToClipboard(programUrls.srt, 'SRT URL')"
                      class="text-xs text-preke-gold hover:underline"
                    >
                      Copy
                    </button>
                  </div>
                  <code class="text-xs text-preke-text-dim break-all">{{ programUrls.srt }}</code>
                  <p class="text-xs text-preke-text-dim mt-1">
                    Low-latency, reliable transport. Ideal for remote production.
                  </p>
                </div>

                <!-- RTMP Output -->
                <div class="p-3 bg-preke-bg-surface rounded-lg">
                  <div class="flex items-center justify-between mb-1">
                    <span class="font-medium">📺 RTMP Output</span>
                    <button
                      @click="copyToClipboard(programUrls.rtmp, 'RTMP URL')"
                      class="text-xs text-preke-gold hover:underline"
                    >
                      Copy
                    </button>
                  </div>
                  <code class="text-xs text-preke-text-dim break-all">{{ programUrls.rtmp }}</code>
                </div>

                <!-- RTSP Output -->
                <div class="p-3 bg-preke-bg-surface rounded-lg">
                  <div class="flex items-center justify-between mb-1">
                    <span class="font-medium">🎬 RTSP Output</span>
                    <button
                      @click="copyToClipboard(programUrls.rtsp, 'RTSP URL')"
                      class="text-xs text-preke-gold hover:underline"
                    >
                      Copy
                    </button>
                  </div>
                  <code class="text-xs text-preke-text-dim break-all">{{ programUrls.rtsp }}</code>
                </div>

                <!-- HLS Output -->
                <div class="p-3 bg-preke-bg-surface rounded-lg">
                  <div class="flex items-center justify-between mb-1">
                    <span class="font-medium">🌐 HLS Output</span>
                    <button
                      @click="copyToClipboard(programUrls.hls, 'HLS URL')"
                      class="text-xs text-preke-gold hover:underline"
                    >
                      Copy
                    </button>
                  </div>
                  <code class="text-xs text-preke-text-dim break-all">{{ programUrls.hls }}</code>
                  <p class="text-xs text-preke-text-dim mt-1">
                    Browser-compatible streaming. Higher latency.
                  </p>
                </div>

                <!-- WHEP Output -->
                <div class="p-3 bg-preke-bg-surface rounded-lg">
                  <div class="flex items-center justify-between mb-1">
                    <span class="font-medium">⚡ WebRTC (WHEP)</span>
                    <button
                      @click="copyToClipboard(programUrls.whep, 'WHEP URL')"
                      class="text-xs text-preke-gold hover:underline"
                    >
                      Copy
                    </button>
                  </div>
                  <code class="text-xs text-preke-text-dim break-all">{{ programUrls.whep }}</code>
                  <p class="text-xs text-preke-text-dim mt-1">
                    Ultra-low latency WebRTC. Best for interactive use.
                  </p>
                </div>
              </div>
            </section>

            <!-- Program Output Mode -->
            <section class="mb-8">
              <h3 class="text-lg font-medium mb-4">Program Output Mode</h3>
              <div class="p-4 bg-preke-bg-surface rounded-lg space-y-3">
                <label class="flex items-center gap-3 text-sm">
                  <input
                    type="radio"
                    name="program-output-mode"
                    value="alpha"
                    :checked="programOutputMode === 'alpha'"
                    @change="setOutputMode('alpha')"
                  />
                  <span>Alpha publish mode (`&publish&mediamtx=`)</span>
                </label>
                <label class="flex items-center gap-3 text-sm">
                  <input
                    type="radio"
                    name="program-output-mode"
                    value="whipout"
                    :checked="programOutputMode === 'whipout'"
                    @change="setOutputMode('whipout')"
                  />
                  <span>WHIP output mode (`&whipout=`)</span>
                </label>
                <p class="text-xs text-preke-text-dim">
                  Alpha publish mode matches the newest VDO.Ninja alpha workflow and is recommended for MediaMTX.
                </p>
              </div>
            </section>

            <!-- SRT Configuration -->
            <section>
              <h3 class="text-lg font-medium mb-4">SRT Configuration</h3>
              <div class="p-4 bg-preke-bg-surface rounded-lg">
                <div class="flex items-center gap-3 mb-4">
                  <button
                    @click="streamingStore.toggleSrtOutput(!streamingStore.srtOutput.enabled)"
                    :class="[
                      'w-10 h-6 rounded-full transition-colors relative',
                      streamingStore.srtOutput.enabled ? 'bg-preke-green' : 'bg-preke-bg-elevated'
                    ]"
                  >
                    <span
                      :class="[
                        'absolute top-1 w-4 h-4 rounded-full bg-white transition-transform',
                        streamingStore.srtOutput.enabled ? 'left-5' : 'left-1'
                      ]"
                    ></span>
                  </button>
                  <span>Enable SRT Output</span>
                </div>

                <div class="text-sm text-preke-text-dim">
                  <p class="mb-2">SRT (Secure Reliable Transport) provides:</p>
                  <ul class="list-disc list-inside space-y-1">
                    <li>Low latency (typically 1-2 seconds)</li>
                    <li>Error correction for unreliable networks</li>
                    <li>AES encryption support</li>
                    <li>Compatible with OBS, vMix, and professional equipment</li>
                  </ul>
                </div>
              </div>
            </section>
          </div>

          <!-- Footer -->
          <div class="flex items-center justify-end gap-3 px-6 py-4 border-t border-preke-bg-surface">
            <button @click="closeSettings" class="btn">Close</button>
          </div>
        </div>
      </div>
    </Teleport>
</template>

