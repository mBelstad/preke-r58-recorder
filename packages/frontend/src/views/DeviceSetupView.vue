<script setup lang="ts">
/**
 * Device Setup View
 * Professional branded first-run experience for Preke Studio
 * Features auto-discovery as the primary connection method
 */
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { isElectron, setDeviceUrl } from '@/lib/api'
import logoSidebar from '@/assets/logo-sidebar.svg'

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

// Welcome screen state
const showWelcome = ref(true)
const welcomeFadingOut = ref(false)

// Discovery state
const isDiscovering = ref(false)
const isBackgroundScan = ref(false) // True when scanning in background (no UI)
const discoveredDevices = ref<DiscoveredDevice[]>([])
const scanningSubnet = ref<string>('')
const backgroundScanInterval = ref<ReturnType<typeof setInterval> | null>(null)
const backgroundScanTimeout = ref<ReturnType<typeof setTimeout> | null>(null)
const backgroundScanCount = ref(0)
const MAX_BACKGROUND_SCANS = 30

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

function startDiscovery(isManual: boolean = false) {
  if (!window.electronAPI || isDiscovering.value) return
  discoveredDevices.value = []
  scanningSubnet.value = ''
  // Manual scan resets the background counter
  if (isManual) {
    backgroundScanCount.value = 0
    isBackgroundScan.value = false
    // Restart background scanning
    startBackgroundScanning()
  }
  window.electronAPI.startDiscovery()
}

function stopDiscovery() {
  if (!window.electronAPI) return
  window.electronAPI.stopDiscovery()
}

// Passive background scanning - rescans every 45 seconds when no devices found (max 30 tries)
function startBackgroundScanning() {
  stopBackgroundScanning()
  // Wait before starting the interval
  backgroundScanTimeout.value = setTimeout(() => {
    backgroundScanInterval.value = setInterval(() => {
      // Only scan if not already scanning, no devices found, and under limit
      if (!isDiscovering.value && discoveredDevices.value.length === 0 && !hasDevices.value) {
        if (backgroundScanCount.value < MAX_BACKGROUND_SCANS) {
          backgroundScanCount.value++
          isBackgroundScan.value = true
          window.electronAPI?.startDiscovery()
        } else {
          // Stop after max tries
          stopBackgroundScanning()
        }
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
        // If device found quickly during welcome, skip welcome immediately
        if (showWelcome.value) {
          showWelcome.value = false
        }
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

function dismissWelcome() {
  welcomeFadingOut.value = true
  setTimeout(() => {
    showWelcome.value = false
  }, 500) // Match fade animation duration
}

onMounted(async () => {
  await loadDevices()
  setupDiscoveryListeners()
  
  // If we already have devices, skip welcome and go straight to list
  if (hasDevices.value) {
    showWelcome.value = false
    return
  }
  
  // Auto-start discovery on mount
  if (window.electronAPI) {
    // Start discovery while showing welcome
    startDiscovery()
    // Start passive background scanning
    startBackgroundScanning()
  }
  
  // Dismiss welcome after a short delay (for both Electron and web)
  // Shows the beautiful welcome animation for ~2.5 seconds
  setTimeout(() => {
    if (showWelcome.value && discoveredDevices.value.length === 0) {
      dismissWelcome()
    }
  }, 2500)
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
    <!-- Background with ambient orbs and moving highlights -->
    <div class="setup-page__bg">
      <div class="setup-page__bg-texture" />
      <div class="bg-orb bg-orb--1"></div>
      <div class="bg-orb bg-orb--2"></div>
      <div class="bg-highlight bg-highlight--1"></div>
      <div class="bg-highlight bg-highlight--2"></div>
    </div>
    
    <!-- Welcome Screen (fades out) -->
    <Transition name="welcome-fade">
      <div v-if="showWelcome" class="welcome-screen" :class="{ 'welcome-screen--fading': welcomeFadingOut }">
        <!-- Moving highlight orbs -->
        <div class="welcome-orb welcome-orb--1"></div>
        <div class="welcome-orb welcome-orb--2"></div>
        <div class="welcome-orb welcome-orb--3"></div>
        <div class="welcome-orb welcome-orb--4"></div>
        <!-- Moving light beams -->
        <div class="welcome-beam welcome-beam--1"></div>
        <div class="welcome-beam welcome-beam--2"></div>
        <div class="welcome-beam welcome-beam--3"></div>
        
        <div class="welcome-content">
          <div class="welcome-logo-wrap">
            <div class="welcome-logo-inline">
              <img :src="logoSidebar" alt="" class="welcome-logo-waveform" />
              <div class="welcome-logo-text">
                <span class="welcome-logo-preke">Preke</span>
                <span class="welcome-logo-studio">Studio</span>
              </div>
            </div>
            <div class="welcome-glow"></div>
          </div>
        </div>
      </div>
    </Transition>
    
    <div v-show="!showWelcome" class="setup-page__content">
      <!-- Large centered logo - inline layout with waveform + text -->
      <div class="logo-hero">
        <div class="logo-hero__inline">
          <img :src="logoSidebar" alt="" class="logo-hero__waveform" />
          <div class="logo-hero__text">
            <span class="logo-hero__preke">Preke</span>
            <span class="logo-hero__studio">Studio</span>
          </div>
        </div>
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
              @click="startDiscovery(true)" 
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
            
            <!-- Scan button below text -->
            <div class="empty-state__actions">
              <button 
                @click="startDiscovery(true)" 
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
   DESIGN TOKENS - Corporate Glassmorphism
   ═══════════════════════════════════════════ */
.setup-page {
  /* Primary accent - warm amber/gold */
  --gold: #e0a030;
  --gold-light: #f5c04a;
  
  /* Backgrounds */
  --bg: #0a0a0a;
  --card-bg: rgba(50, 50, 50, 0.6);
  --glass-bg: rgba(255, 255, 255, 0.03);
  
  /* Borders & dividers - glass edges */
  --border: rgba(255, 255, 255, 0.12);
  --border-glow: rgba(224, 160, 48, 0.2);
  
  /* Typography - high contrast */
  --text: #ffffff;
  --text-dim: #e8e0d0;
  --text-muted: #a8a8a8;
  
  /* Status colors */
  --blue: #5a9fd4;
  --green: #6db56d;
  --red: #d45a5a;
  
  /* Shadows for 3D depth */
  --shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.3);
  --shadow-md: 0 8px 32px rgba(0, 0, 0, 0.4);
  --shadow-lg: 0 16px 48px rgba(0, 0, 0, 0.5);
  --shadow-glow: 0 0 40px rgba(224, 160, 48, 0.15);
}

/* ═══════════════════════════════════════════
   WELCOME SCREEN - Liquid Glass Effect
   ═══════════════════════════════════════════ */
.welcome-screen {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg);
  overflow: hidden;
  transition: opacity 0.5s ease-out;
}

.welcome-screen--fading {
  opacity: 0;
}

/* Moving highlight orbs */
.welcome-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.5;
  pointer-events: none;
}

.welcome-orb--1 {
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, rgba(224, 160, 48, 0.4) 0%, transparent 70%);
  top: -10%;
  left: -5%;
  animation: orb-float-1 8s ease-in-out infinite;
}

.welcome-orb--2 {
  width: 300px;
  height: 300px;
  background: radial-gradient(circle, rgba(168, 153, 104, 0.35) 0%, transparent 70%);
  bottom: -5%;
  right: -5%;
  animation: orb-float-2 10s ease-in-out infinite;
}

.welcome-orb--3 {
  width: 250px;
  height: 250px;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.15) 0%, transparent 70%);
  top: 50%;
  right: 20%;
  animation: orb-float-3 7s ease-in-out infinite;
}

.welcome-orb--4 {
  width: 350px;
  height: 350px;
  background: radial-gradient(circle, rgba(224, 160, 48, 0.25) 0%, transparent 70%);
  bottom: 20%;
  left: 10%;
  animation: orb-float-4 12s ease-in-out infinite;
}

@keyframes orb-float-1 {
  0%, 100% { transform: translate(0, 0) scale(1); }
  25% { transform: translate(80px, 60px) scale(1.1); }
  50% { transform: translate(40px, 100px) scale(0.95); }
  75% { transform: translate(100px, 30px) scale(1.05); }
}

@keyframes orb-float-2 {
  0%, 100% { transform: translate(0, 0) scale(1); }
  25% { transform: translate(-60px, -40px) scale(1.15); }
  50% { transform: translate(-100px, -80px) scale(0.9); }
  75% { transform: translate(-30px, -60px) scale(1.1); }
}

@keyframes orb-float-3 {
  0%, 100% { transform: translate(0, 0) scale(1); opacity: 0.4; }
  33% { transform: translate(-50px, 30px) scale(1.2); opacity: 0.6; }
  66% { transform: translate(30px, -40px) scale(0.85); opacity: 0.3; }
}

@keyframes orb-float-4 {
  0%, 100% { transform: translate(0, 0) scale(1); }
  20% { transform: translate(40px, -30px) scale(1.1); }
  40% { transform: translate(80px, 20px) scale(0.95); }
  60% { transform: translate(50px, 60px) scale(1.15); }
  80% { transform: translate(20px, 30px) scale(1); }
}

/* Light beams sweeping across welcome screen */
.welcome-beam {
  position: absolute;
  pointer-events: none;
  filter: blur(40px);
}

.welcome-beam--1 {
  width: 400px;
  height: 80px;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
  top: 20%;
  left: -30%;
  transform: rotate(-25deg);
  animation: beam-sweep-1 4s ease-in-out infinite;
}

.welcome-beam--2 {
  width: 350px;
  height: 60px;
  background: linear-gradient(90deg, transparent, rgba(224, 160, 48, 0.25), transparent);
  top: 60%;
  left: -25%;
  transform: rotate(15deg);
  animation: beam-sweep-2 5s ease-in-out infinite;
  animation-delay: 1.5s;
}

.welcome-beam--3 {
  width: 300px;
  height: 50px;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.12), transparent);
  top: 45%;
  left: -20%;
  transform: rotate(-10deg);
  animation: beam-sweep-3 6s ease-in-out infinite;
  animation-delay: 0.8s;
}

@keyframes beam-sweep-1 {
  0% { left: -35%; opacity: 0; }
  5% { opacity: 1; }
  95% { opacity: 1; }
  100% { left: 130%; opacity: 0; }
}

@keyframes beam-sweep-2 {
  0% { left: -30%; opacity: 0; }
  5% { opacity: 0.8; }
  95% { opacity: 0.8; }
  100% { left: 125%; opacity: 0; }
}

@keyframes beam-sweep-3 {
  0% { left: -25%; opacity: 0; }
  5% { opacity: 0.6; }
  95% { opacity: 0.6; }
  100% { left: 120%; opacity: 0; }
}

.welcome-content {
  position: relative;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: center;
}

.welcome-logo-wrap {
  position: relative;
  animation: welcome-float 0.8s ease-out;
}

/* Inline welcome logo */
.welcome-logo-inline {
  display: flex;
  align-items: center;
  gap: 2rem;
  position: relative;
  z-index: 1;
}

.welcome-logo-waveform {
  width: 120px;
  height: 120px;
  filter: drop-shadow(0 0 40px rgba(224, 160, 48, 0.5));
}

.welcome-logo-text {
  display: flex;
  align-items: baseline;
  gap: 0.75rem;
}

.welcome-logo-preke {
  font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-size: 5rem;
  font-weight: 800;
  color: #ffffff;
  letter-spacing: 0.02em;
  text-shadow: 0 4px 24px rgba(0, 0, 0, 0.5);
}

.welcome-logo-studio {
  font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-size: 5rem;
  font-weight: 800;
  color: var(--gold);
  letter-spacing: 0.02em;
  text-shadow: 0 0 40px rgba(224, 160, 48, 0.5);
}

/* Legacy stacked welcome logo */
.welcome-logo {
  height: 280px;
  width: auto;
  position: relative;
  z-index: 1;
  filter: drop-shadow(0 0 60px rgba(224, 160, 48, 0.25));
}

.welcome-glow {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, rgba(224, 160, 48, 0.2) 0%, transparent 60%);
  border-radius: 50%;
  animation: welcome-pulse 2.5s ease-in-out infinite;
  pointer-events: none;
}

@keyframes welcome-float {
  from {
    opacity: 0;
    transform: scale(0.9) translateY(20px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

@keyframes welcome-pulse {
  0%, 100% {
    opacity: 0.5;
    transform: translate(-50%, -50%) scale(1);
  }
  50% {
    opacity: 0.8;
    transform: translate(-50%, -50%) scale(1.15);
  }
}

.welcome-fade-enter-active,
.welcome-fade-leave-active {
  transition: opacity 0.5s ease;
}

.welcome-fade-enter-from,
.welcome-fade-leave-to {
  opacity: 0;
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
  /* Subtle noise texture effect using CSS */
  background-image: 
    repeating-linear-gradient(
      45deg,
      transparent 0px,
      transparent 1px,
      rgba(255, 255, 255, 0.01) 1px,
      rgba(255, 255, 255, 0.01) 2px
    );
  background-size: 8px 8px;
  opacity: 0.5;
}

/* Ambient background orbs */
.bg-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(100px);
  pointer-events: none;
}

.bg-orb--1 {
  width: 500px;
  height: 500px;
  background: radial-gradient(circle, rgba(224, 160, 48, 0.15) 0%, transparent 70%);
  top: -15%;
  right: -10%;
  animation: bg-orb-1 15s ease-in-out infinite;
}

.bg-orb--2 {
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, rgba(168, 153, 104, 0.12) 0%, transparent 70%);
  bottom: -10%;
  left: -10%;
  animation: bg-orb-2 18s ease-in-out infinite;
}

@keyframes bg-orb-1 {
  0%, 100% { transform: translate(0, 0); opacity: 0.6; }
  50% { transform: translate(-50px, 80px); opacity: 0.8; }
}

@keyframes bg-orb-2 {
  0%, 100% { transform: translate(0, 0); opacity: 0.5; }
  50% { transform: translate(60px, -60px); opacity: 0.7; }
}

/* Moving background highlights - visible through glass */
.bg-highlight {
  position: absolute;
  pointer-events: none;
  filter: blur(60px);
}

.bg-highlight--1 {
  width: 300px;
  height: 150px;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.15), transparent);
  top: 30%;
  left: -20%;
  transform: rotate(-15deg);
  animation: highlight-sweep-1 6s ease-in-out infinite;
}

.bg-highlight--2 {
  width: 250px;
  height: 120px;
  background: linear-gradient(90deg, transparent, rgba(224, 160, 48, 0.12), transparent);
  bottom: 25%;
  right: -15%;
  transform: rotate(20deg);
  animation: highlight-sweep-2 8s ease-in-out infinite;
  animation-delay: 3s;
}

@keyframes highlight-sweep-1 {
  0% { left: -25%; opacity: 0; }
  10% { opacity: 0.8; }
  90% { opacity: 0.8; }
  100% { left: 120%; opacity: 0; }
}

@keyframes highlight-sweep-2 {
  0% { right: -20%; opacity: 0; }
  10% { opacity: 0.6; }
  90% { opacity: 0.6; }
  100% { right: 120%; opacity: 0; }
}

/* ═══════════════════════════════════════════
   LOGO HERO - Inline layout with waveform + text
   ═══════════════════════════════════════════ */
.logo-hero {
  display: flex;
  justify-content: center;
  animation: fadeIn 0.8s ease-out;
}

.logo-hero__inline {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.logo-hero__waveform {
  width: 80px;
  height: 80px;
  filter: drop-shadow(0 0 24px rgba(224, 160, 48, 0.5));
  transition: filter 0.3s ease;
}

.logo-hero:hover .logo-hero__waveform {
  filter: drop-shadow(0 0 32px rgba(224, 160, 48, 0.7));
}

.logo-hero__text {
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
}

.logo-hero__preke {
  font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-size: 3.5rem;
  font-weight: 800;
  color: #ffffff;
  letter-spacing: 0.02em;
  text-shadow: 0 2px 12px rgba(0, 0, 0, 0.4);
}

.logo-hero__studio {
  font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-size: 3.5rem;
  font-weight: 800;
  color: var(--gold);
  letter-spacing: 0.02em;
  text-shadow: 0 0 24px rgba(224, 160, 48, 0.4);
}

/* Legacy stacked logo support */
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
  background: linear-gradient(
    145deg,
    rgba(80, 80, 80, 0.35) 0%,
    rgba(50, 50, 50, 0.45) 50%,
    rgba(35, 35, 35, 0.55) 100%
  );
  backdrop-filter: blur(40px) saturate(1.2);
  -webkit-backdrop-filter: blur(40px) saturate(1.2);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-top-color: rgba(255, 255, 255, 0.3);
  border-left-color: rgba(255, 255, 255, 0.2);
  border-radius: 24px;
  padding: 2rem;
  box-shadow: 
    0 25px 50px rgba(0, 0, 0, 0.5),
    0 10px 20px rgba(0, 0, 0, 0.3),
    inset 0 1px 1px rgba(255, 255, 255, 0.15),
    inset 0 -1px 1px rgba(0, 0, 0, 0.3);
  animation: cardAppear 0.6s ease-out 0.1s both;
  transform-style: preserve-3d;
  position: relative;
  overflow: hidden;
}

.setup-card::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 24px;
  background: linear-gradient(
    160deg,
    rgba(255, 255, 255, 0.1) 0%,
    rgba(255, 255, 255, 0.03) 30%,
    transparent 60%
  );
  pointer-events: none;
}

@keyframes cardAppear {
  from { 
    opacity: 0; 
    transform: translateY(30px) rotateX(3deg); 
  }
  to { 
    opacity: 1; 
    transform: translateY(0) rotateX(0); 
  }
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
  padding: 1rem;
  background: linear-gradient(
    135deg,
    rgba(255, 255, 255, 0.06) 0%,
    rgba(255, 255, 255, 0.02) 100%
  );
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-top-color: rgba(255, 255, 255, 0.15);
  border-radius: 12px;
  margin-bottom: 0.75rem;
  transition: all 0.2s ease;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.device-item:hover { 
  background: linear-gradient(
    135deg,
    rgba(255, 255, 255, 0.1) 0%,
    rgba(255, 255, 255, 0.04) 100%
  );
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
}

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

/* Actions container - centers button below content */
.empty-state__actions {
  display: flex;
  justify-content: center;
  width: 100%;
  margin-top: 1.5rem;
}

/* Scan button in empty state */
.btn-scan-large {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
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

.btn--primary { 
  background: linear-gradient(145deg, var(--gold-light), var(--gold));
  color: #1a1a1a;
  font-weight: 600;
  box-shadow: 0 4px 16px rgba(224, 160, 48, 0.3);
  border-color: rgba(255, 255, 255, 0.2);
}
.btn--primary:hover:not(:disabled) { 
  background: linear-gradient(145deg, #f8c856, #e8a838);
  box-shadow: 0 6px 20px rgba(224, 160, 48, 0.4);
  transform: translateY(-1px);
}

.btn--success { 
  background: linear-gradient(145deg, #7ec87e, var(--green));
  color: white;
  box-shadow: 0 4px 16px rgba(109, 181, 109, 0.3);
}
.btn--success:hover:not(:disabled) { 
  background: linear-gradient(145deg, #8ed88e, #5ead5e);
  transform: translateY(-1px);
}

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
@media (max-width: 640px) {
  .logo-hero__inline {
    flex-direction: column;
    gap: 0.75rem;
  }
  
  .logo-hero__preke,
  .logo-hero__studio {
    font-size: 2.5rem;
  }
  
  .logo-hero__waveform {
    width: 60px;
    height: 60px;
  }
  
  .welcome-logo-inline {
    flex-direction: column;
    gap: 1rem;
  }
  
  .welcome-logo-preke,
  .welcome-logo-studio {
    font-size: 3rem;
  }
  
  .welcome-logo-waveform {
    width: 80px;
    height: 80px;
  }
}

@media (max-width: 480px) {
  .setup-page { padding: 1rem; }
  .logo-hero__img { height: 180px; }
  .setup-card { padding: 1.25rem; }
  .btn-scan-large { width: 100%; }
  
  .logo-hero__preke,
  .logo-hero__studio {
    font-size: 2rem;
  }
  
  .welcome-logo-preke,
  .welcome-logo-studio {
    font-size: 2.5rem;
  }
}
</style>
