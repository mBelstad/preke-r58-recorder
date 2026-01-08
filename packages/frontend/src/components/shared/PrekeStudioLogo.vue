<script setup lang="ts">
/**
 * Preke Studio Logo Component
 * White Preke logo with waveform + "studio" text (cropped for optimal sizing)
 */
import logoPrekeWhiteCropped from '@/assets/logo-preke-white-cropped.svg'
import logoPrekeDark from '@/assets/logo-preke.svg'
import { ref, onMounted, onUnmounted } from 'vue'

const logoSrc = ref(logoPrekeWhiteCropped)

function updateLogo() {
  const theme = document.documentElement.getAttribute('data-theme')
  logoSrc.value = theme === 'light' ? logoPrekeDark : logoPrekeWhiteCropped
}

let observer: MutationObserver | null = null

onMounted(() => {
  updateLogo()
  // Watch for theme changes
  observer = new MutationObserver(updateLogo)
  observer.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['data-theme']
  })
})

onUnmounted(() => {
  if (observer) {
    observer.disconnect()
    observer = null
  }
})
</script>

<template>
  <div class="preke-studio-logo">
    <img 
      :src="logoSrc" 
      alt="Preke" 
      class="preke-studio-logo__image" 
    />
    <span class="preke-studio-logo__text">STUDIO</span>
  </div>
</template>

<style scoped>
.preke-studio-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
  height: auto; /* Remove height constraint to allow text to grow */
  min-height: 40px; /* Minimum height for consistency */
}

.preke-studio-logo__image {
  height: 40px; /* Fixed height for logo image */
  width: auto;
  object-fit: contain;
  flex-shrink: 0;
}

/* Light mode: Use dark logo (no filter needed - we switch the image source) */

.preke-studio-logo__text {
  font-family: var(--preke-font-sans);
  font-size: 28px; /* Smaller than before */
  font-weight: 900; /* Heavier weight for fatter appearance */
  color: var(--preke-gold);
  letter-spacing: 0.01em; /* Tighter spacing for fatter look */
  line-height: 1;
  flex-shrink: 0;
  white-space: nowrap;
  transform: translateY(0px); /* 1 pixel lower than before (was -1px, now 0px) */
}
</style>

