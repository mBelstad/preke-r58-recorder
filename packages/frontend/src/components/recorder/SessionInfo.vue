<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRecorderStore } from '@/stores/recorder'
import SettingsPanel from '@/components/shared/SettingsPanel.vue'

const recorderStore = useRecorderStore()

const currentSession = computed(() => recorderStore.currentSession)
const activeInputs = computed(() => recorderStore.activeInputs)
const isRecording = computed(() => recorderStore.isRecording)

// Settings panel visibility
const showSettings = ref(false)

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}
</script>

<template>
  <div class="space-y-6">
    <!-- Session info -->
    <div v-if="currentSession" class="card">
      <h3 class="text-sm font-semibold text-r58-text-secondary uppercase tracking-wide mb-3">Current Session</h3>
      <div class="space-y-2">
        <div class="flex justify-between">
          <span class="text-r58-text-secondary">Started</span>
          <span>{{ currentSession.startedAt.toLocaleTimeString() }}</span>
        </div>
        <div class="flex justify-between">
          <span class="text-r58-text-secondary">Duration</span>
          <span class="font-mono">{{ recorderStore.formattedDuration }}</span>
        </div>
        <div class="flex justify-between">
          <span class="text-r58-text-secondary">Inputs</span>
          <span>{{ activeInputs.length }} active</span>
        </div>
      </div>
    </div>
    
    <!-- Input status -->
    <div class="card">
      <h3 class="text-sm font-semibold text-r58-text-secondary uppercase tracking-wide mb-3">Input Status</h3>
      <div class="space-y-3">
        <div
          v-for="input in recorderStore.inputs"
          :key="input.id"
          class="flex items-center justify-between py-2 border-b border-r58-bg-tertiary last:border-0"
        >
          <div class="flex items-center gap-2">
            <span
              class="w-2 h-2 rounded-full"
              :class="input.hasSignal ? 'bg-r58-accent-success' : 'bg-r58-text-secondary'"
            ></span>
            <span :class="input.hasSignal ? '' : 'text-r58-text-secondary'">{{ input.label }}</span>
          </div>
          
          <div v-if="input.hasSignal" class="text-sm text-r58-text-secondary">
            <span v-if="input.isRecording" class="text-r58-accent-danger">
              {{ formatBytes(input.bytesWritten) }}
            </span>
            <span v-else>{{ input.resolution }}</span>
          </div>
          <span v-else class="text-sm text-r58-text-secondary">No signal</span>
        </div>
      </div>
    </div>
    
    <!-- Quick actions -->
    <div class="card">
      <h3 class="text-sm font-semibold text-r58-text-secondary uppercase tracking-wide mb-3">Quick Actions</h3>
      <div class="space-y-2">
        <button 
          class="btn w-full justify-center disabled:opacity-50 disabled:cursor-not-allowed group relative" 
          :disabled="isRecording"
          :title="isRecording ? 'Cannot configure while recording' : 'Open input configuration'"
        >
          Configure Inputs
          <!-- Disabled reason tooltip -->
          <span 
            v-if="isRecording"
            class="absolute -top-8 left-1/2 -translate-x-1/2 px-2 py-1 bg-r58-bg-tertiary text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none"
          >
            Stop recording first
          </span>
        </button>
        <button 
          @click="showSettings = !showSettings"
          class="btn w-full justify-center"
        >
          {{ showSettings ? 'Hide Settings' : 'Interface Settings' }}
        </button>
      </div>
    </div>
    
    <!-- Settings Panel (collapsible) -->
    <Transition name="slide-fade">
      <div v-if="showSettings" class="card">
        <SettingsPanel />
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.slide-fade-enter-active {
  transition: all 0.2s ease-out;
}
.slide-fade-leave-active {
  transition: all 0.15s ease-in;
}
.slide-fade-enter-from,
.slide-fade-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}
</style>

