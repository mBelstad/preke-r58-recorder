<script setup lang="ts">
/**
 * Background Design Drafts View
 * Combined view of design proposals and background experiments
 * Navigate to /background-drafts to view these live
 */
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import geometricPattern from '@/assets/geometric-pattern.jpeg'

const router = useRouter()
const route = useRoute()
const activeDraft = ref<number>(1)

// Combined list: proposals (1-6) + experiments (7-11)
const drafts = [
  // Design Proposals
  { id: 1, name: 'Split Home', desc: 'Two-mode split design for home' },
  { id: 2, name: 'Geometric 3D', desc: 'Animated 3D geometric shapes' },
  { id: 3, name: 'Combined', desc: 'Split + geometric together' },
  { id: 4, name: 'Ribbons', desc: 'Complex intersecting ribbons' },
  { id: 5, name: 'Stock Image', desc: 'Photo background with light effects' },
  { id: 6, name: 'Cyberpunk', desc: 'Neon circuits with glowing edges' },
  // Background Experiments
  { id: 7, name: 'Breathing Tech', desc: 'Organic breathing with subtle pulse' },
  { id: 8, name: 'Tron Grid', desc: 'Hexagonal overlay with scan lines' },
  { id: 9, name: 'Circuit Flow', desc: 'Data flowing through circuits' },
  { id: 10, name: 'Holographic', desc: 'Hologram-like distortion effect' },
  { id: 11, name: 'Neural Net', desc: 'Connected nodes pulsing with life' },
]

// Handle draft query parameter
onMounted(() => {
  const draftParam = route.query.draft
  if (draftParam) {
    const draftId = parseInt(draftParam as string, 10)
    if (draftId >= 1 && draftId <= 11) {
      activeDraft.value = draftId
    }
  }
})

// Simulated mode selection (for demo)
function selectMode(mode: 'recorder' | 'mixer') {
  console.log('Selected mode:', mode)
  // In real app: router.push(`/${mode}`)
}
</script>

<template>
  <div class="drafts">
    <!-- Navigation -->
    <div class="drafts__nav">
      <button class="drafts__back" @click="router.back()">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M19 12H5M12 19l-7-7 7-7"/>
        </svg>
        Back
      </button>
      <h1 class="drafts__title">Background Design Drafts</h1>
      <div class="drafts__tabs">
        <button 
          v-for="d in drafts" 
          :key="d.id"
          @click="activeDraft = d.id"
          class="drafts__tab"
          :class="{ 'drafts__tab--active': activeDraft === d.id }"
        >
          {{ d.name }}
        </button>
      </div>
    </div>

    <!-- ═══════════════════════════════════════════
         DRAFT 1: SPLIT HOME
         ═══════════════════════════════════════════ -->
    <div v-show="activeDraft === 1" class="draft split-home">
      <!-- Recorder Side (Left) -->
      <div class="split-home__side split-home__side--recorder" @click="selectMode('recorder')">
        <div class="split-home__bg">
          <div class="split-home__glow split-home__glow--red"></div>
          <div class="split-home__grid"></div>
        </div>
        <div class="split-home__content">
          <div class="split-home__icon split-home__icon--recorder">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
              <rect x="2" y="5" width="14" height="12" rx="2"/>
              <path d="M16 9l4-2v8l-4-2"/>
              <circle cx="6" cy="8" r="2" fill="currentColor" stroke="none"/>
            </svg>
          </div>
          <h2 class="split-home__title">Recorder</h2>
          <p class="split-home__desc">Multi-cam ISO Recording</p>
          <div class="split-home__features">
            <span>4K Capture</span>
            <span>•</span>
            <span>Multi-track</span>
            <span>•</span>
            <span>Sync</span>
          </div>
        </div>
        <div class="split-home__hover-line"></div>
      </div>

      <!-- Mixer Side (Right) -->
      <div class="split-home__side split-home__side--mixer" @click="selectMode('mixer')">
        <div class="split-home__bg">
          <div class="split-home__glow split-home__glow--purple"></div>
          <div class="split-home__grid"></div>
        </div>
        <div class="split-home__content">
          <div class="split-home__icon split-home__icon--mixer">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
              <rect x="2" y="2" width="9" height="6" rx="1"/>
              <rect x="13" y="2" width="9" height="6" rx="1"/>
              <rect x="2" y="10" width="9" height="6" rx="1"/>
              <rect x="13" y="10" width="9" height="6" rx="1"/>
              <circle cx="12" cy="20" r="2" fill="currentColor"/>
              <path d="M9 19.5a4 4 0 0 1 6 0" stroke-linecap="round"/>
            </svg>
          </div>
          <h2 class="split-home__title">Mixer</h2>
          <p class="split-home__desc">Live Switching & Streaming</p>
          <div class="split-home__features">
            <span>Multi-view</span>
            <span>•</span>
            <span>Transitions</span>
            <span>•</span>
            <span>Stream</span>
          </div>
        </div>
        <div class="split-home__hover-line"></div>
      </div>
    </div>

    <!-- ═══════════════════════════════════════════
         DRAFT 2: GEOMETRIC 3D
         ═══════════════════════════════════════════ -->
    <div v-show="activeDraft === 2" class="draft geometric">
      <div class="geometric__canvas">
        <!-- Layer 1: Background shapes (darkest) -->
        <div class="geo-layer geo-layer--1">
          <div class="geo-shape geo-shape--1"></div>
          <div class="geo-shape geo-shape--2"></div>
          <div class="geo-shape geo-shape--3"></div>
        </div>
        
        <!-- Layer 2: Mid shapes -->
        <div class="geo-layer geo-layer--2">
          <div class="geo-shape geo-shape--4"></div>
          <div class="geo-shape geo-shape--5"></div>
        </div>
        
        <!-- Layer 3: Front shapes with gold edge -->
        <div class="geo-layer geo-layer--3">
          <div class="geo-shape geo-shape--6"></div>
          <div class="geo-shape geo-shape--7"></div>
        </div>
        
        <!-- Gold glimmer effects -->
        <div class="geo-glimmer geo-glimmer--1"></div>
        <div class="geo-glimmer geo-glimmer--2"></div>
        <div class="geo-glimmer geo-glimmer--3"></div>
        
        <!-- Ambient glow -->
        <div class="geo-ambient"></div>
      </div>
      
      <div class="geometric__content">
        <h2 class="geometric__title">Geometric 3D</h2>
        <p class="geometric__desc">Layered shapes with depth, animated gold glimmers catching the light</p>
      </div>
    </div>

    <!-- ═══════════════════════════════════════════
         DRAFT 3: COMBINED
         ═══════════════════════════════════════════ -->
    <div v-show="activeDraft === 3" class="draft combined">
      <!-- Geometric background - 20 parallelograms evenly distributed -->
      <div class="combined__geo">
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
        <!-- Gold glimmers behind shapes -->
        <div class="geo-glimmer geo-glimmer--1"></div>
        <div class="geo-glimmer geo-glimmer--2"></div>
        <div class="geo-glimmer geo-glimmer--3"></div>
      </div>
      
      <!-- Split content overlay -->
      <div class="combined__split">
        <div class="combined__side combined__side--left" @click="selectMode('recorder')">
          <div class="combined__card">
            <div class="combined__icon combined__icon--recorder">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                <rect x="2" y="4" width="14" height="4" rx="1"/>
                <rect x="2" y="10" width="14" height="4" rx="1"/>
                <rect x="2" y="16" width="14" height="4" rx="1"/>
                <circle cx="20" cy="6" r="3" fill="currentColor" stroke="none"/>
                <circle cx="20" cy="15" r="3"/>
                <circle cx="20" cy="15" r="1.5" fill="currentColor" stroke="none"/>
              </svg>
            </div>
            <h3>Recorder</h3>
            <p>Multi-cam ISO</p>
          </div>
        </div>
        
        <div class="combined__center">
          <span class="combined__logo">Choose</span>
        </div>
        
        <div class="combined__side combined__side--right" @click="selectMode('mixer')">
          <div class="combined__card">
            <div class="combined__icon combined__icon--mixer">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                <rect x="2" y="2" width="9" height="6" rx="1"/>
                <rect x="13" y="2" width="9" height="6" rx="1"/>
                <rect x="2" y="10" width="9" height="6" rx="1"/>
                <rect x="13" y="10" width="9" height="6" rx="1"/>
                <circle cx="12" cy="20" r="2" fill="currentColor"/>
                <path d="M9 19.5a4 4 0 0 1 6 0" stroke-linecap="round"/>
              </svg>
            </div>
            <h3>Mixer</h3>
            <p>Live Switching</p>
          </div>
        </div>
      </div>
    </div>

    <!-- ═══════════════════════════════════════════
         DRAFT 4: COMPLEX RIBBONS
         ═══════════════════════════════════════════ -->
    <div v-show="activeDraft === 4" class="draft ribbons">
      <!-- Complex ribbon background - more shapes, semi-symmetrical -->
      <div class="ribbons__canvas">
        <!-- Layer 1: Back ribbons (darkest) -->
        <div class="ribbon ribbon--1"></div>
        <div class="ribbon ribbon--2"></div>
        <div class="ribbon ribbon--3"></div>
        <div class="ribbon ribbon--4"></div>
        <div class="ribbon ribbon--5"></div>
        <div class="ribbon ribbon--6"></div>
        
        <!-- Layer 2: Mid ribbons -->
        <div class="ribbon ribbon--7"></div>
        <div class="ribbon ribbon--8"></div>
        <div class="ribbon ribbon--9"></div>
        <div class="ribbon ribbon--10"></div>
        <div class="ribbon ribbon--11"></div>
        <div class="ribbon ribbon--12"></div>
        
        <!-- Layer 3: Front ribbons (lightest, with gold edges) -->
        <div class="ribbon ribbon--13"></div>
        <div class="ribbon ribbon--14"></div>
        <div class="ribbon ribbon--15"></div>
        <div class="ribbon ribbon--16"></div>
        
        <!-- Gold glimmers along edges -->
        <div class="ribbon-glimmer glimmer--1"></div>
        <div class="ribbon-glimmer glimmer--2"></div>
        <div class="ribbon-glimmer glimmer--3"></div>
        <div class="ribbon-glimmer glimmer--4"></div>
        <div class="ribbon-glimmer glimmer--5"></div>
        
        <!-- Central ambient glow -->
        <div class="ribbons__ambient"></div>
      </div>
      
      <!-- Content overlay -->
      <div class="ribbons__content">
        <div class="ribbons__side ribbons__side--left" @click="selectMode('recorder')">
          <div class="ribbons__card">
            <div class="ribbons__icon ribbons__icon--recorder">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                <rect x="2" y="4" width="14" height="4" rx="1"/>
                <rect x="2" y="10" width="14" height="4" rx="1"/>
                <rect x="2" y="16" width="14" height="4" rx="1"/>
                <circle cx="20" cy="6" r="3" fill="currentColor" stroke="none"/>
                <circle cx="20" cy="15" r="3"/>
                <circle cx="20" cy="15" r="1.5" fill="currentColor" stroke="none"/>
              </svg>
            </div>
            <h3>Recorder</h3>
            <p>Multi-cam ISO</p>
          </div>
        </div>
        
        <div class="ribbons__center">
          <span class="ribbons__logo">Choose</span>
        </div>
        
        <div class="ribbons__side ribbons__side--right" @click="selectMode('mixer')">
          <div class="ribbons__card">
            <div class="ribbons__icon ribbons__icon--mixer">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                <rect x="2" y="2" width="9" height="6" rx="1"/>
                <rect x="13" y="2" width="9" height="6" rx="1"/>
                <rect x="2" y="10" width="9" height="6" rx="1"/>
                <rect x="13" y="10" width="9" height="6" rx="1"/>
                <circle cx="12" cy="20" r="2" fill="currentColor"/>
                <path d="M9 19.5a4 4 0 0 1 6 0" stroke-linecap="round"/>
              </svg>
            </div>
            <h3>Mixer</h3>
            <p>Live Switching</p>
          </div>
        </div>
      </div>
    </div>

    <!-- ═══════════════════════════════════════════
         DRAFT 5: STOCK IMAGE
         Photo background with animated light
         ═══════════════════════════════════════════ -->
    <div v-show="activeDraft === 5" class="draft stock-image">
      <!-- Moving light behind the image -->
      <div class="stock-image__light"></div>
      
      <!-- The stock image (semi-transparent) -->
      <div class="stock-image__photo"></div>
      
      <!-- Dark overlay on top -->
      <div class="stock-image__overlay"></div>
      
      <!-- Content -->
      <div class="stock-image__content">
        <div class="stock-image__side stock-image__side--left" @click="selectMode('recorder')">
          <div class="stock-image__card">
            <div class="stock-image__icon stock-image__icon--recorder">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                <rect x="2" y="4" width="14" height="4" rx="1"/>
                <rect x="2" y="10" width="14" height="4" rx="1"/>
                <rect x="2" y="16" width="14" height="4" rx="1"/>
                <circle cx="20" cy="6" r="3" fill="currentColor" stroke="none"/>
                <circle cx="20" cy="15" r="3"/>
                <circle cx="20" cy="15" r="1.5" fill="currentColor" stroke="none"/>
              </svg>
            </div>
            <h3>Recorder</h3>
            <p>Multi-cam ISO</p>
          </div>
        </div>
        
        <div class="stock-image__center">
          <span class="stock-image__logo">Choose</span>
        </div>
        
        <div class="stock-image__side stock-image__side--right" @click="selectMode('mixer')">
          <div class="stock-image__card">
            <div class="stock-image__icon stock-image__icon--mixer">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                <rect x="2" y="2" width="9" height="6" rx="1"/>
                <rect x="13" y="2" width="9" height="6" rx="1"/>
                <rect x="2" y="10" width="9" height="6" rx="1"/>
                <rect x="13" y="10" width="9" height="6" rx="1"/>
                <circle cx="12" cy="20" r="2" fill="currentColor"/>
                <path d="M9 19.5a4 4 0 0 1 6 0" stroke-linecap="round"/>
              </svg>
            </div>
            <h3>Mixer</h3>
            <p>Live Switching</p>
          </div>
        </div>
      </div>
    </div>

    <!-- ═══════════════════════════════════════════
         DRAFT 6: CYBERPUNK
         Neon circuits with glowing orange edges
         Inspired by sci-fi tech aesthetics
         ═══════════════════════════════════════════ -->
    <div v-show="activeDraft === 6" class="draft cyberpunk">
      <!-- Circuit pattern background -->
      <div class="cyber__circuits"></div>
      
      <!-- Glowing neon lines -->
      <div class="cyber__neon cyber__neon--1"></div>
      <div class="cyber__neon cyber__neon--2"></div>
      <div class="cyber__neon cyber__neon--3"></div>
      <div class="cyber__neon cyber__neon--4"></div>
      <div class="cyber__neon cyber__neon--5"></div>
      
      <!-- Floating sparks -->
      <div class="cyber__sparks">
        <div class="cyber__spark cyber__spark--1"></div>
        <div class="cyber__spark cyber__spark--2"></div>
        <div class="cyber__spark cyber__spark--3"></div>
        <div class="cyber__spark cyber__spark--4"></div>
        <div class="cyber__spark cyber__spark--5"></div>
        <div class="cyber__spark cyber__spark--6"></div>
        <div class="cyber__spark cyber__spark--7"></div>
        <div class="cyber__spark cyber__spark--8"></div>
      </div>
      
      <!-- Ambient glow -->
      <div class="cyber__glow"></div>
      
      <!-- Content -->
      <div class="cyber__content">
        <div class="cyber__side cyber__side--left" @click="selectMode('recorder')">
          <div class="cyber__card">
            <div class="cyber__icon cyber__icon--recorder">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                <rect x="2" y="4" width="14" height="4" rx="1"/>
                <rect x="2" y="10" width="14" height="4" rx="1"/>
                <rect x="2" y="16" width="14" height="4" rx="1"/>
                <circle cx="20" cy="6" r="3" fill="currentColor" stroke="none"/>
                <circle cx="20" cy="15" r="3"/>
                <circle cx="20" cy="15" r="1.5" fill="currentColor" stroke="none"/>
              </svg>
            </div>
            <h3>Recorder</h3>
            <p>Multi-cam ISO</p>
          </div>
        </div>
        
        <div class="cyber__center">
          <span class="cyber__logo">Preke Studio</span>
        </div>
        
        <div class="cyber__side cyber__side--right" @click="selectMode('mixer')">
          <div class="cyber__card">
            <div class="cyber__icon cyber__icon--mixer">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                <rect x="2" y="2" width="9" height="6" rx="1"/>
                <rect x="13" y="2" width="9" height="6" rx="1"/>
                <rect x="2" y="10" width="9" height="6" rx="1"/>
                <rect x="13" y="10" width="9" height="6" rx="1"/>
                <circle cx="12" cy="20" r="2" fill="currentColor"/>
                <path d="M9 19.5a4 4 0 0 1 6 0" stroke-linecap="round"/>
              </svg>
            </div>
            <h3>Mixer</h3>
            <p>Live Switching</p>
          </div>
        </div>
      </div>
    </div>

    <!-- ═══════════════════════════════════════════
         DRAFT 7: BREATHING TECH
         ═══════════════════════════════════════════ -->
    <div v-show="activeDraft === 7" class="draft exp exp--breathing">
      <div class="exp__layer">
        <img :src="geometricPattern" alt="" class="exp__img exp__img--breathe" />
        <div class="exp__overlay exp__overlay--dark"></div>
        <div class="exp__pulse exp__pulse--center"></div>
      </div>
      <div class="exp__content">
        <h2 class="exp__heading">Breathing Tech</h2>
        <p class="exp__desc">The geometric pattern slowly breathes - expanding and contracting like a living organism. Subtle center pulse adds depth.</p>
      </div>
    </div>

    <!-- ═══════════════════════════════════════════
         DRAFT 8: TRON GRID
         ═══════════════════════════════════════════ -->
    <div v-show="activeDraft === 8" class="draft exp exp--tron">
      <div class="exp__layer">
        <img :src="geometricPattern" alt="" class="exp__img" />
        <div class="exp__overlay exp__overlay--dark"></div>
        <div class="exp__hex-grid"></div>
        <div class="exp__scan-line exp__scan-line--h"></div>
        <div class="exp__scan-line exp__scan-line--v"></div>
      </div>
      <div class="exp__content">
        <h2 class="exp__heading exp__heading--tron">Tron Grid</h2>
        <p class="exp__desc">Hexagonal grid overlay with scanning beams that sweep across. Classic Tron aesthetic.</p>
      </div>
    </div>

    <!-- ═══════════════════════════════════════════
         DRAFT 9: CIRCUIT FLOW
         ═══════════════════════════════════════════ -->
    <div v-show="activeDraft === 9" class="draft exp exp--circuit">
      <div class="exp__layer">
        <img :src="geometricPattern" alt="" class="exp__img" />
        <div class="exp__overlay exp__overlay--circuit"></div>
        <div class="circuit">
          <div class="circuit__line circuit__line--1">
            <div class="circuit__particle"></div>
          </div>
          <div class="circuit__line circuit__line--2">
            <div class="circuit__particle"></div>
          </div>
          <div class="circuit__line circuit__line--3">
            <div class="circuit__particle"></div>
          </div>
          <div class="circuit__node circuit__node--1"></div>
          <div class="circuit__node circuit__node--2"></div>
          <div class="circuit__node circuit__node--3"></div>
        </div>
      </div>
      <div class="exp__content">
        <h2 class="exp__heading exp__heading--gold">Circuit Flow</h2>
        <p class="exp__desc">Data particles flowing through circuit traces. Nodes pulse as data passes through.</p>
      </div>
    </div>

    <!-- ═══════════════════════════════════════════
         DRAFT 10: HOLOGRAPHIC
         ═══════════════════════════════════════════ -->
    <div v-show="activeDraft === 10" class="draft exp exp--holo">
      <div class="exp__layer">
        <img :src="geometricPattern" alt="" class="exp__img exp__img--holo" />
        <div class="exp__overlay exp__overlay--holo"></div>
        <div class="exp__scanlines"></div>
        <div class="exp__glitch"></div>
      </div>
      <div class="exp__content">
        <h2 class="exp__heading exp__heading--holo">Holographic</h2>
        <p class="exp__desc">Hologram-like effect with scan lines and subtle chromatic aberration. Feels like projected technology.</p>
      </div>
    </div>

    <!-- ═══════════════════════════════════════════
         DRAFT 11: NEURAL NET
         ═══════════════════════════════════════════ -->
    <div v-show="activeDraft === 11" class="draft exp exp--neural">
      <div class="exp__layer">
        <img :src="geometricPattern" alt="" class="exp__img" />
        <div class="exp__overlay exp__overlay--neural"></div>
        <div class="neural">
          <div class="neural__node neural__node--1"></div>
          <div class="neural__node neural__node--2"></div>
          <div class="neural__node neural__node--3"></div>
          <div class="neural__node neural__node--4"></div>
          <div class="neural__node neural__node--5"></div>
          <svg class="neural__connections" viewBox="0 0 100 100" preserveAspectRatio="none">
            <line x1="20" y1="30" x2="50" y2="50" class="neural__line" />
            <line x1="80" y1="25" x2="50" y2="50" class="neural__line neural__line--delay1" />
            <line x1="15" y1="70" x2="50" y2="50" class="neural__line neural__line--delay2" />
            <line x1="85" y1="75" x2="50" y2="50" class="neural__line neural__line--delay3" />
          </svg>
        </div>
      </div>
      <div class="exp__content">
        <h2 class="exp__heading exp__heading--purple">Neural Network</h2>
        <p class="exp__desc">Connected nodes that pulse with activity. Lines glow as signals pass between neurons.</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.drafts {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--preke-bg);
  overflow-y: auto;
}

.drafts__nav {
  position: sticky;
  top: 0;
  z-index: 100;
  padding: 1rem 2rem 1.5rem;
  background: rgba(0, 0, 0, 0.85);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--preke-border);
}

/* Light mode navigation bar */
[data-theme="light"] .drafts__nav {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
}

/* Back button */
.drafts__back {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  margin-bottom: 1rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 6px;
  color: var(--preke-text-muted);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

[data-theme="light"] .drafts__back {
  background: rgba(0, 0, 0, 0.05);
  border: 1px solid rgba(0, 0, 0, 0.1);
}

.drafts__back:hover {
  background: rgba(255, 255, 255, 0.1);
  color: var(--preke-text);
  border-color: rgba(255, 255, 255, 0.2);
}

[data-theme="light"] .drafts__back:hover {
  background: rgba(0, 0, 0, 0.1);
  border-color: rgba(0, 0, 0, 0.2);
}

.drafts__back svg {
  width: 16px;
  height: 16px;
}

.drafts__title {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--preke-text);
  margin-bottom: 1rem;
}

.drafts__tabs {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.drafts__tab {
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--preke-text-muted);
  background: transparent;
  border: 1px solid var(--preke-border);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.drafts__tab:hover {
  color: var(--preke-text);
  border-color: var(--preke-border-light);
}

.drafts__tab--active {
  color: var(--preke-gold);
  background: rgba(224, 160, 48, 0.1);
  border-color: var(--preke-gold);
}

.draft {
  flex: 1;
  position: relative;
  overflow: hidden;
}

/* ═══════════════════════════════════════════
   PROPOSAL 1: SPLIT HOME
   ═══════════════════════════════════════════ */
.split-home {
  display: flex;
  height: 100%;
}

.split-home__side {
  flex: 1;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  overflow: hidden;
  transition: flex 0.5s cubic-bezier(0.4, 0, 0.2, 1);
}

.split-home__side:hover {
  flex: 1.15;
}

.split-home__bg {
  position: absolute;
  inset: 0;
}

.split-home__glow {
  position: absolute;
  width: 150%;
  height: 150%;
  border-radius: 50%;
  filter: blur(150px);
  animation: glow-pulse 6s ease-in-out infinite;
}

.split-home__glow--red {
  background: radial-gradient(circle, rgba(212, 90, 90, 0.25) 0%, transparent 70%);
  top: -25%;
  left: -25%;
}

.split-home__glow--purple {
  background: radial-gradient(circle, rgba(124, 58, 237, 0.25) 0%, transparent 70%);
  top: -25%;
  right: -25%;
}

@keyframes glow-pulse {
  0%, 100% { opacity: 0.6; transform: scale(1); }
  50% { opacity: 1; transform: scale(1.1); }
}

.split-home__grid {
  position: absolute;
  inset: -50%;
  opacity: 0.06;
  background: 
    repeating-linear-gradient(
      60deg,
      transparent,
      transparent 20px,
      rgba(255, 255, 255, 0.02) 20px,
      rgba(255, 255, 255, 0.02) 21px
    ),
    repeating-linear-gradient(
      -60deg,
      transparent,
      transparent 20px,
      rgba(255, 255, 255, 0.02) 20px,
      rgba(255, 255, 255, 0.02) 21px
    ),
    repeating-linear-gradient(
      0deg,
      transparent,
      transparent 35px,
      rgba(255, 255, 255, 0.015) 35px,
      rgba(255, 255, 255, 0.015) 36px
    );
  animation: grid-shift 20s linear infinite;
}

@keyframes grid-shift {
  0% { transform: translateY(0); }
  100% { transform: translateY(36px); }
}

.split-home__content {
  position: relative;
  z-index: 2;
  text-align: center;
  transform: translateY(0);
  transition: transform 0.4s ease;
}

.split-home__side:hover .split-home__content {
  transform: translateY(-10px);
}

.split-home__icon {
  width: 100px;
  height: 100px;
  margin: 0 auto 1.5rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.4s ease;
}

.split-home__icon svg {
  width: 48px;
  height: 48px;
}

.split-home__icon--recorder {
  background: rgba(212, 90, 90, 0.2);
  border: 2px solid rgba(212, 90, 90, 0.4);
  color: #d45a5a;
  box-shadow: 0 0 40px rgba(212, 90, 90, 0.2);
}

.split-home__side:hover .split-home__icon--recorder {
  box-shadow: 0 0 60px rgba(212, 90, 90, 0.4);
  transform: scale(1.1);
}

.split-home__icon--mixer {
  background: rgba(124, 58, 237, 0.2);
  border: 2px solid rgba(124, 58, 237, 0.4);
  color: #a78bfa;
  box-shadow: 0 0 40px rgba(124, 58, 237, 0.2);
}

.split-home__side:hover .split-home__icon--mixer {
  box-shadow: 0 0 60px rgba(124, 58, 237, 0.4);
  transform: scale(1.1);
}

.split-home__title {
  font-size: 2.5rem;
  font-weight: 700;
  color: var(--preke-text);
  margin-bottom: 0.5rem;
}

.split-home__side--recorder .split-home__title {
  color: #d45a5a;
}

.split-home__side--mixer .split-home__title {
  color: #a78bfa;
}

.split-home__desc {
  font-size: 1.125rem;
  color: var(--preke-text-muted);
  margin-bottom: 1.5rem;
}

.split-home__features {
  display: flex;
  gap: 0.75rem;
  justify-content: center;
  font-size: 0.875rem;
  color: var(--preke-text-muted);
  opacity: 0.7;
}

.split-home__hover-line {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 3px;
  transform: scaleX(0);
  transition: transform 0.4s ease;
}

.split-home__side--recorder .split-home__hover-line {
  background: linear-gradient(90deg, transparent, #d45a5a, transparent);
}

.split-home__side--mixer .split-home__hover-line {
  background: linear-gradient(90deg, transparent, #a78bfa, transparent);
}

.split-home__side:hover .split-home__hover-line {
  transform: scaleX(1);
}

/* Divider */
.split-home__divider {
  position: absolute;
  left: 50%;
  top: 0;
  bottom: 0;
  width: 1px;
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  z-index: 10;
}

.split-home__divider-line {
  flex: 1;
  width: 1px;
  background: linear-gradient(180deg, transparent, rgba(255, 255, 255, 0.2), transparent);
  animation: divider-pulse 15s ease-in-out infinite alternate;
  transform-origin: center center;
}

@keyframes divider-pulse {
  0%, 100% { 
    opacity: 0.6; 
    transform: scaleY(1);
  }
  50% { 
    opacity: 1; 
    transform: scaleY(1.02);
  }
}

.split-home__divider-logo {
  padding: 1.5rem 0;
}

.split-home__divider-text {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--preke-gold);
  text-transform: uppercase;
  letter-spacing: 0.15em;
  writing-mode: vertical-rl;
  text-orientation: mixed;
}

/* ═══════════════════════════════════════════
   PROPOSAL 2: GEOMETRIC 3D
   ═══════════════════════════════════════════ */
.geometric {
  display: flex;
  align-items: center;
  justify-content: center;
  background: #0a0a0c;
}

.geometric__canvas {
  position: absolute;
  inset: 0;
  overflow: hidden;
}

.geometric__content {
  position: relative;
  z-index: 10;
  text-align: center;
}

.geometric__title {
  font-size: 2.5rem;
  font-weight: 700;
  color: var(--preke-text);
  margin-bottom: 0.5rem;
}

.geometric__desc {
  font-size: 1rem;
  color: var(--preke-text-muted);
  max-width: 400px;
}

/* Geometric Layers */
.geo-layer {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.geo-layer--1 { z-index: 1; }
.geo-layer--2 { z-index: 2; }
.geo-layer--3 { z-index: 3; }

/* Individual shapes - recreating the 3D look */
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

/* Gold glimmer effects - behind shapes, casting light on them */
.geo-glimmer {
  position: absolute;
  pointer-events: none;
  z-index: 0;
  filter: blur(8px);
  box-shadow: 0 0 40px rgba(224, 160, 48, 0.4), 0 0 80px rgba(224, 160, 48, 0.2);
}

.geo-glimmer--1 {
  width: 300px;
  height: 30px;
  top: 38%;
  left: 25%;
  background: radial-gradient(ellipse, 
    rgba(224, 160, 48, 0.6) 0%,
    rgba(224, 160, 48, 0.3) 40%,
    transparent 70%
  );
  transform: rotate(-5deg);
  animation: glimmer-1 8s ease-in-out infinite;
}

.geo-glimmer--2 {
  width: 250px;
  height: 25px;
  top: 52%;
  right: 22%;
  background: radial-gradient(ellipse, 
    rgba(224, 160, 48, 0.5) 0%,
    rgba(224, 160, 48, 0.25) 40%,
    transparent 70%
  );
  transform: rotate(8deg);
  animation: glimmer-2 10s ease-in-out infinite;
  animation-delay: 2s;
}

.geo-glimmer--1 {
  width: 300px;
  height: 30px;
  top: 38%;
  left: 25%;
  background: radial-gradient(ellipse, 
    rgba(224, 160, 48, 0.6) 0%,
    rgba(224, 160, 48, 0.3) 40%,
    transparent 70%
  );
  transform: rotate(-5deg);
  animation: glimmer-1 8s ease-in-out infinite;
}

.geo-glimmer--2 {
  width: 250px;
  height: 25px;
  top: 52%;
  right: 22%;
  background: radial-gradient(ellipse, 
    rgba(224, 160, 48, 0.5) 0%,
    rgba(224, 160, 48, 0.25) 40%,
    transparent 70%
  );
  transform: rotate(8deg);
  animation: glimmer-2 10s ease-in-out infinite;
  animation-delay: 2s;
}

.geo-glimmer--3 {
  width: 200px;
  height: 20px;
  bottom: 30%;
  left: 15%;
  background: radial-gradient(ellipse, 
    rgba(224, 160, 48, 0.55) 0%,
    rgba(224, 160, 48, 0.28) 40%,
    transparent 70%
  );
  transform: rotate(-12deg);
  animation: glimmer-3 6s ease-in-out infinite;
  animation-delay: 4s;
}

@keyframes glimmer-1 {
  0%, 20%, 100% { opacity: 0; transform: rotate(-5deg) translateX(-20px); }
  40%, 60% { opacity: 1; transform: rotate(-5deg) translateX(0); }
  80% { opacity: 0; transform: rotate(-5deg) translateX(20px); }
}

@keyframes glimmer-2 {
  0%, 30%, 100% { opacity: 0; transform: rotate(8deg) scaleX(0.8); }
  50%, 70% { opacity: 1; transform: rotate(8deg) scaleX(1); }
}

@keyframes glimmer-3 {
  0%, 100% { opacity: 0; }
  40%, 60% { opacity: 0.8; }
}

/* Ambient glow */
.geo-ambient {
  position: absolute;
  inset: 0;
  background: radial-gradient(ellipse at 40% 40%, rgba(224, 160, 48, 0.03) 0%, transparent 50%);
  animation: ambient-shift 15s ease-in-out infinite;
  z-index: 4;
}

@keyframes ambient-shift {
  0%, 100% { 
    background: radial-gradient(ellipse at 40% 40%, rgba(224, 160, 48, 0.03) 0%, transparent 50%);
  }
  50% { 
    background: radial-gradient(ellipse at 60% 60%, rgba(224, 160, 48, 0.05) 0%, transparent 50%);
  }
}

/* ═══════════════════════════════════════════
   PROPOSAL 3: COMBINED
   Many smaller solid shapes with gold glow behind
   ═══════════════════════════════════════════ */
.combined {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #0a0a0c;
  overflow: hidden;
}

.combined__geo {
  position: absolute;
  inset: 0;
  overflow: hidden;
}

.combined__split {
  position: relative;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 3rem;
  width: 100%;
  max-width: 900px;
  padding: 2rem;
}

.combined__side {
  flex: 1;
  display: flex;
  justify-content: center;
  cursor: pointer;
}

.combined__card {
  padding: 2.5rem 3rem;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 20px;
  text-align: center;
  transition: all 0.4s ease;
}

.combined__side:hover .combined__card {
  transform: translateY(-8px);
  box-shadow: 0 30px 60px rgba(0, 0, 0, 0.4);
}

.combined__side--left:hover .combined__card {
  border-color: rgba(212, 90, 90, 0.3);
  box-shadow: 0 30px 60px rgba(0, 0, 0, 0.4), 0 0 40px rgba(212, 90, 90, 0.1);
}

.combined__side--right:hover .combined__card {
  border-color: rgba(124, 58, 237, 0.3);
  box-shadow: 0 30px 60px rgba(0, 0, 0, 0.4), 0 0 40px rgba(124, 58, 237, 0.1);
}

.combined__icon {
  width: 80px;
  height: 80px;
  margin: 0 auto 1rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
}

.combined__icon svg {
  width: 36px;
  height: 36px;
}

.combined__icon--recorder {
  background: rgba(212, 90, 90, 0.15);
  color: #d45a5a;
}

.combined__side:hover .combined__icon--recorder {
  background: rgba(212, 90, 90, 0.25);
  box-shadow: 0 0 30px rgba(212, 90, 90, 0.3);
}

.combined__icon--mixer {
  background: rgba(124, 58, 237, 0.15);
  color: #a78bfa;
}

.combined__side:hover .combined__icon--mixer {
  background: rgba(124, 58, 237, 0.25);
  box-shadow: 0 0 30px rgba(124, 58, 237, 0.3);
}

.combined__card h3 {
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--preke-text);
  margin-bottom: 0.25rem;
}

.combined__card p {
  font-size: 0.875rem;
  color: var(--preke-text-muted);
}

.combined__center {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  z-index: 5;
}

.combined__logo {
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

/* ═══════════════════════════════════════════
   PROPOSAL 4: COMPLEX RIBBONS
   Inspired by stock image - many intersecting
   diagonal ribbons with 3D layered effect
   ═══════════════════════════════════════════ */
.ribbons {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #08080a;
}

.ribbons__canvas {
  position: absolute;
  inset: -20%;
  overflow: hidden;
}

/* Base ribbon style - long diagonal strips */
.ribbon {
  position: absolute;
  transform-origin: center;
}

/* Layer 1: Back ribbons - horizontal, centered, minimal rotation */
.ribbon--1 {
  width: 140%;
  height: 50px;
  top: 28%;
  left: -20%;
  background: linear-gradient(135deg, #0e0e10 0%, #0a0a0c 100%);
  transform: rotate(-4deg);
  animation: ribbon-glow 14s ease-in-out infinite;
}

.ribbon--2 {
  width: 150%;
  height: 45px;
  top: 36%;
  left: -25%;
  background: linear-gradient(135deg, #0f0f11 0%, #0b0b0d 100%);
  transform: rotate(3deg);
  animation: ribbon-glow 16s ease-in-out infinite;
  animation-delay: 1s;
}

.ribbon--3 {
  width: 145%;
  height: 55px;
  top: 44%;
  left: -22%;
  background: linear-gradient(135deg, #0d0d0f 0%, #090909 100%);
  transform: rotate(-5deg);
  animation: ribbon-glow 12s ease-in-out infinite;
  animation-delay: 2s;
}

.ribbon--4 {
  width: 155%;
  height: 48px;
  top: 52%;
  left: -27%;
  background: linear-gradient(135deg, #0e0e10 0%, #0a0a0c 100%);
  transform: rotate(4deg);
  animation: ribbon-glow 15s ease-in-out infinite;
  animation-delay: 0.5s;
}

.ribbon--5 {
  width: 140%;
  height: 42px;
  top: 60%;
  left: -20%;
  background: linear-gradient(135deg, #0c0c0e 0%, #080808 100%);
  transform: rotate(-3deg);
  animation: ribbon-glow 13s ease-in-out infinite;
  animation-delay: 3s;
}

.ribbon--6 {
  width: 135%;
  height: 38px;
  top: 68%;
  left: -17%;
  background: linear-gradient(135deg, #0d0d0f 0%, #090909 100%);
  transform: rotate(5deg);
  animation: ribbon-glow 11s ease-in-out infinite;
  animation-delay: 1.5s;
}

/* Layer 2: Mid ribbons - slightly more visible, centered */
.ribbon--7 {
  width: 145%;
  height: 65px;
  top: 32%;
  left: -22%;
  background: linear-gradient(135deg, #121214 0%, #0d0d0f 100%);
  transform: rotate(-6deg);
  box-shadow: 0 5px 30px rgba(0, 0, 0, 0.5);
  animation: ribbon-glow 10s ease-in-out infinite;
}

.ribbon--8 {
  width: 150%;
  height: 55px;
  top: 42%;
  left: -25%;
  background: linear-gradient(135deg, #141416 0%, #0f0f11 100%);
  transform: rotate(5deg);
  box-shadow: 0 5px 30px rgba(0, 0, 0, 0.5);
  animation: ribbon-glow 12s ease-in-out infinite;
  animation-delay: 2s;
}

.ribbon--9 {
  width: 140%;
  height: 52px;
  top: 52%;
  left: -20%;
  background: linear-gradient(135deg, #131315 0%, #0e0e10 100%);
  transform: rotate(-4deg);
  box-shadow: 0 5px 30px rgba(0, 0, 0, 0.5);
  animation: ribbon-glow 14s ease-in-out infinite;
  animation-delay: 1s;
}

.ribbon--10 {
  width: 135%;
  height: 48px;
  top: 62%;
  left: -17%;
  background: linear-gradient(135deg, #121214 0%, #0c0c0e 100%);
  transform: rotate(6deg);
  box-shadow: 0 5px 30px rgba(0, 0, 0, 0.5);
  animation: ribbon-glow 11s ease-in-out infinite;
  animation-delay: 3s;
}

.ribbon--11 {
  width: 130%;
  height: 44px;
  top: 25%;
  left: -15%;
  background: linear-gradient(135deg, #101012 0%, #0b0b0d 100%);
  transform: rotate(-3deg);
  box-shadow: 0 3px 20px rgba(0, 0, 0, 0.4);
  animation: ribbon-glow 13s ease-in-out infinite;
  animation-delay: 0.5s;
}

.ribbon--12 {
  width: 125%;
  height: 40px;
  top: 70%;
  left: -12%;
  background: linear-gradient(135deg, #111113 0%, #0c0c0e 100%);
  transform: rotate(4deg);
  box-shadow: 0 3px 20px rgba(0, 0, 0, 0.4);
  animation: ribbon-glow 15s ease-in-out infinite;
  animation-delay: 2.5s;
}

/* Layer 3: Front ribbons - most visible, gold edges, centered */
.ribbon--13 {
  width: 140%;
  height: 75px;
  top: 38%;
  left: -20%;
  background: linear-gradient(135deg, #1a1a1c 0%, #141416 100%);
  transform: rotate(-5deg);
  box-shadow: 
    inset 0 1px 0 rgba(224, 160, 48, 0.1),
    0 8px 40px rgba(0, 0, 0, 0.6);
  animation: ribbon-glow-front 8s ease-in-out infinite;
}

.ribbon--14 {
  width: 135%;
  height: 68px;
  top: 48%;
  left: -17%;
  background: linear-gradient(135deg, #1c1c1e 0%, #161618 100%);
  transform: rotate(4deg);
  box-shadow: 
    inset 0 1px 0 rgba(224, 160, 48, 0.12),
    0 8px 40px rgba(0, 0, 0, 0.6);
  animation: ribbon-glow-front 10s ease-in-out infinite;
  animation-delay: 1s;
}

.ribbon--15 {
  width: 130%;
  height: 60px;
  top: 56%;
  left: -15%;
  background: linear-gradient(135deg, #1b1b1d 0%, #151517 100%);
  transform: rotate(-6deg);
  box-shadow: 
    inset 0 1px 0 rgba(224, 160, 48, 0.14),
    0 8px 40px rgba(0, 0, 0, 0.6);
  animation: ribbon-glow-front 9s ease-in-out infinite;
  animation-delay: 0.5s;
}

.ribbon--16 {
  width: 125%;
  height: 55px;
  top: 64%;
  left: -12%;
  background: linear-gradient(135deg, #1d1d1f 0%, #171719 100%);
  transform: rotate(5deg);
  box-shadow: 
    inset 0 1px 0 rgba(224, 160, 48, 0.16),
    0 8px 40px rgba(0, 0, 0, 0.6);
  animation: ribbon-glow-front 11s ease-in-out infinite;
  animation-delay: 1.5s;
}

/* Ribbon subtle glow animations - no movement, just opacity */
@keyframes ribbon-glow {
  0%, 100% { opacity: 0.85; }
  50% { opacity: 0.95; }
}

@keyframes ribbon-glow-front {
  0%, 100% { opacity: 0.92; }
  50% { opacity: 1; }
}

/* Gold glimmers - thin lines that catch light */
.ribbon-glimmer {
  position: absolute;
  height: 2px;
  pointer-events: none;
  z-index: 10;
}

.glimmer--1 {
  width: 250px;
  top: 32%;
  left: 20%;
  background: linear-gradient(90deg, 
    transparent 0%, 
    rgba(224, 160, 48, 0.3) 20%,
    rgba(224, 160, 48, 0.7) 50%,
    rgba(224, 160, 48, 0.3) 80%,
    transparent 100%
  );
  transform: rotate(-18deg);
  animation: glimmer-pulse 6s ease-in-out infinite;
  filter: blur(0.5px);
}

.glimmer--2 {
  width: 200px;
  top: 47%;
  right: 25%;
  background: linear-gradient(90deg, 
    transparent 0%, 
    rgba(224, 160, 48, 0.4) 30%,
    rgba(224, 160, 48, 0.6) 50%,
    rgba(224, 160, 48, 0.4) 70%,
    transparent 100%
  );
  transform: rotate(22deg);
  animation: glimmer-pulse 8s ease-in-out infinite;
  animation-delay: 2s;
  filter: blur(0.5px);
}

.glimmer--3 {
  width: 180px;
  bottom: 38%;
  left: 30%;
  background: linear-gradient(90deg, 
    transparent 0%, 
    rgba(224, 160, 48, 0.5) 50%,
    transparent 100%
  );
  transform: rotate(-25deg);
  animation: glimmer-pulse 5s ease-in-out infinite;
  animation-delay: 4s;
  filter: blur(0.5px);
}

.glimmer--4 {
  width: 160px;
  bottom: 28%;
  right: 20%;
  background: linear-gradient(90deg, 
    transparent 0%, 
    rgba(224, 160, 48, 0.4) 50%,
    transparent 100%
  );
  transform: rotate(18deg);
  animation: glimmer-pulse 7s ease-in-out infinite;
  animation-delay: 1s;
  filter: blur(0.5px);
}

.glimmer--5 {
  width: 140px;
  top: 55%;
  left: 45%;
  background: linear-gradient(90deg, 
    transparent 0%, 
    rgba(224, 160, 48, 0.6) 50%,
    transparent 100%
  );
  transform: rotate(-10deg);
  animation: glimmer-pulse 9s ease-in-out infinite;
  animation-delay: 3s;
  filter: blur(0.5px);
}

@keyframes glimmer-pulse {
  0%, 20%, 100% { opacity: 0; }
  40%, 60% { opacity: 0.8; }
  80% { opacity: 0; }
}

/* Central ambient glow */
.ribbons__ambient {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 60%;
  height: 60%;
  transform: translate(-50%, -50%);
  background: radial-gradient(ellipse, rgba(224, 160, 48, 0.04) 0%, transparent 60%);
  animation: ambient-pulse 10s ease-in-out infinite;
  pointer-events: none;
}

@keyframes ambient-pulse {
  0%, 100% { opacity: 0.8; transform: translate(-50%, -50%) scale(1); }
  50% { opacity: 1; transform: translate(-50%, -50%) scale(1.1); }
}

/* Content overlay - same as combined but on ribbons */
.ribbons__content {
  position: relative;
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 3rem;
  width: 100%;
  max-width: 900px;
  padding: 2rem;
}

.ribbons__side {
  flex: 1;
  display: flex;
  justify-content: center;
  cursor: pointer;
}

.ribbons__card {
  padding: 2.5rem 3rem;
  background: rgba(10, 10, 12, 0.7);
  backdrop-filter: blur(24px);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 20px;
  text-align: center;
  transition: all 0.4s ease;
}

.ribbons__side:hover .ribbons__card {
  transform: translateY(-8px);
  background: rgba(10, 10, 12, 0.85);
  box-shadow: 0 30px 60px rgba(0, 0, 0, 0.5);
}

.ribbons__side--left:hover .ribbons__card {
  border-color: rgba(212, 90, 90, 0.3);
  box-shadow: 0 30px 60px rgba(0, 0, 0, 0.5), 0 0 40px rgba(212, 90, 90, 0.1);
}

.ribbons__side--right:hover .ribbons__card {
  border-color: rgba(124, 58, 237, 0.3);
  box-shadow: 0 30px 60px rgba(0, 0, 0, 0.5), 0 0 40px rgba(124, 58, 237, 0.1);
}

.ribbons__icon {
  width: 80px;
  height: 80px;
  margin: 0 auto 1rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
}

.ribbons__icon svg {
  width: 36px;
  height: 36px;
}

.ribbons__icon--recorder {
  background: rgba(212, 90, 90, 0.15);
  color: #d45a5a;
}

.ribbons__side:hover .ribbons__icon--recorder {
  background: rgba(212, 90, 90, 0.25);
  box-shadow: 0 0 30px rgba(212, 90, 90, 0.3);
}

.ribbons__icon--mixer {
  background: rgba(124, 58, 237, 0.15);
  color: #a78bfa;
}

.ribbons__side:hover .ribbons__icon--mixer {
  background: rgba(124, 58, 237, 0.25);
  box-shadow: 0 0 30px rgba(124, 58, 237, 0.3);
}

.ribbons__card h3 {
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--preke-text);
  margin-bottom: 0.25rem;
}

.ribbons__card p {
  font-size: 0.875rem;
  color: var(--preke-text-muted);
}

.ribbons__center {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  z-index: 5;
}

.ribbons__logo {
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--preke-gold);
  text-transform: uppercase;
  letter-spacing: 0.2em;
  background: rgba(8, 8, 10, 0.9);
  padding: 0.5rem 1rem;
  border-radius: 100px;
  border: 1px solid rgba(224, 160, 48, 0.2);
}

/* ═══════════════════════════════════════════
   PROPOSAL 5: STOCK IMAGE
   Photo background with moving light behind
   and dark overlay on top
   ═══════════════════════════════════════════ */
.stock-image {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #0a0a0c;
  overflow: hidden;
}

/* Moving light effect behind the image - soft and smooth */
.stock-image__light {
  position: absolute;
  inset: -30%;
  background: radial-gradient(ellipse at 50% 50%, 
    rgba(224, 160, 48, 0.25) 0%, 
    rgba(224, 160, 48, 0.08) 40%, 
    transparent 70%
  );
  filter: blur(40px);
  animation: stock-light-move 25s ease-in-out infinite;
  z-index: 1;
}

@keyframes stock-light-move {
  0%, 100% { 
    transform: translate(-15%, -10%) scale(1);
    opacity: 0.8;
  }
  50% { 
    transform: translate(15%, 10%) scale(1.1);
    opacity: 1;
  }
}

/* The stock image - with increased contrast */
.stock-image__photo {
  position: absolute;
  inset: -5%;
  background-image: url('@/assets/stock-background.jpeg');
  background-size: cover;
  background-position: center;
  opacity: 0.35;
  filter: contrast(1.5) saturate(0.7);
  z-index: 2;
}

/* Dark overlay on top of the image - lighter */
.stock-image__overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    180deg,
    rgba(5, 5, 7, 0.6) 0%,
    rgba(5, 5, 7, 0.35) 30%,
    rgba(5, 5, 7, 0.35) 70%,
    rgba(5, 5, 7, 0.7) 100%
  );
  z-index: 3;
}

/* Content layer */
.stock-image__content {
  position: relative;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 3rem;
  width: 100%;
  max-width: 900px;
  padding: 2rem;
}

.stock-image__side {
  flex: 1;
  display: flex;
  justify-content: center;
  cursor: pointer;
}

.stock-image__card {
  padding: 2.5rem 3rem;
  background: rgba(255, 255, 255, 0.03);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 20px;
  text-align: center;
  transition: all 0.4s ease;
}

.stock-image__side:hover .stock-image__card {
  transform: translateY(-8px);
  box-shadow: 0 30px 60px rgba(0, 0, 0, 0.4);
}

.stock-image__side--left:hover .stock-image__card {
  border-color: rgba(212, 90, 90, 0.3);
  box-shadow: 0 30px 60px rgba(0, 0, 0, 0.4), 0 0 40px rgba(212, 90, 90, 0.1);
}

.stock-image__side--right:hover .stock-image__card {
  border-color: rgba(124, 58, 237, 0.3);
  box-shadow: 0 30px 60px rgba(0, 0, 0, 0.4), 0 0 40px rgba(124, 58, 237, 0.1);
}

.stock-image__icon {
  width: 80px;
  height: 80px;
  margin: 0 auto 1rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
}

.stock-image__icon svg {
  width: 36px;
  height: 36px;
}

.stock-image__icon--recorder {
  background: rgba(212, 90, 90, 0.15);
  color: #d45a5a;
}

.stock-image__side:hover .stock-image__icon--recorder {
  background: rgba(212, 90, 90, 0.25);
  box-shadow: 0 0 30px rgba(212, 90, 90, 0.3);
}

.stock-image__icon--mixer {
  background: rgba(124, 58, 237, 0.15);
  color: #a78bfa;
}

.stock-image__side:hover .stock-image__icon--mixer {
  background: rgba(124, 58, 237, 0.25);
  box-shadow: 0 0 30px rgba(124, 58, 237, 0.3);
}

.stock-image__card h3 {
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--preke-text);
  margin-bottom: 0.25rem;
}

.stock-image__card p {
  font-size: 0.875rem;
  color: var(--preke-text-muted);
}

.stock-image__center {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  z-index: 5;
}

.stock-image__logo {
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--preke-gold);
  text-transform: uppercase;
  letter-spacing: 0.2em;
  background: rgba(10, 10, 12, 0.9);
  padding: 0.5rem 1rem;
  border-radius: 100px;
  border: 1px solid rgba(224, 160, 48, 0.2);
}

/* ═══════════════════════════════════════════
   PROPOSAL 6: CYBERPUNK
   Neon circuits with glowing orange edges
   ═══════════════════════════════════════════ */
.cyberpunk {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #050507;
  overflow: hidden;
}

/* Circuit pattern background */
.cyber__circuits {
  position: absolute;
  inset: 0;
  background: 
    /* Horizontal lines */
    repeating-linear-gradient(
      0deg,
      transparent,
      transparent 40px,
      rgba(255, 100, 50, 0.03) 40px,
      rgba(255, 100, 50, 0.03) 41px
    ),
    /* Vertical lines */
    repeating-linear-gradient(
      90deg,
      transparent,
      transparent 60px,
      rgba(255, 100, 50, 0.02) 60px,
      rgba(255, 100, 50, 0.02) 61px
    ),
    /* Diagonal accent */
    repeating-linear-gradient(
      -45deg,
      transparent,
      transparent 80px,
      rgba(255, 80, 30, 0.015) 80px,
      rgba(255, 80, 30, 0.015) 81px
    );
  opacity: 0.8;
}

/* Glowing neon lines */
.cyber__neon {
  position: absolute;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(255, 100, 40, 0.8) 20%,
    rgba(255, 140, 60, 1) 50%,
    rgba(255, 100, 40, 0.8) 80%,
    transparent 100%
  );
  filter: blur(1px);
  box-shadow: 
    0 0 10px rgba(255, 100, 40, 0.6),
    0 0 20px rgba(255, 80, 30, 0.4),
    0 0 40px rgba(255, 60, 20, 0.2);
  z-index: 2;
}

.cyber__neon--1 {
  width: 200px;
  height: 3px;
  top: 25%;
  left: 10%;
  transform: rotate(-15deg);
  animation: neon-pulse 4s ease-in-out infinite;
}

.cyber__neon--2 {
  width: 150px;
  height: 2px;
  top: 40%;
  right: 15%;
  transform: rotate(20deg);
  animation: neon-pulse 5s ease-in-out infinite;
  animation-delay: 1s;
}

.cyber__neon--3 {
  width: 180px;
  height: 3px;
  bottom: 35%;
  left: 20%;
  transform: rotate(-8deg);
  animation: neon-pulse 3.5s ease-in-out infinite;
  animation-delay: 0.5s;
}

.cyber__neon--4 {
  width: 120px;
  height: 2px;
  bottom: 25%;
  right: 25%;
  transform: rotate(12deg);
  animation: neon-pulse 4.5s ease-in-out infinite;
  animation-delay: 2s;
}

.cyber__neon--5 {
  width: 100px;
  height: 2px;
  top: 60%;
  left: 40%;
  transform: rotate(-25deg);
  animation: neon-pulse 6s ease-in-out infinite;
  animation-delay: 1.5s;
}

@keyframes neon-pulse {
  0%, 100% { opacity: 0.4; filter: blur(1px); }
  50% { opacity: 1; filter: blur(0.5px); }
}

/* Floating sparks */
.cyber__sparks {
  position: absolute;
  inset: 0;
  z-index: 3;
  pointer-events: none;
}

.cyber__spark {
  position: absolute;
  width: 3px;
  height: 3px;
  background: rgba(255, 120, 50, 0.9);
  border-radius: 50%;
  box-shadow: 
    0 0 6px rgba(255, 100, 40, 0.8),
    0 0 12px rgba(255, 80, 30, 0.5);
  animation: spark-float 8s linear infinite;
}

.cyber__spark--1 { left: 15%; animation-delay: 0s; }
.cyber__spark--2 { left: 30%; animation-delay: 1s; }
.cyber__spark--3 { left: 45%; animation-delay: 2s; }
.cyber__spark--4 { left: 60%; animation-delay: 0.5s; }
.cyber__spark--5 { left: 75%; animation-delay: 1.5s; }
.cyber__spark--6 { left: 85%; animation-delay: 2.5s; }
.cyber__spark--7 { left: 25%; animation-delay: 3s; }
.cyber__spark--8 { left: 55%; animation-delay: 3.5s; }

@keyframes spark-float {
  0% { 
    bottom: -5%; 
    opacity: 0;
    transform: translateX(0) scale(0.5);
  }
  10% { opacity: 1; transform: scale(1); }
  90% { opacity: 1; }
  100% { 
    bottom: 105%; 
    opacity: 0;
    transform: translateX(20px) scale(0.3);
  }
}

/* Ambient glow */
.cyber__glow {
  position: absolute;
  inset: 0;
  background: radial-gradient(
    ellipse at 30% 40%,
    rgba(255, 80, 30, 0.15) 0%,
    transparent 50%
  ),
  radial-gradient(
    ellipse at 70% 60%,
    rgba(255, 100, 40, 0.1) 0%,
    transparent 40%
  );
  animation: glow-shift 12s ease-in-out infinite;
  z-index: 1;
}

@keyframes glow-shift {
  0%, 100% {
    background: radial-gradient(
      ellipse at 30% 40%,
      rgba(255, 80, 30, 0.15) 0%,
      transparent 50%
    ),
    radial-gradient(
      ellipse at 70% 60%,
      rgba(255, 100, 40, 0.1) 0%,
      transparent 40%
    );
  }
  50% {
    background: radial-gradient(
      ellipse at 60% 30%,
      rgba(255, 80, 30, 0.12) 0%,
      transparent 50%
    ),
    radial-gradient(
      ellipse at 40% 70%,
      rgba(255, 100, 40, 0.15) 0%,
      transparent 40%
    );
  }
}

/* Content layer */
.cyber__content {
  position: relative;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 3rem;
  width: 100%;
  max-width: 900px;
  padding: 2rem;
}

.cyber__side {
  flex: 1;
  display: flex;
  justify-content: center;
  cursor: pointer;
}

.cyber__card {
  padding: 2.5rem 3rem;
  background: rgba(255, 100, 40, 0.03);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 100, 40, 0.15);
  border-radius: 4px;
  text-align: center;
  transition: all 0.4s ease;
  position: relative;
}

/* Neon corner accents */
.cyber__card::before,
.cyber__card::after {
  content: '';
  position: absolute;
  width: 20px;
  height: 20px;
  border-color: rgba(255, 100, 40, 0.5);
  border-style: solid;
  border-width: 0;
  transition: all 0.3s ease;
}

.cyber__card::before {
  top: -1px;
  left: -1px;
  border-top-width: 2px;
  border-left-width: 2px;
}

.cyber__card::after {
  bottom: -1px;
  right: -1px;
  border-bottom-width: 2px;
  border-right-width: 2px;
}

.cyber__side:hover .cyber__card {
  transform: translateY(-8px);
  background: rgba(255, 100, 40, 0.06);
  box-shadow: 
    0 30px 60px rgba(0, 0, 0, 0.4),
    0 0 30px rgba(255, 80, 30, 0.1);
}

.cyber__side:hover .cyber__card::before,
.cyber__side:hover .cyber__card::after {
  width: 30px;
  height: 30px;
  border-color: rgba(255, 100, 40, 0.8);
}

.cyber__side--left:hover .cyber__card {
  border-color: rgba(212, 90, 90, 0.4);
}

.cyber__side--right:hover .cyber__card {
  border-color: rgba(124, 58, 237, 0.4);
}

.cyber__icon {
  width: 80px;
  height: 80px;
  margin: 0 auto 1rem;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
  position: relative;
}

.cyber__icon svg {
  width: 36px;
  height: 36px;
}

.cyber__icon--recorder {
  background: rgba(212, 90, 90, 0.15);
  color: #d45a5a;
  border: 1px solid rgba(212, 90, 90, 0.2);
}

.cyber__side:hover .cyber__icon--recorder {
  background: rgba(212, 90, 90, 0.25);
  box-shadow: 
    0 0 20px rgba(212, 90, 90, 0.3),
    inset 0 0 20px rgba(212, 90, 90, 0.1);
}

.cyber__icon--mixer {
  background: rgba(124, 58, 237, 0.15);
  color: #a78bfa;
  border: 1px solid rgba(124, 58, 237, 0.2);
}

.cyber__side:hover .cyber__icon--mixer {
  background: rgba(124, 58, 237, 0.25);
  box-shadow: 
    0 0 20px rgba(124, 58, 237, 0.3),
    inset 0 0 20px rgba(124, 58, 237, 0.1);
}

.cyber__card h3 {
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--preke-text);
  margin-bottom: 0.25rem;
  text-shadow: 0 0 20px rgba(255, 100, 40, 0.3);
}

.cyber__card p {
  font-size: 0.875rem;
  color: var(--preke-text-muted);
}

.cyber__center {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  z-index: 5;
}

.cyber__logo {
  font-size: 0.75rem;
  font-weight: 700;
  color: #ff7030;
  text-transform: uppercase;
  letter-spacing: 0.2em;
  background: rgba(5, 5, 7, 0.95);
  padding: 0.5rem 1rem;
  border-radius: 2px;
  border: 1px solid rgba(255, 100, 40, 0.3);
  text-shadow: 0 0 10px rgba(255, 100, 40, 0.5);
  box-shadow: 
    0 0 20px rgba(255, 80, 30, 0.15),
    inset 0 0 10px rgba(255, 100, 40, 0.05);
}
/* ═══════════════════════════════════════════
   EXPERIMENT STYLES (Drafts 7-11)
   ═══════════════════════════════════════════ */
.exp {
  flex: 1;
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.exp__layer {
  position: absolute;
  inset: 0;
}

.exp__img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  filter: invert(1) brightness(0.12) contrast(1.3);
}

.exp__overlay {
  position: absolute;
  inset: 0;
}

.exp__overlay--dark {
  background: rgba(10, 10, 15, 0.75);
}

.exp__content {
  position: relative;
  z-index: 10;
  text-align: center;
  padding: 2rem;
}

.exp__heading {
  font-size: 2.5rem;
  font-weight: 700;
  color: var(--preke-text);
  margin-bottom: 1rem;
}

.exp__heading--tron {
  color: #00d4ff;
  text-shadow: 0 0 20px rgba(0, 212, 255, 0.5), 0 0 40px rgba(0, 212, 255, 0.3);
}

.exp__heading--gold {
  color: var(--preke-gold);
  text-shadow: 0 0 20px rgba(224, 160, 48, 0.5);
}

.exp__heading--holo {
  color: #00ffcc;
  text-shadow: 
    0 0 20px rgba(0, 255, 204, 0.5),
    2px 0 rgba(255, 0, 128, 0.3),
    -2px 0 rgba(0, 255, 255, 0.3);
}

.exp__heading--purple {
  color: #a78bfa;
  text-shadow: 0 0 20px rgba(167, 139, 250, 0.5);
}

.exp__desc {
  font-size: 1rem;
  color: var(--preke-text-muted);
  max-width: 500px;
  line-height: 1.6;
  margin: 0 auto;
}

/* DRAFT 7: BREATHING TECH */
.exp__img--breathe {
  animation: img-breathe 8s ease-in-out infinite;
  transform-origin: center center;
}

@keyframes img-breathe {
  0%, 100% {
    transform: scale(1);
    filter: invert(1) brightness(0.12) contrast(1.3);
  }
  50% {
    transform: scale(1.03);
    filter: invert(1) brightness(0.15) contrast(1.35);
  }
}

.exp__pulse--center {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 300px;
  height: 300px;
  transform: translate(-50%, -50%);
  background: radial-gradient(circle, rgba(224, 160, 48, 0.15) 0%, transparent 70%);
  border-radius: 50%;
  animation: pulse-breathe 6s ease-in-out infinite;
}

@keyframes pulse-breathe {
  0%, 100% {
    transform: translate(-50%, -50%) scale(1);
    opacity: 0.3;
  }
  50% {
    transform: translate(-50%, -50%) scale(1.3);
    opacity: 0.6;
  }
}

/* DRAFT 8: TRON GRID */
.exp__hex-grid {
  position: absolute;
  inset: 0;
  opacity: 0.04;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='28' height='49' viewBox='0 0 28 49'%3E%3Cg fill-rule='evenodd'%3E%3Cg fill='%2300d4ff' fill-opacity='1'%3E%3Cpath d='M13.99 9.25l13 7.5v15l-13 7.5L1 31.75v-15l12.99-7.5zM3 17.9v12.7l10.99 6.34 11-6.35V17.9l-11-6.34L3 17.9zM0 15l12.98-7.5V0h-2v6.35L0 12.69v2.3zm0 18.5L12.98 41v8h-2v-6.85L0 35.81v-2.3zM15 0v7.5L27.99 15H28v-2.31h-.01L17 6.35V0h-2zm0 49v-8l12.99-7.5H28v2.31h-.01L17 42.15V49h-2z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
  animation: grid-pulse 4s ease-in-out infinite;
}

@keyframes grid-pulse {
  0%, 100% { opacity: 0.03; }
  50% { opacity: 0.06; }
}

.exp__scan-line {
  position: absolute;
  pointer-events: none;
}

.exp__scan-line--h {
  width: 100%;
  height: 2px;
  left: 0;
  top: -2px;
  background: linear-gradient(90deg, transparent, rgba(0, 212, 255, 0.8), transparent);
  box-shadow: 0 0 20px rgba(0, 212, 255, 0.5), 0 0 40px rgba(0, 212, 255, 0.3);
  animation: scan-down 6s linear infinite;
}

.exp__scan-line--v {
  width: 2px;
  height: 100%;
  left: -2px;
  top: 0;
  background: linear-gradient(180deg, transparent, rgba(0, 212, 255, 0.6), transparent);
  box-shadow: 0 0 20px rgba(0, 212, 255, 0.4), 0 0 40px rgba(0, 212, 255, 0.2);
  animation: scan-right 8s linear infinite;
  animation-delay: 3s;
}

@keyframes scan-down {
  0% { top: -2px; opacity: 0; }
  5% { opacity: 1; }
  95% { opacity: 1; }
  100% { top: 100%; opacity: 0; }
}

@keyframes scan-right {
  0% { left: -2px; opacity: 0; }
  5% { opacity: 1; }
  95% { opacity: 1; }
  100% { left: 100%; opacity: 0; }
}

/* DRAFT 9: CIRCUIT FLOW */
.exp__overlay--circuit {
  background: linear-gradient(135deg, rgba(10, 10, 15, 0.85) 0%, rgba(20, 15, 10, 0.8) 100%);
}

.circuit {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.circuit__line {
  position: absolute;
  height: 1px;
  background: rgba(224, 160, 48, 0.2);
  overflow: hidden;
}

.circuit__line--1 {
  top: 30%;
  left: 10%;
  width: 35%;
  transform: rotate(-5deg);
}

.circuit__line--2 {
  top: 50%;
  left: 50%;
  width: 40%;
  transform: rotate(3deg);
}

.circuit__line--3 {
  top: 70%;
  left: 20%;
  width: 30%;
  transform: rotate(-2deg);
}

.circuit__particle {
  position: absolute;
  top: -2px;
  left: 0;
  width: 20px;
  height: 5px;
  background: linear-gradient(90deg, transparent, var(--preke-gold), transparent);
  border-radius: 50%;
  box-shadow: 0 0 10px var(--preke-gold), 0 0 20px rgba(224, 160, 48, 0.5);
  animation: particle-flow 3s linear infinite;
}

.circuit__line--2 .circuit__particle {
  animation-delay: 1s;
  animation-duration: 4s;
}

.circuit__line--3 .circuit__particle {
  animation-delay: 2s;
  animation-duration: 3.5s;
}

@keyframes particle-flow {
  0% { left: -20px; opacity: 0; }
  10% { opacity: 1; }
  90% { opacity: 1; }
  100% { left: 100%; opacity: 0; }
}

.circuit__node {
  position: absolute;
  width: 8px;
  height: 8px;
  background: var(--preke-gold);
  border-radius: 50%;
  box-shadow: 0 0 15px var(--preke-gold), 0 0 30px rgba(224, 160, 48, 0.4);
  animation: node-glow 2s ease-in-out infinite;
}

.circuit__node--1 { top: 30%; left: 45%; }
.circuit__node--2 { top: 50%; left: 90%; animation-delay: 0.5s; }
.circuit__node--3 { top: 70%; left: 50%; animation-delay: 1s; }

@keyframes node-glow {
  0%, 100% {
    transform: scale(1);
    box-shadow: 0 0 15px var(--preke-gold), 0 0 30px rgba(224, 160, 48, 0.4);
  }
  50% {
    transform: scale(1.3);
    box-shadow: 0 0 25px var(--preke-gold), 0 0 50px rgba(224, 160, 48, 0.6);
  }
}

/* DRAFT 10: HOLOGRAPHIC */
.exp__img--holo {
  filter: invert(1) brightness(0.15) contrast(1.2) hue-rotate(140deg);
  animation: holo-shift 10s ease-in-out infinite;
}

@keyframes holo-shift {
  0%, 100% {
    filter: invert(1) brightness(0.15) contrast(1.2) hue-rotate(140deg);
    transform: scale(1);
  }
  25% {
    filter: invert(1) brightness(0.18) contrast(1.25) hue-rotate(150deg);
  }
  50% {
    filter: invert(1) brightness(0.12) contrast(1.3) hue-rotate(160deg);
    transform: scale(1.01);
  }
  75% {
    filter: invert(1) brightness(0.16) contrast(1.22) hue-rotate(145deg);
  }
}

.exp__overlay--holo {
  background: linear-gradient(180deg, 
    rgba(0, 20, 30, 0.8) 0%, 
    rgba(0, 40, 50, 0.7) 50%,
    rgba(0, 20, 30, 0.8) 100%
  );
}

.exp__scanlines {
  position: absolute;
  inset: 0;
  background: repeating-linear-gradient(
    0deg,
    transparent 0px,
    transparent 2px,
    rgba(0, 0, 0, 0.15) 2px,
    rgba(0, 0, 0, 0.15) 4px
  );
  pointer-events: none;
  animation: scanlines-scroll 0.5s linear infinite;
}

@keyframes scanlines-scroll {
  0% { transform: translateY(0); }
  100% { transform: translateY(4px); }
}

.exp__glitch {
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, 
    transparent 0%, 
    rgba(0, 255, 200, 0.03) 50%, 
    transparent 100%
  );
  animation: glitch-sweep 8s ease-in-out infinite;
}

@keyframes glitch-sweep {
  0%, 90%, 100% { transform: translateX(-100%); opacity: 0; }
  92% { transform: translateX(0); opacity: 1; }
  98% { transform: translateX(100%); opacity: 0; }
}

/* DRAFT 11: NEURAL NETWORK */
.exp__overlay--neural {
  background: radial-gradient(ellipse at center, 
    rgba(15, 10, 25, 0.7) 0%, 
    rgba(10, 5, 20, 0.85) 100%
  );
}

.neural {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.neural__node {
  position: absolute;
  width: 12px;
  height: 12px;
  background: #a78bfa;
  border-radius: 50%;
  box-shadow: 0 0 20px #a78bfa, 0 0 40px rgba(167, 139, 250, 0.4);
  animation: neural-pulse 3s ease-in-out infinite;
}

.neural__node--1 { top: 30%; left: 20%; animation-delay: 0s; }
.neural__node--2 { top: 25%; left: 80%; animation-delay: 0.5s; }
.neural__node--3 { top: 50%; left: 50%; animation-delay: 1s; width: 16px; height: 16px; }
.neural__node--4 { top: 70%; left: 15%; animation-delay: 1.5s; }
.neural__node--5 { top: 75%; left: 85%; animation-delay: 2s; }

@keyframes neural-pulse {
  0%, 100% {
    transform: scale(1);
    box-shadow: 0 0 20px #a78bfa, 0 0 40px rgba(167, 139, 250, 0.4);
  }
  50% {
    transform: scale(1.4);
    box-shadow: 0 0 35px #a78bfa, 0 0 70px rgba(167, 139, 250, 0.6);
  }
}

.neural__connections {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.neural__line {
  stroke: rgba(167, 139, 250, 0.3);
  stroke-width: 0.3;
  animation: line-pulse 3s ease-in-out infinite;
}

.neural__line--delay1 { animation-delay: 0.5s; }
.neural__line--delay2 { animation-delay: 1s; }
.neural__line--delay3 { animation-delay: 1.5s; }

@keyframes line-pulse {
  0%, 100% {
    stroke: rgba(167, 139, 250, 0.2);
    stroke-width: 0.3;
  }
  50% {
    stroke: rgba(167, 139, 250, 0.6);
    stroke-width: 0.5;
  }
}
</style>

