<script setup lang="ts">
/**
 * TransitionSettings - Transition type and duration controls
 * 
 * Quick access to transition configuration for PVW→PGM switches.
 */
import { computed } from 'vue'
import { useMixerStore } from '@/stores/mixer'

const mixerStore = useMixerStore()

// Current transition settings
const transitionType = computed({
  get: () => mixerStore.transition.type,
  set: (type) => mixerStore.setTransition({ type })
})

const transitionDuration = computed({
  get: () => mixerStore.transition.duration,
  set: (duration) => mixerStore.setTransition({ duration })
})

// Options
const typeOptions = [
  { value: 'cut', label: 'Cut', icon: '⚡' },
  { value: 'fade', label: 'Fade', icon: '🌫️' },
  { value: 'wipe-left', label: 'Wipe L', icon: '◀' },
  { value: 'wipe-right', label: 'Wipe R', icon: '▶' },
  { value: 'wipe-up', label: 'Wipe Up', icon: '▲' },
  { value: 'wipe-down', label: 'Wipe Down', icon: '▼' }
]

const durationOptions = [
  { value: 0, label: '0ms' },
  { value: 100, label: '100ms' },
  { value: 300, label: '300ms' },
  { value: 500, label: '500ms' },
  { value: 750, label: '750ms' },
  { value: 1000, label: '1s' },
  { value: 2000, label: '2s' }
]

function selectType(type: string) {
  mixerStore.setTransition({ type: type as any })
}
</script>

<template>
  <div class="transition-settings space-y-3" data-testid="transition-settings">
    <!-- Transition Type Grid -->
    <div class="grid grid-cols-3 gap-1">
      <button
        v-for="opt in typeOptions"
        :key="opt.value"
        @click="selectType(opt.value)"
        class="px-2 py-2 text-xs rounded transition-colors text-center"
        :class="transitionType === opt.value 
          ? 'bg-r58-accent-primary text-white' 
          : 'bg-r58-bg-tertiary hover:bg-r58-bg-tertiary/80 text-r58-text-secondary'"
      >
        <span class="block text-sm mb-0.5">{{ opt.icon }}</span>
        {{ opt.label }}
      </button>
    </div>
    
    <!-- Duration Selector -->
    <div>
      <label class="block text-xs text-r58-text-secondary mb-1">Duration</label>
      <select 
        v-model.number="transitionDuration"
        class="w-full px-3 py-2 text-sm bg-r58-bg-tertiary border border-r58-bg-tertiary rounded-lg focus:border-r58-accent-primary focus:outline-none"
        :disabled="transitionType === 'cut'"
      >
        <option v-for="opt in durationOptions" :key="opt.value" :value="opt.value">
          {{ opt.label }}
        </option>
      </select>
    </div>
    
    <!-- Preview -->
    <div class="p-3 bg-r58-bg-tertiary rounded-lg">
      <div class="flex items-center justify-between text-xs">
        <span class="text-r58-text-secondary">Current:</span>
        <span class="font-mono">
          {{ typeOptions.find(o => o.value === transitionType)?.label }}
          <span v-if="transitionType !== 'cut'"> ({{ transitionDuration }}ms)</span>
        </span>
      </div>
    </div>
    
    <!-- Quick Tip -->
    <p class="text-xs text-r58-text-secondary">
      Press <kbd class="px-1 py-0.5 bg-r58-bg-tertiary rounded">Space</kbd> to Take with transition
    </p>
  </div>
</template>

