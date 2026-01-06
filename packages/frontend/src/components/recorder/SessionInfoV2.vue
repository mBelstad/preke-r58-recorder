<script setup lang="ts">
/**
 * SessionInfo v2 - Recorder sidebar with session naming and camera controls
 */
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useRecorderStore } from '@/stores/recorder'
import { useCapabilitiesStore } from '@/stores/capabilities'

const router = useRouter()
const recorderStore = useRecorderStore()
const capabilitiesStore = useCapabilitiesStore()

const currentSession = computed(() => recorderStore.currentSession)
const activeInputs = computed(() => recorderStore.activeInputs)
const isRecording = computed(() => recorderStore.isRecording)
const recordingInputs = computed(() => recorderStore.inputs.filter(i => i.isRecording))

// Session name
const sessionName = ref('')

// Generate default session name with date/time
onMounted(() => {
  const now = new Date()
  const dateStr = now.toLocaleDateString('en-GB', { 
    day: '2-digit', 
    month: '2-digit', 
    year: 'numeric' 
  }).replace(/\//g, '.')
  sessionName.value = `Session ${dateStr}`
})

// Camera controls (placeholder values)
const cameraControls = ref([
  { id: 'cam1', name: 'CAM 1', focus: 'auto', wb: 'auto', shutter: 'auto', aperture: 'auto' },
  { id: 'cam2', name: 'CAM 2', focus: 'auto', wb: 'auto', shutter: 'auto', aperture: 'auto' },
  { id: 'cam3', name: 'CAM 3', focus: 'auto', wb: 'auto', shutter: 'auto', aperture: 'auto' },
  { id: 'cam4', name: 'CAM 4', focus: 'auto', wb: 'auto', shutter: 'auto', aperture: 'auto' },
])

// Toggle a setting to auto
function toggleAuto(camIndex: number, setting: 'focus' | 'wb' | 'shutter' | 'aperture') {
  const cam = cameraControls.value[camIndex]
  if (cam) {
    cam[setting] = cam[setting] === 'auto' ? 'manual' : 'auto'
  }
}

// Storage info
const storageInfo = computed(() => {
  const caps = capabilitiesStore.capabilities
  if (!caps) return null
  
  const usedGB = caps.storage_used_gb || 0
  const totalGB = caps.storage_total_gb || 1
  const freeGB = totalGB - usedGB
  const percent = Math.round((usedGB / totalGB) * 100)
  const hoursRemaining = freeGB / 10
  
  return {
    freeGB: Math.round(freeGB),
    totalGB: Math.round(totalGB),
    percent,
    hoursRemaining: Math.round(hoursRemaining * 10) / 10,
    isLow: percent > 85,
    isCritical: percent > 95
  }
})

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

function openInputConfig() {
  router.push({ name: 'admin', query: { tab: 'settings' } })
}
</script>

<template>
  <div class="sidebar">
    <!-- Session Name -->
    <div class="sidebar__card">
      <label class="sidebar__label">Session Name</label>
      <input 
        v-model="sessionName"
        type="text"
        class="sidebar__input"
        placeholder="Session 06.01.2026"
        :disabled="isRecording"
      />
    </div>
    
    <!-- RECORDING STATE -->
    <template v-if="isRecording">
      <div class="sidebar__card sidebar__card--recording">
        <div class="recording__header">
          <span class="recording__dot"></span>
          <span class="recording__label">Recording</span>
        </div>
        <div class="recording__duration">{{ recorderStore.formattedDuration }}</div>
        <div class="recording__meta">
          {{ recordingInputs.length }} camera{{ recordingInputs.length !== 1 ? 's' : '' }} recording
        </div>
      </div>
      
      <!-- Recording Stats -->
      <div class="sidebar__card">
        <div class="sidebar__label">Recording Stats</div>
        <div class="stats">
          <div 
            v-for="input in recordingInputs" 
            :key="input.id"
            class="stats__item"
          >
            <span class="stats__label">{{ input.label }}</span>
            <span class="stats__value">{{ formatBytes(input.bytesWritten) }}</span>
          </div>
        </div>
      </div>
      
      <!-- Storage Warning -->
      <div v-if="storageInfo?.isLow" class="sidebar__card sidebar__card--warning">
        <span class="warning__icon">⚠️</span>
        <div class="warning__text">
          <strong>Low storage</strong>
          <span>{{ storageInfo.freeGB }} GB remaining</span>
        </div>
      </div>
    </template>
    
    <!-- IDLE STATE -->
    <template v-else>
      <!-- Status -->
      <div class="sidebar__card">
        <div class="sidebar__label">Status</div>
        <p class="sidebar__hint">
          {{ activeInputs.length }} input{{ activeInputs.length !== 1 ? 's' : '' }} with signal.
          Press <kbd>Space</kbd> to start recording.
        </p>
      </div>
      
      <!-- Camera Controls -->
      <div class="sidebar__card">
        <div class="sidebar__label">Camera Controls</div>
        <div class="cameras">
          <div 
            v-for="(cam, index) in cameraControls" 
            :key="cam.id"
            class="camera"
          >
            <div class="camera__header">{{ cam.name }}</div>
            <div class="camera__controls">
              <button 
                class="camera__btn"
                :class="{ 'camera__btn--auto': cam.focus === 'auto' }"
                @click="toggleAuto(index, 'focus')"
                title="Focus"
              >
                <span class="camera__btn-icon">◎</span>
                <span class="camera__btn-label">{{ cam.focus === 'auto' ? 'A' : 'M' }}</span>
              </button>
              <button 
                class="camera__btn"
                :class="{ 'camera__btn--auto': cam.wb === 'auto' }"
                @click="toggleAuto(index, 'wb')"
                title="White Balance"
              >
                <span class="camera__btn-icon">☀</span>
                <span class="camera__btn-label">{{ cam.wb === 'auto' ? 'A' : 'M' }}</span>
              </button>
              <button 
                class="camera__btn"
                :class="{ 'camera__btn--auto': cam.shutter === 'auto' }"
                @click="toggleAuto(index, 'shutter')"
                title="Shutter"
              >
                <span class="camera__btn-icon">⏱</span>
                <span class="camera__btn-label">{{ cam.shutter === 'auto' ? 'A' : 'M' }}</span>
              </button>
              <button 
                class="camera__btn"
                :class="{ 'camera__btn--auto': cam.aperture === 'auto' }"
                @click="toggleAuto(index, 'aperture')"
                title="Aperture"
              >
                <span class="camera__btn-icon">◐</span>
                <span class="camera__btn-label">{{ cam.aperture === 'auto' ? 'A' : 'M' }}</span>
              </button>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Storage -->
      <div v-if="storageInfo" class="sidebar__card">
        <div class="sidebar__label">Storage</div>
        <div class="storage">
          <div class="storage__bar">
            <div 
              class="storage__fill"
              :class="{
                'storage__fill--ok': !storageInfo.isLow,
                'storage__fill--low': storageInfo.isLow && !storageInfo.isCritical,
                'storage__fill--critical': storageInfo.isCritical
              }"
              :style="{ width: `${storageInfo.percent}%` }"
            ></div>
          </div>
          <div class="storage__info">
            <span>{{ storageInfo.freeGB }} GB free</span>
            <span class="storage__estimate">~{{ storageInfo.hoursRemaining }}h</span>
          </div>
        </div>
      </div>
      
      <!-- Quick Actions -->
      <div class="sidebar__card">
        <div class="sidebar__label">Quick Actions</div>
        <button @click="openInputConfig" class="sidebar__btn">
          <svg class="sidebar__btn-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.8">
            <path stroke-linecap="round" stroke-linejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
            <circle cx="12" cy="12" r="3"/>
          </svg>
          Configure Inputs
        </button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.sidebar {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.sidebar__card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--preke-border, rgba(255,255,255,0.1));
  border-radius: 10px;
  padding: 12px;
}

.sidebar__card--recording {
  background: rgba(212, 90, 90, 0.1);
  border-color: rgba(212, 90, 90, 0.3);
  text-align: center;
}

.sidebar__card--warning {
  background: rgba(245, 158, 11, 0.1);
  border-color: rgba(245, 158, 11, 0.3);
  display: flex;
  align-items: center;
  gap: 10px;
}

.sidebar__label {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--preke-text-muted, #888);
  margin-bottom: 8px;
}

.sidebar__input {
  width: 100%;
  padding: 8px 10px;
  font-size: 13px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid var(--preke-border, rgba(255,255,255,0.1));
  border-radius: 6px;
  color: var(--preke-text, #fff);
}

.sidebar__input:focus {
  outline: none;
  border-color: var(--preke-gold, #e0a030);
}

.sidebar__input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.sidebar__hint {
  font-size: 12px;
  color: var(--preke-text-muted, #888);
  line-height: 1.5;
}

.sidebar__hint kbd {
  display: inline-block;
  padding: 2px 6px;
  font-family: monospace;
  font-size: 11px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid var(--preke-border, rgba(255,255,255,0.1));
  border-radius: 4px;
}

.sidebar__btn {
  width: 100%;
  padding: 10px;
  font-size: 12px;
  font-weight: 500;
  color: var(--preke-text-muted, #888);
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid var(--preke-border, rgba(255,255,255,0.1));
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.sidebar__btn:hover {
  background: rgba(255, 255, 255, 0.05);
  color: var(--preke-text, #fff);
}

.sidebar__btn-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}

/* Recording */
.recording__header {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-bottom: 4px;
}

.recording__dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--preke-red, #d45a5a);
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(0.85); }
}

.recording__label {
  font-size: 11px;
  font-weight: 600;
  color: var(--preke-red, #d45a5a);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.recording__duration {
  font-family: monospace;
  font-size: 28px;
  font-weight: 700;
  color: var(--preke-text, #fff);
  margin: 8px 0;
}

.recording__meta {
  font-size: 12px;
  color: var(--preke-text-muted, #888);
}

/* Stats */
.stats {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.stats__item {
  display: flex;
  justify-content: space-between;
  padding: 4px 0;
  border-bottom: 1px solid var(--preke-border, rgba(255,255,255,0.05));
}

.stats__item:last-child {
  border-bottom: none;
}

.stats__label {
  font-size: 12px;
  color: var(--preke-text-muted, #888);
}

.stats__value {
  font-family: monospace;
  font-size: 12px;
  color: var(--preke-text, #fff);
}

/* Warning */
.warning__icon {
  font-size: 18px;
}

.warning__text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 12px;
}

.warning__text strong {
  color: var(--preke-amber, #f59e0b);
}

.warning__text span {
  color: var(--preke-text-muted, #888);
}

/* Camera Controls */
.cameras {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.camera {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 6px;
  padding: 8px;
}

.camera__header {
  font-size: 11px;
  font-weight: 600;
  color: var(--preke-text-muted, #888);
  margin-bottom: 6px;
}

.camera__controls {
  display: flex;
  gap: 4px;
}

.camera__btn {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 6px 4px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--preke-border, rgba(255,255,255,0.1));
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.camera__btn:hover {
  background: rgba(255, 255, 255, 0.08);
}

.camera__btn--auto {
  background: rgba(34, 197, 94, 0.15);
  border-color: rgba(34, 197, 94, 0.3);
}

.camera__btn--auto .camera__btn-label {
  color: var(--preke-green, #22c55e);
}

.camera__btn-icon {
  font-size: 12px;
  color: var(--preke-text-muted, #888);
}

.camera__btn-label {
  font-size: 9px;
  font-weight: 600;
  color: var(--preke-text-muted, #888);
}

/* Storage */
.storage {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.storage__bar {
  height: 6px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 3px;
  overflow: hidden;
}

.storage__fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.3s ease;
}

.storage__fill--ok { background: var(--preke-green, #22c55e); }
.storage__fill--low { background: var(--preke-amber, #f59e0b); }
.storage__fill--critical { background: var(--preke-red, #d45a5a); }

.storage__info {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: var(--preke-text-muted, #888);
}

.storage__estimate {
  color: var(--preke-text-subtle, #666);
}
</style>
