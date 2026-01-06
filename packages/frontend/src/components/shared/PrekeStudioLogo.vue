<script setup lang="ts">
/**
 * Preke Studio Logo Component
 * Combines the Preke logo with "studio" text for better visual balance
 */
import logoPreke from '@/assets/logo-preke.svg'

defineProps<{
  height?: number
}>()
</script>

<template>
  <div class="preke-studio-logo" :style="{ height: `${height || 36}px` }">
    <img :src="logoPreke" alt="Preke" class="preke-studio-logo__image" />
    <span class="preke-studio-logo__text">studio</span>
  </div>
</template>

<style scoped>
.preke-studio-logo {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.preke-studio-logo__image {
  height: 100%;
  width: auto;
  object-fit: contain;
}

.preke-studio-logo__text {
  font-family: var(--preke-font-sans);
  font-size: 0.95em; /* Sized to match the "Preke" text in the SVG */
  font-weight: 700;
  color: var(--preke-gold);
  letter-spacing: 0.02em;
  line-height: 1;
  margin-top: 0.02em; /* Slight optical adjustment for vertical centering */
}
</style>

