<script setup lang="ts">
/**
 * VdoNinjaFrame - Wrapper component for VDO.ninja embeds with app chrome
 * 
 * Features:
 * - Consistent app toolbar above iframe
 * - Loading state with branded spinner
 * - Connection status indicator
 * - Slot-based customization for toolbar content
 * - Responsive sizing with safe aspect handling
 */
import { ref, computed } from 'vue'
import VdoNinjaEmbed from './VdoNinjaEmbed.vue'
import type { embedProfiles } from '@/lib/vdoninja'

const props = defineProps<{
  profile: keyof typeof embedProfiles
  title?: string
  showToolbar?: boolean
  sources?: string[]
  room?: string
  password?: string
}>()

const embedRef = ref<InstanceType<typeof VdoNinjaEmbed> | null>(null)

// Expose embed methods to parent
const isReady = computed(() => embedRef.value?.isReady ?? false)
const isRecording = computed(() => embedRef.value?.isRecording ?? false)
const connectionState = computed(() => embedRef.value?.connectionState ?? 'disconnected')
const lastError = computed(() => embedRef.value?.lastError ?? null)
const sources = computed(() => embedRef.value?.sources ?? new Map())

// Status color mapping
const statusColorClass = computed(() => {
  switch (connectionState.value) {
    case 'connected':
      return 'bg-preke-green'
    case 'connecting':
      return 'bg-preke-amber animate-pulse'
    case 'disconnected':
      return 'bg-preke-red'
    default:
      return 'bg-preke-text-dim'
  }
})

const statusLabel = computed(() => {
  switch (connectionState.value) {
    case 'connected':
      return 'Connected'
    case 'connecting':
      return 'Connecting...'
    case 'disconnected':
      return 'Disconnected'
    default:
      return 'Unknown'
  }
})

// Expose embed controls
defineExpose({
  isReady,
  isRecording,
  connectionState,
  lastError,
  sources,
  
  // Pass through embed methods
  addToScene: (...args: Parameters<typeof embedRef.value.addToScene>) => embedRef.value?.addToScene(...args),
  removeFromScene: (...args: Parameters<typeof embedRef.value.removeFromScene>) => embedRef.value?.removeFromScene(...args),
  setMute: (...args: Parameters<typeof embedRef.value.setMute>) => embedRef.value?.setMute(...args),
  toggleMute: (...args: Parameters<typeof embedRef.value.toggleMute>) => embedRef.value?.toggleMute(...args),
  setVolume: (...args: Parameters<typeof embedRef.value.setVolume>) => embedRef.value?.setVolume(...args),
  startRecording: () => embedRef.value?.startRecording(),
  stopRecording: () => embedRef.value?.stopRecording(),
  kickGuest: (...args: Parameters<typeof embedRef.value.kickGuest>) => embedRef.value?.kickGuest(...args),
  setLayout: (...args: Parameters<typeof embedRef.value.setLayout>) => embedRef.value?.setLayout(...args),
  sendCommand: (...args: Parameters<typeof embedRef.value.sendCommand>) => embedRef.value?.sendCommand(...args),
})
</script>

<template>
  <div class="vdo-frame flex flex-col h-full bg-preke-bg-base">
    <!-- Toolbar (App Chrome) -->
    <div 
      v-if="showToolbar !== false"
      class="vdo-frame__toolbar flex items-center justify-between px-4 py-2 bg-preke-bg-elevated border-b border-preke-bg-surface"
    >
      <!-- Left: Title and status -->
      <div class="flex items-center gap-3">
        <h3 v-if="title" class="text-sm font-semibold text-preke-text">
          {{ title }}
        </h3>
        
        <!-- Connection status indicator -->
        <div class="flex items-center gap-2 text-xs text-preke-text-dim">
          <span 
            :class="['w-2 h-2 rounded-full transition-colors', statusColorClass]"
          ></span>
          <span>{{ statusLabel }}</span>
        </div>

        <!-- Source count -->
        <div 
          v-if="isReady && sources.size > 0"
          class="flex items-center gap-1.5 px-2 py-1 bg-preke-bg-surface rounded text-xs"
        >
          <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
          </svg>
          <span>{{ sources.size }} {{ sources.size === 1 ? 'source' : 'sources' }}</span>
        </div>
      </div>
      
      <!-- Right: Toolbar slot for custom controls -->
      <div class="flex items-center gap-2">
        <slot name="toolbar" :embed="embedRef" />
      </div>
    </div>
    
    <!-- VDO.ninja Embed (fills remaining space) -->
    <div class="vdo-frame__content flex-1 relative min-h-0">
      <VdoNinjaEmbed
        ref="embedRef"
        :profile="profile"
        :sources="sources"
        :room="room"
        :password="password"
        class="w-full h-full"
      />
      
      <!-- Error overlay -->
      <div 
        v-if="lastError"
        class="absolute bottom-4 left-4 right-4 bg-preke-red/90 text-white px-4 py-3 rounded-lg shadow-lg flex items-start gap-3"
      >
        <svg class="w-5 h-5 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <div class="flex-1">
          <div class="font-semibold mb-1">Connection Error</div>
          <div class="text-sm opacity-90">{{ lastError }}</div>
        </div>
      </div>
    </div>
    
    <!-- Bottom slot (for additional controls if needed) -->
    <div v-if="$slots.bottom" class="vdo-frame__bottom border-t border-preke-bg-surface">
      <slot name="bottom" :embed="embedRef" />
    </div>
  </div>
</template>

<style scoped>
.vdo-frame {
  /* Ensure frame fills container */
  width: 100%;
  height: 100%;
}

.vdo-frame__content {
  /* Ensure iframe container maintains aspect */
  position: relative;
  overflow: hidden;
}
</style>

