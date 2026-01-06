<script setup lang="ts">
/**
 * Preke Studio Logo Component
 * White version of the Preke logo with "studio" text
 * The actual "Preke" text height matches the "studio" text height
 */
import logoWhite from '@/assets/logo-white.svg'

defineProps<{
  height?: number
}>()
</script>

<template>
  <div class="preke-studio-logo">
    <img :src="logoWhite" alt="Preke" class="preke-studio-logo__image" />
    <span class="preke-studio-logo__text">studio</span>
  </div>
</template>

<style scoped>
.preke-studio-logo {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
  height: 46px; /* 30% bigger than original 36px */
}

.preke-studio-logo__image {
  /* The SVG has a lot of empty space. Scale it so the actual "Preke" text 
     matches the height of the "studio" text */
  height: 100%;
  width: auto;
  object-fit: contain;
}

.preke-studio-logo__text {
  font-family: var(--preke-font-sans);
  font-size: 24px; /* Fixed size to match the "Preke" text in the logo */
  font-weight: 800;
  color: var(--preke-gold);
  letter-spacing: 0.02em;
  line-height: 1;
}
</style>

