<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { r58Api } from '@/lib/api'
import { useRoute } from 'vue-router'
import StudioDisplayShell from '@/components/shared/StudioDisplayShell.vue'

const props = defineProps<{
  status: any
  isPreview?: boolean
}>()

const route = useRoute()
const token = computed(() => route.params.token as string)

const currentTipIndex = ref(0)
const vdoNinjaAvailable = ref(true)
const vdoNinjaUrl = ref<string | null>(null)
const checkingVdo = ref(true)
let tipInterval: number | null = null

const webinarTips = [
  {
    icon: '🎥',
    title: 'Check Your Audio and Video Settings',
    description: 'Test your microphone and camera before starting'
  },
  {
    icon: '🔇',
    title: 'Mute When Not Speaking',
    description: 'Reduce background noise for better audio quality'
  },
  {
    icon: '💡',
    title: 'Use Good Lighting',
    description: 'Face a light source for clear video'
  },
  {
    icon: '🖼️',
    title: 'Minimize Background Distractions',
    description: 'Choose a clean, professional background'
  },
  {
    icon: '📊',
    title: 'Have Your Presentation Ready',
    description: 'Prepare slides and materials in advance'
  }
]

onMounted(async () => {
  // Only check VDO.ninja if not in preview mode
  if (!props.isPreview) {
    await checkVdoNinja()
  } else {
    checkingVdo.value = false
    vdoNinjaAvailable.value = false
  }
  
  // Rotate tips every 5 seconds
  tipInterval = window.setInterval(() => {
    currentTipIndex.value = (currentTipIndex.value + 1) % webinarTips.length
  }, 5000)
})

onUnmounted(() => {
  if (tipInterval) clearInterval(tipInterval)
})

async function checkVdoNinja() {
  try {
    const response = await r58Api.wordpress.checkVdoNinjaStatus(token.value)
    vdoNinjaAvailable.value = response.available
    if (response.available && response.url) {
      // Build VDO.ninja URL with room and parameters
      const roomId = `r58-${props.status.booking.id}`
      vdoNinjaUrl.value = `${response.url}/?room=${roomId}&scene&cleanoutput&darkmode`
    }
  } catch (e) {
    console.error('Failed to check VDO.ninja status:', e)
    vdoNinjaAvailable.value = false
  } finally {
    checkingVdo.value = false
  }
}

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

const currentTip = computed(() => webinarTips[currentTipIndex.value])
</script>

<template>
  <StudioDisplayShell
    title="Webinar Session"
    subtitle="Remote guest experience"
    accent="blue"
    :show-footer="true"
    main-class="webinar-display__main"
  >
    <template #header-right>
      <div class="webinar-display__timing">
        <div class="webinar-display__timer">{{ recordingDuration }}</div>
        <div v-if="timeRemaining" class="webinar-display__remaining">{{ timeRemaining }}</div>
      </div>
    </template>

    <div class="webinar-display__layout">
      <section class="webinar-display__left glass-card">
        <div v-if="!isRecording" class="webinar-display__tip">
          <div class="webinar-display__tip-icon">{{ currentTip.icon }}</div>
          <h2 class="webinar-display__tip-title">{{ currentTip.title }}</h2>
          <p class="webinar-display__tip-text">{{ currentTip.description }}</p>
        </div>
        <div v-else class="webinar-display__vdo">
          <div v-if="checkingVdo" class="webinar-display__vdo-status">
            <div class="webinar-display__spinner"></div>
            <p>Connecting to VDO.ninja...</p>
          </div>
          <div v-else-if="!vdoNinjaAvailable && !isPreview" class="webinar-display__vdo-status">
            <h2>VDO.ninja Offline</h2>
            <p>Please check the internet connection.</p>
          </div>
          <div v-else-if="vdoNinjaUrl" class="webinar-display__vdo-frame">
            <iframe
              :src="vdoNinjaUrl"
              class="webinar-display__vdo-iframe"
              allow="camera; microphone; display-capture; autoplay; clipboard-write"
              allowfullscreen
            ></iframe>
            <div class="webinar-display__recording-indicator">
              <span class="webinar-display__recording-dot"></span>
              RECORDING
            </div>
          </div>
        </div>
      </section>

      <aside class="webinar-display__right">
        <div class="webinar-display__card glass-panel">
          <div class="webinar-display__label">Session</div>
          <div class="webinar-display__value">{{ status.booking.customer?.name || 'Guest' }}</div>
          <div class="webinar-display__meta">
            <span v-if="status.booking.client?.name">{{ status.booking.client.name }}</span>
            <span v-if="status.project?.name">• {{ status.project.name }}</span>
          </div>
          <div class="webinar-display__meta">
            {{ status.booking.date }} • {{ status.booking.slot_start }} - {{ status.booking.slot_end }}
          </div>
        </div>

        <div class="webinar-display__card glass-panel">
          <div class="webinar-display__label">Connection</div>
          <div class="webinar-display__status" :class="{ 'webinar-display__status--ok': vdoNinjaAvailable }">
            <span class="webinar-display__status-dot"></span>
            {{ vdoNinjaAvailable ? 'VDO.ninja connected' : 'Waiting for VDO.ninja' }}
          </div>
          <div v-if="!isPreview && status.disk_space_gb" class="webinar-display__meta">
            {{ status.disk_space_gb.toFixed(1) }} GB available
          </div>
        </div>
      </aside>
    </div>

    <template #footer>
      <div class="webinar-display__footer-left">
        <span v-if="isRecording" class="webinar-display__rec-badge">
          <span class="webinar-display__rec-dot"></span>
          REC
        </span>
        <span class="webinar-display__footer-text">Keep your microphone muted when not speaking.</span>
      </div>
      <div class="webinar-display__footer-right">
        {{ vdoNinjaAvailable ? 'Video link active' : 'Video link offline' }}
      </div>
    </template>
  </StudioDisplayShell>
</template>

<style scoped>
@import '@/styles/design-system-v2.css';

.webinar-display__main {
  align-items: stretch;
}

.webinar-display__timing {
  text-align: right;
}

.webinar-display__timer {
  font-size: 2.25rem;
  font-family: var(--preke-font-mono);
  font-weight: 700;
}

.webinar-display__remaining {
  font-size: 1rem;
  color: var(--preke-text-muted);
}

.webinar-display__layout {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(0, 0.8fr);
  gap: 2rem;
  width: 100%;
  height: 100%;
  min-height: 0;
}

.webinar-display__left {
  padding: 1.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 0;
}

.webinar-display__tip {
  text-align: center;
  max-width: 520px;
}

.webinar-display__tip-icon {
  font-size: 4.5rem;
  margin-bottom: 1.5rem;
}

.webinar-display__tip-title {
  font-size: 2rem;
  font-weight: 700;
  margin-bottom: 0.75rem;
  color: var(--preke-gold);
}

.webinar-display__tip-text {
  font-size: 1.25rem;
  color: var(--preke-text-dim);
  line-height: 1.6;
}

.webinar-display__vdo {
  width: 100%;
  height: 100%;
}

.webinar-display__vdo-frame {
  width: 100%;
  height: 100%;
  position: relative;
  border-radius: var(--preke-radius-lg);
  overflow: hidden;
  background: #000;
}

.webinar-display__vdo-iframe {
  width: 100%;
  height: 100%;
  border: none;
}

.webinar-display__vdo-status {
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  color: var(--preke-text-dim);
}

.webinar-display__spinner {
  width: 56px;
  height: 56px;
  border: 5px solid var(--preke-border);
  border-top-color: var(--preke-blue);
  border-radius: 50%;
  margin: 0 auto;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.webinar-display__recording-indicator {
  position: absolute;
  top: 1.5rem;
  right: 1.5rem;
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.6rem 1rem;
  border-radius: var(--preke-radius-md);
  background: rgba(220, 38, 38, 0.85);
  color: #fff;
  font-weight: 700;
}

.webinar-display__recording-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #fff;
}

.webinar-display__right {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.webinar-display__card {
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.webinar-display__label {
  text-transform: uppercase;
  letter-spacing: 0.2em;
  font-size: 0.75rem;
  color: var(--preke-text-muted);
}

.webinar-display__value {
  font-size: 1.75rem;
  font-weight: 700;
}

.webinar-display__meta {
  color: var(--preke-text-dim);
  font-size: 1rem;
}

.webinar-display__status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  color: var(--preke-text-dim);
}

.webinar-display__status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--preke-red);
}

.webinar-display__status--ok .webinar-display__status-dot {
  background: var(--preke-green);
  box-shadow: 0 0 12px rgba(109, 181, 109, 0.4);
}

.webinar-display__footer-left {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.webinar-display__footer-text {
  color: var(--preke-text-muted);
}

.webinar-display__footer-right {
  color: var(--preke-text-muted);
}

.webinar-display__rec-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.35rem 0.75rem;
  border-radius: var(--preke-radius-md);
  background: rgba(220, 38, 38, 0.2);
  color: var(--preke-red);
  font-weight: 700;
}

.webinar-display__rec-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--preke-red);
}

@media (max-width: 1200px) {
  .webinar-display__layout {
    grid-template-columns: 1fr;
  }
}
</style>
