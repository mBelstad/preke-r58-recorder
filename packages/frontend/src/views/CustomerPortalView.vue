<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, defineAsyncComponent } from 'vue'
import { useRoute } from 'vue-router'
import { r58Api } from '@/lib/api'
import CustomerPortalShell from '@/components/customer-portal/CustomerPortalShell.vue'

// Lazy load portal components
const PodcastPortal = defineAsyncComponent(() => import('@/components/customer-portal/PodcastPortal.vue'))
const TalkingHeadPortal = defineAsyncComponent(() => import('@/components/customer-portal/TalkingHeadPortal.vue'))
const WebinarPortal = defineAsyncComponent(() => import('@/components/customer-portal/WebinarPortal.vue'))

const route = useRoute()
const token = computed(() => route.params.token as string)

const status = ref<any>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const currentSlideIndex = ref(0)
const isRecording = ref(false)
const displayMode = ref<string>('podcast')
const teleprompterSpeed = ref<number>(50)
const teleprompterScript = ref<string>('')

let statusInterval: number | null = null

onMounted(async () => {
  await loadStatus()
  // Poll status every 2 seconds
  statusInterval = window.setInterval(loadStatus, 2000)
  
  // Switch TV display when portal loads
  // We do this after initial loadStatus to ensure we have the correct mode
  if (status.value && !error.value) {
    activateSession()
  }
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
    teleprompterScript.value = response.teleprompter_script || ''
    error.value = null
  } catch (e: any) {
    if (loading.value) {
      error.value = e.message || 'Invalid or expired link'
    }
  } finally {
    loading.value = false
  }
}

async function activateSession() {
  try {
    // Activate session and switch TV display via API
    await r58Api.wordpress.activateSession(token.value)
  } catch (e) {
    console.error('Failed to activate session:', e)
  }
}

async function startRecording() {
  try {
    await r58Api.wordpress.customerStartRecording(token.value)
    isRecording.value = true
    if ('vibrate' in navigator) navigator.vibrate(50)
  } catch (e: any) {
    alert(e.message || 'Failed to start recording')
  }
}

async function stopRecording() {
  if (!confirm('Stop recording?')) return
  try {
    await r58Api.wordpress.customerStopRecording(token.value)
    isRecording.value = false
    if ('vibrate' in navigator) navigator.vibrate([50, 100, 50])
  } catch (e: any) {
    alert(e.message || 'Failed to stop recording')
  }
}

async function gotoSlide(index: number) {
  try {
    await r58Api.wordpress.customerGotoSlide(token.value, index)
    currentSlideIndex.value = index
    if ('vibrate' in navigator) navigator.vibrate(30)
  } catch (e: any) {
    console.error('Failed to change slide:', e)
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

async function updateSpeed(speed: number) {
  teleprompterSpeed.value = speed
  try {
    await r58Api.wordpress.setTeleprompterSpeed(token.value, speed)
  } catch (e) {
    console.error('Failed to set speed:', e)
  }
}

async function updateScript(script: string) {
  teleprompterScript.value = script
  // API call is handled inside TalkingHeadPortal for now
}
</script>

<template>
  <div class="customer-portal-view">
    <!-- Loading State -->
    <div v-if="loading" class="flex h-screen items-center justify-center bg-preke-bg-base text-preke-text-dim">
      <div class="text-center">
        <div class="animate-spin w-12 h-12 border-4 border-preke-gold border-t-transparent rounded-full mx-auto mb-4"></div>
        <p>Loading your session...</p>
      </div>
    </div>
    
    <!-- Error State -->
    <div v-else-if="error" class="flex h-screen items-center justify-center bg-preke-bg-base text-preke-text-dim p-4">
      <div class="glass-card text-center max-w-md w-full p-8">
        <svg class="w-16 h-16 text-preke-red mx-auto mb-4" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"/>
        </svg>
        <h2 class="text-xl font-bold mb-2">Session Not Found</h2>
        <p>{{ error }}</p>
      </div>
    </div>
    
    <!-- Main Content -->
    <CustomerPortalShell 
      v-else-if="status" 
      :status="status" 
      :is-recording="isRecording"
    >
      <!-- Podcast Mode -->
      <PodcastPortal
        v-if="displayMode === 'podcast'"
        :status="status"
        :current-slide-index="currentSlideIndex"
        :is-recording="isRecording"
        @start-recording="startRecording"
        @stop-recording="stopRecording"
        @prev-slide="prevSlide"
        @next-slide="nextSlide"
      />
      
      <!-- Talking Head / Course Mode -->
      <TalkingHeadPortal
        v-else-if="displayMode === 'teleprompter' || displayMode === 'course'"
        :token="token"
        :status="status"
        :current-slide-index="currentSlideIndex"
        :is-recording="isRecording"
        :teleprompter-speed="teleprompterSpeed"
        :teleprompter-script="teleprompterScript"
        @start-recording="startRecording"
        @stop-recording="stopRecording"
        @prev-slide="prevSlide"
        @next-slide="nextSlide"
        @update-speed="updateSpeed"
        @update-script="updateScript"
      />
      
      <!-- Webinar Mode -->
      <WebinarPortal
        v-else-if="displayMode === 'webinar'"
        :token="token"
        :status="status"
        :current-slide-index="currentSlideIndex"
        :is-recording="isRecording"
        @prev-slide="prevSlide"
        @next-slide="nextSlide"
      />
      
      <!-- Unknown Mode Fallback -->
      <div v-else class="text-center p-8 glass-card">
        <p class="text-preke-text-muted">Unknown display mode: {{ displayMode }}</p>
      </div>
    </CustomerPortalShell>
  </div>
</template>

<style scoped>
@import '@/styles/design-system-v2.css';
</style>
