/**
 * BrowserWindow management with security defaults
 */

import { BrowserWindow, shell, app } from 'electron'
import * as path from 'path'
import { log } from './logger'
import { deviceStore } from './deviceStore'

let mainWindow: BrowserWindow | null = null

// Development mode detection (lazy to support Playwright testing)
const isDev = (): boolean => !app.isPackaged

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

// ALLOWED_IFRAME_ORIGINS is now dynamic - built from device configuration
// VDO.ninja origins are added dynamically when device is configured

/**
 * Get the path to the renderer (Vue frontend)
 */
function getRendererPath(): string {
  if (isDev()) {
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
      // Allow HTTP content in HTTPS iframes (VDO.ninja) for Tailscale P2P
      // This enables direct MediaMTX connection instead of FRP tunnel
      allowRunningInsecureContent: true,
      
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

  // Open DevTools in development (unless PREKE_NO_DEVTOOLS is set)
  if (isDev() && !process.env.PREKE_NO_DEVTOOLS) {
    mainWindow.webContents.openDevTools({ mode: 'detach' })
  }

  // Handle window close
  mainWindow.on('closed', () => {
    mainWindow = null
  })

  // Log when page finishes loading
  mainWindow.webContents.on('did-finish-load', async () => {
    log.info('Renderer loaded successfully')
    
    // Only send existing active device to renderer - no auto-selection
    // Let the device setup page handle discovery and selection
    const activeDevice = deviceStore.getActiveDevice()
    
    if (activeDevice) {
      log.info(`Sending existing device to renderer: ${activeDevice.url}`)
      mainWindow?.webContents.send('device-changed', activeDevice)
    } else {
      log.info('No active device configured - renderer will show device setup')
    }
  })

  return mainWindow
}

/**
 * Setup URL rewriting to redirect FRP WHEP requests to direct connection when available
 * This dramatically improves performance when direct connection is possible
 */
function setupWhepRedirect(win: BrowserWindow): void {
  win.webContents.session.webRequest.onBeforeRequest(
    { urls: ['*://*/*/whep*'] }, // Match any WHEP URL
    (details, callback) => {
      const activeDevice = deviceStore.getActiveDevice()
      
      // Only redirect if we have a direct device connection and the request is going through FRP
      if (activeDevice) {
        try {
          const requestUrl = new URL(details.url)
          const deviceUrl = new URL(activeDevice.url)
          
          // If request is going to a different host than the device, try to redirect to device
          if (requestUrl.hostname !== deviceUrl.hostname) {
            // Extract the camera ID from the URL (e.g., /cam0/whep -> cam0)
            const match = details.url.match(/\/(cam\d+)\/whep/)
            if (match) {
              const cameraId = match[1]
              const directUrl = `http://${deviceUrl.hostname}:8889/${cameraId}/whep`
              log.info(`[WHEP P2P] Redirecting ${details.url} -> ${directUrl}`)
              callback({ redirectURL: directUrl })
              return
            }
          }
        } catch (e) {
          // Invalid URL, continue with original
        }
      }
      
      // No redirect - use original URL
      callback({})
    }
  )
  log.info('WHEP redirect enabled - will use direct connection when available')
}

/**
 * Setup navigation security to prevent unauthorized navigation
 */
function setupNavigationSecurity(win: BrowserWindow): void {
  // Setup WHEP redirect for P2P performance
  setupWhepRedirect(win)
  
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
    
    // Open HTTPS URLs in external browser
    if (url.startsWith('https://')) {
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

    // Allow VDO.ninja iframes (check if URL looks like VDO.ninja)
    // VDO.ninja URLs are typically: https://<host>/mixer.html or https://<host>/?director=...
    const isVdoUrl = details.url.includes('/mixer.html') || 
                     details.url.includes('?director=') ||
                     details.url.includes('?room=')
    
    if (isVdoUrl && details.responseHeaders) {
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

