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
      :class="hasSignal ? 'bg-preke-green' : 'bg-preke-text-dim'"
    ></span>
    <span v-if="label" class="text-sm" :class="hasSignal ? '' : 'text-preke-text-dim'">
      {{ label }}
    </span>
  </div>
</template>

