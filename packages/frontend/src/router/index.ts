import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'studio',
      component: () => import('@/views/StudioView.vue'),
      meta: { title: 'Studio' }
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
  ]
})

// Update document title
router.beforeEach((to, _from, next) => {
  const title = to.meta.title as string
  document.title = title ? `${title} - R58 Studio` : 'R58 Studio'
  next()
})

export default router

