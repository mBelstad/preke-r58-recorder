<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRecorderStore } from '@/stores/recorder'
import { useKeyboardShortcuts } from '@/composables/useKeyboardShortcuts'
import { useDiskSpace } from '@/composables/useDiskSpace'
import { toast } from '@/composables/useToast'
import ConfirmDialog from '@/components/shared/ConfirmDialog.vue'

const recorderStore = useRecorderStore()
const { register } = useKeyboardShortcuts()
const { preflightCheck, status: diskStatus, canStartRecording, warningMessage } = useDiskSpace()

const stopConfirmDialog = ref<InstanceType<typeof ConfirmDialog> | null>(null)
const diskWarningDialog = ref<InstanceType<typeof ConfirmDialog> | null>(null)
const confirmButtonEnabled = ref(false)
const isPreflight = ref(false)

const isRecording = computed(() => recorderStore.status === 'recording')
const isStarting = computed(() => recorderStore.status === 'starting')
const isStopping = computed(() => recorderStore.status === 'stopping')
const duration = computed(() => recorderStore.formattedDuration)

// Button disabled state with reason
const isButtonDisabled = computed(() => isStarting.value || isStopping.value || isPreflight.value)
const buttonDisabledReason = computed(() => {
  if (isStarting.value) return 'Starting recording...'
  if (isStopping.value) return 'Stopping recording...'
  if (isPreflight.value) return 'Checking disk space...'
  if (!isRecording.value && !canStartRecording.value) return 'Insufficient disk space'
  return ''
})

// Register Space shortcut for recording toggle
let unregisterShortcut: (() => void) | null = null

onMounted(() => {
  unregisterShortcut = register({
    key: ' ',
    description: 'Toggle Recording',
    action: handleRecordAction,
    context: 'recorder',
    enabled: () => !isStarting.value && !isStopping.value,
  })
})

onUnmounted(() => {
  if (unregisterShortcut) {
    unregisterShortcut()
  }
})

async function handleRecordAction() {
  if (isRecording.value) {
    // Show confirmation dialog
    showStopConfirmation()
  } else {
    await handleStartRecording()
  }
}

async function handleStartRecording() {
  // Run preflight checks
  isPreflight.value = true
  
  try {
    const preflight = await preflightCheck()
    
    if (!preflight.ok) {
      // Critical - cannot proceed
      toast.error('Cannot start recording', preflight.message || 'Preflight check failed')
      return
    }
    
    if (preflight.message && diskStatus.value === 'warning') {
      // Warning - show dialog and let user decide
      toast.warning('Low disk space', preflight.message)
    }
    
    // Proceed with recording
    await startRecording()
  } finally {
    isPreflight.value = false
  }
}

async function startRecording() {
  try {
    await recorderStore.startRecording()
    toast.success('Recording started', `Session ID: ${recorderStore.sessionId}`)
  } catch (error: any) {
    toast.error('Failed to start recording', error.message || 'Unknown error', {
      label: 'Retry',
      onClick: handleStartRecording,
    })
  }
}

async function stopRecording() {
  try {
    const result = await recorderStore.stopRecording()
    toast.success('Recording stopped', `Duration: ${duration.value}`)
  } catch (error: any) {
    toast.error('Failed to stop recording', error.message || 'Unknown error')
  }
}

function showStopConfirmation() {
  confirmButtonEnabled.value = false
  stopConfirmDialog.value?.open()
  
  // Enable confirm button after 500ms delay (safeguard)
  setTimeout(() => {
    confirmButtonEnabled.value = true
  }, 500)
}

function handleConfirmStop() {
  if (confirmButtonEnabled.value) {
    stopRecording()
  }
}

async function toggleRecording() {
  if (isRecording.value) {
    showStopConfirmation()
  } else {
    await startRecording()
  }
}
</script>

<template>
  <div class="flex items-center gap-4">
    <!-- Duration display -->
    <div v-if="isRecording" class="font-mono text-xl text-r58-accent-danger">
      {{ duration }}
    </div>
    
    <!-- Record button -->
    <button
      @click="toggleRecording"
      :disabled="isButtonDisabled"
      class="flex items-center gap-2 px-6 py-2 rounded-lg font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed"
      :class="[
        isRecording 
          ? 'bg-r58-accent-danger hover:bg-red-600 text-white' 
          : 'bg-r58-accent-success hover:bg-green-600 text-white'
      ]"
      :title="buttonDisabledReason || (isRecording ? 'Stop Recording (Space)' : 'Start Recording (Space)')"
    >
      <span v-if="isStarting || isStopping || isPreflight" class="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"></span>
      <template v-else>
        <span v-if="isRecording" class="w-3 h-3 bg-white rounded-sm"></span>
        <span v-else class="w-3 h-3 bg-white rounded-full"></span>
      </template>
      <span>{{ isPreflight ? 'Checking...' : (isRecording ? 'Stop' : 'Start Recording') }}</span>
    </button>
    
    <!-- Keyboard hint -->
    <span class="text-xs text-r58-text-secondary hidden md:inline">
      Press <kbd class="px-1 py-0.5 bg-r58-bg-tertiary rounded text-xs font-mono">Space</kbd> to {{ isRecording ? 'stop' : 'start' }}
    </span>
  </div>
  
  <!-- Stop Confirmation Dialog -->
  <ConfirmDialog
    ref="stopConfirmDialog"
    title="Stop Recording?"
    :message="`You have been recording for ${duration}. This will finalize all files.`"
    confirm-text="Stop Recording"
    cancel-text="Keep Recording"
    :danger="true"
    @confirm="handleConfirmStop"
  />
</template>

