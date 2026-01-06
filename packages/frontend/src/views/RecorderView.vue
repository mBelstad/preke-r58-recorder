<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRecorderStore } from '@/stores/recorder'
import { useCapabilitiesStore } from '@/stores/capabilities'
import { useRecordingGuard } from '@/composables/useRecordingGuard'
import { buildApiUrl, hasDeviceConfigured } from '@/lib/api'
import { toast } from '@/composables/useToast'
import RecorderControls from '@/components/recorder/RecorderControls.vue'
import RecordingHealth from '@/components/recorder/RecordingHealth.vue'
import InputGrid from '@/components/recorder/InputGrid.vue'
import SessionInfo from '@/components/recorder/SessionInfoV2.vue'
import ConfirmDialog from '@/components/shared/ConfirmDialog.vue'
import ModeLoadingScreen from '@/components/shared/ModeLoadingScreen.vue'

const recorderStore = useRecorderStore()
const capabilitiesStore = useCapabilitiesStore()
const { showLeaveConfirmation, confirmLeave, cancelLeave } = useRecordingGuard()

const isRecording = computed(() => recorderStore.status === 'recording')
const duration = computed(() => recorderStore.formattedDuration)

// Loading state
const isLoading = ref(true)
const dataLoaded = ref(false)
const videosReady = ref(false)

// Content is ready when BOTH data is loaded AND videos are displaying
const contentReady = computed(() => dataLoaded.value && videosReady.value)

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

// Called by InputGrid when all videos have their first frame
function handleAllVideosReady() {
  console.log('[Recorder] All videos ready!')
  videosReady.value = true
}

// Fetch real input status on mount - parallelized for speed
onMounted(async () => {
  const startTime = performance.now()
  
  // Fetch data (mode, inputs, status) in parallel
  // Video connections start automatically via InputPreview components
  await Promise.all([
    ensureRecorderMode(),
    recorderStore.fetchInputs(),
    recorderStore.fetchStatus()
  ])
  
  const camerasWithSignal = recorderStore.inputs.filter(i => i.hasSignal).length
  console.log(`[Recorder] Data loaded: ${recorderStore.inputs.length} inputs, ${camerasWithSignal} with signal (${Math.round(performance.now() - startTime)}ms)`)
  
  // Mark data as loaded - videos are loading in parallel via InputPreview
  dataLoaded.value = true
  
  // If no cameras with signal, mark videos as ready immediately
  if (camerasWithSignal === 0) {
    videosReady.value = true
  }
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
  
  <!-- Content fades in when loading complete -->
  <Transition name="content-fade">
    <div v-show="!isLoading" class="h-full flex flex-col">
    <!-- Header - Riverside-inspired -->
    <header class="preke-header">
      <div class="flex items-center gap-4">
        <div class="flex items-center gap-2">
          <span 
            class="w-3 h-3 rounded-full"
            :class="isRecording ? 'bg-preke-red animate-recording' : 'bg-preke-border'"
          ></span>
          <span class="text-lg font-semibold text-preke-text">Recorder</span>
        </div>
        <span v-if="isRecording" class="preke-badge preke-badge-live">
          REC
        </span>
        
        <!-- Recording health indicator -->
        <RecordingHealth />
      </div>
      
      <RecorderControls />
    </header>
    
    <!-- Main content - fills available space without scroll -->
    <div class="flex-1 flex min-h-0 overflow-hidden">
      <!-- Input grid - fills all available space -->
      <div class="flex-1 min-h-0 min-w-0 p-3 overflow-hidden">
        <InputGrid @all-videos-ready="handleAllVideosReady" />
      </div>
      
      <!-- Sidebar -->
      <aside class="w-72 flex-shrink-0 border-l border-preke-border bg-preke-bg-elevated p-4 overflow-y-auto">
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
  </Transition>
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

/* Content fade in animation */
.content-fade-enter-active {
  transition: opacity 0.4s ease-out, transform 0.4s ease-out;
}

.content-fade-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.content-fade-enter-to {
  opacity: 1;
  transform: translateY(0);
}
</style>

