<script setup lang="ts">
/**
 * Preke Studio Logo Component
 * White Preke logo with waveform + "studio" text (cropped for optimal sizing)
 */
import logoPrekeWhiteCropped from '@/assets/logo-preke-white-cropped.svg'
</script>

<template>
  <div class="preke-studio-logo">
    <img :src="logoPrekeWhiteCropped" alt="Preke" class="preke-studio-logo__image" />
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

.preke-studio-logo__text {
  font-family: var(--preke-font-sans);
  font-size: 32px; /* Slightly smaller */
  font-weight: 900; /* Heavier weight for fatter appearance */
  color: var(--preke-gold);
  letter-spacing: 0.01em; /* Tighter spacing for fatter look */
  line-height: 1;
  flex-shrink: 0;
  white-space: nowrap;
}
</style>

