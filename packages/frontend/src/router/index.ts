import { createRouter, createWebHistory, createWebHashHistory } from 'vue-router'
import { isElectron } from '@/lib/api'

// Use hash history for Electron (file:// protocol), web history for browser
const createHistory = () => {
  // Check if we're in Electron via the global flag set at build time
  // or by checking window.electronAPI at runtime
  const inElectron = typeof window !== 'undefined' && !!window.electronAPI
  
  if (inElectron) {
    return createWebHashHistory()
  }
  return createWebHistory(import.meta.env.BASE_URL)
}

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
  ]
})

// Update document title
router.beforeEach((to, _from, next) => {
  const title = to.meta.title as string
  document.title = title ? `${title} - Preke Studio` : 'Preke Studio'
  next()
})

export default router

