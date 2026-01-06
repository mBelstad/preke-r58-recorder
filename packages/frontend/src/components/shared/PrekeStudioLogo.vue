<script setup lang="ts">
/**
 * Preke Studio Logo Component
 * Combines the white waveform logo with "studio" text for better visual balance
 */
import logoWaveform from '@/assets/logo-waveform-white.svg'

defineProps<{
  height?: number
}>()
</script>

<template>
  <div class="preke-studio-logo" :style="{ height: `${height || 36}px` }">
    <img :src="logoWaveform" alt="Preke" class="preke-studio-logo__waveform" />
    <span class="preke-studio-logo__text preke-studio-logo__text--preke">preke</span>
    <span class="preke-studio-logo__text preke-studio-logo__text--studio">studio</span>
  </div>
</template>

<style scoped>
.preke-studio-logo {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.preke-studio-logo__waveform {
  height: 130%; /* 30% bigger than container */
  width: auto;
  object-fit: contain;
}

.preke-studio-logo__text {
  font-family: var(--preke-font-sans);
  font-size: 1.3em; /* Sized to match container height */
  font-weight: 800;
  letter-spacing: 0.02em;
  line-height: 1;
}

.preke-studio-logo__text--preke {
  color: var(--preke-text); /* White/light text */
}

.preke-studio-logo__text--studio {
  color: var(--preke-gold); /* Gold accent */
}
</style>

