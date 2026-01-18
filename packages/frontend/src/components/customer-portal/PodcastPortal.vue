<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  status: any
  currentSlideIndex: number
  isRecording: boolean
}>()

const emit = defineEmits<{
  (e: 'start-recording'): void
  (e: 'stop-recording'): void
  (e: 'prev-slide'): void
  (e: 'next-slide'): void
}>()

const currentGraphic = computed(() => {
  if (!props.status?.project?.graphics) return null
  return props.status.project.graphics[props.currentSlideIndex]
})

const hasGraphics = computed(() => {
  return props.status?.project?.graphics && props.status.project.graphics.length > 0
})
</script>

<template>
  <div class="podcast-portal space-y-6">
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
    
    <!-- Upload Link -->
    <div class="glass-panel p-4 text-center">
      <p class="text-preke-text-muted mb-3 text-sm">Need to upload slides or documents?</p>
      <a 
        href="https://preke.no/wp-login.php" 
        target="_blank" 
        class="btn-v2 btn-v2--secondary w-full justify-center touch-target"
      >
        <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
        </svg>
        Upload Files
      </a>
    </div>
  </div>
</template>

<style scoped>
@import '@/styles/design-system-v2.css';

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
  min-height: 56px; /* Larger for mobile thumbs */
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
