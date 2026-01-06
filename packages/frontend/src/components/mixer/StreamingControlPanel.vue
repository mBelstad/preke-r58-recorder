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

const props = withDefaults(defineProps<{
  roomName?: string
  cameraCount?: number
}>(), {
  roomName: '',
  cameraCount: 0
})

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
    case 'live': return 'control-bar__dot--live'
    case 'connecting': return 'control-bar__dot--connecting'
    case 'error': return 'control-bar__dot--error'
    default: return 'control-bar__dot--idle'
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
    <div class="control-bar">
      <!-- Room Info (left) -->
      <div v-if="props.roomName" class="control-bar__room">
        <span class="control-bar__room-label">Room</span>
        <span class="control-bar__room-name">{{ props.roomName }}</span>
        <span v-if="props.cameraCount > 0" class="control-bar__camera-count">
          {{ props.cameraCount }} cam{{ props.cameraCount !== 1 ? 's' : '' }}
        </span>
      </div>
      
      <!-- Divider -->
      <div v-if="props.roomName" class="control-bar__divider"></div>
      
      <!-- Status Indicator -->
      <div class="control-bar__status">
        <span :class="['control-bar__dot', getStatusColor()]"></span>
        <span class="control-bar__status-text">{{ getStatusText() }}</span>
      </div>
      
      <!-- Divider -->
      <div class="control-bar__divider"></div>
      
      <!-- Start/Stop Streaming Button -->
      <button
        @click="toggleStreaming"
        :class="[
          'control-bar__btn',
          isStreaming ? 'control-bar__btn--stop' : 'control-bar__btn--start'
        ]"
      >
        {{ isStreaming ? '⏹ Stop' : '▶ Start Streaming' }}
      </button>
      
      <!-- Quick Setup Button (shows when no destinations) -->
      <button
        v-if="!hasDestinations"
        @click="toggleQuickSetup"
        :class="[
          'control-bar__btn control-bar__btn--dashed',
          showQuickSetup ? 'control-bar__btn--active' : ''
        ]"
      >
        🔑 Add Stream Key
      </button>
      
      <!-- Watch Program Button -->
      <button
        @click="watchProgram"
        class="control-bar__btn control-bar__btn--secondary"
        title="Open program output in new window"
      >
        👁 Watch
      </button>
      
      <!-- Streaming Settings Button -->
      <button
        @click="openStreamingSettings"
        class="control-bar__btn control-bar__btn--secondary"
        title="Configure streaming destinations"
      >
        ⚙️
      </button>
      
      <!-- Active Destinations Indicator -->
      <div v-if="hasEnabledDestinations" class="control-bar__destinations">
        <span class="control-bar__destinations-label">To:</span>
        <div class="control-bar__destinations-list">
          <span
            v-for="dest in streamingStore.enabledDestinations"
            :key="dest.id"
            class="control-bar__destination"
            :title="dest.name"
          >
            {{ dest.platformId === 'youtube' ? '▶️' : dest.platformId === 'twitch' ? '📺' : '🔴' }}
          </span>
        </div>
      </div>
    </div>
    
    <!-- Quick Setup Panel (slides down) -->
    <transition name="slide">
      <div v-if="showQuickSetup" class="quick-setup">
        <div class="quick-setup__form">
          <!-- Platform Selector -->
          <div class="quick-setup__platform">
            <span class="quick-setup__platform-icon">{{ getQuickPlatformIcon() }}</span>
            <select v-model="quickPlatform" class="quick-setup__select">
              <option value="youtube">YouTube</option>
              <option value="twitch">Twitch</option>
              <option value="facebook">Facebook</option>
              <option value="restream">Restream</option>
            </select>
          </div>
          
          <!-- Stream Key Input -->
          <div class="quick-setup__input-wrap">
            <input
              v-model="quickStreamKey"
              type="password"
              :placeholder="getQuickPlatformPlaceholder()"
              class="quick-setup__input"
              @keyup.enter="quickSetupAndStream"
            />
          </div>
          
          <!-- Go Live Button -->
          <button @click="quickSetupAndStream" class="quick-setup__go-live">
            🔴 Go Live
          </button>
          
          <!-- Cancel -->
          <button @click="showQuickSetup = false" class="quick-setup__cancel">✕</button>
        </div>
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
/* Control Bar */
.control-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 16px;
  background: var(--preke-surface);
  border-bottom: 1px solid var(--preke-surface-border);
}

.control-bar__room {
  display: flex;
  align-items: center;
  gap: 8px;
}

.control-bar__room-label {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  color: var(--preke-text-subtle);
}

.control-bar__room-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--preke-text);
  padding: 4px 10px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 6px;
}

.control-bar__camera-count {
  font-size: 11px;
  color: var(--preke-green);
}

.control-bar__divider {
  width: 1px;
  height: 24px;
  background: var(--preke-border);
}

.control-bar__status {
  display: flex;
  align-items: center;
  gap: 8px;
}

.control-bar__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.control-bar__dot--live {
  background: var(--preke-red);
  box-shadow: 0 0 8px var(--preke-red);
  animation: pulse 1.5s ease-in-out infinite;
}

.control-bar__dot--connecting {
  background: var(--preke-amber);
  animation: pulse 1s ease-in-out infinite;
}

.control-bar__dot--error {
  background: var(--preke-red);
}

.control-bar__dot--idle {
  background: var(--preke-text-subtle);
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(0.85); }
}

.control-bar__status-text {
  font-size: 12px;
  font-weight: 600;
  color: var(--preke-text-muted);
}

/* Buttons */
.control-bar__btn {
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 500;
  border-radius: 6px;
  border: none;
  cursor: pointer;
  transition: all 0.15s ease;
}

.control-bar__btn--start {
  background: var(--preke-green);
  color: white;
}

.control-bar__btn--start:hover {
  filter: brightness(1.1);
}

.control-bar__btn--stop {
  background: var(--preke-red);
  color: white;
}

.control-bar__btn--stop:hover {
  filter: brightness(1.1);
}

.control-bar__btn--secondary {
  background: rgba(255, 255, 255, 0.05);
  color: var(--preke-text-muted);
  border: 1px solid var(--preke-border);
}

.control-bar__btn--secondary:hover {
  background: rgba(255, 255, 255, 0.1);
  color: var(--preke-text);
}

.control-bar__btn--dashed {
  background: transparent;
  color: var(--preke-text-muted);
  border: 2px dashed var(--preke-border);
}

.control-bar__btn--dashed:hover,
.control-bar__btn--active {
  border-color: var(--preke-gold);
  color: var(--preke-gold);
}

.control-bar__destinations {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-left: auto;
}

.control-bar__destinations-label {
  font-size: 10px;
  color: var(--preke-text-subtle);
}

.control-bar__destinations-list {
  display: flex;
  gap: 4px;
}

.control-bar__destination {
  padding: 2px 6px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 4px;
  font-size: 12px;
}

/* Quick Setup */
.quick-setup {
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.02);
  border-bottom: 1px solid var(--preke-surface-border);
}

.quick-setup__form {
  display: flex;
  align-items: center;
  gap: 12px;
}

.quick-setup__platform {
  display: flex;
  align-items: center;
  gap: 8px;
}

.quick-setup__platform-icon {
  font-size: 20px;
}

.quick-setup__select {
  padding: 8px 12px;
  background: var(--preke-bg);
  border: 1px solid var(--preke-border);
  border-radius: 6px;
  font-size: 12px;
  color: var(--preke-text);
}

.quick-setup__select:focus {
  outline: none;
  border-color: var(--preke-gold);
}

.quick-setup__input-wrap {
  flex: 1;
}

.quick-setup__input {
  width: 100%;
  padding: 8px 12px;
  background: var(--preke-bg);
  border: 1px solid var(--preke-border);
  border-radius: 6px;
  font-size: 12px;
  font-family: monospace;
  color: var(--preke-text);
}

.quick-setup__input:focus {
  outline: none;
  border-color: var(--preke-gold);
}

.quick-setup__go-live {
  padding: 8px 16px;
  background: var(--preke-red);
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}

.quick-setup__go-live:hover {
  filter: brightness(1.1);
}

.quick-setup__cancel {
  padding: 8px;
  background: transparent;
  border: none;
  color: var(--preke-text-muted);
  cursor: pointer;
  font-size: 14px;
}

.quick-setup__cancel:hover {
  color: var(--preke-text);
}

/* Slide transition */
.slide-enter-active,
.slide-leave-active {
  transition: all 0.2s ease-out;
  max-height: 80px;
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

