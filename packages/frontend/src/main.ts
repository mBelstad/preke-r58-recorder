import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import { initializeDeviceUrl, setDeviceUrl, isElectron } from './lib/api'

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
    window.electronAPI?.onDeviceChanged((device) => {
      console.log('[App] Device changed:', device)
      setDeviceUrl(device?.url || null)
      
      // Reload the current page to use new device
      if (device) {
        router.go(0)
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
