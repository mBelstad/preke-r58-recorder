<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRecorderStore } from '@/stores/recorder'
import RecorderControls from '@/components/recorder/RecorderControls.vue'
import InputGrid from '@/components/recorder/InputGrid.vue'
import SessionInfo from '@/components/recorder/SessionInfo.vue'

const recorderStore = useRecorderStore()

const isRecording = computed(() => recorderStore.status === 'recording')
</script>

<template>
  <div class="h-full flex flex-col">
    <!-- Header -->
    <header class="flex items-center justify-between px-6 py-4 border-b border-r58-bg-tertiary bg-r58-bg-secondary">
      <div class="flex items-center gap-4">
        <div class="flex items-center gap-2">
          <span 
            class="w-3 h-3 rounded-full"
            :class="isRecording ? 'bg-r58-accent-danger animate-recording' : 'bg-r58-bg-tertiary'"
          ></span>
          <span class="text-xl font-semibold">Recorder</span>
        </div>
        <span v-if="isRecording" class="badge badge-danger">RECORDING</span>
      </div>
      
      <RecorderControls />
    </header>
    
    <!-- Main content -->
    <div class="flex-1 flex overflow-hidden">
      <!-- Input grid -->
      <div class="flex-1 p-4">
        <InputGrid />
      </div>
      
      <!-- Sidebar -->
      <aside class="w-80 border-l border-r58-bg-tertiary bg-r58-bg-secondary p-4 overflow-y-auto">
        <SessionInfo />
      </aside>
    </div>
  </div>
</template>

