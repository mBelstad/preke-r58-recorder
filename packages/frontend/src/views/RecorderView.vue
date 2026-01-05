<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRecorderStore } from '@/stores/recorder'
import { useCapabilitiesStore } from '@/stores/capabilities'
import { useRecordingGuard } from '@/composables/useRecordingGuard'
import { buildApiUrl, hasDeviceConfigured } from '@/lib/api'
import { toast } from '@/composables/useToast'
import { preloadConnections } from '@/lib/whepConnectionManager'
import RecorderControls from '@/components/recorder/RecorderControls.vue'
import RecordingHealth from '@/components/recorder/RecordingHealth.vue'
import InputGrid from '@/components/recorder/InputGrid.vue'
import SessionInfo from '@/components/recorder/SessionInfo.vue'
import ConfirmDialog from '@/components/shared/ConfirmDialog.vue'
import ModeLoadingScreen from '@/components/shared/ModeLoadingScreen.vue'

const recorderStore = useRecorderStore()
const capabilitiesStore = useCapabilitiesStore()
const { showLeaveConfirmation, confirmLeave, cancelLeave } = useRecordingGuard()

const isRecording = computed(() => recorderStore.status === 'recording')
const duration = computed(() => recorderStore.formattedDuration)

// Loading state
const isLoading = ref(true)
const contentReady = ref(false)

function handleLoadingReady() {
  isLoading.value = false
}

// Auto-switch to recorder mode if not already in it
async function ensureRecorderMode() {
  if (!hasDeviceConfigured()) return
  
  // Fetch current capabilities to get mode
  await capabilitiesStore.fetchCapabilities()
  
  const currentMode = capabilitiesStore.capabilities?.current_mode
  if (currentMode && currentMode !== 'recorder') {
    console.log('[Recorder] Not in recorder mode, switching...')
    try {
      const response = await fetch(buildApiUrl('/api/mode/recorder'), { method: 'POST' })
      if (response.ok) {
        await capabilitiesStore.fetchCapabilities()
        toast.success('Switched to Recorder mode')
      }
    } catch (e) {
      console.warn('[Recorder] Failed to switch mode:', e)
    }
  }
}

// Preload WHEP connections for cameras with signal
async function preloadVideoStreams() {
  // Get cameras with signal from the store (after fetchInputs completes)
  const camerasWithSignal = recorderStore.inputs
    .filter(i => i.hasSignal)
    .map(i => i.id)
  
  if (camerasWithSignal.length === 0) {
    console.log('[Recorder] No cameras with signal to preload')
    return
  }
  
  console.log(`[Recorder] Preloading ${camerasWithSignal.length} video streams...`)
  await preloadConnections(camerasWithSignal)
}

// Fetch real input status on mount - parallelized for speed
onMounted(async () => {
  const startTime = performance.now()
  
  // Phase 1: Fetch data (mode, inputs, status) in parallel
  await Promise.all([
    ensureRecorderMode(),
    recorderStore.fetchInputs(),
    recorderStore.fetchStatus()
  ])
  console.log(`[Recorder] Loaded ${recorderStore.inputs.length} inputs, ${recorderStore.inputs.filter(i => i.hasSignal).length} with signal`)
  
  // Phase 2: Preload video streams (while loading screen still visible)
  await preloadVideoStreams()
  
  console.log(`[Recorder] Total load time: ${Math.round(performance.now() - startTime)}ms`)
  
  // Mark content as ready - loading screen will dismiss
  contentReady.value = true
})

// Ref for leave confirmation dialog
const leaveDialog = ref<InstanceType<typeof ConfirmDialog> | null>(null)

// Watch for leave confirmation request
watch(showLeaveConfirmation, (show) => {
  if (show) {
    leaveDialog.value?.open()
  } else {
    leaveDialog.value?.close()
  }
})
</script>

<template>
  <!-- Loading Screen -->
  <Transition name="fade">
    <ModeLoadingScreen
      v-if="isLoading"
      mode="recorder"
      :content-ready="contentReady"
      :min-time="1500"
      :max-time="5000"
      @ready="handleLoadingReady"
    />
  </Transition>
  
  <div class="h-full flex flex-col">
    <!-- Header -->
    <header class="flex items-center justify-between px-6 py-4 border-b border-r58-bg-tertiary bg-r58-bg-secondary">
      <div class="flex items-center gap-4">
        <div class="flex items-center gap-2">
          <span 
            class="w-3 h-3 rounded-full"
            :class="isRecording ? 'bg-r58-accent-danger animate-recording' : 'bg-r58-bg-tertiary'"
          ></span>
          <span class="text-xl font-semibold">Recorder</span>
        </div>
        <span v-if="isRecording" class="badge badge-danger">RECORDING</span>
        
        <!-- Recording health indicator -->
        <RecordingHealth />
      </div>
      
      <RecorderControls />
    </header>
    
    <!-- Main content -->
    <div class="flex-1 flex overflow-hidden">
      <!-- Input grid -->
      <div class="flex-1 p-4">
        <InputGrid />
      </div>
      
      <!-- Sidebar -->
      <aside class="w-80 border-l border-r58-bg-tertiary bg-r58-bg-secondary p-4 overflow-y-auto">
        <SessionInfo />
      </aside>
    </div>
    
    <!-- Leave Confirmation Dialog -->
    <ConfirmDialog
      ref="leaveDialog"
      title="Recording in Progress"
      :message="`You are currently recording (${duration}). Leaving will stop the recording and save all files.`"
      confirm-text="Leave and Stop Recording"
      cancel-text="Stay"
      :danger="true"
      @confirm="confirmLeave"
      @cancel="cancelLeave"
    />
  </div>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>

