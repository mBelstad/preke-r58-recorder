<script setup lang="ts">
/**
 * Settings Panel Component
 * 
 * Quick access to UX settings:
 * - Audio feedback toggle
 * - Touch mode toggle
 * - Performance mode toggle
 */
import { computed, onMounted } from 'vue'
import { useAudioFeedback } from '@/composables/useAudioFeedback'
import { usePerformanceMode } from '@/composables/usePerformanceMode'

const { enabled: audioEnabled, toggle: toggleAudio, playClick } = useAudioFeedback()
const { 
  enabled: perfEnabled, 
  autoEnable: perfAutoEnable,
  isActive: perfActive,
  setEnabled: setPerfEnabled,
  setAutoEnable: setPerfAutoEnable,
} = usePerformanceMode()

// Touch mode (stored in localStorage)
const touchMode = computed({
  get: () => document.body.classList.contains('touch-mode'),
  set: (value: boolean) => {
    if (value) {
      document.body.classList.add('touch-mode')
      localStorage.setItem('r58_touch_mode', 'true')
    } else {
      document.body.classList.remove('touch-mode')
      localStorage.setItem('r58_touch_mode', 'false')
    }
  }
})

// Initialize touch mode from localStorage
onMounted(() => {
  if (localStorage.getItem('r58_touch_mode') === 'true') {
    document.body.classList.add('touch-mode')
  }
})

function handleAudioToggle() {
  toggleAudio()
  if (audioEnabled.value) {
    playClick()
  }
}
</script>

<template>
  <div class="space-y-4">
    <h3 class="text-sm font-semibold text-r58-text-secondary uppercase tracking-wide">
      Interface Settings
    </h3>
    
    <!-- Audio Feedback -->
    <label class="flex items-center justify-between py-2 cursor-pointer">
      <div>
        <span class="text-r58-text-primary">Audio Feedback</span>
        <p class="text-xs text-r58-text-secondary">Play sounds for recording start/stop</p>
      </div>
      <button
        @click="handleAudioToggle"
        :class="[
          'relative w-12 h-7 rounded-full transition-colors',
          audioEnabled ? 'bg-r58-accent-primary' : 'bg-r58-bg-tertiary'
        ]"
        role="switch"
        :aria-checked="audioEnabled"
      >
        <span 
          :class="[
            'absolute top-1 w-5 h-5 bg-white rounded-full shadow transition-transform',
            audioEnabled ? 'translate-x-6' : 'translate-x-1'
          ]"
        />
      </button>
    </label>
    
    <!-- Touch Mode -->
    <label class="flex items-center justify-between py-2 cursor-pointer">
      <div>
        <span class="text-r58-text-primary">Touch Mode</span>
        <p class="text-xs text-r58-text-secondary">Larger buttons for touchscreen</p>
      </div>
      <button
        @click="touchMode = !touchMode"
        :class="[
          'relative w-12 h-7 rounded-full transition-colors',
          touchMode ? 'bg-r58-accent-primary' : 'bg-r58-bg-tertiary'
        ]"
        role="switch"
        :aria-checked="touchMode"
      >
        <span 
          :class="[
            'absolute top-1 w-5 h-5 bg-white rounded-full shadow transition-transform',
            touchMode ? 'translate-x-6' : 'translate-x-1'
          ]"
        />
      </button>
    </label>
    
    <!-- Performance Mode -->
    <label class="flex items-center justify-between py-2 cursor-pointer">
      <div>
        <span class="text-r58-text-primary">Performance Mode</span>
        <p class="text-xs text-r58-text-secondary">
          Reduce UI updates during recording
          <span v-if="perfActive && !perfEnabled" class="text-amber-400">(auto-enabled)</span>
        </p>
      </div>
      <button
        @click="setPerfEnabled(!perfEnabled)"
        :class="[
          'relative w-12 h-7 rounded-full transition-colors',
          perfEnabled ? 'bg-r58-accent-primary' : 'bg-r58-bg-tertiary'
        ]"
        role="switch"
        :aria-checked="perfEnabled"
      >
        <span 
          :class="[
            'absolute top-1 w-5 h-5 bg-white rounded-full shadow transition-transform',
            perfEnabled ? 'translate-x-6' : 'translate-x-1'
          ]"
        />
      </button>
    </label>
    
    <!-- Auto Performance Mode -->
    <label class="flex items-center justify-between py-2 pl-4 cursor-pointer opacity-80">
      <div>
        <span class="text-sm text-r58-text-primary">Auto-enable when recording 3+ inputs</span>
      </div>
      <button
        @click="setPerfAutoEnable(!perfAutoEnable)"
        :class="[
          'relative w-10 h-6 rounded-full transition-colors',
          perfAutoEnable ? 'bg-r58-accent-primary' : 'bg-r58-bg-tertiary'
        ]"
        role="switch"
        :aria-checked="perfAutoEnable"
      >
        <span 
          :class="[
            'absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform',
            perfAutoEnable ? 'translate-x-4' : 'translate-x-0.5'
          ]"
        />
      </button>
    </label>
  </div>
</template>

