/**
 * BrowserWindow management with security defaults
 */

import { BrowserWindow, shell, app } from 'electron'
import * as path from 'path'
import { log } from './logger'
import { deviceStore } from './deviceStore'

let mainWindow: BrowserWindow | null = null

// Development mode detection
const isDev = !app.isPackaged

// Vite dev server URL (for hot reload development)
const VITE_DEV_SERVER_URL = process.env.VITE_DEV_SERVER_URL

/**
 * Allowed origins for navigation and iframe embedding
 */
const ALLOWED_NAVIGATION_ORIGINS = [
  'file://',                          // Local UI
  'http://localhost:5173',            // Vite dev server
  'http://localhost:5174',            // Vite fallback port
]

const ALLOWED_IFRAME_ORIGINS = [
  'https://r58-vdo.itagenten.no',     // Self-hosted VDO.ninja
  'https://vdo.itagenten.no',         // Alternate VDO.ninja
  'https://vdo.ninja',                // Public VDO.ninja (fallback)
]

/**
 * Get the path to the renderer (Vue frontend)
 */
function getRendererPath(): string {
  if (isDev) {
    // In development, load from the frontend dev server or built files
    return path.join(__dirname, '../../app/renderer/index.html')
  }
  // In production, load from extraResources
  return path.join(process.resourcesPath, 'renderer', 'index.html')
}

/**
 * Create the main application window
 */
export function createMainWindow(): BrowserWindow {
  log.info('Creating main window...')
  
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1024,
    minHeight: 768,
    title: 'Preke Studio',
    backgroundColor: '#0f172a', // Match app theme
    
    webPreferences: {
      // SECURITY: Mandatory settings
      contextIsolation: true,
      sandbox: true,
      nodeIntegration: false,
      
      // Preload script for IPC
      preload: path.join(__dirname, '../preload/index.js'),
      
      // Additional security
      webSecurity: true,
      allowRunningInsecureContent: false,
      
      // Performance
      spellcheck: false,
    },
    
    // macOS specific
    titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default',
    trafficLightPosition: { x: 16, y: 16 },
    
    show: false, // Show when ready to prevent flash
  })

  // Show window when ready
  mainWindow.once('ready-to-show', () => {
    mainWindow?.show()
    log.info('Main window shown')
  })

  // Setup navigation security
  setupNavigationSecurity(mainWindow)

  // Load from dev server or file
  if (VITE_DEV_SERVER_URL) {
    log.info(`Loading from Vite dev server: ${VITE_DEV_SERVER_URL}`)
    mainWindow.loadURL(VITE_DEV_SERVER_URL).catch((error) => {
      log.error('Failed to load from dev server:', error)
    })
  } else {
    const rendererPath = getRendererPath()
    log.info(`Loading renderer from: ${rendererPath}`)
    mainWindow.loadFile(rendererPath).catch((error) => {
      log.error('Failed to load renderer:', error)
    })
  }

  // Open DevTools in development
  if (isDev) {
    mainWindow.webContents.openDevTools({ mode: 'detach' })
  }

  // Handle window close
  mainWindow.on('closed', () => {
    mainWindow = null
  })

  // Log when page finishes loading
  mainWindow.webContents.on('did-finish-load', async () => {
    log.info('Renderer loaded successfully')
    
    // Check for P2P devices if no active device or current is FRP
    let activeDevice = deviceStore.getActiveDevice()
    
    if (!activeDevice || activeDevice.url.includes('itagenten.no')) {
      log.info('Checking for P2P devices on startup...')
      try {
        const { findR58DevicesOnTailscale } = await import('./tailscale')
        const tailscaleDevices = await findR58DevicesOnTailscale()
        
        for (const tsDevice of tailscaleDevices) {
          if (tsDevice.isP2P) {
            const p2pUrl = `http://${tsDevice.tailscaleIp}:8000`
            log.info(`Found P2P device on startup: ${tsDevice.name} at ${p2pUrl}`)
            
            // Add or update device
            let device = deviceStore.getDevices().find(d => d.url === p2pUrl)
            if (!device) {
              device = deviceStore.addDevice(tsDevice.name, p2pUrl)
            }
            
            // Set as active
            deviceStore.setActiveDevice(device.id)
            activeDevice = device
            log.info(`Auto-selected P2P device: ${device.name}`)
            break
          }
        }
      } catch (e) {
        log.warn('Failed to check for P2P devices:', e)
      }
    }
    
    // Send device info to renderer
    if (activeDevice) {
      log.info(`Sending device to renderer: ${activeDevice.url}`)
      mainWindow?.webContents.send('device-changed', activeDevice)
    }
  })

  return mainWindow
}

/**
 * Setup navigation security to prevent unauthorized navigation
 */
function setupNavigationSecurity(win: BrowserWindow): void {
  // Skip navigation security in dev mode with Vite (HMR needs freedom)
  if (VITE_DEV_SERVER_URL) {
    log.info('Dev mode: Navigation security relaxed for Vite HMR')
    return
  }

  // Block navigation to unauthorized origins
  win.webContents.on('will-navigate', (event, url) => {
    const isAllowed = ALLOWED_NAVIGATION_ORIGINS.some(origin => url.startsWith(origin))
    
    if (!isAllowed) {
      log.warn(`Blocked navigation to: ${url}`)
      event.preventDefault()
    }
  })

  // Handle new window requests (e.g., target="_blank" links)
  win.webContents.setWindowOpenHandler(({ url }) => {
    log.info(`New window requested for: ${url}`)
    
    // Check if it's a VDO.ninja related URL - open in external browser
    const isVdoUrl = ALLOWED_IFRAME_ORIGINS.some(origin => url.startsWith(origin))
    
    if (isVdoUrl || url.startsWith('https://')) {
      shell.openExternal(url)
    }
    
    // Always deny opening new Electron windows
    return { action: 'deny' }
  })

  // Block loading of unauthorized iframes (except allowed ones)
  win.webContents.session.webRequest.onHeadersReceived((details, callback) => {
    // Allow device API requests (configured device URLs)
    const activeDevice = deviceStore.getActiveDevice()
    if (activeDevice && details.url.startsWith(activeDevice.url)) {
      callback({ responseHeaders: details.responseHeaders })
      return
    }

    // Allow VDO.ninja iframes
    const isAllowedIframe = ALLOWED_IFRAME_ORIGINS.some(origin => 
      details.url.startsWith(origin)
    )
    
    if (isAllowedIframe && details.responseHeaders) {
      // Remove X-Frame-Options to allow embedding
      delete details.responseHeaders['x-frame-options']
      delete details.responseHeaders['X-Frame-Options']
    }

    callback({ responseHeaders: details.responseHeaders })
  })
}

/**
 * Get the main window instance
 */
export function getMainWindow(): BrowserWindow | null {
  return mainWindow
}

/**
 * Focus the main window
 */
export function focusMainWindow(): void {
  if (mainWindow) {
    if (mainWindow.isMinimized()) mainWindow.restore()
    mainWindow.focus()
  }
}

/**
 * Reload the main window
 */
export function reloadMainWindow(): void {
  mainWindow?.reload()
}

/**
 * Toggle DevTools
 */
export function toggleDevTools(): void {
  mainWindow?.webContents.toggleDevTools()
}

/**
 * Navigate to device setup page
 */
export function showDeviceSetup(): void {
  mainWindow?.webContents.send('navigate', '/device-setup')
}

