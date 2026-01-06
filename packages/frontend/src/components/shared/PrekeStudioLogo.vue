<script setup lang="ts">
/**
 * Preke Studio Logo Component
 * White version of the Preke logo with "studio" text
 * Uses cropped SVG with no empty space for better sizing
 */
import logoWhiteCropped from '@/assets/logo-white-cropped.svg'

defineProps<{
  height?: number
}>()
</script>

<template>
  <div class="preke-studio-logo">
    <img :src="logoWhiteCropped" alt="Preke" class="preke-studio-logo__image" />
    <span class="preke-studio-logo__text">studio</span>
  </div>
</template>

<style scoped>
.preke-studio-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
  height: 38px;
  max-height: 38px; /* Prevent growing beyond container */
  overflow: hidden; /* Clip anything that overflows */
}

.preke-studio-logo__image {
  /* Cropped SVG with no empty space - scales perfectly */
  height: 100%;
  max-height: 100%;
  width: auto;
  object-fit: contain;
  flex-shrink: 0; /* Don't shrink the image */
}

.preke-studio-logo__text {
  font-family: var(--preke-font-sans);
  font-size: 36.8px; /* 15% bigger than 32px (32 * 1.15 = 36.8) */
  font-weight: 800;
  color: var(--preke-gold);
  letter-spacing: 0.02em;
  line-height: 1;
  flex-shrink: 0; /* Don't shrink the text */
  white-space: nowrap; /* Prevent text wrapping */
}
</style>

