<script setup lang="ts">
import { ref } from 'vue'

const guestName = ref('')
const isConnecting = ref(false)
const isConnected = ref(false)

async function joinAsGuest() {
  if (!guestName.value.trim()) return
  
  isConnecting.value = true
  
  // TODO: Get VDO.ninja guest invite URL from API
  // For now, simulate connection
  await new Promise(resolve => setTimeout(resolve, 1500))
  
  isConnected.value = true
  isConnecting.value = false
}
</script>

<template>
  <div class="min-h-screen bg-r58-bg-primary flex items-center justify-center p-8">
    <div class="card max-w-md w-full">
      <div class="text-center mb-8">
        <h1 class="text-2xl font-bold mb-2">Join R58 Studio</h1>
        <p class="text-r58-text-secondary">Enter your name to join as a remote guest</p>
      </div>
      
      <div v-if="!isConnected" class="space-y-4">
        <div>
          <label class="block text-sm font-medium mb-2">Your Name</label>
          <input
            v-model="guestName"
            type="text"
            placeholder="Enter your name..."
            class="input w-full"
            :disabled="isConnecting"
            @keyup.enter="joinAsGuest"
          />
        </div>
        
        <button
          @click="joinAsGuest"
          :disabled="!guestName.trim() || isConnecting"
          class="btn btn-primary w-full btn-lg"
        >
          <span v-if="isConnecting" class="flex items-center justify-center gap-2">
            <span class="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"></span>
            Connecting...
          </span>
          <span v-else>Join Studio</span>
        </button>
      </div>
      
      <div v-else class="text-center">
        <div class="w-16 h-16 rounded-full bg-r58-accent-success/20 flex items-center justify-center mx-auto mb-4">
          <svg class="w-8 h-8 text-r58-accent-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
          </svg>
        </div>
        <h2 class="text-xl font-semibold mb-2">Connected!</h2>
        <p class="text-r58-text-secondary">You're now connected as {{ guestName }}</p>
      </div>
    </div>
  </div>
</template>

