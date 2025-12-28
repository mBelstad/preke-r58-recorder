/**
 * Recording Navigation Guard
 * 
 * Prevents accidental navigation away while recording is active.
 * Shows confirmation dialog before leaving.
 */
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import { useRecorderStore } from '@/stores/recorder'

const isGuardActive = ref(false)
const showLeaveConfirmation = ref(false)
let pendingNavigation: (() => void) | null = null

export function useRecordingGuard() {
  const recorderStore = useRecorderStore()

  // Watch recording status to toggle guard
  watch(
    () => recorderStore.status,
    (status) => {
      isGuardActive.value = status === 'recording'
    },
    { immediate: true }
  )

  // Browser beforeunload handler
  function handleBeforeUnload(event: BeforeUnloadEvent) {
    if (isGuardActive.value) {
      event.preventDefault()
      event.returnValue = 'Recording in progress. Are you sure you want to leave?'
      return event.returnValue
    }
  }

  onMounted(() => {
    window.addEventListener('beforeunload', handleBeforeUnload)
  })

  onUnmounted(() => {
    window.removeEventListener('beforeunload', handleBeforeUnload)
  })

  // Vue Router guard
  onBeforeRouteLeave((_to, _from, next) => {
    if (isGuardActive.value) {
      // Store the pending navigation
      pendingNavigation = () => next()
      showLeaveConfirmation.value = true
      next(false) // Cancel navigation for now
    } else {
      next()
    }
  })

  function confirmLeave() {
    showLeaveConfirmation.value = false
    isGuardActive.value = false // Temporarily disable guard
    
    // Stop recording first
    recorderStore.stopRecording().finally(() => {
      if (pendingNavigation) {
        pendingNavigation()
        pendingNavigation = null
      }
    })
  }

  function cancelLeave() {
    showLeaveConfirmation.value = false
    pendingNavigation = null
  }

  return {
    isGuardActive,
    showLeaveConfirmation,
    confirmLeave,
    cancelLeave,
  }
}

