<script setup lang="ts">
/**
 * Animated Background Component
 * Adds subtle ambient animations: orbs, light beams, and geometric patterns
 * Can be customized for different color schemes
 */
defineProps<{
  /** Primary accent color (e.g., 'gold', 'red', 'purple') */
  accent?: 'gold' | 'red' | 'purple' | 'blue'
  /** Show moving light beams */
  showBeams?: boolean
  /** Show floating orbs */
  showOrbs?: boolean
  /** Show geometric pattern overlay */
  showPattern?: boolean
  /** Intensity of effects (0-1) */
  intensity?: number
}>()
</script>

<template>
  <div class="animated-bg">
    <!-- Gradient base -->
    <div class="animated-bg__gradient" :class="`animated-bg__gradient--${accent || 'gold'}`"></div>
    
    <!-- Subtle texture -->
    <div class="animated-bg__texture"></div>
    
    <!-- Floating orbs -->
    <template v-if="showOrbs !== false">
      <div class="animated-bg__orb animated-bg__orb--1" :class="`animated-bg__orb--${accent || 'gold'}`"></div>
      <div class="animated-bg__orb animated-bg__orb--2" :class="`animated-bg__orb--${accent || 'gold'}`"></div>
      <div class="animated-bg__orb animated-bg__orb--3"></div>
    </template>
    
    <!-- Light beams that sweep across -->
    <template v-if="showBeams !== false">
      <div class="animated-bg__beam animated-bg__beam--1"></div>
      <div class="animated-bg__beam animated-bg__beam--2" :class="`animated-bg__beam--${accent || 'gold'}`"></div>
    </template>
    
    <!-- Geometric pattern overlay (inspired by stock background) -->
    <div v-if="showPattern" class="animated-bg__pattern"></div>
  </div>
</template>

<style scoped>
.animated-bg {
  position: absolute;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
}

/* Gradient base with radial glow */
.animated-bg__gradient {
  position: absolute;
  inset: 0;
}

.animated-bg__gradient::before {
  content: '';
  position: absolute;
  inset: 0;
  background: 
    radial-gradient(ellipse 80% 50% at 50% 0%, rgba(59, 130, 246, 0.08), transparent 50%),
    radial-gradient(ellipse 60% 40% at 100% 100%, rgba(217, 152, 30, 0.06), transparent 40%);
}

.animated-bg__gradient--gold::before {
  background: 
    radial-gradient(ellipse 80% 50% at 50% 0%, rgba(224, 160, 48, 0.1), transparent 50%),
    radial-gradient(ellipse 60% 40% at 100% 100%, rgba(168, 153, 104, 0.06), transparent 40%);
}

.animated-bg__gradient--red::before {
  background: 
    radial-gradient(ellipse 80% 50% at 50% 0%, rgba(212, 90, 90, 0.1), transparent 50%),
    radial-gradient(ellipse 60% 40% at 100% 100%, rgba(212, 90, 90, 0.05), transparent 40%);
}

.animated-bg__gradient--purple::before {
  background: 
    radial-gradient(ellipse 80% 50% at 50% 0%, rgba(124, 58, 237, 0.1), transparent 50%),
    radial-gradient(ellipse 60% 40% at 100% 100%, rgba(167, 139, 250, 0.05), transparent 40%);
}

.animated-bg__gradient--blue::before {
  background: 
    radial-gradient(ellipse 80% 50% at 50% 0%, rgba(59, 130, 246, 0.1), transparent 50%),
    radial-gradient(ellipse 60% 40% at 100% 100%, rgba(96, 165, 250, 0.05), transparent 40%);
}

/* Subtle texture */
.animated-bg__texture {
  position: absolute;
  inset: 0;
  background-image: 
    repeating-linear-gradient(
      45deg,
      transparent 0px,
      transparent 1px,
      rgba(255, 255, 255, 0.008) 1px,
      rgba(255, 255, 255, 0.008) 2px
    );
  background-size: 8px 8px;
  opacity: 0.5;
}

/* Floating orbs */
.animated-bg__orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(100px);
  pointer-events: none;
}

.animated-bg__orb--1 {
  width: 500px;
  height: 500px;
  top: -15%;
  right: -10%;
  background: radial-gradient(circle, rgba(224, 160, 48, 0.12) 0%, transparent 70%);
  animation: orb-float-1 15s ease-in-out infinite;
}

.animated-bg__orb--2 {
  width: 400px;
  height: 400px;
  bottom: -10%;
  left: -10%;
  background: radial-gradient(circle, rgba(168, 153, 104, 0.1) 0%, transparent 70%);
  animation: orb-float-2 18s ease-in-out infinite;
}

.animated-bg__orb--3 {
  width: 300px;
  height: 300px;
  top: 40%;
  left: 50%;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.04) 0%, transparent 70%);
  animation: orb-float-3 12s ease-in-out infinite;
}

/* Color variants for orbs */
.animated-bg__orb--gold.animated-bg__orb--1 {
  background: radial-gradient(circle, rgba(224, 160, 48, 0.12) 0%, transparent 70%);
}

.animated-bg__orb--gold.animated-bg__orb--2 {
  background: radial-gradient(circle, rgba(168, 153, 104, 0.1) 0%, transparent 70%);
}

.animated-bg__orb--red.animated-bg__orb--1 {
  background: radial-gradient(circle, rgba(212, 90, 90, 0.15) 0%, transparent 70%);
}

.animated-bg__orb--red.animated-bg__orb--2 {
  background: radial-gradient(circle, rgba(212, 90, 90, 0.08) 0%, transparent 70%);
}

.animated-bg__orb--purple.animated-bg__orb--1 {
  background: radial-gradient(circle, rgba(124, 58, 237, 0.15) 0%, transparent 70%);
}

.animated-bg__orb--purple.animated-bg__orb--2 {
  background: radial-gradient(circle, rgba(167, 139, 250, 0.08) 0%, transparent 70%);
}

@keyframes orb-float-1 {
  0%, 100% { transform: translate(0, 0); opacity: 0.6; }
  50% { transform: translate(-50px, 80px); opacity: 0.8; }
}

@keyframes orb-float-2 {
  0%, 100% { transform: translate(0, 0); opacity: 0.5; }
  50% { transform: translate(60px, -60px); opacity: 0.7; }
}

@keyframes orb-float-3 {
  0%, 100% { transform: translate(-50%, 0); opacity: 0.3; }
  50% { transform: translate(-50%, -40px); opacity: 0.5; }
}

/* Light beams */
.animated-bg__beam {
  position: absolute;
  pointer-events: none;
  filter: blur(60px);
}

.animated-bg__beam--1 {
  width: 300px;
  height: 150px;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.12), transparent);
  top: 30%;
  left: -25%;
  transform: rotate(-15deg);
  animation: beam-sweep-1 8s ease-in-out infinite;
}

.animated-bg__beam--2 {
  width: 250px;
  height: 120px;
  background: linear-gradient(90deg, transparent, rgba(224, 160, 48, 0.1), transparent);
  bottom: 25%;
  right: -20%;
  transform: rotate(20deg);
  animation: beam-sweep-2 10s ease-in-out infinite;
  animation-delay: 4s;
}

.animated-bg__beam--red {
  background: linear-gradient(90deg, transparent, rgba(212, 90, 90, 0.1), transparent);
}

.animated-bg__beam--purple {
  background: linear-gradient(90deg, transparent, rgba(124, 58, 237, 0.1), transparent);
}

@keyframes beam-sweep-1 {
  0% { left: -30%; opacity: 0; }
  10% { opacity: 0.8; }
  90% { opacity: 0.8; }
  100% { left: 120%; opacity: 0; }
}

@keyframes beam-sweep-2 {
  0% { right: -25%; opacity: 0; }
  10% { opacity: 0.6; }
  90% { opacity: 0.6; }
  100% { right: 120%; opacity: 0; }
}

/* Geometric pattern overlay (inspired by stock background) */
.animated-bg__pattern {
  position: absolute;
  inset: 0;
  opacity: 0.03;
  background: 
    linear-gradient(135deg, transparent 40%, rgba(255, 255, 255, 0.5) 45%, transparent 50%),
    linear-gradient(-135deg, transparent 40%, rgba(255, 255, 255, 0.3) 45%, transparent 50%),
    linear-gradient(45deg, transparent 40%, rgba(255, 255, 255, 0.2) 45%, transparent 50%);
  background-size: 100px 100px, 80px 80px, 120px 120px;
  animation: pattern-shift 20s linear infinite;
}

@keyframes pattern-shift {
  0% { background-position: 0 0, 0 0, 0 0; }
  100% { background-position: 100px 100px, -80px 80px, 120px -120px; }
}
</style>

