<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { buildApiUrl } from '@/lib/api'
import { toast } from '@/composables/useToast'
import { useCapabilitiesStore } from '@/stores/capabilities'

const router = useRouter()
const capabilitiesStore = useCapabilitiesStore()
const selectedMode = ref<'recorder' | 'mixer' | null>(null)
const switching = ref(false)
const switchError = ref<string | null>(null)

// AbortController to cancel in-flight mode switch requests
let switchAbortController: AbortController | null = null

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

  // Cancel any existing request
  if (switchAbortController) {
    switchAbortController.abort()
  }
  
  // Create new abort controller for this request
  switchAbortController = new AbortController()
  const currentController = switchAbortController // Capture reference for this request
  const signal = currentController.signal

  selectedMode.value = mode
  switching.value = true
  switchError.value = null
  
  try {
    // Call mode switch API to prepare device resources
    const response = await fetch(buildApiUrl(`/api/mode/${mode}`), { 
      method: 'POST',
      signal 
    })
    
    // Check if cancelled before proceeding
    if (signal.aborted) return
    
    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      throw new Error(data.detail || `Failed to switch to ${mode} mode`)
    }
    
    // Check again before navigation (in case cancelled during response parsing)
    if (signal.aborted) return
    
    // Navigate to the mode view
    router.push(`/${mode}`)
  } catch (e) {
    // Ignore abort errors - these are expected when user cancels
    if (e instanceof Error && e.name === 'AbortError') {
      console.log('[Studio] Mode switch cancelled by user')
      return
    }
    
    const message = e instanceof Error ? e.message : 'Failed to switch mode'
    switchError.value = message
    toast.error(message)
    console.error('Mode switch error:', e)
  } finally {
    // Only reset state if this request is still the current one
    // (prevents race condition when user cancels and quickly starts new request)
    if (switchAbortController === currentController) {
      switching.value = false
      switchAbortController = null
    }
  }
}

</script>

<template>
  <div class="studio">
    <!-- Geometric background - 20 parallelograms evenly distributed -->
    <div class="studio__geo">
      <!-- Row 1: Top edge shapes -->
      <div class="geo-layer geo-layer--1">
        <div class="geo-shape geo-shape--1"></div>
        <div class="geo-shape geo-shape--2"></div>
        <div class="geo-shape geo-shape--3"></div>
        <div class="geo-shape geo-shape--4"></div>
        <div class="geo-shape geo-shape--5"></div>
      </div>
      <!-- Row 2: Upper middle shapes -->
      <div class="geo-layer geo-layer--2">
        <div class="geo-shape geo-shape--6"></div>
        <div class="geo-shape geo-shape--7"></div>
        <div class="geo-shape geo-shape--8"></div>
        <div class="geo-shape geo-shape--9"></div>
        <div class="geo-shape geo-shape--10"></div>
      </div>
      <!-- Row 3: Lower middle shapes -->
      <div class="geo-layer geo-layer--3">
        <div class="geo-shape geo-shape--11"></div>
        <div class="geo-shape geo-shape--12"></div>
        <div class="geo-shape geo-shape--13"></div>
        <div class="geo-shape geo-shape--14"></div>
        <div class="geo-shape geo-shape--15"></div>
      </div>
      <!-- Row 4: Bottom edge shapes -->
      <div class="geo-layer geo-layer--4">
        <div class="geo-shape geo-shape--16"></div>
        <div class="geo-shape geo-shape--17"></div>
        <div class="geo-shape geo-shape--18"></div>
        <div class="geo-shape geo-shape--19"></div>
        <div class="geo-shape geo-shape--20"></div>
      </div>
      <!-- Animated soundwaves (like the logo) -->
      <div class="soundwave soundwave--1">
        <div class="soundwave__bar" style="--i: 0; --h: 0.3"></div>
        <div class="soundwave__bar" style="--i: 1; --h: 0.5"></div>
        <div class="soundwave__bar" style="--i: 2; --h: 0.8"></div>
        <div class="soundwave__bar" style="--i: 3; --h: 1"></div>
        <div class="soundwave__bar" style="--i: 4; --h: 0.7"></div>
        <div class="soundwave__bar" style="--i: 5; --h: 0.4"></div>
        <div class="soundwave__bar" style="--i: 6; --h: 0.6"></div>
        <div class="soundwave__bar" style="--i: 7; --h: 0.9"></div>
        <div class="soundwave__bar" style="--i: 8; --h: 0.5"></div>
        <div class="soundwave__bar" style="--i: 9; --h: 0.3"></div>
        <div class="soundwave__bar" style="--i: 10; --h: 0.6"></div>
        <div class="soundwave__bar" style="--i: 11; --h: 0.8"></div>
        <div class="soundwave__bar" style="--i: 12; --h: 1"></div>
        <div class="soundwave__bar" style="--i: 13; --h: 0.7"></div>
        <div class="soundwave__bar" style="--i: 14; --h: 0.4"></div>
      </div>
      <div class="soundwave soundwave--2">
        <div class="soundwave__bar" style="--i: 0; --h: 0.4"></div>
        <div class="soundwave__bar" style="--i: 1; --h: 0.7"></div>
        <div class="soundwave__bar" style="--i: 2; --h: 0.5"></div>
        <div class="soundwave__bar" style="--i: 3; --h: 0.9"></div>
        <div class="soundwave__bar" style="--i: 4; --h: 1"></div>
        <div class="soundwave__bar" style="--i: 5; --h: 0.6"></div>
        <div class="soundwave__bar" style="--i: 6; --h: 0.8"></div>
        <div class="soundwave__bar" style="--i: 7; --h: 0.4"></div>
        <div class="soundwave__bar" style="--i: 8; --h: 0.7"></div>
        <div class="soundwave__bar" style="--i: 9; --h: 0.5"></div>
        <div class="soundwave__bar" style="--i: 10; --h: 0.3"></div>
        <div class="soundwave__bar" style="--i: 11; --h: 0.6"></div>
      </div>
      <div class="soundwave soundwave--3">
        <div class="soundwave__bar" style="--i: 0; --h: 0.5"></div>
        <div class="soundwave__bar" style="--i: 1; --h: 0.3"></div>
        <div class="soundwave__bar" style="--i: 2; --h: 0.7"></div>
        <div class="soundwave__bar" style="--i: 3; --h: 0.6"></div>
        <div class="soundwave__bar" style="--i: 4; --h: 1"></div>
        <div class="soundwave__bar" style="--i: 5; --h: 0.8"></div>
        <div class="soundwave__bar" style="--i: 6; --h: 0.4"></div>
        <div class="soundwave__bar" style="--i: 7; --h: 0.9"></div>
        <div class="soundwave__bar" style="--i: 8; --h: 0.5"></div>
        <div class="soundwave__bar" style="--i: 9; --h: 0.7"></div>
      </div>
      
      <!-- Subtle purple background lights -->
      <div class="purple-light purple-light--1"></div>
      <div class="purple-light purple-light--2"></div>
      <div class="purple-light purple-light--3"></div>
      <div class="purple-light purple-light--4"></div>
    </div>
    
    <!-- Content overlay -->
    <div class="studio__content">
      <div class="studio__side studio__side--left">
        <button
          @click="selectMode('recorder')"
          :disabled="switching"
          class="studio__card studio__card--recorder"
          :class="{ 'studio__card--selected': selectedMode === 'recorder' }"
        >
          <div class="studio__icon studio__icon--recorder">
            <svg v-if="switching && selectedMode === 'recorder'" class="animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <!-- Simplified recorder icon: video camera with REC dot -->
            <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
              <rect x="2" y="5" width="14" height="12" rx="2"/>
              <path d="M16 9l4-2v8l-4-2"/>
              <circle cx="6" cy="8" r="2" fill="currentColor" stroke="none"/>
            </svg>
          </div>
          <h3>Recorder</h3>
          <p>{{ switching && selectedMode === 'recorder' ? 'Starting...' : 'Multi-cam ISO' }}</p>
        </button>
      </div>
      
      <div class="studio__center">
        <span class="studio__badge">Choose</span>
      </div>
      
      <div class="studio__side studio__side--right">
        <button
          @click="selectMode('mixer')"
          :disabled="switching"
          class="studio__card studio__card--mixer"
          :class="{ 'studio__card--selected': selectedMode === 'mixer' }"
        >
          <div class="studio__icon studio__icon--mixer">
            <svg v-if="switching && selectedMode === 'mixer'" class="animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
              <rect x="2" y="2" width="9" height="6" rx="1"/>
              <rect x="13" y="2" width="9" height="6" rx="1"/>
              <rect x="2" y="10" width="9" height="6" rx="1"/>
              <rect x="13" y="10" width="9" height="6" rx="1"/>
              <circle cx="12" cy="20" r="2" fill="currentColor"/>
              <path d="M9 19.5a4 4 0 0 1 6 0" stroke-linecap="round"/>
            </svg>
          </div>
          <h3>Mixer</h3>
          <p>{{ switching && selectedMode === 'mixer' ? 'Starting...' : 'Live Switching' }}</p>
        </button>
      </div>
    </div>
    
    <!-- Error message -->
    <div v-if="switchError" class="studio__error">
      {{ switchError }}
    </div>
  </div>
</template>

<style scoped>
.studio {
  position: relative;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #0a0a0c;
  overflow: hidden;
}

/* Geometric background */
.studio__geo {
  position: absolute;
  inset: 0;
  overflow: hidden;
}

/* Geo layers */
.geo-layer {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.geo-layer--1 { z-index: 1; }
.geo-layer--2 { z-index: 2; }
.geo-layer--3 { z-index: 3; }
.geo-layer--4 { z-index: 4; }

/* Individual shapes - parallelograms */
.geo-shape {
  position: absolute;
  background: linear-gradient(135deg, rgba(21, 21, 24, 0.6) 0%, rgba(13, 13, 15, 0.6) 100%);
  transform-origin: center;
}

/* All shapes are parallelograms with alternating 45°/115° rotation
   Grid: 5 columns x 4 rows = 20 shapes, evenly distributed
   Edge shapes start outside container */

/* Row 1 - Top edge (starting outside) */
.geo-shape--1 {
  width: 22%;
  height: 18%;
  top: -8%;
  left: 0%;
  clip-path: polygon(25% 0%, 100% 0%, 75% 100%, 0% 100%);
  transform: rotate(45deg);
  animation: shape-breathe-45 12s ease-in-out infinite;
}

.geo-shape--2 {
  width: 20%;
  height: 16%;
  top: -6%;
  left: 20%;
  clip-path: polygon(25% 0%, 100% 0%, 75% 100%, 0% 100%);
  transform: rotate(115deg);
  animation: shape-breathe-115 14s ease-in-out infinite;
}

.geo-shape--3 {
  width: 24%;
  height: 20%;
  top: -10%;
  left: 42%;
  clip-path: polygon(25% 0%, 100% 0%, 75% 100%, 0% 100%);
  transform: rotate(45deg);
  animation: shape-breathe-45 10s ease-in-out infinite;
  animation-delay: 2s;
}

.geo-shape--4 {
  width: 18%;
  height: 14%;
  top: -5%;
  left: 65%;
  clip-path: polygon(25% 0%, 100% 0%, 75% 100%, 0% 100%);
  transform: rotate(115deg);
  animation: shape-breathe-115 13s ease-in-out infinite;
}

.geo-shape--5 {
  width: 22%;
  height: 18%;
  top: -8%;
  right: -5%;
  clip-path: polygon(25% 0%, 100% 0%, 75% 100%, 0% 100%);
  transform: rotate(45deg);
  animation: shape-breathe-45 11s ease-in-out infinite;
  animation-delay: 1s;
}

/* Row 2 - Upper middle */
.geo-shape--6 {
  width: 20%;
  height: 16%;
  top: 18%;
  left: -8%;
  clip-path: polygon(25% 0%, 100% 0%, 75% 100%, 0% 100%);
  transform: rotate(115deg);
  animation: shape-breathe-115 15s ease-in-out infinite;
}

.geo-shape--7 {
  width: 18%;
  height: 14%;
  top: 22%;
  left: 15%;
  clip-path: polygon(25% 0%, 100% 0%, 75% 100%, 0% 100%);
  transform: rotate(45deg);
  animation: shape-breathe-45 12s ease-in-out infinite;
  animation-delay: 3s;
}

.geo-shape--8 {
  width: 22%;
  height: 18%;
  top: 20%;
  left: 38%;
  clip-path: polygon(25% 0%, 100% 0%, 75% 100%, 0% 100%);
  transform: rotate(115deg);
  animation: shape-breathe-115 10s ease-in-out infinite;
}

.geo-shape--9 {
  width: 16%;
  height: 14%;
  top: 18%;
  left: 62%;
  clip-path: polygon(25% 0%, 100% 0%, 75% 100%, 0% 100%);
  transform: rotate(45deg);
  animation: shape-breathe-45 14s ease-in-out infinite;
  animation-delay: 2s;
}

.geo-shape--10 {
  width: 24%;
  height: 20%;
  top: 15%;
  right: -10%;
  clip-path: polygon(25% 0%, 100% 0%, 75% 100%, 0% 100%);
  transform: rotate(115deg);
  animation: shape-breathe-115 11s ease-in-out infinite;
}

/* Row 3 - Lower middle */
.geo-shape--11 {
  width: 22%;
  height: 18%;
  top: 48%;
  left: -10%;
  clip-path: polygon(25% 0%, 100% 0%, 75% 100%, 0% 100%);
  transform: rotate(45deg);
  animation: shape-breathe-45 13s ease-in-out infinite;
}

.geo-shape--12 {
  width: 18%;
  height: 16%;
  top: 52%;
  left: 18%;
  clip-path: polygon(25% 0%, 100% 0%, 75% 100%, 0% 100%);
  transform: rotate(115deg);
  animation: shape-breathe-115 12s ease-in-out infinite;
  animation-delay: 1s;
}

.geo-shape--13 {
  width: 20%;
  height: 16%;
  top: 50%;
  left: 40%;
  clip-path: polygon(25% 0%, 100% 0%, 75% 100%, 0% 100%);
  transform: rotate(45deg);
  animation: shape-breathe-45 15s ease-in-out infinite;
}

.geo-shape--14 {
  width: 22%;
  height: 18%;
  top: 48%;
  left: 65%;
  clip-path: polygon(25% 0%, 100% 0%, 75% 100%, 0% 100%);
  transform: rotate(115deg);
  animation: shape-breathe-115 10s ease-in-out infinite;
  animation-delay: 3s;
}

.geo-shape--15 {
  width: 20%;
  height: 16%;
  top: 52%;
  right: -8%;
  clip-path: polygon(25% 0%, 100% 0%, 75% 100%, 0% 100%);
  transform: rotate(45deg);
  animation: shape-breathe-45 14s ease-in-out infinite;
}

/* Row 4 - Bottom edge (starting outside) */
.geo-shape--16 {
  width: 24%;
  height: 20%;
  bottom: -10%;
  left: -5%;
  clip-path: polygon(25% 0%, 100% 0%, 75% 100%, 0% 100%);
  transform: rotate(115deg);
  animation: shape-breathe-115 11s ease-in-out infinite;
  animation-delay: 2s;
}

.geo-shape--17 {
  width: 20%;
  height: 16%;
  bottom: -6%;
  left: 22%;
  clip-path: polygon(25% 0%, 100% 0%, 75% 100%, 0% 100%);
  transform: rotate(45deg);
  animation: shape-breathe-45 13s ease-in-out infinite;
}

.geo-shape--18 {
  width: 22%;
  height: 18%;
  bottom: -8%;
  left: 45%;
  clip-path: polygon(25% 0%, 100% 0%, 75% 100%, 0% 100%);
  transform: rotate(115deg);
  animation: shape-breathe-115 12s ease-in-out infinite;
  animation-delay: 1s;
}

.geo-shape--19 {
  width: 18%;
  height: 14%;
  bottom: -5%;
  left: 68%;
  clip-path: polygon(25% 0%, 100% 0%, 75% 100%, 0% 100%);
  transform: rotate(45deg);
  animation: shape-breathe-45 14s ease-in-out infinite;
}

.geo-shape--20 {
  width: 22%;
  height: 18%;
  bottom: -8%;
  right: -8%;
  clip-path: polygon(25% 0%, 100% 0%, 75% 100%, 0% 100%);
  transform: rotate(115deg);
  animation: shape-breathe-115 10s ease-in-out infinite;
  animation-delay: 3s;
}

/* Breathing animations - two variants for alternating rotations */
@keyframes shape-breathe-45 {
  0%, 100% { transform: rotate(45deg) translate(0, 0); opacity: 0.75; }
  50% { transform: rotate(45deg) translate(8px, 5px); opacity: 0.9; }
}

@keyframes shape-breathe-115 {
  0%, 100% { transform: rotate(115deg) translate(0, 0); opacity: 0.7; }
  50% { transform: rotate(115deg) translate(-6px, 4px); opacity: 0.85; }
}

/* Animated soundwaves - realistic audio visualization with strong glow */
.soundwave {
  position: absolute;
  display: flex;
  align-items: center;
  gap: 4px;
  pointer-events: none;
  z-index: 0; /* Behind all shapes */
  /* Slight blur for soft edges */
  filter: blur(1px);
}

/* Subtle glow aura behind each soundwave - emits light onto surroundings */
.soundwave::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 300px;
  height: 240px;
  background: radial-gradient(
    ellipse at center,
    rgba(224, 160, 48, 0.25) 0%,
    rgba(224, 160, 48, 0.12) 25%,
    rgba(224, 160, 48, 0.05) 50%,
    rgba(224, 160, 48, 0.01) 75%,
    transparent 100%
  );
  filter: blur(40px);
  pointer-events: none;
  animation: soundwave-glow 4s ease-in-out infinite;
}

/* Secondary outer glow - reduced light emission */
.soundwave::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 400px;
  height: 320px;
  background: radial-gradient(
    ellipse at center,
    rgba(224, 160, 48, 0.08) 0%,
    rgba(224, 160, 48, 0.03) 40%,
    transparent 70%
  );
  filter: blur(60px);
  pointer-events: none;
  animation: soundwave-glow 4s ease-in-out infinite 0.5s;
}

.soundwave__bar {
  width: 5px;
  background: linear-gradient(180deg, 
    rgba(255, 200, 80, 0.9) 0%,
    rgba(224, 160, 48, 0.7) 50%,
    rgba(255, 200, 80, 0.9) 100%
  );
  border-radius: 3px;
  transform-origin: center;
  /* Base height from --h variable, animated with wave motion */
  height: calc(var(--h) * 70px);
  animation: soundwave-wave 3s ease-in-out infinite;
  /* Wave offset creates ripple effect - slower, more natural */
  animation-delay: calc(var(--i) * 0.15s);
  /* Subtle glow on each bar */
  box-shadow: 
    0 0 8px rgba(224, 160, 48, 0.3),
    0 0 15px rgba(224, 160, 48, 0.15),
    0 0 25px rgba(224, 160, 48, 0.08);
}

/* Soundwave 1 - Left side */
.soundwave--1 {
  top: 30%;
  left: 10%;
  transform: rotate(-5deg);
  opacity: 0;
  animation: soundwave-fade 14s ease-in-out infinite;
}

.soundwave--1 .soundwave__bar {
  height: calc(var(--h) * 60px);
}

/* Soundwave 2 - Right side */
.soundwave--2 {
  top: 50%;
  right: 12%;
  transform: rotate(3deg);
  opacity: 0;
  animation: soundwave-fade 14s ease-in-out infinite;
  animation-delay: 4.5s;
}

.soundwave--2 .soundwave__bar {
  height: calc(var(--h) * 55px);
}

/* Soundwave 3 - Bottom left */
.soundwave--3 {
  bottom: 20%;
  left: 18%;
  transform: rotate(-2deg);
  opacity: 0;
  animation: soundwave-fade 14s ease-in-out infinite;
  animation-delay: 9s;
}

.soundwave--3 .soundwave__bar {
  height: calc(var(--h) * 50px);
}

/* Realistic wave animation - bars move like audio levels */
@keyframes soundwave-wave {
  0%, 100% {
    transform: scaleY(0.3);
    opacity: 0.5;
  }
  25% {
    transform: scaleY(0.8);
    opacity: 0.85;
  }
  50% {
    transform: scaleY(1);
    opacity: 1;
  }
  75% {
    transform: scaleY(0.6);
    opacity: 0.75;
  }
}

/* Glow pulsing animation - reduced intensity */
@keyframes soundwave-glow {
  0%, 100% {
    opacity: 0.4;
    transform: translate(-50%, -50%) scale(0.9);
  }
  50% {
    opacity: 0.6;
    transform: translate(-50%, -50%) scale(1.1);
  }
}

/* Fade in/out animation for the whole soundwave - slow and smooth */
@keyframes soundwave-fade {
  0%, 8%, 92%, 100% {
    opacity: 0;
    transform: rotate(var(--rotation, 0deg)) translateX(-5px);
  }
  20%, 80% {
    opacity: 0.7;
    transform: rotate(var(--rotation, 0deg)) translateX(0);
  }
  40%, 60% {
    opacity: 0.85;
    transform: rotate(var(--rotation, 0deg)) translateX(0);
  }
}

/* Subtle purple background lights */
.purple-light {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  pointer-events: none;
  z-index: -1; /* Behind shapes and soundwaves */
  opacity: 0.3;
}

.purple-light--1 {
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, rgba(124, 58, 237, 0.4) 0%, rgba(124, 58, 237, 0.1) 50%, transparent 80%);
  top: 15%;
  left: -10%;
  animation: purple-float-1 25s ease-in-out infinite;
}

.purple-light--2 {
  width: 350px;
  height: 350px;
  background: radial-gradient(circle, rgba(139, 92, 246, 0.35) 0%, rgba(139, 92, 246, 0.1) 50%, transparent 80%);
  top: 60%;
  right: -8%;
  animation: purple-float-2 30s ease-in-out infinite;
  animation-delay: 5s;
}

.purple-light--3 {
  width: 300px;
  height: 300px;
  background: radial-gradient(circle, rgba(167, 139, 250, 0.3) 0%, rgba(167, 139, 250, 0.08) 50%, transparent 80%);
  bottom: 20%;
  left: 15%;
  animation: purple-float-3 28s ease-in-out infinite;
  animation-delay: 10s;
}

.purple-light--4 {
  width: 450px;
  height: 450px;
  background: radial-gradient(circle, rgba(124, 58, 237, 0.25) 0%, rgba(124, 58, 237, 0.08) 50%, transparent 80%);
  top: 40%;
  left: 50%;
  animation: purple-float-4 35s ease-in-out infinite;
  animation-delay: 15s;
}

@keyframes purple-float-1 {
  0%, 100% {
    transform: translate(0, 0) scale(1);
    opacity: 0.2;
  }
  25% {
    transform: translate(120px, 80px) scale(1.1);
    opacity: 0.35;
  }
  50% {
    transform: translate(200px, 40px) scale(0.9);
    opacity: 0.3;
  }
  75% {
    transform: translate(80px, 120px) scale(1.05);
    opacity: 0.4;
  }
}

@keyframes purple-float-2 {
  0%, 100% {
    transform: translate(0, 0) scale(1);
    opacity: 0.25;
  }
  25% {
    transform: translate(-100px, -60px) scale(1.15);
    opacity: 0.35;
  }
  50% {
    transform: translate(-180px, -100px) scale(0.85);
    opacity: 0.2;
  }
  75% {
    transform: translate(-60px, -80px) scale(1.1);
    opacity: 0.3;
  }
}

@keyframes purple-float-3 {
  0%, 100% {
    transform: translate(0, 0) scale(1);
    opacity: 0.2;
  }
  33% {
    transform: translate(60px, -40px) scale(1.2);
    opacity: 0.3;
  }
  66% {
    transform: translate(-40px, 60px) scale(0.9);
    opacity: 0.25;
  }
}

@keyframes purple-float-4 {
  0%, 100% {
    transform: translate(0, 0) scale(1);
    opacity: 0.15;
  }
  20% {
    transform: translate(-80px, 50px) scale(1.1);
    opacity: 0.25;
  }
  40% {
    transform: translate(-120px, -30px) scale(0.95);
    opacity: 0.2;
  }
  60% {
    transform: translate(-40px, -80px) scale(1.15);
    opacity: 0.3;
  }
  80% {
    transform: translate(30px, 40px) scale(1);
    opacity: 0.2;
  }
}

/* Content overlay - full width */
.studio__content {
  position: relative;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 3rem;
  width: 100%;
  max-width: 100%;
  padding: 2rem;
  box-sizing: border-box;
}

.studio__side {
  flex: 1;
  display: flex;
  justify-content: center;
  min-width: 0; /* Allow flex items to shrink if needed */
}

/* Cards */
.studio__card {
  padding: 4rem 5rem;
  background: rgba(0, 0, 0, 0.25);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 24px;
  text-align: center;
  transition: all 0.4s ease;
  cursor: pointer;
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
}

.studio__side:hover .studio__card:not(:disabled) {
  transform: translateY(-8px);
  box-shadow: 0 30px 60px rgba(0, 0, 0, 0.4);
}

.studio__card:disabled {
  opacity: 0.7;
  cursor: wait;
}

.studio__side--left:hover .studio__card:not(:disabled) {
  border-color: rgba(212, 90, 90, 0.3);
  box-shadow: 0 30px 60px rgba(0, 0, 0, 0.4), 0 0 40px rgba(212, 90, 90, 0.1);
}

.studio__card--recorder.studio__card--selected {
  border-color: rgba(212, 90, 90, 0.5);
  background: rgba(212, 90, 90, 0.08);
}

.studio__side--right:hover .studio__card:not(:disabled) {
  border-color: rgba(124, 58, 237, 0.3);
  box-shadow: 0 30px 60px rgba(0, 0, 0, 0.4), 0 0 40px rgba(124, 58, 237, 0.1);
}

.studio__card--mixer.studio__card--selected {
  border-color: rgba(124, 58, 237, 0.5);
  background: rgba(124, 58, 237, 0.08);
}

/* Icons */
.studio__icon {
  width: 100px;
  height: 100px;
  margin: 0 auto 1.5rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
}

.studio__icon svg {
  width: 44px;
  height: 44px;
}

.studio__icon--recorder {
  background: rgba(212, 90, 90, 0.15);
  color: #d45a5a;
}

.studio__side--left:hover .studio__icon--recorder {
  background: rgba(212, 90, 90, 0.25);
  box-shadow: 0 0 30px rgba(212, 90, 90, 0.3);
}

.studio__icon--mixer {
  background: rgba(124, 58, 237, 0.15);
  color: #a78bfa;
}

.studio__side--right:hover .studio__icon--mixer {
  background: rgba(124, 58, 237, 0.25);
  box-shadow: 0 0 30px rgba(124, 58, 237, 0.3);
}

.studio__card h3 {
  font-size: 1.875rem;
  font-weight: 600;
  color: var(--preke-text);
  margin-bottom: 0.5rem;
}

.studio__card p {
  font-size: 1rem;
  color: var(--preke-text-muted);
}

/* Center badge */
.studio__center {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  z-index: 5;
}

.studio__badge {
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--preke-gold);
  text-transform: uppercase;
  letter-spacing: 0.2em;
  background: var(--preke-bg);
  padding: 0.5rem 1rem;
  border-radius: 100px;
  border: 1px solid rgba(224, 160, 48, 0.2);
}

/* Error */
.studio__error {
  position: absolute;
  bottom: 2rem;
  left: 50%;
  transform: translateX(-50%);
  color: var(--preke-red);
  font-size: 0.875rem;
  z-index: 20;
}

/* Spin animation */
.animate-spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
