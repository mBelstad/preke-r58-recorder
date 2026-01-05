<script setup lang="ts">
/**
 * StreamingControlPanel - Controls for program output streaming
 * 
 * Features:
 * - Start/Stop streaming to MediaMTX (WHIP output)
 * - Watch program locally in popup window
 * - Configure streaming destinations (YouTube, Twitch, etc.)
 * - Status indicator showing connection state
 * - Quick setup for easy stream key entry
 */
import { ref, computed } from 'vue'
import { useMixerStore } from '@/stores/mixer'
import { useStreamingStore, STREAMING_PLATFORMS } from '@/stores/streaming'
import { openProgramPopup } from '@/lib/vdoninja'
import { toast } from '@/composables/useToast'
import StreamingSettings from './StreamingSettings.vue'
import ProgramOutput from './ProgramOutput.vue'

const mixerStore = useMixerStore()
const streamingStore = useStreamingStore()

const streamingSettingsRef = ref<InstanceType<typeof StreamingSettings> | null>(null)
const programOutputRef = ref<InstanceType<typeof ProgramOutput> | null>(null)

// Quick setup state
const showQuickSetup = ref(false)
const quickPlatform = ref('youtube')
const quickStreamKey = ref('')

// Local state
const isStreaming = computed(() => mixerStore.isLive)
const hasDestinations = computed(() => streamingStore.destinations.length > 0)
const hasEnabledDestinations = computed(() => streamingStore.enabledDestinations.length > 0)

const streamingStatus = computed(() => {
  if (!isStreaming.value) return 'idle'
  // Get status from ProgramOutput component if available
  return 'live'
})

// Actions
function toggleStreaming() {
  if (isStreaming.value) {
    stopStreaming()
  } else {
    startStreaming()
  }
}

async function startStreaming() {
  // Toggle mixer live state which triggers ProgramOutput to start WHIP push
  mixerStore.setLive(true)
  
  // If there are enabled destinations, configure RTMP relay via MediaMTX runOnReady hook
  if (streamingStore.enabledDestinations.length > 0) {
    const result = await streamingStore.startRtmpRelay()
    if (result.success) {
      toast.success(result.message)
    } else {
      toast.error(`RTMP relay failed: ${result.message}`)
    }
  } else {
    toast.success('Streaming started (no RTMP destinations configured)')
  }
}

async function stopStreaming() {
  mixerStore.setLive(false)
  
  // Stop RTMP relay (removes MediaMTX runOnReady hook)
  if (streamingStore.enabledDestinations.length > 0) {
    const result = await streamingStore.stopRtmpRelay()
    if (!result.success) {
      toast.warning(`Note: ${result.message}`)
    }
  }
  
  toast.info('Streaming stopped')
}

function watchProgram() {
  const popup = openProgramPopup(1)
  if (!popup) {
    toast.error('Popup blocked - please allow popups for this site')
  } else {
    toast.success('Program window opened')
  }
}

function openStreamingSettings() {
  streamingSettingsRef.value?.open()
}

// Quick setup functions
function toggleQuickSetup() {
  showQuickSetup.value = !showQuickSetup.value
}

function quickSetupAndStream() {
  if (!quickStreamKey.value.trim()) {
    toast.error('Please enter your stream key')
    return
  }
  
  // Add the destination
  const platform = STREAMING_PLATFORMS.find(p => p.id === quickPlatform.value)
  if (!platform) return
  
  // Check if we already have this platform
  const existing = streamingStore.destinations.find(d => d.platformId === quickPlatform.value)
  if (existing) {
    // Update existing
    streamingStore.updateDestination(existing.id, {
      streamKey: quickStreamKey.value,
      enabled: true
    })
  } else {
    // Add new
    const dest = streamingStore.addDestination(quickPlatform.value)
    streamingStore.updateDestination(dest.id, {
      streamKey: quickStreamKey.value,
      enabled: true
    })
  }
  
  streamingStore.saveDestinations()
  showQuickSetup.value = false
  quickStreamKey.value = ''
  
  // Start streaming automatically
  startStreaming()
}

function getQuickPlatformPlaceholder(): string {
  const platform = STREAMING_PLATFORMS.find(p => p.id === quickPlatform.value)
  return platform?.streamKeyPlaceholder || 'Enter your stream key'
}

function getQuickPlatformIcon(): string {
  const platform = STREAMING_PLATFORMS.find(p => p.id === quickPlatform.value)
  return platform?.icon || '📡'
}

// Status color helper
function getStatusColor(): string {
  switch (streamingStatus.value) {
    case 'live': return 'bg-r58-accent-danger'
    case 'connecting': return 'bg-r58-accent-warning animate-pulse'
    case 'error': return 'bg-r58-accent-danger'
    default: return 'bg-r58-text-secondary'
  }
}

function getStatusText(): string {
  switch (streamingStatus.value) {
    case 'live': return 'LIVE'
    case 'connecting': return 'Connecting...'
    case 'error': return 'Error'
    default: return 'Offline'
  }
}
</script>

<template>
  <div class="streaming-control-panel">
    <!-- Main Control Bar -->
    <div class="flex items-center gap-3 px-4 py-2 bg-r58-bg-secondary border-b border-r58-bg-tertiary">
      <!-- Status Indicator -->
      <div class="flex items-center gap-2">
        <span :class="['w-2 h-2 rounded-full', getStatusColor()]"></span>
        <span class="text-sm font-medium">{{ getStatusText() }}</span>
      </div>
      
      <!-- Divider -->
      <div class="h-6 w-px bg-r58-bg-tertiary"></div>
      
      <!-- Start/Stop Streaming Button -->
      <button
        @click="toggleStreaming"
        :class="[
          'px-4 py-2 rounded-lg font-medium text-sm transition-all',
          isStreaming 
            ? 'bg-r58-accent-danger hover:bg-red-600 text-white' 
            : 'bg-r58-accent-success hover:bg-green-600 text-white'
        ]"
      >
        {{ isStreaming ? '⏹ Stop Streaming' : '▶ Start Streaming' }}
      </button>
      
      <!-- Quick Setup Button (shows when no destinations) -->
      <button
        v-if="!hasDestinations"
        @click="toggleQuickSetup"
        :class="[
          'px-4 py-2 rounded-lg font-medium text-sm transition-all border-2 border-dashed',
          showQuickSetup 
            ? 'bg-amber-600/20 border-amber-500 text-amber-400' 
            : 'bg-transparent border-r58-bg-tertiary hover:border-amber-500 text-r58-text-secondary hover:text-amber-400'
        ]"
      >
        🔑 Add Stream Key
      </button>
      
      <!-- Watch Program Button -->
      <button
        @click="watchProgram"
        class="px-4 py-2 rounded-lg font-medium text-sm bg-r58-bg-tertiary hover:bg-r58-accent-primary text-r58-text-primary transition-colors"
        title="Open program output in new window"
      >
        👁 Watch Program
      </button>
      
      <!-- Streaming Settings Button -->
      <button
        @click="openStreamingSettings"
        class="px-4 py-2 rounded-lg font-medium text-sm bg-r58-bg-tertiary hover:bg-r58-accent-primary text-r58-text-primary transition-colors"
        title="Configure streaming destinations"
      >
        ⚙️ Settings
      </button>
      
      <!-- Active Destinations Indicator -->
      <div v-if="hasEnabledDestinations" class="flex items-center gap-2 ml-auto">
        <span class="text-xs text-r58-text-secondary">
          Streaming to:
        </span>
        <div class="flex items-center gap-1">
          <span
            v-for="dest in streamingStore.enabledDestinations"
            :key="dest.id"
            class="px-2 py-1 bg-r58-bg-tertiary rounded text-xs"
            :title="dest.name"
          >
            {{ dest.platformId === 'youtube' ? '▶️' : dest.platformId === 'twitch' ? '📺' : '🔴' }}
            {{ dest.name }}
          </span>
        </div>
      </div>
    </div>
    
    <!-- Quick Setup Panel (slides down) -->
    <transition name="slide">
      <div v-if="showQuickSetup" class="px-4 py-3 bg-r58-bg-tertiary/50 border-b border-r58-bg-tertiary">
        <div class="flex items-center gap-4 max-w-4xl">
          <!-- Platform Selector -->
          <div class="flex items-center gap-2">
            <span class="text-2xl">{{ getQuickPlatformIcon() }}</span>
            <select
              v-model="quickPlatform"
              class="px-3 py-2 bg-r58-bg-secondary border border-r58-bg-tertiary rounded-lg text-sm focus:border-amber-500 focus:outline-none"
            >
              <option value="youtube">YouTube Live</option>
              <option value="twitch">Twitch</option>
              <option value="facebook">Facebook Live</option>
              <option value="restream">Restream</option>
            </select>
          </div>
          
          <!-- Stream Key Input -->
          <div class="flex-1 relative">
            <input
              v-model="quickStreamKey"
              type="password"
              :placeholder="getQuickPlatformPlaceholder()"
              class="w-full px-4 py-2 bg-r58-bg-secondary border border-r58-bg-tertiary rounded-lg text-sm font-mono focus:border-amber-500 focus:outline-none"
              @keyup.enter="quickSetupAndStream"
            />
            <span class="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-r58-text-secondary">
              🔒 Stored locally
            </span>
          </div>
          
          <!-- Go Live Button -->
          <button
            @click="quickSetupAndStream"
            class="px-6 py-2 bg-red-600 hover:bg-red-500 text-white rounded-lg font-medium text-sm transition-colors flex items-center gap-2"
          >
            🔴 Go Live
          </button>
          
          <!-- Cancel -->
          <button
            @click="showQuickSetup = false"
            class="px-3 py-2 text-r58-text-secondary hover:text-r58-text-primary"
          >
            ✕
          </button>
        </div>
        
        <!-- Help text -->
        <p class="text-xs text-r58-text-secondary mt-2">
          Paste your stream key from 
          <a v-if="quickPlatform === 'youtube'" href="https://studio.youtube.com" target="_blank" class="text-amber-400 hover:underline">YouTube Studio → Go Live → Stream Settings</a>
          <a v-else-if="quickPlatform === 'twitch'" href="https://dashboard.twitch.tv/settings/stream" target="_blank" class="text-amber-400 hover:underline">Twitch Dashboard → Stream Key</a>
          <a v-else-if="quickPlatform === 'facebook'" href="https://facebook.com/live/producer" target="_blank" class="text-amber-400 hover:underline">Facebook Live Producer</a>
          <a v-else-if="quickPlatform === 'restream'" href="https://app.restream.io" target="_blank" class="text-amber-400 hover:underline">Restream Dashboard</a>
          <span v-else>your streaming platform</span>
        </p>
      </div>
    </transition>
    
    <!-- Hidden ProgramOutput component (handles WHIP push) -->
    <div class="hidden">
      <ProgramOutput ref="programOutputRef" />
    </div>
    
    <!-- Streaming Settings Modal -->
    <StreamingSettings ref="streamingSettingsRef" />
  </div>
</template>

<style scoped>
/* Slide transition for quick setup panel */
.slide-enter-active,
.slide-leave-active {
  transition: all 0.2s ease-out;
  max-height: 100px;
  overflow: hidden;
}

.slide-enter-from,
.slide-leave-to {
  max-height: 0;
  opacity: 0;
  padding-top: 0;
  padding-bottom: 0;
}
</style>

