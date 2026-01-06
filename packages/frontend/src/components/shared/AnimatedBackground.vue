<script setup lang="ts">
/**
 * Animated Background Component
 * Sci-fi inspired ambient animations with breathing/pulsing effects
 * Inspired by Tron, modern tech aesthetics
 */
defineProps<{
  /** Primary accent color */
  accent?: 'gold' | 'red' | 'purple' | 'blue'
  /** Show moving light beams */
  showBeams?: boolean
  /** Show floating orbs */
  showOrbs?: boolean
  /** Show hexagonal grid */
  showGrid?: boolean
  /** Show circuit lines */
  showCircuits?: boolean
}>()
</script>

<template>
  <div class="animated-bg">
    <!-- Base gradient -->
    <div class="animated-bg__gradient" :class="`animated-bg__gradient--${accent || 'gold'}`"></div>
    
    <!-- Hexagonal grid overlay - sci-fi feel -->
    <div v-if="showGrid !== false" class="animated-bg__hex-grid"></div>
    
    <!-- Breathing orbs -->
    <template v-if="showOrbs !== false">
      <div class="animated-bg__orb animated-bg__orb--1" :class="`animated-bg__orb--${accent || 'gold'}`"></div>
      <div class="animated-bg__orb animated-bg__orb--2" :class="`animated-bg__orb--${accent || 'gold'}`"></div>
      <div class="animated-bg__orb animated-bg__orb--3"></div>
    </template>
    
    <!-- Scanning beams -->
    <template v-if="showBeams !== false">
      <div class="animated-bg__scan animated-bg__scan--h"></div>
      <div class="animated-bg__scan animated-bg__scan--v" :class="`animated-bg__scan--${accent || 'gold'}`"></div>
    </template>
    
    <!-- Circuit traces -->
    <div v-if="showCircuits" class="animated-bg__circuits">
      <div class="circuit-line circuit-line--1"></div>
      <div class="circuit-line circuit-line--2"></div>
      <div class="circuit-line circuit-line--3"></div>
      <div class="circuit-node circuit-node--1"></div>
      <div class="circuit-node circuit-node--2"></div>
    </div>
    
    <!-- Breathing pulse overlay -->
    <div class="animated-bg__pulse" :class="`animated-bg__pulse--${accent || 'gold'}`"></div>
  </div>
</template>

<style scoped>
.animated-bg {
  position: absolute;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
}

/* ═══════════════════════════════════════════
   GRADIENT BASE
   ═══════════════════════════════════════════ */
.animated-bg__gradient {
  position: absolute;
  inset: 0;
}

.animated-bg__gradient::before {
  content: '';
  position: absolute;
  inset: 0;
  background: 
    radial-gradient(ellipse 100% 80% at 50% 0%, rgba(255, 255, 255, 0.02), transparent 50%),
    radial-gradient(ellipse 80% 60% at 100% 100%, rgba(217, 152, 30, 0.04), transparent 40%);
}

.animated-bg__gradient--gold::before {
  background: 
    radial-gradient(ellipse 100% 80% at 50% 0%, rgba(224, 160, 48, 0.06), transparent 50%),
    radial-gradient(ellipse 80% 60% at 100% 100%, rgba(168, 153, 104, 0.04), transparent 40%);
}

.animated-bg__gradient--red::before {
  background: 
    radial-gradient(ellipse 100% 80% at 50% 0%, rgba(212, 90, 90, 0.06), transparent 50%),
    radial-gradient(ellipse 80% 60% at 100% 100%, rgba(212, 90, 90, 0.03), transparent 40%);
}

.animated-bg__gradient--purple::before {
  background: 
    radial-gradient(ellipse 100% 80% at 50% 0%, rgba(124, 58, 237, 0.06), transparent 50%),
    radial-gradient(ellipse 80% 60% at 100% 100%, rgba(167, 139, 250, 0.03), transparent 40%);
}

/* ═══════════════════════════════════════════
   HEXAGONAL GRID - Tron-like
   ═══════════════════════════════════════════ */
.animated-bg__hex-grid {
  position: absolute;
  inset: 0;
  opacity: 0.015;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='28' height='49' viewBox='0 0 28 49'%3E%3Cg fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='1'%3E%3Cpath d='M13.99 9.25l13 7.5v15l-13 7.5L1 31.75v-15l12.99-7.5zM3 17.9v12.7l10.99 6.34 11-6.35V17.9l-11-6.34L3 17.9zM0 15l12.98-7.5V0h-2v6.35L0 12.69v2.3zm0 18.5L12.98 41v8h-2v-6.85L0 35.81v-2.3zM15 0v7.5L27.99 15H28v-2.31h-.01L17 6.35V0h-2zm0 49v-8l12.99-7.5H28v2.31h-.01L17 42.15V49h-2z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
  animation: hex-breathe 8s ease-in-out infinite;
}

@keyframes hex-breathe {
  0%, 100% { 
    opacity: 0.012;
    transform: scale(1);
  }
  50% { 
    opacity: 0.025;
    transform: scale(1.02);
  }
}

/* ═══════════════════════════════════════════
   BREATHING ORBS
   ═══════════════════════════════════════════ */
.animated-bg__orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(120px);
  pointer-events: none;
}

.animated-bg__orb--1 {
  width: 600px;
  height: 600px;
  top: -20%;
  right: -15%;
  background: radial-gradient(circle, rgba(224, 160, 48, 0.1) 0%, transparent 70%);
  animation: orb-breathe-1 10s ease-in-out infinite;
}

.animated-bg__orb--2 {
  width: 500px;
  height: 500px;
  bottom: -15%;
  left: -15%;
  background: radial-gradient(circle, rgba(168, 153, 104, 0.08) 0%, transparent 70%);
  animation: orb-breathe-2 12s ease-in-out infinite;
}

.animated-bg__orb--3 {
  width: 400px;
  height: 400px;
  top: 30%;
  left: 40%;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.03) 0%, transparent 70%);
  animation: orb-breathe-3 8s ease-in-out infinite;
}

/* Color variants */
.animated-bg__orb--gold.animated-bg__orb--1 {
  background: radial-gradient(circle, rgba(224, 160, 48, 0.1) 0%, transparent 70%);
}
.animated-bg__orb--red.animated-bg__orb--1 {
  background: radial-gradient(circle, rgba(212, 90, 90, 0.12) 0%, transparent 70%);
}
.animated-bg__orb--purple.animated-bg__orb--1 {
  background: radial-gradient(circle, rgba(124, 58, 237, 0.12) 0%, transparent 70%);
}

/* Breathing animations - organic, alive feeling */
@keyframes orb-breathe-1 {
  0%, 100% { 
    transform: scale(1) translate(0, 0);
    opacity: 0.5;
  }
  25% {
    transform: scale(1.1) translate(-20px, 30px);
    opacity: 0.7;
  }
  50% { 
    transform: scale(0.95) translate(-10px, 15px);
    opacity: 0.4;
  }
  75% {
    transform: scale(1.05) translate(10px, -10px);
    opacity: 0.6;
  }
}

@keyframes orb-breathe-2 {
  0%, 100% { 
    transform: scale(1) translate(0, 0);
    opacity: 0.4;
  }
  33% {
    transform: scale(1.15) translate(30px, -20px);
    opacity: 0.6;
  }
  66% { 
    transform: scale(0.9) translate(15px, 10px);
    opacity: 0.35;
  }
}

@keyframes orb-breathe-3 {
  0%, 100% { 
    transform: translate(-50%, 0) scale(1);
    opacity: 0.25;
  }
  50% { 
    transform: translate(-50%, -30px) scale(1.2);
    opacity: 0.4;
  }
}

/* ═══════════════════════════════════════════
   SCANNING BEAMS - Tron light cycle feel
   ═══════════════════════════════════════════ */
.animated-bg__scan {
  position: absolute;
  pointer-events: none;
}

/* Horizontal scan line */
.animated-bg__scan--h {
  width: 100%;
  height: 1px;
  left: 0;
  top: 0;
  background: linear-gradient(90deg, 
    transparent 0%, 
    rgba(255, 255, 255, 0.1) 20%,
    rgba(255, 255, 255, 0.3) 50%,
    rgba(255, 255, 255, 0.1) 80%,
    transparent 100%
  );
  box-shadow: 
    0 0 20px rgba(255, 255, 255, 0.1),
    0 0 40px rgba(255, 255, 255, 0.05);
  animation: scan-h 8s ease-in-out infinite;
}

/* Vertical scan line */
.animated-bg__scan--v {
  width: 1px;
  height: 100%;
  left: 0;
  top: 0;
  background: linear-gradient(180deg, 
    transparent 0%, 
    rgba(224, 160, 48, 0.15) 30%,
    rgba(224, 160, 48, 0.4) 50%,
    rgba(224, 160, 48, 0.15) 70%,
    transparent 100%
  );
  box-shadow: 
    0 0 30px rgba(224, 160, 48, 0.15),
    0 0 60px rgba(224, 160, 48, 0.08);
  animation: scan-v 12s ease-in-out infinite;
  animation-delay: 4s;
}

.animated-bg__scan--red {
  background: linear-gradient(180deg, 
    transparent 0%, 
    rgba(212, 90, 90, 0.15) 30%,
    rgba(212, 90, 90, 0.4) 50%,
    rgba(212, 90, 90, 0.15) 70%,
    transparent 100%
  );
  box-shadow: 
    0 0 30px rgba(212, 90, 90, 0.15),
    0 0 60px rgba(212, 90, 90, 0.08);
}

.animated-bg__scan--purple {
  background: linear-gradient(180deg, 
    transparent 0%, 
    rgba(124, 58, 237, 0.15) 30%,
    rgba(124, 58, 237, 0.4) 50%,
    rgba(124, 58, 237, 0.15) 70%,
    transparent 100%
  );
  box-shadow: 
    0 0 30px rgba(124, 58, 237, 0.15),
    0 0 60px rgba(124, 58, 237, 0.08);
}

@keyframes scan-h {
  0%, 100% { top: -2px; opacity: 0; }
  5% { opacity: 0.8; }
  95% { opacity: 0.8; }
  100% { top: 100%; opacity: 0; }
}

@keyframes scan-v {
  0%, 100% { left: -2px; opacity: 0; }
  5% { opacity: 0.6; }
  95% { opacity: 0.6; }
  100% { left: 100%; opacity: 0; }
}

/* ═══════════════════════════════════════════
   CIRCUIT TRACES
   ═══════════════════════════════════════════ */
.animated-bg__circuits {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.circuit-line {
  position: absolute;
  background: linear-gradient(90deg, transparent, rgba(224, 160, 48, 0.15), transparent);
  height: 1px;
}

.circuit-line--1 {
  top: 25%;
  left: 10%;
  width: 30%;
  animation: circuit-glow 4s ease-in-out infinite;
}

.circuit-line--2 {
  top: 60%;
  right: 5%;
  width: 25%;
  animation: circuit-glow 5s ease-in-out infinite;
  animation-delay: 1.5s;
}

.circuit-line--3 {
  bottom: 30%;
  left: 20%;
  width: 20%;
  animation: circuit-glow 6s ease-in-out infinite;
  animation-delay: 3s;
}

.circuit-node {
  position: absolute;
  width: 4px;
  height: 4px;
  background: rgba(224, 160, 48, 0.4);
  border-radius: 50%;
  box-shadow: 0 0 10px rgba(224, 160, 48, 0.3);
}

.circuit-node--1 {
  top: 25%;
  left: 40%;
  animation: node-pulse 3s ease-in-out infinite;
}

.circuit-node--2 {
  top: 60%;
  right: 30%;
  animation: node-pulse 3s ease-in-out infinite;
  animation-delay: 1s;
}

@keyframes circuit-glow {
  0%, 100% { opacity: 0.1; }
  50% { opacity: 0.4; }
}

@keyframes node-pulse {
  0%, 100% { 
    transform: scale(1);
    opacity: 0.3;
    box-shadow: 0 0 10px rgba(224, 160, 48, 0.3);
  }
  50% { 
    transform: scale(1.5);
    opacity: 0.6;
    box-shadow: 0 0 20px rgba(224, 160, 48, 0.5);
  }
}

/* ═══════════════════════════════════════════
   BREATHING PULSE OVERLAY - The "alive" feeling
   ═══════════════════════════════════════════ */
.animated-bg__pulse {
  position: absolute;
  inset: 0;
  background: radial-gradient(ellipse at center, transparent 0%, transparent 50%, rgba(0, 0, 0, 0.1) 100%);
  animation: ambient-breathe 6s ease-in-out infinite;
}

.animated-bg__pulse--gold {
  background: radial-gradient(ellipse at center, 
    rgba(224, 160, 48, 0.02) 0%, 
    transparent 40%, 
    rgba(0, 0, 0, 0.05) 100%
  );
}

.animated-bg__pulse--red {
  background: radial-gradient(ellipse at center, 
    rgba(212, 90, 90, 0.02) 0%, 
    transparent 40%, 
    rgba(0, 0, 0, 0.05) 100%
  );
}

.animated-bg__pulse--purple {
  background: radial-gradient(ellipse at center, 
    rgba(124, 58, 237, 0.02) 0%, 
    transparent 40%, 
    rgba(0, 0, 0, 0.05) 100%
  );
}

@keyframes ambient-breathe {
  0%, 100% { 
    opacity: 0.5;
    transform: scale(1);
  }
  50% { 
    opacity: 0.8;
    transform: scale(1.02);
  }
}
</style>
