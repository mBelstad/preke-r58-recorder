<script setup lang="ts">
/**
 * Device Setup View
 * Professional branded first-run experience for Preke Studio
 * Features auto-discovery as the primary connection method
 */
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { isElectron, setDeviceUrl } from '@/lib/api'

interface DeviceConfig {
  id: string
  name: string
  url: string
  lastConnected?: string
  createdAt: string
}

interface DiscoveredDevice {
  id: string
  name: string
  host: string
  port: number
  url: string
  source: 'mdns' | 'probe' | 'hostname'
  status?: string
  version?: string
}

const router = useRouter()

// Saved devices
const devices = ref<DeviceConfig[]>([])
const activeDeviceId = ref<string | null>(null)

// Discovery state
const isDiscovering = ref(false)
const isBackgroundScan = ref(false) // True when scanning in background (no UI)
const discoveredDevices = ref<DiscoveredDevice[]>([])
const scanningSubnet = ref<string>('')
const backgroundScanInterval = ref<ReturnType<typeof setInterval> | null>(null)
const backgroundScanTimeout = ref<ReturnType<typeof setTimeout> | null>(null)

// Manual entry
const showManualEntry = ref(false)
const manualUrl = ref('')
const manualName = ref('')
const manualError = ref('')
const isProbing = ref(false)

// Cleanup functions for event listeners
const cleanupFns: (() => void)[] = []

const hasDevices = computed(() => devices.value.length > 0)
const activeDevice = computed(() => devices.value.find(d => d.id === activeDeviceId.value))
const inElectron = computed(() => isElectron())

// Combine discovered + saved for display
const allDevices = computed(() => {
  const saved = new Set(devices.value.map(d => d.url.replace(/\/$/, '')))
  const newDiscovered = discoveredDevices.value.filter(d => !saved.has(d.url.replace(/\/$/, '')))
  return {
    saved: devices.value,
    discovered: newDiscovered
  }
})

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

function startDiscovery() {
  if (!window.electronAPI || isDiscovering.value) return
  discoveredDevices.value = []
  scanningSubnet.value = ''
  window.electronAPI.startDiscovery()
}

function stopDiscovery() {
  if (!window.electronAPI) return
  window.electronAPI.stopDiscovery()
}

// Passive background scanning - rescans every 45 seconds when no devices found
function startBackgroundScanning() {
  stopBackgroundScanning()
  // Wait before starting the interval
  backgroundScanTimeout.value = setTimeout(() => {
    backgroundScanInterval.value = setInterval(() => {
      // Only scan if not already scanning and no devices found yet
      if (!isDiscovering.value && discoveredDevices.value.length === 0 && !hasDevices.value) {
        isBackgroundScan.value = true
        window.electronAPI?.startDiscovery()
      }
    }, 45000) // Every 45 seconds - not aggressive
  }, 30000) // Wait 30 seconds after initial scan before starting background scans
}

function stopBackgroundScanning() {
  if (backgroundScanTimeout.value) {
    clearTimeout(backgroundScanTimeout.value)
    backgroundScanTimeout.value = null
  }
  if (backgroundScanInterval.value) {
    clearInterval(backgroundScanInterval.value)
    backgroundScanInterval.value = null
  }
}

async function addDiscoveredDevice(discovered: DiscoveredDevice) {
  if (!window.electronAPI) return
  try {
    const device = await window.electronAPI.addDevice(discovered.name, discovered.url)
    await loadDevices()
    if (devices.value.length === 1) {
      await selectDevice(device.id)
    }
  } catch (error) {
    console.error('Failed to add device:', error)
  }
}

async function addManualDevice() {
  if (!window.electronAPI) return
  manualError.value = ''
  
  if (!manualUrl.value.trim()) {
    manualError.value = 'URL is required'
    return
  }
  
  let url = manualUrl.value.trim()
  // Add protocol if missing
  if (!url.startsWith('http://') && !url.startsWith('https://')) {
    url = `http://${url}`
  }
  
  try {
    new URL(url)
  } catch {
    manualError.value = 'Invalid URL format'
    return
  }
  
  isProbing.value = true
  try {
    const probed = await window.electronAPI.probeDevice(url)
    if (probed) {
      await addDiscoveredDevice(probed)
      manualUrl.value = ''
      manualName.value = ''
      showManualEntry.value = false
    } else {
      // Add anyway but warn
      const device = await window.electronAPI.addDevice(
        manualName.value.trim() || 'Preke Device',
        url
      )
      await loadDevices()
      if (devices.value.length === 1) {
        await selectDevice(device.id)
      }
      manualUrl.value = ''
      manualName.value = ''
      showManualEntry.value = false
    }
  } catch (error) {
    manualError.value = 'Failed to add device'
  } finally {
    isProbing.value = false
  }
}

async function removeDevice(deviceId: string) {
  if (!window.electronAPI || !confirm('Remove this device?')) return
  try {
    await window.electronAPI.removeDevice(deviceId)
    await loadDevices()
  } catch (error) {
    console.error('Failed to remove device:', error)
  }
}

async function selectDevice(deviceId: string) {
  if (!window.electronAPI) return
  try {
    await window.electronAPI.setActiveDevice(deviceId)
    activeDeviceId.value = deviceId
    const device = devices.value.find(d => d.id === deviceId)
    if (device) setDeviceUrl(device.url)
    router.push('/')
  } catch (error) {
    console.error('Failed to select device:', error)
  }
}

function goBack() {
  if (activeDevice.value) router.push('/')
}

function setupDiscoveryListeners() {
  if (!window.electronAPI) return

  cleanupFns.push(
    window.electronAPI.onDiscoveryStarted(() => {
      isDiscovering.value = true
    }),
    window.electronAPI.onDeviceDiscovered((device) => {
      // Avoid duplicates
      if (!discoveredDevices.value.find(d => d.id === device.id)) {
        discoveredDevices.value.push(device)
        // Stop background scanning when we find devices
        stopBackgroundScanning()
        isBackgroundScan.value = false
      }
    }),
    window.electronAPI.onScanningSubnet((subnet) => {
      // Only show subnet during foreground scans
      if (!isBackgroundScan.value) {
        scanningSubnet.value = subnet
      }
    }),
    window.electronAPI.onDiscoveryComplete((devices) => {
      isDiscovering.value = false
      isBackgroundScan.value = false
      scanningSubnet.value = ''
      // Merge any we might have missed
      for (const d of devices) {
        if (!discoveredDevices.value.find(e => e.id === d.id)) {
          discoveredDevices.value.push(d)
        }
      }
      // If devices found, stop background scanning
      if (discoveredDevices.value.length > 0 || hasDevices.value) {
        stopBackgroundScanning()
      }
    })
  )
}

onMounted(() => {
  loadDevices()
  setupDiscoveryListeners()
  // Auto-start discovery on mount
  if (window.electronAPI) {
    startDiscovery()
    // Start passive background scanning
    startBackgroundScanning()
  }
})

onUnmounted(() => {
  // Cleanup listeners
  for (const fn of cleanupFns) {
    fn()
  }
  // Stop background scanning
  stopBackgroundScanning()
  // Stop any ongoing discovery
  if (isDiscovering.value) {
    stopDiscovery()
  }
})
</script>

<template>
  <div class="setup-page">
    <!-- Background -->
    <div class="setup-page__bg">
      <div class="setup-page__bg-texture" />
    </div>
    
    <div class="setup-page__content">
      <!-- Large centered logo -->
      <div class="logo-hero">
        <img src="/logo-studio-stacked.svg" alt="Preke Studio" class="logo-hero__img" />
      </div>
      
      <!-- Main content card -->
      <div class="setup-card">
        <!-- Discovery Section (Primary) -->
        <div class="discovery-section">
          <div class="discovery-header">
            <h2 v-if="(isDiscovering && !isBackgroundScan) || discoveredDevices.length > 0 || hasDevices" class="section-title">
              <template v-if="isDiscovering && !isBackgroundScan">Searching...</template>
              <template v-else>Devices</template>
            </h2>
            <div v-else class="section-title-spacer"></div>
            
            <!-- Scan/Stop buttons -->
            <button 
              v-if="isDiscovering && !isBackgroundScan" 
              @click="stopDiscovery" 
              class="btn-scan btn-scan--stop"
            >
              Stop
            </button>
            <button 
              v-else-if="(discoveredDevices.length > 0 || hasDevices)" 
              @click="startDiscovery" 
              :disabled="isDiscovering"
              class="btn-scan"
              :class="{ 'btn-scan--spinning': isBackgroundScan }"
              title="Scan again"
            >
              <svg viewBox="0 0 20 20" fill="currentColor" class="btn-scan__icon">
                <path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd"/>
              </svg>
              Scan
            </button>
          </div>

          <!-- Scanning Animation (Soundwave) - only for foreground scans -->
          <div v-if="isDiscovering && !isBackgroundScan" class="scan-indicator">
            <div class="soundwave">
              <span v-for="i in 24" :key="i" class="soundwave__bar" :style="{ '--i': i }" />
            </div>
            <p v-if="scanningSubnet" class="scan-status">Scanning {{ scanningSubnet }}.x</p>
          </div>

          <!-- Discovered Devices (not yet saved) -->
          <div v-if="allDevices.discovered.length > 0" class="device-group">
            <p class="device-group__label">
              Found on network
              <span v-if="allDevices.discovered.length > 1" class="device-group__count">
                ({{ allDevices.discovered.length }} devices)
              </span>
            </p>
            
            <!-- Multiple device selection view -->
            <div v-if="allDevices.discovered.length > 1" class="device-selection">
              <p class="device-selection__hint">Select a device to connect:</p>
            </div>
            
            <div 
              v-for="device in allDevices.discovered" 
              :key="device.id" 
              class="device-item device-item--discovered"
            >
              <div class="device-item__icon device-item__icon--new">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <rect x="2" y="3" width="20" height="14" rx="2"/>
                  <path d="M8 21h8M12 17v4"/>
                </svg>
              </div>
              <div class="device-item__info">
                <span class="device-item__name">{{ device.name }}</span>
                <span v-if="device.version" class="device-item__version">v{{ device.version }}</span>
                <span class="device-item__url">{{ device.host }}:{{ device.port }}</span>
              </div>
              <button @click="addDiscoveredDevice(device)" class="btn btn--primary">
                Connect
              </button>
            </div>
          </div>

          <!-- Saved Devices -->
          <div v-if="allDevices.saved.length > 0" class="device-group">
            <p v-if="allDevices.discovered.length > 0" class="device-group__label">Saved devices</p>
            <div 
              v-for="device in allDevices.saved" 
              :key="device.id" 
              class="device-item"
              :class="{ 'device-item--active': device.id === activeDeviceId }"
            >
              <div class="device-item__icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <rect x="2" y="3" width="20" height="14" rx="2"/>
                  <path d="M8 21h8M12 17v4"/>
                </svg>
              </div>
              <div class="device-item__info">
                <span class="device-item__name">{{ device.name }}</span>
                <span v-if="device.id === activeDeviceId" class="device-item__badge">Connected</span>
                <span class="device-item__url">{{ device.url }}</span>
              </div>
              <div class="device-item__actions">
                <button v-if="device.id !== activeDeviceId" @click="selectDevice(device.id)" class="btn btn--primary">
                  Connect
                </button>
                <button v-else @click="goBack" class="btn btn--success">
                  Open
                </button>
                <button @click="removeDevice(device.id)" class="btn-icon btn-icon--danger" title="Remove">
                  <svg viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd"/>
                  </svg>
                </button>
              </div>
            </div>
          </div>

          <!-- Empty state when not discovering (foreground) and nothing found -->
          <div v-if="(!isDiscovering || isBackgroundScan) && discoveredDevices.length === 0 && !hasDevices" class="empty-state">
            <div class="empty-state__icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <rect x="2" y="3" width="20" height="14" rx="2"/>
                <path d="M8 21h8M12 17v4"/>
                <path d="M9 9l6 6M15 9l-6 6" stroke-width="1.5" stroke-linecap="round"/>
              </svg>
            </div>
            <p class="empty-state__title">No devices found</p>
            <p class="empty-state__hint">Make sure your Preke device is:</p>
            <ul class="empty-state__checklist">
              <li>Powered on</li>
              <li>Connected to the same network</li>
              <li>Finished booting up (~30 seconds)</li>
            </ul>
            
            <!-- Scan button in empty state -->
            <button 
              @click="startDiscovery" 
              :disabled="isDiscovering"
              class="btn-scan-large"
              :class="{ 'btn-scan-large--spinning': isBackgroundScan }"
            >
              <svg viewBox="0 0 20 20" fill="currentColor" class="btn-scan-large__icon">
                <path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd"/>
              </svg>
              {{ isBackgroundScan ? 'Searching...' : 'Scan for devices' }}
            </button>
          </div>
        </div>

        <!-- Divider -->
        <div class="divider">
          <span>or</span>
        </div>

        <!-- Manual Entry Section -->
        <div class="manual-section">
          <button 
            v-if="!showManualEntry" 
            @click="showManualEntry = true" 
            class="btn-manual"
          >
            <svg viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clip-rule="evenodd"/>
            </svg>
            Enter address manually
          </button>
          
          <form v-else @submit.prevent="addManualDevice" class="manual-form">
            <div class="manual-form__row">
              <input 
                v-model="manualUrl" 
                type="text" 
                placeholder="IP address or URL (e.g., 192.168.1.100)"
                class="input"
                :class="{ 'input--error': manualError }"
              />
              <button 
                type="submit" 
                :disabled="isProbing" 
                class="btn btn--primary"
              >
                <svg v-if="isProbing" class="spinner" viewBox="0 0 24 24">
                  <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none" opacity="0.25"/>
                  <path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" opacity="0.75"/>
                </svg>
                Add
              </button>
            </div>
            <span v-if="manualError" class="field-error">{{ manualError }}</span>
            <button type="button" @click="showManualEntry = false; manualError = ''" class="btn-cancel">
              Cancel
            </button>
          </form>
        </div>

        <!-- Web warning -->
        <div v-if="!inElectron" class="electron-warning">
          <svg viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
          </svg>
          Auto-discovery requires the <strong>Preke Studio</strong> desktop app.
        </div>
      </div>
      
      <footer class="setup-footer">
        <button v-if="activeDevice" @click="goBack" class="back-link">← Back to Studio</button>
        <span class="version">v2.0</span>
      </footer>
    </div>
  </div>
</template>

<style scoped>
/* ═══════════════════════════════════════════
   DESIGN TOKENS
   ═══════════════════════════════════════════ */
.setup-page {
  --gold: #d9981e;
  --gold-light: #f5c842;
  --bg: #0a0e17;
  --card-bg: rgba(15, 23, 42, 0.95);
  --border: rgba(255, 255, 255, 0.08);
  --text: #f8fafc;
  --text-dim: #94a3b8;
  --text-muted: #64748b;
  --blue: #3b82f6;
  --green: #22c55e;
  --red: #ef4444;
}

/* ═══════════════════════════════════════════
   PAGE LAYOUT
   ═══════════════════════════════════════════ */
.setup-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  position: relative;
  background: var(--bg);
}

.setup-page__content {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 480px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2rem;
}

/* ═══════════════════════════════════════════
   BACKGROUND
   ═══════════════════════════════════════════ */
.setup-page__bg {
  position: fixed;
  inset: 0;
  overflow: hidden;
}

.setup-page__bg::before {
  content: '';
  position: absolute;
  inset: 0;
  background: 
    radial-gradient(ellipse 80% 50% at 50% 0%, rgba(59, 130, 246, 0.12), transparent 50%),
    radial-gradient(ellipse 60% 40% at 100% 100%, rgba(217, 152, 30, 0.08), transparent 40%);
}

.setup-page__bg-texture {
  position: absolute;
  inset: 0;
  background-image: url('/background_image.webp');
  background-size: 300px;
  opacity: 0.03;
}

/* ═══════════════════════════════════════════
   LOGO HERO
   ═══════════════════════════════════════════ */
.logo-hero {
  display: flex;
  justify-content: center;
  animation: fadeIn 0.8s ease-out;
}

.logo-hero__img {
  height: 240px;
  width: auto;
  filter: drop-shadow(0 4px 24px rgba(0, 0, 0, 0.3));
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-10px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ═══════════════════════════════════════════
   CARD
   ═══════════════════════════════════════════ */
.setup-card {
  width: 100%;
  background: var(--card-bg);
  backdrop-filter: blur(16px);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 1.5rem;
  animation: slideUp 0.6s ease-out 0.1s both;
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ═══════════════════════════════════════════
   DISCOVERY SECTION
   ═══════════════════════════════════════════ */
.discovery-section {
  min-height: 100px;
}

.discovery-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
}

.section-title {
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--text);
  margin: 0;
}

.section-title-spacer {
  height: 1rem;
}

.btn-scan {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.375rem 0.625rem;
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--text-dim);
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--border);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-scan:hover { background: rgba(255, 255, 255, 0.08); color: var(--text); }
.btn-scan--stop { color: var(--red); border-color: rgba(239, 68, 68, 0.3); }
.btn-scan--stop:hover { background: rgba(239, 68, 68, 0.1); }
.btn-scan svg { width: 14px; height: 14px; }
.btn-scan__icon { transition: transform 0.3s ease; }
.btn-scan--spinning .btn-scan__icon { animation: spin-slow 2s linear infinite; }
.btn-scan:disabled { opacity: 0.7; cursor: default; }

/* ═══════════════════════════════════════════
   SOUNDWAVE ANIMATION (Searching Indicator)
   ═══════════════════════════════════════════ */
.scan-indicator {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  padding: 1.5rem 0;
}

.soundwave {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 3px;
  height: 32px;
}

.soundwave__bar {
  /* Left-to-right wave: delay increases from left to right */
  --delay: calc(var(--i) * 0.08s);
  display: block;
  width: 3px;
  height: 20px; /* Base height, animation will scale */
  background: linear-gradient(0deg, var(--gold) 0%, var(--gold-light) 100%);
  border-radius: 2px;
  transform: scaleY(0.2); /* Start small */
  animation: soundwave 1.4s ease-in-out infinite;
  animation-delay: var(--delay);
  box-shadow: 0 0 6px rgba(217, 152, 30, 0.4);
}

@keyframes soundwave {
  0% {
    transform: scaleY(0.2);
    opacity: 0.4;
  }
  50% {
    transform: scaleY(1);
    opacity: 1;
  }
  100% {
    transform: scaleY(0.2);
    opacity: 0.4;
  }
}

.scan-status {
  font-size: 0.75rem;
  color: var(--text-muted);
}

/* ═══════════════════════════════════════════
   DEVICE GROUPS & ITEMS
   ═══════════════════════════════════════════ */
.device-group {
  margin-bottom: 0.75rem;
}

.device-group__label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.6875rem;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
  margin-bottom: 0.5rem;
}

.device-group__count {
  font-weight: 400;
  text-transform: none;
  color: var(--gold);
}

.device-selection {
  margin-bottom: 0.75rem;
}

.device-selection__hint {
  font-size: 0.8125rem;
  color: var(--text-dim);
}

.device-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--border);
  border-radius: 10px;
  margin-bottom: 0.5rem;
  transition: all 0.15s;
}

.device-item:hover { background: rgba(255, 255, 255, 0.04); }

.device-item--active {
  border-color: var(--gold);
  background: rgba(217, 152, 30, 0.05);
}

.device-item--discovered {
  border-color: rgba(34, 197, 94, 0.3);
  background: rgba(34, 197, 94, 0.03);
}

.device-item__icon {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.04);
  display: grid;
  place-items: center;
  flex-shrink: 0;
}

.device-item__icon svg {
  width: 16px;
  height: 16px;
  color: var(--text-muted);
}

.device-item--active .device-item__icon { background: rgba(217, 152, 30, 0.12); }
.device-item--active .device-item__icon svg { color: var(--gold); }
.device-item__icon--new { background: rgba(34, 197, 94, 0.12); }
.device-item__icon--new svg { color: var(--green); }

.device-item__info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.25rem 0.5rem;
}

.device-item__name {
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--text);
}

.device-item__badge {
  font-size: 0.5625rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  padding: 0.125rem 0.375rem;
  border-radius: 999px;
  background: rgba(34, 197, 94, 0.15);
  color: var(--green);
}

.device-item__version {
  font-size: 0.5625rem;
  font-weight: 500;
  padding: 0.125rem 0.375rem;
  border-radius: 999px;
  background: rgba(59, 130, 246, 0.15);
  color: var(--blue);
}

.device-item__url {
  width: 100%;
  font-size: 0.6875rem;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.device-item__actions {
  display: flex;
  gap: 0.375rem;
  flex-shrink: 0;
}

/* ═══════════════════════════════════════════
   EMPTY STATE
   ═══════════════════════════════════════════ */
.empty-state {
  text-align: center;
  padding: 1.5rem 1rem;
}

.empty-state__icon {
  width: 48px;
  height: 48px;
  margin: 0 auto 1rem;
  opacity: 0.4;
}

.empty-state__icon svg {
  width: 100%;
  height: 100%;
  color: var(--text-muted);
}

.empty-state__title {
  font-size: 0.9375rem;
  font-weight: 500;
  color: var(--text-dim);
  margin-bottom: 0.5rem;
}

.empty-state__hint {
  font-size: 0.8125rem;
  color: var(--text-muted);
  margin-bottom: 0.75rem;
}

.empty-state__checklist {
  list-style: none;
  padding: 0;
  margin: 0 0 1rem;
  display: inline-flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.25rem;
}

.empty-state__checklist li {
  font-size: 0.75rem;
  color: var(--text-muted);
  display: flex;
  align-items: center;
  gap: 0.375rem;
}

.empty-state__checklist li::before {
  content: '○';
  font-size: 0.5rem;
  color: var(--gold);
}

/* Scan button in empty state */
.btn-scan-large {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  margin-top: 1.25rem;
  padding: 0.625rem 1.25rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text);
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid var(--border);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-scan-large:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.1);
  border-color: var(--gold);
}

.btn-scan-large:disabled {
  opacity: 0.7;
  cursor: default;
}

.btn-scan-large__icon {
  width: 16px;
  height: 16px;
  transition: transform 0.3s ease;
}

.btn-scan-large--spinning .btn-scan-large__icon {
  animation: spin-slow 2s linear infinite;
}

@keyframes spin-slow {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* ═══════════════════════════════════════════
   DIVIDER
   ═══════════════════════════════════════════ */
.divider {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin: 1.25rem 0;
}

.divider::before,
.divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--border);
}

.divider span {
  font-size: 0.6875rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* ═══════════════════════════════════════════
   MANUAL ENTRY
   ═══════════════════════════════════════════ */
.manual-section {
  text-align: center;
}

.btn-manual {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.5rem 0.875rem;
  font-size: 0.8125rem;
  color: var(--text-muted);
  background: transparent;
  border: 1px dashed rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-manual:hover {
  color: var(--text);
  border-color: rgba(255, 255, 255, 0.2);
  background: rgba(255, 255, 255, 0.02);
}

.btn-manual svg { width: 14px; height: 14px; }

.manual-form {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.manual-form__row {
  display: flex;
  gap: 0.5rem;
}

.btn-cancel {
  font-size: 0.75rem;
  color: var(--text-muted);
  background: none;
  border: none;
  cursor: pointer;
}

.btn-cancel:hover { color: var(--text); }

.field-error {
  font-size: 0.75rem;
  color: var(--red);
  text-align: left;
}

/* ═══════════════════════════════════════════
   BUTTONS
   ═══════════════════════════════════════════ */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.375rem;
  padding: 0.5rem 0.875rem;
  font-size: 0.75rem;
  font-weight: 500;
  border-radius: 6px;
  border: none;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
}

.btn:disabled { opacity: 0.5; cursor: not-allowed; }

.btn--primary { background: var(--blue); color: white; }
.btn--primary:hover:not(:disabled) { background: #2563eb; }

.btn--success { background: var(--green); color: white; }
.btn--success:hover:not(:disabled) { background: #16a34a; }

.btn-icon {
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border-radius: 6px;
  border: none;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.15s;
}

.btn-icon:hover { background: rgba(255, 255, 255, 0.06); color: var(--text); }
.btn-icon--danger:hover { background: rgba(239, 68, 68, 0.12); color: var(--red); }
.btn-icon svg { width: 14px; height: 14px; }

.input {
  flex: 1;
  padding: 0.5rem 0.75rem;
  font-size: 0.8125rem;
  color: var(--text);
  background: rgba(0, 0, 0, 0.25);
  border: 1px solid var(--border);
  border-radius: 6px;
  outline: none;
  transition: all 0.15s;
}

.input::placeholder { color: var(--text-muted); }
.input:focus { border-color: var(--blue); box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15); }
.input--error { border-color: var(--red); }

.spinner { width: 14px; height: 14px; animation: spin 1s linear infinite; }

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* ═══════════════════════════════════════════
   WARNING & FOOTER
   ═══════════════════════════════════════════ */
.electron-warning {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  padding: 0.75rem;
  margin-top: 1rem;
  background: rgba(245, 158, 11, 0.08);
  border: 1px solid rgba(245, 158, 11, 0.12);
  border-radius: 8px;
  font-size: 0.75rem;
  color: #fbbf24;
  line-height: 1.4;
}

.electron-warning svg { width: 16px; height: 16px; flex-shrink: 0; margin-top: 1px; }
.electron-warning strong { color: #fcd34d; }

.setup-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  animation: slideUp 0.6s ease-out 0.2s both;
}

.back-link {
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 0.8125rem;
  cursor: pointer;
  transition: color 0.15s;
}

.back-link:hover { color: var(--text); }

.version {
  font-size: 0.6875rem;
  color: var(--text-muted);
  letter-spacing: 0.02em;
  margin-left: auto;
}

/* ═══════════════════════════════════════════
   RESPONSIVE
   ═══════════════════════════════════════════ */
@media (max-width: 480px) {
  .setup-page { padding: 1rem; }
  .logo-hero__img { height: 180px; }
  .setup-card { padding: 1.25rem; }
  .btn-scan-large { width: 100%; }
}
</style>
