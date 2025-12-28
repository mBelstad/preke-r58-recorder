<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useMixerStore } from '@/stores/mixer'
import { useKeyboardShortcuts } from '@/composables/useKeyboardShortcuts'
import { toast } from '@/composables/useToast'
import VdoNinjaEmbed from '@/components/mixer/VdoNinjaEmbed.vue'
import SourcePanel from '@/components/mixer/SourcePanel.vue'

const mixerStore = useMixerStore()
const { register } = useKeyboardShortcuts()
const vdoEmbedRef = ref<InstanceType<typeof VdoNinjaEmbed> | null>(null)

const isLive = computed(() => mixerStore.isLive)

// Track registered shortcuts for cleanup
const unregisterFns: (() => void)[] = []

onMounted(() => {
  // Register scene shortcuts (1-9)
  for (let i = 1; i <= 9; i++) {
    const unregister = register({
      key: String(i),
      description: `Switch to scene ${i}`,
      action: () => switchToScene(i),
      context: 'mixer',
    })
    unregisterFns.push(unregister)
  }
  
  // T for transition/cut
  unregisterFns.push(register({
    key: 't',
    description: 'Cut to preview (transition)',
    action: () => performTransition(),
    context: 'mixer',
  }))
  
  // A for auto-transition
  unregisterFns.push(register({
    key: 'a',
    description: 'Auto-transition with fade',
    action: () => performAutoTransition(),
    context: 'mixer',
  }))
  
  // Tab to cycle sources
  unregisterFns.push(register({
    key: 'Tab',
    description: 'Cycle through sources',
    action: () => cyclePreviewSource(),
    context: 'mixer',
  }))
  
  // G for Go Live toggle
  unregisterFns.push(register({
    key: 'g',
    description: 'Toggle Go Live',
    action: () => {
      mixerStore.toggleLive()
      toast.info(mixerStore.isLive ? 'Session started' : 'Session ended')
    },
    context: 'mixer',
  }))
})

onUnmounted(() => {
  unregisterFns.forEach(fn => fn())
})

function switchToScene(sceneNumber: number) {
  const sceneId = `scene-${sceneNumber}`
  mixerStore.setScene(sceneId)
  
  // Send command to VDO.ninja if embedded
  if (vdoEmbedRef.value) {
    vdoEmbedRef.value.sendCommand('changeScene', { scene: sceneNumber })
  }
  
  toast.info(`Scene ${sceneNumber}`)
}

function performTransition() {
  // Instant cut to preview
  if (mixerStore.previewSource) {
    mixerStore.setProgram(mixerStore.previewSource)
    toast.info('Cut')
  }
}

function performAutoTransition() {
  // Auto-transition with fade
  if (mixerStore.previewSource) {
    // Send transition command to VDO.ninja
    if (vdoEmbedRef.value) {
      vdoEmbedRef.value.sendCommand('transition', { type: 'fade', duration: 500 })
    }
    mixerStore.setProgram(mixerStore.previewSource)
    toast.info('Fade')
  }
}

function cyclePreviewSource() {
  const sources = mixerStore.activeSources
  if (sources.length === 0) return
  
  const currentIndex = sources.findIndex(s => s.id === mixerStore.previewSource)
  const nextIndex = (currentIndex + 1) % sources.length
  mixerStore.setPreview(sources[nextIndex].id)
}
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

