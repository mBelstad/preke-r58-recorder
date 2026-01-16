/**
 * Preke Studio Desktop - Main Process Entry
 * 
 * This is the main entry point for the Electron application.
 * It handles app lifecycle, window creation, and IPC communication.
 */

import { app, BrowserWindow, ipcMain, dialog, shell } from 'electron'
import * as path from 'path'
import { createMainWindow, getMainWindow } from './window'
import { createApplicationMenu } from './menu'
import { deviceStore } from './deviceStore'
import { initializeLogger, log, exportSupportBundle, readRecentLogs, getLogFilePath } from './logger'
import { setupDiscoveryHandlers } from './discovery'
import { setupUpdateListeners, checkForUpdates, downloadUpdate, installUpdate, getCurrentVersion } from './updater'
import { setupDaVinciHandlers } from './davinci'

// Prevent multiple instances
const gotTheLock = app.requestSingleInstanceLock()
if (!gotTheLock) {
  console.error('Another instance is already running')
  app.quit()
  process.exit(1)
}

// Initialize logger early
initializeLogger()

log.info('Preke Studio starting...')
log.info(`Version: ${app.getVersion()}`)
log.info(`Electron: ${process.versions.electron}`)
log.info(`Chrome: ${process.versions.chrome}`)
log.info(`Node: ${process.versions.node}`)
log.info('Got single instance lock, waiting for app ready...')

/**
 * Handle certificate errors for self-signed certificates on user-configured devices
 */
app.on('certificate-error', (event, _webContents, url, _error, _cert, callback) => {
  const activeDevice = deviceStore.getActiveDevice()
  
  // Only allow certificate bypass for user-configured device URLs
  if (activeDevice && url.startsWith(activeDevice.url)) {
    log.warn(`Allowing self-signed certificate for configured device: ${activeDevice.url}`)
    event.preventDefault()
    callback(true)
  } else {
    log.warn(`Rejecting certificate for unknown origin: ${url}`)
    callback(false)
  }
})

/**
 * Register IPC handlers
 */
function registerIpcHandlers(): void {
  // Device management
  ipcMain.handle('get-device-url', () => {
    const device = deviceStore.getActiveDevice()
    return device?.url || null
  })

  ipcMain.handle('get-devices', () => {
    return deviceStore.getDevices()
  })

  ipcMain.handle('get-active-device', () => {
    return deviceStore.getActiveDevice()
  })

  ipcMain.handle('add-device', (_event, device: { name: string; url: string; fallbackUrl?: string }) => {
    return deviceStore.addDevice(device.name, device.url, device.fallbackUrl)
  })

  ipcMain.handle('remove-device', (_event, deviceId: string) => {
    return deviceStore.removeDevice(deviceId)
  })

  ipcMain.handle('set-active-device', (_event, deviceId: string) => {
    deviceStore.setActiveDevice(deviceId)
    // Notify renderer that device changed
    const win = getMainWindow()
    if (win) {
      win.webContents.send('device-changed', deviceStore.getActiveDevice())
    }
    return true
  })

  ipcMain.handle('update-device', (_event, deviceId: string, updates: { name?: string; url?: string; fallbackUrl?: string }) => {
    return deviceStore.updateDevice(deviceId, updates)
  })

  // Support bundle export
  ipcMain.handle('export-support-bundle', async () => {
    const win = getMainWindow()
    if (!win) return null

    const { canceled, filePath } = await dialog.showSaveDialog(win, {
      title: 'Export Support Bundle',
      defaultPath: `preke-studio-support-bundle-${Date.now()}.zip`,
      filters: [{ name: 'ZIP Archive', extensions: ['zip'] }]
    })

    if (canceled || !filePath) return null

    try {
      await exportSupportBundle(filePath)
      return filePath
    } catch (error) {
      log.error('Failed to export support bundle:', error)
      throw error
    }
  })

  // App info
  ipcMain.handle('get-app-info', () => {
    return {
      version: app.getVersion(),
      electron: process.versions.electron,
      chrome: process.versions.chrome,
      node: process.versions.node,
      platform: process.platform,
      arch: process.arch,
    }
  })

  // Open external URL
  ipcMain.handle('open-external', (_event, url: string) => {
    // Validate URL before opening
    try {
      const parsed = new URL(url)
      if (parsed.protocol === 'https:' || parsed.protocol === 'http:') {
        shell.openExternal(url)
        return true
      }
    } catch {
      log.warn('Invalid URL for external open:', url)
    }
    return false
  })

  // Logging from renderer
  ipcMain.on('log', (_event, level: string, ...args: unknown[]) => {
    switch (level) {
      case 'error':
        log.error('[Renderer]', ...args)
        break
      case 'warn':
        log.warn('[Renderer]', ...args)
        break
      case 'info':
        log.info('[Renderer]', ...args)
        break
      default:
        log.debug('[Renderer]', ...args)
    }
  })

  // Get recent logs from file (for debugging/MCP integration)
  ipcMain.handle('get-recent-logs', (_event, maxLines?: number) => {
    return {
      logs: readRecentLogs(maxLines || 100),
      path: getLogFilePath()
    }
  })

  // Update management
  ipcMain.handle('check-for-updates', async () => {
    return await checkForUpdates()
  })

  ipcMain.handle('download-update', async () => {
    return await downloadUpdate()
  })

  ipcMain.handle('install-update', () => {
    installUpdate()
  })

  ipcMain.handle('get-current-version', () => {
    return getCurrentVersion()
  })
}

/**
 * App ready handler
 */
app.whenReady().then(() => {
  log.info('App ready, creating window...')
  
  // Register IPC handlers before creating window
  registerIpcHandlers()
  
  // Register discovery handlers
  setupDiscoveryHandlers(getMainWindow)
  
  // Register DaVinci Resolve integration handlers
  setupDaVinciHandlers(getMainWindow)
  
  // Setup update listeners (must be after window creation)
  setupUpdateListeners()
  
  // Create application menu
  createApplicationMenu()
  
  // Create main window
  createMainWindow()
  
  // Check for updates on startup (after a short delay to not block UI)
  setTimeout(() => {
    log.info('Checking for updates on startup...')
    checkForUpdates().catch((error) => {
      log.warn('Failed to check for updates on startup:', error)
    })
  }, 5000) // Wait 5 seconds after app start
  
  // macOS: Re-create window when dock icon is clicked
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createMainWindow()
    }
  })
})

/**
 * Handle second instance (focus existing window)
 */
app.on('second-instance', () => {
  const win = getMainWindow()
  if (win) {
    if (win.isMinimized()) win.restore()
    win.focus()
  }
})

/**
 * Quit when all windows are closed (except on macOS)
 */
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

/**
 * Clean up before quit
 */
app.on('before-quit', () => {
  log.info('App quitting...')
})

// Handle uncaught exceptions
process.on('uncaughtException', (error) => {
  log.error('Uncaught exception:', error)
})

process.on('unhandledRejection', (reason) => {
  log.error('Unhandled rejection:', reason)
})

