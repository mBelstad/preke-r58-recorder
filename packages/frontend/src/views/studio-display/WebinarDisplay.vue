<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { r58Api } from '@/lib/api'
import { useRoute } from 'vue-router'

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
  <div class="webinar-display">
    <!-- Header -->
    <div class="display-header">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-6">
          <img v-if="status.booking.client?.logo_url" :src="status.booking.client.logo_url" alt="Logo" class="h-16 object-contain" />
          <div>
            <h1 class="text-2xl font-bold">{{ status.booking.customer?.name || 'Guest' }}</h1>
            <p v-if="status.booking.client?.name" class="text-lg text-preke-text-dim">{{ status.booking.client.name }}</p>
            <p v-if="status.project?.name" class="text-base text-preke-text-muted mt-1">{{ status.project.name }}</p>
          </div>
        </div>
        <div class="flex items-center gap-6">
          <div v-if="isRecording" class="recording-badge">
            <span class="recording-dot"></span>
            REC
          </div>
          <div class="text-right">
            <div class="text-3xl font-mono font-bold">{{ recordingDuration }}</div>
            <div v-if="timeRemaining" class="text-sm text-preke-text-muted">{{ timeRemaining }}</div>
          </div>
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
            v-for="(tip, index) in webinarTips" 
            :key="index"
            :class="['tip-dot', { active: index === currentTipIndex }]"
          ></span>
        </div>
      </div>
    </div>
    
    <!-- Recording: VDO.ninja -->
    <div v-else class="display-main webinar-mode">
      <!-- VDO.ninja Checking -->
      <div v-if="checkingVdo" class="vdo-status">
        <div class="animate-spin w-12 h-12 border-4 border-preke-gold border-t-transparent rounded-full mx-auto mb-4"></div>
        <p class="text-xl text-preke-text-dim">Connecting to VDO.ninja...</p>
      </div>
      
      <!-- VDO.ninja Offline -->
      <div v-else-if="!vdoNinjaAvailable && !isPreview" class="vdo-status">
        <svg class="w-20 h-20 text-preke-red mx-auto mb-4" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"/>
        </svg>
        <h2 class="text-2xl font-bold mb-2">VDO.ninja Offline</h2>
        <p class="text-lg text-preke-text-dim">Cannot connect to vdo.itagenten.no</p>
        <p class="text-sm text-preke-text-muted mt-4">Please check your internet connection or contact support</p>
      </div>
      
      <!-- VDO.ninja iframe -->
      <div v-else-if="vdoNinjaUrl" class="vdo-container">
        <iframe 
          :src="vdoNinjaUrl" 
          class="vdo-iframe"
          allow="camera; microphone; display-capture; autoplay; clipboard-write"
          allowfullscreen
        ></iframe>
        
        <!-- Recording indicator overlay -->
        <div class="recording-indicator">
          <span class="recording-dot"></span>
          RECORDING
        </div>
      </div>
    </div>
    
    <!-- Status Bar -->
    <div class="display-footer">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-4">
          <span class="text-preke-text-muted">{{ status.booking.date }} • {{ status.booking.slot_start }} - {{ status.booking.slot_end }}</span>
        </div>
        <div v-if="!isPreview" class="flex items-center gap-4 text-preke-text-muted">
          <span v-if="status.disk_space_gb">{{ status.disk_space_gb.toFixed(1) }} GB available</span>
          <span class="flex items-center gap-2">
            <span :class="['w-3 h-3 rounded-full', vdoNinjaAvailable ? 'bg-preke-green' : 'bg-preke-red']"></span>
            {{ vdoNinjaAvailable ? 'VDO.ninja Connected' : 'VDO.ninja Offline' }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
@import '@/styles/design-system-v2.css';

.webinar-display {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--preke-bg-base);
}

.display-header {
  background: var(--preke-glass-bg);
  border-bottom: 1px solid var(--preke-border);
  padding: 1.5rem 3rem;
  backdrop-filter: blur(20px);
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

/* Webinar Mode */
.webinar-mode {
  padding: 2rem;
}

.vdo-status {
  text-align: center;
  max-width: 600px;
}

.vdo-container {
  width: 100%;
  height: 100%;
  position: relative;
  background: #000;
  border-radius: var(--preke-radius-lg);
  overflow: hidden;
}

.vdo-iframe {
  width: 100%;
  height: 100%;
  border: none;
}

.recording-indicator {
  position: absolute;
  top: 2rem;
  right: 2rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  background: rgba(220, 38, 38, 0.9);
  color: white;
  padding: 0.75rem 1.5rem;
  border-radius: var(--preke-radius-md);
  font-weight: 700;
  font-size: 1.125rem;
  backdrop-filter: blur(10px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

/* Footer */
.display-footer {
  background: var(--preke-glass-bg);
  border-top: 1px solid var(--preke-border);
  padding: 1.5rem 3rem;
  backdrop-filter: blur(20px);
  font-size: 1rem;
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
  font-size: 1.125rem;
}

.recording-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: currentColor;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.3); }
}
</style>
