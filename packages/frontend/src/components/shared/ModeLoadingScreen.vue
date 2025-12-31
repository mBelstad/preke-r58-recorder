<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'

const props = withDefaults(defineProps<{
  mode: 'recorder' | 'mixer'
  /** Minimum time to show loading screen (ms) */
  minTime?: number
  /** Maximum time before auto-dismissing (ms) */
  maxTime?: number
  /** Signal from parent that content is ready */
  contentReady?: boolean
}>(), {
  minTime: 1500,  // Show for at least 1.5 seconds
  maxTime: 8000,  // Max 8 seconds before auto-dismiss
  contentReady: false
})

const emit = defineEmits<{
  (e: 'ready'): void
}>()

// Track if minimum time has passed
const minTimePassed = ref(false)
let minTimeoutId: ReturnType<typeof setTimeout> | null = null
let maxTimeoutId: ReturnType<typeof setTimeout> | null = null

// Dismiss when both minTime passed AND contentReady
function checkAndDismiss() {
  if (minTimePassed.value && props.contentReady) {
    emit('ready')
  }
}

// Watch for contentReady changes
watch(() => props.contentReady, (ready) => {
  if (ready) {
    checkAndDismiss()
  }
})

// Mode-specific styling
const modeColor = computed(() => props.mode === 'recorder' ? '#ef4444' : '#3b82f6')
const modeName = computed(() => props.mode === 'recorder' ? 'Recorder' : 'Mixer')
const modeTagline = computed(() => props.mode === 'recorder' ? 'Multi-cam ISO Recording' : 'Live Switching & Streaming')

// Soundwave animation
const bars = ref([0.3, 0.5, 0.8, 1, 0.8, 0.5, 0.3])

let animationFrame: number | null = null
const animationStart = ref(Date.now())

function animateBars() {
  const elapsed = (Date.now() - animationStart.value) / 1000
  bars.value = bars.value.map((_, i) => {
    const phase = (i / bars.value.length) * Math.PI * 2
    const wave = Math.sin(elapsed * 3 + phase) * 0.4 + 0.6
    return Math.max(0.2, Math.min(1, wave))
  })
  animationFrame = requestAnimationFrame(animateBars)
}

onMounted(() => {
  // Start animation
  animateBars()
  
  // Minimum time before allowing dismiss
  minTimeoutId = setTimeout(() => {
    minTimePassed.value = true
    checkAndDismiss()
  }, props.minTime)
  
  // Maximum time - force dismiss even if content not ready
  maxTimeoutId = setTimeout(() => {
    emit('ready')
  }, props.maxTime)
})

onUnmounted(() => {
  if (minTimeoutId) clearTimeout(minTimeoutId)
  if (maxTimeoutId) clearTimeout(maxTimeoutId)
  if (animationFrame) cancelAnimationFrame(animationFrame)
})
</script>

<template>
  <div class="fixed inset-0 z-50 flex flex-col items-center justify-center bg-r58-bg-primary overflow-hidden">
    <!-- Animated background -->
    <div class="absolute inset-0">
      <!-- Gradient orbs -->
      <div 
        class="absolute w-[600px] h-[600px] rounded-full blur-3xl opacity-20 animate-float-slow"
        :style="{ background: `radial-gradient(circle, ${modeColor} 0%, transparent 70%)`, left: '10%', top: '10%' }"
      ></div>
      <div 
        class="absolute w-[400px] h-[400px] rounded-full blur-3xl opacity-15 animate-float-medium"
        :style="{ background: `radial-gradient(circle, ${modeColor} 0%, transparent 70%)`, right: '15%', bottom: '20%' }"
      ></div>
      
      <!-- Subtle grid pattern -->
      <div class="absolute inset-0 opacity-5" style="background-image: linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px); background-size: 50px 50px;"></div>
    </div>
    
    <!-- Content -->
    <div class="relative z-10 flex flex-col items-center gap-10">
      <!-- Mode Icon with Soundwave -->
      <div class="relative flex items-center justify-center">
        <!-- Outer ring pulse -->
        <div 
          class="absolute w-40 h-40 rounded-full animate-ping-slow opacity-20"
          :style="{ backgroundColor: modeColor }"
        ></div>
        
        <!-- Icon container -->
        <div 
          class="relative w-32 h-32 rounded-full flex items-center justify-center backdrop-blur-sm"
          :style="{ backgroundColor: `${modeColor}15`, border: `2px solid ${modeColor}40` }"
        >
          <!-- Recorder icon -->
          <div v-if="mode === 'recorder'" class="relative">
            <svg class="w-16 h-16" :style="{ color: modeColor }" fill="currentColor" viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="8" class="animate-pulse-glow"/>
            </svg>
            <!-- Recording ring -->
            <div 
              class="absolute inset-0 rounded-full animate-spin-slow"
              :style="{ border: `3px solid ${modeColor}`, borderTopColor: 'transparent' }"
            ></div>
          </div>
          
          <!-- Mixer icon with animated soundwave bars -->
          <div v-else class="flex items-end gap-1.5 h-14">
            <div 
              v-for="(height, i) in bars" 
              :key="i"
              class="w-2 rounded-full transition-all duration-75"
              :style="{ 
                height: `${height * 100}%`, 
                backgroundColor: modeColor,
                opacity: 0.6 + height * 0.4
              }"
            ></div>
          </div>
        </div>
      </div>
      
      <!-- Mode title -->
      <div class="text-center">
        <h2 class="text-4xl font-bold mb-3 tracking-tight" :style="{ color: modeColor }">
          {{ modeName }}
        </h2>
        <p class="text-r58-text-secondary text-lg">
          {{ modeTagline }}
        </p>
      </div>
      
      <!-- Animated loading dots -->
      <div class="flex items-center gap-2">
        <div 
          v-for="i in 3"
          :key="i"
          class="w-2 h-2 rounded-full animate-bounce-dot"
          :style="{ 
            backgroundColor: modeColor,
            animationDelay: `${(i - 1) * 0.15}s`
          }"
        ></div>
      </div>
    </div>
  </div>
</template>

<style scoped>
@keyframes float-slow {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50% { transform: translate(30px, -20px) scale(1.1); }
}

@keyframes float-medium {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50% { transform: translate(-20px, 15px) scale(1.05); }
}

@keyframes ping-slow {
  0% { transform: scale(1); opacity: 0.2; }
  100% { transform: scale(1.5); opacity: 0; }
}

@keyframes spin-slow {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@keyframes pulse-glow {
  0%, 100% { filter: drop-shadow(0 0 8px currentColor); }
  50% { filter: drop-shadow(0 0 20px currentColor); }
}

@keyframes bounce-dot {
  0%, 80%, 100% { transform: translateY(0); opacity: 0.5; }
  40% { transform: translateY(-8px); opacity: 1; }
}

.animate-float-slow {
  animation: float-slow 8s ease-in-out infinite;
}

.animate-float-medium {
  animation: float-medium 6s ease-in-out infinite;
}

.animate-ping-slow {
  animation: ping-slow 2s cubic-bezier(0, 0, 0.2, 1) infinite;
}

.animate-spin-slow {
  animation: spin-slow 3s linear infinite;
}

.animate-pulse-glow {
  animation: pulse-glow 2s ease-in-out infinite;
}

.animate-bounce-dot {
  animation: bounce-dot 1.2s ease-in-out infinite;
}
</style>
