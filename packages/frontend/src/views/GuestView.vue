<script setup lang="ts">
import { ref } from 'vue'
import { apiPost, buildApiUrl } from '@/lib/api'

const guestName = ref('')
const isConnecting = ref(false)
const isConnected = ref(false)
const vdoNinjaUrl = ref<string | null>(null)
const error = ref<string | null>(null)
const iframeRef = ref<HTMLIFrameElement | null>(null)

// Check if we should embed or open in new tab
const embedMode = ref(true)

interface VdoUrlResponse {
  url: string
  profile: string
  room: string
  css_url: string
}

async function joinAsGuest() {
  if (!guestName.value.trim()) return
  
  isConnecting.value = true
  error.value = null
  
  try {
    // Call the API to get the VDO.ninja guest invite URL
    const response = await apiPost<VdoUrlResponse>(
      buildApiUrl('/api/v1/vdoninja/url'),
      {
        profile: 'guestInvite',
        guest_name: guestName.value.trim(),
      }
    )
    
    if (response.url) {
      vdoNinjaUrl.value = response.url
      isConnected.value = true
      
      // If not embedding, open in new tab
      if (!embedMode.value) {
        window.open(response.url, '_blank')
      }
    } else {
      error.value = 'Failed to get VDO.ninja URL'
    }
  } catch (e) {
    console.error('Failed to join as guest:', e)
    error.value = e instanceof Error ? e.message : 'Failed to connect'
  } finally {
    isConnecting.value = false
  }
}

function disconnect() {
  isConnected.value = false
  vdoNinjaUrl.value = null
  guestName.value = ''
}

function openInNewTab() {
  if (vdoNinjaUrl.value) {
    window.open(vdoNinjaUrl.value, '_blank')
  }
}
</script>

<template>
  <div class="min-h-screen bg-r58-bg-primary flex items-center justify-center p-4">
    <!-- Join Form -->
    <div v-if="!isConnected" class="card max-w-md w-full">
      <div class="text-center mb-8">
        <h1 class="text-2xl font-bold mb-2">Join Preke Studio</h1>
        <p class="text-r58-text-secondary">Enter your name to join as a remote guest</p>
      </div>
      
      <div class="space-y-4">
        <div>
          <label class="block text-sm font-medium mb-2" for="guest-name">Your Name</label>
          <input
            id="guest-name"
            v-model="guestName"
            type="text"
            placeholder="Enter your name..."
            class="input w-full"
            :disabled="isConnecting"
            @keyup.enter="joinAsGuest"
          />
        </div>
        
        <div class="flex items-center gap-2">
          <input
            id="embed-mode"
            v-model="embedMode"
            type="checkbox"
            class="w-4 h-4 rounded border-gray-600 bg-gray-700 text-r58-accent-primary focus:ring-r58-accent-primary"
          />
          <label for="embed-mode" class="text-sm text-r58-text-secondary">
            Stay on this page (embed video)
          </label>
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
        
        <p v-if="error" class="text-red-400 text-sm text-center">
          {{ error }}
        </p>
      </div>
    </div>
    
    <!-- Connected View with VDO.ninja Embed -->
    <div v-else class="w-full h-full flex flex-col">
      <!-- Header bar -->
      <div class="bg-r58-bg-secondary border-b border-r58-bg-tertiary p-4 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="w-3 h-3 rounded-full bg-green-500 animate-pulse"></div>
          <span class="font-medium">Connected as {{ guestName }}</span>
        </div>
        <div class="flex items-center gap-2">
          <button
            v-if="embedMode && vdoNinjaUrl"
            @click="openInNewTab"
            class="btn btn-sm btn-secondary"
            title="Open in new tab"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
            </svg>
            <span class="ml-1">New Tab</span>
          </button>
          <button
            @click="disconnect"
            class="btn btn-sm btn-danger"
          >
            Disconnect
          </button>
        </div>
      </div>
      
      <!-- VDO.ninja iframe (embedded mode) -->
      <div v-if="embedMode && vdoNinjaUrl" class="flex-1 bg-black">
        <iframe
          ref="iframeRef"
          :src="vdoNinjaUrl"
          class="w-full h-full border-0"
          allow="camera; microphone; display-capture; autoplay; clipboard-write"
          allowfullscreen
        />
      </div>
      
      <!-- Non-embed success message -->
      <div v-else class="flex-1 flex items-center justify-center">
        <div class="text-center">
          <div class="w-20 h-20 rounded-full bg-r58-accent-success/20 flex items-center justify-center mx-auto mb-6">
            <svg class="w-10 h-10 text-r58-accent-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
            </svg>
          </div>
          <h2 class="text-2xl font-semibold mb-2">You're Connected!</h2>
          <p class="text-r58-text-secondary mb-6">
            VDO.ninja opened in a new tab. You can close this page.
          </p>
          <button
            v-if="vdoNinjaUrl"
            @click="openInNewTab"
            class="btn btn-primary"
          >
            Open VDO.ninja Again
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

