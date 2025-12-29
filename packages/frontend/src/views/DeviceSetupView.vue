<script setup lang="ts">
/**
 * Device Setup View
 * 
 * First-run screen for configuring R58 device connections.
 * Only shown in Electron when no device is configured.
 */
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { isElectron, setDeviceUrl } from '@/lib/api'

interface DeviceConfig {
  id: string
  name: string
  url: string
  lastConnected?: string
  createdAt: string
}

const router = useRouter()

// State
const devices = ref<DeviceConfig[]>([])
const activeDeviceId = ref<string | null>(null)
const isLoading = ref(false)
const isTesting = ref(false)
const testResult = ref<{ success: boolean; message: string } | null>(null)

// Form state
const showAddForm = ref(false)
const newDeviceName = ref('')
const newDeviceUrl = ref('')
const formError = ref('')

// Edit state
const editingDevice = ref<DeviceConfig | null>(null)

// Computed
const hasDevices = computed(() => devices.value.length > 0)
const activeDevice = computed(() => 
  devices.value.find(d => d.id === activeDeviceId.value)
)

// Check if we're in Electron
const inElectron = computed(() => isElectron())

/**
 * Load devices from Electron store
 */
async function loadDevices() {
  if (!window.electronAPI) return
  
  try {
    devices.value = await window.electronAPI.getDevices()
    const active = await window.electronAPI.getActiveDevice()
    activeDeviceId.value = active?.id || null
  } catch (error) {
    console.error('Failed to load devices:', error)
  }
}

/**
 * Test connection to a device URL
 */
async function testConnection(url: string): Promise<{ success: boolean; message: string }> {
  isTesting.value = true
  testResult.value = null
  
  try {
    // Normalize URL
    const normalizedUrl = url.replace(/\/+$/, '')
    
    // Try to hit the health endpoint
    const response = await fetch(`${normalizedUrl}/api/v1/health`, {
      method: 'GET',
      headers: { 'Accept': 'application/json' },
      signal: AbortSignal.timeout(10000),
    })
    
    if (response.ok) {
      const data = await response.json()
      return {
        success: true,
        message: `Connected! Status: ${data.status || 'OK'}`
      }
    } else {
      return {
        success: false,
        message: `HTTP ${response.status}: ${response.statusText}`
      }
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Connection failed'
    return {
      success: false,
      message: message.includes('timeout') ? 'Connection timed out' : message
    }
  } finally {
    isTesting.value = false
  }
}

/**
 * Add a new device
 */
async function addDevice() {
  if (!window.electronAPI) return
  
  formError.value = ''
  
  // Validate
  if (!newDeviceUrl.value.trim()) {
    formError.value = 'Device URL is required'
    return
  }
  
  // Validate URL format
  try {
    new URL(newDeviceUrl.value)
  } catch {
    formError.value = 'Invalid URL format. Use http:// or https://'
    return
  }
  
  isLoading.value = true
  
  try {
    // Test connection first
    const result = await testConnection(newDeviceUrl.value)
    testResult.value = result
    
    if (!result.success) {
      formError.value = 'Connection test failed. Device may be offline or URL incorrect.'
      // Still allow adding even if test fails - user might be configuring for later
    }
    
    // Add the device
    const device = await window.electronAPI.addDevice(
      newDeviceName.value.trim() || 'Preke Device',
      newDeviceUrl.value.trim()
    )
    
    // Refresh list
    await loadDevices()
    
    // If this is the first device, activate it
    if (devices.value.length === 1) {
      await selectDevice(device.id)
    }
    
    // Reset form
    newDeviceName.value = ''
    newDeviceUrl.value = ''
    showAddForm.value = false
    testResult.value = null
    
  } catch (error) {
    console.error('Failed to add device:', error)
    formError.value = 'Failed to save device configuration'
  } finally {
    isLoading.value = false
  }
}

/**
 * Remove a device
 */
async function removeDevice(deviceId: string) {
  if (!window.electronAPI) return
  
  if (!confirm('Remove this device?')) return
  
  try {
    await window.electronAPI.removeDevice(deviceId)
    await loadDevices()
  } catch (error) {
    console.error('Failed to remove device:', error)
  }
}

/**
 * Select and connect to a device
 */
async function selectDevice(deviceId: string) {
  if (!window.electronAPI) return
  
  isLoading.value = true
  
  try {
    await window.electronAPI.setActiveDevice(deviceId)
    activeDeviceId.value = deviceId
    
    // Update the API client
    const device = devices.value.find(d => d.id === deviceId)
    if (device) {
      setDeviceUrl(device.url)
    }
    
    // Navigate to home
    router.push('/')
    
  } catch (error) {
    console.error('Failed to select device:', error)
  } finally {
    isLoading.value = false
  }
}

/**
 * Start editing a device
 */
function startEdit(device: DeviceConfig) {
  editingDevice.value = { ...device }
}

/**
 * Save device edits
 */
async function saveEdit() {
  if (!window.electronAPI || !editingDevice.value) return
  
  try {
    await window.electronAPI.updateDevice(editingDevice.value.id, {
      name: editingDevice.value.name,
      url: editingDevice.value.url,
    })
    await loadDevices()
    editingDevice.value = null
  } catch (error) {
    console.error('Failed to update device:', error)
  }
}

/**
 * Cancel editing
 */
function cancelEdit() {
  editingDevice.value = null
}

/**
 * Go back to main app
 */
function goBack() {
  if (activeDevice.value) {
    router.push('/')
  }
}

// Load devices on mount
onMounted(() => {
  loadDevices()
})
</script>

<template>
  <div class="device-setup">
    <!-- Background with subtle pattern -->
    <div class="device-setup__bg">
      <div class="device-setup__gradient" />
      <div class="device-setup__pattern" />
    </div>
    
    <div class="device-setup__content">
      <div class="device-setup__card" :class="{ 'device-setup__card--wide': hasDevices }">
        <!-- Header with Logo -->
        <header class="device-setup__header">
          <!-- Preke Logo (white version for dark background) -->
          <div class="device-setup__logo-container">
            <img src="/logo-white.svg" alt="Preke" class="device-setup__logo" />
          </div>
          
          <!-- Tagline -->
          <p class="device-setup__tagline">
            Professional Recording & Live Production
          </p>
          
          <!-- Divider with audio waveform accent -->
          <div class="device-setup__divider">
            <span class="device-setup__divider-line" />
            <svg class="device-setup__waveform" viewBox="0 0 80 24" fill="none">
              <rect x="4" y="8" width="2" height="8" rx="1" fill="currentColor" opacity="0.4"/>
              <rect x="10" y="6" width="2" height="12" rx="1" fill="currentColor" opacity="0.6"/>
              <rect x="16" y="4" width="2" height="16" rx="1" fill="currentColor" opacity="0.8"/>
              <rect x="22" y="2" width="2" height="20" rx="1" fill="currentColor"/>
              <rect x="28" y="4" width="2" height="16" rx="1" fill="currentColor" opacity="0.8"/>
              <rect x="34" y="6" width="2" height="12" rx="1" fill="currentColor" opacity="0.6"/>
              <rect x="40" y="4" width="2" height="16" rx="1" fill="currentColor" opacity="0.8"/>
              <rect x="46" y="2" width="2" height="20" rx="1" fill="currentColor"/>
              <rect x="52" y="4" width="2" height="16" rx="1" fill="currentColor" opacity="0.8"/>
              <rect x="58" y="6" width="2" height="12" rx="1" fill="currentColor" opacity="0.6"/>
              <rect x="64" y="4" width="2" height="16" rx="1" fill="currentColor" opacity="0.8"/>
              <rect x="70" y="8" width="2" height="8" rx="1" fill="currentColor" opacity="0.4"/>
            </svg>
            <span class="device-setup__divider-line" />
          </div>
          
          <!-- Status text -->
          <h2 class="device-setup__status">
            {{ hasDevices ? 'Your Devices' : 'Welcome to Preke Studio' }}
          </h2>
          <p class="device-setup__subtitle" v-if="!hasDevices">
            Connect to your first device to get started
          </p>
        </header>

        <!-- Device List -->
        <div v-if="hasDevices && !showAddForm" class="device-setup__devices">
          <TransitionGroup name="device-list">
            <div 
              v-for="device in devices" 
              :key="device.id"
              class="device-setup__device"
              :class="{ 'device-setup__device--active': device.id === activeDeviceId }"
            >
              <!-- Edit Mode -->
              <div v-if="editingDevice?.id === device.id" class="device-setup__device-edit">
                <input 
                  v-model="editingDevice.name"
                  type="text"
                  placeholder="Device name"
                  class="device-setup__input"
                />
                <input 
                  v-model="editingDevice.url"
                  type="url"
                  placeholder="Device URL"
                  class="device-setup__input"
                />
                <div class="device-setup__device-edit-actions">
                  <button @click="saveEdit" class="device-setup__btn device-setup__btn--primary device-setup__btn--sm">
                    Save
                  </button>
                  <button @click="cancelEdit" class="device-setup__btn device-setup__btn--ghost device-setup__btn--sm">
                    Cancel
                  </button>
                </div>
              </div>

              <!-- View Mode -->
              <div v-else class="device-setup__device-view">
                <div class="device-setup__device-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <rect x="2" y="3" width="20" height="14" rx="2" />
                    <path d="M8 21h8M12 17v4" />
                  </svg>
                </div>
                <div class="device-setup__device-info">
                  <div class="device-setup__device-header">
                    <h3 class="device-setup__device-name">{{ device.name }}</h3>
                    <span v-if="device.id === activeDeviceId" class="device-setup__badge device-setup__badge--active">
                      Connected
                    </span>
                  </div>
                  <p class="device-setup__device-url">{{ device.url }}</p>
                  <p v-if="device.lastConnected" class="device-setup__device-meta">
                    Last connected {{ new Date(device.lastConnected).toLocaleDateString() }}
                  </p>
                </div>
                <div class="device-setup__device-actions">
                  <button 
                    v-if="device.id !== activeDeviceId"
                    @click="selectDevice(device.id)"
                    :disabled="isLoading"
                    class="device-setup__btn device-setup__btn--primary"
                  >
                    <span>Connect</span>
                    <svg class="device-setup__btn-icon" viewBox="0 0 20 20" fill="currentColor">
                      <path fill-rule="evenodd" d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z" clip-rule="evenodd" />
                    </svg>
                  </button>
                  <button 
                    v-else
                    @click="goBack"
                    class="device-setup__btn device-setup__btn--success"
                  >
                    <span>Open Studio</span>
                    <svg class="device-setup__btn-icon" viewBox="0 0 20 20" fill="currentColor">
                      <path fill-rule="evenodd" d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z" clip-rule="evenodd" />
                    </svg>
                  </button>
                  <button 
                    @click="startEdit(device)"
                    class="device-setup__icon-btn"
                    title="Edit device"
                  >
                    <svg viewBox="0 0 20 20" fill="currentColor">
                      <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
                    </svg>
                  </button>
                  <button 
                    @click="removeDevice(device.id)"
                    class="device-setup__icon-btn device-setup__icon-btn--danger"
                    title="Remove device"
                  >
                    <svg viewBox="0 0 20 20" fill="currentColor">
                      <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          </TransitionGroup>
        </div>

        <!-- Add Device Form -->
        <div v-if="showAddForm || !hasDevices" class="device-setup__form">
          <h3 class="device-setup__form-title">
            {{ hasDevices ? 'Add New Device' : 'Connect Your Device' }}
          </h3>
          
          <div class="device-setup__form-fields">
            <div class="device-setup__field">
              <label class="device-setup__label">
                Device Name
                <span class="device-setup__label-hint">(optional)</span>
              </label>
              <input 
                v-model="newDeviceName"
                type="text"
                placeholder="e.g., Studio Recorder, Church System"
                class="device-setup__input"
              />
            </div>
            
            <div class="device-setup__field">
              <label class="device-setup__label">
                Device URL
                <span class="device-setup__label-required">*</span>
              </label>
              <input 
                v-model="newDeviceUrl"
                type="url"
                placeholder="https://r58-api.itagenten.no"
                class="device-setup__input"
                :class="{ 'device-setup__input--error': formError }"
              />
              <p v-if="formError" class="device-setup__error">{{ formError }}</p>
              <p class="device-setup__hint">
                Enter the full URL to your Preke device API
              </p>
            </div>

            <!-- Test Result -->
            <Transition name="fade">
              <div 
                v-if="testResult"
                class="device-setup__result"
                :class="testResult.success ? 'device-setup__result--success' : 'device-setup__result--error'"
              >
                <svg v-if="testResult.success" class="device-setup__result-icon" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                </svg>
                <svg v-else class="device-setup__result-icon" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
                </svg>
                <span>{{ testResult.message }}</span>
              </div>
            </Transition>
          </div>

          <div class="device-setup__form-actions">
            <button 
              @click="addDevice"
              :disabled="isLoading || isTesting"
              class="device-setup__btn device-setup__btn--primary device-setup__btn--lg"
            >
              <svg v-if="isLoading || isTesting" class="device-setup__spinner" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none" />
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              <span>{{ isTesting ? 'Testing Connection...' : 'Connect Device' }}</span>
            </button>
            
            <button 
              v-if="hasDevices"
              @click="showAddForm = false; testResult = null; formError = ''"
              class="device-setup__btn device-setup__btn--ghost"
            >
              Cancel
            </button>
          </div>
        </div>

        <!-- Add Another Device Button -->
        <div v-if="hasDevices && !showAddForm" class="device-setup__footer">
          <button 
            @click="showAddForm = true"
            class="device-setup__add-btn"
          >
            <svg viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clip-rule="evenodd" />
            </svg>
            Add Another Device
          </button>
        </div>

        <!-- Not in Electron Warning -->
        <Transition name="fade">
          <div v-if="!inElectron" class="device-setup__warning">
            <svg viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
            </svg>
            <p>
              Device management is only available in the <strong>Preke Studio</strong> desktop app.
              In the web version, the device is configured automatically.
            </p>
          </div>
        </Transition>
        
        <!-- Version footer -->
        <footer class="device-setup__version">
          <span>Preke Studio</span>
          <span class="device-setup__version-sep">•</span>
          <span>Desktop v2.0</span>
        </footer>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Design Tokens */
:root {
  --preke-gold: #d9981e;
  --preke-gold-light: #f5c842;
  --preke-dark: #0a0e17;
  --preke-card: #111827;
  --preke-border: #1f2937;
  --preke-text: #f9fafb;
  --preke-text-muted: #9ca3af;
  --preke-text-dim: #6b7280;
  --preke-blue: #3b82f6;
  --preke-green: #10b981;
  --preke-red: #ef4444;
}

/* Container */
.device-setup {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  position: relative;
  overflow: hidden;
}

/* Background */
.device-setup__bg {
  position: absolute;
  inset: 0;
  z-index: 0;
}

.device-setup__gradient {
  position: absolute;
  inset: 0;
  background: 
    radial-gradient(ellipse 80% 50% at 50% -20%, rgba(59, 130, 246, 0.15), transparent),
    radial-gradient(ellipse 60% 40% at 80% 100%, rgba(217, 152, 30, 0.1), transparent),
    linear-gradient(180deg, #0a0e17 0%, #111827 100%);
}

.device-setup__pattern {
  position: absolute;
  inset: 0;
  opacity: 0.03;
  background-image: 
    linear-gradient(rgba(255,255,255,0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.05) 1px, transparent 1px);
  background-size: 32px 32px;
}

/* Content */
.device-setup__content {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 480px;
  animation: fadeInUp 0.6s ease-out;
}

.device-setup__card--wide {
  max-width: 600px;
}

.device-setup__card {
  background: linear-gradient(180deg, rgba(17, 24, 39, 0.9) 0%, rgba(17, 24, 39, 0.95) 100%);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 24px;
  padding: 2.5rem;
  box-shadow: 
    0 25px 50px -12px rgba(0, 0, 0, 0.5),
    0 0 0 1px rgba(255, 255, 255, 0.05) inset;
}

/* Header */
.device-setup__header {
  text-align: center;
  margin-bottom: 2rem;
}

.device-setup__logo-container {
  display: flex;
  justify-content: center;
  margin-bottom: 1rem;
}

.device-setup__logo {
  height: 48px;
  width: auto;
  filter: brightness(1.1);
}

.device-setup__tagline {
  font-size: 0.875rem;
  color: var(--preke-text-muted);
  letter-spacing: 0.05em;
  margin-bottom: 1.5rem;
}

.device-setup__divider {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.device-setup__divider-line {
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent);
}

.device-setup__waveform {
  width: 80px;
  height: 24px;
  color: var(--preke-gold);
  animation: pulse 2s ease-in-out infinite;
}

.device-setup__status {
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--preke-text);
  margin-bottom: 0.5rem;
}

.device-setup__subtitle {
  font-size: 0.9375rem;
  color: var(--preke-text-muted);
}

/* Devices List */
.device-setup__devices {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}

.device-setup__device {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 16px;
  padding: 1rem 1.25rem;
  transition: all 0.2s ease;
}

.device-setup__device:hover {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.1);
}

.device-setup__device--active {
  border-color: var(--preke-gold);
  background: rgba(217, 152, 30, 0.08);
}

.device-setup__device-view {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.device-setup__device-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.05);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.device-setup__device-icon svg {
  width: 24px;
  height: 24px;
  color: var(--preke-text-muted);
}

.device-setup__device--active .device-setup__device-icon {
  background: rgba(217, 152, 30, 0.2);
}

.device-setup__device--active .device-setup__device-icon svg {
  color: var(--preke-gold);
}

.device-setup__device-info {
  flex: 1;
  min-width: 0;
}

.device-setup__device-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.device-setup__device-name {
  font-size: 0.9375rem;
  font-weight: 500;
  color: var(--preke-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.device-setup__device-url {
  font-size: 0.8125rem;
  color: var(--preke-text-dim);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-top: 0.125rem;
}

.device-setup__device-meta {
  font-size: 0.75rem;
  color: var(--preke-text-dim);
  margin-top: 0.25rem;
}

.device-setup__badge {
  padding: 0.125rem 0.5rem;
  border-radius: 9999px;
  font-size: 0.6875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.device-setup__badge--active {
  background: rgba(16, 185, 129, 0.2);
  color: var(--preke-green);
}

.device-setup__device-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-shrink: 0;
}

.device-setup__device-edit {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.device-setup__device-edit-actions {
  display: flex;
  gap: 0.5rem;
}

/* Buttons */
.device-setup__btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.625rem 1rem;
  font-size: 0.875rem;
  font-weight: 500;
  border-radius: 10px;
  border: none;
  cursor: pointer;
  transition: all 0.15s ease;
  white-space: nowrap;
}

.device-setup__btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.device-setup__btn--primary {
  background: var(--preke-blue);
  color: white;
}

.device-setup__btn--primary:hover:not(:disabled) {
  background: #2563eb;
  transform: translateY(-1px);
}

.device-setup__btn--success {
  background: var(--preke-green);
  color: white;
}

.device-setup__btn--success:hover:not(:disabled) {
  background: #059669;
}

.device-setup__btn--ghost {
  background: transparent;
  color: var(--preke-text-muted);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.device-setup__btn--ghost:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.05);
  color: var(--preke-text);
}

.device-setup__btn--sm {
  padding: 0.5rem 0.875rem;
  font-size: 0.8125rem;
}

.device-setup__btn--lg {
  padding: 0.875rem 1.5rem;
  font-size: 0.9375rem;
  width: 100%;
}

.device-setup__btn-icon {
  width: 16px;
  height: 16px;
}

.device-setup__icon-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  border: none;
  background: transparent;
  color: var(--preke-text-dim);
  cursor: pointer;
  transition: all 0.15s ease;
}

.device-setup__icon-btn:hover {
  background: rgba(255, 255, 255, 0.08);
  color: var(--preke-text);
}

.device-setup__icon-btn--danger:hover {
  background: rgba(239, 68, 68, 0.15);
  color: var(--preke-red);
}

.device-setup__icon-btn svg {
  width: 18px;
  height: 18px;
}

/* Form */
.device-setup__form {
  margin-bottom: 1rem;
}

.device-setup__form-title {
  font-size: 1.0625rem;
  font-weight: 500;
  color: var(--preke-text);
  margin-bottom: 1.25rem;
  text-align: center;
}

.device-setup__form-fields {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.device-setup__field {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.device-setup__label {
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--preke-text);
}

.device-setup__label-hint {
  color: var(--preke-text-dim);
  font-weight: 400;
}

.device-setup__label-required {
  color: var(--preke-gold);
}

.device-setup__input {
  width: 100%;
  padding: 0.75rem 1rem;
  font-size: 0.9375rem;
  color: var(--preke-text);
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  outline: none;
  transition: all 0.15s ease;
}

.device-setup__input::placeholder {
  color: var(--preke-text-dim);
}

.device-setup__input:focus {
  border-color: var(--preke-blue);
  background: rgba(255, 255, 255, 0.08);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
}

.device-setup__input--error {
  border-color: var(--preke-red);
}

.device-setup__input--error:focus {
  box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.15);
}

.device-setup__error {
  font-size: 0.8125rem;
  color: var(--preke-red);
}

.device-setup__hint {
  font-size: 0.75rem;
  color: var(--preke-text-dim);
}

.device-setup__result {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  padding: 0.75rem 1rem;
  border-radius: 10px;
  font-size: 0.875rem;
}

.device-setup__result--success {
  background: rgba(16, 185, 129, 0.1);
  color: var(--preke-green);
}

.device-setup__result--error {
  background: rgba(239, 68, 68, 0.1);
  color: var(--preke-red);
}

.device-setup__result-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

.device-setup__form-actions {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.device-setup__spinner {
  width: 20px;
  height: 20px;
  animation: spin 1s linear infinite;
}

/* Footer */
.device-setup__footer {
  text-align: center;
  padding-top: 0.5rem;
}

.device-setup__add-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 1rem;
  font-size: 0.875rem;
  color: var(--preke-text-muted);
  background: transparent;
  border: 1px dashed rgba(255, 255, 255, 0.15);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.device-setup__add-btn:hover {
  color: var(--preke-text);
  border-color: var(--preke-gold);
  background: rgba(217, 152, 30, 0.05);
}

.device-setup__add-btn svg {
  width: 16px;
  height: 16px;
}

/* Warning */
.device-setup__warning {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 1rem;
  margin-top: 1.5rem;
  background: rgba(245, 158, 11, 0.1);
  border: 1px solid rgba(245, 158, 11, 0.2);
  border-radius: 12px;
  font-size: 0.8125rem;
  color: #fbbf24;
}

.device-setup__warning svg {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  margin-top: 0.125rem;
}

.device-setup__warning strong {
  color: #fcd34d;
}

/* Version */
.device-setup__version {
  display: flex;
  justify-content: center;
  gap: 0.5rem;
  margin-top: 2rem;
  padding-top: 1.5rem;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  font-size: 0.75rem;
  color: var(--preke-text-dim);
}

.device-setup__version-sep {
  opacity: 0.5;
}

/* Animations */
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.6;
  }
}

/* Transitions */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.device-list-enter-active,
.device-list-leave-active {
  transition: all 0.3s ease;
}

.device-list-enter-from {
  opacity: 0;
  transform: translateX(-20px);
}

.device-list-leave-to {
  opacity: 0;
  transform: translateX(20px);
}

.device-list-move {
  transition: transform 0.3s ease;
}

/* Responsive */
@media (max-width: 480px) {
  .device-setup {
    padding: 1rem;
  }
  
  .device-setup__card {
    padding: 1.5rem;
    border-radius: 20px;
  }
  
  .device-setup__device-actions {
    flex-wrap: wrap;
  }
}
</style>
