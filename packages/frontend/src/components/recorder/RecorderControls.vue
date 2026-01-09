<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRecorderStore } from '@/stores/recorder'
import { useKeyboardShortcuts } from '@/composables/useKeyboardShortcuts'
import { useDiskSpace } from '@/composables/useDiskSpace'
import { useAudioFeedback } from '@/composables/useAudioFeedback'
import { toast } from '@/composables/useToast'
import ConfirmDialog from '@/components/shared/ConfirmDialog.vue'
import SessionNameDialog from '@/components/recorder/SessionNameDialog.vue'

const recorderStore = useRecorderStore()
const { register } = useKeyboardShortcuts()
const { preflightCheck, status: diskStatus, canStartRecording } = useDiskSpace()
const { playRecordStart, playRecordStop, playError, playWarning, vibrate } = useAudioFeedback()

const stopConfirmDialog = ref<InstanceType<typeof ConfirmDialog> | null>(null)
const confirmButtonEnabled = ref(false)
const isPreflight = ref(false)

// Session naming state
const showSessionNameDialog = ref(false)
const requireSessionName = ref(false) // Toggle via settings
const pendingSessionName = ref<string | undefined>(undefined)

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

async function handleStartRecording(sessionName?: string) {
  // Run preflight checks
  isPreflight.value = true
  
  try {
    const preflight = await preflightCheck()
    
    if (!preflight.ok) {
      // Critical - cannot proceed
      playError()
      vibrate(200)
      toast.error('Cannot start recording', preflight.message || 'Preflight check failed')
      return
    }
    
    if (preflight.message && diskStatus.value === 'warning') {
      // Warning - show dialog and let user decide
      playWarning()
      toast.warning('Low disk space', preflight.message)
    }
    
    // Show session name dialog if required and not already provided
    if (requireSessionName.value && !sessionName) {
      pendingSessionName.value = undefined
      showSessionNameDialog.value = true
      return // Wait for dialog response
    }
    
    // Proceed with recording
    await startRecording(sessionName || pendingSessionName.value)
  } finally {
    isPreflight.value = false
  }
}

async function startRecording(sessionName?: string) {
  try {
    await recorderStore.startRecording(sessionName)
    const displayName = sessionName || recorderStore.sessionId
    
    // Audio/haptic feedback
    playRecordStart()
    vibrate([50, 30, 50]) // Short double vibration
    
    toast.success('Recording started', `Session: ${displayName}`)
  } catch (error: any) {
    playError()
    vibrate(200) // Long vibration for error
    
    toast.error('Failed to start recording', error.message || 'Unknown error', {
      label: 'Retry',
      onClick: () => handleStartRecording(sessionName),
    })
  }
}

// Session name dialog handlers
function handleSessionNameConfirm(name: string) {
  showSessionNameDialog.value = false
  pendingSessionName.value = name
  handleStartRecording(name)
}

function handleSessionNameSkip() {
  showSessionNameDialog.value = false
  pendingSessionName.value = undefined
  handleStartRecording()
}

function handleSessionNameCancel() {
  showSessionNameDialog.value = false
  isPreflight.value = false
}

async function stopRecording() {
  try {
    await recorderStore.stopRecording()
    
    // Audio/haptic feedback
    playRecordStop()
    vibrate(100) // Single vibration for stop
    
    toast.success('Recording stopped')
  } catch (error: any) {
    playError()
    vibrate(200)
    
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
  <div class="recorder-controls">
    <!-- Duration display -->
    <div v-if="isRecording" class="recorder-controls__duration">
      {{ duration }}
    </div>
    
    <!-- Record button -->
    <button
      @click="toggleRecording"
      :disabled="isButtonDisabled"
      class="recorder-controls__btn"
      :class="isRecording ? 'recorder-controls__btn--stop' : 'recorder-controls__btn--start'"
      :title="buttonDisabledReason || (isRecording ? 'Stop Recording (Space)' : 'Start Recording (Space)')"
    >
      <span v-if="isStarting || isStopping || isPreflight" class="recorder-controls__spinner"></span>
      <template v-else>
        <span v-if="isRecording" class="recorder-controls__icon recorder-controls__icon--stop"></span>
        <span v-else class="recorder-controls__icon recorder-controls__icon--record"></span>
      </template>
      <span>{{ isPreflight ? 'Checking...' : (isRecording ? 'Stop' : 'Start Recording') }}</span>
    </button>
    
    <!-- Keyboard hint -->
    <span class="recorder-controls__hint">
      Press <kbd>Space</kbd> to {{ isRecording ? 'stop' : 'start' }}
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
  
  <!-- Session Name Dialog -->
  <SessionNameDialog
    :open="showSessionNameDialog"
    @confirm="handleSessionNameConfirm"
    @skip="handleSessionNameSkip"
    @cancel="handleSessionNameCancel"
  />
</template>

<style scoped>
.recorder-controls {
  display: flex;
  align-items: center;
  gap: 16px;
}

.recorder-controls__duration {
  font-family: var(--preke-font-mono, monospace);
  font-size: 18px;
  font-weight: 600;
  color: var(--preke-red);
}

.recorder-controls__btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 20px;
  font-size: 14px;
  font-weight: 600;
  border-radius: 8px;
  border: none;
  cursor: pointer;
  transition: all 0.2s ease;
}

.recorder-controls__btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.recorder-controls__btn--start {
  background: var(--preke-green);
  color: white;
}

.recorder-controls__btn--start:hover:not(:disabled) {
  filter: brightness(1.1);
  transform: translateY(-1px);
}

.recorder-controls__btn--stop {
  background: var(--preke-red);
  color: white;
}

.recorder-controls__btn--stop:hover:not(:disabled) {
  filter: brightness(1.1);
  transform: translateY(-1px);
}

.recorder-controls__spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.recorder-controls__icon {
  width: 12px;
  height: 12px;
}

.recorder-controls__icon--record {
  background: white;
  border-radius: 50%;
}

.recorder-controls__icon--stop {
  background: white;
  border-radius: 2px;
}

.recorder-controls__hint {
  font-size: 12px;
  color: var(--preke-text-muted);
  display: none;
}

@media (min-width: 768px) {
  .recorder-controls__hint {
    display: inline;
  }
}

.recorder-controls__hint kbd {
  padding: 2px 6px;
  font-family: var(--preke-font-mono, monospace);
  font-size: 11px;
  background: var(--preke-bg);
  border: 1px solid var(--preke-border);
  border-radius: 4px;
  color: var(--preke-text);
}
</style>

