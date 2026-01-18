<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  status: any
  isRecording?: boolean
}>()

const recordingDuration = computed(() => {
  if (!props.status?.recording_duration_ms) return '00:00'
  const seconds = Math.floor(props.status.recording_duration_ms / 1000)
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
})

const timeRemaining = computed(() => {
  if (!props.status?.booking) return null
  const now = new Date()
  const endTime = new Date(`${props.status.booking.date} ${props.status.booking.slot_end}`)
  const diff = endTime.getTime() - now.getTime()
  if (diff <= 0) return 'Time expired'
  
  const hours = Math.floor(diff / (1000 * 60 * 60))
  const mins = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60))
  
  if (hours > 0) {
    return `${hours}h ${mins}m left`
  }
  return `${mins}m left`
})
</script>

<template>
  <div class="customer-portal">
    <!-- Ambient background -->
    <div class="portal-bg">
      <div class="bg-orb bg-orb--1"></div>
      <div class="bg-orb bg-orb--2"></div>
    </div>
    
    <div class="portal-content">
      <!-- Header -->
      <header class="portal-header glass-card">
        <div class="flex items-center gap-4">
          <img 
            v-if="status.booking.client?.logo_url" 
            :src="status.booking.client.logo_url" 
            alt="Logo" 
            class="w-16 h-16 object-contain rounded-lg bg-preke-bg-elevated p-2" 
          />
          <div class="flex-1 min-w-0">
            <h1 class="text-xl font-bold truncate">Welcome, {{ status.booking.customer?.name || 'Guest' }}</h1>
            <p class="text-preke-text-dim text-sm truncate">{{ status.booking.client?.name }}</p>
          </div>
        </div>
        
        <div class="mt-4 flex items-center justify-between text-sm">
          <div class="flex flex-col">
            <span class="text-preke-text-muted">{{ status.booking.date }}</span>
            <span class="font-mono text-preke-text-dim">{{ status.booking.slot_start }} - {{ status.booking.slot_end }}</span>
          </div>
          
          <div class="flex flex-col items-end gap-1">
            <span class="badge-v2 badge-v2--success" v-if="isRecording">
              REC {{ recordingDuration }}
            </span>
            <span class="text-preke-amber font-mono font-medium" v-if="timeRemaining">
              {{ timeRemaining }}
            </span>
          </div>
        </div>
      </header>
      
      <!-- Main Content Slot -->
      <main class="portal-main">
        <slot />
      </main>
      
      <!-- Footer -->
      <footer class="mt-8 text-center space-y-4 pb-8">
        <a 
          href="https://preke.no/wp-login.php" 
          target="_blank" 
          class="inline-flex items-center gap-2 text-preke-text-dim hover:text-preke-gold transition-colors text-sm"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1" />
          </svg>
          Login to Customer Portal
        </a>
        
        <div class="glass-panel p-3 text-xs text-preke-text-muted">
          <div class="flex items-center justify-between">
            <span>Disk Space: {{ status.disk_space_gb?.toFixed(1) || '0.0' }} GB</span>
            <span class="flex items-center gap-2">
              <span class="w-2 h-2 rounded-full bg-preke-green"></span>
              Connected
            </span>
          </div>
        </div>
      </footer>
    </div>
  </div>
</template>

<style scoped>
@import '@/styles/design-system-v2.css';

.customer-portal {
  min-height: 100vh;
  min-height: 100dvh;
  background: var(--preke-bg-base);
  position: relative;
  overflow-x: hidden;
  padding-top: env(safe-area-inset-top);
  padding-bottom: env(safe-area-inset-bottom);
  padding-left: env(safe-area-inset-left);
  padding-right: env(safe-area-inset-right);
}

.portal-bg {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;
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
  gap: 1.5rem;
}

.portal-header {
  padding: 1.25rem;
}

.portal-main {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

/* Responsive adjustments */
@media (max-width: 640px) {
  .portal-content {
    padding: 0.75rem;
    gap: 1rem;
  }
  
  .portal-header {
    padding: 1rem;
  }
  
  .portal-main {
    gap: 1rem;
  }
}
</style>
