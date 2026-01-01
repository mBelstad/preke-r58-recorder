<script setup lang="ts">
/**
 * MixerWorkspace - Main workspace layout for the mixer
 * 
 * Contains:
 * - Sources Panel (left)
 * - Preview/Program View (center)
 * - Scene Strip (bottom)
 */
import { ref } from 'vue'
import { useMixerStore } from '@/stores/mixer'
import { useScenesStore, type Scene } from '@/stores/scenes'
import SourcePanel from './SourcePanel.vue'
import PreviewProgramView from './PreviewProgramView.vue'
import SceneStrip from './SceneStrip.vue'
import VdoNinjaEmbed from './VdoNinjaEmbed.vue'
import type { MixerController } from '@/composables/useMixerController'

const props = defineProps<{
  vdoEmbed?: InstanceType<typeof VdoNinjaEmbed> | null
  controller?: MixerController
}>()

const emit = defineEmits<{
  (e: 'edit-scene', scene: Scene): void
  (e: 'add-scene'): void
}>()

const mixerStore = useMixerStore()
const scenesStore = useScenesStore()

// Panel collapse state
const sourcePanelCollapsed = ref(false)

// Actions
function toggleSourcePanel() {
  sourcePanelCollapsed.value = !sourcePanelCollapsed.value
}

function handleEditScene(scene: Scene) {
  emit('edit-scene', scene)
}

function handleAddScene() {
  emit('add-scene')
}

function handleTake() {
  // Additional logic after take if needed
  console.log('[Workspace] Take executed')
}

function handleCut() {
  // Additional logic after cut if needed
  console.log('[Workspace] Cut executed')
}
</script>

<template>
  <div class="mixer-workspace h-full flex flex-col" data-testid="mixer-workspace">
    <!-- Main Layout -->
    <div class="flex-1 flex gap-4 min-h-0 p-4">
      <!-- Sources Panel (Left) -->
      <aside 
        class="sources-panel flex-shrink-0 transition-all duration-300 overflow-hidden"
        :class="sourcePanelCollapsed ? 'w-12' : 'w-64'"
      >
        <!-- Collapse Toggle -->
        <button 
          @click="toggleSourcePanel"
          class="w-full mb-3 flex items-center justify-between px-3 py-2 bg-r58-bg-tertiary rounded-lg hover:bg-r58-bg-tertiary/80 transition-colors"
        >
          <span v-if="!sourcePanelCollapsed" class="text-sm font-medium">Sources</span>
          <svg 
            class="w-4 h-4 transition-transform" 
            :class="{ 'rotate-180': sourcePanelCollapsed }"
            fill="none" stroke="currentColor" viewBox="0 0 24 24"
          >
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        
        <!-- Panel Content -->
        <div 
          v-show="!sourcePanelCollapsed" 
          class="h-[calc(100%-48px)] overflow-y-auto scrollbar-thin"
        >
          <SourcePanel :vdo-embed="vdoEmbed" :controller="controller" />
        </div>
        
        <!-- Collapsed Icon View -->
        <div v-show="sourcePanelCollapsed" class="space-y-2">
          <div 
            v-for="source in mixerStore.connectedSources.slice(0, 6)" 
            :key="source.id"
            class="w-8 h-8 mx-auto rounded bg-r58-bg-tertiary flex items-center justify-center text-xs"
            :title="source.label"
          >
            {{ source.label.charAt(0) }}
          </div>
        </div>
      </aside>
      
      <!-- Main Content Area -->
      <div class="flex-1 flex flex-col min-w-0">
        <!-- Preview/Program View -->
        <div class="flex-1 min-h-0">
          <PreviewProgramView 
            :vdo-embed="vdoEmbed"
            :controller="controller"
            @take="handleTake"
            @cut="handleCut"
          />
        </div>
        
        <!-- Scene Strip -->
        <div class="mt-4 pt-4 border-t border-r58-bg-tertiary">
          <div class="flex items-center justify-between mb-2">
            <h3 class="text-sm font-medium text-r58-text-secondary">Scenes</h3>
            <div class="flex items-center gap-2 text-xs text-r58-text-secondary">
              <span>Click = Preview</span>
              <span class="opacity-50">|</span>
              <span>Double-click = Live</span>
              <span class="opacity-50">|</span>
              <span>Right-click = Menu</span>
            </div>
          </div>
          <SceneStrip 
            @edit-scene="handleEditScene"
            @add-scene="handleAddScene"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.scrollbar-thin::-webkit-scrollbar {
  width: 4px;
}

.scrollbar-thin::-webkit-scrollbar-track {
  background: transparent;
}

.scrollbar-thin::-webkit-scrollbar-thumb {
  background: var(--r58-bg-tertiary);
  border-radius: 2px;
}
</style>

