<script setup lang="ts">
/**
 * InviteLinks - Generate and share guest invite links
 * 
 * Creates VDO.ninja invite URLs for remote guests to join the room.
 */
import { ref, computed } from 'vue'
import { buildGuestInviteUrl, VDO_ROOM } from '@/lib/vdoninja'
import { toast } from '@/composables/useToast'

// State
const guestName = ref('')
const showAdvanced = ref(false)
const enableVideo = ref(true)
const enableAudio = ref(true)

// Generated link
const inviteLink = computed(() => {
  if (!guestName.value.trim()) return ''
  return buildGuestInviteUrl(guestName.value.trim())
})

// Copy link to clipboard
function copyLink() {
  if (!inviteLink.value) {
    toast.error('Enter a guest name first')
    return
  }
  
  navigator.clipboard.writeText(inviteLink.value)
  toast.success('Invite link copied!')
}

// Open link in new tab (for testing)
function openLink() {
  if (!inviteLink.value) {
    toast.error('Enter a guest name first')
    return
  }
  
  window.open(inviteLink.value, '_blank')
}

// Share via native share API if available
async function shareLink() {
  if (!inviteLink.value) {
    toast.error('Enter a guest name first')
    return
  }
  
  if (navigator.share) {
    try {
      await navigator.share({
        title: `Join ${VDO_ROOM} as ${guestName.value}`,
        text: `Click to join the video call as ${guestName.value}`,
        url: inviteLink.value
      })
    } catch (err) {
      // User cancelled or error
      if ((err as Error).name !== 'AbortError') {
        copyLink() // Fallback to copy
      }
    }
  } else {
    copyLink()
  }
}

// QR Code generation (simple data URL)
const qrCodeUrl = computed(() => {
  if (!inviteLink.value) return ''
  // Use a free QR code API
  return `https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=${encodeURIComponent(inviteLink.value)}`
})
</script>

<template>
  <div class="invite-links space-y-3" data-testid="invite-links">
    <!-- Guest Name Input -->
    <div>
      <label class="block text-xs text-r58-text-secondary mb-1">Guest Name</label>
      <input 
        v-model="guestName"
        type="text"
        placeholder="e.g., John Smith"
        class="w-full px-3 py-2 text-sm bg-r58-bg-tertiary border border-r58-bg-tertiary rounded-lg focus:border-r58-accent-primary focus:outline-none"
      />
    </div>
    
    <!-- Generated Link -->
    <div v-if="inviteLink" class="space-y-2">
      <div class="p-2 bg-r58-bg-tertiary rounded-lg">
        <code class="text-xs text-r58-text-secondary break-all block">
          {{ inviteLink }}
        </code>
      </div>
      
      <!-- Action Buttons -->
      <div class="flex gap-2">
        <button 
          @click="copyLink"
          class="flex-1 btn btn-sm btn-primary"
        >
          <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
          </svg>
          Copy
        </button>
        
        <button 
          @click="shareLink"
          class="btn btn-sm"
          title="Share"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
          </svg>
        </button>
        
        <button 
          @click="openLink"
          class="btn btn-sm"
          title="Open in new tab"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
          </svg>
        </button>
      </div>
    </div>
    
    <!-- Advanced Options Toggle -->
    <button 
      @click="showAdvanced = !showAdvanced"
      class="w-full text-xs text-r58-text-secondary hover:text-r58-text-primary flex items-center justify-center gap-1"
    >
      <span>{{ showAdvanced ? 'Hide' : 'Show' }} options</span>
      <svg 
        class="w-3 h-3 transition-transform" 
        :class="{ 'rotate-180': showAdvanced }"
        fill="none" stroke="currentColor" viewBox="0 0 24 24"
      >
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
      </svg>
    </button>
    
    <!-- Advanced Options -->
    <div v-if="showAdvanced" class="space-y-2 p-3 bg-r58-bg-tertiary rounded-lg">
      <label class="flex items-center gap-2 text-xs">
        <input type="checkbox" v-model="enableVideo" class="rounded" />
        <span>Enable video</span>
      </label>
      <label class="flex items-center gap-2 text-xs">
        <input type="checkbox" v-model="enableAudio" class="rounded" />
        <span>Enable audio</span>
      </label>
    </div>
    
    <!-- QR Code (if link exists) -->
    <div v-if="inviteLink && qrCodeUrl" class="text-center">
      <button 
        @click="showAdvanced = !showAdvanced"
        class="text-xs text-r58-text-secondary hover:text-r58-text-primary"
      >
        Show QR Code
      </button>
      <div v-if="showAdvanced" class="mt-2 flex justify-center">
        <img 
          :src="qrCodeUrl" 
          alt="QR Code"
          class="w-32 h-32 bg-white p-2 rounded"
        />
      </div>
    </div>
    
    <!-- Room Info -->
    <div class="text-xs text-r58-text-secondary text-center">
      Room: <span class="font-mono">{{ VDO_ROOM }}</span>
    </div>
  </div>
</template>

