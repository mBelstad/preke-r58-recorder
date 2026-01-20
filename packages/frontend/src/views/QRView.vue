<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { buildApiUrl } from '@/lib/api'
import StudioDisplayShell from '@/components/shared/StudioDisplayShell.vue'

const sessionToken = ref<string | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const qrCodeUrl = ref<string>('')
const customerPortalUrl = ref<string>('')

// Public URL for QR codes - must be accessible from phones scanning the QR code
// When running on the R58 device (localhost), we need to use the public FRP URL
// Note: Vue app uses hash router, so format is https://domain/#/route
const PUBLIC_BASE_URL = 'https://app.itagenten.no'

onMounted(async () => {
  await createSession()
})

/**
 * Get the public base URL for the customer portal
 * - If running on localhost (R58 kiosk), use the public FRP URL
 * - Otherwise use the current origin (for remote access)
 */
function getPublicBaseUrl(): string {
  const origin = window.location.origin
  
  // Check if running on localhost (R58 device kiosk mode)
  if (origin.includes('localhost') || origin.includes('127.0.0.1')) {
    return PUBLIC_BASE_URL
  }
  
  // If already on the public URL, use it
  return origin
}

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
    
    // Generate customer portal URL for QR code using PUBLIC URL
    // This must be accessible from phones, not localhost!
    const baseUrl = getPublicBaseUrl()
    customerPortalUrl.value = `${baseUrl}#/customer/${data.token}`
    
    // Debug: Log the URL being used (check browser console)
    console.log('[QR] Window origin:', window.location.origin)
    console.log('[QR] Public base URL:', baseUrl)
    console.log('[QR] Customer portal URL:', customerPortalUrl.value)
    
    // Generate QR code - larger size for TV display
    // Add cache-busting timestamp to force QR code regeneration
    const timestamp = Date.now()
    qrCodeUrl.value = `https://api.qrserver.com/v1/create-qr-code/?size=600x600&data=${encodeURIComponent(customerPortalUrl.value)}&t=${timestamp}`
    
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
    title="Welcome to Preke Studio"
    subtitle="Your professional recording experience starts here"
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
      <div v-else-if="sessionToken && qrCodeUrl" class="qr-view__welcome-layout">
        <div class="qr-view__welcome-section">
          <h1 class="qr-view__welcome-title">Welcome</h1>
          <p class="qr-view__welcome-tagline">Scan to begin your professional recording session</p>
        </div>
        
        <div class="qr-view__qr-container glass-card qr-view__fade-in">
          <img
            :src="qrCodeUrl"
            alt="QR Code - Scan with your phone"
            class="qr-view__qr-image"
          />
        </div>
        
        <div class="qr-view__instructions glass-card qr-view__fade-in">
          <h2 class="qr-view__instructions-title">Get Started</h2>
          <ol class="qr-view__instructions-list">
            <li>Open your phone camera</li>
            <li>Point it at the QR code above</li>
          </ol>
          <p class="qr-view__instructions-note">Your session controls will appear on your phone</p>
        </div>
      </div>
    </div>

    <template #footer>
      <div class="qr-view__footer-content">
        <span class="qr-view__footer-text">Need help? Ask the studio technician.</span>
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

.qr-view__welcome-layout {
  width: 100%;
  max-width: 1200px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3rem;
  padding: 2rem 0;
}

.qr-view__welcome-section {
  text-align: center;
  animation: fadeInUp 0.8s ease-out;
}

.qr-view__welcome-title {
  font-size: clamp(3rem, 6vw, 5rem);
  font-weight: 700;
  color: var(--preke-text-primary);
  margin-bottom: 1rem;
  letter-spacing: -0.02em;
  background: linear-gradient(135deg, var(--preke-text-primary) 0%, var(--preke-gold) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.qr-view__welcome-tagline {
  font-size: clamp(1.25rem, 2vw, 1.75rem);
  color: var(--preke-text-dim);
  font-weight: 400;
}

.qr-view__qr-container {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2.5rem;
  animation-delay: 0.2s;
}

.qr-view__qr-image {
  width: clamp(400px, 35vw, 600px);
  height: clamp(400px, 35vw, 600px);
  border-radius: 20px;
  background: #ffffff;
  padding: 1.5rem;
  box-shadow: 0 25px 80px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(224, 160, 48, 0.1);
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.qr-view__qr-image:hover {
  transform: scale(1.02);
  box-shadow: 0 30px 100px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(224, 160, 48, 0.2);
}

.qr-view__instructions {
  padding: 2.5rem 3rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  text-align: center;
  max-width: 600px;
  animation-delay: 0.4s;
}

.qr-view__instructions-title {
  font-size: 2rem;
  font-weight: 700;
  color: var(--preke-text-primary);
}

.qr-view__instructions-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  font-size: 1.5rem;
  color: var(--preke-text-dim);
  counter-reset: step-counter;
}

.qr-view__instructions-list li {
  counter-increment: step-counter;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
}

.qr-view__instructions-list li::before {
  content: counter(step-counter);
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 50%;
  background: var(--preke-gold);
  color: var(--preke-bg-base);
  font-weight: 700;
  font-size: 1.25rem;
  flex-shrink: 0;
}

.qr-view__instructions-note {
  margin-top: 0.5rem;
  font-size: 1.125rem;
  color: var(--preke-text-muted);
  font-style: italic;
}

.qr-view__fade-in {
  animation: fadeInUp 0.8s ease-out both;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.qr-view__footer-content {
  width: 100%;
  text-align: center;
}

.qr-view__footer-text {
  color: var(--preke-text-muted);
  font-size: 1rem;
}

@media (max-width: 1100px) {
  .qr-view__welcome-layout {
    gap: 2rem;
    padding: 1rem 0;
  }

  .qr-view__qr-image {
    width: clamp(300px, 50vw, 500px);
    height: clamp(300px, 50vw, 500px);
  }

  .qr-view__instructions {
    padding: 2rem;
  }
}
</style>
