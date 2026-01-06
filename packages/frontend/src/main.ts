import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import { initializeDeviceUrl, setDeviceUrl, isElectron, disableFrpFallback } from './lib/api'

// Global styles - Preke Design System v3
import './styles/preke-design-system.css'
import './style.css'

/**
 * Initialize the application
 */
async function initApp() {
  const app = createApp(App)
  const pinia = createPinia()

  app.use(pinia)
  app.use(router)

  // Electron-specific initialization
  if (isElectron()) {
    console.log('[App] Running in Electron mode')
    
    // Initialize device URL before mounting
    const deviceUrl = await initializeDeviceUrl()
    
    // If no device configured, redirect to setup
    if (!deviceUrl) {
      console.log('[App] No device configured, redirecting to setup')
      router.push('/device-setup')
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
