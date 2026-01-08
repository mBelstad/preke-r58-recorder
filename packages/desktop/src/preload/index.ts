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
 * Discovered device type
 */
interface DiscoveredDevice {
  id: string
  name: string
  host: string
  port: number
  url: string
  source: 'mdns' | 'probe' | 'hostname' | 'tailscale'
  status?: string
  version?: string
  /** Tailscale-specific: whether connection is P2P or via DERP relay */
  isP2P?: boolean
  /** Tailscale-specific: latency in ms */
  latencyMs?: number
  /** Tailscale IP if discovered via Tailscale */
  tailscaleIp?: string
}

/**
 * Tailscale status type
 */
interface TailscaleStatus {
  installed: boolean
  running: boolean
  loggedIn: boolean
  selfIp?: string
  selfHostname?: string
  version?: string
  error?: string
}

/**
 * Tailscale device type
 */
interface TailscaleDevice {
  id: string
  name: string
  hostname: string
  tailscaleIp: string
  online: boolean
  os?: string
  isP2P: boolean
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
  // Device Discovery
  // ============================================

  /**
   * Start network discovery for Preke devices
   */
  startDiscovery: (): void => {
    ipcRenderer.send('discovery:start')
  },

  /**
   * Stop ongoing discovery
   */
  stopDiscovery: (): void => {
    ipcRenderer.send('discovery:stop')
  },

  /**
   * Probe a specific URL to check if it's a Preke device
   */
  probeDevice: (url: string): Promise<DiscoveredDevice | null> => {
    return ipcRenderer.invoke('discovery:probe', url)
  },

  /**
   * Check if discovery is currently running
   */
  isDiscovering: (): Promise<boolean> => {
    return ipcRenderer.invoke('discovery:is-scanning')
  },

  /**
   * Listen for discovery started
   */
  onDiscoveryStarted: (callback: () => void): (() => void) => {
    const handler = () => callback()
    ipcRenderer.on('discovery:started', handler)
    return () => ipcRenderer.removeListener('discovery:started', handler)
  },

  /**
   * Listen for device found during discovery
   */
  onDeviceDiscovered: (callback: (device: DiscoveredDevice) => void): (() => void) => {
    const handler = (_event: Electron.IpcRendererEvent, device: DiscoveredDevice) => callback(device)
    ipcRenderer.on('discovery:device-found', handler)
    return () => ipcRenderer.removeListener('discovery:device-found', handler)
  },

  /**
   * Listen for subnet scanning progress
   */
  onScanningSubnet: (callback: (subnet: string) => void): (() => void) => {
    const handler = (_event: Electron.IpcRendererEvent, subnet: string) => callback(subnet)
    ipcRenderer.on('discovery:scanning-subnet', handler)
    return () => ipcRenderer.removeListener('discovery:scanning-subnet', handler)
  },

  /**
   * Listen for discovery complete
   */
  onDiscoveryComplete: (callback: (devices: DiscoveredDevice[]) => void): (() => void) => {
    const handler = (_event: Electron.IpcRendererEvent, devices: DiscoveredDevice[]) => callback(devices)
    ipcRenderer.on('discovery:complete', handler)
    return () => ipcRenderer.removeListener('discovery:complete', handler)
  },

  /**
   * Listen for discovery phase changes
   */
  onDiscoveryPhase: (callback: (phase: { phase: string; message: string }) => void): (() => void) => {
    const handler = (_event: Electron.IpcRendererEvent, phase: { phase: string; message: string }) => callback(phase)
    ipcRenderer.on('discovery:phase', handler)
    return () => ipcRenderer.removeListener('discovery:phase', handler)
  },

  // ============================================
  // Tailscale P2P
  // ============================================

  /**
   * Get Tailscale status
   * Checks if Tailscale is installed, running, and logged in
   */
  getTailscaleStatus: (): Promise<TailscaleStatus> => {
    return ipcRenderer.invoke('tailscale:status')
  },

  /**
   * Find R58 devices on Tailscale network
   * Returns devices that are online and running R58 API
   */
  findTailscaleDevices: (): Promise<TailscaleDevice[]> => {
    return ipcRenderer.invoke('tailscale:find-devices')
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

  /**
   * Get recent logs from the main process log file
   * Useful for debugging and MCP integration
   */
  getRecentLogs: (maxLines?: number): Promise<{ logs: string; path: string }> => {
    return ipcRenderer.invoke('get-recent-logs', maxLines)
  },

  // ============================================
  // Auto-Updates
  // ============================================

  /**
   * Check for app updates
   */
  checkForUpdates: (): Promise<{
    updateAvailable: boolean
    version?: string
    releaseDate?: Date
    releaseNotes?: string
    error?: string
  }> => {
    return ipcRenderer.invoke('check-for-updates')
  },

  /**
   * Download the available update
   */
  downloadUpdate: (): Promise<{ success: boolean; error?: string }> => {
    return ipcRenderer.invoke('download-update')
  },

  /**
   * Install the downloaded update and restart
   */
  installUpdate: (): void => {
    ipcRenderer.invoke('install-update')
  },

  /**
   * Get current app version
   */
  getCurrentVersion: (): Promise<string> => {
    return ipcRenderer.invoke('get-current-version')
  },

  /**
   * Listen for update checking
   */
  onUpdateChecking: (callback: () => void): (() => void) => {
    const handler = () => callback()
    ipcRenderer.on('update-checking', handler)
    return () => ipcRenderer.removeListener('update-checking', handler)
  },

  /**
   * Listen for update available
   */
  onUpdateAvailable: (callback: (info: { version: string; releaseDate?: Date; releaseNotes?: string }) => void): (() => void) => {
    const handler = (_event: Electron.IpcRendererEvent, info: { version: string; releaseDate?: Date; releaseNotes?: string }) => callback(info)
    ipcRenderer.on('update-available', handler)
    return () => ipcRenderer.removeListener('update-available', handler)
  },

  /**
   * Listen for update not available
   */
  onUpdateNotAvailable: (callback: (info: { version: string }) => void): (() => void) => {
    const handler = (_event: Electron.IpcRendererEvent, info: { version: string }) => callback(info)
    ipcRenderer.on('update-not-available', handler)
    return () => ipcRenderer.removeListener('update-not-available', handler)
  },

  /**
   * Listen for update error
   */
  onUpdateError: (callback: (error: { message: string }) => void): (() => void) => {
    const handler = (_event: Electron.IpcRendererEvent, error: { message: string }) => callback(error)
    ipcRenderer.on('update-error', handler)
    return () => ipcRenderer.removeListener('update-error', handler)
  },

  /**
   * Listen for download progress
   */
  onUpdateDownloadProgress: (callback: (progress: { percent: number; transferred: number; total: number }) => void): (() => void) => {
    const handler = (_event: Electron.IpcRendererEvent, progress: { percent: number; transferred: number; total: number }) => callback(progress)
    ipcRenderer.on('update-download-progress', handler)
    return () => ipcRenderer.removeListener('update-download-progress', handler)
  },

  /**
   * Listen for update downloaded
   */
  onUpdateDownloaded: (callback: (info: { version: string; releaseDate?: Date; releaseNotes?: string }) => void): (() => void) => {
    const handler = (_event: Electron.IpcRendererEvent, info: { version: string; releaseDate?: Date; releaseNotes?: string }) => callback(info)
    ipcRenderer.on('update-downloaded', handler)
    return () => ipcRenderer.removeListener('update-downloaded', handler)
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

  // ============================================
  // DaVinci Resolve Integration
  // ============================================

  /**
   * Start DaVinci Resolve integration (polls R58 for recording changes)
   */
  davinciStart: (): Promise<{ success: boolean }> => {
    return ipcRenderer.invoke('davinci-start')
  },

  /**
   * Stop DaVinci Resolve integration
   */
  davinciStop: (): Promise<{ success: boolean }> => {
    return ipcRenderer.invoke('davinci-stop')
  },

  /**
   * Get DaVinci integration status
   */
  davinciStatus: (): Promise<{
    enabled: boolean
    resolveConnected: boolean
    currentSession: string | null
  }> => {
    return ipcRenderer.invoke('davinci-status')
  },

  /**
   * Check if DaVinci Resolve is running and accessible
   */
  davinciCheckResolve: (): Promise<{
    connected: boolean
    scriptPath: string | null
  }> => {
    return ipcRenderer.invoke('davinci-check-resolve')
  },

  /**
   * Update DaVinci config
   */
  davinciConfig: (config?: {
    pollIntervalMs?: number
    projectNamePrefix?: string
    autoCreateProject?: boolean
    autoImportMedia?: boolean
    createMulticamTimeline?: boolean
  }): Promise<{
    enabled: boolean
    pollIntervalMs: number
    projectNamePrefix: string
    autoCreateProject: boolean
    autoImportMedia: boolean
    createMulticamTimeline: boolean
  }> => {
    return ipcRenderer.invoke('davinci-config', config)
  },

  /**
   * Listen for DaVinci session start events
   */
  onDavinciSessionStart: (callback: (data: {
    sessionId: string
    startTime: string
    cameras: Record<string, unknown>
  }) => void): (() => void) => {
    const handler = (_event: Electron.IpcRendererEvent, data: {
      sessionId: string
      startTime: string
      cameras: Record<string, unknown>
    }) => callback(data)
    ipcRenderer.on('davinci-session-start', handler)
    return () => ipcRenderer.removeListener('davinci-session-start', handler)
  },

  /**
   * Listen for DaVinci session stop events
   */
  onDavinciSessionStop: (callback: (data: {
    sessionId: string
    cameras: Record<string, unknown>
    filePaths: string[]
  }) => void): (() => void) => {
    const handler = (_event: Electron.IpcRendererEvent, data: {
      sessionId: string
      cameras: Record<string, unknown>
      filePaths: string[]
    }) => callback(data)
    ipcRenderer.on('davinci-session-stop', handler)
    return () => ipcRenderer.removeListener('davinci-session-stop', handler)
  },

  /**
   * Listen for DaVinci connection changes
   */
  onDavinciConnectionChanged: (callback: (data: { connected: boolean }) => void): (() => void) => {
    const handler = (_event: Electron.IpcRendererEvent, data: { connected: boolean }) => callback(data)
    ipcRenderer.on('davinci-connection-changed', handler)
    return () => ipcRenderer.removeListener('davinci-connection-changed', handler)
  },

  /**
   * Open or create a DaVinci Resolve project (launches Resolve if not running)
   */
  davinciOpenProject: (projectName?: string): Promise<{
    success: boolean
    error?: string
    projectName?: string
  }> => {
    return ipcRenderer.invoke('davinci-open-project', projectName)
  },

  /**
   * Create a multicam timeline from clips
   */
  davinciCreateMulticam: (options: {
    projectName?: string
    clipName?: string
    filePaths?: string[]
    syncMethod?: string
    sessionId?: string
  }): Promise<{
    success: boolean
    error?: string
    timelineName?: string
    filesImported?: number
  }> => {
    return ipcRenderer.invoke('davinci-create-multicam', options)
  },

  /**
   * Check if R58 recordings are mounted via SMB
   */
  davinciCheckMount: (): Promise<{
    mounted: boolean
    path: string | null
    hint: string | null
  }> => {
    return ipcRenderer.invoke('davinci-check-mount')
  },

  /**
   * Get recent recording files from mounted share
   */
  davinciGetRecordings: (sessionPattern?: string): Promise<string[]> => {
    return ipcRenderer.invoke('davinci-get-recordings', sessionPattern)
  },
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

