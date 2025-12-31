<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRecorderStore } from '@/stores/recorder'
import { useRecordingGuard } from '@/composables/useRecordingGuard'
import RecorderControls from '@/components/recorder/RecorderControls.vue'
import RecordingHealth from '@/components/recorder/RecordingHealth.vue'
import InputGrid from '@/components/recorder/InputGrid.vue'
import SessionInfo from '@/components/recorder/SessionInfo.vue'
import ConfirmDialog from '@/components/shared/ConfirmDialog.vue'
import ModeLoadingScreen from '@/components/shared/ModeLoadingScreen.vue'

const recorderStore = useRecorderStore()
const { showLeaveConfirmation, confirmLeave, cancelLeave } = useRecordingGuard()

const isRecording = computed(() => recorderStore.status === 'recording')
const duration = computed(() => recorderStore.formattedDuration)

// Loading state
const isLoading = ref(true)
const contentReady = ref(false)

function handleLoadingReady() {
  isLoading.value = false
}

// Fetch real input status on mount
onMounted(async () => {
  await recorderStore.fetchInputs()
  await recorderStore.fetchStatus()
  // Mark content as ready once data is fetched
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
      :max-time="6000"
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

