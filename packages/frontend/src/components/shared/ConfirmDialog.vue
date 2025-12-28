<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  title: string
  message: string
  confirmText?: string
  cancelText?: string
  danger?: boolean
}>()

const emit = defineEmits<{
  (e: 'confirm'): void
  (e: 'cancel'): void
}>()

const isOpen = ref(false)

function open() {
  isOpen.value = true
}

function close() {
  isOpen.value = false
}

function confirm() {
  emit('confirm')
  close()
}

function cancel() {
  emit('cancel')
  close()
}

defineExpose({ open, close })
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div 
        v-if="isOpen"
        class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50"
        @click.self="cancel"
      >
        <div class="bg-r58-bg-secondary rounded-lg shadow-xl max-w-md w-full p-6">
          <h2 class="text-lg font-semibold mb-2">{{ title }}</h2>
          <p class="text-r58-text-secondary mb-6">{{ message }}</p>
          
          <div class="flex justify-end gap-3">
            <button 
              @click="cancel"
              class="btn"
            >
              {{ cancelText || 'Cancel' }}
            </button>
            <button 
              @click="confirm"
              class="btn"
              :class="danger ? 'btn-danger' : 'btn-primary'"
            >
              {{ confirmText || 'Confirm' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

