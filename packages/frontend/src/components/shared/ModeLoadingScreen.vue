<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'

const props = defineProps<{
  mode: 'recorder' | 'mixer'
  camerasReady?: number
  totalCameras?: number
  isLoading?: boolean
}>()

const emit = defineEmits<{
  (e: 'ready'): void
}>()

// Auto-dismiss after timeout
const autoTimeout = 3000 // 3 seconds max
let timeoutId: ReturnType<typeof setTimeout> | null = null

// Animation state
const animationPhase = ref(0)
const progressWidth = computed(() => {
  if (props.totalCameras && props.totalCameras > 0) {
    return Math.min(100, (props.camerasReady || 0) / props.totalCameras * 100)
  }
  return animationPhase.value * 25 // Animated progress when no camera data
})

// Mode-specific styling
const modeColor = computed(() => props.mode === 'recorder' ? 'r58-recorder' : 'r58-mixer')
const modeName = computed(() => props.mode === 'recorder' ? 'Recorder' : 'Mixer')

// Animate the progress bar if no camera data
let animationInterval: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  // Auto-dismiss after timeout
  timeoutId = setTimeout(() => {
    emit('ready')
  }, autoTimeout)
  
  // Animate progress if no camera data
  if (!props.camerasReady) {
    animationInterval = setInterval(() => {
      animationPhase.value = (animationPhase.value + 1) % 5
    }, 600)
  }
})

onUnmounted(() => {
  if (timeoutId) clearTimeout(timeoutId)
  if (animationInterval) clearInterval(animationInterval)
})

// Emit ready when first camera loads
watch(() => props.camerasReady, (ready) => {
  if (ready && ready > 0) {
    // Give a brief moment to show the progress, then emit ready
    setTimeout(() => emit('ready'), 500)
  }
})
</script>

<template>
  <div class="fixed inset-0 z-50 flex flex-col items-center justify-center bg-r58-bg-primary">
    <!-- Animated background gradient -->
    <div 
      class="absolute inset-0 opacity-20"
      :class="mode === 'recorder' ? 'bg-gradient-radial-red' : 'bg-gradient-radial-blue'"
    ></div>
    
    <!-- Content -->
    <div class="relative z-10 flex flex-col items-center gap-8">
      <!-- Animated Logo/Icon -->
      <div class="relative">
        <!-- Pulse rings -->
        <div 
          class="absolute inset-0 rounded-full animate-ping opacity-20"
          :class="`bg-${modeColor}`"
          style="animation-duration: 1.5s;"
        ></div>
        <div 
          class="absolute inset-0 rounded-full animate-ping opacity-10"
          :class="`bg-${modeColor}`"
          style="animation-duration: 2s; animation-delay: 0.5s;"
        ></div>
        
        <!-- Icon container -->
        <div 
          class="relative w-24 h-24 rounded-full flex items-center justify-center"
          :class="`bg-${modeColor}/20`"
        >
          <!-- Recorder icon -->
          <svg v-if="mode === 'recorder'" class="w-12 h-12 text-r58-recorder animate-pulse" fill="currentColor" viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="8"/>
          </svg>
          <!-- Mixer icon -->
          <svg v-else class="w-12 h-12 text-r58-mixer" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M4 6h16M4 12h16m-7 6h7"/>
            <circle cx="8" cy="6" r="2" fill="currentColor" class="animate-pulse"/>
            <circle cx="16" cy="12" r="2" fill="currentColor" class="animate-pulse" style="animation-delay: 0.2s;"/>
            <circle cx="12" cy="18" r="2" fill="currentColor" class="animate-pulse" style="animation-delay: 0.4s;"/>
          </svg>
        </div>
      </div>
      
      <!-- Mode title -->
      <div class="text-center">
        <h2 class="text-3xl font-bold mb-2">{{ modeName }}</h2>
        <p class="text-r58-text-secondary">
          <span v-if="camerasReady !== undefined && totalCameras">
            Loading cameras... {{ camerasReady }}/{{ totalCameras }}
          </span>
          <span v-else>
            Initializing cameras...
          </span>
        </p>
      </div>
      
      <!-- Progress bar -->
      <div class="w-64 h-1.5 bg-r58-bg-tertiary rounded-full overflow-hidden">
        <div 
          class="h-full rounded-full transition-all duration-300"
          :class="`bg-${modeColor}`"
          :style="{ width: `${progressWidth}%` }"
        ></div>
      </div>
      
      <!-- Camera indicators -->
      <div v-if="totalCameras" class="flex gap-3">
        <div 
          v-for="i in totalCameras" 
          :key="i"
          class="w-3 h-3 rounded-full transition-all duration-300"
          :class="[
            i <= (camerasReady || 0) 
              ? `bg-${modeColor}` 
              : 'bg-r58-bg-tertiary'
          ]"
        ></div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.bg-gradient-radial-red {
  background: radial-gradient(circle at center, rgba(239, 68, 68, 0.3) 0%, transparent 70%);
}

.bg-gradient-radial-blue {
  background: radial-gradient(circle at center, rgba(59, 130, 246, 0.3) 0%, transparent 70%);
}
</style>

