<script setup lang="ts">
/**
 * Preke Studio Logo Component
 * White Preke logo with waveform + "studio" text
 */
import logoPrekeWhite from '@/assets/logo-preke-white.svg'

defineProps<{
  height?: number
}>()
</script>

<template>
  <div class="preke-studio-logo">
    <img :src="logoPrekeWhite" alt="Preke" class="preke-studio-logo__image" />
    <span class="preke-studio-logo__text">studio</span>
  </div>
</template>

<style scoped>
.preke-studio-logo {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
  height: 32px;
  max-height: 32px; /* Prevent growing beyond container */
  overflow: visible; /* Allow full logo to show */
}

.preke-studio-logo__image {
  /* Full Preke logo with waveform - scale to show complete logo */
  height: 100%;
  max-height: 100%;
  width: auto;
  object-fit: contain;
  flex-shrink: 0; /* Don't shrink the image */
}

.preke-studio-logo__text {
  font-family: var(--preke-font-sans);
  font-size: 32px; /* Match the logo text size */
  font-weight: 800;
  color: var(--preke-gold);
  letter-spacing: 0.02em;
  line-height: 1;
  flex-shrink: 0; /* Don't shrink the text */
  white-space: nowrap; /* Prevent text wrapping */
}
</style>

