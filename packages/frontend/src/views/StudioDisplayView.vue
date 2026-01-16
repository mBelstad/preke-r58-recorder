<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { r58Api } from '@/lib/api'
import PodcastDisplay from './studio-display/PodcastDisplay.vue'
import TeleprompterDisplay from './studio-display/TeleprompterDisplay.vue'
import WebinarDisplay from './studio-display/WebinarDisplay.vue'

const route = useRoute()
const token = computed(() => route.params.token as string | undefined)

// Check if this is a direct-access mode page (no token)
const isDirectAccess = computed(() => !token.value)

// Determine display mode from route if direct access
const routeMode = computed(() => {
  if (isDirectAccess.value) {
    const routeName = route.name as string
    if (routeName === 'podcast-display') return 'podcast'
    if (routeName === 'talking-head-display') return 'teleprompter'
    if (routeName === 'course-display') return 'course'
    if (routeName === 'webinar-display') return 'webinar'
  }
  return null
})

const status = ref<any>(null)
const loading = ref(true)
const error = ref<string | null>(null)

let statusInterval: number | null = null

onMounted(async () => {
  if (isDirectAccess.value) {
    // Direct access mode - create mock status
    console.log('[StudioDisplay] Direct access mode, route:', route.name, 'mode:', routeMode.value)
    createMockStatus()
  } else {
    // Token-based mode - load from API
    console.log('[StudioDisplay] Token-based mode, token:', token.value)
    await loadStatus()
    statusInterval = window.setInterval(loadStatus, 2000)
  }
})

onUnmounted(() => {
  if (statusInterval) clearInterval(statusInterval)
})

function createMockStatus() {
  // Create mock status for preview mode
  const mode = routeMode.value || 'podcast'
  console.log('[StudioDisplay] Creating mock status for mode:', mode)
  status.value = {
    booking: {
      id: 0,
      date: new Date().toISOString().split('T')[0],
      slot_start: '10:00',
      slot_end: '11:00',
      customer: { name: 'Preview Mode', email: 'preview@preke.no' }
    },
    project: {
      id: 0,
      name: 'Preview Session',
      slug: 'preview',
      graphics: []
    },
    recording_active: false,
    recording_duration_ms: 0,
    current_slide_index: 0,
    display_mode: mode,
    disk_space_gb: 100.0 // Mock disk space for preview mode
  }
  loading.value = false
  console.log('[StudioDisplay] Mock status created:', status.value)
}

async function loadStatus() {
  if (!token.value) return
  
  try {
    const response = await r58Api.wordpress.getCustomerStatus(token.value)
    status.value = response
    error.value = null
  } catch (e: any) {
    if (loading.value) {
      error.value = e.message || 'Invalid session'
    }
  } finally {
    loading.value = false
  }
}

const displayMode = computed(() => {
  if (isDirectAccess.value) {
    return routeMode.value || 'podcast'
  }
  return status.value?.display_mode || 'podcast'
})
</script>

<template>
  <div class="studio-display">
    <!-- Ambient background -->
    <div class="display-bg">
      <div class="bg-orb bg-orb--1"></div>
      <div class="bg-orb bg-orb--2"></div>
    </div>
    
    <!-- Loading State -->
    <div v-if="loading" class="display-content">
      <div class="text-center">
        <div class="animate-spin w-16 h-16 border-4 border-preke-gold border-t-transparent rounded-full mx-auto mb-6"></div>
        <p class="text-2xl text-preke-text-dim">Loading session...</p>
      </div>
    </div>
    
    <!-- Error State -->
    <div v-else-if="error" class="display-content">
      <div class="text-center">
        <svg class="w-24 h-24 text-preke-red mx-auto mb-6" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"/>
        </svg>
        <h2 class="text-3xl font-bold mb-4">Session Not Found</h2>
        <p class="text-xl text-preke-text-dim">{{ error }}</p>
      </div>
    </div>
    
    <!-- Display Mode Router -->
    <div v-else-if="status" class="display-content">
      <PodcastDisplay v-if="displayMode === 'podcast' || displayMode === 'course'" :status="status" />
      <TeleprompterDisplay v-else-if="displayMode === 'teleprompter'" :status="status" />
      <WebinarDisplay v-else-if="displayMode === 'webinar'" :status="status" />
      <div v-else class="text-center">
        <p class="text-2xl text-preke-text-dim">Unknown display mode: {{ displayMode }}</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
@import '@/styles/design-system-v2.css';

.studio-display {
  width: 100vw;
  height: 100vh;
  background: var(--preke-bg-base);
  position: relative;
  overflow: hidden;
  color: var(--preke-text-primary);
}

.display-bg {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;
}

.bg-orb--1 {
  position: absolute;
  width: 600px;
  height: 600px;
  background: radial-gradient(circle, rgba(224, 160, 48, 0.12) 0%, transparent 70%);
  top: -15%;
  right: -10%;
  filter: blur(120px);
  animation: float 20s ease-in-out infinite;
}

.bg-orb--2 {
  position: absolute;
  width: 500px;
  height: 500px;
  background: radial-gradient(circle, rgba(168, 153, 104, 0.08) 0%, transparent 70%);
  bottom: -10%;
  left: -10%;
  filter: blur(120px);
  animation: float 25s ease-in-out infinite reverse;
}

@keyframes float {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(50px, 60px); }
}

.display-content {
  position: relative;
  z-index: 1;
  height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
</style>
