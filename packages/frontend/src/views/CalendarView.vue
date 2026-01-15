<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { r58Api } from '@/lib/api'

const calendar = ref<any>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const showBookingModal = ref(false)
const selectedSlot = ref<any>(null)

// Booking form
const bookingForm = ref({
  customer_name: '',
  customer_email: '',
  customer_phone: '',
  duration: 30,
  recording_type: 'podcast'
})

const submitting = ref(false)
const bookingSuccess = ref(false)

let refreshInterval: number | null = null

onMounted(async () => {
  await loadCalendar()
  // Auto-refresh every 60 seconds
  refreshInterval = window.setInterval(loadCalendar, 60000)
})

onUnmounted(() => {
  if (refreshInterval) clearInterval(refreshInterval)
})

async function loadCalendar() {
  try {
    const response = await r58Api.wordpress.getCalendarToday()
    calendar.value = response
    error.value = null
  } catch (e: any) {
    error.value = e.message || 'Failed to load calendar'
  } finally {
    loading.value = false
  }
}

const todayFormatted = computed(() => {
  if (!calendar.value) return ''
  const date = new Date(calendar.value.date)
  return date.toLocaleDateString('en-US', { 
    weekday: 'long', 
    year: 'numeric', 
    month: 'long', 
    day: 'numeric' 
  })
})

function openBookingModal(slot: any) {
  if (!slot.available) return
  selectedSlot.value = slot
  showBookingModal.value = true
  bookingSuccess.value = false
  // Reset form
  bookingForm.value = {
    customer_name: '',
    customer_email: '',
    customer_phone: '',
    duration: 30,
    recording_type: 'podcast'
  }
}

function closeBookingModal() {
  showBookingModal.value = false
  selectedSlot.value = null
}

async function submitBooking() {
  if (!selectedSlot.value) return
  
  submitting.value = true
  error.value = null
  
  try {
    // Calculate end time based on duration
    const startTime = selectedSlot.value.start_time
    const [hours, minutes] = startTime.split(':').map(Number)
    const startDate = new Date()
    startDate.setHours(hours, minutes, 0, 0)
    
    const endDate = new Date(startDate.getTime() + bookingForm.value.duration * 60000)
    const endTime = `${endDate.getHours().toString().padStart(2, '0')}:${endDate.getMinutes().toString().padStart(2, '0')}`
    
    await r58Api.wordpress.createWalkInBooking({
      slot_start: startTime,
      slot_end: endTime,
      customer_name: bookingForm.value.customer_name,
      customer_email: bookingForm.value.customer_email,
      customer_phone: bookingForm.value.customer_phone || undefined,
      recording_type: bookingForm.value.recording_type
    })
    
    bookingSuccess.value = true
    
    // Reload calendar after 2 seconds
    setTimeout(async () => {
      await loadCalendar()
      closeBookingModal()
    }, 2000)
  } catch (e: any) {
    error.value = e.message || 'Failed to create booking'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="calendar-kiosk">
    <!-- Ambient background -->
    <div class="calendar-bg">
      <div class="bg-orb bg-orb--1"></div>
      <div class="bg-orb bg-orb--2"></div>
    </div>
    
    <!-- Header -->
    <header class="calendar-header">
      <div class="flex items-center gap-4">
        <router-link to="/" class="back-btn">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
          </svg>
        </router-link>
        <div>
          <h1 class="text-4xl font-bold">PREKE STUDIO</h1>
          <p class="text-xl text-preke-text-dim mt-1">{{ todayFormatted }}</p>
        </div>
      </div>
    </header>
    
    <!-- Loading State -->
    <div v-if="loading" class="calendar-content">
      <div class="text-center">
        <div class="animate-spin w-16 h-16 border-4 border-preke-gold border-t-transparent rounded-full mx-auto mb-6"></div>
        <p class="text-2xl text-preke-text-dim">Loading schedule...</p>
      </div>
    </div>
    
    <!-- Error State -->
    <div v-else-if="error && !calendar" class="calendar-content">
      <div class="text-center">
        <svg class="w-24 h-24 text-preke-red mx-auto mb-6" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"/>
        </svg>
        <h2 class="text-3xl font-bold mb-4">Failed to Load Schedule</h2>
        <p class="text-xl text-preke-text-dim">{{ error }}</p>
      </div>
    </div>
    
    <!-- Calendar Content -->
    <div v-else-if="calendar" class="calendar-content">
      <div class="slots-container">
        <div
          v-for="slot in calendar.slots"
          :key="slot.start_time"
          class="slot-card"
          :class="{
            'slot-card--available': slot.available,
            'slot-card--booked': slot.booking,
            'slot-card--lunch': slot.is_lunch
          }"
          @click="openBookingModal(slot)"
        >
          <div class="slot-time">{{ slot.start_time }} - {{ slot.end_time }}</div>
          
          <div v-if="slot.is_lunch" class="slot-status">
            <span class="status-badge status-badge--lunch">LUNCH BREAK</span>
          </div>
          
          <div v-else-if="slot.booking" class="slot-status">
            <div class="text-2xl font-bold mb-1">{{ slot.booking.client?.name || slot.booking.customer?.name }}</div>
            <span class="status-badge status-badge--booked">{{ slot.booking.service_name || 'Recording' }}</span>
          </div>
          
          <div v-else class="slot-status">
            <span class="status-badge status-badge--available">AVAILABLE</span>
            <button class="book-btn">Book Now</button>
          </div>
        </div>
      </div>
      
      <!-- Footer instruction -->
      <div class="calendar-footer">
        Tap an available slot to book
      </div>
    </div>
    
    <!-- Booking Modal -->
    <div v-if="showBookingModal" class="modal-overlay" @click.self="closeBookingModal">
      <div class="modal-content">
        <div v-if="bookingSuccess" class="text-center py-12">
          <svg class="w-24 h-24 text-preke-green mx-auto mb-6" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"/>
          </svg>
          <h2 class="text-3xl font-bold mb-2">Booking Confirmed!</h2>
          <p class="text-xl text-preke-text-dim">Your session has been booked</p>
        </div>
        
        <div v-else>
          <h2 class="text-3xl font-bold mb-2">Book Studio Time</h2>
          <p class="text-lg text-preke-text-dim mb-6">
            {{ selectedSlot?.start_time }} - {{ selectedSlot?.end_time }}
          </p>
          
          <form @submit.prevent="submitBooking" class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-preke-text-dim mb-2">Name *</label>
              <input
                v-model="bookingForm.customer_name"
                type="text"
                required
                class="w-full px-4 py-3 bg-preke-bg-elevated border border-preke-border rounded-lg text-lg text-preke-text-primary focus:outline-none focus:ring-2 focus:ring-preke-gold"
                placeholder="Your name"
              />
            </div>
            
            <div>
              <label class="block text-sm font-medium text-preke-text-dim mb-2">Email *</label>
              <input
                v-model="bookingForm.customer_email"
                type="email"
                required
                class="w-full px-4 py-3 bg-preke-bg-elevated border border-preke-border rounded-lg text-lg text-preke-text-primary focus:outline-none focus:ring-2 focus:ring-preke-gold"
                placeholder="your@email.com"
              />
            </div>
            
            <div>
              <label class="block text-sm font-medium text-preke-text-dim mb-2">Phone (optional)</label>
              <input
                v-model="bookingForm.customer_phone"
                type="tel"
                class="w-full px-4 py-3 bg-preke-bg-elevated border border-preke-border rounded-lg text-lg text-preke-text-primary focus:outline-none focus:ring-2 focus:ring-preke-gold"
                placeholder="+47 123 45 678"
              />
            </div>
            
            <div>
              <label class="block text-sm font-medium text-preke-text-dim mb-2">Duration</label>
              <select
                v-model.number="bookingForm.duration"
                class="w-full px-4 py-3 bg-preke-bg-elevated border border-preke-border rounded-lg text-lg text-preke-text-primary focus:outline-none focus:ring-2 focus:ring-preke-gold"
              >
                <option :value="30">30 minutes</option>
                <option :value="60">1 hour</option>
                <option :value="120">2 hours</option>
              </select>
            </div>
            
            <div>
              <label class="block text-sm font-medium text-preke-text-dim mb-2">Recording Type</label>
              <select
                v-model="bookingForm.recording_type"
                class="w-full px-4 py-3 bg-preke-bg-elevated border border-preke-border rounded-lg text-lg text-preke-text-primary focus:outline-none focus:ring-2 focus:ring-preke-gold"
              >
                <option value="podcast">Podcast</option>
                <option value="recording">Talking Head</option>
                <option value="course">Course</option>
                <option value="webinar">Webinar</option>
              </select>
            </div>
            
            <div v-if="error" class="p-3 bg-preke-red/10 border border-preke-red/30 rounded-lg text-preke-red text-sm">
              {{ error }}
            </div>
            
            <div class="flex gap-3 pt-4">
              <button
                type="button"
                @click="closeBookingModal"
                class="flex-1 px-6 py-3 bg-preke-bg-elevated border border-preke-border rounded-lg text-lg font-medium hover:bg-preke-bg-base transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                :disabled="submitting"
                class="flex-1 px-6 py-3 bg-preke-gold text-preke-bg-base rounded-lg text-lg font-bold hover:bg-preke-gold-hover disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {{ submitting ? 'Booking...' : 'Confirm Booking' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
@import '@/styles/design-system-v2.css';

.calendar-kiosk {
  width: 100vw;
  height: 100vh;
  background: var(--preke-bg-base);
  position: relative;
  overflow: hidden;
  color: var(--preke-text-primary);
}

.calendar-bg {
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

.calendar-header {
  position: relative;
  z-index: 1;
  padding: 2rem 3rem;
  background: var(--preke-glass-bg);
  border-bottom: 1px solid var(--preke-border);
  backdrop-filter: blur(20px);
}

.back-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 3rem;
  height: 3rem;
  background: var(--preke-bg-elevated);
  border: 1px solid var(--preke-border);
  border-radius: var(--preke-radius-md);
  color: var(--preke-text-dim);
  transition: all 0.2s ease;
}

.back-btn:hover {
  background: var(--preke-glass-bg);
  border-color: var(--preke-border-gold);
  color: var(--preke-gold);
}

.calendar-content {
  position: relative;
  z-index: 1;
  height: calc(100vh - 120px);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
}

.slots-container {
  width: 100%;
  max-width: 1400px;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 1.5rem;
  overflow-y: auto;
  padding: 2rem;
}

.slot-card {
  background: var(--preke-glass-bg);
  border: 2px solid var(--preke-border);
  border-radius: var(--preke-radius-lg);
  padding: 2rem;
  backdrop-filter: blur(20px);
  transition: all 0.2s ease;
}

.slot-card--available {
  cursor: pointer;
  border-color: var(--preke-border-gold);
}

.slot-card--available:hover {
  transform: translateY(-4px);
  box-shadow: var(--preke-shadow-xl);
  border-color: var(--preke-gold);
}

.slot-card--booked {
  background: var(--preke-bg-elevated);
  opacity: 0.8;
}

.slot-card--lunch {
  background: var(--preke-bg-elevated);
  opacity: 0.6;
}

.slot-time {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--preke-gold);
  margin-bottom: 1rem;
}

.slot-status {
  text-align: center;
}

.status-badge {
  display: inline-block;
  padding: 0.5rem 1rem;
  border-radius: var(--preke-radius-md);
  font-size: 0.875rem;
  font-weight: 700;
  letter-spacing: 0.05em;
}

.status-badge--available {
  background: rgba(34, 197, 94, 0.2);
  color: var(--preke-green);
  border: 1px solid rgba(34, 197, 94, 0.3);
}

.status-badge--booked {
  background: rgba(224, 160, 48, 0.2);
  color: var(--preke-gold);
  border: 1px solid rgba(224, 160, 48, 0.3);
}

.status-badge--lunch {
  background: rgba(168, 153, 104, 0.2);
  color: var(--preke-text-muted);
  border: 1px solid var(--preke-border);
}

.book-btn {
  margin-top: 1rem;
  padding: 0.75rem 2rem;
  background: var(--preke-gold);
  color: var(--preke-bg-base);
  border: none;
  border-radius: var(--preke-radius-md);
  font-size: 1.125rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s ease;
}

.book-btn:hover {
  background: var(--preke-gold-hover);
  transform: scale(1.05);
}

.calendar-footer {
  position: fixed;
  bottom: 2rem;
  left: 50%;
  transform: translateX(-50%);
  padding: 1rem 2rem;
  background: var(--preke-glass-bg);
  border: 1px solid var(--preke-border);
  border-radius: var(--preke-radius-lg);
  backdrop-filter: blur(20px);
  font-size: 1.125rem;
  color: var(--preke-text-dim);
  z-index: 10;
}

/* Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  padding: 2rem;
}

.modal-content {
  background: var(--preke-bg-base);
  border: 1px solid var(--preke-border);
  border-radius: var(--preke-radius-xl);
  padding: 3rem;
  max-width: 600px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: var(--preke-shadow-2xl);
}
</style>
