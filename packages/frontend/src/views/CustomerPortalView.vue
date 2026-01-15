<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { r58Api } from '@/lib/api'

const route = useRoute()
const token = computed(() => route.params.token as string)

const status = ref<any>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const currentSlideIndex = ref(0)
const isRecording = ref(false)
const displayMode = ref<string>('podcast')
const teleprompterPaused = ref(false)
const teleprompterSpeed = ref<number>(50)

let statusInterval: number | null = null

onMounted(async () => {
  await loadStatus()
  // Poll status every 2 seconds
  statusInterval = window.setInterval(loadStatus, 2000)
})

onUnmounted(() => {
  if (statusInterval) {
    clearInterval(statusInterval)
  }
})

async function loadStatus() {
  try {
    const response = await r58Api.wordpress.getCustomerStatus(token.value)
    status.value = response
    isRecording.value = response.recording_active
    currentSlideIndex.value = response.current_slide_index
    displayMode.value = response.display_mode || 'podcast'
    teleprompterSpeed.value = response.teleprompter_scroll_speed || 50
    error.value = null
  } catch (e: any) {
    if (loading.value) {
      error.value = e.message || 'Invalid or expired link'
    }
  } finally {
    loading.value = false
  }
}

async function startRecording() {
  try {
    await r58Api.wordpress.customerStartRecording(token.value)
    isRecording.value = true
    // Haptic feedback if available
    if ('vibrate' in navigator) {
      navigator.vibrate(50)
    }
  } catch (e: any) {
    error.value = e.message || 'Failed to start recording'
  }
}

async function stopRecording() {
  if (!confirm('Stop recording?')) return
  
  try {
    await r58Api.wordpress.customerStopRecording(token.value)
    isRecording.value = false
    if ('vibrate' in navigator) {
      navigator.vibrate([50, 100, 50])
    }
  } catch (e: any) {
    error.value = e.message || 'Failed to stop recording'
  }
}

async function gotoSlide(index: number) {
  try {
    await r58Api.wordpress.customerGotoSlide(token.value, index)
    currentSlideIndex.value = index
    if ('vibrate' in navigator) {
      navigator.vibrate(30)
    }
  } catch (e: any) {
    error.value = e.message || 'Failed to change slide'
  }
}

function nextSlide() {
  if (status.value && currentSlideIndex.value < status.value.project.graphics.length - 1) {
    gotoSlide(currentSlideIndex.value + 1)
  }
}

function prevSlide() {
  if (currentSlideIndex.value > 0) {
    gotoSlide(currentSlideIndex.value - 1)
  }
}

const currentGraphic = computed(() => {
  if (!status.value?.project?.graphics) return null
  return status.value.project.graphics[currentSlideIndex.value]
})

const recordingDuration = computed(() => {
  if (!status.value?.recording_duration_ms) return '00:00'
  const seconds = Math.floor(status.value.recording_duration_ms / 1000)
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
})

async function adjustTeleprompterSpeed(delta: number) {
  const newSpeed = Math.max(1, Math.min(100, teleprompterSpeed.value + delta))
  teleprompterSpeed.value = newSpeed
  try {
    await r58Api.wordpress.setTeleprompterSpeed(token.value, newSpeed)
    if ('vibrate' in navigator) {
      navigator.vibrate(20)
    }
  } catch (e: any) {
    error.value = e.message || 'Failed to adjust speed'
  }
}
</script>

<template>
  <div class="customer-portal">
    <!-- Ambient background -->
    <div class="portal-bg">
      <div class="bg-orb bg-orb--1"></div>
      <div class="bg-orb bg-orb--2"></div>
    </div>
    
    <!-- Loading State -->
    <div v-if="loading" class="portal-content">
      <div class="glass-card text-center">
        <div class="animate-spin w-12 h-12 border-4 border-preke-gold border-t-transparent rounded-full mx-auto mb-4"></div>
        <p class="text-preke-text-dim">Loading your session...</p>
      </div>
    </div>
    
    <!-- Error State -->
    <div v-else-if="error" class="portal-content">
      <div class="glass-card text-center">
        <svg class="w-16 h-16 text-preke-red mx-auto mb-4" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"/>
        </svg>
        <h2 class="text-xl font-bold mb-2">Session Not Found</h2>
        <p class="text-preke-text-dim">{{ error }}</p>
      </div>
    </div>
    
    <!-- Main Content -->
    <div v-else-if="status" class="portal-content">
      <!-- Header -->
      <div class="portal-header glass-card">
        <div class="flex items-center gap-4">
          <img v-if="status.booking.client?.logo_url" :src="status.booking.client.logo_url" alt="Logo" class="w-16 h-16 object-contain rounded-lg bg-preke-bg-elevated p-2" />
          <div class="flex-1">
            <h1 class="text-xl font-bold">Welcome, {{ status.booking.customer?.name || 'Guest' }}</h1>
            <p class="text-preke-text-dim text-sm">{{ status.booking.client?.name }}</p>
          </div>
        </div>
        <div class="mt-4 flex items-center justify-between text-sm">
          <span class="text-preke-text-muted">{{ status.booking.date }} • {{ status.booking.slot_start }} - {{ status.booking.slot_end }}</span>
          <span class="badge-v2 badge-v2--success" v-if="isRecording">Recording</span>
        </div>
      </div>
      
      <!-- Graphics Preview (Podcast/Webinar modes) -->
      <div v-if="currentGraphic && displayMode !== 'teleprompter'" class="glass-card">
        <h2 class="text-lg font-semibold mb-3">Presentation</h2>
        <div class="graphic-preview">
          <img :src="currentGraphic.url" :alt="currentGraphic.filename" class="w-full rounded-lg" />
          <div class="slide-indicator">
            {{ currentSlideIndex + 1 }} / {{ status.project.graphics.length }}
          </div>
        </div>
        
        <!-- Slide Navigation -->
        <div class="flex items-center gap-2 mt-4">
          <button
            @click="prevSlide"
            :disabled="currentSlideIndex === 0"
            class="btn-v2 btn-v2--glass flex-1 touch-target"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
            </svg>
            Previous
          </button>
          <button
            @click="nextSlide"
            :disabled="currentSlideIndex >= status.project.graphics.length - 1"
            class="btn-v2 btn-v2--glass flex-1 touch-target"
          >
            Next
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
            </svg>
          </button>
        </div>
      </div>
      
      <!-- Teleprompter Controls -->
      <div v-if="displayMode === 'teleprompter'" class="glass-card">
        <h2 class="text-lg font-semibold mb-3">Teleprompter Controls</h2>
        
        <div class="space-y-3">
          <div class="flex items-center justify-between p-3 bg-preke-bg-elevated rounded-lg">
            <span class="text-preke-text-dim">Scroll Speed</span>
            <div class="flex items-center gap-2">
              <button
                @click="adjustTeleprompterSpeed(-10)"
                class="btn-v2 btn-v2--glass btn-sm touch-target"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 12H4"/>
                </svg>
              </button>
              <span class="font-mono font-bold min-w-[3rem] text-center">{{ teleprompterSpeed }}%</span>
              <button
                @click="adjustTeleprompterSpeed(10)"
                class="btn-v2 btn-v2--glass btn-sm touch-target"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
                </svg>
              </button>
            </div>
          </div>
          
          <div class="p-3 bg-preke-bg-elevated rounded-lg text-sm text-preke-text-muted">
            <p>💡 The teleprompter is displayed on the studio TV.</p>
            <p class="mt-1">Use the speed controls to adjust reading pace.</p>
          </div>
        </div>
      </div>
      
      <!-- Recording Controls -->
      <div class="glass-card">
        <h2 class="text-lg font-semibold mb-3">Recording Controls</h2>
        
        <div v-if="!isRecording" class="text-center">
          <button
            @click="startRecording"
            class="record-button touch-target"
          >
            <div class="record-button-inner">
              <svg class="w-12 h-12" fill="currentColor" viewBox="0 0 20 20">
                <circle cx="10" cy="10" r="8"/>
              </svg>
            </div>
            <span class="mt-3 block text-lg font-semibold">Start Recording</span>
          </button>
        </div>
        
        <div v-else class="text-center">
          <div class="recording-indicator mb-4">
            <div class="recording-dot"></div>
            <span class="text-2xl font-mono font-bold">{{ recordingDuration }}</span>
          </div>
          <button
            @click="stopRecording"
            class="btn-v2 btn-v2--danger w-full touch-target"
          >
            <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <rect x="6" y="6" width="8" height="8" rx="1"/>
            </svg>
            Stop Recording
          </button>
        </div>
      </div>
      
      <!-- Status Bar -->
      <div class="glass-panel p-3 text-sm">
        <div class="flex items-center justify-between text-preke-text-muted">
          <span>Disk Space: {{ status.disk_space_gb.toFixed(1) }} GB</span>
          <span class="flex items-center gap-2">
            <span class="w-2 h-2 rounded-full bg-preke-green"></span>
            Connected
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
@import '@/styles/design-system-v2.css';

.customer-portal {
  min-height: 100vh;
  min-height: 100dvh; /* Dynamic viewport height for mobile */
  background: var(--preke-bg-base);
  position: relative;
  overflow-x: hidden;
  /* Safe area insets for notched phones */
  padding-top: env(safe-area-inset-top);
  padding-bottom: env(safe-area-inset-bottom);
  padding-left: env(safe-area-inset-left);
  padding-right: env(safe-area-inset-right);
}

.portal-bg {
  position: fixed;
  inset: 0;
  pointer-events: none;
}

.bg-orb--1 {
  position: absolute;
  width: 300px;
  height: 300px;
  background: radial-gradient(circle, rgba(224, 160, 48, 0.15) 0%, transparent 70%);
  top: -10%;
  right: -10%;
  filter: blur(80px);
  animation: float 15s ease-in-out infinite;
}

.bg-orb--2 {
  position: absolute;
  width: 250px;
  height: 250px;
  background: radial-gradient(circle, rgba(168, 153, 104, 0.1) 0%, transparent 70%);
  bottom: -10%;
  left: -10%;
  filter: blur(80px);
  animation: float 18s ease-in-out infinite reverse;
}

@keyframes float {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(30px, 40px); }
}

.portal-content {
  position: relative;
  z-index: 1;
  max-width: 600px;
  margin: 0 auto;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.portal-header {
  padding: 1.5rem;
}

.graphic-preview {
  position: relative;
  border-radius: var(--preke-radius-lg);
  overflow: hidden;
  background: var(--preke-bg-elevated);
}

.slide-indicator {
  position: absolute;
  bottom: 0.75rem;
  right: 0.75rem;
  background: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 0.25rem 0.75rem;
  border-radius: var(--preke-radius-md);
  font-size: 0.875rem;
  font-weight: 600;
}

/* Touch-friendly buttons */
.touch-target {
  min-height: 48px;
  min-width: 48px;
}

/* Record Button */
.record-button {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: none;
  border: none;
  cursor: pointer;
  padding: 1.5rem;
  width: 100%;
  color: var(--preke-text-primary);
  transition: transform 0.2s ease;
}

.record-button:active {
  transform: scale(0.95);
}

.record-button-inner {
  width: 120px;
  height: 120px;
  border-radius: 50%;
  background: linear-gradient(145deg, #dc2626, #b91c1c);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  box-shadow: 
    0 4px 20px rgba(220, 38, 38, 0.4),
    inset 0 2px 4px rgba(255, 255, 255, 0.2);
  transition: all 0.3s ease;
}

.record-button:hover .record-button-inner {
  box-shadow: 
    0 6px 30px rgba(220, 38, 38, 0.6),
    inset 0 2px 4px rgba(255, 255, 255, 0.3);
}

/* Recording Indicator */
.recording-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
}

.recording-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--preke-red);
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.2); }
}

/* Responsive adjustments */
@media (max-width: 640px) {
  .portal-content {
    padding: 0.75rem;
  }
  
  .portal-header {
    padding: 1rem;
  }
  
  .record-button-inner {
    width: 100px;
    height: 100px;
  }
}
</style>
