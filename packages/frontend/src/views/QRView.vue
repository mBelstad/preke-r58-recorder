<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { buildApiUrl } from '@/lib/api'

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
  <div class="qr-view">
    <!-- Loading State -->
    <div v-if="loading" class="qr-view__loading">
      <div class="qr-view__spinner"></div>
      <p class="qr-view__loading-text">Preparing your session...</p>
    </div>
    
    <!-- Error State -->
    <div v-else-if="error" class="qr-view__error">
      <svg class="qr-view__error-icon" fill="currentColor" viewBox="0 0 20 20">
        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"/>
      </svg>
      <h2 class="qr-view__error-title">Unable to Load</h2>
      <p class="qr-view__error-message">Please refresh the page</p>
    </div>
    
    <!-- QR Code Display -->
    <div v-else-if="sessionToken && qrCodeUrl" class="qr-view__content">
      <div class="qr-view__welcome">
        <h1 class="qr-view__welcome-title">Welcome</h1>
        <p class="qr-view__welcome-subtitle">Scan the QR code with your phone to get started</p>
      </div>
      
      <div class="qr-view__qr-container">
        <img
          :src="qrCodeUrl"
          alt="QR Code - Scan with your phone"
          class="qr-view__qr-image"
        />
      </div>
      
      <p class="qr-view__instructions">
        Point your phone camera at the QR code to access controls and information
      </p>
    </div>
  </div>
</template>

<style scoped>
.qr-view {
  width: 100%;
  height: 100%;
  min-height: 100vh;
  background: linear-gradient(135deg, var(--preke-bg-base) 0%, var(--preke-bg-elevated) 100%);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  padding: 6rem 2rem 4rem;
  text-align: center;
  box-sizing: border-box;
  overflow-y: auto;
  overflow-x: hidden;
  position: relative;
}

/* Loading State */
.qr-view__loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2rem;
}

.qr-view__spinner {
  width: 80px;
  height: 80px;
  border: 6px solid var(--preke-border);
  border-top-color: var(--preke-gold);
  border-radius: 50%;
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

/* Error State */
.qr-view__error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1.5rem;
}

.qr-view__error-icon {
  width: 96px;
  height: 96px;
  color: var(--preke-red);
}

.qr-view__error-title {
  font-size: 2.5rem;
  font-weight: 700;
  color: var(--preke-text);
}

.qr-view__error-message {
  font-size: 1.25rem;
  color: var(--preke-text-dim);
}

/* Content */
.qr-view__content {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  gap: 3rem;
  max-width: 800px;
  width: 100%;
  margin: 0 auto;
  padding-top: 2rem;
}

.qr-view__welcome {
  margin-bottom: 0;
  padding-top: 0;
}

.qr-view__welcome-title {
  font-size: 3.5rem;
  font-weight: 700;
  color: var(--preke-text);
  margin-bottom: 1rem;
  letter-spacing: -0.02em;
  line-height: 1.1;
}

.qr-view__welcome-subtitle {
  font-size: 1.5rem;
  color: var(--preke-text-dim);
  font-weight: 400;
}

.qr-view__qr-container {
  padding: 2.5rem;
  background: white;
  border-radius: 24px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  display: inline-block;
}

.qr-view__qr-image {
  width: 600px;
  height: 600px;
  display: block;
  border-radius: 8px;
}

.qr-view__instructions {
  font-size: 1.25rem;
  color: var(--preke-text-dim);
  font-weight: 400;
  max-width: 600px;
  line-height: 1.6;
}

/* Responsive for smaller screens */
@media (max-width: 1024px) {
  .qr-view__welcome-title {
    font-size: 3rem;
  }
  
  .qr-view__welcome-subtitle {
    font-size: 1.25rem;
  }
  
  .qr-view__qr-image {
    width: 500px;
    height: 500px;
  }
  
  .qr-view__instructions {
    font-size: 1.125rem;
  }
}

@media (max-width: 768px) {
  .qr-view {
    padding: 2rem 1rem;
  }
  
  .qr-view__welcome-title {
    font-size: 2.5rem;
  }
  
  .qr-view__welcome-subtitle {
    font-size: 1.125rem;
  }
  
  .qr-view__qr-container {
    padding: 1.5rem;
  }
  
  .qr-view__qr-image {
    width: 400px;
    height: 400px;
  }
  
  .qr-view__instructions {
    font-size: 1rem;
  }
}

@media (max-width: 480px) {
  .qr-view__welcome-title {
    font-size: 2rem;
  }
  
  .qr-view__qr-image {
    width: 300px;
    height: 300px;
  }
}
</style>
