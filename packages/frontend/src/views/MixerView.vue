<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useMixerStore } from '@/stores/mixer'
import VdoNinjaEmbed from '@/components/mixer/VdoNinjaEmbed.vue'
import SourcePanel from '@/components/mixer/SourcePanel.vue'

const mixerStore = useMixerStore()
const vdoEmbedRef = ref<InstanceType<typeof VdoNinjaEmbed> | null>(null)

const isLive = computed(() => mixerStore.isLive)
</script>

<template>
  <div class="h-full flex flex-col">
    <!-- Header -->
    <header class="flex items-center justify-between px-6 py-4 border-b border-r58-bg-tertiary bg-r58-bg-secondary">
      <div class="flex items-center gap-4">
        <div class="flex items-center gap-2">
          <span 
            class="w-3 h-3 rounded-full"
            :class="isLive ? 'bg-r58-accent-danger animate-recording' : 'bg-r58-bg-tertiary'"
          ></span>
          <span class="text-xl font-semibold text-r58-mixer">Mixer</span>
        </div>
        <span v-if="isLive" class="badge badge-danger">ON AIR</span>
      </div>
      
      <div class="flex items-center gap-4">
        <button class="btn" @click="mixerStore.toggleLive">
          {{ isLive ? 'End Session' : 'Go Live' }}
        </button>
      </div>
    </header>
    
    <!-- Main content -->
    <div class="flex-1 flex overflow-hidden">
      <!-- VDO.ninja embed -->
      <div class="flex-1 p-4">
        <VdoNinjaEmbed 
          ref="vdoEmbedRef"
          profile="director"
          class="h-full"
        />
      </div>
      
      <!-- Source panel -->
      <aside class="w-80 border-l border-r58-bg-tertiary bg-r58-bg-secondary p-4 overflow-y-auto">
        <SourcePanel />
      </aside>
    </div>
  </div>
</template>

