<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'

const props = defineProps<{
  status: any
}>()

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

onMounted(() => {
  // Rotate tips every 5 seconds
  tipInterval = window.setInterval(() => {
    currentTipIndex.value = (currentTipIndex.value + 1) % recordingTips.length
  }, 5000)
})

onUnmounted(() => {
  if (tipInterval) clearInterval(tipInterval)
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
</script>

<template>
  <div class="podcast-display">
    <!-- Header -->
    <div class="display-header">
      <div class="flex items-center gap-6">
        <img v-if="status.booking.client?.logo_url" :src="status.booking.client.logo_url" alt="Logo" class="h-20 object-contain" />
        <div class="flex-1">
          <h1 class="text-3xl font-bold">{{ status.booking.customer?.name || 'Guest' }}</h1>
          <p class="text-xl text-preke-text-dim">{{ status.booking.client?.name }}</p>
        </div>
        <div class="text-right">
          <div class="text-4xl font-mono font-bold">{{ recordingDuration }}</div>
          <div v-if="timeRemaining" class="text-lg text-preke-text-muted">{{ timeRemaining }}</div>
        </div>
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
            v-for="(tip, index) in recordingTips" 
            :key="index"
            :class="['tip-dot', { active: index === currentTipIndex }]"
          ></span>
        </div>
      </div>
    </div>
    
    <!-- Recording: Multiview + Graphic -->
    <div v-else class="display-main recording-mode">
      <!-- Camera Grid Placeholder -->
      <div class="camera-grid">
        <div v-for="i in 4" :key="i" class="camera-preview">
          <div class="camera-placeholder">
            <svg class="w-16 h-16 text-preke-text-subtle" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
            </svg>
            <span class="text-sm">Camera {{ i }}</span>
          </div>
        </div>
      </div>
      
      <!-- Current Graphic (if any) -->
      <div v-if="currentGraphic" class="graphic-display">
        <img :src="currentGraphic.url" :alt="currentGraphic.filename" class="graphic-image" />
        <div class="graphic-indicator">
          Slide {{ status.current_slide_index + 1 }} / {{ status.project.graphics.length }}
        </div>
      </div>
    </div>
    
    <!-- Status Bar -->
    <div class="display-footer">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-4">
          <span v-if="isRecording" class="recording-badge">
            <span class="recording-dot"></span>
            REC
          </span>
          <span class="text-preke-text-muted">{{ status.booking.date }} • {{ status.booking.slot_start }} - {{ status.booking.slot_end }}</span>
        </div>
        <div class="flex items-center gap-4 text-preke-text-muted">
          <span>{{ status.disk_space_gb.toFixed(1) }} GB available</span>
          <span class="flex items-center gap-2">
            <span class="w-3 h-3 rounded-full bg-preke-green"></span>
            Connected
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
@import '@/styles/design-system-v2.css';

.podcast-display {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 3rem;
}

.display-header {
  background: var(--preke-glass-bg);
  border: 1px solid var(--preke-border);
  border-radius: var(--preke-radius-lg);
  padding: 2rem;
  backdrop-filter: blur(20px);
  box-shadow: var(--preke-shadow-lg);
}

.display-main {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 3rem 0;
}

/* Tips Mode */
.tips-container {
  text-align: center;
  max-width: 800px;
}

.tip-card {
  background: var(--preke-glass-bg);
  border: 1px solid var(--preke-border);
  border-radius: var(--preke-radius-xl);
  padding: 4rem;
  backdrop-filter: blur(20px);
  box-shadow: var(--preke-shadow-xl);
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
  color: var(--preke-text-dim);
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
  background: var(--preke-text-subtle);
  transition: all 0.3s ease;
}

.tip-dot.active {
  background: var(--preke-gold);
  transform: scale(1.5);
}

/* Recording Mode */
.recording-mode {
  gap: 2rem;
}

.camera-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1.5rem;
  flex: 1;
}

.camera-preview {
  background: var(--preke-glass-bg);
  border: 1px solid var(--preke-border);
  border-radius: var(--preke-radius-lg);
  aspect-ratio: 16/9;
  overflow: hidden;
}

.camera-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
}

.graphic-display {
  flex: 1;
  position: relative;
  background: var(--preke-glass-bg);
  border: 1px solid var(--preke-border);
  border-radius: var(--preke-radius-lg);
  overflow: hidden;
}

.graphic-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.graphic-indicator {
  position: absolute;
  bottom: 1.5rem;
  right: 1.5rem;
  background: rgba(0, 0, 0, 0.8);
  color: white;
  padding: 0.75rem 1.5rem;
  border-radius: var(--preke-radius-md);
  font-size: 1.25rem;
  font-weight: 600;
}

/* Footer */
.display-footer {
  background: var(--preke-glass-bg);
  border: 1px solid var(--preke-border);
  border-radius: var(--preke-radius-lg);
  padding: 1.5rem 2rem;
  backdrop-filter: blur(20px);
  font-size: 1.125rem;
}

.recording-badge {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  background: rgba(220, 38, 38, 0.2);
  color: var(--preke-red);
  padding: 0.5rem 1rem;
  border-radius: var(--preke-radius-md);
  font-weight: 700;
  font-size: 1.25rem;
}

.recording-dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: var(--preke-red);
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.3); }
}
</style>
