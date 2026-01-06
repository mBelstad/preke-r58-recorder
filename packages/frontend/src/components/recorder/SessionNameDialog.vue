<script setup lang="ts">
/**
 * Session Name Dialog
 * 
 * Optional prompt to name a recording session before starting.
 * Suggests a default name based on date/time.
 */
import { ref, computed, watch } from 'vue'

const props = defineProps<{
  open: boolean
  suggestedName?: string
}>()

const emit = defineEmits<{
  (e: 'confirm', sessionName: string): void
  (e: 'cancel'): void
  (e: 'skip'): void
}>()

const sessionName = ref('')
const inputRef = ref<HTMLInputElement | null>(null)

// Generate default suggested name
const defaultSuggestedName = computed(() => {
  const now = new Date()
  const date = now.toLocaleDateString('en-CA') // YYYY-MM-DD format
  const time = now.toLocaleTimeString('en-US', { 
    hour: '2-digit', 
    minute: '2-digit',
    hour12: false 
  }).replace(':', '')
  return `Recording_${date}_${time}`
})

// Use provided suggestion or default
const suggestion = computed(() => props.suggestedName || defaultSuggestedName.value)

// When dialog opens, set suggestion and focus input
watch(() => props.open, (isOpen) => {
  if (isOpen) {
    sessionName.value = suggestion.value
    // Focus and select text after next tick
    setTimeout(() => {
      inputRef.value?.focus()
      inputRef.value?.select()
    }, 100)
  }
})

function handleConfirm() {
  emit('confirm', sessionName.value.trim() || suggestion.value)
}

function handleSkip() {
  emit('skip')
}

function handleCancel() {
  emit('cancel')
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter') {
    handleConfirm()
  } else if (event.key === 'Escape') {
    handleCancel()
  }
}
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div 
        v-if="open"
        class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50"
        @click.self="handleCancel"
        @keydown="handleKeydown"
      >
        <div class="bg-preke-bg-elevated rounded-lg shadow-xl max-w-md w-full p-6">
          <h2 class="text-lg font-semibold mb-2">Name This Recording</h2>
          <p class="text-preke-text-dim text-sm mb-4">
            Give your recording a name to find it easily later (optional).
          </p>
          
          <!-- Session name input -->
          <input
            ref="inputRef"
            v-model="sessionName"
            type="text"
            :placeholder="suggestion"
            class="w-full px-4 py-2 bg-preke-bg-surface border border-preke-bg-surface rounded-lg text-preke-text placeholder-preke-text-dim focus:outline-none focus:ring-2 focus:ring-preke-gold"
          />
          
          <p class="text-xs text-preke-text-dim mt-2">
            Suggested: {{ suggestion }}
          </p>
          
          <div class="flex justify-between mt-6">
            <button 
              @click="handleSkip"
              class="text-sm text-preke-text-dim hover:text-preke-text transition-colors"
            >
              Skip (use default)
            </button>
            
            <div class="flex gap-3">
              <button 
                @click="handleCancel"
                class="btn"
              >
                Cancel
              </button>
              <button 
                @click="handleConfirm"
                class="btn btn-primary"
              >
                Start Recording
              </button>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>

