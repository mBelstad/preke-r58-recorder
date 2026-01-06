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
    <span class="preke-studio-logo__text">studio</span>
  </div>
</template>

<style scoped>
.preke-studio-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
  height: 45px; /* 40% bigger than original 32px: 32 * 1.4 = 44.8px, rounded to 45px */
}

.preke-studio-logo__image {
  height: 100%;
  width: auto;
  object-fit: contain;
  flex-shrink: 0;
}

.preke-studio-logo__text {
  font-family: var(--preke-font-sans);
  font-size: 32px;
  font-weight: 800;
  color: var(--preke-gold);
  letter-spacing: 0.02em;
  line-height: 1;
  flex-shrink: 0;
  white-space: nowrap;
}
</style>

