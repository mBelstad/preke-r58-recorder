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
  // Animation runs for 4 seconds total (longer)
  setTimeout(() => {
    isAnimating.value = false
  }, 3500)
  
  // Hide completely after fade out
  setTimeout(() => {
    isVisible.value = false
  }, 4000)
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
      
      <!-- Logo -->
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
  filter: blur(120px);
  opacity: 0.5;
  pointer-events: none;
  animation: orb-float 5s ease-in-out infinite;
}

.splash__orb--1 {
  width: 500px;
  height: 500px;
  top: -150px;
  right: -150px;
  background: radial-gradient(circle, rgba(224, 160, 48, 0.5) 0%, transparent 70%);
  animation-delay: 0s;
}

.splash__orb--2 {
  width: 400px;
  height: 400px;
  bottom: -100px;
  left: -100px;
  background: radial-gradient(circle, rgba(168, 153, 104, 0.25) 0%, transparent 70%);
  animation-delay: 1s;
}

.splash__orb--3 {
  width: 300px;
  height: 300px;
  top: 35%;
  left: 55%;
  background: radial-gradient(circle, rgba(224, 160, 48, 0.25) 0%, transparent 70%);
  animation-delay: 2s;
}

@keyframes orb-float {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50% { transform: translate(30px, -30px) scale(1.05); }
}

/* Logo container */
.splash__logo-container {
  opacity: 0;
  animation: logo-enter 1s cubic-bezier(0.34, 1.56, 0.64, 1) 0.3s forwards;
}

@keyframes logo-enter {
  0% {
    opacity: 0;
    transform: scale(0.7) translateY(30px);
  }
  100% {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

/* Stacked logo - MUCH BIGGER */
.splash__logo {
  height: 280px;
  width: auto;
  filter: drop-shadow(0 0 40px rgba(224, 160, 48, 0.4));
  animation: logo-glow 3s ease-in-out 1s infinite;
}

@keyframes logo-glow {
  0%, 100% { filter: drop-shadow(0 0 40px rgba(224, 160, 48, 0.4)); }
  50% { filter: drop-shadow(0 0 70px rgba(224, 160, 48, 0.6)); }
}

/* Tagline */
.splash__tagline {
  margin-top: 2.5rem;
  font-size: 1rem;
  color: #a8a8a8;
  opacity: 0;
  animation: tagline-enter 0.6s ease-out 0.9s forwards;
}

@keyframes tagline-enter {
  0% {
    opacity: 0;
    transform: translateY(15px);
  }
  100% {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Loading bar */
.splash__loader {
  position: absolute;
  bottom: 80px;
  width: 240px;
  height: 4px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
  overflow: hidden;
  opacity: 0;
  animation: loader-enter 0.3s ease-out 1.2s forwards;
}

@keyframes loader-enter {
  from { opacity: 0; }
  to { opacity: 1; }
}

.splash__loader-bar {
  width: 0%;
  height: 100%;
  background: linear-gradient(90deg, #e0a030, #f5c04a);
  border-radius: 2px;
  animation: loader-progress 2.5s ease-out 1.3s forwards;
  box-shadow: 0 0 15px rgba(224, 160, 48, 0.6);
}

@keyframes loader-progress {
  0% { width: 0%; }
  100% { width: 100%; }
}

/* Responsive */
@media (max-width: 480px) {
  .splash__logo {
    height: 180px;
  }
  
  .splash__tagline {
    font-size: 0.875rem;
    text-align: center;
    padding: 0 1rem;
  }
}
</style>
