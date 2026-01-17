<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { buildApiUrl } from '@/lib/api'
import StudioDisplayShell from '@/components/shared/StudioDisplayShell.vue'

const sessionToken = ref<string | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const qrCodeUrl = ref<string>('')
const customerPortalUrl = ref<string>('')

onMounted(async () => {
  await createSession()
})

async function createSession() {
  loading.value = true
  error.value = null
  
  try {
    // Create a temporary session for this QR code
    // Display mode will be determined by active booking (if exists) or default to podcast
    const response = await fetch(await buildApiUrl('/api/v1/wordpress/qr-session'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({})
    })
    
    if (!response.ok) {
      throw new Error('Failed to create QR session')
    }
    
    const data = await response.json()
    sessionToken.value = data.token
    
    // Generate customer portal URL for QR code
    const baseUrl = window.location.origin
    customerPortalUrl.value = `${baseUrl}/#/customer/${data.token}`
    
    // Generate QR code - larger size for TV display
    qrCodeUrl.value = `https://api.qrserver.com/v1/create-qr-code/?size=600x600&data=${encodeURIComponent(customerPortalUrl.value)}`
    
  } catch (e: any) {
    error.value = e.message || 'Failed to create session'
    console.error('QR session creation error:', e)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <StudioDisplayShell
    title="Scan to Start"
    subtitle="Your session begins on your phone"
    accent="gold"
    :show-footer="true"
    main-class="qr-view__main"
  >
    <template #header-right>
      <div class="qr-view__status" :class="{ 'qr-view__status--error': !!error }">
        <span class="qr-view__status-dot"></span>
        {{ error ? 'Session unavailable' : 'Ready for scan' }}
      </div>
    </template>

    <div class="qr-view__content">
      <!-- Loading State -->
      <div v-if="loading" class="qr-view__loading glass-card">
        <div class="qr-view__spinner"></div>
        <p class="qr-view__loading-text">Preparing your session...</p>
      </div>

      <!-- Error State -->
      <div v-else-if="error" class="qr-view__error glass-card">
        <div class="qr-view__error-icon">!</div>
        <h2 class="qr-view__error-title">Unable to Load</h2>
        <p class="qr-view__error-message">Please refresh the page or contact staff</p>
      </div>

      <!-- QR Code Display -->
      <div v-else-if="sessionToken && qrCodeUrl" class="qr-view__grid">
        <div class="qr-view__qr glass-card">
          <img
            :src="qrCodeUrl"
            alt="QR Code - Scan with your phone"
            class="qr-view__qr-image"
          />
          <p class="qr-view__qr-caption">Open your phone camera and scan</p>
        </div>
        <div class="qr-view__steps glass-card">
          <h2 class="qr-view__steps-title">Start your booked session</h2>
          <ol class="qr-view__steps-list">
            <li>Scan the QR code with your phone</li>
            <li>Confirm your booking details</li>
            <li>Use the mobile controls to begin</li>
          </ol>
        </div>
      </div>
    </div>

    <template #footer>
      <div class="qr-view__footer-left">
        <span class="qr-view__footer-label">Session link</span>
        <span class="qr-view__footer-url">{{ customerPortalUrl || 'Generating secure link...' }}</span>
      </div>
      <div class="qr-view__footer-right">
        Need help? Ask the studio technician.
      </div>
    </template>
  </StudioDisplayShell>
</template>

<style scoped>
@import '@/styles/design-system-v2.css';

.qr-view__main {
  align-items: stretch;
}

.qr-view__content {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.qr-view__status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  color: var(--preke-text-muted);
}

.qr-view__status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--preke-green);
  box-shadow: 0 0 12px rgba(109, 181, 109, 0.4);
}

.qr-view__status--error .qr-view__status-dot {
  background: var(--preke-red);
  box-shadow: 0 0 12px rgba(212, 90, 90, 0.4);
}

.qr-view__loading,
.qr-view__error {
  width: min(620px, 90%);
  text-align: center;
  padding: 3rem;
}

.qr-view__spinner {
  width: 80px;
  height: 80px;
  border: 6px solid var(--preke-border);
  border-top-color: var(--preke-gold);
  border-radius: 50%;
  margin: 0 auto 2rem;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.qr-view__loading-text {
  font-size: 1.5rem;
  color: var(--preke-text-dim);
  font-weight: 500;
}

.qr-view__error-icon {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  margin: 0 auto 1.5rem;
  background: var(--preke-red-bg);
  color: var(--preke-red);
  font-size: 3rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}

.qr-view__error-title {
  font-size: 2.25rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
}

.qr-view__error-message {
  font-size: 1.25rem;
  color: var(--preke-text-dim);
}

.qr-view__grid {
  width: 100%;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 2rem;
  align-items: center;
}

.qr-view__qr {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1.5rem;
  padding: 2.5rem;
}

.qr-view__qr-image {
  width: clamp(320px, 30vw, 520px);
  height: clamp(320px, 30vw, 520px);
  border-radius: 16px;
  background: #ffffff;
  padding: 1rem;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.35);
}

.qr-view__qr-caption {
  font-size: 1.125rem;
  color: var(--preke-text-dim);
}

.qr-view__steps {
  padding: 2.5rem 3rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.qr-view__steps-title {
  font-size: 2rem;
  font-weight: 700;
}

.qr-view__steps-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 1rem;
  font-size: 1.25rem;
  color: var(--preke-text-dim);
}

.qr-view__steps-list li::before {
  content: '•';
  color: var(--preke-gold);
  font-weight: 700;
  margin-right: 0.75rem;
}

.qr-view__footer-left {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  min-width: 0;
}

.qr-view__footer-label {
  text-transform: uppercase;
  font-size: 0.75rem;
  letter-spacing: 0.2em;
}

.qr-view__footer-url {
  color: var(--preke-text-dim);
  font-size: 0.9rem;
  max-width: 520px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.qr-view__footer-right {
  text-align: right;
  color: var(--preke-text-muted);
}

@media (max-width: 1100px) {
  .qr-view__grid {
    grid-template-columns: 1fr;
  }

  .qr-view__footer-url {
    max-width: 320px;
  }
}
</style>
