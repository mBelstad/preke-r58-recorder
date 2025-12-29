/**
 * Preload script for R58 Studio Desktop
 * 
 * Exposes a secure API to the renderer process via contextBridge.
 * This is the ONLY way for the renderer to communicate with the main process.
 */

import { contextBridge, ipcRenderer } from 'electron'

/**
 * Device configuration type
 */
interface DeviceConfig {
  id: string
  name: string
  url: string
  lastConnected?: string
  createdAt: string
}

/**
 * App info type
 */
interface AppInfo {
  version: string
  electron: string
  chrome: string
  node: string
  platform: string
  arch: string
}

/**
 * Electron API exposed to renderer
 */
const electronAPI = {
  // ============================================
  // Device Management
  // ============================================
  
  /**
   * Get the active device URL
   */
  getDeviceUrl: (): Promise<string | null> => {
    return ipcRenderer.invoke('get-device-url')
  },

  /**
   * Get all configured devices
   */
  getDevices: (): Promise<DeviceConfig[]> => {
    return ipcRenderer.invoke('get-devices')
  },

  /**
   * Get the currently active device
   */
  getActiveDevice: (): Promise<DeviceConfig | null> => {
    return ipcRenderer.invoke('get-active-device')
  },

  /**
   * Add a new device
   */
  addDevice: (name: string, url: string): Promise<DeviceConfig> => {
    return ipcRenderer.invoke('add-device', { name, url })
  },

  /**
   * Remove a device
   */
  removeDevice: (deviceId: string): Promise<boolean> => {
    return ipcRenderer.invoke('remove-device', deviceId)
  },

  /**
   * Set the active device
   */
  setActiveDevice: (deviceId: string): Promise<boolean> => {
    return ipcRenderer.invoke('set-active-device', deviceId)
  },

  /**
   * Update a device
   */
  updateDevice: (deviceId: string, updates: { name?: string; url?: string }): Promise<DeviceConfig | null> => {
    return ipcRenderer.invoke('update-device', deviceId, updates)
  },

  // ============================================
  // Event Listeners
  // ============================================

  /**
   * Listen for device changes
   */
  onDeviceChanged: (callback: (device: DeviceConfig | null) => void): (() => void) => {
    const handler = (_event: Electron.IpcRendererEvent, device: DeviceConfig | null) => {
      callback(device)
    }
    ipcRenderer.on('device-changed', handler)
    
    // Return unsubscribe function
    return () => {
      ipcRenderer.removeListener('device-changed', handler)
    }
  },

  /**
   * Listen for navigation requests from main process
   */
  onNavigate: (callback: (path: string) => void): (() => void) => {
    const handler = (_event: Electron.IpcRendererEvent, path: string) => {
      callback(path)
    }
    ipcRenderer.on('navigate', handler)
    
    return () => {
      ipcRenderer.removeListener('navigate', handler)
    }
  },

  /**
   * Listen for support bundle export request
   */
  onExportSupportBundle: (callback: () => void): (() => void) => {
    const handler = () => {
      callback()
    }
    ipcRenderer.on('export-support-bundle', handler)
    
    return () => {
      ipcRenderer.removeListener('export-support-bundle', handler)
    }
  },

  // ============================================
  // App Info & Utilities
  // ============================================

  /**
   * Get app information
   */
  getAppInfo: (): Promise<AppInfo> => {
    return ipcRenderer.invoke('get-app-info')
  },

  /**
   * Export support bundle
   */
  exportSupportBundle: (): Promise<string | null> => {
    return ipcRenderer.invoke('export-support-bundle')
  },

  /**
   * Open URL in external browser
   */
  openExternal: (url: string): Promise<boolean> => {
    return ipcRenderer.invoke('open-external', url)
  },

  // ============================================
  // Logging
  // ============================================

  /**
   * Log a message (sent to main process for file logging)
   */
  log: {
    debug: (...args: unknown[]) => ipcRenderer.send('log', 'debug', ...args),
    info: (...args: unknown[]) => ipcRenderer.send('log', 'info', ...args),
    warn: (...args: unknown[]) => ipcRenderer.send('log', 'warn', ...args),
    error: (...args: unknown[]) => ipcRenderer.send('log', 'error', ...args),
  },

  // ============================================
  // Platform Info
  // ============================================

  /**
   * Check if running in Electron
   */
  isElectron: true,

  /**
   * Get platform
   */
  platform: process.platform,
}

// Expose the API to the renderer
contextBridge.exposeInMainWorld('electronAPI', electronAPI)

// Type declaration for the renderer
declare global {
  interface Window {
    electronAPI: typeof electronAPI
    __R58_DEVICE_URL__?: string
  }
}

// Log that preload script loaded
console.log('[R58 Preload] Loaded successfully')

