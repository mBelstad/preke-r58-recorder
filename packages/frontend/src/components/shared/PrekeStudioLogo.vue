<script setup lang="ts">
/**
 * Preke Studio Logo Component
 * White Preke logo with waveform + "studio" text (cropped for optimal sizing)
 */
import logoPrekeWhiteCropped from '@/assets/logo-preke-white-cropped.svg'

defineProps<{
  height?: number
}>()
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
  gap: 12px;
  flex-shrink: 0;
}

.preke-studio-logo__image {
  /* Make the logo image much bigger - explicit height to match text */
  height: 48px;
  width: auto;
  object-fit: contain;
  flex-shrink: 0;
}

.preke-studio-logo__text {
  font-family: var(--preke-font-sans);
  font-size: 48px; /* Large text to match logo */
  font-weight: 800;
  color: var(--preke-gold);
  letter-spacing: 0.02em;
  line-height: 1;
  flex-shrink: 0;
  white-space: nowrap;
}
</style>

