<script setup lang="ts">
import { computed } from 'vue'
import { useRecorderStore } from '@/stores/recorder'
import InputPreview from '@/components/shared/InputPreview.vue'

const recorderStore = useRecorderStore()
const inputs = computed(() => recorderStore.inputs)
</script>

<template>
  <div class="h-full grid grid-cols-2 gap-4">
    <div
      v-for="input in inputs"
      :key="input.id"
      class="relative rounded-lg overflow-hidden border-2 transition-all"
      :class="[
        input.isRecording 
          ? 'border-r58-accent-danger' 
          : input.hasSignal 
            ? 'border-r58-bg-tertiary' 
            : 'border-r58-bg-tertiary/50'
      ]"
    >
      <!-- Video preview -->
      <InputPreview
        v-if="input.hasSignal"
        :input-id="input.id"
        class="w-full h-full object-cover"
      />
      
      <!-- No signal placeholder -->
      <div
        v-else
        class="w-full h-full bg-r58-bg-secondary flex items-center justify-center"
      >
        <div class="text-center text-r58-text-secondary">
          <svg class="w-12 h-12 mx-auto mb-2 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
          </svg>
          <p>No Signal</p>
        </div>
      </div>
      
      <!-- Overlay info -->
      <div class="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 to-transparent p-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span
              class="w-2 h-2 rounded-full"
              :class="input.hasSignal ? 'bg-r58-accent-success' : 'bg-r58-text-secondary'"
            ></span>
            <span class="font-medium">{{ input.label }}</span>
          </div>
          
          <div v-if="input.hasSignal" class="flex items-center gap-2 text-sm text-r58-text-secondary">
            <span>{{ input.resolution }}</span>
            <span>{{ input.framerate }}fps</span>
          </div>
        </div>
        
        <!-- Recording indicator -->
        <div v-if="input.isRecording" class="mt-2 flex items-center gap-2 text-r58-accent-danger">
          <span class="w-2 h-2 rounded-full bg-r58-accent-danger animate-recording"></span>
          <span class="text-sm font-medium">REC</span>
        </div>
      </div>
    </div>
  </div>
</template>

