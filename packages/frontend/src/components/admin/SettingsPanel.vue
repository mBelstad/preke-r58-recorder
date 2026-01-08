<script setup lang="ts">
/**
 * SettingsPanel - Device and app settings configuration
 * 
 * Settings are stored locally (localStorage for web, Electron store for desktop)
 */
import { ref, onMounted, computed, onUnmounted } from 'vue'
import { isElectron } from '@/lib/api'
import { useToast } from '@/composables/useToast'
import { getVdoHost, VDO_ROOM } from '@/lib/vdoninja'

const toast = useToast()

// Device management
interface DeviceConfig {
  id: string
  name: string
  url: string
  lastConnected?: string
  createdAt: string
}

const devices = ref<DeviceConfig[]>([])
const activeDeviceId = ref<string | null>(null)

// Settings state
const deviceName = ref('Preke Device')
const vdoRoom = ref(VDO_ROOM)
const vdoHost = ref(getVdoHost())
// Note: Recording path is configured in config.yml on R58 device
// Default: /opt/r58/recordings/
// This UI setting is for display/reference only
const recordingPath = ref('/opt/r58/recordings')
const autoCleanup = ref(false)
const cleanupDays = ref(30)

// DaVinci Resolve Integration
const davinciEnabled = ref(false)
const davinciResolveConnected = ref(false)
const davinciCurrentSession = ref<string | null>(null)
const davinciChecking = ref(false)
const davinciProjectPrefix = ref('Preke')

// Computed
const inElectron = computed(() => isElectron())

// Local storage keys
const SETTINGS_KEY = 'preke-settings'

function loadSettings() {
  try {
    const stored = localStorage.getItem(SETTINGS_KEY)
    if (stored) {
      const settings = JSON.parse(stored)
      deviceName.value = settings.deviceName || deviceName.value
      vdoRoom.value = settings.vdoRoom || vdoRoom.value
      autoCleanup.value = settings.autoCleanup || false
      cleanupDays.value = settings.cleanupDays || 30
    }
  } catch {
    // Use defaults
  }
}

function saveSettings() {
  try {
    const settings = {
      deviceName: deviceName.value,
      vdoRoom: vdoRoom.value,
      autoCleanup: autoCleanup.value,
      cleanupDays: cleanupDays.value,
    }
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings))
    toast.success('Settings saved')
  } catch (e) {
    toast.error('Failed to save settings')
    console.error('Failed to save settings:', e)
  }
}

function resetToDefaults() {
  deviceName.value = 'Preke Device'
  vdoRoom.value = VDO_ROOM
  autoCleanup.value = false
  cleanupDays.value = 30
  saveSettings()
  toast.info('Settings reset to defaults')
}

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

async function removeDevice(deviceId: string) {
  if (!window.electronAPI || !confirm('Remove this device?')) return
  try {
    await window.electronAPI.removeDevice(deviceId)
    await loadDevices()
    toast.success('Device removed')
  } catch (error) {
    console.error('Failed to remove device:', error)
    toast.error('Failed to remove device')
  }
}

// DaVinci functions
async function checkDaVinciResolve() {
  if (!window.electronAPI?.davinciCheckResolve) return
  davinciChecking.value = true
  try {
    const result = await window.electronAPI.davinciCheckResolve()
    davinciResolveConnected.value = result.connected
    if (result.connected) {
      toast.success('DaVinci Resolve is connected!')
    } else {
      toast.warning('DaVinci Resolve is not running or not accessible')
    }
  } catch (error) {
    console.error('Failed to check DaVinci:', error)
    toast.error('Failed to check DaVinci Resolve')
  } finally {
    davinciChecking.value = false
  }
}

async function toggleDaVinciIntegration() {
  if (!window.electronAPI) return
  
  try {
    if (davinciEnabled.value) {
      // Disable
      await window.electronAPI.davinciStop()
      davinciEnabled.value = false
      toast.info('DaVinci integration stopped')
    } else {
      // Enable - first check if Resolve is running
      const check = await window.electronAPI.davinciCheckResolve()
      if (!check.connected) {
        toast.error('Please start DaVinci Resolve Studio first')
        return
      }
      
      // Update config with project prefix
      await window.electronAPI.davinciConfig({
        projectNamePrefix: davinciProjectPrefix.value
      })
      
      // Start
      await window.electronAPI.davinciStart()
      davinciEnabled.value = true
      davinciResolveConnected.value = true
      toast.success('DaVinci integration started! Recording sessions will auto-create projects.')
    }
  } catch (error) {
    console.error('Failed to toggle DaVinci:', error)
    toast.error('Failed to toggle DaVinci integration')
  }
}

async function loadDaVinciStatus() {
  if (!window.electronAPI?.davinciStatus) return
  try {
    const status = await window.electronAPI.davinciStatus()
    davinciEnabled.value = status.enabled
    davinciResolveConnected.value = status.resolveConnected
    davinciCurrentSession.value = status.currentSession
  } catch (error) {
    console.error('Failed to load DaVinci status:', error)
  }
}

// Event listeners cleanup
let cleanupSessionStart: (() => void) | null = null
let cleanupSessionStop: (() => void) | null = null
let cleanupConnectionChanged: (() => void) | null = null

onMounted(() => {
  loadSettings()
  loadDevices()
  loadDaVinciStatus()
  
  // Setup DaVinci event listeners
  if (window.electronAPI?.onDavinciSessionStart) {
    cleanupSessionStart = window.electronAPI.onDavinciSessionStart((data) => {
      davinciCurrentSession.value = data.sessionId
      toast.success(`Recording started: ${data.sessionId}`)
    })
  }
  
  if (window.electronAPI?.onDavinciSessionStop) {
    cleanupSessionStop = window.electronAPI.onDavinciSessionStop((data) => {
      davinciCurrentSession.value = null
      toast.info(`Recording stopped, ${data.filePaths.length} files imported`)
    })
  }
  
  if (window.electronAPI?.onDavinciConnectionChanged) {
    cleanupConnectionChanged = window.electronAPI.onDavinciConnectionChanged((data) => {
      davinciResolveConnected.value = data.connected
      if (!data.connected && davinciEnabled.value) {
        toast.warning('DaVinci Resolve disconnected')
      }
    })
  }
})

onUnmounted(() => {
  cleanupSessionStart?.()
  cleanupSessionStop?.()
  cleanupConnectionChanged?.()
})
</script>

<template>
  <div class="space-y-6">
    <!-- Device Settings -->
    <div class="glass-card p-4 rounded-xl">
      <h3 class="text-xs font-semibold text-preke-text-muted uppercase tracking-wide mb-4">Device</h3>
      
      <div class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-preke-text mb-2">Device Name</label>
          <input 
            v-model="deviceName"
            type="text"
            class="input w-full"
            placeholder="My Preke Device"
          />
          <p class="text-xs text-preke-text-muted mt-1">Display name for this device in the app</p>
        </div>
      </div>
    </div>
    
    <!-- Device Management -->
    <div v-if="inElectron && devices.length > 0" class="glass-card p-4 rounded-xl">
      <h3 class="text-xs font-semibold text-preke-text-muted uppercase tracking-wide mb-4">Saved Devices</h3>
      
      <div class="space-y-2">
        <div 
          v-for="device in devices" 
          :key="device.id"
          class="flex items-center justify-between p-3 rounded-lg border border-preke-surface-border"
          :class="{ 'bg-preke-gold/10 border-preke-gold/30': device.id === activeDeviceId }"
        >
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2">
              <span class="text-sm font-medium text-preke-text">{{ device.name }}</span>
              <span v-if="device.id === activeDeviceId" class="text-xs px-2 py-0.5 rounded bg-preke-gold/20 text-preke-gold">
                Active
              </span>
            </div>
            <p class="text-xs text-preke-text-muted truncate mt-1">{{ device.url }}</p>
          </div>
          <button
            @click="removeDevice(device.id)"
            class="ml-3 p-2 rounded-lg text-preke-text-muted hover:text-red-400 hover:bg-red-500/10 transition-colors"
            title="Remove device"
          >
            <svg viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4">
              <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd"/>
            </svg>
          </button>
        </div>
      </div>
    </div>
    
    <!-- VDO.ninja Settings -->
    <div class="glass-card p-4 rounded-xl">
      <h3 class="text-xs font-semibold text-preke-text-muted uppercase tracking-wide mb-4">VDO.ninja / Mixer</h3>
      
      <div class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-preke-text mb-2">Room Name</label>
          <input 
            v-model="vdoRoom"
            type="text"
            class="input w-full"
            placeholder="r58studio"
          />
          <p class="text-xs text-preke-text-muted mt-1">VDO.ninja room for video mixing</p>
        </div>
        
        <div>
          <label class="block text-sm font-medium text-preke-text mb-2">VDO Host</label>
          <input 
            :value="vdoHost"
            type="text"
            class="input w-full bg-preke-surface opacity-60"
            readonly
            disabled
          />
          <p class="text-xs text-preke-text-muted mt-1">VDO.ninja server (read-only)</p>
        </div>
      </div>
    </div>
    
    <!-- DaVinci Resolve Integration (Electron only) -->
    <div v-if="inElectron" class="glass-card p-4 rounded-xl">
      <h3 class="text-xs font-semibold text-preke-text-muted uppercase tracking-wide mb-4">
        DaVinci Resolve Integration
      </h3>
      
      <div class="space-y-4">
        <!-- Status indicator -->
        <div class="flex items-center justify-between p-3 rounded-lg bg-preke-surface/50 border border-preke-surface-border">
          <div class="flex items-center gap-3">
            <div 
              class="w-3 h-3 rounded-full"
              :class="davinciResolveConnected ? 'bg-green-500' : 'bg-zinc-500'"
            />
            <div>
              <p class="text-sm font-medium text-preke-text">
                {{ davinciResolveConnected ? 'DaVinci Resolve Connected' : 'DaVinci Resolve Not Connected' }}
              </p>
              <p v-if="davinciCurrentSession" class="text-xs text-preke-gold">
                Recording: {{ davinciCurrentSession }}
              </p>
            </div>
          </div>
          <button
            @click="checkDaVinciResolve"
            :disabled="davinciChecking"
            class="px-3 py-1.5 text-xs rounded-lg bg-preke-surface hover:bg-preke-surface-elevated border border-preke-surface-border text-preke-text transition-colors disabled:opacity-50"
          >
            {{ davinciChecking ? 'Checking...' : 'Check Connection' }}
          </button>
        </div>
        
        <!-- Enable toggle -->
        <div class="flex items-center justify-between">
          <div>
            <label class="block text-sm font-medium text-preke-text">Auto-sync with DaVinci Resolve</label>
            <p class="text-xs text-preke-text-muted">
              Automatically create projects and import media when recording
            </p>
          </div>
          <button
            @click="toggleDaVinciIntegration"
            class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors"
            :class="davinciEnabled ? 'bg-preke-gold' : 'bg-preke-surface-elevated'"
          >
            <span
              class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform"
              :class="davinciEnabled ? 'translate-x-6' : 'translate-x-1'"
            />
          </button>
        </div>
        
        <!-- Project prefix -->
        <div v-if="davinciEnabled">
          <label class="block text-sm font-medium text-preke-text mb-2">Project Name Prefix</label>
          <input 
            v-model="davinciProjectPrefix"
            type="text"
            class="input w-full"
            placeholder="Preke"
          />
          <p class="text-xs text-preke-text-muted mt-1">
            Projects will be named: {{ davinciProjectPrefix }}_session-id
          </p>
        </div>
        
        <!-- Info box -->
        <div class="p-3 rounded-lg bg-blue-500/10 border border-blue-500/20">
          <p class="text-xs text-blue-300">
            <strong>How it works:</strong> When you start a recording on the R58, a new DaVinci project 
            is automatically created. When recording stops, the files are imported into the project's media pool.
          </p>
        </div>
      </div>
    </div>
    
    <!-- Storage Settings -->
    <div class="glass-card p-4 rounded-xl">
      <h3 class="text-xs font-semibold text-preke-text-muted uppercase tracking-wide mb-4">Storage</h3>
      
      <div class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-preke-text mb-2">Recording Path</label>
          <input 
            :value="recordingPath"
            type="text"
            class="input w-full bg-preke-surface opacity-60"
            readonly
            disabled
          />
          <p class="text-xs text-preke-text-muted mt-1">
            Configured in config.yml on R58 device. Default: /opt/r58/recordings/
          </p>
        </div>
        
        <div class="flex items-center justify-between">
          <div>
            <label class="block text-sm font-medium text-preke-text">Auto-cleanup old recordings</label>
            <p class="text-xs text-preke-text-muted">Automatically delete recordings older than specified days</p>
          </div>
          <button
            @click="autoCleanup = !autoCleanup"
            class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors"
            :class="autoCleanup ? 'bg-preke-gold' : 'bg-preke-surface-elevated'"
          >
            <span
              class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform"
              :class="autoCleanup ? 'translate-x-6' : 'translate-x-1'"
            />
          </button>
        </div>
        
        <div v-if="autoCleanup">
          <label class="block text-sm font-medium text-preke-text mb-2">Keep recordings for (days)</label>
          <input 
            v-model.number="cleanupDays"
            type="number"
            min="1"
            max="365"
            class="input w-24"
          />
        </div>
        
        <!-- Reset to Defaults - only resets recording path settings -->
        <div class="pt-4 border-t border-preke-surface-border">
          <button 
            @click="resetToDefaults"
            class="btn-v2 btn-v2--secondary w-full"
          >
            Reset to Defaults
          </button>
        </div>
      </div>
    </div>
    
    <!-- Actions -->
    <div class="flex items-center justify-end">
      <button 
        @click="saveSettings"
        class="btn-v2 btn-v2--primary"
      >
        Save Settings
      </button>
    </div>
    
    <!-- App Info -->
    <div class="glass-card p-4 rounded-xl bg-preke-surface/30">
      <h3 class="text-xs font-semibold text-preke-text-muted uppercase tracking-wide mb-4">About</h3>
      
      <div class="space-y-2 text-sm">
        <div class="flex justify-between">
          <span class="text-preke-text-muted">App Version</span>
          <span class="text-preke-text">2.0.0</span>
        </div>
        <div class="flex justify-between">
          <span class="text-preke-text-muted">Platform</span>
          <span class="text-preke-text">{{ inElectron ? 'Desktop (Electron)' : 'Web Browser' }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

