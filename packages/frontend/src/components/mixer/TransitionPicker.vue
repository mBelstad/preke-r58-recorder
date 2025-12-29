<script setup lang="ts">
/**
 * TransitionPicker Component
 * 
 * Select and configure transitions between sources/scenes:
 * - Cut (instant)
 * - Fade (cross-dissolve)
 * - Wipe (directional)
 * - Slide
 * - Zoom
 * - Custom durations
 */
import { ref, computed } from 'vue'
import { toast } from '@/composables/useToast'
import type { VdoTransitionType, VdoTransitionConfig } from '@/types/vdoninja'

// Props
const props = defineProps<{
  vdoEmbed?: {
    sendCommand: (action: string, target?: string, value?: unknown) => void
  }
}>()

// Emit for parent to know about transition
const emit = defineEmits<{
  transition: [config: VdoTransitionConfig]
}>()

// Local state
const selectedType = ref<VdoTransitionType>('cut')
const duration = ref(500) // milliseconds
const isExpanded = ref(false)

// Transition options
interface TransitionOption {
  type: VdoTransitionType
  name: string
  icon: string
  description: string
  hasDuration: boolean
}

const transitions: TransitionOption[] = [
  { type: 'cut', name: 'Cut', icon: '⏹', description: 'Instant switch', hasDuration: false },
  { type: 'fade', name: 'Fade', icon: '🌫️', description: 'Cross-dissolve', hasDuration: true },
  { type: 'wipe-left', name: 'Wipe Left', icon: '◀️', description: 'Wipe from right to left', hasDuration: true },
  { type: 'wipe-right', name: 'Wipe Right', icon: '▶️', description: 'Wipe from left to right', hasDuration: true },
  { type: 'wipe-up', name: 'Wipe Up', icon: '🔼', description: 'Wipe from bottom to top', hasDuration: true },
  { type: 'wipe-down', name: 'Wipe Down', icon: '🔽', description: 'Wipe from top to bottom', hasDuration: true },
  { type: 'slide-left', name: 'Slide Left', icon: '⬅️', description: 'Slide in from right', hasDuration: true },
  { type: 'slide-right', name: 'Slide Right', icon: '➡️', description: 'Slide in from left', hasDuration: true },
  { type: 'zoom', name: 'Zoom', icon: '🔍', description: 'Zoom in/out', hasDuration: true },
]

// Duration presets
const durationPresets = [
  { value: 200, label: '0.2s' },
  { value: 500, label: '0.5s' },
  { value: 1000, label: '1s' },
  { value: 2000, label: '2s' },
]

// Current transition config
const currentConfig = computed<VdoTransitionConfig>(() => ({
  type: selectedType.value,
  duration: duration.value,
}))

// Selected transition details
const selectedTransition = computed(() => 
  transitions.find(t => t.type === selectedType.value) || transitions[0]
)

// Select a transition type
function selectTransition(type: VdoTransitionType) {
  selectedType.value = type
  
  // Collapse picker if instant transition
  if (type === 'cut') {
    isExpanded.value = false
  }
}

// Execute the transition
function executeTransition() {
  const config = currentConfig.value
  
  // Send to VDO.ninja
  if (props.vdoEmbed) {
    if (config.type === 'cut') {
      // Instant cut - no transition command needed
      props.vdoEmbed.sendCommand('cut')
    } else {
      // Animated transition
      props.vdoEmbed.sendCommand('transition', undefined, config)
    }
  }
  
  // Emit to parent
  emit('transition', config)
  
  toast.info(`${selectedTransition.value.name}${config.type !== 'cut' ? ` (${config.duration}ms)` : ''}`)
}

// Quick cut (T key equivalent)
function quickCut() {
  selectedType.value = 'cut'
  executeTransition()
}

// Quick auto-transition (A key equivalent)
function quickAuto() {
  if (selectedType.value === 'cut') {
    selectedType.value = 'fade'
  }
  executeTransition()
}

// Toggle expanded state
function toggleExpanded() {
  isExpanded.value = !isExpanded.value
}

// Expose methods
defineExpose({ executeTransition, quickCut, quickAuto })
</script>

<template>
  <div class="transition-picker" data-testid="transition-picker">
    <!-- Compact view - quick buttons -->
    <div class="flex items-center gap-2">
      <!-- Cut button -->
      <button
        @click="quickCut"
        class="btn btn-sm flex-1 justify-center"
        :class="{ 'btn-primary': selectedType === 'cut' }"
        title="Instant cut (T)"
        data-testid="cut-button"
      >
        ⏹ Cut
      </button>
      
      <!-- Auto button -->
      <button
        @click="quickAuto"
        class="btn btn-sm flex-1 justify-center"
        :class="{ 'btn-primary': selectedType !== 'cut' }"
        title="Auto-transition (A)"
        data-testid="auto-button"
      >
        {{ selectedTransition.icon }} {{ selectedType === 'cut' ? 'Auto' : selectedTransition.name }}
      </button>
      
      <!-- Expand/collapse button -->
      <button
        @click="toggleExpanded"
        class="btn btn-sm"
        :class="{ 'btn-primary': isExpanded }"
        title="More transition options"
      >
        <svg 
          class="w-4 h-4 transition-transform"
          :class="{ 'rotate-180': isExpanded }"
          fill="none" stroke="currentColor" viewBox="0 0 24 24"
        >
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
        </svg>
      </button>
    </div>
    
    <!-- Expanded view - all options -->
    <div v-if="isExpanded" class="mt-3 p-3 bg-r58-bg-tertiary rounded-lg space-y-4">
      <!-- Transition type grid -->
      <div>
        <h4 class="text-xs font-semibold text-r58-text-secondary uppercase tracking-wide mb-2">Transition Type</h4>
        <div class="grid grid-cols-3 gap-2">
          <button
            v-for="transition in transitions"
            :key="transition.type"
            @click="selectTransition(transition.type)"
            class="flex flex-col items-center gap-1 p-2 rounded-lg transition-colors text-xs"
            :class="selectedType === transition.type 
              ? 'bg-r58-accent-primary text-white' 
              : 'bg-r58-bg-secondary hover:bg-r58-accent-primary/20'"
            :title="transition.description"
          >
            <span class="text-lg">{{ transition.icon }}</span>
            <span>{{ transition.name }}</span>
          </button>
        </div>
      </div>
      
      <!-- Duration slider (for transitions that have duration) -->
      <div v-if="selectedTransition.hasDuration">
        <h4 class="text-xs font-semibold text-r58-text-secondary uppercase tracking-wide mb-2">
          Duration: {{ duration }}ms
        </h4>
        
        <!-- Duration presets -->
        <div class="flex gap-2 mb-2">
          <button
            v-for="preset in durationPresets"
            :key="preset.value"
            @click="duration = preset.value"
            class="btn btn-sm flex-1"
            :class="{ 'btn-primary': duration === preset.value }"
          >
            {{ preset.label }}
          </button>
        </div>
        
        <!-- Duration slider -->
        <input
          v-model.number="duration"
          type="range"
          min="100"
          max="3000"
          step="100"
          class="w-full h-2 bg-r58-bg-secondary rounded-lg appearance-none cursor-pointer accent-r58-accent-primary"
        />
      </div>
      
      <!-- Execute button -->
      <button
        @click="executeTransition"
        class="btn btn-primary w-full justify-center"
        data-testid="execute-transition-button"
      >
        {{ selectedTransition.icon }} Execute {{ selectedTransition.name }}
        {{ selectedTransition.hasDuration ? `(${duration}ms)` : '' }}
      </button>
    </div>
  </div>
</template>

