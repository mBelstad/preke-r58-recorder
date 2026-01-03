import { createRouter, createWebHistory, createWebHashHistory } from 'vue-router'
import { isElectron, buildApiUrl, getDeviceUrl } from '@/lib/api'
import { useCapabilitiesStore } from '@/stores/capabilities'

// Use hash history for both Electron and web (works with static file serving)
// This avoids needing server-side SPA routing configuration
const createHistory = () => {
  // Always use hash history for compatibility with static file serving
  // This works in both Electron (file:// protocol) and web (https://)
  return createWebHashHistory()
}

// Track mode switching state to avoid duplicate calls
let isSwitchingMode = false

const router = createRouter({
  history: createHistory(),
  routes: [
    {
      path: '/',
      name: 'studio',
      component: () => import('@/views/StudioView.vue'),
      meta: { title: 'Studio' }
    },
    {
      path: '/device-setup',
      name: 'device-setup',
      component: () => import('@/views/DeviceSetupView.vue'),
      meta: { title: 'Device Setup', layout: 'minimal' }
    },
    {
      path: '/recorder',
      name: 'recorder',
      component: () => import('@/views/RecorderView.vue'),
      meta: { title: 'Recorder', mode: 'recorder' }
    },
    {
      path: '/mixer',
      name: 'mixer',
      component: () => import('@/views/MixerView.vue'),
      meta: { title: 'Mixer', mode: 'mixer' }
    },
    {
      path: '/library',
      name: 'library',
      component: () => import('@/views/LibraryView.vue'),
      meta: { title: 'Library' }
    },
    {
      path: '/admin',
      name: 'admin',
      component: () => import('@/views/AdminView.vue'),
      meta: { title: 'Admin', requiresAuth: true }
    },
    {
      path: '/guest',
      name: 'guest',
      component: () => import('@/views/GuestView.vue'),
      meta: { title: 'Guest Join', layout: 'minimal' }
    },
    {
      path: '/fleet',
      name: 'fleet',
      component: () => import('@/views/FleetDashboard.vue'),
      meta: { title: 'Fleet Management', requiresAuth: true }
    },
    {
      path: '/fleet/devices/:deviceId',
      name: 'device-detail',
      component: () => import('@/views/DeviceDetail.vue'),
      meta: { title: 'Device Details', requiresAuth: true }
    },
    {
      path: '/stream-test',
      name: 'stream-test',
      component: () => import('@/views/StreamTestView.vue'),
      meta: { title: 'Stream Test' }
    },
  ]
})

// Update document title
router.beforeEach((to, _from, next) => {
  const title = to.meta.title as string
  document.title = title ? `${title} - Preke Studio` : 'Preke Studio'
  next()
})

// Auto-switch mode when navigating to routes that require a specific mode
router.beforeEach(async (to, _from, next) => {
  const requiredMode = to.meta.mode as 'recorder' | 'mixer' | undefined
  
  if (!requiredMode || isSwitchingMode) {
    next()
    return
  }
  
  // In Electron, skip mode switching if no device is configured
  if (isElectron() && !getDeviceUrl()) {
    console.log('[Router] No device configured, skipping mode switch')
    next()
    return
  }
  
  try {
    // Fetch current mode from API with timeout to prevent hanging
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 5000) // 5 second timeout
    
    const modeRes = await fetch(buildApiUrl('/api/mode/status'), {
      signal: controller.signal
    }).finally(() => clearTimeout(timeoutId))
    if (!modeRes.ok) {
      console.warn('[Router] Could not fetch mode status, proceeding anyway')
      next()
      return
    }
    
    const modeData = await modeRes.json()
    const currentMode = modeData.current_mode as string
    
    // If already in the correct mode, proceed
    if (currentMode === requiredMode) {
      next()
      return
    }
    
    // Switch to the required mode
    console.log(`[Router] Switching mode from ${currentMode} to ${requiredMode}`)
    isSwitchingMode = true
    
    const switchController = new AbortController()
    const switchTimeoutId = setTimeout(() => switchController.abort(), 10000) // 10 second timeout
    
    const switchRes = await fetch(buildApiUrl(`/api/mode/${requiredMode}`), { 
      method: 'POST',
      signal: switchController.signal
    }).finally(() => clearTimeout(switchTimeoutId))
    
    if (!switchRes.ok) {
      const errorData = await switchRes.json().catch(() => ({}))
      console.error('[Router] Mode switch failed:', errorData.detail || 'Unknown error')
    } else {
      console.log(`[Router] Successfully switched to ${requiredMode} mode`)
      
      // Refresh capabilities store to update UI mode indicator
      try {
        const capabilitiesStore = useCapabilitiesStore()
        await capabilitiesStore.fetchCapabilities()
        console.log('[Router] Refreshed capabilities after mode switch')
      } catch (e) {
        console.warn('[Router] Failed to refresh capabilities:', e)
      }
    }
    
    isSwitchingMode = false
    next()
  } catch (e) {
    console.error('[Router] Error during mode switch:', e)
    isSwitchingMode = false
    next()
  }
})

export default router

