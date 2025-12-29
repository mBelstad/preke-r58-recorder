/**
 * Type declarations for Electron API exposed via preload
 */

export interface DeviceConfig {
  id: string
  name: string
  url: string
  lastConnected?: string
  createdAt: string
}

export interface AppInfo {
  version: string
  electron: string
  chrome: string
  node: string
  platform: string
  arch: string
}

export interface ElectronAPI {
  // Device Management
  getDeviceUrl: () => Promise<string | null>
  getDevices: () => Promise<DeviceConfig[]>
  getActiveDevice: () => Promise<DeviceConfig | null>
  addDevice: (name: string, url: string) => Promise<DeviceConfig>
  removeDevice: (deviceId: string) => Promise<boolean>
  setActiveDevice: (deviceId: string) => Promise<boolean>
  updateDevice: (deviceId: string, updates: { name?: string; url?: string }) => Promise<DeviceConfig | null>

  // Event Listeners
  onDeviceChanged: (callback: (device: DeviceConfig | null) => void) => () => void
  onNavigate: (callback: (path: string) => void) => () => void
  onExportSupportBundle: (callback: () => void) => () => void

  // App Info & Utilities
  getAppInfo: () => Promise<AppInfo>
  exportSupportBundle: () => Promise<string | null>
  openExternal: (url: string) => Promise<boolean>

  // Logging
  log: {
    debug: (...args: unknown[]) => void
    info: (...args: unknown[]) => void
    warn: (...args: unknown[]) => void
    error: (...args: unknown[]) => void
  }

  // Platform Info
  isElectron: boolean
  platform: string
}

declare global {
  interface Window {
    electronAPI?: ElectronAPI
    __R58_DEVICE_URL__?: string
  }
  
  // Build-time constant
  const __ELECTRON__: boolean
}

export {}

