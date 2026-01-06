<script setup lang="ts">
/**
 * SplashScreen - 3-second opening animation
 * 
 * Shows the Preke Studio logo with animated entrance effects
 * Auto-hides after the animation completes
 */
import { ref, onMounted } from 'vue'
import logoWaveform from '@/assets/logo-waveform.svg'

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
      
      <!-- Logo container -->
      <div class="splash__content">
        <!-- Waveform icon -->
        <img 
          :src="logoWaveform" 
          alt="" 
          class="splash__waveform"
        />
        
        <!-- Text -->
        <div class="splash__text">
          <span class="splash__preke">Preke</span>
          <span class="splash__studio">Studio</span>
        </div>
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

/* Main content */
.splash__content {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  animation: splash-enter 0.8s cubic-bezier(0.34, 1.56, 0.64, 1) both;
}

@keyframes splash-enter {
  0% {
    opacity: 0;
    transform: scale(0.8);
  }
  100% {
    opacity: 1;
    transform: scale(1);
  }
}

/* Waveform */
.splash__waveform {
  width: 80px;
  height: 80px;
  opacity: 0;
  animation: 
    waveform-enter 0.6s ease-out 0.2s forwards,
    waveform-glow 2s ease-in-out 0.8s infinite;
}

@keyframes waveform-enter {
  0% {
    opacity: 0;
    transform: scale(0.5) rotate(-15deg);
  }
  100% {
    opacity: 1;
    transform: scale(1) rotate(0deg);
  }
}

@keyframes waveform-glow {
  0%, 100% { filter: drop-shadow(0 0 20px rgba(224, 160, 48, 0.4)); }
  50% { filter: drop-shadow(0 0 40px rgba(224, 160, 48, 0.6)); }
}

/* Text */
.splash__text {
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
  opacity: 0;
  animation: text-enter 0.6s ease-out 0.4s forwards;
}

@keyframes text-enter {
  0% {
    opacity: 0;
    transform: translateX(-20px);
  }
  100% {
    opacity: 1;
    transform: translateX(0);
  }
}

.splash__preke {
  font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-size: 3rem;
  font-weight: 800;
  color: #ffffff;
  letter-spacing: -0.02em;
}

.splash__studio {
  font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-size: 3rem;
  font-weight: 800;
  background: linear-gradient(to bottom, #f5c04a, #d9981e);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  filter: drop-shadow(0 0 12px rgba(224, 160, 48, 0.5));
}

/* Tagline */
.splash__tagline {
  margin-top: 1.5rem;
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
  .splash__content {
    flex-direction: column;
    gap: 0.75rem;
  }
  
  .splash__waveform {
    width: 60px;
    height: 60px;
  }
  
  .splash__preke,
  .splash__studio {
    font-size: 2.5rem;
  }
  
  .splash__tagline {
    font-size: 0.8125rem;
    text-align: center;
    padding: 0 1rem;
  }
}
</style>

