<script setup lang="ts">
/**
 * GuestManager Component
 * 
 * Manages VDO.ninja guests with controls for:
 * - Viewing all connected guests
 * - Muting/unmuting guests
 * - Kicking guests from the room
 * - Requesting screen share from guests
 * - Sending messages to guests
 * - Managing waiting room (future)
 */
import { ref, computed, inject, type Ref } from 'vue'
import { useMixerStore, type MixerSource } from '@/stores/mixer'
import { toast } from '@/composables/useToast'

// Get VDO.ninja embed reference from parent
const props = defineProps<{
  vdoEmbed?: {
    kickGuest: (id: string) => void
    setMute: (id: string, muted: boolean) => void
    requestScreenShare: (id: string) => void
    sendCommand: (action: string, target?: string, value?: unknown) => void
  }
}>()

const mixerStore = useMixerStore()
const isOpen = ref(false)
const selectedGuest = ref<string | null>(null)
const messageText = ref('')

// Get guests (sources that are type 'guest')
const guests = computed(() => 
  mixerStore.sources.filter(s => s.type === 'guest')
)

// Get all sources for display
const allSources = computed(() => mixerStore.sources)

// Categorize sources
const cameraSourcesCount = computed(() => 
  mixerStore.sources.filter(s => s.type === 'camera').length
)

const guestSourcesCount = computed(() => guests.value.length)

const screenSourcesCount = computed(() => 
  mixerStore.sources.filter(s => s.type === 'screen').length
)

function open() {
  isOpen.value = true
}

function close() {
  isOpen.value = false
  selectedGuest.value = null
  messageText.value = ''
}

function toggleMute(guest: MixerSource) {
  if (props.vdoEmbed) {
    props.vdoEmbed.setMute(guest.id, !guest.muted)
    mixerStore.setSourceMute(guest.id, !guest.muted)
    toast.info(guest.muted ? `Unmuted ${guest.label}` : `Muted ${guest.label}`)
  }
}

function kickGuest(guest: MixerSource) {
  if (props.vdoEmbed && confirm(`Are you sure you want to remove ${guest.label} from the room?`)) {
    props.vdoEmbed.kickGuest(guest.id)
    toast.info(`Removed ${guest.label} from room`)
  }
}

function requestScreenShare(guest: MixerSource) {
  if (props.vdoEmbed) {
    props.vdoEmbed.requestScreenShare(guest.id)
    toast.info(`Requested screen share from ${guest.label}`)
  }
}

function sendMessage(guest: MixerSource) {
  if (props.vdoEmbed && messageText.value.trim()) {
    props.vdoEmbed.sendCommand('sendChat', guest.id, messageText.value)
    toast.success(`Message sent to ${guest.label}`)
    messageText.value = ''
  }
}

function selectGuest(guestId: string) {
  selectedGuest.value = selectedGuest.value === guestId ? null : guestId
}

function getSourceIcon(type: MixerSource['type']) {
  switch (type) {
    case 'camera': return '📹'
    case 'guest': return '👤'
    case 'screen': return '🖥️'
    case 'media': return '🎬'
    default: return '📺'
  }
}

function getSourceTypeLabel(type: MixerSource['type']) {
  switch (type) {
    case 'camera': return 'Camera'
    case 'guest': return 'Guest'
    case 'screen': return 'Screen Share'
    case 'media': return 'Media'
    default: return 'Source'
  }
}

// Expose open method
defineExpose({ open })
</script>

<template>
  <Teleport to="body">
    <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center">
      <!-- Backdrop -->
      <div class="absolute inset-0 bg-black/60" @click="close"></div>
      
      <!-- Modal content -->
      <div class="relative bg-r58-bg-secondary border border-r58-bg-tertiary rounded-xl w-full max-w-2xl max-h-[80vh] overflow-hidden shadow-2xl" data-testid="guest-manager-modal">
        <!-- Header -->
        <div class="flex items-center justify-between px-6 py-4 border-b border-r58-bg-tertiary">
          <div class="flex items-center gap-4">
            <h2 class="text-xl font-semibold">Source Manager</h2>
            <div class="flex gap-2 text-sm text-r58-text-secondary">
              <span class="px-2 py-1 bg-r58-bg-tertiary rounded">👤 {{ guestSourcesCount }}</span>
              <span class="px-2 py-1 bg-r58-bg-tertiary rounded">📹 {{ cameraSourcesCount }}</span>
              <span class="px-2 py-1 bg-r58-bg-tertiary rounded">🖥️ {{ screenSourcesCount }}</span>
            </div>
          </div>
          <button @click="close" class="text-r58-text-secondary hover:text-r58-text-primary text-2xl">
            ×
          </button>
        </div>

        <!-- Content -->
        <div class="p-6 overflow-y-auto max-h-[60vh]">
          <!-- No sources state -->
          <div v-if="allSources.length === 0" class="text-center py-12">
            <div class="text-4xl mb-4">👥</div>
            <h3 class="text-lg font-medium mb-2">No Sources Connected</h3>
            <p class="text-r58-text-secondary">
              Guests and cameras will appear here when they join the room.
            </p>
          </div>

          <!-- Sources list -->
          <div v-else class="space-y-3">
            <div
              v-for="source in allSources"
              :key="source.id"
              class="border border-r58-bg-tertiary rounded-lg overflow-hidden transition-colors"
              :class="{ 'border-r58-accent-primary bg-r58-accent-primary/5': selectedGuest === source.id }"
              data-testid="source-card"
            >
              <!-- Source header -->
              <div 
                class="flex items-center justify-between p-4 cursor-pointer hover:bg-r58-bg-tertiary/50"
                @click="selectGuest(source.id)"
              >
                <div class="flex items-center gap-3">
                  <!-- Source icon -->
                  <div class="w-10 h-10 rounded-full bg-r58-bg-tertiary flex items-center justify-center text-lg">
                    {{ getSourceIcon(source.type) }}
                  </div>
                  
                  <!-- Source info -->
                  <div>
                    <div class="flex items-center gap-2">
                      <span class="font-medium">{{ source.label }}</span>
                      <span 
                        v-if="source.muted" 
                        class="text-xs px-1.5 py-0.5 bg-r58-accent-danger/20 text-r58-accent-danger rounded"
                      >
                        Muted
                      </span>
                    </div>
                    <span class="text-xs text-r58-text-secondary">{{ getSourceTypeLabel(source.type) }}</span>
                  </div>
                </div>

                <!-- Quick actions -->
                <div class="flex items-center gap-2">
                  <!-- Audio level -->
                  <div class="w-16 h-2 bg-r58-bg-primary rounded-full overflow-hidden">
                    <div 
                      class="h-full bg-r58-accent-success rounded-full transition-all duration-100"
                      :style="{ width: `${source.audioLevel || 0}%` }"
                    ></div>
                  </div>

                  <!-- Video/Audio indicators -->
                  <div class="flex gap-1 text-xs">
                    <span v-if="source.hasVideo" class="text-r58-accent-success">📹</span>
                    <span v-if="source.hasAudio" class="text-r58-accent-success">🎤</span>
                  </div>

                  <!-- Expand indicator -->
                  <svg 
                    class="w-4 h-4 text-r58-text-secondary transition-transform"
                    :class="{ 'rotate-180': selectedGuest === source.id }"
                    fill="none" stroke="currentColor" viewBox="0 0 24 24"
                  >
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
              </div>

              <!-- Expanded controls -->
              <div 
                v-if="selectedGuest === source.id" 
                class="px-4 pb-4 space-y-4 border-t border-r58-bg-tertiary"
              >
                <!-- Action buttons -->
                <div class="flex flex-wrap gap-2 pt-4">
                  <!-- Mute/Unmute -->
                  <button
                    @click.stop="toggleMute(source)"
                    class="btn btn-sm"
                    :class="source.muted ? 'btn-primary' : ''"
                    data-testid="mute-guest-button"
                  >
                    {{ source.muted ? '🔊 Unmute' : '🔇 Mute' }}
                  </button>

                  <!-- Request Screen Share (guests only) -->
                  <button
                    v-if="source.type === 'guest'"
                    @click.stop="requestScreenShare(source)"
                    class="btn btn-sm"
                    data-testid="request-screen-button"
                  >
                    🖥️ Request Screen
                  </button>

                  <!-- Kick (guests only) -->
                  <button
                    v-if="source.type === 'guest'"
                    @click.stop="kickGuest(source)"
                    class="btn btn-sm btn-danger"
                    data-testid="kick-guest-button"
                  >
                    ❌ Remove
                  </button>
                </div>

                <!-- Send message (guests only) -->
                <div v-if="source.type === 'guest'" class="flex gap-2">
                  <input
                    v-model="messageText"
                    type="text"
                    placeholder="Send a message to this guest..."
                    class="flex-1 px-3 py-2 bg-r58-bg-tertiary border border-r58-bg-tertiary rounded-lg focus:border-r58-accent-primary focus:outline-none text-sm"
                    @keyup.enter="sendMessage(source)"
                  />
                  <button
                    @click.stop="sendMessage(source)"
                    class="btn btn-sm btn-primary"
                    :disabled="!messageText.trim()"
                  >
                    Send
                  </button>
                </div>

                <!-- Stream ID (for debugging) -->
                <div class="text-xs text-r58-text-secondary">
                  ID: <code class="bg-r58-bg-tertiary px-1 rounded">{{ source.id }}</code>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Footer -->
        <div class="flex items-center justify-between px-6 py-4 border-t border-r58-bg-tertiary">
          <div class="text-sm text-r58-text-secondary">
            {{ allSources.length }} source{{ allSources.length !== 1 ? 's' : '' }} connected
          </div>
          <button @click="close" class="btn">Close</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.btn-danger {
  @apply bg-r58-accent-danger hover:bg-red-600;
}
</style>

