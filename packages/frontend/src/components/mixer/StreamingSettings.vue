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

// Form fields for custom RTMP
const customRtmpUrl = ref('')
const customStreamKey = ref('')

// Computed
const destinations = computed(() => streamingStore.destinations)
const platforms = computed(() => STREAMING_PLATFORMS)
const programUrls = computed(() => streamingStore.programOutputUrls)

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
        <div class="relative bg-r58-bg-secondary border border-r58-bg-tertiary rounded-xl w-full max-w-2xl max-h-[80vh] overflow-hidden shadow-2xl">
          <!-- Header -->
          <div class="flex items-center justify-between px-6 py-4 border-b border-r58-bg-tertiary">
            <h2 class="text-xl font-semibold">Streaming Settings</h2>
            <button @click="closeSettings" class="text-r58-text-secondary hover:text-r58-text-primary text-2xl">
              ×
            </button>
          </div>

          <!-- Content -->
          <div class="p-6 overflow-y-auto max-h-[60vh]">
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
              <div v-if="showAddPlatform" class="mb-4 p-4 bg-r58-bg-tertiary rounded-lg">
                <p class="text-sm text-r58-text-secondary mb-3">Select a streaming platform:</p>
                <div class="grid grid-cols-2 gap-2">
                  <button
                    v-for="platform in platforms"
                    :key="platform.id"
                    @click="addPlatform(platform.id)"
                    class="flex items-center gap-2 p-3 bg-r58-bg-secondary hover:bg-r58-accent-primary/20 rounded-lg transition-colors text-left"
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
                  class="flex items-center gap-3 p-3 bg-r58-bg-tertiary rounded-lg"
                >
                  <!-- Enable toggle -->
                  <button
                    @click="toggleDestination(dest)"
                    :class="[
                      'w-10 h-6 rounded-full transition-colors relative',
                      dest.enabled ? 'bg-r58-accent-success' : 'bg-r58-bg-secondary'
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
                    <div class="text-xs text-r58-text-secondary">
                      {{ dest.streamKey ? '••••••••' + dest.streamKey.slice(-4) : 'No stream key' }}
                    </div>
                  </div>

                  <!-- Actions -->
                  <button
                    @click="editingDestination = { ...dest }"
                    class="text-r58-accent-primary hover:underline text-sm"
                  >
                    Edit
                  </button>
                  <button
                    @click="removeDestination(dest.id)"
                    class="text-r58-accent-danger hover:underline text-sm"
                  >
                    Remove
                  </button>
                </div>
              </div>

              <p v-else class="text-r58-text-secondary text-sm">
                No streaming destinations configured. Add a platform above.
              </p>
            </section>

            <!-- Edit Destination Form -->
            <section v-if="editingDestination" class="mb-8 p-4 bg-r58-bg-tertiary rounded-lg">
              <h3 class="text-lg font-medium mb-4">
                Edit {{ getPlatformName(editingDestination.platformId) }}
              </h3>

              <div class="space-y-4">
                <!-- Name -->
                <div>
                  <label class="block text-sm text-r58-text-secondary mb-1">Display Name</label>
                  <input
                    v-model="editingDestination.name"
                    type="text"
                    class="w-full px-3 py-2 bg-r58-bg-secondary border border-r58-bg-tertiary rounded-lg focus:border-r58-accent-primary focus:outline-none"
                  />
                </div>

                <!-- Stream Key -->
                <div>
                  <label class="block text-sm text-r58-text-secondary mb-1">Stream Key</label>
                  <input
                    v-model="editingDestination.streamKey"
                    type="password"
                    :placeholder="STREAMING_PLATFORMS.find(p => p.id === editingDestination!.platformId)?.streamKeyPlaceholder"
                    class="w-full px-3 py-2 bg-r58-bg-secondary border border-r58-bg-tertiary rounded-lg focus:border-r58-accent-primary focus:outline-none font-mono"
                  />
                  <p class="text-xs text-r58-text-secondary mt-1">
                    Your stream key is stored locally and never sent to our servers.
                  </p>
                </div>

                <!-- Custom RTMP URL (for custom platform) -->
                <div v-if="editingDestination.platformId === 'custom'">
                  <label class="block text-sm text-r58-text-secondary mb-1">RTMP URL</label>
                  <input
                    v-model="editingDestination.name"
                    type="text"
                    placeholder="rtmp://your-server.com/live/"
                    class="w-full px-3 py-2 bg-r58-bg-secondary border border-r58-bg-tertiary rounded-lg focus:border-r58-accent-primary focus:outline-none font-mono"
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
              <p class="text-sm text-r58-text-secondary mb-4">
                Use these URLs to consume the program feed from MediaMTX:
              </p>

              <div class="space-y-3">
                <!-- SRT Output -->
                <div class="p-3 bg-r58-bg-tertiary rounded-lg">
                  <div class="flex items-center justify-between mb-1">
                    <span class="font-medium">🔴 SRT Output</span>
                    <button
                      @click="copyToClipboard(programUrls.srt, 'SRT URL')"
                      class="text-xs text-r58-accent-primary hover:underline"
                    >
                      Copy
                    </button>
                  </div>
                  <code class="text-xs text-r58-text-secondary break-all">{{ programUrls.srt }}</code>
                  <p class="text-xs text-r58-text-secondary mt-1">
                    Low-latency, reliable transport. Ideal for remote production.
                  </p>
                </div>

                <!-- RTMP Output -->
                <div class="p-3 bg-r58-bg-tertiary rounded-lg">
                  <div class="flex items-center justify-between mb-1">
                    <span class="font-medium">📺 RTMP Output</span>
                    <button
                      @click="copyToClipboard(programUrls.rtmp, 'RTMP URL')"
                      class="text-xs text-r58-accent-primary hover:underline"
                    >
                      Copy
                    </button>
                  </div>
                  <code class="text-xs text-r58-text-secondary break-all">{{ programUrls.rtmp }}</code>
                </div>

                <!-- RTSP Output -->
                <div class="p-3 bg-r58-bg-tertiary rounded-lg">
                  <div class="flex items-center justify-between mb-1">
                    <span class="font-medium">🎬 RTSP Output</span>
                    <button
                      @click="copyToClipboard(programUrls.rtsp, 'RTSP URL')"
                      class="text-xs text-r58-accent-primary hover:underline"
                    >
                      Copy
                    </button>
                  </div>
                  <code class="text-xs text-r58-text-secondary break-all">{{ programUrls.rtsp }}</code>
                </div>

                <!-- HLS Output -->
                <div class="p-3 bg-r58-bg-tertiary rounded-lg">
                  <div class="flex items-center justify-between mb-1">
                    <span class="font-medium">🌐 HLS Output</span>
                    <button
                      @click="copyToClipboard(programUrls.hls, 'HLS URL')"
                      class="text-xs text-r58-accent-primary hover:underline"
                    >
                      Copy
                    </button>
                  </div>
                  <code class="text-xs text-r58-text-secondary break-all">{{ programUrls.hls }}</code>
                  <p class="text-xs text-r58-text-secondary mt-1">
                    Browser-compatible streaming. Higher latency.
                  </p>
                </div>

                <!-- WHEP Output -->
                <div class="p-3 bg-r58-bg-tertiary rounded-lg">
                  <div class="flex items-center justify-between mb-1">
                    <span class="font-medium">⚡ WebRTC (WHEP)</span>
                    <button
                      @click="copyToClipboard(programUrls.whep, 'WHEP URL')"
                      class="text-xs text-r58-accent-primary hover:underline"
                    >
                      Copy
                    </button>
                  </div>
                  <code class="text-xs text-r58-text-secondary break-all">{{ programUrls.whep }}</code>
                  <p class="text-xs text-r58-text-secondary mt-1">
                    Ultra-low latency WebRTC. Best for interactive use.
                  </p>
                </div>
              </div>
            </section>

            <!-- SRT Configuration -->
            <section>
              <h3 class="text-lg font-medium mb-4">SRT Configuration</h3>
              <div class="p-4 bg-r58-bg-tertiary rounded-lg">
                <div class="flex items-center gap-3 mb-4">
                  <button
                    @click="streamingStore.toggleSrtOutput(!streamingStore.srtOutput.enabled)"
                    :class="[
                      'w-10 h-6 rounded-full transition-colors relative',
                      streamingStore.srtOutput.enabled ? 'bg-r58-accent-success' : 'bg-r58-bg-secondary'
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

                <div class="text-sm text-r58-text-secondary">
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
          <div class="flex items-center justify-end gap-3 px-6 py-4 border-t border-r58-bg-tertiary">
            <button @click="closeSettings" class="btn">Close</button>
          </div>
        </div>
      </div>
    </Teleport>
</template>

