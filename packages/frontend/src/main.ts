import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import { initializeDeviceUrl, setDeviceUrl, disableFrpFallback } from './lib/api'
import { platform } from './lib/platform'

// Global styles - Preke Design System v3
import './styles/preke-design-system.css'
import './style.css'

// Initialize theme before app mounts (prevent flash)
function initializeTheme() {
  try {
    const stored = localStorage.getItem('preke-theme')
    const root = document.documentElement
    if (stored === 'light') {
      root.setAttribute('data-theme', 'light')
    } else {
      root.setAttribute('data-theme', 'dark')
    }
  } catch (error) {
    // Use default (dark)
    document.documentElement.setAttribute('data-theme', 'dark')
  }
}

// Initialize theme immediately
initializeTheme()

/**
 * Initialize the application
 */
async function initApp() {
  const app = createApp(App)
  const pinia = createPinia()

  app.use(pinia)
  app.use(router)

  // Electron-specific initialization
  if (platform.isElectron()) {
    console.log('[App] Running in Electron mode')
    
    // Add platform-specific classes to body for CSS targeting
    platform.getBodyClasses().forEach(cls => {
      document.body.classList.add(cls)
      document.documentElement.classList.add(cls)
    })
    
    const isTailscaleUrl = (url: string): boolean => {
      try {
        const host = new URL(url).hostname
        return host.startsWith('100.') || host.endsWith('.ts.net')
      } catch {
        return false
      }
    }

    const normalizeName = (name: string): string => name.replace(/\s*\(.*\)\s*$/, '').trim().toLowerCase()

    const maybePromoteLanDevice = async () => {
      if (!window.electronAPI) return
      const active = await window.electronAPI.getActiveDevice()
      if (!active || !isTailscaleUrl(active.url)) return

      let promoted = false
      const activeName = normalizeName(active.name || '')

      const cleanup = window.electronAPI.onDeviceDiscovered(async (device) => {
        if (promoted || device.source === 'tailscale') return
        const incomingName = normalizeName(device.name || '')
        if (activeName && incomingName && activeName !== incomingName) return

        try {
          const devices = await window.electronAPI?.getDevices()
          const existing = devices?.find(d => d.url === device.url)
          const added = existing || await window.electronAPI?.addDevice(device.name, device.url, active.url)
          if (added) {
            console.log('[App] Promoting LAN device over Tailscale:', added.url)
            await window.electronAPI?.setActiveDevice(added.id)
            promoted = true
            window.electronAPI?.stopDiscovery()
            cleanup()
          }
        } catch (error) {
          console.warn('[App] Failed to promote LAN device:', error)
        }
      })

      window.electronAPI.startDiscovery()
    }

    // Initialize device URL before mounting
    const deviceUrl = await initializeDeviceUrl()
    
    // If no device configured, redirect to setup
    if (!deviceUrl) {
      console.log('[App] No device configured, redirecting to setup')
      router.push('/device-setup')
    } else if (isTailscaleUrl(deviceUrl)) {
      maybePromoteLanDevice()
    }

    // Listen for device changes from main process
    // Track current device to avoid reload loops
    let currentDeviceUrl = deviceUrl
    
    window.electronAPI?.onDeviceChanged((device) => {
      console.log('[App] Device changed:', device)
      const newUrl = device?.url || null
      
      // Reset FRP fallback when we get a direct device URL
      if (newUrl && !newUrl.includes('itagenten.no')) {
        console.log('[App] Direct device URL received, resetting FRP fallback')
        disableFrpFallback()
      }
      
      // Only reload if device actually changed (not on initial load)
      if (newUrl !== currentDeviceUrl && currentDeviceUrl !== null) {
        console.log('[App] Device URL changed, reloading...')
        setDeviceUrl(newUrl)
        currentDeviceUrl = newUrl
        router.go(0)
      } else {
        // Just update without reload (initial load)
        setDeviceUrl(newUrl)
        currentDeviceUrl = newUrl
      }
    })

    // Listen for navigation requests from main process
    window.electronAPI?.onNavigate((path) => {
      console.log('[App] Navigate to:', path)
      router.push(path)
    })

    // Listen for support bundle export request
    window.electronAPI?.onExportSupportBundle(async () => {
      try {
        const filePath = await window.electronAPI?.exportSupportBundle()
        if (filePath) {
          console.log('[App] Support bundle exported:', filePath)
          // Could show a toast notification here
        }
      } catch (error) {
        console.error('[App] Failed to export support bundle:', error)
      }
    })
  }

  app.mount('#app')
}

// Start the app
initApp().catch((error) => {
  console.error('[App] Failed to initialize:', error)
})
