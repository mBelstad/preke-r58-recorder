<script setup lang="ts">
import { computed } from 'vue'
import { useRecorderStore } from '@/stores/recorder'

const recorderStore = useRecorderStore()

const isRecording = computed(() => recorderStore.status === 'recording')
const isStarting = computed(() => recorderStore.status === 'starting')
const isStopping = computed(() => recorderStore.status === 'stopping')
const duration = computed(() => recorderStore.formattedDuration)

async function toggleRecording() {
  if (isRecording.value) {
    await recorderStore.stopRecording()
  } else {
    await recorderStore.startRecording()
  }
}
</script>

<template>
  <div class="flex items-center gap-4">
    <!-- Duration display -->
    <div v-if="isRecording" class="font-mono text-xl text-r58-accent-danger">
      {{ duration }}
    </div>
    
    <!-- Record button -->
    <button
      @click="toggleRecording"
      :disabled="isStarting || isStopping"
      class="flex items-center gap-2 px-6 py-2 rounded-lg font-medium transition-all"
      :class="[
        isRecording 
          ? 'bg-r58-accent-danger hover:bg-red-600 text-white' 
          : 'bg-r58-accent-success hover:bg-green-600 text-white'
      ]"
    >
      <span v-if="isStarting || isStopping" class="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"></span>
      <template v-else>
        <span v-if="isRecording" class="w-3 h-3 bg-white rounded-sm"></span>
        <span v-else class="w-3 h-3 bg-white rounded-full"></span>
      </template>
      <span>{{ isRecording ? 'Stop' : 'Start Recording' }}</span>
    </button>
  </div>
</template>

