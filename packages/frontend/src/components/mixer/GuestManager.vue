<script setup lang="ts">
/**
 * GuestManager - Greenroom and guest waiting room management
 * 
 * Shows guests waiting to join and provides controls to admit/reject them.
 */
import { computed } from 'vue'
import { useMixerStore, type GreenroomGuest } from '@/stores/mixer'
import { toast } from '@/composables/useToast'
import VdoNinjaEmbed from './VdoNinjaEmbed.vue'

const props = defineProps<{
  vdoEmbed?: InstanceType<typeof VdoNinjaEmbed> | null
}>()

const mixerStore = useMixerStore()

// Computed
const greenroomGuests = computed(() => mixerStore.greenroom)
const connectedSources = computed(() => mixerStore.connectedSources)
const hasGuests = computed(() => greenroomGuests.value.length > 0)

// Actions
function admitGuest(guest: GreenroomGuest) {
  mixerStore.admitFromGreenroom(guest.id)
  
  // Add to scene via VDO.ninja
  if (props.vdoEmbed) {
    props.vdoEmbed.addSource?.(guest.id)
  }
  
  toast.success(`Admitted: ${guest.label}`)
}

function rejectGuest(guest: GreenroomGuest) {
  mixerStore.removeFromGreenroom(guest.id)
  
  // Kick from VDO.ninja room
  if (props.vdoEmbed) {
    props.vdoEmbed.kickGuest?.(guest.id)
  }
  
  toast.info(`Removed: ${guest.label}`)
}

function admitAll() {
  for (const guest of greenroomGuests.value) {
    admitGuest(guest)
  }
}

function getWaitTime(joinedAt: string): string {
  const seconds = Math.floor((Date.now() - new Date(joinedAt).getTime()) / 1000)
  if (seconds < 60) return `${seconds}s`
  const minutes = Math.floor(seconds / 60)
  return `${minutes}m`
}

function kickSource(sourceId: string) {
  if (props.vdoEmbed) {
    props.vdoEmbed.kickGuest?.(sourceId)
  }
  mixerStore.removeSource(sourceId)
  toast.info('Guest removed')
}
</script>

<template>
  <div class="guest-manager" data-testid="guest-manager">
    <!-- Greenroom Section -->
    <div v-if="hasGuests" class="mb-6">
      <div class="flex items-center justify-between mb-3">
        <h4 class="text-sm font-medium flex items-center gap-2">
          <span class="w-2 h-2 rounded-full bg-amber-500 animate-pulse"></span>
          Waiting Room
          <span class="text-xs text-r58-text-secondary">({{ greenroomGuests.length }})</span>
        </h4>
        <button 
          v-if="greenroomGuests.length > 1"
          @click="admitAll"
          class="text-xs text-r58-accent-primary hover:underline"
        >
          Admit All
        </button>
      </div>
      
      <div class="space-y-2">
        <div 
          v-for="guest in greenroomGuests" 
          :key="guest.id"
          class="flex items-center gap-3 p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg"
        >
          <!-- Guest Avatar -->
          <div class="w-10 h-10 rounded-full bg-r58-bg-tertiary flex items-center justify-center">
            <svg class="w-5 h-5 text-r58-text-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
          </div>
          
          <!-- Guest Info -->
          <div class="flex-1 min-w-0">
            <p class="font-medium text-sm truncate">{{ guest.label }}</p>
            <div class="flex items-center gap-2 text-xs text-r58-text-secondary">
              <span v-if="guest.hasVideo">📹</span>
              <span v-if="guest.hasAudio">🎤</span>
              <span>Waiting {{ getWaitTime(guest.joinedAt) }}</span>
            </div>
          </div>
          
          <!-- Actions -->
          <div class="flex gap-2">
            <button 
              @click="admitGuest(guest)"
              class="px-3 py-1 text-xs bg-emerald-500 text-white rounded hover:bg-emerald-400 transition-colors"
            >
              Admit
            </button>
            <button 
              @click="rejectGuest(guest)"
              class="px-3 py-1 text-xs bg-r58-bg-tertiary text-r58-text-secondary rounded hover:bg-red-500/20 hover:text-red-400 transition-colors"
            >
              Reject
            </button>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Connected Guests Section -->
    <div>
      <h4 class="text-sm font-medium mb-3 flex items-center gap-2">
        <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
        Connected
        <span class="text-xs text-r58-text-secondary">({{ connectedSources.length }})</span>
      </h4>
      
      <div v-if="connectedSources.length > 0" class="space-y-2">
        <div 
          v-for="source in connectedSources" 
          :key="source.id"
          class="flex items-center gap-3 p-2 bg-r58-bg-tertiary/50 rounded-lg"
        >
          <!-- Type Icon -->
          <div class="w-8 h-8 rounded bg-r58-bg-tertiary flex items-center justify-center">
            <svg v-if="source.type === 'camera'" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
            <svg v-else-if="source.type === 'guest'" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
            <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
          </div>
          
          <!-- Source Info -->
          <div class="flex-1 min-w-0">
            <p class="text-sm truncate">{{ source.label }}</p>
            <p class="text-xs text-r58-text-secondary">{{ source.type }}</p>
          </div>
          
          <!-- Status Indicators -->
          <div class="flex items-center gap-1">
            <span v-if="source.muted" class="text-red-400" title="Muted">🔇</span>
            <span 
              v-if="mixerStore.liveSourceIds.includes(source.id)" 
              class="px-1.5 py-0.5 text-xs bg-red-600 text-white rounded"
            >
              LIVE
            </span>
          </div>
          
          <!-- Kick Button (guests only) -->
          <button 
            v-if="source.type === 'guest'"
            @click="kickSource(source.id)"
            class="p-1 text-r58-text-secondary hover:text-red-400 transition-colors"
            title="Remove guest"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>
      
      <!-- Empty State -->
      <div v-else class="text-center py-4 text-r58-text-secondary">
        <p class="text-sm">No sources connected</p>
        <p class="text-xs mt-1">HDMI sources and guests will appear here</p>
      </div>
    </div>
  </div>
</template>

