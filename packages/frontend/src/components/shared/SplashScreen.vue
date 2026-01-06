<script setup lang="ts">
/**
 * SplashScreen - Opening animation with large stacked logo
 * 
 * Shows the Preke Studio stacked logo with animated entrance
 * Auto-hides after the animation completes
 */
import { ref, onMounted } from 'vue'
import logoStacked from '@/assets/logo-studio-stacked.svg'

const isVisible = ref(true)
const isAnimating = ref(true)

onMounted(() => {
  // Animation runs for 4.5 seconds total
  setTimeout(() => {
    isAnimating.value = false
  }, 4000)
  
  // Hide completely after fade out
  setTimeout(() => {
    isVisible.value = false
  }, 4500)
})
</script>

<template>
  <Teleport to="body">
    <div 
      v-if="isVisible"
      class="splash"
      :class="{ 'splash--fading': !isAnimating }"
    >
      <!-- Ambient orbs -->
      <div class="splash__orb splash__orb--1"></div>
      <div class="splash__orb splash__orb--2"></div>
      <div class="splash__orb splash__orb--3"></div>
      
      <!-- Logo - much bigger -->
      <div class="splash__logo-container">
        <img 
          :src="logoStacked" 
          alt="Preke Studio" 
          class="splash__logo"
        />
      </div>
      
      <!-- Tagline -->
      <div class="splash__tagline">
        Professional Multi-Camera Recording
      </div>
      
      <!-- Loading bar -->
      <div class="splash__loader">
        <div class="splash__loader-bar"></div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.splash {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: #0a0a0a;
  overflow: hidden;
  transition: opacity 0.5s ease-out;
}

.splash--fading {
  opacity: 0;
  pointer-events: none;
}

/* Ambient orbs */
.splash__orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(150px);
  opacity: 0.6;
  pointer-events: none;
  animation: orb-float 6s ease-in-out infinite;
}

.splash__orb--1 {
  width: 600px;
  height: 600px;
  top: -200px;
  right: -200px;
  background: radial-gradient(circle, rgba(224, 160, 48, 0.5) 0%, transparent 70%);
  animation-delay: 0s;
}

.splash__orb--2 {
  width: 500px;
  height: 500px;
  bottom: -150px;
  left: -150px;
  background: radial-gradient(circle, rgba(168, 153, 104, 0.3) 0%, transparent 70%);
  animation-delay: 1s;
}

.splash__orb--3 {
  width: 400px;
  height: 400px;
  top: 30%;
  left: 50%;
  background: radial-gradient(circle, rgba(224, 160, 48, 0.3) 0%, transparent 70%);
  animation-delay: 2s;
}

@keyframes orb-float {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50% { transform: translate(40px, -40px) scale(1.1); }
}

/* Logo container */
.splash__logo-container {
  opacity: 0;
  animation: logo-enter 1.2s cubic-bezier(0.34, 1.56, 0.64, 1) 0.3s forwards;
}

@keyframes logo-enter {
  0% {
    opacity: 0;
    transform: scale(0.6) translateY(40px);
  }
  100% {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

/* Stacked logo - VERY BIG */
.splash__logo {
  width: 420px;
  height: auto;
  filter: drop-shadow(0 0 60px rgba(224, 160, 48, 0.5));
  animation: logo-glow 3s ease-in-out 1.5s infinite;
}

@keyframes logo-glow {
  0%, 100% { filter: drop-shadow(0 0 60px rgba(224, 160, 48, 0.5)); }
  50% { filter: drop-shadow(0 0 100px rgba(224, 160, 48, 0.7)); }
}

/* Tagline */
.splash__tagline {
  margin-top: 3rem;
  font-size: 1.125rem;
  color: #a8a8a8;
  opacity: 0;
  animation: tagline-enter 0.6s ease-out 1.2s forwards;
}

@keyframes tagline-enter {
  0% {
    opacity: 0;
    transform: translateY(20px);
  }
  100% {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Loading bar */
.splash__loader {
  position: absolute;
  bottom: 100px;
  width: 280px;
  height: 4px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
  overflow: hidden;
  opacity: 0;
  animation: loader-enter 0.3s ease-out 1.5s forwards;
}

@keyframes loader-enter {
  to { opacity: 1; }
}

.splash__loader-bar {
  height: 100%;
  background: linear-gradient(90deg, #e0a030, #f5c04a);
  border-radius: 2px;
  animation: loader-progress 2.5s ease-out 1.6s forwards;
  box-shadow: 0 0 20px rgba(224, 160, 48, 0.6);
}

@keyframes loader-progress {
  from { width: 0; }
  to { width: 100%; }
}

/* Responsive */
@media (max-width: 600px) {
  .splash__logo {
    width: 280px;
  }
  
  .splash__tagline {
    font-size: 0.9375rem;
    text-align: center;
    padding: 0 1rem;
  }
  
  .splash__loader {
    width: 200px;
  }
}
</style>
