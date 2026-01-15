<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { r58Api } from '@/lib/api'

const route = useRoute()
const router = useRouter()

const appointmentId = computed(() => parseInt(route.params.appointmentId as string))
const booking = ref<any>(null)
const graphics = ref<any[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const activating = ref(false)
const completing = ref(false)
const isActive = ref(false)
const accessToken = ref<string>('')
const displayMode = ref<string>('podcast')
const teleprompterScript = ref<string>('')
const teleprompterSpeed = ref<number>(50)
const savingScript = ref(false)
const savingSpeed = ref(false)

onMounted(async () => {
  await loadBooking()
})

async function loadBooking() {
  loading.value = true
  error.value = null
  
  try {
    const response = await r58Api.wordpress.getAppointment(appointmentId.value)
    booking.value = response.booking
    graphics.value = response.graphics || []
    
    // Check if this booking is currently active
    const current = await r58Api.wordpress.getCurrentBooking()
    if (current.active && current.booking?.id === appointmentId.value) {
      isActive.value = true
      // Extract token from message if available
      const tokenMatch = current.booking?.message?.match(/Access token: (\S+)/)
      if (tokenMatch) {
        accessToken.value = tokenMatch[1]
        
        // Load display mode and teleprompter settings
        try {
          const status = await r58Api.wordpress.getCustomerStatus(tokenMatch[1])
          displayMode.value = status.display_mode || 'podcast'
          teleprompterScript.value = status.teleprompter_script || ''
          teleprompterSpeed.value = status.teleprompter_scroll_speed || 50
        } catch (e) {
          console.error('Failed to load display mode:', e)
        }
      }
    }
  } catch (e: any) {
    error.value = e.message || 'Failed to load booking'
  } finally {
    loading.value = false
  }
}

async function activateBooking() {
  activating.value = true
  error.value = null
  
  try {
    const response = await r58Api.wordpress.activateBooking(appointmentId.value, true)
    isActive.value = true
    
    // Extract token from response message
    const tokenMatch = response.message.match(/Access token: (\S+)/)
    if (tokenMatch) {
      accessToken.value = tokenMatch[1]
    }
    
    await loadBooking()
  } catch (e: any) {
    error.value = e.message || 'Failed to activate booking'
  } finally {
    activating.value = false
  }
}

async function completeBooking() {
  if (!confirm('Complete this booking and upload recordings?')) return
  
  completing.value = true
  error.value = null
  
  try {
    await r58Api.wordpress.completeBooking(appointmentId.value, true)
    isActive.value = false
    accessToken.value = ''
    await loadBooking()
  } catch (e: any) {
    error.value = e.message || 'Failed to complete booking'
  } finally {
    completing.value = false
  }
}

const customerPortalUrl = computed(() => {
  if (!accessToken.value) return ''
  const baseUrl = window.location.origin
  return `${baseUrl}/#/customer/${accessToken.value}`
})

const studioDisplayUrl = computed(() => {
  if (!accessToken.value) return ''
  const baseUrl = window.location.origin
  return `${baseUrl}/#/studio-display/${accessToken.value}`
})

function copyToClipboard(text: string) {
  navigator.clipboard.writeText(text)
}

async function saveTeleprompterScript() {
  if (!accessToken.value) return
  
  savingScript.value = true
  try {
    await r58Api.wordpress.updateTeleprompterScript(accessToken.value, teleprompterScript.value)
  } catch (e: any) {
    error.value = e.message || 'Failed to save script'
  } finally {
    savingScript.value = false
  }
}

async function saveTeleprompterSpeed() {
  if (!accessToken.value) return
  
  savingSpeed.value = true
  try {
    await r58Api.wordpress.setTeleprompterSpeed(accessToken.value, teleprompterSpeed.value)
  } catch (e: any) {
    error.value = e.message || 'Failed to save speed'
  } finally {
    savingSpeed.value = false
  }
}
</script>

<template>
  <div class="min-h-screen bg-preke-bg-base p-4">
    <!-- Header -->
    <div class="max-w-6xl mx-auto mb-6">
      <button
        @click="router.back()"
        class="btn-v2 btn-v2--ghost mb-4"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
        </svg>
        <span class="ml-2">Back</span>
      </button>
      
      <h1 class="text-3xl font-bold">Booking Details</h1>
    </div>
    
    <!-- Loading State -->
    <div v-if="loading" class="max-w-6xl mx-auto">
      <div class="glass-card text-center py-12">
        <div class="animate-spin w-8 h-8 border-4 border-preke-gold border-t-transparent rounded-full mx-auto mb-4"></div>
        <p class="text-preke-text-dim">Loading booking...</p>
      </div>
    </div>
    
    <!-- Error State -->
    <div v-else-if="error" class="max-w-6xl mx-auto">
      <div class="alert-v2 alert-v2--danger">
        <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"/>
        </svg>
        {{ error }}
      </div>
    </div>
    
    <!-- Booking Content -->
    <div v-else-if="booking" class="max-w-6xl mx-auto space-y-6">
      <!-- Status Badge -->
      <div class="flex items-center gap-4">
        <span v-if="isActive" class="badge-v2 badge-v2--success">Active Session</span>
        <span v-else class="badge-v2 badge-v2--info">{{ booking.status }}</span>
      </div>
      
      <!-- Main Info Card -->
      <div class="glass-card">
        <div class="flex items-start gap-6">
          <!-- Client Logo -->
          <div v-if="booking.client?.logo_url" class="flex-shrink-0">
            <img :src="booking.client.logo_url" :alt="booking.client.name" class="w-24 h-24 object-contain rounded-lg bg-preke-bg-elevated p-2" />
          </div>
          
          <div class="flex-1">
            <h2 class="text-2xl font-bold mb-2">{{ booking.client?.name || 'Unknown Client' }}</h2>
            
            <div class="grid grid-cols-2 gap-4 mt-4">
              <div>
                <p class="text-preke-text-subtle text-sm">Date</p>
                <p class="text-preke-text-primary font-medium">{{ booking.date }}</p>
              </div>
              <div>
                <p class="text-preke-text-subtle text-sm">Time</p>
                <p class="text-preke-text-primary font-medium">{{ booking.slot_start }} - {{ booking.slot_end }}</p>
              </div>
              <div v-if="booking.customer">
                <p class="text-preke-text-subtle text-sm">Customer</p>
                <p class="text-preke-text-primary font-medium">{{ booking.customer.name }}</p>
                <p v-if="booking.customer.email" class="text-preke-text-muted text-sm">{{ booking.customer.email }}</p>
              </div>
              <div v-if="booking.service_name">
                <p class="text-preke-text-subtle text-sm">Service</p>
                <p class="text-preke-text-primary font-medium">{{ booking.service_name }}</p>
              </div>
            </div>
            
            <p v-if="booking.notes" class="mt-4 text-preke-text-dim">
              <strong>Notes:</strong> {{ booking.notes }}
            </p>
          </div>
        </div>
      </div>
      
      <!-- Graphics Preview -->
      <div v-if="graphics.length > 0" class="glass-card">
        <h3 class="text-xl font-semibold mb-4">Project Graphics ({{ graphics.length }})</h3>
        <div class="grid grid-cols-3 gap-4">
          <div v-for="graphic in graphics" :key="graphic.id" class="relative group">
            <img :src="graphic.url" :alt="graphic.filename" class="w-full h-32 object-cover rounded-lg" />
            <div class="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity rounded-lg flex items-center justify-center">
              <p class="text-white text-sm px-2 text-center">{{ graphic.filename }}</p>
            </div>
          </div>
        </div>
      </div>
      
      <!-- QR Codes for Customer/Display (when active) -->
      <div v-if="isActive && accessToken" class="glass-card">
        <h3 class="text-xl font-semibold mb-4">Access Links</h3>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <p class="text-preke-text-dim text-sm mb-2">Customer Portal (Phone)</p>
            <div class="bg-preke-bg-elevated p-4 rounded-lg">
              <p class="text-xs text-preke-text-muted mb-2 break-all">{{ customerPortalUrl }}</p>
              <button @click="copyToClipboard(customerPortalUrl)" class="btn-v2 btn-v2--glass btn-sm w-full">
                Copy Link
              </button>
            </div>
          </div>
          <div>
            <p class="text-preke-text-dim text-sm mb-2">Studio Display (TV)</p>
            <div class="bg-preke-bg-elevated p-4 rounded-lg">
              <p class="text-xs text-preke-text-muted mb-2 break-all">{{ studioDisplayUrl }}</p>
              <button @click="copyToClipboard(studioDisplayUrl)" class="btn-v2 btn-v2--glass btn-sm w-full">
                Copy Link
              </button>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Display Mode Controls (when active) -->
      <div v-if="isActive && accessToken" class="glass-card">
        <h3 class="text-xl font-semibold mb-4">Display Mode: {{ displayMode }}</h3>
        
        <!-- Teleprompter Controls -->
        <div v-if="displayMode === 'teleprompter'" class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-preke-text-dim mb-2">Teleprompter Script</label>
            <textarea
              v-model="teleprompterScript"
              rows="8"
              class="w-full px-4 py-3 bg-preke-bg-elevated border border-preke-border rounded-lg text-preke-text-primary focus:outline-none focus:ring-2 focus:ring-preke-gold resize-none"
              placeholder="Enter script text here..."
            ></textarea>
            <button
              @click="saveTeleprompterScript"
              :disabled="savingScript"
              class="btn-v2 btn-v2--primary mt-2"
            >
              <span v-if="savingScript">Saving...</span>
              <span v-else>Save Script</span>
            </button>
          </div>
          
          <div>
            <label class="block text-sm font-medium text-preke-text-dim mb-2">
              Scroll Speed: {{ teleprompterSpeed }}%
            </label>
            <div class="flex items-center gap-4">
              <input
                v-model.number="teleprompterSpeed"
                type="range"
                min="1"
                max="100"
                class="flex-1"
              />
              <button
                @click="saveTeleprompterSpeed"
                :disabled="savingSpeed"
                class="btn-v2 btn-v2--glass btn-sm"
              >
                <span v-if="savingSpeed">Saving...</span>
                <span v-else>Save</span>
              </button>
            </div>
          </div>
        </div>
        
        <!-- Webinar Controls -->
        <div v-else-if="displayMode === 'webinar'" class="space-y-4">
          <div class="alert-v2 alert-v2--info">
            <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"/>
            </svg>
            <div>
              <p class="font-medium">Webinar Mode Active</p>
              <p class="text-sm text-preke-text-muted">VDO.ninja is running at vdo.itagenten.no</p>
              <p class="text-sm text-preke-text-muted mt-1">Layout controls are available on the customer portal and studio display.</p>
            </div>
          </div>
        </div>
        
        <!-- Podcast Mode Info -->
        <div v-else-if="displayMode === 'podcast'" class="alert-v2 alert-v2--info">
          <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"/>
          </svg>
          <div>
            <p class="font-medium">Podcast Mode Active</p>
            <p class="text-sm text-preke-text-muted">Multi-camera setup with presentation graphics.</p>
          </div>
        </div>
      </div>
      
      <!-- Actions -->
      <div class="glass-card">
        <div class="flex gap-4">
          <button
            v-if="!isActive"
            @click="activateBooking"
            :disabled="activating"
            class="btn-v2 btn-v2--primary flex-1"
          >
            <span v-if="activating" class="flex items-center justify-center gap-2">
              <span class="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"></span>
              Activating...
            </span>
            <span v-else>Activate Booking</span>
          </button>
          
          <button
            v-if="isActive"
            @click="completeBooking"
            :disabled="completing"
            class="btn-v2 btn-v2--success flex-1"
          >
            <span v-if="completing" class="flex items-center justify-center gap-2">
              <span class="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"></span>
              Completing...
            </span>
            <span v-else>Complete & Upload</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
@import '@/styles/design-system-v2.css';
</style>
