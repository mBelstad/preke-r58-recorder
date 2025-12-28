<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

const currentTime = ref(new Date())

let timeInterval: number | null = null

onMounted(() => {
  timeInterval = window.setInterval(() => {
    currentTime.value = new Date()
  }, 1000)
})

onUnmounted(() => {
  if (timeInterval) {
    clearInterval(timeInterval)
  }
})

const formattedTime = () => {
  return currentTime.value.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  })
}

const formattedDate = () => {
  return currentTime.value.toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric'
  })
}
</script>

<template>
  <header class="h-10 bg-r58-bg-secondary border-b border-r58-bg-tertiary flex items-center justify-between px-4 text-sm">
    <!-- Left: Device info -->
    <div class="flex items-center gap-4">
      <div class="flex items-center gap-2">
        <span class="w-2 h-2 rounded-full bg-r58-accent-success"></span>
        <span class="text-r58-text-secondary">R58-001</span>
      </div>
    </div>
    
    <!-- Center: Status indicators -->
    <div class="flex items-center gap-6">
      <!-- Inputs -->
      <div class="flex items-center gap-2 text-r58-text-secondary">
        <span>Inputs:</span>
        <div class="flex gap-1">
          <span class="w-4 h-4 rounded bg-r58-accent-success text-[10px] flex items-center justify-center text-white font-bold">1</span>
          <span class="w-4 h-4 rounded bg-r58-accent-success text-[10px] flex items-center justify-center text-white font-bold">2</span>
          <span class="w-4 h-4 rounded bg-r58-bg-tertiary text-[10px] flex items-center justify-center text-r58-text-secondary font-bold">3</span>
          <span class="w-4 h-4 rounded bg-r58-bg-tertiary text-[10px] flex items-center justify-center text-r58-text-secondary font-bold">4</span>
        </div>
      </div>
      
      <!-- Storage -->
      <div class="flex items-center gap-2 text-r58-text-secondary">
        <span>Storage:</span>
        <div class="w-20 h-2 bg-r58-bg-tertiary rounded-full overflow-hidden">
          <div class="h-full bg-r58-accent-success rounded-full" style="width: 35%"></div>
        </div>
        <span class="text-xs">256 GB</span>
      </div>
    </div>
    
    <!-- Right: Time -->
    <div class="flex items-center gap-4 text-r58-text-secondary">
      <span>{{ formattedDate() }}</span>
      <span class="font-mono">{{ formattedTime() }}</span>
    </div>
  </header>
</template>

