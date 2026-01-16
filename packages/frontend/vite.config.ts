import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { VitePWA } from 'vite-plugin-pwa'
import { fileURLToPath, URL } from 'node:url'

// Check if building for Electron
const isElectronBuild = process.env.ELECTRON_BUILD === 'true'
// Check if building for R58 static serving (relative paths)
const isStaticBuild = process.env.STATIC_BUILD === 'true'

export default defineConfig({
  // Use relative paths for Electron (file:// protocol) and static serving
  base: isElectronBuild || isStaticBuild ? './' : '/',
  
  // Output to desktop package for Electron builds
  build: {
    outDir: isElectronBuild ? '../desktop/app/renderer' : 'dist',
    emptyOutDir: true,
    // Ensure assets use relative paths
    assetsDir: 'assets',
    rollupOptions: {
      output: {
        // Ensure consistent chunk naming for Electron
        manualChunks: isElectronBuild ? undefined : undefined,
      }
    }
  },
  
  plugins: [
    vue(),
    // Only include PWA plugin for web builds, not Electron
    ...(!isElectronBuild ? [
      VitePWA({
        registerType: 'autoUpdate',
        includeAssets: ['favicon.svg', 'apple-touch-icon.png', 'pwa-192x192.png', 'pwa-512x512.png'],
        manifest: {
          name: 'Preke Studio',
          short_name: 'Preke',
          description: 'Preke Recorder & Mixer Control',
          theme_color: '#0f172a',
          background_color: '#0f172a',
          display: 'standalone',
          orientation: 'landscape',
          icons: [
            {
              src: 'pwa-192x192.png',
              sizes: '192x192',
              type: 'image/png'
            },
            {
              src: 'pwa-512x512.png',
              sizes: '512x512',
              type: 'image/png'
            },
            {
              src: 'pwa-512x512.png',
              sizes: '512x512',
              type: 'image/png',
              purpose: 'maskable'
            }
          ]
        },
        workbox: {
          // Force immediate activation of new service worker
          skipWaiting: true,
          clientsClaim: true,
          // Clear old caches on update
          cleanupOutdatedCaches: true,
          // Only cache static assets, not dynamic content
          globPatterns: ['**/*.{js,css,html,svg,woff,woff2}'],
          // Exclude API calls and video streams from caching
          navigateFallbackDenylist: [/^\/api/, /^\/cam/, /\/whep$/],
          runtimeCaching: [
            {
              // Cache static images only
              urlPattern: /\.(?:png|jpg|jpeg|gif|webp|ico)$/i,
              handler: 'CacheFirst',
              options: {
                cacheName: 'image-cache',
                expiration: {
                  maxEntries: 50,
                  maxAgeSeconds: 60 * 60 * 24 // 24 hours
                }
              }
            }
            // Removed API caching - real-time data should always be fresh
          ]
        }
      })
    ] : [])
  ],
  
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  
  // Define global constants
  define: {
    __ELECTRON__: JSON.stringify(isElectronBuild),
  },
  
  server: {
    host: true,
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
