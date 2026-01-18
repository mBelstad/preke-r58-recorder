<script setup lang="ts">
import { ref, computed } from 'vue'
import { buildGuestInviteUrl, VDO_ROOM } from '@/lib/vdoninja'
import { r58Api } from '@/lib/api'

const props = defineProps<{
  token: string
  status: any
  currentSlideIndex: number
  isRecording: boolean
}>()

const emit = defineEmits<{
  (e: 'prev-slide'): void
  (e: 'next-slide'): void
}>()

// State
const guestName = ref('')
const showAdvanced = ref(false)
const enableVideo = ref(true)
const enableAudio = ref(true)
const isMuted = ref(false)
const isCameraOff = ref(false)
const isSharingPresentation = ref(false)

// Generated link
const inviteLink = computed(() => {
  if (!guestName.value.trim()) return ''
  return buildGuestInviteUrl(guestName.value.trim())
})

// QR Code generation
const qrCodeUrl = computed(() => {
  if (!inviteLink.value) return ''
  return `https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=${encodeURIComponent(inviteLink.value)}`
})

// Actions
function copyLink() {
  if (!inviteLink.value) return
  navigator.clipboard.writeText(inviteLink.value)
  alert('Link copied!')
}

async function shareLink() {
  if (!inviteLink.value) return
  
  if (navigator.share) {
    try {
      await navigator.share({
        title: `Join ${VDO_ROOM} as ${guestName.value}`,
        text: `Click to join the video call as ${guestName.value}`,
        url: inviteLink.value
      })
    } catch (err) {
      // User cancelled
    }
  } else {
    copyLink()
  }
}

// TODO: Implement actual API calls for these controls
async function toggleMute() {
  isMuted.value = !isMuted.value
  console.log('Toggle mute', isMuted.value)
}

async function toggleCamera() {
  isCameraOff.value = !isCameraOff.value
  console.log('Toggle camera', isCameraOff.value)
}

async function togglePresentationShare() {
  isSharingPresentation.value = !isSharingPresentation.value
  console.log('Toggle presentation share', isSharingPresentation.value)
}

const currentGraphic = computed(() => {
  if (!props.status?.project?.graphics) return null
  return props.status.project.graphics[props.currentSlideIndex]
})

const hasGraphics = computed(() => {
  return props.status?.project?.graphics && props.status.project.graphics.length > 0
})
</script>

<template>
  <div class="webinar-portal space-y-6">
    <!-- Studio Controls -->
    <div class="glass-card">
      <h2 class="text-lg font-semibold mb-4 px-1">Studio Controls</h2>
      
      <div class="grid grid-cols-2 gap-3">
        <button
          @click="toggleMute"
          class="btn-control touch-target"
          :class="isMuted ? 'bg-preke-red-bg text-preke-red border-preke-red' : 'bg-preke-bg-surface text-preke-text-primary'"
        >
          <div class="icon-wrapper mb-2">
            <svg v-if="isMuted" class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 3l18 18" />
            </svg>
            <svg v-else class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
            </svg>
          </div>
          <span class="text-sm font-medium">{{ isMuted ? 'Unmute Mic' : 'Mute Mic' }}</span>
        </button>
        
        <button
          @click="toggleCamera"
          class="btn-control touch-target"
          :class="isCameraOff ? 'bg-preke-red-bg text-preke-red border-preke-red' : 'bg-preke-bg-surface text-preke-text-primary'"
        >
          <div class="icon-wrapper mb-2">
            <svg v-if="isCameraOff" class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 3l18 18" />
            </svg>
            <svg v-else class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
          </div>
          <span class="text-sm font-medium">{{ isCameraOff ? 'Camera On' : 'Camera Off' }}</span>
        </button>
      </div>
    </div>
    
    <!-- Invite Links -->
    <div class="glass-card">
      <h2 class="text-lg font-semibold mb-4 px-1">Invite Guests</h2>
      
      <div class="space-y-4">
        <div>
          <label class="block text-sm text-preke-text-dim mb-2">Guest Name</label>
          <input 
            v-model="guestName"
            type="text"
            placeholder="e.g. John Doe"
            class="w-full bg-preke-bg-elevated border border-preke-border rounded-lg p-3 text-preke-text-primary focus:border-preke-gold focus:outline-none"
          />
        </div>
        
        <div v-if="inviteLink" class="space-y-4 pt-2">
          <div class="p-3 bg-preke-bg-elevated rounded-lg break-all text-sm text-preke-text-dim font-mono border border-preke-border/50">
            {{ inviteLink }}
          </div>
          
          <div class="grid grid-cols-2 gap-3">
            <button
              @click="copyLink"
              class="btn-v2 btn-v2--primary touch-target"
            >
              <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
              </svg>
              Copy Link
            </button>
            <button
              @click="shareLink"
              class="btn-v2 btn-v2--secondary touch-target"
            >
              <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
              </svg>
              Share
            </button>
          </div>
          
          <div class="flex justify-center pt-2">
            <div class="bg-white p-3 rounded-xl shadow-lg">
              <img :src="qrCodeUrl" alt="QR Code" class="w-40 h-40" />
            </div>
          </div>
        </div>
        
        <p v-else class="text-center text-preke-text-muted text-sm py-2">
          Enter a name to generate an invite link.
        </p>
      </div>
    </div>
    
    <!-- Presentation -->
    <div v-if="hasGraphics" class="glass-card">
      <div class="flex items-center justify-between mb-3 px-1">
        <h2 class="text-lg font-semibold">Presentation</h2>
        <button 
          @click="togglePresentationShare"
          class="text-sm font-medium px-3 py-1.5 rounded-lg border transition-colors"
          :class="isSharingPresentation ? 'bg-preke-green-bg text-preke-green border-preke-green' : 'bg-preke-bg-surface text-preke-text-muted border-preke-border'"
        >
          {{ isSharingPresentation ? 'Sharing On' : 'Sharing Off' }}
        </button>
      </div>
      
      <div class="graphic-preview mb-4" :class="{ 'opacity-50': !isSharingPresentation }">
        <img 
          v-if="currentGraphic" 
          :src="currentGraphic.url" 
          :alt="currentGraphic.filename" 
          class="w-full h-auto object-contain bg-black/50" 
        />
        <div v-else class="w-full aspect-video flex items-center justify-center bg-black/50 text-preke-text-muted">
          No preview available
        </div>
        
        <div class="slide-indicator">
          {{ currentSlideIndex + 1 }} / {{ status.project.graphics.length }}
        </div>
      </div>
      
      <div class="flex items-center gap-3">
        <button
          @click="emit('prev-slide')"
          :disabled="currentSlideIndex === 0"
          class="btn-v2 btn-v2--glass flex-1 touch-target text-lg py-4"
        >
          Previous
        </button>
        <button
          @click="emit('next-slide')"
          :disabled="currentSlideIndex >= status.project.graphics.length - 1"
          class="btn-v2 btn-v2--glass flex-1 touch-target text-lg py-4"
        >
          Next
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
@import '@/styles/design-system-v2.css';

.btn-control {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 1rem;
  border-radius: var(--preke-radius-lg);
  border: 1px solid var(--preke-border);
  transition: all 0.2s ease;
}

.btn-control:active {
  transform: scale(0.98);
}

.graphic-preview {
  position: relative;
  border-radius: var(--preke-radius-lg);
  overflow: hidden;
  background: var(--preke-bg-elevated);
  box-shadow: inset 0 0 0 1px var(--preke-border);
  transition: opacity 0.3s ease;
}

.slide-indicator {
  position: absolute;
  bottom: 0.75rem;
  right: 0.75rem;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(4px);
  color: white;
  padding: 0.25rem 0.75rem;
  border-radius: var(--preke-radius-md);
  font-size: 0.875rem;
  font-weight: 600;
}

/* Touch-friendly buttons */
.touch-target {
  min-height: 56px;
}
</style>
