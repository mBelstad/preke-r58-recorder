import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { VitePWA } from 'vite-plugin-pwa'
import { fileURLToPath, URL } from 'node:url'

// Check if building for Electron
const isElectronBuild = process.env.ELECTRON_BUILD === 'true'

export default defineConfig({
  // Use relative paths for Electron (file:// protocol)
  base: isElectronBuild ? './' : '/',
  
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
        includeAssets: ['favicon.ico', 'robots.txt', 'apple-touch-icon.png'],
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
          globPatterns: ['**/*.{js,css,html,ico,png,svg,woff,woff2}'],
          runtimeCaching: [
            {
              urlPattern: /^https?:\/\/.*\/api\/.*/i,
              handler: 'NetworkFirst',
              options: {
                cacheName: 'api-cache',
                expiration: {
                  maxEntries: 100,
                  maxAgeSeconds: 60 * 60 // 1 hour
                }
              }
            }
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
