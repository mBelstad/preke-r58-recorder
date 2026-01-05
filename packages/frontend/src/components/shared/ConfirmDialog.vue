<script setup lang="ts">
import { ref } from 'vue'
import BaseModal from './BaseModal.vue'

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

const modalRef = ref<InstanceType<typeof BaseModal> | null>(null)

function open() {
  modalRef.value?.open()
}

function close() {
  modalRef.value?.close()
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
  <BaseModal 
    ref="modalRef" 
    :title="title"
    @close="cancel"
  >
    <p class="text-r58-text-secondary">{{ message }}</p>
    
    <template #footer>
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
    </template>
  </BaseModal>
</template>


