<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { buildApiUrl } from '@/lib/api'
import { toast } from '@/composables/useToast'
import { useCapabilitiesStore } from '@/stores/capabilities'

const router = useRouter()
const capabilitiesStore = useCapabilitiesStore()
const selectedMode = ref<'recorder' | 'mixer'>('recorder')
const switching = ref(false)
const switchError = ref<string | null>(null)

// Switch to idle mode when entering Studio page (stops all camera processes)
onMounted(async () => {
  try {
    const response = await fetch(buildApiUrl('/api/mode/idle'), { method: 'POST' })
    if (response.ok) {
      console.log('[Studio] Switched to idle mode')
      // Refresh capabilities to update sidebar
      await capabilitiesStore.fetchCapabilities()
    }
  } catch (e) {
    console.warn('[Studio] Failed to switch to idle mode:', e)
  }
})

async function selectMode(mode: 'recorder' | 'mixer') {
  if (switching.value) return

  selectedMode.value = mode
  switching.value = true
  switchError.value = null
  
  try {
    // Call mode switch API to prepare device resources
    const response = await fetch(buildApiUrl(`/api/mode/${mode}`), { method: 'POST' })
    
    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      throw new Error(data.detail || `Failed to switch to ${mode} mode`)
    }
    
    // Navigate to the mode view
  router.push(`/${mode}`)
  } catch (e) {
    const message = e instanceof Error ? e.message : 'Failed to switch mode'
    switchError.value = message
    toast.error(message)
    console.error('Mode switch error:', e)
  } finally {
    switching.value = false
  }
}
</script>

<template>
  <div class="h-full flex flex-col items-center justify-center p-8 bg-preke-bg">
    <h1 class="text-4xl font-bold mb-2 text-preke-text">Preke Studio</h1>
    <p class="text-preke-text-muted mb-12">Select a mode to begin</p>
    
    <div class="flex gap-6">
      <!-- Recorder Mode -->
      <button
        @click="selectMode('recorder')"
        :disabled="switching"
        class="group relative w-64 h-48 rounded-2xl border-2 transition-all duration-300 disabled:opacity-60 disabled:cursor-wait backdrop-blur-sm"
        :class="[
          selectedMode === 'recorder' 
            ? 'border-preke-red bg-preke-red/10 shadow-lg shadow-preke-red/20' 
            : 'border-preke-surface-border hover:border-preke-red/50 hover:bg-preke-surface/50'
        ]"
      >
        <div class="h-full flex flex-col items-center justify-center gap-4">
          <!-- Recording icon / Loading spinner -->
          <div class="w-16 h-16 rounded-full bg-preke-red/20 flex items-center justify-center group-hover:scale-110 transition-transform">
            <svg v-if="switching && selectedMode === 'recorder'" class="w-8 h-8 text-preke-red animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <svg v-else class="w-8 h-8 text-preke-red" fill="currentColor" viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="8"/>
            </svg>
          </div>
          <div class="text-center">
            <h3 class="text-xl font-semibold text-preke-text">Recorder</h3>
            <p class="text-sm text-preke-text-muted">
              {{ switching && selectedMode === 'recorder' ? 'Switching mode...' : 'Multi-cam ISO recording' }}
            </p>
          </div>
        </div>
      </button>
      
      <!-- Mixer Mode -->
      <button
        @click="selectMode('mixer')"
        :disabled="switching"
        class="group relative w-64 h-48 rounded-2xl border-2 transition-all duration-300 disabled:opacity-60 disabled:cursor-wait backdrop-blur-sm"
        :class="[
          selectedMode === 'mixer' 
            ? 'border-violet-500 bg-violet-500/10 shadow-lg shadow-violet-500/20' 
            : 'border-preke-surface-border hover:border-violet-500/50 hover:bg-preke-surface/50'
        ]"
      >
        <div class="h-full flex flex-col items-center justify-center gap-4">
          <!-- Mixer icon / Loading spinner -->
          <div class="w-16 h-16 rounded-full bg-violet-500/20 flex items-center justify-center group-hover:scale-110 transition-transform">
            <svg v-if="switching && selectedMode === 'mixer'" class="w-8 h-8 text-violet-500 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <svg v-else class="w-8 h-8 text-violet-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M4 6h16M4 12h16m-7 6h7"/>
              <circle cx="8" cy="6" r="2" fill="currentColor"/>
              <circle cx="16" cy="12" r="2" fill="currentColor"/>
              <circle cx="12" cy="18" r="2" fill="currentColor"/>
            </svg>
          </div>
          <div class="text-center">
            <h3 class="text-xl font-semibold text-preke-text">Mixer</h3>
            <p class="text-sm text-preke-text-muted">
              {{ switching && selectedMode === 'mixer' ? 'Switching mode...' : 'Live switching & streaming' }}
            </p>
          </div>
        </div>
      </button>
    </div>
    
    <!-- Error message -->
    <div v-if="switchError" class="mt-4 text-preke-red text-sm">
      {{ switchError }}
    </div>
    
    <!-- Quick status -->
    <div class="mt-12 flex gap-8 text-sm text-preke-text-muted">
      <div class="flex items-center gap-2">
        <span class="w-2 h-2 rounded-full bg-preke-green"></span>
        <span>4 inputs available</span>
      </div>
      <div class="flex items-center gap-2">
        <span class="w-2 h-2 rounded-full bg-preke-green"></span>
        <span>Storage: 256 GB free</span>
      </div>
    </div>
  </div>
</template>

