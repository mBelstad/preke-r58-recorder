<script setup lang="ts">
defineProps<{
  hasSignal: boolean
  label?: string
}>()
</script>

<template>
  <div class="flex items-center gap-2">
    <span 
      class="w-2 h-2 rounded-full"
      :class="hasSignal ? 'bg-r58-accent-success' : 'bg-r58-text-secondary'"
    ></span>
    <span v-if="label" class="text-sm" :class="hasSignal ? '' : 'text-r58-text-secondary'">
      {{ label }}
    </span>
  </div>
</template>

