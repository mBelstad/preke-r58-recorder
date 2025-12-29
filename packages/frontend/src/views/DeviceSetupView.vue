<script setup lang="ts">
/**
 * Device Setup View
 * 
 * First-run screen for configuring R58 device connections.
 * Only shown in Electron when no device is configured.
 */
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { isElectron, setDeviceUrl, apiGet } from '@/lib/api'

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
      newDeviceName.value.trim() || 'R58 Device',
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
  <div class="min-h-screen bg-r58-bg-primary flex items-center justify-center p-8">
    <div class="w-full max-w-2xl">
      <!-- Header -->
      <div class="text-center mb-8">
        <div class="w-16 h-16 bg-r58-accent-primary rounded-2xl flex items-center justify-center mx-auto mb-4">
          <svg class="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
              d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
          </svg>
        </div>
        <h1 class="text-2xl font-bold text-r58-text-primary">R58 Studio</h1>
        <p class="text-r58-text-secondary mt-2">
          {{ hasDevices ? 'Manage your R58 devices' : 'Connect to your first R58 device' }}
        </p>
      </div>

      <!-- Device List -->
      <div v-if="hasDevices && !showAddForm" class="space-y-4 mb-6">
        <div 
          v-for="device in devices" 
          :key="device.id"
          class="bg-r58-bg-secondary rounded-xl p-4 border-2 transition-colors"
          :class="device.id === activeDeviceId 
            ? 'border-r58-accent-primary' 
            : 'border-transparent hover:border-r58-bg-tertiary'"
        >
          <!-- Edit Mode -->
          <div v-if="editingDevice?.id === device.id" class="space-y-3">
            <input 
              v-model="editingDevice.name"
              type="text"
              placeholder="Device name"
              class="w-full px-3 py-2 bg-r58-bg-tertiary rounded-lg text-r58-text-primary"
            />
            <input 
              v-model="editingDevice.url"
              type="url"
              placeholder="Device URL"
              class="w-full px-3 py-2 bg-r58-bg-tertiary rounded-lg text-r58-text-primary"
            />
            <div class="flex gap-2">
              <button 
                @click="saveEdit"
                class="px-4 py-2 bg-r58-accent-primary text-white rounded-lg hover:bg-opacity-80"
              >
                Save
              </button>
              <button 
                @click="cancelEdit"
                class="px-4 py-2 bg-r58-bg-tertiary text-r58-text-secondary rounded-lg hover:bg-opacity-80"
              >
                Cancel
              </button>
            </div>
          </div>

          <!-- View Mode -->
          <div v-else class="flex items-center justify-between">
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2">
                <h3 class="font-medium text-r58-text-primary truncate">{{ device.name }}</h3>
                <span 
                  v-if="device.id === activeDeviceId"
                  class="px-2 py-0.5 text-xs bg-r58-accent-primary text-white rounded-full"
                >
                  Active
                </span>
              </div>
              <p class="text-sm text-r58-text-secondary truncate">{{ device.url }}</p>
              <p v-if="device.lastConnected" class="text-xs text-r58-text-tertiary mt-1">
                Last connected: {{ new Date(device.lastConnected).toLocaleString() }}
              </p>
            </div>
            
            <div class="flex items-center gap-2 ml-4">
              <button 
                v-if="device.id !== activeDeviceId"
                @click="selectDevice(device.id)"
                :disabled="isLoading"
                class="px-4 py-2 bg-r58-accent-primary text-white rounded-lg hover:bg-opacity-80 disabled:opacity-50"
              >
                Connect
              </button>
              <button 
                @click="startEdit(device)"
                class="p-2 text-r58-text-secondary hover:text-r58-text-primary rounded-lg hover:bg-r58-bg-tertiary"
                title="Edit"
              >
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                    d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
              </button>
              <button 
                @click="removeDevice(device.id)"
                class="p-2 text-r58-text-secondary hover:text-red-500 rounded-lg hover:bg-r58-bg-tertiary"
                title="Remove"
              >
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                    d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Add Device Form -->
      <div v-if="showAddForm || !hasDevices" class="bg-r58-bg-secondary rounded-xl p-6 mb-6">
        <h2 class="text-lg font-medium text-r58-text-primary mb-4">
          {{ hasDevices ? 'Add Device' : 'Add Your First Device' }}
        </h2>
        
        <div class="space-y-4">
          <div>
            <label class="block text-sm text-r58-text-secondary mb-1">Device Name (optional)</label>
            <input 
              v-model="newDeviceName"
              type="text"
              placeholder="e.g., Studio R58, Church Recorder"
              class="w-full px-4 py-3 bg-r58-bg-tertiary rounded-lg text-r58-text-primary placeholder-r58-text-tertiary focus:outline-none focus:ring-2 focus:ring-r58-accent-primary"
            />
          </div>
          
          <div>
            <label class="block text-sm text-r58-text-secondary mb-1">Device URL *</label>
            <input 
              v-model="newDeviceUrl"
              type="url"
              placeholder="https://r58-api.itagenten.no or http://192.168.1.50:8000"
              class="w-full px-4 py-3 bg-r58-bg-tertiary rounded-lg text-r58-text-primary placeholder-r58-text-tertiary focus:outline-none focus:ring-2 focus:ring-r58-accent-primary"
              :class="{ 'ring-2 ring-red-500': formError }"
            />
            <p v-if="formError" class="text-sm text-red-500 mt-1">{{ formError }}</p>
            <p class="text-xs text-r58-text-tertiary mt-1">
              Enter the full URL to your R58 device's API endpoint
            </p>
          </div>

          <!-- Test Result -->
          <div 
            v-if="testResult"
            class="p-3 rounded-lg"
            :class="testResult.success ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'"
          >
            <div class="flex items-center gap-2">
              <svg v-if="testResult.success" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
              </svg>
              <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
              <span>{{ testResult.message }}</span>
            </div>
          </div>

          <div class="flex gap-3">
            <button 
              @click="addDevice"
              :disabled="isLoading || isTesting"
              class="flex-1 px-4 py-3 bg-r58-accent-primary text-white rounded-lg font-medium hover:bg-opacity-80 disabled:opacity-50 flex items-center justify-center gap-2"
            >
              <svg v-if="isLoading || isTesting" class="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              <span>{{ isTesting ? 'Testing...' : 'Add Device' }}</span>
            </button>
            
            <button 
              v-if="hasDevices"
              @click="showAddForm = false; testResult = null; formError = ''"
              class="px-4 py-3 bg-r58-bg-tertiary text-r58-text-secondary rounded-lg hover:bg-opacity-80"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>

      <!-- Add Another Device Button -->
      <div v-if="hasDevices && !showAddForm" class="text-center">
        <button 
          @click="showAddForm = true"
          class="inline-flex items-center gap-2 px-4 py-2 text-r58-text-secondary hover:text-r58-text-primary"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
          </svg>
          Add Another Device
        </button>
      </div>

      <!-- Back Button (when devices exist) -->
      <div v-if="activeDevice" class="text-center mt-6">
        <button 
          @click="goBack"
          class="text-r58-text-secondary hover:text-r58-text-primary"
        >
          ← Back to Studio
        </button>
      </div>

      <!-- Not in Electron Warning -->
      <div v-if="!inElectron" class="mt-6 p-4 bg-yellow-500/10 border border-yellow-500/20 rounded-lg">
        <p class="text-yellow-500 text-sm">
          Device management is only available in the R58 Studio desktop app.
          <br />
          In the web version, the device is configured automatically.
        </p>
      </div>
    </div>
  </div>
</template>

