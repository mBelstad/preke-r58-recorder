<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { r58Api } from '@/lib/api'

const props = defineProps<{
  token: string
  status: any
  currentSlideIndex: number
  isRecording: boolean
  teleprompterSpeed: number
  teleprompterScript?: string
}>()

const emit = defineEmits<{
  (e: 'start-recording'): void
  (e: 'stop-recording'): void
  (e: 'prev-slide'): void
  (e: 'next-slide'): void
  (e: 'update-speed', speed: number): void
  (e: 'update-script', script: string): void
}>()

const localScript = ref(props.teleprompterScript || '')
const isEditingScript = ref(false)
const textSize = ref(3) // 1-5 scale
const isSavingScript = ref(false)

// Sync local script when prop changes (if not editing)
watch(() => props.teleprompterScript, (newScript) => {
  if (!isEditingScript.value && newScript !== undefined) {
    localScript.value = newScript
  }
})

const currentGraphic = computed(() => {
  if (!props.status?.project?.graphics) return null
  return props.status.project.graphics[props.currentSlideIndex]
})

const hasGraphics = computed(() => {
  return props.status?.project?.graphics && props.status.project.graphics.length > 0
})

async function saveScript() {
  isSavingScript.value = true
  try {
    await r58Api.wordpress.updateTeleprompterScript(props.token, localScript.value)
    isEditingScript.value = false
    emit('update-script', localScript.value)
  } catch (e) {
    console.error('Failed to save script:', e)
    alert('Failed to save script')
  } finally {
    isSavingScript.value = false
  }
}

async function scrollTeleprompter(direction: 'up' | 'down') {
  try {
    // TODO: Add backend endpoint for this
    // await r58Api.wordpress.scrollTeleprompter(props.token, direction)
    console.log('Scroll', direction)
  } catch (e) {
    console.error('Failed to scroll:', e)
  }
}

async function jumpTo(position: 'top' | 'bottom') {
  try {
    // TODO: Add backend endpoint for this
    // await r58Api.wordpress.jumpTeleprompter(props.token, position)
    console.log('Jump to', position)
  } catch (e) {
    console.error('Failed to jump:', e)
  }
}

async function updateTextSize(newSize: number) {
  textSize.value = newSize
  try {
    // TODO: Add backend endpoint for this
    // await r58Api.wordpress.setTeleprompterTextSize(props.token, newSize)
    console.log('Text size', newSize)
  } catch (e) {
    console.error('Failed to set text size:', e)
  }
}
</script>

<template>
  <div class="talking-head-portal space-y-6">
    <!-- Recording Controls -->
    <div class="glass-card">
      <h2 class="text-lg font-semibold mb-4 px-1">Recording Controls</h2>
      
      <div v-if="!isRecording" class="text-center py-2">
        <button
          @click="emit('start-recording')"
          class="record-button touch-target"
        >
          <div class="record-button-inner">
            <svg class="w-12 h-12" fill="currentColor" viewBox="0 0 20 20">
              <circle cx="10" cy="10" r="8"/>
            </svg>
          </div>
          <span class="mt-3 block text-lg font-semibold">Start Recording</span>
        </button>
      </div>
      
      <div v-else class="text-center py-2">
        <div class="recording-indicator mb-6">
          <div class="recording-dot"></div>
          <span class="text-xl font-medium text-preke-red-light">Recording in progress</span>
        </div>
        <button
          @click="emit('stop-recording')"
          class="btn-v2 btn-v2--danger w-full touch-target text-lg font-medium"
        >
          <svg class="w-6 h-6 mr-2" fill="currentColor" viewBox="0 0 20 20">
            <rect x="6" y="6" width="8" height="8" rx="1"/>
          </svg>
          Stop Recording
        </button>
      </div>
    </div>
    
    <!-- Teleprompter Controls -->
    <div class="glass-card">
      <div class="flex items-center justify-between mb-4 px-1">
        <h2 class="text-lg font-semibold">Teleprompter</h2>
        <div class="flex gap-2">
          <button 
            @click="jumpTo('top')"
            class="btn-v2 btn-v2--glass btn-sm"
            title="Jump to Top"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 10l7-7m0 0l7 7m-7-7v18"/>
            </svg>
          </button>
          <button 
            @click="jumpTo('bottom')"
            class="btn-v2 btn-v2--glass btn-sm"
            title="Jump to Bottom"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 14l-7 7m0 0l-7-7m7 7V3"/>
            </svg>
          </button>
        </div>
      </div>
      
      <div class="space-y-6">
        <!-- Speed Control -->
        <div class="p-4 bg-preke-bg-elevated rounded-lg">
          <div class="flex justify-between items-center mb-2">
            <span class="text-preke-text-dim font-medium">Scroll Speed</span>
            <span class="font-mono font-bold text-preke-gold">{{ teleprompterSpeed }}%</span>
          </div>
          
          <input 
            type="range" 
            min="1" 
            max="100" 
            :value="teleprompterSpeed" 
            @input="e => emit('update-speed', parseInt((e.target as HTMLInputElement).value))"
            class="w-full h-3 bg-preke-bg-surface rounded-lg appearance-none cursor-pointer accent-preke-gold"
          />
          
          <div class="flex justify-between mt-3">
            <button
              @click="emit('update-speed', Math.max(1, teleprompterSpeed - 5))"
              class="btn-v2 btn-v2--glass btn-sm touch-target w-12"
            >
              -
            </button>
            <button
              @click="emit('update-speed', Math.max(1, teleprompterSpeed + 5))"
              class="btn-v2 btn-v2--glass btn-sm touch-target w-12"
            >
              +
            </button>
          </div>
        </div>
        
        <!-- Manual Scroll -->
        <div class="grid grid-cols-2 gap-3">
          <button
            @click="scrollTeleprompter('up')"
            class="btn-v2 btn-v2--secondary touch-target flex justify-center items-center py-4"
          >
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7"/>
            </svg>
            Scroll Up
          </button>
          <button
            @click="scrollTeleprompter('down')"
            class="btn-v2 btn-v2--secondary touch-target flex justify-center items-center py-4"
          >
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
            </svg>
            Scroll Down
          </button>
        </div>
        
        <!-- Text Size -->
        <div class="flex items-center justify-between p-3 bg-preke-bg-elevated rounded-lg">
          <span class="text-preke-text-dim font-medium">Text Size</span>
          <div class="flex items-center gap-1 bg-preke-bg-surface rounded p-1">
            <button 
              v-for="size in 5" 
              :key="size"
              @click="updateTextSize(size)"
              class="w-8 h-8 rounded flex items-center justify-center transition-colors"
              :class="textSize === size ? 'bg-preke-gold text-preke-bg-base' : 'text-preke-text-muted hover:bg-white/10'"
            >
              <span :style="{ fontSize: `${0.7 + (size * 0.15)}rem` }">A</span>
            </button>
          </div>
        </div>
        
        <!-- Script Editor -->
        <div class="border-t border-preke-border pt-4">
          <div class="flex justify-between items-center mb-3">
            <h3 class="font-medium text-preke-text-dim">Script</h3>
            <button 
              v-if="!isEditingScript"
              @click="isEditingScript = true"
              class="text-preke-gold text-sm font-medium hover:underline px-2 py-1"
            >
              Edit Script
            </button>
            <div v-else class="flex gap-2">
              <button 
                @click="isEditingScript = false; localScript = props.teleprompterScript || ''"
                class="text-preke-text-muted text-xs hover:text-white px-2 py-1"
              >
                Cancel
              </button>
              <button 
                @click="saveScript"
                :disabled="isSavingScript"
                class="text-preke-gold text-xs font-bold hover:text-preke-gold-light px-2 py-1 bg-preke-gold-glow rounded"
              >
                {{ isSavingScript ? 'Saving...' : 'Save' }}
              </button>
            </div>
          </div>
          
          <div v-if="isEditingScript">
            <textarea
              v-model="localScript"
              rows="8"
              class="w-full bg-preke-bg-elevated border border-preke-border rounded-lg p-3 text-preke-text-primary focus:border-preke-gold focus:outline-none resize-y"
              placeholder="Enter your script here..."
            ></textarea>
          </div>
          <div v-else class="bg-preke-bg-elevated rounded-lg p-4 max-h-40 overflow-y-auto border border-preke-border/50">
            <p class="whitespace-pre-wrap text-sm text-preke-text-dim">{{ localScript || 'No script loaded.' }}</p>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Presentation Controls (if graphics exist) -->
    <div v-if="hasGraphics" class="glass-card">
      <h2 class="text-lg font-semibold mb-3 px-1">Presentation</h2>
      
      <div class="graphic-preview mb-4">
        <img 
          v-if="currentGraphic" 
          :src="currentGraphic.url" 
          :alt="currentGraphic.filename" 
          class="w-full h-auto object-contain bg-black/50" 
        />
        <div v-else class="w-full aspect-video flex items-center justify-center bg-black/50 text-preke-text-muted">
          No preview available
        </div>
        
        <div class="slide-indicator">
          {{ currentSlideIndex + 1 }} / {{ status.project.graphics.length }}
        </div>
      </div>
      
      <div class="flex items-center gap-3">
        <button
          @click="emit('prev-slide')"
          :disabled="currentSlideIndex === 0"
          class="btn-v2 btn-v2--glass flex-1 touch-target text-lg py-4"
        >
          <svg class="w-6 h-6 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
          </svg>
          Previous
        </button>
        <button
          @click="emit('next-slide')"
          :disabled="currentSlideIndex >= status.project.graphics.length - 1"
          class="btn-v2 btn-v2--glass flex-1 touch-target text-lg py-4"
        >
          Next
          <svg class="w-6 h-6 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
@import '@/styles/design-system-v2.css';

/* Range Input Styling */
input[type=range] {
  -webkit-appearance: none;
  background: transparent;
}

input[type=range]::-webkit-slider-thumb {
  -webkit-appearance: none;
  height: 24px;
  width: 24px;
  border-radius: 50%;
  background: var(--preke-gold);
  cursor: pointer;
  margin-top: -10px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3);
}

input[type=range]::-webkit-slider-runnable-track {
  width: 100%;
  height: 4px;
  cursor: pointer;
  background: var(--preke-border);
  border-radius: 2px;
}

.graphic-preview {
  position: relative;
  border-radius: var(--preke-radius-lg);
  overflow: hidden;
  background: var(--preke-bg-elevated);
  box-shadow: inset 0 0 0 1px var(--preke-border);
}

.slide-indicator {
  position: absolute;
  bottom: 0.75rem;
  right: 0.75rem;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(4px);
  color: white;
  padding: 0.25rem 0.75rem;
  border-radius: var(--preke-radius-md);
  font-size: 0.875rem;
  font-weight: 600;
}

/* Touch-friendly buttons */
.touch-target {
  min-height: 56px;
}

/* Record Button */
.record-button {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: none;
  border: none;
  cursor: pointer;
  padding: 1rem;
  width: 100%;
  color: var(--preke-text-primary);
  transition: transform 0.2s ease;
  user-select: none;
}

.record-button:active {
  transform: scale(0.95);
}

.record-button-inner {
  width: 120px;
  height: 120px;
  border-radius: 50%;
  background: linear-gradient(145deg, #dc2626, #b91c1c);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  box-shadow: 
    0 4px 20px rgba(220, 38, 38, 0.4),
    inset 0 2px 4px rgba(255, 255, 255, 0.2);
  transition: all 0.3s ease;
}

.record-button:hover .record-button-inner {
  box-shadow: 
    0 6px 30px rgba(220, 38, 38, 0.6),
    inset 0 2px 4px rgba(255, 255, 255, 0.3);
}

/* Recording Indicator */
.recording-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
}

.recording-dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: var(--preke-red);
  animation: pulse 1.5s ease-in-out infinite;
  box-shadow: 0 0 10px var(--preke-red-bg);
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.2); }
}
</style>
