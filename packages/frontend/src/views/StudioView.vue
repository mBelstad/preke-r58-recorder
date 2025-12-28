<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const selectedMode = ref<'recorder' | 'mixer'>('recorder')

function selectMode(mode: 'recorder' | 'mixer') {
  selectedMode.value = mode
  router.push(`/${mode}`)
}
</script>

<template>
  <div class="h-full flex flex-col items-center justify-center p-8">
    <h1 class="text-4xl font-bold mb-2">Preke Studio</h1>
    <p class="text-r58-text-secondary mb-12">Select a mode to begin</p>
    
    <div class="flex gap-6">
      <!-- Recorder Mode -->
      <button
        @click="selectMode('recorder')"
        class="group relative w-64 h-48 rounded-2xl border-2 transition-all duration-300"
        :class="[
          selectedMode === 'recorder' 
            ? 'border-r58-recorder bg-r58-recorder/10' 
            : 'border-r58-bg-tertiary hover:border-r58-recorder/50 hover:bg-r58-bg-secondary'
        ]"
      >
        <div class="h-full flex flex-col items-center justify-center gap-4">
          <!-- Recording icon -->
          <div class="w-16 h-16 rounded-full bg-r58-recorder/20 flex items-center justify-center group-hover:scale-110 transition-transform">
            <svg class="w-8 h-8 text-r58-recorder" fill="currentColor" viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="8"/>
            </svg>
          </div>
          <div class="text-center">
            <h3 class="text-xl font-semibold">Recorder</h3>
            <p class="text-sm text-r58-text-secondary">Multi-cam ISO recording</p>
          </div>
        </div>
      </button>
      
      <!-- Mixer Mode -->
      <button
        @click="selectMode('mixer')"
        class="group relative w-64 h-48 rounded-2xl border-2 transition-all duration-300"
        :class="[
          selectedMode === 'mixer' 
            ? 'border-r58-mixer bg-r58-mixer/10' 
            : 'border-r58-bg-tertiary hover:border-r58-mixer/50 hover:bg-r58-bg-secondary'
        ]"
      >
        <div class="h-full flex flex-col items-center justify-center gap-4">
          <!-- Mixer icon -->
          <div class="w-16 h-16 rounded-full bg-r58-mixer/20 flex items-center justify-center group-hover:scale-110 transition-transform">
            <svg class="w-8 h-8 text-r58-mixer" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M4 6h16M4 12h16m-7 6h7"/>
              <circle cx="8" cy="6" r="2" fill="currentColor"/>
              <circle cx="16" cy="12" r="2" fill="currentColor"/>
              <circle cx="12" cy="18" r="2" fill="currentColor"/>
            </svg>
          </div>
          <div class="text-center">
            <h3 class="text-xl font-semibold">Mixer</h3>
            <p class="text-sm text-r58-text-secondary">Live switching & streaming</p>
          </div>
        </div>
      </button>
    </div>
    
    <!-- Quick status -->
    <div class="mt-12 flex gap-8 text-sm text-r58-text-secondary">
      <div class="flex items-center gap-2">
        <span class="w-2 h-2 rounded-full bg-r58-accent-success"></span>
        <span>4 inputs available</span>
      </div>
      <div class="flex items-center gap-2">
        <span class="w-2 h-2 rounded-full bg-r58-accent-success"></span>
        <span>Storage: 256 GB free</span>
      </div>
    </div>
  </div>
</template>

