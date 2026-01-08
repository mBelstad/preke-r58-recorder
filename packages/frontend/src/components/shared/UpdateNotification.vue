<script setup lang="ts">
/**
 * Update Notification Component
 * 
 * Shows update notifications and download progress for Electron app updates.
 * Only renders in Electron environment.
 */
import { ref, onMounted, onUnmounted } from 'vue'
import { toast } from '@/composables/useToast'

const isElectron = typeof window !== 'undefined' && (window as any).electronAPI

// Update state
const updateAvailable = ref(false)
const updateVersion = ref<string | null>(null)
const updateReleaseNotes = ref<string | null>(null)
const isDownloading = ref(false)
const downloadProgress = ref(0)
const isDownloaded = ref(false)
const isChecking = ref(false)

// Unsubscribe functions
let unsubscribeFunctions: (() => void)[] = []

async function checkForUpdates() {
  if (!isElectron) return
  
  isChecking.value = true
  try {
    const result = await (window as any).electronAPI.checkForUpdates()
    if (result.updateAvailable) {
      updateAvailable.value = true
      updateVersion.value = result.version || null
      updateReleaseNotes.value = result.releaseNotes || null
      
      toast.info(
        'Update Available',
        `Version ${result.version} is available. Click to download.`
      )
    } else if (result.error) {
      console.warn('Update check error:', result.error)
    }
  } catch (error) {
    console.error('Failed to check for updates:', error)
  } finally {
    isChecking.value = false
  }
}

async function downloadUpdate() {
  if (!isElectron || !updateAvailable.value) return
  
  isDownloading.value = true
  downloadProgress.value = 0
  
  try {
    const result = await (window as any).electronAPI.downloadUpdate()
    if (!result.success) {
      toast.error('Download Failed', result.error || 'Failed to download update')
      isDownloading.value = false
    }
  } catch (error) {
    console.error('Failed to download update:', error)
    toast.error('Download Failed', 'An error occurred while downloading the update')
    isDownloading.value = false
  }
}

function installUpdate() {
  if (!isElectron) return
  ;(window as any).electronAPI.installUpdate()
}

function dismissNotification() {
  updateAvailable.value = false
  isDownloaded.value = false
}

onMounted(() => {
  if (!isElectron) return
  
  // Setup event listeners
  const unsubs = [
    (window as any).electronAPI.onUpdateChecking(() => {
      isChecking.value = true
    }),
    (window as any).electronAPI.onUpdateAvailable((info: { version: string; releaseNotes?: string }) => {
      updateAvailable.value = true
      updateVersion.value = info.version
      updateReleaseNotes.value = info.releaseNotes || null
      
      toast.info(
        'Update Available',
        `Version ${info.version} is available.`
      )
    }),
    (window as any).electronAPI.onUpdateNotAvailable(() => {
      isChecking.value = false
    }),
    (window as any).electronAPI.onUpdateError((error: { message: string }) => {
      isChecking.value = false
      isDownloading.value = false
      toast.error('Update Error', error.message)
    }),
    (window as any).electronAPI.onUpdateDownloadProgress((progress: { percent: number }) => {
      downloadProgress.value = progress.percent
    }),
    (window as any).electronAPI.onUpdateDownloaded((info: { version: string; releaseNotes?: string }) => {
      isDownloading.value = false
      isDownloaded.value = true
      downloadProgress.value = 100
      
      toast.success(
        'Update Downloaded',
        `Version ${info.version} is ready to install.`
      )
    }),
  ]
  
  unsubscribeFunctions = unsubs
  
  // Check for updates on mount (only in Electron)
  checkForUpdates()
})

onUnmounted(() => {
  unsubscribeFunctions.forEach(unsub => unsub())
})
</script>

<template>
  <!-- Update notification banner (only in Electron) -->
  <Transition name="slide-down">
    <div
      v-if="isElectron && (updateAvailable || isDownloading || isDownloaded)"
      class="fixed top-0 left-0 right-0 z-50 bg-preke-surface border-b border-preke-surface-border backdrop-blur-lg"
    >
      <div class="max-w-7xl mx-auto px-4 py-3">
        <div class="flex items-center justify-between gap-4">
          <!-- Status & Info -->
          <div class="flex items-center gap-3 flex-1 min-w-0">
            <div class="flex-shrink-0 w-2 h-2 rounded-full" :class="{
              'bg-preke-gold animate-pulse': isChecking,
              'bg-preke-blue': updateAvailable && !isDownloading && !isDownloaded,
              'bg-preke-green': isDownloaded,
            }"></div>
            
            <div class="flex-1 min-w-0">
              <p class="font-medium text-sm text-preke-text">
                <span v-if="isChecking">Checking for updates...</span>
                <span v-else-if="isDownloading">
                  Downloading update {{ updateVersion ? `v${updateVersion}` : '' }}...
                  <span class="text-preke-text-muted">{{ Math.round(downloadProgress) }}%</span>
                </span>
                <span v-else-if="isDownloaded">
                  Update {{ updateVersion ? `v${updateVersion}` : '' }} ready to install
                </span>
                <span v-else-if="updateAvailable">
                  Update {{ updateVersion ? `v${updateVersion}` : '' }} available
                </span>
              </p>
              
              <!-- Download progress bar -->
              <div
                v-if="isDownloading"
                class="mt-2 h-1 bg-preke-bg rounded-full overflow-hidden"
              >
                <div
                  class="h-full bg-preke-blue transition-all duration-300"
                  :style="{ width: `${downloadProgress}%` }"
                ></div>
              </div>
            </div>
          </div>
          
          <!-- Actions -->
          <div class="flex items-center gap-2 flex-shrink-0">
            <button
              v-if="updateAvailable && !isDownloading && !isDownloaded"
              @click="downloadUpdate"
              class="px-3 py-1.5 text-sm font-medium bg-preke-blue text-white rounded-lg hover:bg-preke-blue/90 transition-colors"
            >
              Download
            </button>
            
            <button
              v-if="isDownloaded"
              @click="installUpdate"
              class="px-3 py-1.5 text-sm font-medium bg-preke-green text-white rounded-lg hover:bg-preke-green/90 transition-colors"
            >
              Install & Restart
            </button>
            
            <button
              @click="dismissNotification"
              class="px-2 py-1.5 text-preke-text-muted hover:text-preke-text transition-colors"
              aria-label="Dismiss"
            >
              ×
            </button>
          </div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.slide-down-enter-active,
.slide-down-leave-active {
  transition: all 0.3s ease-out;
}

.slide-down-enter-from {
  transform: translateY(-100%);
  opacity: 0;
}

.slide-down-leave-to {
  transform: translateY(-100%);
  opacity: 0;
}
</style>
