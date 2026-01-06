<script setup lang="ts">
/**
 * Background Experiments View
 * Sci-fi / Tron inspired explorations with the geometric pattern
 * Navigate to /experiments to view these live
 */
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import geometricPattern from '@/assets/geometric-pattern.jpeg'

const router = useRouter()
const activeExperiment = ref<number>(1)
const experiments = [
  { id: 1, name: 'Breathing Tech', desc: 'Organic breathing with subtle pulse' },
  { id: 2, name: 'Tron Grid', desc: 'Hexagonal overlay with scan lines' },
  { id: 3, name: 'Circuit Flow', desc: 'Data flowing through circuits' },
  { id: 4, name: 'Holographic', desc: 'Hologram-like distortion effect' },
  { id: 5, name: 'Neural Net', desc: 'Connected nodes pulsing with life' },
]
</script>

<template>
  <div class="experiments">
    <!-- Navigation -->
    <div class="experiments__nav">
      <button class="experiments__back" @click="router.push('/admin')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M19 12H5M12 19l-7-7 7-7"/>
        </svg>
        Back
      </button>
      <h1 class="experiments__title">Sci-Fi Background Experiments</h1>
      <div class="experiments__tabs">
        <button 
          v-for="exp in experiments" 
          :key="exp.id"
          @click="activeExperiment = exp.id"
          class="experiments__tab"
          :class="{ 'experiments__tab--active': activeExperiment === exp.id }"
        >
          {{ exp.name }}
        </button>
      </div>
    </div>

    <!-- Experiment 1: Breathing Tech -->
    <div v-show="activeExperiment === 1" class="exp exp--breathing">
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

    <!-- Experiment 2: Tron Grid -->
    <div v-show="activeExperiment === 2" class="exp exp--tron">
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

    <!-- Experiment 3: Circuit Flow -->
    <div v-show="activeExperiment === 3" class="exp exp--circuit">
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

    <!-- Experiment 4: Holographic -->
    <div v-show="activeExperiment === 4" class="exp exp--holo">
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

    <!-- Experiment 5: Neural Net -->
    <div v-show="activeExperiment === 5" class="exp exp--neural">
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
.experiments {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--preke-bg);
  overflow-y: auto;
}

.experiments__nav {
  position: sticky;
  top: 0;
  z-index: 100;
  padding: 1rem 2rem 1.5rem;
  background: rgba(0, 0, 0, 0.85);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--preke-border);
}

/* Back button */
.experiments__back {
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

.experiments__back:hover {
  background: rgba(255, 255, 255, 0.1);
  color: var(--preke-text);
  border-color: rgba(255, 255, 255, 0.2);
}

.experiments__back svg {
  width: 16px;
  height: 16px;
}

.experiments__title {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--preke-text);
  margin-bottom: 1rem;
}

.experiments__tabs {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.experiments__tab {
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

.experiments__tab:hover {
  color: var(--preke-text);
  border-color: var(--preke-border-light);
}

.experiments__tab--active {
  color: var(--preke-gold);
  background: rgba(224, 160, 48, 0.1);
  border-color: var(--preke-gold);
}

/* ═══════════════════════════════════════════
   BASE EXPERIMENT STYLES
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

/* ═══════════════════════════════════════════
   EXPERIMENT 1: BREATHING TECH
   ═══════════════════════════════════════════ */
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

/* ═══════════════════════════════════════════
   EXPERIMENT 2: TRON GRID
   ═══════════════════════════════════════════ */
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

/* ═══════════════════════════════════════════
   EXPERIMENT 3: CIRCUIT FLOW
   ═══════════════════════════════════════════ */
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

/* ═══════════════════════════════════════════
   EXPERIMENT 4: HOLOGRAPHIC
   ═══════════════════════════════════════════ */
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

/* ═══════════════════════════════════════════
   EXPERIMENT 5: NEURAL NETWORK
   ═══════════════════════════════════════════ */
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
