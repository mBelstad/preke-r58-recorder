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
let tipInterval: number | null = null
let pollInterval: number | null = null

const courseTips = [
  {
    icon: '🎓',
    title: 'Keep your slides simple',
    description: 'Big text and clear visuals work best on camera'
  },
  {
    icon: '🧭',
    title: 'Guide the viewer',
    description: 'Use short sections and clear takeaways'
  },
  {
    icon: '🎤',
    title: 'Audio is everything',
    description: 'Speak close to the microphone for clarity'
  },
  {
    icon: '⏱️',
    title: 'Keep the pace steady',
    description: 'Pause between points to keep it easy to follow'
  }
]

onMounted(async () => {
  tipInterval = window.setInterval(() => {
    currentTipIndex.value = (currentTipIndex.value + 1) % courseTips.length
  }, 6000)

  await recorderStore.fetchInputs()
  pollInterval = window.setInterval(() => {
    recorderStore.fetchInputs()
  }, 2000)
})

onUnmounted(() => {
  if (tipInterval) clearInterval(tipInterval)
  if (pollInterval) clearInterval(pollInterval)
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

const currentGraphic = computed(() => {
  if (!props.status?.project?.graphics) return null
  return props.status.project.graphics[props.status.current_slide_index]
})

const currentTip = computed(() => courseTips[currentTipIndex.value])

const previewCamera = computed(() => {
  return recorderStore.inputs.find(i => i.hasSignal) || null
})
</script>

<template>
  <StudioDisplayShell
    title="Course Session"
    subtitle="Presentation + recording"
    accent="blue"
    :show-footer="true"
    main-class="course-display__main"
  >
    <template #header-right>
      <div class="course-display__timing">
        <div class="course-display__timer">{{ recordingDuration }}</div>
        <div v-if="timeRemaining" class="course-display__remaining">{{ timeRemaining }}</div>
      </div>
    </template>

    <div class="course-display__layout">
      <section class="course-display__slides glass-card">
        <div v-if="currentGraphic" class="course-display__slide">
          <img :src="currentGraphic.url" :alt="currentGraphic.filename" />
          <span class="course-display__slide-count">
            Slide {{ props.status.current_slide_index + 1 }} / {{ props.status.project.graphics.length }}
          </span>
        </div>
        <div v-else class="course-display__tip">
          <div class="course-display__tip-icon">{{ currentTip.icon }}</div>
          <h2 class="course-display__tip-title">{{ currentTip.title }}</h2>
          <p class="course-display__tip-text">{{ currentTip.description }}</p>
        </div>
      </section>

      <aside class="course-display__side">
        <div class="course-display__card glass-panel">
          <div class="course-display__label">Presenter</div>
          <div v-if="previewCamera" class="course-display__camera">
            <div class="course-display__camera-label">{{ previewCamera.label }}</div>
            <InputPreview :input-id="previewCamera.id" />
          </div>
          <div v-else class="course-display__camera-empty">Waiting for camera signal</div>
        </div>

        <div class="course-display__card glass-panel">
          <div class="course-display__label">Session</div>
          <div class="course-display__value">{{ props.status.booking.customer?.name || 'Guest' }}</div>
          <div class="course-display__meta">
            <span v-if="props.status.booking.client?.name">{{ props.status.booking.client.name }}</span>
            <span v-if="props.status.project?.name">• {{ props.status.project.name }}</span>
          </div>
          <div class="course-display__meta">
            {{ props.status.booking.date }} • {{ props.status.booking.slot_start }} - {{ props.status.booking.slot_end }}
          </div>
        </div>

        <div class="course-display__card glass-panel">
          <div class="course-display__label">Status</div>
          <div class="course-display__status" :class="{ 'course-display__status--live': isRecording }">
            <span class="course-display__status-dot"></span>
            {{ isRecording ? 'Recording' : 'Ready for recording' }}
          </div>
          <div v-if="!props.isPreview && props.status.disk_space_gb" class="course-display__meta">
            {{ props.status.disk_space_gb.toFixed(1) }} GB available
          </div>
        </div>
      </aside>
    </div>

    <template #footer>
      <div class="course-display__footer-left">
        <span v-if="isRecording" class="course-display__rec-badge">
          <span class="course-display__rec-dot"></span>
          REC
        </span>
        <span class="course-display__footer-text">Keep the slide in sync with your talk.</span>
      </div>
      <div class="course-display__footer-right">
        Slides will appear on this screen.
      </div>
    </template>
  </StudioDisplayShell>
</template>

<style scoped>
@import '@/styles/design-system-v2.css';

.course-display__main {
  align-items: stretch;
}

.course-display__timing {
  text-align: right;
}

.course-display__timer {
  font-size: 2.25rem;
  font-family: var(--preke-font-mono);
  font-weight: 700;
}

.course-display__remaining {
  font-size: 1rem;
  color: var(--preke-text-muted);
}

.course-display__layout {
  display: grid;
  grid-template-columns: minmax(0, 1.6fr) minmax(0, 0.7fr);
  gap: 2rem;
  width: 100%;
  height: 100%;
  min-height: 0;
}

.course-display__slides {
  padding: 1.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
}

.course-display__slide {
  width: 100%;
  height: 100%;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.course-display__slide img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  border-radius: var(--preke-radius-md);
  background: rgba(0, 0, 0, 0.3);
}

.course-display__slide-count {
  position: absolute;
  bottom: 1rem;
  right: 1rem;
  background: rgba(0, 0, 0, 0.7);
  color: #fff;
  padding: 0.4rem 0.8rem;
  border-radius: var(--preke-radius-md);
  font-size: 0.9rem;
}

.course-display__tip {
  text-align: center;
  max-width: 520px;
}

.course-display__tip-icon {
  font-size: 4.5rem;
  margin-bottom: 1.5rem;
}

.course-display__tip-title {
  font-size: 2rem;
  font-weight: 700;
  color: var(--preke-gold);
  margin-bottom: 0.75rem;
}

.course-display__tip-text {
  font-size: 1.25rem;
  color: var(--preke-text-dim);
  line-height: 1.6;
}

.course-display__side {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.course-display__card {
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.course-display__label {
  text-transform: uppercase;
  letter-spacing: 0.2em;
  font-size: 0.75rem;
  color: var(--preke-text-muted);
}

.course-display__camera {
  position: relative;
  border-radius: var(--preke-radius-md);
  overflow: hidden;
  aspect-ratio: 16/9;
  background: rgba(0, 0, 0, 0.4);
}

.course-display__camera-label {
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

.course-display__camera-empty {
  text-align: center;
  color: var(--preke-text-muted);
}

.course-display__value {
  font-size: 1.75rem;
  font-weight: 700;
}

.course-display__meta {
  color: var(--preke-text-dim);
  font-size: 1rem;
}

.course-display__status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  color: var(--preke-text-dim);
}

.course-display__status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--preke-text-subtle);
}

.course-display__status--live .course-display__status-dot {
  background: var(--preke-red);
  box-shadow: 0 0 12px rgba(212, 90, 90, 0.4);
}

.course-display__footer-left {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.course-display__footer-text {
  color: var(--preke-text-muted);
}

.course-display__footer-right {
  color: var(--preke-text-muted);
}

.course-display__rec-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.35rem 0.75rem;
  border-radius: var(--preke-radius-md);
  background: rgba(220, 38, 38, 0.2);
  color: var(--preke-red);
  font-weight: 700;
}

.course-display__rec-dot {
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
  .course-display__layout {
    grid-template-columns: 1fr;
  }
}
</style>
