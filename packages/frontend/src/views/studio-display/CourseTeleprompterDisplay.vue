<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRecorderStore } from '@/stores/recorder'
import InputPreview from '@/components/shared/InputPreview.vue'
import StudioDisplayShell from '@/components/shared/StudioDisplayShell.vue'

const props = defineProps<{
  status: any
  isPreview?: boolean
}>()

const recorderStore = useRecorderStore()
const currentTipIndex = ref(0)
const scrollPosition = ref(0)
const isPaused = ref(false)
let tipInterval: number | null = null
let scrollAnimationId: number | null = null
let pollInterval: number | null = null

const courseTeleprompterTips = [
  {
    icon: '🎯',
    title: 'Look Directly at the Camera Lens',
    description: 'Maintain eye contact with the lens for a natural connection'
  },
  {
    icon: '🗣️',
    title: 'Speak at a Steady, Natural Pace',
    description: 'Take your time and speak clearly'
  },
  {
    icon: '⏸️',
    title: 'Use the Pause Function',
    description: 'Press Space to pause and collect your thoughts'
  },
  {
    icon: '⚡',
    title: 'Adjust Scroll Speed',
    description: 'Use +/- keys to match your reading pace'
  }
]

onMounted(async () => {
  tipInterval = window.setInterval(() => {
    currentTipIndex.value = (currentTipIndex.value + 1) % courseTeleprompterTips.length
  }, 5000)
  
  window.addEventListener('keydown', handleKeyDown)
  
  if (isRecording.value) {
    startScroll()
  }
  
  await recorderStore.fetchInputs()
  pollInterval = window.setInterval(() => {
    recorderStore.fetchInputs()
  }, 2000)
})

onUnmounted(() => {
  if (tipInterval) clearInterval(tipInterval)
  if (pollInterval) clearInterval(pollInterval)
  if (scrollAnimationId) cancelAnimationFrame(scrollAnimationId)
  window.removeEventListener('keydown', handleKeyDown)
})

const isRecording = computed(() => props.status?.recording_active || false)

const recordingDuration = computed(() => {
  if (!props.status?.recording_duration_ms) return '00:00:00'
  const seconds = Math.floor(props.status.recording_duration_ms / 1000)
  const hours = Math.floor(seconds / 3600)
  const mins = Math.floor((seconds % 3600) / 60)
  const secs = seconds % 60
  return `${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
})

const timeRemaining = computed(() => {
  if (!props.status?.booking) return null
  const now = new Date()
  const endTime = new Date(`${props.status.booking.date} ${props.status.booking.slot_end}`)
  const diff = endTime.getTime() - now.getTime()
  if (diff <= 0) return 'Time expired'
  const mins = Math.floor(diff / 60000)
  return `${mins} min left`
})

const currentTip = computed(() => courseTeleprompterTips[currentTipIndex.value])

const scrollSpeed = computed(() => {
  const speed = props.status?.teleprompter_scroll_speed || 50
  return (speed / 100) * 4.5 + 0.5
})

const scriptText = computed(() => {
  if (props.isPreview) {
    return 'This is a preview of the course teleprompter display.\n\nWhen a script is loaded, it will appear here and scroll automatically during recording.\n\nUse the arrow keys to scroll manually, or press Space to pause.'
  }
  return props.status?.teleprompter_script || 'No script loaded. Please add a script in the booking settings.'
})

// Get cameras for display
const presenterCamera = computed(() => {
  return recorderStore.inputs.find(i => i.hasSignal) || null
})

const secondCamera = computed(() => {
  const cameras = recorderStore.inputs.filter(i => i.hasSignal)
  return cameras.length > 1 ? cameras[1] : null
})

function handleKeyDown(e: KeyboardEvent) {
  if (!isRecording.value) return
  
  switch (e.key) {
    case ' ':
      e.preventDefault()
      isPaused.value = !isPaused.value
      break
    case 'ArrowUp':
      e.preventDefault()
      scrollPosition.value = Math.max(0, scrollPosition.value - 50)
      break
    case 'ArrowDown':
      e.preventDefault()
      scrollPosition.value += 50
      break
  }
}

function startScroll() {
  function scroll() {
    if (!isPaused.value) {
      scrollPosition.value += scrollSpeed.value
    }
    scrollAnimationId = requestAnimationFrame(scroll)
  }
  scroll()
}
</script>

<template>
  <div class="course-teleprompter-display__mirror-wrapper">
    <StudioDisplayShell
      title="Course Session"
      subtitle="Teleprompter mode"
      accent="blue"
      :show-footer="isRecording"
      main-class="course-teleprompter-display__main"
    >
      <template #header-right>
        <div class="course-teleprompter-display__timing">
          <span class="course-teleprompter-display__timer">{{ recordingDuration }}</span>
          <span v-if="timeRemaining" class="course-teleprompter-display__remaining">{{ timeRemaining }}</span>
        </div>
      </template>

      <div class="course-teleprompter-display__layout">
        <section class="course-teleprompter-display__script glass-card">
          <div
            class="course-teleprompter-display__text"
            :style="{ transform: `translateY(-${scrollPosition}px)` }"
          >
            <div class="course-teleprompter-display__text-content">
              {{ scriptText }}
            </div>
          </div>
        </section>

        <aside class="course-teleprompter-display__side">
          <div v-if="presenterCamera" class="course-teleprompter-display__card glass-panel">
            <div class="course-teleprompter-display__label">Presenter</div>
            <div class="course-teleprompter-display__camera-frame">
              <div class="course-teleprompter-display__camera-label">{{ presenterCamera.label }}</div>
              <InputPreview :input-id="presenterCamera.id" :is-preview="isPreview" />
            </div>
          </div>

          <div v-if="secondCamera" class="course-teleprompter-display__card glass-panel">
            <div class="course-teleprompter-display__label">Second Camera</div>
            <div class="course-teleprompter-display__camera-frame">
              <div class="course-teleprompter-display__camera-label">{{ secondCamera.label }}</div>
              <InputPreview :input-id="secondCamera.id" :is-preview="isPreview" />
            </div>
          </div>

          <div class="course-teleprompter-display__card glass-panel">
            <div class="course-teleprompter-display__label">Tip</div>
            <div class="course-teleprompter-display__tip-title">{{ currentTip.title }}</div>
            <div class="course-teleprompter-display__tip-text">{{ currentTip.description }}</div>
          </div>

          <div class="course-teleprompter-display__card glass-panel">
            <div class="course-teleprompter-display__label">Status</div>
            <div class="course-teleprompter-display__status" :class="{ 'course-teleprompter-display__status--live': isRecording }">
              <span class="course-teleprompter-display__status-dot"></span>
              {{ isRecording ? 'Recording' : 'Ready for recording' }}
            </div>
            <div class="course-teleprompter-display__meta">
              Scroll speed: {{ props.status.teleprompter_scroll_speed || 50 }}%
            </div>
          </div>
        </aside>
      </div>

      <template #footer>
        <div class="course-teleprompter-display__footer-left">
          <span class="course-teleprompter-display__rec-badge">
            <span class="course-teleprompter-display__rec-dot"></span>
            REC
          </span>
          <span class="course-teleprompter-display__footer-text">
            Space = {{ isPaused ? 'Resume' : 'Pause' }} • ↑↓ = Scroll
          </span>
        </div>
        <div v-if="isPaused" class="course-teleprompter-display__footer-right">
          ⏸ Paused
        </div>
      </template>
    </StudioDisplayShell>
  </div>
</template>

<style scoped>
@import '@/styles/design-system-v2.css';

/* Full page mirroring for teleprompter */
.course-teleprompter-display__mirror-wrapper {
  width: 100vw;
  height: 100vh;
  transform: scaleX(-1);
}

.course-teleprompter-display__mirror-wrapper > * {
  transform: scaleX(-1);
}

.course-teleprompter-display__main {
  align-items: stretch;
}

.course-teleprompter-display__timing {
  display: flex;
  flex-direction: column;
  text-align: right;
}

.course-teleprompter-display__timer {
  font-size: 2.25rem;
  font-family: var(--preke-font-mono);
  font-weight: 700;
}

.course-teleprompter-display__remaining {
  font-size: 1rem;
  color: var(--preke-text-muted);
}

.course-teleprompter-display__layout {
  width: 100%;
  height: 100%;
  display: grid;
  grid-template-columns: minmax(0, 1.6fr) minmax(0, 0.7fr);
  gap: 1.75rem;
  min-height: 0;
  align-items: start;
}

.course-teleprompter-display__script {
  position: relative;
  overflow: hidden;
  padding: 2rem 0;
  background: #000;
}

.course-teleprompter-display__text {
  width: 100%;
  height: 100%;
  text-align: center;
  font-size: clamp(44px, 6vw, 68px);
  line-height: 1.5;
  font-weight: 500;
  transition: transform 0.05s linear;
  will-change: transform;
  color: #fff;
}

.course-teleprompter-display__text-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 4rem;
  white-space: pre-wrap;
}

.course-teleprompter-display__side {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  max-height: 100%;
  overflow-y: auto;
}

.course-teleprompter-display__card {
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.course-teleprompter-display__label {
  text-transform: uppercase;
  letter-spacing: 0.2em;
  font-size: 0.75rem;
  color: var(--preke-text-muted);
}

.course-teleprompter-display__camera-frame {
  position: relative;
  border-radius: var(--preke-radius-md);
  overflow: hidden;
  aspect-ratio: 16/9;
  background: rgba(0, 0, 0, 0.6);
  min-height: 0;
}

.course-teleprompter-display__camera-label {
  position: absolute;
  top: 0.5rem;
  left: 0.5rem;
  background: rgba(0, 0, 0, 0.8);
  color: #fff;
  padding: 0.25rem 0.5rem;
  border-radius: var(--preke-radius-sm);
  font-size: 0.7rem;
  z-index: 2;
}

.course-teleprompter-display__tip-title {
  font-size: 1.5rem;
  font-weight: 700;
}

.course-teleprompter-display__tip-text {
  color: var(--preke-text-dim);
  font-size: 1.05rem;
}

.course-teleprompter-display__status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  color: var(--preke-text-dim);
}

.course-teleprompter-display__status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--preke-text-subtle);
}

.course-teleprompter-display__status--live .course-teleprompter-display__status-dot {
  background: var(--preke-red);
  box-shadow: 0 0 12px rgba(212, 90, 90, 0.4);
}

.course-teleprompter-display__meta {
  color: var(--preke-text-muted);
  font-size: 0.95rem;
}

.course-teleprompter-display__footer-left {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.course-teleprompter-display__footer-text {
  color: var(--preke-text-muted);
  font-size: 0.95rem;
}

.course-teleprompter-display__footer-right {
  color: var(--preke-gold);
  font-weight: 600;
}

.course-teleprompter-display__rec-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.35rem 0.75rem;
  border-radius: var(--preke-radius-md);
  background: rgba(220, 38, 38, 0.2);
  color: var(--preke-red);
  font-weight: 700;
}

.course-teleprompter-display__rec-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--preke-red);
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.3); }
}

@media (max-width: 1200px) {
  .course-teleprompter-display__layout {
    grid-template-columns: 1fr;
  }

  .course-teleprompter-display__text-content {
    padding: 0 2rem;
  }
}
</style>
