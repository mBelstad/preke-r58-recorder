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

const recordingTips = [
  {
    icon: '🎤',
    title: 'Use the Shure SM7B Microphone',
    description: 'Speak directly into the microphone for best audio quality'
  },
  {
    icon: '🎧',
    title: 'Headset Available',
    description: 'A headset is available if you prefer'
  },
  {
    icon: '👀',
    title: 'Look at the Host',
    description: 'Not at the camera - maintain natural conversation'
  },
  {
    icon: '💇',
    title: 'Check Your Hair',
    description: 'Keep hair away from your face for best visibility'
  },
  {
    icon: '😌',
    title: 'Relax and Be Natural',
    description: 'Speak naturally and take your time'
  }
]

let pollInterval: number | null = null

onMounted(async () => {
  // Rotate tips every 5 seconds
  tipInterval = window.setInterval(() => {
    currentTipIndex.value = (currentTipIndex.value + 1) % recordingTips.length
  }, 5000)
  
  // Always fetch camera inputs - multiview is core functionality
  console.log('[PodcastDisplay] Fetching camera inputs')
  await recorderStore.fetchInputs()
  // Poll for input updates every 2 seconds
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

const currentTip = computed(() => recordingTips[currentTipIndex.value])

// Get active cameras for multiview - always show if available
const activeCameras = computed(() => {
  return recorderStore.inputs.filter(i => i.hasSignal).slice(0, 4) // Max 4 cameras
})
</script>

<template>
  <StudioDisplayShell
    title="Podcast Session"
    subtitle="Live multi-cam recording"
    accent="gold"
    :show-footer="true"
    main-class="podcast-display__main"
  >
    <template #header-right>
      <div class="podcast-display__timing">
        <div class="podcast-display__timer">{{ recordingDuration }}</div>
        <div v-if="timeRemaining" class="podcast-display__remaining">{{ timeRemaining }}</div>
      </div>
    </template>

    <div class="podcast-display__layout">
      <section class="podcast-display__left glass-card">
        <div v-if="activeCameras.length > 0" class="podcast-display__grid">
          <div
            v-for="camera in activeCameras"
            :key="camera.id"
            class="podcast-display__camera"
          >
            <div class="podcast-display__camera-label">{{ camera.label }}</div>
            <InputPreview :input-id="camera.id" />
          </div>
          <div
            v-for="i in (4 - activeCameras.length)"
            :key="`empty-${i}`"
            class="podcast-display__camera podcast-display__camera--empty"
          >
            <span>No Camera</span>
          </div>
        </div>
        <div v-else class="podcast-display__tip">
          <div class="podcast-display__tip-icon">{{ currentTip.icon }}</div>
          <h2 class="podcast-display__tip-title">{{ currentTip.title }}</h2>
          <p class="podcast-display__tip-text">{{ currentTip.description }}</p>
        </div>
      </section>

      <aside class="podcast-display__right">
        <div class="podcast-display__card glass-panel">
          <div class="podcast-display__label">Session</div>
          <div class="podcast-display__value">{{ status.booking.customer?.name || 'Guest' }}</div>
          <div class="podcast-display__meta">
            <span v-if="status.booking.client?.name">{{ status.booking.client.name }}</span>
            <span v-if="status.project?.name">• {{ status.project.name }}</span>
          </div>
          <div class="podcast-display__meta">
            {{ status.booking.date }} • {{ status.booking.slot_start }} - {{ status.booking.slot_end }}
          </div>
        </div>

        <div v-if="currentGraphic" class="podcast-display__card glass-panel">
          <div class="podcast-display__label">Current Slide</div>
          <div class="podcast-display__slide">
            <img :src="currentGraphic.url" :alt="currentGraphic.filename" />
            <span>Slide {{ status.current_slide_index + 1 }} / {{ status.project.graphics.length }}</span>
          </div>
        </div>

        <div class="podcast-display__card glass-panel">
          <div class="podcast-display__label">Status</div>
          <div class="podcast-display__status" :class="{ 'podcast-display__status--live': isRecording }">
            <span class="podcast-display__status-dot"></span>
            {{ isRecording ? 'Recording in progress' : 'Ready to record' }}
          </div>
          <div v-if="!isPreview && status.disk_space_gb" class="podcast-display__meta">
            {{ status.disk_space_gb.toFixed(1) }} GB available
          </div>
        </div>
      </aside>
    </div>

    <template #footer>
      <div class="podcast-display__footer-left">
        <span v-if="isRecording" class="podcast-display__rec-badge">
          <span class="podcast-display__rec-dot"></span>
          REC
        </span>
        <span class="podcast-display__footer-text">Stay close to the mic and speak clearly.</span>
      </div>
      <div v-if="!isPreview" class="podcast-display__footer-right">
        System connected
      </div>
    </template>
  </StudioDisplayShell>
</template>

<style scoped>
@import '@/styles/design-system-v2.css';

.podcast-display__main {
  align-items: stretch;
}

.podcast-display__timing {
  text-align: right;
}

.podcast-display__timer {
  font-size: 2.5rem;
  font-family: var(--preke-font-mono);
  font-weight: 700;
}

.podcast-display__remaining {
  font-size: 1rem;
  color: var(--preke-text-muted);
}

.podcast-display__layout {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(0, 0.8fr);
  gap: 2rem;
  width: 100%;
  height: 100%;
  min-height: 0;
}

.podcast-display__left {
  padding: 1.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 0;
}

.podcast-display__grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
  width: 100%;
}

.podcast-display__camera {
  position: relative;
  background: rgba(0, 0, 0, 0.35);
  border-radius: var(--preke-radius-lg);
  overflow: hidden;
  aspect-ratio: 16/9;
  border: 1px solid var(--preke-border);
}

.podcast-display__camera--empty {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--preke-text-subtle);
  font-size: 1rem;
}

.podcast-display__camera-label {
  position: absolute;
  top: 0.75rem;
  left: 0.75rem;
  background: rgba(0, 0, 0, 0.75);
  color: #fff;
  padding: 0.35rem 0.75rem;
  border-radius: var(--preke-radius-sm);
  font-size: 0.75rem;
  font-weight: 600;
  z-index: 2;
}

.podcast-display__tip {
  text-align: center;
  max-width: 520px;
}

.podcast-display__tip-icon {
  font-size: 4.5rem;
  margin-bottom: 1.5rem;
}

.podcast-display__tip-title {
  font-size: 2rem;
  font-weight: 700;
  color: var(--preke-gold);
  margin-bottom: 0.75rem;
}

.podcast-display__tip-text {
  font-size: 1.25rem;
  color: var(--preke-text-dim);
  line-height: 1.6;
}

.podcast-display__right {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  min-height: 0;
}

.podcast-display__card {
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.podcast-display__label {
  text-transform: uppercase;
  letter-spacing: 0.2em;
  font-size: 0.75rem;
  color: var(--preke-text-muted);
}

.podcast-display__value {
  font-size: 1.75rem;
  font-weight: 700;
}

.podcast-display__meta {
  color: var(--preke-text-dim);
  font-size: 1rem;
}

.podcast-display__slide {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  align-items: flex-start;
  color: var(--preke-text-muted);
}

.podcast-display__slide img {
  width: 100%;
  max-height: 220px;
  object-fit: contain;
  border-radius: var(--preke-radius-md);
  background: rgba(0, 0, 0, 0.35);
}

.podcast-display__status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  color: var(--preke-text-dim);
}

.podcast-display__status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--preke-text-subtle);
}

.podcast-display__status--live .podcast-display__status-dot {
  background: var(--preke-red);
  box-shadow: 0 0 12px rgba(212, 90, 90, 0.4);
}

.podcast-display__footer-left {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.podcast-display__footer-text {
  color: var(--preke-text-muted);
}

.podcast-display__footer-right {
  color: var(--preke-text-muted);
}

.podcast-display__rec-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.4rem 0.9rem;
  border-radius: var(--preke-radius-md);
  background: rgba(220, 38, 38, 0.2);
  color: var(--preke-red);
  font-weight: 700;
}

.podcast-display__rec-dot {
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
  .podcast-display__layout {
    grid-template-columns: 1fr;
  }
}
</style>
