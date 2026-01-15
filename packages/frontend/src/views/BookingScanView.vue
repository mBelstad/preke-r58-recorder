<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const manualId = ref('')
const scanning = ref(false)
const error = ref<string | null>(null)

// QR Scanner would use a library like html5-qrcode or @zxing/browser
// For now, providing manual entry fallback

async function startScanning() {
  scanning.value = true
  error.value = null
  
  // TODO: Implement actual QR scanning using device camera
  // For now, just show manual entry
  console.log('QR scanning would start here')
}

function stopScanning() {
  scanning.value = false
}

function goToBooking() {
  if (!manualId.value.trim()) {
    error.value = 'Please enter a booking ID'
    return
  }
  
  const appointmentId = parseInt(manualId.value.trim())
  if (isNaN(appointmentId)) {
    error.value = 'Invalid booking ID'
    return
  }
  
  router.push({ name: 'booking-detail', params: { appointmentId } })
}
</script>

<template>
  <div class="min-h-screen bg-preke-bg-base flex items-center justify-center p-4">
    <div class="glass-card max-w-md w-full">
      <button
        @click="router.push('/')"
        class="btn-v2 btn-v2--ghost mb-4"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
        </svg>
        <span class="ml-2">Back</span>
      </button>
      
      <div class="text-center mb-8">
        <h1 class="text-2xl font-bold mb-2">Scan Booking QR Code</h1>
        <p class="text-preke-text-dim">Scan the QR code from the booking confirmation</p>
      </div>
      
      <!-- QR Scanner Area -->
      <div v-if="!scanning" class="space-y-4">
        <button
          @click="startScanning"
          class="btn-v2 btn-v2--primary w-full btn-lg"
        >
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
              d="M12 4v1m6 11h2m-6 0h-2v4m0-11v3m0 0h.01M12 12h4.01M16 20h4M4 12h4m12 0h.01M5 8h2a1 1 0 001-1V5a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1zm12 0h2a1 1 0 001-1V5a1 1 0 00-1-1h-2a1 1 0 00-1 1v2a1 1 0 001 1zM5 20h2a1 1 0 001-1v-2a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1z"/>
          </svg>
          <span class="ml-2">Start QR Scanner</span>
        </button>
        
        <div class="divider-v2"><span>Or enter manually</span></div>
        
        <div class="form-group">
          <label for="booking-id">Booking ID</label>
          <input
            id="booking-id"
            v-model="manualId"
            type="text"
            placeholder="Enter booking ID..."
            class="input-v2 w-full"
            @keyup.enter="goToBooking"
          />
        </div>
        
        <button
          @click="goToBooking"
          :disabled="!manualId.trim()"
          class="btn-v2 btn-v2--glass w-full"
        >
          Go to Booking
        </button>
        
        <p v-if="error" class="text-red-400 text-sm text-center">
          {{ error }}
        </p>
      </div>
      
      <!-- Scanning State -->
      <div v-else class="space-y-4">
        <div class="bg-preke-bg-elevated rounded-lg p-8 text-center">
          <div class="w-48 h-48 mx-auto mb-4 border-4 border-preke-gold rounded-lg relative">
            <div class="absolute inset-0 flex items-center justify-center">
              <svg class="w-16 h-16 text-preke-gold animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                  d="M12 4v1m6 11h2m-6 0h-2v4m0-11v3m0 0h.01M12 12h4.01M16 20h4M4 12h4m12 0h.01M5 8h2a1 1 0 001-1V5a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1zm12 0h2a1 1 0 001-1V5a1 1 0 00-1-1h-2a1 1 0 00-1 1v2a1 1 0 001 1zM5 20h2a1 1 0 001-1v-2a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1z"/>
              </svg>
            </div>
            <!-- Scanning line animation -->
            <div class="absolute inset-x-0 top-0 h-1 bg-preke-gold animate-scan"></div>
          </div>
          <p class="text-preke-text-dim">Position QR code within the frame</p>
        </div>
        
        <button
          @click="stopScanning"
          class="btn-v2 btn-v2--ghost w-full"
        >
          Cancel
        </button>
      </div>
      
      <!-- Back button -->
      <button
        @click="router.back()"
        class="btn-v2 btn-v2--ghost w-full mt-4"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
        </svg>
        <span class="ml-2">Back</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
@import '@/styles/design-system-v2.css';

@keyframes scan {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(192px); }
}

.animate-scan {
  animation: scan 2s ease-in-out infinite;
}
</style>
