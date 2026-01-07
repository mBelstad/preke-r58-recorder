import { createRouter, createWebHashHistory } from 'vue-router'

// Use hash history for both Electron and web (works with static file serving)
// This avoids needing server-side SPA routing configuration
const createHistory = () => {
  // Always use hash history for compatibility with static file serving
  // This works in both Electron (file:// protocol) and web (https://)
  return createWebHashHistory()
}

// Track if this is the initial app load (for redirecting to device setup)
let isInitialLoad = true

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
      path: '/settings',
      name: 'settings',
      redirect: { name: 'admin', query: { tab: 'settings' } }
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
    {
      path: '/style-guide',
      name: 'style-guide',
      component: () => import('@/views/StyleGuideView.vue'),
      meta: { title: 'Style Guide' }
    },
    {
      path: '/style-guide-v2',
      name: 'style-guide-v2',
      component: () => import('@/views/StyleGuideV2View.vue'),
      meta: { title: 'Style Guide v2 - Glassmorphism' }
    },
    {
      path: '/background-drafts',
      name: 'background-drafts',
      component: () => import('@/views/BackgroundDesignDraftsView.vue'),
      meta: { title: 'Background Design Drafts' }
    },
    // Legacy routes - redirect to combined page
    {
      path: '/experiments',
      redirect: { name: 'background-drafts' }
    },
    {
      path: '/proposals',
      redirect: { name: 'background-drafts' }
    },
    {
      path: '/design-archive',
      name: 'design-archive',
      component: () => import('@/views/DesignArchiveView.vue'),
      meta: { title: 'Design Archive' }
    },
    // Aliases for styleguide routes
    {
      path: '/styleguide',
      redirect: { name: 'style-guide' }
    },
    {
      path: '/styleguide-v2',
      redirect: { name: 'style-guide-v2' }
    },
  ]
})

// Navigation guard: redirect to device-setup on initial app load (Electron only)
router.beforeEach((to, _from, next) => {
  // Update document title
  const title = to.meta.title as string
  document.title = title ? `${title} - Preke Studio` : 'Preke Studio'
  
  // On initial load in Electron, redirect to device-setup so user can choose device
  if (isInitialLoad && window.electronAPI?.isElectron) {
    isInitialLoad = false
    
    // If navigating to root, redirect to device-setup
    if (to.path === '/') {
      next({ name: 'device-setup' })
      return
    }
  }
  
  // Mark initial load complete after first navigation
  isInitialLoad = false
  
  next()
})

// Note: Mode switching is handled by the Sidebar component
// The router just navigates, the Sidebar handles the mode switch API calls
// This avoids duplicate mode switches and keeps the UI in sync

export default router

