<script setup lang="ts">
/**
 * Device Setup View
 * 
 * First-run screen for configuring device connections.
 * Professional branded experience for Preke Studio.
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
    const normalizedUrl = url.replace(/\/+$/, '')
    const response = await fetch(`${normalizedUrl}/api/v1/health`, {
      method: 'GET',
      headers: { 'Accept': 'application/json' },
      signal: AbortSignal.timeout(10000),
    })
    
    if (response.ok) {
      const data = await response.json()
      return { success: true, message: `Connected! Status: ${data.status || 'OK'}` }
    } else {
      return { success: false, message: `HTTP ${response.status}: ${response.statusText}` }
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Connection failed'
    return { success: false, message: message.includes('timeout') ? 'Connection timed out' : message }
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
  
  if (!newDeviceUrl.value.trim()) {
    formError.value = 'Device URL is required'
    return
  }
  
  try {
    new URL(newDeviceUrl.value)
  } catch {
    formError.value = 'Invalid URL format. Use http:// or https://'
    return
  }
  
  isLoading.value = true
  
  try {
    const result = await testConnection(newDeviceUrl.value)
    testResult.value = result
    
    if (!result.success) {
      formError.value = 'Connection failed. You can still save for later.'
    }
    
    const device = await window.electronAPI.addDevice(
      newDeviceName.value.trim() || 'Preke Device',
      newDeviceUrl.value.trim()
    )
    
    await loadDevices()
    
    if (devices.value.length === 1) {
      await selectDevice(device.id)
    }
    
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
    
    const device = devices.value.find(d => d.id === deviceId)
    if (device) {
      setDeviceUrl(device.url)
    }
    
    router.push('/')
  } catch (error) {
    console.error('Failed to select device:', error)
  } finally {
    isLoading.value = false
  }
}

function startEdit(device: DeviceConfig) {
  editingDevice.value = { ...device }
}

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

function cancelEdit() {
  editingDevice.value = null
}

function goBack() {
  if (activeDevice.value) {
    router.push('/')
  }
}

onMounted(() => {
  loadDevices()
})
</script>

<template>
  <div class="setup">
    <!-- Background layers -->
    <div class="setup__bg">
      <div class="setup__bg-gradient" />
      <div class="setup__bg-texture" />
      <div class="setup__bg-glow setup__bg-glow--top" />
      <div class="setup__bg-glow setup__bg-glow--bottom" />
    </div>
    
    <div class="setup__container">
      <!-- Hero Section with Logo -->
      <header class="setup__hero">
        <div class="setup__logo-wrapper">
          <img src="/logo-white.svg" alt="Preke" class="setup__logo" />
        </div>
        
        <!-- 3D Soundwave -->
        <div class="setup__wave-container">
          <div class="setup__wave">
            <span v-for="i in 24" :key="i" class="setup__wave-bar" :style="{ '--i': i }" />
          </div>
        </div>
      </header>
      
      <!-- Main Content Card -->
      <main class="setup__card" :class="{ 'setup__card--wide': hasDevices }">
        <!-- Welcome Text (only on first run) -->
        <div v-if="!hasDevices && !showAddForm" class="setup__welcome">
          <h1 class="setup__title">Welcome</h1>
          <p class="setup__subtitle">Connect your first device to get started</p>
        </div>
        
        <!-- Devices Header (when devices exist) -->
        <div v-if="hasDevices && !showAddForm" class="setup__section-header">
          <h2 class="setup__section-title">Your Devices</h2>
        </div>

        <!-- Device List -->
        <div v-if="hasDevices && !showAddForm" class="setup__devices">
          <div 
            v-for="device in devices" 
            :key="device.id"
            class="setup__device"
            :class="{ 'setup__device--active': device.id === activeDeviceId }"
          >
            <!-- Edit Mode -->
            <div v-if="editingDevice?.id === device.id" class="setup__device-edit">
              <input v-model="editingDevice.name" type="text" placeholder="Device name" class="setup__input" />
              <input v-model="editingDevice.url" type="url" placeholder="Device URL" class="setup__input" />
              <div class="setup__device-edit-actions">
                <button @click="saveEdit" class="setup__btn setup__btn--primary setup__btn--sm">Save</button>
                <button @click="cancelEdit" class="setup__btn setup__btn--ghost setup__btn--sm">Cancel</button>
              </div>
            </div>

            <!-- View Mode -->
            <div v-else class="setup__device-row">
              <div class="setup__device-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <rect x="2" y="3" width="20" height="14" rx="2" />
                  <path d="M8 21h8M12 17v4" />
                </svg>
              </div>
              <div class="setup__device-info">
                <div class="setup__device-name-row">
                  <span class="setup__device-name">{{ device.name }}</span>
                  <span v-if="device.id === activeDeviceId" class="setup__badge">Connected</span>
                </div>
                <span class="setup__device-url">{{ device.url }}</span>
              </div>
              <div class="setup__device-actions">
                <button 
                  v-if="device.id !== activeDeviceId"
                  @click="selectDevice(device.id)"
                  :disabled="isLoading"
                  class="setup__btn setup__btn--primary"
                >
                  Connect
                </button>
                <button 
                  v-else
                  @click="goBack"
                  class="setup__btn setup__btn--success"
                >
                  Open Studio
                </button>
                <button @click="startEdit(device)" class="setup__icon-btn" title="Edit">
                  <svg viewBox="0 0 20 20" fill="currentColor">
                    <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
                  </svg>
                </button>
                <button @click="removeDevice(device.id)" class="setup__icon-btn setup__icon-btn--danger" title="Remove">
                  <svg viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
          
          <!-- Add device button -->
          <button @click="showAddForm = true" class="setup__add-device">
            <svg viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clip-rule="evenodd" />
            </svg>
            <span>Add Device</span>
          </button>
        </div>

        <!-- Add Device Form -->
        <div v-if="showAddForm || !hasDevices" class="setup__form">
          <h3 v-if="hasDevices" class="setup__form-title">Add New Device</h3>
          
          <div class="setup__field">
            <label class="setup__label">Device Name <span class="setup__label-opt">(optional)</span></label>
            <input 
              v-model="newDeviceName"
              type="text"
              placeholder="e.g., Studio Recorder"
              class="setup__input"
            />
          </div>
          
          <div class="setup__field">
            <label class="setup__label">Device URL <span class="setup__label-req">*</span></label>
            <input 
              v-model="newDeviceUrl"
              type="url"
              placeholder="https://r58-api.itagenten.no"
              class="setup__input"
              :class="{ 'setup__input--error': formError }"
            />
            <span v-if="formError" class="setup__error">{{ formError }}</span>
          </div>

          <!-- Test Result -->
          <div 
            v-if="testResult"
            class="setup__result"
            :class="testResult.success ? 'setup__result--success' : 'setup__result--error'"
          >
            <svg v-if="testResult.success" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
            </svg>
            <svg v-else viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
            </svg>
            <span>{{ testResult.message }}</span>
          </div>

          <div class="setup__form-actions">
            <button 
              @click="addDevice"
              :disabled="isLoading || isTesting"
              class="setup__btn setup__btn--primary setup__btn--lg"
            >
              <svg v-if="isLoading || isTesting" class="setup__spinner" viewBox="0 0 24 24">
                <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none" opacity="0.25" />
                <path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" opacity="0.75" />
              </svg>
              <span>{{ isTesting ? 'Testing...' : 'Connect Device' }}</span>
            </button>
            
            <button v-if="hasDevices" @click="showAddForm = false; testResult = null; formError = ''" class="setup__btn setup__btn--ghost">
              Cancel
            </button>
          </div>
        </div>

        <!-- Not in Electron Warning -->
        <div v-if="!inElectron" class="setup__warning">
          <svg viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
          </svg>
          <span>Device management requires the <strong>Preke Studio</strong> desktop app.</span>
        </div>
      </main>
      
      <!-- Footer -->
      <footer class="setup__footer">
        <span>Preke Studio</span>
        <span class="setup__footer-dot">•</span>
        <span>Desktop v2.0</span>
      </footer>
    </div>
  </div>
</template>

<style scoped>
/* ============================================
   DESIGN TOKENS
   ============================================ */
.setup {
  --gold: #d9981e;
  --gold-light: #f5c842;
  --gold-glow: rgba(217, 152, 30, 0.4);
  --dark-base: #070b14;
  --dark-card: rgba(15, 23, 42, 0.85);
  --border-subtle: rgba(255, 255, 255, 0.08);
  --text-primary: #f8fafc;
  --text-secondary: #94a3b8;
  --text-muted: #64748b;
  --blue: #3b82f6;
  --green: #10b981;
  --red: #ef4444;
}

/* ============================================
   LAYOUT
   ============================================ */
.setup {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  position: relative;
  overflow: hidden;
}

.setup__container {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 420px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1.5rem;
  animation: fadeIn 0.8s ease-out;
}

/* ============================================
   BACKGROUND
   ============================================ */
.setup__bg {
  position: fixed;
  inset: 0;
  z-index: 0;
  background: var(--dark-base);
}

.setup__bg-gradient {
  position: absolute;
  inset: 0;
  background: 
    radial-gradient(ellipse 100% 60% at 50% 0%, rgba(59, 130, 246, 0.12), transparent 50%),
    radial-gradient(ellipse 80% 50% at 100% 100%, rgba(217, 152, 30, 0.08), transparent 50%);
}

.setup__bg-texture {
  position: absolute;
  inset: 0;
  opacity: 0.02;
  background-image: 
    linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px);
  background-size: 40px 40px;
  /* Ready for texture: uncomment when background_image.webp is added */
  /* background-image: url('/background_image.webp');
  background-size: 300px;
  opacity: 0.03; */
}

.setup__bg-glow {
  position: absolute;
  width: 600px;
  height: 600px;
  border-radius: 50%;
  filter: blur(120px);
  pointer-events: none;
}

.setup__bg-glow--top {
  top: -300px;
  left: 50%;
  transform: translateX(-50%);
  background: radial-gradient(circle, rgba(59, 130, 246, 0.15), transparent 70%);
}

.setup__bg-glow--bottom {
  bottom: -300px;
  right: -200px;
  background: radial-gradient(circle, var(--gold-glow), transparent 70%);
  opacity: 0.5;
}

/* ============================================
   HERO SECTION (Logo + Wave)
   ============================================ */
.setup__hero {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2rem;
}

.setup__logo-wrapper {
  position: relative;
}

.setup__logo {
  height: 80px;
  width: auto;
  filter: drop-shadow(0 4px 24px rgba(255, 255, 255, 0.1));
}

/* ============================================
   3D SOUNDWAVE
   ============================================ */
.setup__wave-container {
  perspective: 500px;
  height: 48px;
}

.setup__wave {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 3px;
  height: 100%;
  transform: rotateX(25deg);
  transform-style: preserve-3d;
}

.setup__wave-bar {
  --delay: calc(var(--i) * 0.05s);
  --height: 8px;
  display: block;
  width: 3px;
  height: var(--height);
  background: linear-gradient(180deg, var(--gold-light), var(--gold));
  border-radius: 2px;
  transform-origin: center bottom;
  animation: wave3d 1.4s ease-in-out infinite;
  animation-delay: var(--delay);
  box-shadow: 
    0 0 8px var(--gold-glow),
    0 4px 12px rgba(0, 0, 0, 0.3);
}

/* Create varying heights for visual interest */
.setup__wave-bar:nth-child(1), .setup__wave-bar:nth-child(24) { --height: 6px; }
.setup__wave-bar:nth-child(2), .setup__wave-bar:nth-child(23) { --height: 10px; }
.setup__wave-bar:nth-child(3), .setup__wave-bar:nth-child(22) { --height: 14px; }
.setup__wave-bar:nth-child(4), .setup__wave-bar:nth-child(21) { --height: 20px; }
.setup__wave-bar:nth-child(5), .setup__wave-bar:nth-child(20) { --height: 26px; }
.setup__wave-bar:nth-child(6), .setup__wave-bar:nth-child(19) { --height: 32px; }
.setup__wave-bar:nth-child(7), .setup__wave-bar:nth-child(18) { --height: 36px; }
.setup__wave-bar:nth-child(8), .setup__wave-bar:nth-child(17) { --height: 40px; }
.setup__wave-bar:nth-child(9), .setup__wave-bar:nth-child(16) { --height: 44px; }
.setup__wave-bar:nth-child(10), .setup__wave-bar:nth-child(15) { --height: 46px; }
.setup__wave-bar:nth-child(11), .setup__wave-bar:nth-child(14) { --height: 48px; }
.setup__wave-bar:nth-child(12), .setup__wave-bar:nth-child(13) { --height: 48px; }

@keyframes wave3d {
  0%, 100% {
    transform: scaleY(0.4) translateZ(0);
    opacity: 0.6;
  }
  50% {
    transform: scaleY(1) translateZ(10px);
    opacity: 1;
  }
}

/* ============================================
   CARD
   ============================================ */
.setup__card {
  width: 100%;
  background: var(--dark-card);
  backdrop-filter: blur(24px);
  border: 1px solid var(--border-subtle);
  border-radius: 20px;
  padding: 2rem;
  box-shadow: 
    0 25px 50px -12px rgba(0, 0, 0, 0.5),
    inset 0 1px 0 rgba(255, 255, 255, 0.05);
}

.setup__card--wide {
  max-width: 520px;
}

/* ============================================
   WELCOME SECTION
   ============================================ */
.setup__welcome {
  text-align: center;
  margin-bottom: 2rem;
}

.setup__title {
  font-size: 1.75rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 0.5rem;
}

.setup__subtitle {
  font-size: 0.9375rem;
  color: var(--text-secondary);
}

/* ============================================
   SECTION HEADERS
   ============================================ */
.setup__section-header {
  margin-bottom: 1rem;
}

.setup__section-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
}

/* ============================================
   DEVICES LIST
   ============================================ */
.setup__devices {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.setup__device {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  padding: 1rem;
  transition: all 0.2s ease;
}

.setup__device:hover {
  background: rgba(255, 255, 255, 0.05);
}

.setup__device--active {
  border-color: var(--gold);
  background: rgba(217, 152, 30, 0.08);
}

.setup__device-row {
  display: flex;
  align-items: center;
  gap: 0.875rem;
}

.setup__device-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.05);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.setup__device-icon svg {
  width: 22px;
  height: 22px;
  color: var(--text-secondary);
}

.setup__device--active .setup__device-icon {
  background: rgba(217, 152, 30, 0.2);
}

.setup__device--active .setup__device-icon svg {
  color: var(--gold);
}

.setup__device-info {
  flex: 1;
  min-width: 0;
}

.setup__device-name-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.setup__device-name {
  font-size: 0.9375rem;
  font-weight: 500;
  color: var(--text-primary);
}

.setup__device-url {
  font-size: 0.8125rem;
  color: var(--text-muted);
  display: block;
  margin-top: 0.125rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.setup__badge {
  padding: 0.125rem 0.5rem;
  border-radius: 999px;
  font-size: 0.6875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  background: rgba(16, 185, 129, 0.2);
  color: var(--green);
}

.setup__device-actions {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  flex-shrink: 0;
}

.setup__device-edit {
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
}

.setup__device-edit-actions {
  display: flex;
  gap: 0.5rem;
}

.setup__add-device {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.75rem;
  margin-top: 0.5rem;
  background: transparent;
  border: 1px dashed rgba(255, 255, 255, 0.15);
  border-radius: 12px;
  color: var(--text-secondary);
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.setup__add-device:hover {
  border-color: var(--gold);
  color: var(--gold);
  background: rgba(217, 152, 30, 0.05);
}

.setup__add-device svg {
  width: 16px;
  height: 16px;
}

/* ============================================
   FORM
   ============================================ */
.setup__form {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.setup__form-title {
  font-size: 1rem;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 0.25rem;
}

.setup__field {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.setup__label {
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--text-primary);
}

.setup__label-opt {
  font-weight: 400;
  color: var(--text-muted);
}

.setup__label-req {
  color: var(--gold);
}

.setup__input {
  width: 100%;
  padding: 0.75rem 1rem;
  font-size: 0.9375rem;
  color: var(--text-primary);
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  outline: none;
  transition: all 0.15s ease;
}

.setup__input::placeholder {
  color: var(--text-muted);
}

.setup__input:focus {
  border-color: var(--blue);
  background: rgba(255, 255, 255, 0.08);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
}

.setup__input--error {
  border-color: var(--red);
}

.setup__error {
  font-size: 0.8125rem;
  color: var(--red);
}

.setup__result {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem;
  border-radius: 10px;
  font-size: 0.875rem;
}

.setup__result svg {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}

.setup__result--success {
  background: rgba(16, 185, 129, 0.1);
  color: var(--green);
}

.setup__result--error {
  background: rgba(239, 68, 68, 0.1);
  color: var(--red);
}

.setup__form-actions {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-top: 0.5rem;
}

/* ============================================
   BUTTONS
   ============================================ */
.setup__btn {
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

.setup__btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.setup__btn--primary {
  background: var(--blue);
  color: white;
}

.setup__btn--primary:hover:not(:disabled) {
  background: #2563eb;
  transform: translateY(-1px);
}

.setup__btn--success {
  background: var(--green);
  color: white;
}

.setup__btn--success:hover:not(:disabled) {
  background: #059669;
}

.setup__btn--ghost {
  background: transparent;
  color: var(--text-secondary);
  border: 1px solid var(--border-subtle);
}

.setup__btn--ghost:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.05);
  color: var(--text-primary);
}

.setup__btn--sm {
  padding: 0.5rem 0.75rem;
  font-size: 0.8125rem;
}

.setup__btn--lg {
  padding: 0.875rem 1.5rem;
  font-size: 0.9375rem;
  width: 100%;
}

.setup__icon-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  border: none;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.15s ease;
}

.setup__icon-btn:hover {
  background: rgba(255, 255, 255, 0.08);
  color: var(--text-primary);
}

.setup__icon-btn--danger:hover {
  background: rgba(239, 68, 68, 0.15);
  color: var(--red);
}

.setup__icon-btn svg {
  width: 16px;
  height: 16px;
}

.setup__spinner {
  width: 18px;
  height: 18px;
  animation: spin 1s linear infinite;
}

/* ============================================
   WARNING & FOOTER
   ============================================ */
.setup__warning {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  padding: 0.875rem;
  margin-top: 1.25rem;
  background: rgba(245, 158, 11, 0.1);
  border: 1px solid rgba(245, 158, 11, 0.2);
  border-radius: 10px;
  font-size: 0.8125rem;
  color: #fbbf24;
}

.setup__warning svg {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}

.setup__warning strong {
  color: #fcd34d;
}

.setup__footer {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  font-size: 0.75rem;
  color: var(--text-muted);
}

.setup__footer-dot {
  opacity: 0.5;
}

/* ============================================
   ANIMATIONS
   ============================================ */
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* ============================================
   RESPONSIVE
   ============================================ */
@media (max-width: 480px) {
  .setup {
    padding: 1rem;
  }
  
  .setup__logo {
    height: 64px;
  }
  
  .setup__card {
    padding: 1.5rem;
    border-radius: 16px;
  }
  
  .setup__wave-bar {
    width: 2px;
    gap: 2px;
  }
  
  .setup__device-actions {
    flex-wrap: wrap;
  }
}
</style>
