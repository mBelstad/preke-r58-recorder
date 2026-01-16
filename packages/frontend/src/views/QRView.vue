<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { buildApiUrl } from '@/lib/api'

const router = useRouter()

const sessionToken = ref<string | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const qrCodeUrl = ref<string>('')
const customerPortalUrl = ref<string>('')
const studioDisplayUrl = ref<string>('')
const displayMode = ref<string>('')

onMounted(async () => {
  await createSession()
  // Generate QR code after session is created and URL is available
  if (customerPortalUrl.value) {
    generateQRCode()
  }
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
    displayMode.value = data.display_mode || 'podcast'
    
    // Generate URLs
    const baseUrl = window.location.origin
    customerPortalUrl.value = `${baseUrl}/#/customer/${data.token}`
    studioDisplayUrl.value = `${baseUrl}/#/studio-display/${data.token}`
    
    // Generate QR code now that URL is available
    generateQRCode()
    
  } catch (e: any) {
    error.value = e.message || 'Failed to create session'
    console.error('QR session creation error:', e)
  } finally {
    loading.value = false
  }
}

function generateQRCode() {
  if (!customerPortalUrl.value) return
  
  // Use QR code API to generate QR code
  // The QR code should link to the customer portal (phone controls)
  qrCodeUrl.value = `https://api.qrserver.com/v1/create-qr-code/?size=400x400&data=${encodeURIComponent(customerPortalUrl.value)}`
}

function copyCustomerUrl() {
  if (customerPortalUrl.value) {
    navigator.clipboard.writeText(customerPortalUrl.value)
  }
}

function copyDisplayUrl() {
  if (studioDisplayUrl.value) {
    navigator.clipboard.writeText(studioDisplayUrl.value)
  }
}
</script>

<template>
  <div class="qr-view">
    <div class="qr-view__container">
      <!-- Header -->
      <div class="qr-view__header">
        <button
          @click="router.push('/')"
          class="qr-view__back-btn"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
          </svg>
          <span>Back</span>
        </button>
        <h1 class="qr-view__title">QR Code</h1>
      </div>
      
      <!-- Loading State -->
      <div v-if="loading" class="qr-view__loading">
        <div class="animate-spin w-16 h-16 border-4 border-preke-gold border-t-transparent rounded-full mx-auto mb-6"></div>
        <p class="text-xl text-preke-text-dim">Creating session...</p>
      </div>
      
      <!-- Error State -->
      <div v-else-if="error" class="qr-view__error">
        <svg class="w-24 h-24 text-preke-red mx-auto mb-6" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"/>
        </svg>
        <h2 class="text-3xl font-bold mb-4">Failed to Create Session</h2>
        <p class="text-xl text-preke-text-dim">{{ error }}</p>
        <button
          @click="createSession"
          class="mt-6 px-6 py-3 bg-preke-gold text-preke-bg-base rounded-lg font-semibold hover:bg-opacity-90 transition"
        >
          Try Again
        </button>
      </div>
      
      <!-- QR Code Display -->
      <div v-else-if="sessionToken && qrCodeUrl" class="qr-view__content">
        <div class="qr-view__qr-section">
          <h2 class="qr-view__section-title">Scan with Phone</h2>
          <p class="qr-view__section-subtitle">Scan this QR code to get controls on your phone</p>
          
          <div class="qr-view__qr-container">
            <img
              :src="qrCodeUrl"
              alt="QR Code"
              class="qr-view__qr-image"
            />
          </div>
          
          <p class="qr-view__instructions">
            Scan this QR code to get controls on your phone. The TV will display the appropriate mode automatically.
          </p>
        </div>
        
        <!-- Links Section -->
        <div class="qr-view__links">
          <div class="qr-view__link-card">
            <h3 class="qr-view__link-title">Customer Portal (Phone)</h3>
            <p class="qr-view__link-url">{{ customerPortalUrl }}</p>
            <button
              @click="copyCustomerUrl"
              class="qr-view__copy-btn"
            >
              Copy Link
            </button>
          </div>
          
          <div class="qr-view__link-card">
            <h3 class="qr-view__link-title">Studio Display (TV)</h3>
            <p class="qr-view__link-url">{{ studioDisplayUrl }}</p>
            <button
              @click="copyDisplayUrl"
              class="qr-view__copy-btn"
            >
              Copy Link
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.qr-view {
  min-height: 100vh;
  background: var(--preke-bg-base);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
}

.qr-view__container {
  max-width: 1200px;
  width: 100%;
}

.qr-view__header {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 3rem;
}

.qr-view__back-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: var(--preke-bg-elevated);
  border: 1px solid var(--preke-border);
  border-radius: var(--preke-radius-md);
  color: var(--preke-text);
  cursor: pointer;
  transition: all 0.2s ease;
}

.qr-view__back-btn:hover {
  background: var(--preke-glass-bg);
  border-color: var(--preke-border-gold);
  color: var(--preke-gold);
}

.qr-view__title {
  font-size: 2.5rem;
  font-weight: 700;
  color: var(--preke-text);
}

.qr-view__loading,
.qr-view__error {
  text-align: center;
  padding: 4rem 2rem;
}

.qr-view__content {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 3rem;
  align-items: start;
}

.qr-view__qr-section {
  text-align: center;
}

.qr-view__section-title {
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--preke-text);
  margin-bottom: 0.5rem;
}

.qr-view__section-subtitle {
  font-size: 1rem;
  color: var(--preke-text-dim);
  margin-bottom: 2rem;
}

.qr-view__qr-container {
  display: inline-block;
  padding: 2rem;
  background: white;
  border-radius: var(--preke-radius-lg);
  box-shadow: var(--preke-shadow-xl);
  margin-bottom: 1.5rem;
}

.qr-view__qr-image {
  width: 400px;
  height: 400px;
  display: block;
}

.qr-view__instructions {
  font-size: 1rem;
  color: var(--preke-text-dim);
  max-width: 400px;
  margin: 0 auto;
}

.qr-view__instructions strong {
  color: var(--preke-gold);
  font-weight: 600;
}

.qr-view__links {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.qr-view__link-card {
  background: var(--preke-glass-card);
  backdrop-filter: blur(20px) saturate(150%);
  border: 1px solid var(--preke-border-light);
  border-radius: var(--preke-radius-lg);
  padding: 1.5rem;
}

.qr-view__link-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--preke-text);
  margin-bottom: 0.75rem;
}

.qr-view__link-url {
  font-size: 0.75rem;
  color: var(--preke-text-dim);
  word-break: break-all;
  margin-bottom: 1rem;
  font-family: monospace;
}

.qr-view__copy-btn {
  width: 100%;
  padding: 0.75rem;
  background: var(--preke-gold);
  color: var(--preke-bg-base);
  border: none;
  border-radius: var(--preke-radius-md);
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.qr-view__copy-btn:hover {
  background: var(--preke-gold);
  opacity: 0.9;
  transform: translateY(-1px);
}

/* Responsive */
@media (max-width: 1024px) {
  .qr-view__content {
    grid-template-columns: 1fr;
  }
  
  .qr-view__qr-image {
    width: 300px;
    height: 300px;
  }
}

@media (max-width: 640px) {
  .qr-view__title {
    font-size: 1.75rem;
  }
  
  .qr-view__qr-image {
    width: 250px;
    height: 250px;
  }
}
</style>
