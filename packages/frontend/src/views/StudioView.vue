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
// Note: Idle mode endpoint may not exist on all devices, so we handle 404 gracefully
onMounted(async () => {
  try {
    const response = await fetch(await buildApiUrl('/api/mode/idle'), { method: 'POST' })
    if (response.ok) {
      console.log('[Studio] Switched to idle mode')
      // Refresh capabilities to update sidebar
      await capabilitiesStore.fetchCapabilities()
    } else if (response.status === 404) {
      // Idle mode endpoint doesn't exist - this is OK, just continue
      console.debug('[Studio] Idle mode endpoint not available')
    }
  } catch (e) {
    // Silently handle errors - idle mode is optional
    console.debug('[Studio] Idle mode not available:', e)
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
    const response = await fetch(await buildApiUrl(`/api/mode/${mode}`), { 
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
      <!-- Row 3.5: Middle-lower shapes (new row) -->
      <div class="geo-layer geo-layer--3-5">
        <div class="geo-shape geo-shape--26"></div>
        <div class="geo-shape geo-shape--27"></div>
        <div class="geo-shape geo-shape--28"></div>
        <div class="geo-shape geo-shape--29"></div>
        <div class="geo-shape geo-shape--30"></div>
      </div>
      <!-- Row 4: Lower middle shapes -->
      <div class="geo-layer geo-layer--4">
        <div class="geo-shape geo-shape--16"></div>
        <div class="geo-shape geo-shape--17"></div>
        <div class="geo-shape geo-shape--18"></div>
        <div class="geo-shape geo-shape--19"></div>
        <div class="geo-shape geo-shape--20"></div>
      </div>
      <!-- Row 5: Bottom edge shapes -->
      <div class="geo-layer geo-layer--5">
        <div class="geo-shape geo-shape--21"></div>
        <div class="geo-shape geo-shape--22"></div>
        <div class="geo-shape geo-shape--23"></div>
        <div class="geo-shape geo-shape--24"></div>
        <div class="geo-shape geo-shape--25"></div>
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
        <div class="soundwave__bar" style="--i: 0; --h: 0.2"></div>
        <div class="soundwave__bar" style="--i: 1; --h: 0.9"></div>
        <div class="soundwave__bar" style="--i: 2; --h: 0.4"></div>
        <div class="soundwave__bar" style="--i: 3; --h: 1"></div>
        <div class="soundwave__bar" style="--i: 4; --h: 0.6"></div>
        <div class="soundwave__bar" style="--i: 5; --h: 0.3"></div>
        <div class="soundwave__bar" style="--i: 6; --h: 0.8"></div>
        <div class="soundwave__bar" style="--i: 7; --h: 0.5"></div>
        <div class="soundwave__bar" style="--i: 8; --h: 0.7"></div>
        <div class="soundwave__bar" style="--i: 9; --h: 0.4"></div>
        <div class="soundwave__bar" style="--i: 10; --h: 0.9"></div>
      </div>
      <div class="soundwave soundwave--3">
        <div class="soundwave__bar" style="--i: 0; --h: 0.6"></div>
        <div class="soundwave__bar" style="--i: 1; --h: 0.3"></div>
        <div class="soundwave__bar" style="--i: 2; --h: 0.9"></div>
        <div class="soundwave__bar" style="--i: 3; --h: 0.5"></div>
        <div class="soundwave__bar" style="--i: 4; --h: 1"></div>
        <div class="soundwave__bar" style="--i: 5; --h: 0.4"></div>
        <div class="soundwave__bar" style="--i: 6; --h: 0.8"></div>
        <div class="soundwave__bar" style="--i: 7; --h: 0.2"></div>
        <div class="soundwave__bar" style="--i: 8; --h: 0.7"></div>
        <div class="soundwave__bar" style="--i: 9; --h: 0.5"></div>
        <div class="soundwave__bar" style="--i: 10; --h: 0.6"></div>
        <div class="soundwave__bar" style="--i: 11; --h: 0.3"></div>
      </div>
      <div class="soundwave soundwave--4">
        <div class="soundwave__bar" style="--i: 0; --h: 0.4"></div>
        <div class="soundwave__bar" style="--i: 1; --h: 0.8"></div>
        <div class="soundwave__bar" style="--i: 2; --h: 0.5"></div>
        <div class="soundwave__bar" style="--i: 3; --h: 1"></div>
        <div class="soundwave__bar" style="--i: 4; --h: 0.3"></div>
        <div class="soundwave__bar" style="--i: 5; --h: 0.7"></div>
        <div class="soundwave__bar" style="--i: 6; --h: 0.2"></div>
        <div class="soundwave__bar" style="--i: 7; --h: 0.9"></div>
        <div class="soundwave__bar" style="--i: 8; --h: 0.6"></div>
      </div>
      <div class="soundwave soundwave--5">
        <div class="soundwave__bar" style="--i: 0; --h: 0.7"></div>
        <div class="soundwave__bar" style="--i: 1; --h: 0.4"></div>
        <div class="soundwave__bar" style="--i: 2; --h: 0.9"></div>
        <div class="soundwave__bar" style="--i: 3; --h: 0.5"></div>
        <div class="soundwave__bar" style="--i: 4; --h: 1"></div>
        <div class="soundwave__bar" style="--i: 5; --h: 0.3"></div>
        <div class="soundwave__bar" style="--i: 6; --h: 0.8"></div>
        <div class="soundwave__bar" style="--i: 7; --h: 0.6"></div>
      </div>
      <div class="soundwave soundwave--6">
        <div class="soundwave__bar" style="--i: 0; --h: 0.5"></div>
        <div class="soundwave__bar" style="--i: 1; --h: 0.2"></div>
        <div class="soundwave__bar" style="--i: 2; --h: 0.8"></div>
        <div class="soundwave__bar" style="--i: 3; --h: 0.4"></div>
        <div class="soundwave__bar" style="--i: 4; --h: 1"></div>
        <div class="soundwave__bar" style="--i: 5; --h: 0.7"></div>
        <div class="soundwave__bar" style="--i: 6; --h: 0.3"></div>
        <div class="soundwave__bar" style="--i: 7; --h: 0.9"></div>
        <div class="soundwave__bar" style="--i: 8; --h: 0.5"></div>
        <div class="soundwave__bar" style="--i: 9; --h: 0.6"></div>
      </div>
      <div class="soundwave soundwave--7">
        <div class="soundwave__bar" style="--i: 0; --h: 0.3"></div>
        <div class="soundwave__bar" style="--i: 1; --h: 0.7"></div>
        <div class="soundwave__bar" style="--i: 2; --h: 0.5"></div>
        <div class="soundwave__bar" style="--i: 3; --h: 0.9"></div>
        <div class="soundwave__bar" style="--i: 4; --h: 0.4"></div>
        <div class="soundwave__bar" style="--i: 5; --h: 1"></div>
        <div class="soundwave__bar" style="--i: 6; --h: 0.6"></div>
        <div class="soundwave__bar" style="--i: 7; --h: 0.2"></div>
      </div>
      <div class="soundwave soundwave--8">
        <div class="soundwave__bar" style="--i: 0; --h: 0.8"></div>
        <div class="soundwave__bar" style="--i: 1; --h: 0.4"></div>
        <div class="soundwave__bar" style="--i: 2; --h: 0.6"></div>
        <div class="soundwave__bar" style="--i: 3; --h: 1"></div>
        <div class="soundwave__bar" style="--i: 4; --h: 0.3"></div>
        <div class="soundwave__bar" style="--i: 5; --h: 0.9"></div>
        <div class="soundwave__bar" style="--i: 6; --h: 0.5"></div>
        <div class="soundwave__bar" style="--i: 7; --h: 0.7"></div>
        <div class="soundwave__bar" style="--i: 8; --h: 0.4"></div>
      </div>
      
      <!-- Subtle purple background lights -->
      <div class="purple-light purple-light--1"></div>
      <div class="purple-light purple-light--2"></div>
      <div class="purple-light purple-light--3"></div>
      <div class="purple-light purple-light--4"></div>
    </div>
    
    <!-- Content overlay -->
    <div class="studio__content">
      <!-- Gradient light from top -->
      <div class="studio__gradient-light"></div>
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
        <span class="studio__badge">Choose Mode</span>
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
    
    <!-- Quick access to views for external displays -->
    <div class="studio__views">
      <span class="studio__views-label">Open on Display</span>
      <div class="studio__views-grid">
        <router-link to="/qr" class="studio__view-btn">
          <svg class="studio__view-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v1m6 11h2m-6 0h-2v4m0-11v3m0 0h.01M12 12h4.01M16 20h4M4 12h4m12 0h.01M5 8h2a1 1 0 001-1V5a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1zm12 0h2a1 1 0 001-1V5a1 1 0 00-1-1h-2a1 1 0 00-1 1v2a1 1 0 001 1zM5 20h2a1 1 0 001-1v-2a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1z"/>
          </svg>
          <span>QR Code</span>
        </router-link>
        <router-link to="/podcast" class="studio__view-btn">
          <svg class="studio__view-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"/>
          </svg>
          <span>Podcast</span>
        </router-link>
        <router-link to="/talking-head" class="studio__view-btn">
          <svg class="studio__view-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/>
          </svg>
          <span>Talking Head</span>
        </router-link>
        <router-link to="/course" class="studio__view-btn">
          <svg class="studio__view-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"/>
          </svg>
          <span>Course</span>
        </router-link>
        <router-link to="/webinar" class="studio__view-btn">
          <svg class="studio__view-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
          </svg>
          <span>Webinar</span>
        </router-link>
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
  background: var(--preke-bg-base);
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
.geo-layer--3-5 { z-index: 3; }
.geo-layer--4 { z-index: 4; }

/* Individual shapes - parallelograms - adapts to theme */
.geo-shape {
  position: absolute;
  background: linear-gradient(
    135deg,
    var(--preke-bg-surface) 0%,
    var(--preke-bg-elevated) 100%
  );
  opacity: 0.6;
  transform-origin: center;
}

/* All shapes are parallelograms with alternating 45°/115° rotation
   Grid: 5 columns x 5 rows = 25 shapes, evenly distributed
   Edge shapes start outside container */

/* Row 1 - Top edge (starting outside) */
.geo-shape--1 {
  width: 20%;
  height: 24%;
  top: -8%;
  left: 0%;
  clip-path: polygon(25% 0%, 100% 0%, 75% 100%, 0% 100%);
  transform: rotate(45deg);
  animation: shape-breathe-45 12s ease-in-out infinite;
}

.geo-shape--2 {
  width: 18%;
  height: 22%;
  top: -6%;
  left: 16%;
  clip-path: polygon(25% 0%, 100% 0%, 75% 100%, 0% 100%);
  transform: rotate(115deg);
  animation: shape-breathe-115 14s ease-in-out infinite;
}

.geo-shape--3 {
  width: 22%;
  height: 26%;
  top: -10%;
  left: 35%;
  clip-path: polygon(25% 0%, 100% 0%, 75% 100%, 0% 100%);
  transform: rotate(45deg);
  animation: shape-breathe-45 10s ease-in-out infinite;
  animation-delay: 2s;
}

.geo-shape--4 {
  width: 18%;
  height: 22%;
  top: -5%;
  left: 58%;
  clip-path: polygon(25% 0%, 100% 0%, 75% 100%, 0% 100%);
  transform: rotate(115deg);
  animation: shape-breathe-115 13s ease-in-out infinite;
}

.geo-shape--5 {
  width: 20%;
  height: 24%;
  top: -8%;
  right: -5%;
  clip-path: polygon(25% 0%, 100% 0%, 75% 100%, 0% 100%);
  transform: rotate(45deg);
  animation: shape-breathe-45 11s ease-in-out infinite;
  animation-delay: 1s;
}

/* Row 2 - Upper middle */
.geo-shape--6 {
  width: 18%;
  height: 22%;
  top: 12%;
  left: -8%;
  clip-path: polygon(25% 0%, 100% 0%, 75% 100%, 0% 100%);
  transform: rotate(115deg);
  animation: shape-breathe-115 15s ease-in-out infinite;
}

.geo-shape--7 {
  width: 20%;
  height: 24%;
  top: 14%;
  left: 12%;
  clip-path: polygon(25% 0%, 100% 0%, 75% 100%, 0% 100%);
  transform: rotate(45deg);
  animation: shape-breathe-45 12s ease-in-out infinite;
  animation-delay: 3s;
}

.geo-shape--8 {
  width: 22%;
  height: 26%;
  top: 13%;
  left: 33%;
  clip-path: polygon(25% 0%, 100% 0%, 75% 100%, 0% 100%);
  transform: rotate(115deg);
  animation: shape-breathe-115 10s ease-in-out infinite;
}

.geo-shape--9 {
  width: 18%;
  height: 22%;
  top: 12%;
  left: 56%;
  clip-path: polygon(25% 0%, 100% 0%, 75% 100%, 0% 100%);
  transform: rotate(45deg);
  animation: shape-breathe-45 14s ease-in-out infinite;
  animation-delay: 2s;
}

.geo-shape--10 {
  width: 20%;
  height: 24%;
  top: 10%;
  right: -10%;
  clip-path: polygon(25% 0%, 100% 0%, 75% 100%, 0% 100%);
  transform: rotate(115deg);
  animation: shape-breathe-115 11s ease-in-out infinite;
}

/* Row 3 - Middle */
.geo-shape--11 {
  width: 20%;
  height: 24%;
  top: 38%;
  left: -10%;
  clip-path: polygon(25% 0%, 100% 0%, 75% 100%, 0% 100%);
  transform: rotate(45deg);
  animation: shape-breathe-45 13s ease-in-out infinite;
}

.geo-shape--12 {
  width: 18%;
  height: 22%;
  top: 40%;
  left: 12%;
  clip-path: polygon(25% 0%, 100% 0%, 75% 100%, 0% 100%);
  transform: rotate(115deg);
  animation: shape-breathe-115 12s ease-in-out infinite;
  animation-delay: 1s;
}

.geo-shape--13 {
  width: 22%;
  height: 26%;
  top: 38%;
  left: 31%;
  clip-path: polygon(25% 0%, 100% 0%, 75% 100%, 0% 100%);
  transform: rotate(45deg);
  animation: shape-breathe-45 15s ease-in-out infinite;
}

.geo-shape--14 {
  width: 20%;
  height: 24%;
  top: 40%;
  left: 54%;
  clip-path: polygon(25% 0%, 100% 0%, 75% 100%, 0% 100%);
  transform: rotate(115deg);
  animation: shape-breathe-115 10s ease-in-out infinite;
  animation-delay: 3s;
}

.geo-shape--15 {
  width: 18%;
  height: 22%;
  top: 42%;
  right: -8%;
  clip-path: polygon(25% 0%, 100% 0%, 75% 100%, 0% 100%);
  transform: rotate(45deg);
  animation: shape-breathe-45 14s ease-in-out infinite;
}

/* Row 4 - Lower middle */
.geo-shape--16 {
  width: 22%;
  height: 26%;
  top: 64%;
  left: -5%;
  clip-path: polygon(25% 0%, 100% 0%, 75% 100%, 0% 100%);
  transform: rotate(115deg);
  animation: shape-breathe-115 11s ease-in-out infinite;
  animation-delay: 2s;
}

.geo-shape--17 {
  width: 18%;
  height: 22%;
  top: 66%;
  left: 14%;
  clip-path: polygon(25% 0%, 100% 0%, 75% 100%, 0% 100%);
  transform: rotate(45deg);
  animation: shape-breathe-45 13s ease-in-out infinite;
}

.geo-shape--18 {
  width: 20%;
  height: 24%;
  top: 64%;
  left: 33%;
  clip-path: polygon(25% 0%, 100% 0%, 75% 100%, 0% 100%);
  transform: rotate(115deg);
  animation: shape-breathe-115 12s ease-in-out infinite;
  animation-delay: 1s;
}

.geo-shape--19 {
  width: 22%;
  height: 26%;
  top: 66%;
  left: 54%;
  clip-path: polygon(25% 0%, 100% 0%, 75% 100%, 0% 100%);
  transform: rotate(45deg);
  animation: shape-breathe-45 14s ease-in-out infinite;
}

.geo-shape--20 {
  width: 20%;
  height: 24%;
  top: 64%;
  right: -8%;
  clip-path: polygon(25% 0%, 100% 0%, 75% 100%, 0% 100%);
  transform: rotate(115deg);
  animation: shape-breathe-115 10s ease-in-out infinite;
  animation-delay: 3s;
}

/* Row 5 - Bottom edge (starting outside) */
.geo-shape--21 {
  width: 20%;
  height: 24%;
  bottom: -10%;
  left: -3%;
  clip-path: polygon(25% 0%, 100% 0%, 75% 100%, 0% 100%);
  transform: rotate(45deg);
  animation: shape-breathe-45 12s ease-in-out infinite;
  animation-delay: 1s;
}

.geo-shape--22 {
  width: 18%;
  height: 22%;
  bottom: -8%;
  left: 16%;
  clip-path: polygon(25% 0%, 100% 0%, 75% 100%, 0% 100%);
  transform: rotate(115deg);
  animation: shape-breathe-115 14s ease-in-out infinite;
  animation-delay: 2s;
}

.geo-shape--23 {
  width: 22%;
  height: 26%;
  bottom: -10%;
  left: 35%;
  clip-path: polygon(25% 0%, 100% 0%, 75% 100%, 0% 100%);
  transform: rotate(45deg);
  animation: shape-breathe-45 11s ease-in-out infinite;
}

.geo-shape--24 {
  width: 18%;
  height: 22%;
  bottom: -7%;
  left: 58%;
  clip-path: polygon(25% 0%, 100% 0%, 75% 100%, 0% 100%);
  transform: rotate(115deg);
  animation: shape-breathe-115 13s ease-in-out infinite;
  animation-delay: 1.5s;
}

.geo-shape--25 {
  width: 20%;
  height: 24%;
  bottom: -9%;
  right: -5%;
  clip-path: polygon(25% 0%, 100% 0%, 75% 100%, 0% 100%);
  transform: rotate(45deg);
  animation: shape-breathe-45 15s ease-in-out infinite;
  animation-delay: 2.5s;
}

/* Row 3.5 - New middle-lower row (between row 3 and 4) */
.geo-shape--26 {
  width: 18%;
  height: 22%;
  top: 51%;
  left: -6%;
  clip-path: polygon(25% 0%, 100% 0%, 75% 100%, 0% 100%);
  transform: rotate(115deg);
  animation: shape-breathe-115 12s ease-in-out infinite;
  animation-delay: 1.5s;
}

.geo-shape--27 {
  width: 20%;
  height: 24%;
  top: 53%;
  left: 13%;
  clip-path: polygon(25% 0%, 100% 0%, 75% 100%, 0% 100%);
  transform: rotate(45deg);
  animation: shape-breathe-45 14s ease-in-out infinite;
  animation-delay: 0.5s;
}

.geo-shape--28 {
  width: 22%;
  height: 26%;
  top: 51%;
  left: 32%;
  clip-path: polygon(25% 0%, 100% 0%, 75% 100%, 0% 100%);
  transform: rotate(115deg);
  animation: shape-breathe-115 13s ease-in-out infinite;
  animation-delay: 2s;
}

.geo-shape--29 {
  width: 18%;
  height: 22%;
  top: 53%;
  left: 55%;
  clip-path: polygon(25% 0%, 100% 0%, 75% 100%, 0% 100%);
  transform: rotate(45deg);
  animation: shape-breathe-45 11s ease-in-out infinite;
  animation-delay: 1s;
}

.geo-shape--30 {
  width: 20%;
  height: 24%;
  top: 51%;
  right: -7%;
  clip-path: polygon(25% 0%, 100% 0%, 75% 100%, 0% 100%);
  transform: rotate(115deg);
  animation: shape-breathe-115 15s ease-in-out infinite;
  animation-delay: 2.5s;
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

/* Soundwave 1 - Random position with variation */
.soundwave--1 {
  top: 12%;
  left: 5%;
  transform: rotate(-18deg);
  opacity: 0;
  animation: soundwave-fade-1 5.5s ease-in-out infinite;
  animation-delay: 0.3s;
}

.soundwave--1 .soundwave__bar {
  height: calc(var(--h) * 65px);
}

.soundwave--1::before {
  width: 280px;
  height: 220px;
}

.soundwave--1::after {
  width: 380px;
  height: 300px;
}

/* Soundwave 2 - Random position with variation */
.soundwave--2 {
  top: 42%;
  right: 8%;
  transform: rotate(22deg);
  opacity: 0;
  animation: soundwave-fade-2 7s ease-in-out infinite;
  animation-delay: 1.8s;
}

.soundwave--2 .soundwave__bar {
  height: calc(var(--h) * 48px);
}

.soundwave--2::before {
  width: 320px;
  height: 260px;
}

.soundwave--2::after {
  width: 420px;
  height: 340px;
}

/* Soundwave 3 - Random position with variation */
.soundwave--3 {
  bottom: 18%;
  left: 28%;
  transform: rotate(-14deg);
  opacity: 0;
  animation: soundwave-fade-3 6.2s ease-in-out infinite;
  animation-delay: 3.5s;
}

.soundwave--3 .soundwave__bar {
  height: calc(var(--h) * 58px);
}

.soundwave--3::before {
  width: 300px;
  height: 240px;
}

.soundwave--3::after {
  width: 400px;
  height: 320px;
}

/* Soundwave 4 - Random position */
.soundwave--4 {
  top: 25%;
  left: 45%;
  transform: rotate(8deg);
  opacity: 0;
  animation: soundwave-fade-1 6.8s ease-in-out infinite;
  animation-delay: 4.2s;
}

.soundwave--4 .soundwave__bar {
  height: calc(var(--h) * 52px);
}

.soundwave--4::before {
  width: 290px;
  height: 230px;
}

.soundwave--4::after {
  width: 390px;
  height: 310px;
}

/* Soundwave 5 - Random position */
.soundwave--5 {
  top: 60%;
  left: 15%;
  transform: rotate(-25deg);
  opacity: 0;
  animation: soundwave-fade-2 5.8s ease-in-out infinite;
  animation-delay: 5.1s;
}

.soundwave--5 .soundwave__bar {
  height: calc(var(--h) * 54px);
}

.soundwave--5::before {
  width: 310px;
  height: 250px;
}

.soundwave--5::after {
  width: 410px;
  height: 330px;
}

/* Soundwave 6 - Random position */
.soundwave--6 {
  bottom: 35%;
  right: 25%;
  transform: rotate(15deg);
  opacity: 0;
  animation: soundwave-fade-3 6.5s ease-in-out infinite;
  animation-delay: 6.3s;
}

.soundwave--6 .soundwave__bar {
  height: calc(var(--h) * 50px);
}

.soundwave--6::before {
  width: 270px;
  height: 210px;
}

.soundwave--6::after {
  width: 370px;
  height: 290px;
}

/* Soundwave 7 - Random position */
.soundwave--7 {
  top: 8%;
  right: 30%;
  transform: rotate(-12deg);
  opacity: 0;
  animation: soundwave-fade-1 7.2s ease-in-out infinite;
  animation-delay: 7.5s;
}

.soundwave--7 .soundwave__bar {
  height: calc(var(--h) * 56px);
}

.soundwave--7::before {
  width: 300px;
  height: 240px;
}

.soundwave--7::after {
  width: 400px;
  height: 320px;
}

/* Soundwave 8 - Random position */
.soundwave--8 {
  bottom: 12%;
  left: 50%;
  transform: rotate(20deg);
  opacity: 0;
  animation: soundwave-fade-2 6.0s ease-in-out infinite;
  animation-delay: 8.7s;
}

.soundwave--8 .soundwave__bar {
  height: calc(var(--h) * 48px);
}

.soundwave--8::before {
  width: 280px;
  height: 220px;
}

.soundwave--8::after {
  width: 380px;
  height: 300px;
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

/* Fade in/out animations - varied timing for each soundwave */
@keyframes soundwave-fade-1 {
  0%, 12%, 88%, 100% {
    opacity: 0;
    transform: rotate(-18deg) translateX(-8px) translateY(3px);
  }
  28%, 72% {
    opacity: 0.65;
    transform: rotate(-18deg) translateX(0) translateY(0);
  }
  48%, 52% {
    opacity: 0.8;
    transform: rotate(-18deg) translateX(2px) translateY(-2px);
  }
}

@keyframes soundwave-fade-2 {
  0%, 8%, 92%, 100% {
    opacity: 0;
    transform: rotate(22deg) translateX(6px) translateY(-4px);
  }
  22%, 78% {
    opacity: 0.7;
    transform: rotate(22deg) translateX(0) translateY(0);
  }
  42%, 58% {
    opacity: 0.9;
    transform: rotate(22deg) translateX(-3px) translateY(2px);
  }
}

@keyframes soundwave-fade-3 {
  0%, 15%, 85%, 100% {
    opacity: 0;
    transform: rotate(-14deg) translateX(-5px) translateY(5px);
  }
  30%, 70% {
    opacity: 0.6;
    transform: rotate(-14deg) translateX(0) translateY(0);
  }
  50% {
    opacity: 0.85;
    transform: rotate(-14deg) translateX(3px) translateY(-3px);
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
  justify-content: space-around;
  gap: 1.5rem;
  width: 100%;
  max-width: 100%;
  padding: 2rem;
  box-sizing: border-box;
}

/* Gradient light from top - similar to loading screen */
.studio__gradient-light {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 60vh;
  pointer-events: none;
  background: radial-gradient(
    ellipse 100% 80% at 50% 0%,
    rgba(224, 160, 48, 0.06) 0%,
    transparent 50%
  );
  z-index: 0;
}

/* Light mode gradient */
[data-theme="light"] .studio__gradient-light {
  background: radial-gradient(
    ellipse 100% 80% at 50% 0%,
    rgba(224, 160, 48, 0.04) 0%,
    transparent 50%
  );
}

.studio__side {
  flex: 1 1 auto;
  display: flex;
  justify-content: center;
  min-width: 0; /* Allow flex items to shrink if needed */
  max-width: none;
}

/* Cards - adapts to theme */
.studio__card {
  padding: 5rem 2rem;
  background: var(--preke-glass-card);
  backdrop-filter: blur(20px) saturate(150%);
  border: 1px solid var(--preke-border-light);
  border-radius: 20px;
  text-align: center;
  transition: all 0.4s ease;
  cursor: pointer;
  width: 100%;
  max-width: 320px;
  box-sizing: border-box;
  /* Liquid glass glow effect - adapts to theme */
  box-shadow: 
    var(--preke-shadow-lg),
    0 0 0 1px var(--preke-border-light) inset,
    0 1px 0 var(--preke-border-light) inset,
    0 0 20px var(--preke-glass-light);
  position: relative;
}

.studio__card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(
    90deg,
    transparent,
    var(--preke-border-light),
    transparent
  );
  border-radius: 20px 20px 0 0;
  pointer-events: none;
}

/* Light mode: More transparent and liquid glass effect */
[data-theme="light"] .studio__card {
  background: linear-gradient(
    145deg,
    rgba(255, 255, 255, 0.4) 0%,
    rgba(255, 255, 255, 0.25) 50%,
    rgba(255, 255, 255, 0.15) 100%
  );
  backdrop-filter: blur(30px) saturate(180%);
  -webkit-backdrop-filter: blur(30px) saturate(180%);
  border: 1px solid rgba(255, 255, 255, 0.3);
  box-shadow: 
    0 8px 32px rgba(0, 0, 0, 0.08),
    0 0 0 1px rgba(255, 255, 255, 0.5) inset,
    0 1px 0 rgba(255, 255, 255, 0.6) inset,
    0 0 40px rgba(255, 255, 255, 0.2),
    /* Outer glow */
    0 0 60px rgba(255, 255, 255, 0.1);
}

[data-theme="light"] .studio__card::before {
  background: linear-gradient(
    90deg,
    transparent,
    rgba(255, 255, 255, 0.6),
    transparent
  );
}

[data-theme="light"] .studio__card::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 20px;
  background: linear-gradient(
    160deg,
    rgba(255, 255, 255, 0.15) 0%,
    rgba(255, 255, 255, 0.05) 30%,
    transparent 60%
  );
  pointer-events: none;
}

.studio__side:hover .studio__card:not(:disabled) {
  transform: translateY(-8px);
  box-shadow: var(--preke-shadow-xl);
}

.studio__card:disabled {
  opacity: 0.7;
  cursor: wait;
}

.studio__side--left:hover .studio__card:not(:disabled) {
  border-color: var(--preke-red);
  box-shadow: var(--preke-shadow-xl), 0 0 40px var(--preke-red-bg);
}

.studio__card--recorder.studio__card--selected {
  border-color: var(--preke-red);
  background: var(--preke-red-bg);
}

.studio__side--right:hover .studio__card:not(:disabled) {
  border-color: var(--preke-purple);
  box-shadow: var(--preke-shadow-xl), 0 0 40px var(--preke-purple-bg);
}

.studio__card--mixer.studio__card--selected {
  border-color: var(--preke-purple);
  background: var(--preke-purple-bg);
}

/* Icons */
.studio__icon {
  width: 80px;
  height: 80px;
  margin: 0 auto 1rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
}

.studio__icon svg {
  width: 36px;
  height: 36px;
}

.studio__icon--recorder {
  background: var(--preke-red-bg);
  color: var(--preke-red);
}

.studio__side--left:hover .studio__icon--recorder {
  background: var(--preke-red-bg);
  box-shadow: 0 0 30px var(--preke-red-bg);
}

.studio__icon--mixer {
  background: var(--preke-purple-bg);
  color: var(--preke-purple);
}

.studio__side--right:hover .studio__icon--mixer {
  background: var(--preke-purple-bg);
  box-shadow: 0 0 30px var(--preke-purple-bg);
}

.studio__card h3 {
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--preke-text);
  margin-bottom: 0.5rem;
}

.studio__card p {
  font-size: 0.875rem;
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
  background: var(--preke-bg-elevated);
  padding: 0.5rem 1rem;
  border-radius: 100px;
  border: 1px solid var(--preke-border-gold);
  box-shadow: var(--preke-shadow-sm);
}

/* Views section */
.studio__views {
  position: absolute;
  bottom: 3rem;
  left: 50%;
  transform: translateX(-50%);
  z-index: 10;
  text-align: center;
}

.studio__views-label {
  display: block;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--preke-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin-bottom: 0.75rem;
}

.studio__views-grid {
  display: flex;
  gap: 0.75rem;
}

.studio__view-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.375rem;
  padding: 0.75rem 1rem;
  background: var(--preke-bg-elevated);
  border: 1px solid var(--preke-border);
  border-radius: var(--preke-radius-md);
  color: var(--preke-text-dim);
  text-decoration: none;
  font-size: 0.75rem;
  font-weight: 500;
  transition: all 0.2s ease;
  cursor: pointer;
}

.studio__view-btn:hover {
  background: var(--preke-glass-bg);
  border-color: var(--preke-border-gold);
  color: var(--preke-gold);
  transform: translateY(-2px);
  box-shadow: var(--preke-shadow-md);
}

.studio__view-icon {
  width: 1.25rem;
  height: 1.25rem;
  stroke-width: 2;
}

/* Error */
.studio__error {
  position: absolute;
  bottom: 1rem;
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
