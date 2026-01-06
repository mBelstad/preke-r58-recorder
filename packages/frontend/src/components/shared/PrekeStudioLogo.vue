<script setup lang="ts">
/**
 * Preke Studio Logo Component
 * White version of the Preke logo with "studio" text
 */
import logoWhite from '@/assets/logo-white.svg'

defineProps<{
  height?: number
}>()
</script>

<template>
  <div class="preke-studio-logo" :style="{ height: `${height || 36}px` }">
    <img :src="logoWhite" alt="Preke" class="preke-studio-logo__image" />
    <span class="preke-studio-logo__text">studio</span>
  </div>
</template>

<style scoped>
.preke-studio-logo {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.preke-studio-logo__image {
  height: 130%; /* 30% bigger than container */
  width: auto;
  object-fit: contain;
}

.preke-studio-logo__text {
  font-family: var(--preke-font-sans);
  font-size: 1.3em; /* Sized to match the "Preke" text in the logo */
  font-weight: 800;
  color: var(--preke-gold);
  letter-spacing: 0.02em;
  line-height: 1;
}
</style>

