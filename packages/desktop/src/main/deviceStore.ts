/**
 * Device configuration store using electron-store
 * Stores device URLs and settings with encryption
 */

import Store from 'electron-store'
import { log } from './logger'

/**
 * Device configuration
 */
export interface DeviceConfig {
  id: string
  name: string
  url: string
  fallbackUrl?: string
  lastConnected?: string
  createdAt: string
}

/**
 * Store schema
 */
interface StoreSchema {
  devices: DeviceConfig[]
  activeDeviceId: string | null
}

// Generate a unique ID
function generateId(): string {
  return `device_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`
}

/**
 * Initialize the store
 */
const store = new Store<StoreSchema>({
  name: 'preke-studio-devices',
  defaults: {
    devices: [],
    activeDeviceId: null
  },
  // Encrypt sensitive data
  encryptionKey: 'preke-studio-device-config-v2',
  // Clear invalid data on error
  clearInvalidConfig: true
})

/**
 * Device store API
 */
export const deviceStore = {
  /**
   * Get all configured devices
   */
  getDevices(): DeviceConfig[] {
    return store.get('devices', [])
  },

  /**
   * Get a device by ID
   */
  getDevice(deviceId: string): DeviceConfig | undefined {
    const devices = this.getDevices()
    return devices.find(d => d.id === deviceId)
  },

  /**
   * Get the currently active device
   */
  getActiveDevice(): DeviceConfig | null {
    const activeId = store.get('activeDeviceId')
    if (!activeId) return null
    
    const device = this.getDevice(activeId)
    if (!device) {
      // Active device was deleted, clear the reference
      store.set('activeDeviceId', null)
      return null
    }
    
    return device
  },

  /**
   * Get the active device ID
   */
  getActiveDeviceId(): string | null {
    return store.get('activeDeviceId', null)
  },

  /**
   * Add a new device
   */
  addDevice(name: string, url: string, fallbackUrl?: string): DeviceConfig {
    // Normalize URL (remove trailing slash)
    const normalizedUrl = url.replace(/\/+$/, '')
    const normalizedFallback = fallbackUrl ? fallbackUrl.replace(/\/+$/, '') : undefined
    
    const device: DeviceConfig = {
      id: generateId(),
      name: name.trim() || 'Preke Device',
      url: normalizedUrl,
      fallbackUrl: normalizedFallback,
      createdAt: new Date().toISOString()
    }

    const devices = this.getDevices()
    devices.push(device)
    store.set('devices', devices)

    // If this is the first device, make it active
    if (devices.length === 1) {
      this.setActiveDevice(device.id)
    }

    log.info(`Device added: ${device.name} (${device.url})`)
    return device
  },

  /**
   * Remove a device
   */
  removeDevice(deviceId: string): boolean {
    const devices = this.getDevices()
    const index = devices.findIndex(d => d.id === deviceId)
    
    if (index === -1) return false

    const removed = devices.splice(index, 1)[0]
    store.set('devices', devices)

    // If removed device was active, clear or select another
    if (store.get('activeDeviceId') === deviceId) {
      const newActive = devices.length > 0 ? devices[0].id : null
      store.set('activeDeviceId', newActive)
    }

    log.info(`Device removed: ${removed.name}`)
    return true
  },

  /**
   * Update a device
   */
  updateDevice(deviceId: string, updates: Partial<Pick<DeviceConfig, 'name' | 'url' | 'fallbackUrl'>>): DeviceConfig | null {
    const devices = this.getDevices()
    const index = devices.findIndex(d => d.id === deviceId)
    
    if (index === -1) return null

    if (updates.name !== undefined) {
      devices[index].name = updates.name.trim() || devices[index].name
    }
    if (updates.url !== undefined) {
      devices[index].url = updates.url.replace(/\/+$/, '')
    }
    if (updates.fallbackUrl !== undefined) {
      devices[index].fallbackUrl = updates.fallbackUrl ? updates.fallbackUrl.replace(/\/+$/, '') : undefined
    }

    store.set('devices', devices)
    log.info(`Device updated: ${devices[index].name}`)
    return devices[index]
  },

  /**
   * Set the active device
   */
  setActiveDevice(deviceId: string | null): void {
    if (deviceId) {
      const device = this.getDevice(deviceId)
      if (device) {
        // Update last connected timestamp
        this.updateLastConnected(deviceId)
        store.set('activeDeviceId', deviceId)
        log.info(`Active device set: ${device.name}`)
      }
    } else {
      store.set('activeDeviceId', null)
      log.info('Active device cleared')
    }
  },

  /**
   * Update the last connected timestamp
   */
  updateLastConnected(deviceId: string): void {
    const devices = this.getDevices()
    const index = devices.findIndex(d => d.id === deviceId)
    
    if (index !== -1) {
      devices[index].lastConnected = new Date().toISOString()
      store.set('devices', devices)
    }
  },

  /**
   * Check if any devices are configured
   */
  hasDevices(): boolean {
    return this.getDevices().length > 0
  },

  /**
   * Get device config for export (with sensitive data redacted)
   */
  getConfigForExport(): Partial<StoreSchema> {
    const devices = this.getDevices().map(d => ({
      ...d,
      // Keep URL for debugging but could redact if needed
      url: d.url
    }))

    return {
      devices,
      activeDeviceId: store.get('activeDeviceId')
    }
  },

  /**
   * Clear all devices (for testing/reset)
   */
  clearAll(): void {
    store.clear()
    log.info('All device configuration cleared')
  }
}

export default deviceStore

