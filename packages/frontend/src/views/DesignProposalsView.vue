<script setup lang="ts">
/**
 * Design Proposals View
 * Test page for exploring new design directions
 * Navigate to /proposals to view these live
 */
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const activeProposal = ref<number>(1)
const proposals = [
  { id: 1, name: 'Split Home', desc: 'Two-mode split design for home' },
  { id: 2, name: 'Geometric 3D', desc: 'Animated 3D geometric shapes' },
  { id: 3, name: 'Combined', desc: 'Split + geometric together' },
  { id: 4, name: 'Ribbons', desc: 'Complex intersecting ribbons' },
]

// Simulated mode selection (for demo)
function selectMode(mode: 'recorder' | 'mixer') {
  console.log('Selected mode:', mode)
  // In real app: router.push(`/${mode}`)
}
</script>

<template>
  <div class="proposals">
    <!-- Navigation -->
    <div class="proposals__nav">
      <h1 class="proposals__title">Design Proposals</h1>
      <div class="proposals__tabs">
        <button 
          v-for="p in proposals" 
          :key="p.id"
          @click="activeProposal = p.id"
          class="proposals__tab"
          :class="{ 'proposals__tab--active': activeProposal === p.id }"
        >
          {{ p.name }}
        </button>
      </div>
    </div>

    <!-- ═══════════════════════════════════════════
         PROPOSAL 1: SPLIT HOME
         ═══════════════════════════════════════════ -->
    <div v-show="activeProposal === 1" class="proposal split-home">
      <!-- Recorder Side (Left) -->
      <div class="split-home__side split-home__side--recorder" @click="selectMode('recorder')">
        <div class="split-home__bg">
          <div class="split-home__glow split-home__glow--red"></div>
          <div class="split-home__grid"></div>
        </div>
        <div class="split-home__content">
          <div class="split-home__icon split-home__icon--recorder">
            <svg viewBox="0 0 24 24" fill="currentColor">
              <circle cx="12" cy="12" r="8"/>
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

      <!-- Divider -->
      <div class="split-home__divider">
        <div class="split-home__divider-line"></div>
        <div class="split-home__divider-logo">
          <span class="split-home__divider-text">Preke</span>
        </div>
        <div class="split-home__divider-line"></div>
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
         PROPOSAL 2: GEOMETRIC 3D
         ═══════════════════════════════════════════ -->
    <div v-show="activeProposal === 2" class="proposal geometric">
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
         PROPOSAL 3: COMBINED
         ═══════════════════════════════════════════ -->
    <div v-show="activeProposal === 3" class="proposal combined">
      <!-- Geometric background -->
      <div class="combined__geo">
        <div class="geo-layer geo-layer--1">
          <div class="geo-shape geo-shape--1"></div>
          <div class="geo-shape geo-shape--2"></div>
          <div class="geo-shape geo-shape--3"></div>
        </div>
        <div class="geo-layer geo-layer--2">
          <div class="geo-shape geo-shape--4"></div>
          <div class="geo-shape geo-shape--5"></div>
        </div>
        <div class="geo-glimmer geo-glimmer--1"></div>
        <div class="geo-glimmer geo-glimmer--2"></div>
      </div>
      
      <!-- Split content overlay -->
      <div class="combined__split">
        <div class="combined__side combined__side--left" @click="selectMode('recorder')">
          <div class="combined__card">
            <div class="combined__icon combined__icon--recorder">
              <svg viewBox="0 0 24 24" fill="currentColor">
                <circle cx="12" cy="12" r="8"/>
              </svg>
            </div>
            <h3>Recorder</h3>
            <p>Multi-cam ISO</p>
          </div>
        </div>
        
        <div class="combined__center">
          <span class="combined__logo">Preke Studio</span>
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
         PROPOSAL 4: COMPLEX RIBBONS
         ═══════════════════════════════════════════ -->
    <div v-show="activeProposal === 4" class="proposal ribbons">
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
              <svg viewBox="0 0 24 24" fill="currentColor">
                <circle cx="12" cy="12" r="8"/>
              </svg>
            </div>
            <h3>Recorder</h3>
            <p>Multi-cam ISO</p>
          </div>
        </div>
        
        <div class="ribbons__center">
          <span class="ribbons__logo">Preke Studio</span>
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
  </div>
</template>

<style scoped>
.proposals {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--preke-bg);
}

.proposals__nav {
  position: relative;
  z-index: 100;
  padding: 1.5rem 2rem;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--preke-border);
}

.proposals__title {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--preke-text);
  margin-bottom: 1rem;
}

.proposals__tabs {
  display: flex;
  gap: 0.5rem;
}

.proposals__tab {
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

.proposals__tab:hover {
  color: var(--preke-text);
  border-color: var(--preke-border-light);
}

.proposals__tab--active {
  color: var(--preke-gold);
  background: rgba(224, 160, 48, 0.1);
  border-color: var(--preke-gold);
}

.proposal {
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
  inset: 0;
  opacity: 0.02;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='28' height='49' viewBox='0 0 28 49'%3E%3Cg fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='1'%3E%3Cpath d='M13.99 9.25l13 7.5v15l-13 7.5L1 31.75v-15l12.99-7.5zM3 17.9v12.7l10.99 6.34 11-6.35V17.9l-11-6.34L3 17.9z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
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
  background: linear-gradient(135deg, #151518 0%, #0d0d0f 100%);
  transform-origin: center;
}

/* Layer 1 shapes (darkest, back) */
.geo-shape--1 {
  width: 60%;
  height: 40%;
  top: 5%;
  left: -10%;
  clip-path: polygon(30% 0%, 100% 0%, 70% 100%, 0% 100%);
  animation: shape-breathe-1 12s ease-in-out infinite;
}

.geo-shape--2 {
  width: 50%;
  height: 35%;
  top: 60%;
  right: -5%;
  clip-path: polygon(0% 20%, 100% 0%, 100% 100%, 20% 80%);
  animation: shape-breathe-2 15s ease-in-out infinite;
}

.geo-shape--3 {
  width: 40%;
  height: 50%;
  bottom: 10%;
  left: 20%;
  clip-path: polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%);
  animation: shape-breathe-3 10s ease-in-out infinite;
}

/* Layer 2 shapes (mid depth) */
.geo-shape--4 {
  width: 45%;
  height: 30%;
  top: 20%;
  right: 10%;
  background: linear-gradient(135deg, #1a1a1e 0%, #101012 100%);
  clip-path: polygon(20% 0%, 100% 10%, 80% 100%, 0% 90%);
  animation: shape-breathe-4 14s ease-in-out infinite;
  box-shadow: 
    inset 0 1px 0 rgba(255, 255, 255, 0.03),
    0 0 60px rgba(0, 0, 0, 0.5);
}

.geo-shape--5 {
  width: 35%;
  height: 45%;
  bottom: 20%;
  left: 5%;
  background: linear-gradient(135deg, #1c1c20 0%, #111113 100%);
  clip-path: polygon(10% 0%, 100% 20%, 90% 100%, 0% 80%);
  animation: shape-breathe-5 11s ease-in-out infinite;
  box-shadow: 
    inset 0 1px 0 rgba(255, 255, 255, 0.04),
    0 0 80px rgba(0, 0, 0, 0.6);
}

/* Layer 3 shapes (front, with gold edge highlights) */
.geo-shape--6 {
  width: 55%;
  height: 35%;
  top: 35%;
  left: 25%;
  background: linear-gradient(135deg, #1f1f24 0%, #141416 100%);
  clip-path: polygon(15% 0%, 100% 5%, 85% 100%, 0% 95%);
  animation: shape-breathe-6 13s ease-in-out infinite;
  box-shadow: 
    inset 0 1px 0 rgba(224, 160, 48, 0.08),
    inset -1px 0 0 rgba(224, 160, 48, 0.05),
    0 0 100px rgba(0, 0, 0, 0.7);
}

.geo-shape--7 {
  width: 30%;
  height: 25%;
  top: 50%;
  right: 20%;
  background: linear-gradient(135deg, #222228 0%, #161618 100%);
  clip-path: polygon(0% 15%, 100% 0%, 100% 85%, 0% 100%);
  animation: shape-breathe-7 9s ease-in-out infinite;
  box-shadow: 
    inset 0 1px 0 rgba(224, 160, 48, 0.1),
    0 0 120px rgba(0, 0, 0, 0.8);
}

/* Breathing animations - subtle, organic */
@keyframes shape-breathe-1 {
  0%, 100% { transform: translate(0, 0) rotate(0deg); opacity: 0.8; }
  50% { transform: translate(10px, 5px) rotate(0.5deg); opacity: 0.9; }
}

@keyframes shape-breathe-2 {
  0%, 100% { transform: translate(0, 0) rotate(0deg); opacity: 0.75; }
  50% { transform: translate(-8px, -5px) rotate(-0.3deg); opacity: 0.85; }
}

@keyframes shape-breathe-3 {
  0%, 100% { transform: translate(0, 0) scale(1); opacity: 0.7; }
  50% { transform: translate(5px, -10px) scale(1.02); opacity: 0.8; }
}

@keyframes shape-breathe-4 {
  0%, 100% { transform: translate(0, 0); opacity: 0.85; }
  50% { transform: translate(-5px, 8px); opacity: 0.95; }
}

@keyframes shape-breathe-5 {
  0%, 100% { transform: translate(0, 0) rotate(0deg); opacity: 0.8; }
  50% { transform: translate(8px, -5px) rotate(0.2deg); opacity: 0.9; }
}

@keyframes shape-breathe-6 {
  0%, 100% { transform: translate(0, 0) scale(1); opacity: 0.9; }
  50% { transform: translate(-3px, 3px) scale(1.01); opacity: 1; }
}

@keyframes shape-breathe-7 {
  0%, 100% { transform: translate(0, 0); opacity: 0.85; }
  50% { transform: translate(5px, -3px); opacity: 0.95; }
}

/* Gold glimmer effects - catching the light */
.geo-glimmer {
  position: absolute;
  pointer-events: none;
  z-index: 5;
}

.geo-glimmer--1 {
  width: 200px;
  height: 3px;
  top: 38%;
  left: 25%;
  background: linear-gradient(90deg, 
    transparent 0%, 
    rgba(224, 160, 48, 0.4) 30%,
    rgba(224, 160, 48, 0.8) 50%,
    rgba(224, 160, 48, 0.4) 70%,
    transparent 100%
  );
  transform: rotate(-5deg);
  animation: glimmer-1 8s ease-in-out infinite;
  filter: blur(1px);
}

.geo-glimmer--2 {
  width: 150px;
  height: 2px;
  top: 52%;
  right: 22%;
  background: linear-gradient(90deg, 
    transparent 0%, 
    rgba(224, 160, 48, 0.3) 40%,
    rgba(224, 160, 48, 0.6) 50%,
    rgba(224, 160, 48, 0.3) 60%,
    transparent 100%
  );
  transform: rotate(8deg);
  animation: glimmer-2 10s ease-in-out infinite;
  animation-delay: 2s;
  filter: blur(1px);
}

.geo-glimmer--3 {
  width: 100px;
  height: 2px;
  bottom: 30%;
  left: 15%;
  background: linear-gradient(90deg, 
    transparent 0%, 
    rgba(224, 160, 48, 0.5) 50%,
    transparent 100%
  );
  transform: rotate(-12deg);
  animation: glimmer-3 6s ease-in-out infinite;
  animation-delay: 4s;
  filter: blur(0.5px);
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
   ═══════════════════════════════════════════ */
.combined {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #0a0a0c;
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
  background: rgba(255, 255, 255, 0.03);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.08);
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

/* Layer 1: Back ribbons (darkest) - going both directions */
.ribbon--1 {
  width: 180%;
  height: 60px;
  top: 5%;
  left: -40%;
  background: linear-gradient(135deg, #0e0e10 0%, #0a0a0c 100%);
  transform: rotate(-25deg);
  animation: ribbon-breathe 14s ease-in-out infinite;
}

.ribbon--2 {
  width: 180%;
  height: 45px;
  top: 15%;
  left: -40%;
  background: linear-gradient(135deg, #0f0f11 0%, #0b0b0d 100%);
  transform: rotate(22deg);
  animation: ribbon-breathe 16s ease-in-out infinite;
  animation-delay: 1s;
}

.ribbon--3 {
  width: 160%;
  height: 55px;
  bottom: 25%;
  left: -30%;
  background: linear-gradient(135deg, #0d0d0f 0%, #090909 100%);
  transform: rotate(-28deg);
  animation: ribbon-breathe 12s ease-in-out infinite;
  animation-delay: 2s;
}

.ribbon--4 {
  width: 170%;
  height: 50px;
  bottom: 10%;
  left: -35%;
  background: linear-gradient(135deg, #0e0e10 0%, #0a0a0c 100%);
  transform: rotate(20deg);
  animation: ribbon-breathe 15s ease-in-out infinite;
  animation-delay: 0.5s;
}

.ribbon--5 {
  width: 150%;
  height: 40px;
  top: 40%;
  left: -25%;
  background: linear-gradient(135deg, #0c0c0e 0%, #080808 100%);
  transform: rotate(-18deg);
  animation: ribbon-breathe 13s ease-in-out infinite;
  animation-delay: 3s;
}

.ribbon--6 {
  width: 140%;
  height: 35px;
  bottom: 40%;
  left: -20%;
  background: linear-gradient(135deg, #0d0d0f 0%, #090909 100%);
  transform: rotate(30deg);
  animation: ribbon-breathe 11s ease-in-out infinite;
  animation-delay: 1.5s;
}

/* Layer 2: Mid ribbons - more prominent */
.ribbon--7 {
  width: 160%;
  height: 70px;
  top: 20%;
  left: -30%;
  background: linear-gradient(135deg, #121214 0%, #0d0d0f 100%);
  transform: rotate(-22deg);
  box-shadow: 0 5px 30px rgba(0, 0, 0, 0.5);
  animation: ribbon-breathe 10s ease-in-out infinite;
}

.ribbon--8 {
  width: 170%;
  height: 55px;
  top: 35%;
  left: -35%;
  background: linear-gradient(135deg, #141416 0%, #0f0f11 100%);
  transform: rotate(25deg);
  box-shadow: 0 5px 30px rgba(0, 0, 0, 0.5);
  animation: ribbon-breathe 12s ease-in-out infinite;
  animation-delay: 2s;
}

.ribbon--9 {
  width: 150%;
  height: 50px;
  bottom: 30%;
  left: -25%;
  background: linear-gradient(135deg, #131315 0%, #0e0e10 100%);
  transform: rotate(-20deg);
  box-shadow: 0 5px 30px rgba(0, 0, 0, 0.5);
  animation: ribbon-breathe 14s ease-in-out infinite;
  animation-delay: 1s;
}

.ribbon--10 {
  width: 140%;
  height: 45px;
  bottom: 20%;
  left: -20%;
  background: linear-gradient(135deg, #121214 0%, #0c0c0e 100%);
  transform: rotate(28deg);
  box-shadow: 0 5px 30px rgba(0, 0, 0, 0.5);
  animation: ribbon-breathe 11s ease-in-out infinite;
  animation-delay: 3s;
}

.ribbon--11 {
  width: 130%;
  height: 40px;
  top: 55%;
  left: -15%;
  background: linear-gradient(135deg, #101012 0%, #0b0b0d 100%);
  transform: rotate(-32deg);
  box-shadow: 0 3px 20px rgba(0, 0, 0, 0.4);
  animation: ribbon-breathe 13s ease-in-out infinite;
  animation-delay: 0.5s;
}

.ribbon--12 {
  width: 120%;
  height: 35px;
  top: 65%;
  left: -10%;
  background: linear-gradient(135deg, #111113 0%, #0c0c0e 100%);
  transform: rotate(15deg);
  box-shadow: 0 3px 20px rgba(0, 0, 0, 0.4);
  animation: ribbon-breathe 15s ease-in-out infinite;
  animation-delay: 2.5s;
}

/* Layer 3: Front ribbons - lightest with gold edge highlights */
.ribbon--13 {
  width: 150%;
  height: 80px;
  top: 30%;
  left: -25%;
  background: linear-gradient(135deg, #1a1a1c 0%, #141416 100%);
  transform: rotate(-18deg);
  box-shadow: 
    inset 0 1px 0 rgba(224, 160, 48, 0.08),
    0 8px 40px rgba(0, 0, 0, 0.6);
  animation: ribbon-breathe-front 8s ease-in-out infinite;
}

.ribbon--14 {
  width: 140%;
  height: 65px;
  top: 45%;
  left: -20%;
  background: linear-gradient(135deg, #1c1c1e 0%, #161618 100%);
  transform: rotate(22deg);
  box-shadow: 
    inset 0 1px 0 rgba(224, 160, 48, 0.1),
    0 8px 40px rgba(0, 0, 0, 0.6);
  animation: ribbon-breathe-front 10s ease-in-out infinite;
  animation-delay: 1s;
}

.ribbon--15 {
  width: 130%;
  height: 55px;
  bottom: 35%;
  left: -15%;
  background: linear-gradient(135deg, #1b1b1d 0%, #151517 100%);
  transform: rotate(-25deg);
  box-shadow: 
    inset 0 1px 0 rgba(224, 160, 48, 0.12),
    0 8px 40px rgba(0, 0, 0, 0.6);
  animation: ribbon-breathe-front 9s ease-in-out infinite;
  animation-delay: 0.5s;
}

.ribbon--16 {
  width: 120%;
  height: 50px;
  bottom: 25%;
  left: -10%;
  background: linear-gradient(135deg, #1d1d1f 0%, #171719 100%);
  transform: rotate(18deg);
  box-shadow: 
    inset 0 1px 0 rgba(224, 160, 48, 0.15),
    0 8px 40px rgba(0, 0, 0, 0.6);
  animation: ribbon-breathe-front 11s ease-in-out infinite;
  animation-delay: 1.5s;
}

/* Ribbon breathing animations */
@keyframes ribbon-breathe {
  0%, 100% { 
    opacity: 0.8; 
    transform: rotate(var(--rotate, -25deg)) translateX(0); 
  }
  50% { 
    opacity: 0.9; 
    transform: rotate(var(--rotate, -25deg)) translateX(5px); 
  }
}

@keyframes ribbon-breathe-front {
  0%, 100% { 
    opacity: 0.95; 
    transform: rotate(var(--rotate, -18deg)) translateX(0) scale(1); 
  }
  50% { 
    opacity: 1; 
    transform: rotate(var(--rotate, -18deg)) translateX(3px) scale(1.005); 
  }
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
  animation: glimmer-sweep 6s ease-in-out infinite;
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
  animation: glimmer-sweep 8s ease-in-out infinite;
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
  animation: glimmer-sweep 5s ease-in-out infinite;
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
  animation: glimmer-sweep 7s ease-in-out infinite;
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
  animation: glimmer-sweep 9s ease-in-out infinite;
  animation-delay: 3s;
  filter: blur(0.5px);
}

@keyframes glimmer-sweep {
  0%, 15%, 100% { 
    opacity: 0; 
    transform: rotate(var(--rotate, -18deg)) translateX(-30px); 
  }
  30%, 70% { 
    opacity: 1; 
    transform: rotate(var(--rotate, -18deg)) translateX(0); 
  }
  85% { 
    opacity: 0; 
    transform: rotate(var(--rotate, -18deg)) translateX(30px); 
  }
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
</style>

