<script setup lang="ts">
/**
 * SplashScreen - Opening animation with stacked logo
 * 
 * Shows the Preke Studio stacked logo with animated entrance
 * Auto-hides after the animation completes
 */
import { ref, onMounted } from 'vue'
import logoStacked from '@/assets/logo-studio-stacked.svg'

const isVisible = ref(true)
const isAnimating = ref(true)

onMounted(() => {
  // Animation runs for 3 seconds total
  setTimeout(() => {
    isAnimating.value = false
  }, 2500)
  
  // Hide completely after fade out
  setTimeout(() => {
    isVisible.value = false
  }, 3000)
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
  filter: blur(100px);
  opacity: 0.4;
  pointer-events: none;
  animation: orb-float 4s ease-in-out infinite;
}

.splash__orb--1 {
  width: 400px;
  height: 400px;
  top: -100px;
  right: -100px;
  background: radial-gradient(circle, rgba(224, 160, 48, 0.4) 0%, transparent 70%);
  animation-delay: 0s;
}

.splash__orb--2 {
  width: 300px;
  height: 300px;
  bottom: -50px;
  left: -50px;
  background: radial-gradient(circle, rgba(168, 153, 104, 0.2) 0%, transparent 70%);
  animation-delay: 1s;
}

.splash__orb--3 {
  width: 200px;
  height: 200px;
  top: 40%;
  left: 60%;
  background: radial-gradient(circle, rgba(224, 160, 48, 0.2) 0%, transparent 70%);
  animation-delay: 2s;
}

@keyframes orb-float {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(20px, -20px); }
}

/* Logo container */
.splash__logo-container {
  opacity: 0;
  animation: logo-enter 0.8s cubic-bezier(0.34, 1.56, 0.64, 1) 0.2s forwards;
}

@keyframes logo-enter {
  0% {
    opacity: 0;
    transform: scale(0.8) translateY(20px);
  }
  100% {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

/* Stacked logo */
.splash__logo {
  height: 180px;
  width: auto;
  filter: drop-shadow(0 0 30px rgba(224, 160, 48, 0.3));
  animation: logo-glow 2.5s ease-in-out 0.8s infinite;
}

@keyframes logo-glow {
  0%, 100% { filter: drop-shadow(0 0 30px rgba(224, 160, 48, 0.3)); }
  50% { filter: drop-shadow(0 0 50px rgba(224, 160, 48, 0.5)); }
}

/* Tagline */
.splash__tagline {
  margin-top: 2rem;
  font-size: 0.9375rem;
  color: #a8a8a8;
  opacity: 0;
  animation: tagline-enter 0.5s ease-out 0.7s forwards;
}

@keyframes tagline-enter {
  0% {
    opacity: 0;
    transform: translateY(10px);
  }
  100% {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Loading bar */
.splash__loader {
  position: absolute;
  bottom: 60px;
  width: 200px;
  height: 3px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
  overflow: hidden;
  opacity: 0;
  animation: loader-enter 0.3s ease-out 0.9s forwards;
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
  animation: loader-progress 2s ease-out 1s forwards;
  box-shadow: 0 0 10px rgba(224, 160, 48, 0.5);
}

@keyframes loader-progress {
  0% { width: 0%; }
  100% { width: 100%; }
}

/* Responsive */
@media (max-width: 480px) {
  .splash__logo {
    height: 140px;
  }
  
  .splash__tagline {
    font-size: 0.8125rem;
    text-align: center;
    padding: 0 1rem;
  }
}
</style>
