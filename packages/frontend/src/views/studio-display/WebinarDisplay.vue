<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import StudioDisplayShell from '@/components/shared/StudioDisplayShell.vue'

const props = defineProps<{
  status: any
  isPreview?: boolean
}>()

const route = useRoute()
const token = computed(() => route.params.token as string | undefined)

const currentTipIndex = ref(0)
// Hardcoded VDO.ninja room URL with password for auto-join
const vdoNinjaUrl = ref<string>('https://app.itagenten.no/vdo/?room=studio&hash=c1f7&password=preke-r58-2024&broadcast&scene&cleanoutput&darkmode')
// Program output WHEP URL for MediaMTX mixer_program stream
const programWhepUrl = 'https://app.itagenten.no/mixer_program/whep'
const programVideoRef = ref<HTMLVideoElement | null>(null)
const programLoading = ref(false)
let programConnection: RTCPeerConnection | null = null
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

const isRecording = computed(() => props.status?.recording_active || false)

async function connectProgramOutput() {
  if (!programVideoRef.value || props.isPreview) return
  
  try {
    programLoading.value = true
    // Import ICE config
    const { getIceServers } = await import('@/lib/iceConfig')
    const iceServers = await getIceServers()
    
    programConnection = new RTCPeerConnection({
      iceServers
    })
    
    programConnection.ontrack = (event) => {
      if (programVideoRef.value && event.track.kind === 'video') {
        programVideoRef.value.srcObject = event.streams[0]
        programVideoRef.value.play().catch(console.warn)
        programLoading.value = false
      }
    }
    
    const response = await fetch(programWhepUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/sdp' }
    })
    
    if (!response.ok) {
      throw new Error(`WHEP connection failed: ${response.statusText}`)
    }
    
    const sdp = await response.text()
    await programConnection.setRemoteDescription({ type: 'offer', sdp })
    const answer = await programConnection.createAnswer()
    await programConnection.setLocalDescription(answer)
    
    const answerResponse = await fetch(response.headers.get('Location') || programWhepUrl, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/sdp' },
      body: answer.sdp
    })
    
    if (!answerResponse.ok) {
      throw new Error('Failed to send WHEP answer')
    }
  } catch (e) {
    console.error('[WebinarDisplay] Failed to connect program output:', e)
    programLoading.value = false
  }
}

function disconnectProgramOutput() {
  if (programConnection) {
    programConnection.close()
    programConnection = null
  }
  if (programVideoRef.value) {
    programVideoRef.value.srcObject = null
  }
}

onMounted(async () => {
  tipInterval = window.setInterval(() => {
    currentTipIndex.value = (currentTipIndex.value + 1) % webinarTips.length
  }, 5000)
  
  // Connect to program output when recording
  if (isRecording.value) {
    await connectProgramOutput()
  }
})

onUnmounted(() => {
  if (tipInterval) clearInterval(tipInterval)
  disconnectProgramOutput()
})

// Watch recording state to connect/disconnect program output
watch(isRecording, async (recording) => {
  if (recording) {
    await connectProgramOutput()
  } else {
    disconnectProgramOutput()
  }
})

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
      <section class="webinar-display__vdo-section glass-card">
        <div class="webinar-display__vdo-frame">
          <iframe
            :src="vdoNinjaUrl"
            class="webinar-display__vdo-iframe"
            allow="camera; microphone; display-capture; autoplay; clipboard-write"
            allowfullscreen
          ></iframe>
          <div v-if="isRecording" class="webinar-display__recording-indicator">
            <span class="webinar-display__recording-dot"></span>
            RECORDING
          </div>
        </div>
      </section>

      <aside class="webinar-display__right">
        <div v-if="isRecording" class="webinar-display__card glass-panel">
          <div class="webinar-display__label">Program Output</div>
          <div class="webinar-display__program-preview">
            <video
              ref="programVideoRef"
              autoplay
              muted
              playsinline
              class="webinar-display__program-video"
            ></video>
            <div v-if="programLoading" class="webinar-display__program-loading">
              <div class="webinar-display__spinner"></div>
            </div>
          </div>
        </div>

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
          <div class="webinar-display__label">Status</div>
          <div class="webinar-display__status" :class="{ 'webinar-display__status--ok': true }">
            <span class="webinar-display__status-dot"></span>
            VDO.ninja room active
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
        VDO.ninja room: studio
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
  gap: 1.75rem;
  width: 100%;
  height: 100%;
  min-height: 0;
  align-items: start;
}

.webinar-display__vdo-section {
  padding: 1.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 0;
  max-height: 100%;
  overflow: hidden;
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

.webinar-display__program-preview {
  position: relative;
  border-radius: var(--preke-radius-md);
  overflow: hidden;
  aspect-ratio: 16/9;
  background: rgba(0, 0, 0, 0.6);
  min-height: 0;
}

.webinar-display__program-video {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.webinar-display__program-loading {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.5);
}

.webinar-display__spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--preke-border);
  border-top-color: var(--preke-blue);
  border-radius: 50%;
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
  gap: 1.25rem;
  max-height: 100%;
  overflow-y: auto;
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
  background: var(--preke-green);
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
