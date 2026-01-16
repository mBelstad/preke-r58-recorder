<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRecorderStore } from '@/stores/recorder'
import InputPreview from '@/components/shared/InputPreview.vue'

const props = defineProps<{
  status: any
  isPreview?: boolean
}>()

const recorderStore = useRecorderStore()

const currentTipIndex = ref(0)
const scrollPosition = ref(0)
const isPaused = ref(false)
const showCamera = ref(false)
let tipInterval: number | null = null
let scrollAnimationId: number | null = null

const teleprompterTips = [
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
  },
  {
    icon: '🌬️',
    title: 'Take a Breath Between Sections',
    description: 'Pause naturally between paragraphs'
  }
]

onMounted(async () => {
  // Rotate tips every 5 seconds
  tipInterval = window.setInterval(() => {
    currentTipIndex.value = (currentTipIndex.value + 1) % teleprompterTips.length
  }, 5000)
  
  // Keyboard controls
  window.addEventListener('keydown', handleKeyDown)
  
  // Start auto-scroll when recording
  if (isRecording.value) {
    startScroll()
  }
  
  // Fetch camera inputs if not in preview mode
  if (!props.isPreview) {
    await recorderStore.fetchInputs()
    // Poll for input updates every 2 seconds
    const pollInterval = window.setInterval(() => {
      recorderStore.fetchInputs()
    }, 2000)
    onUnmounted(() => clearInterval(pollInterval))
  }
})

onUnmounted(() => {
  if (tipInterval) clearInterval(tipInterval)
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

const currentTip = computed(() => teleprompterTips[currentTipIndex.value])

const scrollSpeed = computed(() => {
  const speed = props.status?.teleprompter_scroll_speed || 50
  // Convert 1-100 to pixels per frame (0.5 to 5)
  return (speed / 100) * 4.5 + 0.5
})

const scriptText = computed(() => {
  return props.status?.teleprompter_script || 'No script loaded. Please add a script in the booking settings.'
})

// Get first active camera for preview
const previewCamera = computed(() => {
  if (props.isPreview) return null
  return recorderStore.inputs.find(i => i.hasSignal) || null
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
    case 'h':
    case 'H':
      e.preventDefault()
      showCamera.value = !showCamera.value
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
  <div class="teleprompter-display">
    <!-- Header (only when recording) -->
    <div v-if="isRecording" class="display-header">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-4">
          <span class="recording-badge">
            <span class="recording-dot"></span>
            REC
          </span>
          <div class="text-2xl font-mono font-bold">{{ recordingDuration }}</div>
        </div>
        <div v-if="timeRemaining" class="text-lg text-preke-text-muted">{{ timeRemaining }}</div>
      </div>
    </div>
    
    <!-- Pre-Recording: Tips Mode -->
    <div v-if="!isRecording" class="display-main">
      <div class="tips-container">
        <div class="tip-card">
          <div class="tip-icon">{{ currentTip.icon }}</div>
          <h2 class="tip-title">{{ currentTip.title }}</h2>
          <p class="tip-description">{{ currentTip.description }}</p>
        </div>
        
        <!-- Tip indicators -->
        <div class="tip-indicators">
          <span 
            v-for="(tip, index) in teleprompterTips" 
            :key="index"
            :class="['tip-dot', { active: index === currentTipIndex }]"
          ></span>
        </div>
      </div>
    </div>
    
    <!-- Recording: Teleprompter -->
    <div v-else class="display-main teleprompter-mode">
      <!-- Teleprompter Text Container -->
      <div class="teleprompter-container">
        <div 
          class="teleprompter-text" 
          :style="{ transform: `translateY(-${scrollPosition}px) scaleX(-1)` }"
        >
          <div class="text-content">
            {{ scriptText }}
          </div>
        </div>
      </div>
      
      <!-- Camera Preview (toggleable) -->
      <div v-if="showCamera" class="camera-preview">
        <div v-if="previewCamera" class="camera-preview-container">
          <div class="camera-label">{{ previewCamera.label }}</div>
          <InputPreview :input-id="previewCamera.id" />
        </div>
        <div v-else class="camera-placeholder">
          <svg class="w-12 h-12 text-preke-text-subtle" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
          </svg>
          <span class="text-xs">No Camera Available</span>
        </div>
      </div>
    </div>
    
    <!-- Controls Footer (only when recording) -->
    <div v-if="isRecording" class="display-footer">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-6">
          <div class="control-hint">
            <kbd>Space</kbd> {{ isPaused ? 'Resume' : 'Pause' }}
          </div>
          <div class="control-hint">
            <kbd>↑↓</kbd> Manual Scroll
          </div>
          <div class="control-hint">
            <kbd>H</kbd> {{ showCamera ? 'Hide' : 'Show' }} Camera
          </div>
        </div>
        <div class="flex items-center gap-4">
          <span class="text-preke-text-muted">Speed: {{ status.teleprompter_scroll_speed }}%</span>
          <span v-if="isPaused" class="pause-indicator">⏸ PAUSED</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
@import '@/styles/design-system-v2.css';

.teleprompter-display {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #000;
  color: #fff;
}

.display-header {
  padding: 2rem 3rem;
  background: rgba(0, 0, 0, 0.8);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.display-main {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
}

/* Tips Mode */
.tips-container {
  text-align: center;
  max-width: 800px;
  padding: 3rem;
}

.tip-card {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 1.5rem;
  padding: 4rem;
  backdrop-filter: blur(20px);
  animation: fadeIn 0.5s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.tip-icon {
  font-size: 6rem;
  margin-bottom: 2rem;
}

.tip-title {
  font-size: 2.5rem;
  font-weight: 700;
  margin-bottom: 1rem;
  color: var(--preke-gold);
}

.tip-description {
  font-size: 1.5rem;
  color: rgba(255, 255, 255, 0.7);
  line-height: 1.6;
}

.tip-indicators {
  display: flex;
  gap: 1rem;
  justify-content: center;
  margin-top: 3rem;
}

.tip-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.3);
  transition: all 0.3s ease;
}

.tip-dot.active {
  background: var(--preke-gold);
  transform: scale(1.5);
}

/* Teleprompter Mode */
.teleprompter-mode {
  padding: 0;
}

.teleprompter-container {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  position: relative;
}

.teleprompter-text {
  font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-size: clamp(48px, 8vw, 72px);
  line-height: 1.4;
  font-weight: 500;
  text-align: center;
  padding: 2rem 4rem;
  transition: transform 0.05s linear;
  will-change: transform;
}

.text-content {
  max-width: 1200px;
  margin: 0 auto;
  white-space: pre-wrap;
  word-wrap: break-word;
}

/* Camera Preview */
.camera-preview {
  position: absolute;
  bottom: 2rem;
  right: 2rem;
  width: 320px;
  aspect-ratio: 16/9;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 0.75rem;
  overflow: hidden;
  backdrop-filter: blur(10px);
}

.camera-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
}

/* Footer */
.display-footer {
  padding: 1.5rem 3rem;
  background: rgba(0, 0, 0, 0.8);
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  font-size: 1rem;
}

.control-hint {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: rgba(255, 255, 255, 0.7);
}

kbd {
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 0.25rem;
  padding: 0.25rem 0.5rem;
  font-family: monospace;
  font-size: 0.875rem;
  color: #fff;
}

.pause-indicator {
  color: var(--preke-gold);
  font-weight: 600;
  animation: blink 1s ease-in-out infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.recording-badge {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  background: rgba(220, 38, 38, 0.3);
  color: #ff4444;
  padding: 0.5rem 1rem;
  border-radius: 0.5rem;
  font-weight: 700;
  font-size: 1.25rem;
}

.recording-dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #ff4444;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.3); }
}
</style>
