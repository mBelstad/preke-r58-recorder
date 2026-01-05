<script setup lang="ts">
/**
 * LogoStudio - Preke Studio branding component
 * 
 * Supports two layouts:
 * - stacked: Preke waveform icon above, "STUDIO" text below
 * - inline: Waveform + "Preke Studio" horizontally
 */
defineProps<{
  layout?: 'stacked' | 'inline'
  size?: 'sm' | 'md' | 'lg' | 'xl'
  showText?: boolean
}>()
</script>

<template>
  <div 
    class="logo-studio" 
    :class="[
      `logo-studio--${layout || 'stacked'}`,
      `logo-studio--${size || 'md'}`
    ]"
  >
    <!-- Waveform icon -->
    <svg class="logo-studio__waveform" viewBox="0 0 50 36" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="logoGoldGrad" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stop-color="#f5c04a"/>
          <stop offset="100%" stop-color="#d9981e"/>
        </linearGradient>
      </defs>
      <!-- 7 waveform bars with gold gradient -->
      <rect x="0" y="13" width="4" height="10" rx="2" fill="url(#logoGoldGrad)"/>
      <rect x="7" y="9" width="4" height="18" rx="2" fill="url(#logoGoldGrad)"/>
      <rect x="14" y="5" width="4" height="26" rx="2" fill="url(#logoGoldGrad)"/>
      <rect x="21" y="0" width="4" height="36" rx="2" fill="url(#logoGoldGrad)"/>
      <rect x="28" y="5" width="4" height="26" rx="2" fill="url(#logoGoldGrad)"/>
      <rect x="35" y="9" width="4" height="18" rx="2" fill="url(#logoGoldGrad)"/>
      <rect x="42" y="13" width="4" height="10" rx="2" fill="url(#logoGoldGrad)"/>
    </svg>
    
    <!-- Text for stacked layout -->
    <div v-if="(layout || 'stacked') === 'stacked' && (showText !== false)" class="logo-studio__text-stacked">
      <span class="logo-studio__preke">Preke</span>
      <span class="logo-studio__studio">STUDIO</span>
    </div>
    
    <!-- Text for inline layout -->
    <div v-if="layout === 'inline' && (showText !== false)" class="logo-studio__text-inline">
      <span class="logo-studio__preke">Preke</span>
      <span class="logo-studio__studio">Studio</span>
    </div>
  </div>
</template>

<style scoped>
.logo-studio {
  display: flex;
  align-items: center;
  gap: var(--preke-space-sm, 8px);
  user-select: none;
}

/* Stacked layout: waveform above, text below */
.logo-studio--stacked {
  flex-direction: column;
  gap: var(--preke-space-md, 16px);
}

/* Inline layout: waveform left, text right */
.logo-studio--inline {
  flex-direction: row;
  gap: var(--preke-space-md, 16px);
}

/* Waveform sizing */
.logo-studio__waveform {
  filter: drop-shadow(0 0 16px rgba(224, 160, 48, 0.4));
  transition: filter 0.2s ease;
}

.logo-studio:hover .logo-studio__waveform {
  filter: drop-shadow(0 0 24px rgba(224, 160, 48, 0.6));
}

/* Size variants for waveform */
.logo-studio--sm .logo-studio__waveform {
  width: 36px;
  height: 26px;
}

.logo-studio--md .logo-studio__waveform {
  width: 50px;
  height: 36px;
}

.logo-studio--lg .logo-studio__waveform {
  width: 70px;
  height: 50px;
}

.logo-studio--xl .logo-studio__waveform {
  width: 100px;
  height: 72px;
}

/* Stacked text */
.logo-studio__text-stacked {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.logo-studio--stacked .logo-studio__preke {
  font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-weight: 800;
  color: #ffffff;
  letter-spacing: 0.02em;
  line-height: 1;
  text-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.logo-studio--stacked .logo-studio__studio {
  font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-weight: 700;
  color: #d9981e;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  line-height: 1;
}

/* Stacked size variants for text */
.logo-studio--stacked.logo-studio--sm .logo-studio__preke { font-size: 24px; }
.logo-studio--stacked.logo-studio--sm .logo-studio__studio { font-size: 12px; }

.logo-studio--stacked.logo-studio--md .logo-studio__preke { font-size: 36px; }
.logo-studio--stacked.logo-studio--md .logo-studio__studio { font-size: 16px; }

.logo-studio--stacked.logo-studio--lg .logo-studio__preke { font-size: 48px; }
.logo-studio--stacked.logo-studio--lg .logo-studio__studio { font-size: 20px; }

.logo-studio--stacked.logo-studio--xl .logo-studio__preke { font-size: 64px; }
.logo-studio--stacked.logo-studio--xl .logo-studio__studio { font-size: 28px; }

/* Inline text */
.logo-studio__text-inline {
  display: flex;
  align-items: baseline;
  gap: 0.25em;
}

.logo-studio--inline .logo-studio__preke {
  font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-weight: 700;
  color: #ffffff;
  letter-spacing: 0.01em;
}

.logo-studio--inline .logo-studio__studio {
  font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-weight: 700;
  color: #d9981e;
  letter-spacing: 0.01em;
}

/* Inline size variants for text */
.logo-studio--inline.logo-studio--sm .logo-studio__preke,
.logo-studio--inline.logo-studio--sm .logo-studio__studio { font-size: 18px; }

.logo-studio--inline.logo-studio--md .logo-studio__preke,
.logo-studio--inline.logo-studio--md .logo-studio__studio { font-size: 24px; }

.logo-studio--inline.logo-studio--lg .logo-studio__preke,
.logo-studio--inline.logo-studio--lg .logo-studio__studio { font-size: 32px; }

.logo-studio--inline.logo-studio--xl .logo-studio__preke,
.logo-studio--inline.logo-studio--xl .logo-studio__studio { font-size: 42px; }
</style>

