<script setup lang="ts">
/**
 * SessionInfo v2 - Recorder sidebar with session naming and camera controls
 */
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useRecorderStore } from '@/stores/recorder'
import { useCapabilitiesStore } from '@/stores/capabilities'
import { useConnectionStatus } from '@/composables/useConnectionStatus'
import { useTailscaleStatus } from '@/composables/useTailscaleStatus'
import { useCameraControls } from '@/composables/useCameraControls'
import CameraControlModal from '@/components/camera/CameraControlModal.vue'

const router = useRouter()
const recorderStore = useRecorderStore()
const capabilitiesStore = useCapabilitiesStore()

// Connection status
const { state, latencyMs } = useConnectionStatus()
const { connectionMethod, connectionLabel } = useTailscaleStatus()

// Connection display info
const connectionInfo = computed(() => {
  const isConnected = state.value === 'connected'
  const isConnecting = state.value === 'connecting'
  const isDegraded = state.value === 'degraded'
  
  if (isConnected) {
    let methodLabel = ''
    if (connectionMethod.value === 'relay') {
      methodLabel = 'Relay'
    } else if (connectionMethod.value === 'p2p') {
      methodLabel = 'P2P'
    } else if (connectionMethod.value === 'local') {
      methodLabel = 'Local'
    }
    
    return {
      status: 'online',
      color: 'green',
      label: methodLabel || 'Connected',
      latency: latencyMs.value,
      pulse: false
    }
  }
  
  if (isConnecting) {
    return {
      status: 'connecting',
      color: 'amber',
      label: 'Connecting...',
      latency: null,
      pulse: true
    }
  }
  
  if (isDegraded) {
    return {
      status: 'degraded',
      color: 'amber',
      label: 'Slow',
      latency: latencyMs.value,
      pulse: false
    }
  }
  
  return {
    status: 'offline',
    color: 'red',
    label: 'Offline',
    latency: null,
    pulse: true
  }
})

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

// Camera controls
const { cameras, loadCameras } = useCameraControls()
const selectedCameraForControl = ref<string | null>(null)
const cameraModalRef = ref<InstanceType<typeof CameraControlModal> | null>(null)

onMounted(async () => {
  await loadCameras()
})

function openCameraControl(cameraName: string) {
  selectedCameraForControl.value = cameraName
  cameraModalRef.value?.open()
}

function closeCameraControl() {
  selectedCameraForControl.value = null
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
    <!-- Connection Status + Session Name (combined) -->
    <div class="sidebar__card sidebar__card--header">
      <!-- Connection status row -->
      <div class="connection-row">
        <div class="connection-status">
          <span 
            class="connection-dot" 
            :class="[
              `connection-dot--${connectionInfo.color}`,
              { 'connection-dot--pulse': connectionInfo.pulse }
            ]"
          ></span>
          <span class="connection-label">{{ connectionInfo.label }}</span>
          <span v-if="connectionInfo.latency" class="connection-latency">
            {{ connectionInfo.latency }}ms
          </span>
        </div>
      </div>
      
      <!-- Divider -->
      <div class="sidebar__divider"></div>
      
      <!-- Session name -->
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
      <!-- Camera Controls -->
      <div v-if="cameras.length > 0" class="sidebar__card">
        <div class="sidebar__label">Camera Controls</div>
        <div class="cameras">
          <div 
            v-for="cam in cameras" 
            :key="cam.name"
            class="camera"
          >
            <div class="camera__header">
              {{ cam.name }}
              <span 
                :class="[
                  'camera__status',
                  cam.connected ? 'camera__status--connected' : 'camera__status--disconnected'
                ]"
              >
                {{ cam.connected ? '●' : '○' }}
              </span>
            </div>
            <button 
              class="camera__control-btn"
              @click="openCameraControl(cam.name)"
              :disabled="!cam.connected"
            >
              <svg class="camera__control-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
                <circle cx="12" cy="12" r="3"/>
              </svg>
              <span>Controls</span>
            </button>
          </div>
        </div>
      </div>
      
      <!-- Camera Control Modal -->
      <CameraControlModal
        ref="cameraModalRef"
        :camera-name="selectedCameraForControl"
        @close="closeCameraControl"
      />
      
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

.sidebar__card--header {
  padding: 14px;
}

.sidebar__card--recording {
  background: rgba(212, 90, 90, 0.1);
  border-color: rgba(212, 90, 90, 0.3);
  text-align: center;
}

/* Connection status row */
.connection-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.connection-status {
  display: flex;
  align-items: center;
  gap: 8px;
}

.connection-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.connection-dot--green {
  background: var(--preke-green);
  box-shadow: 0 0 8px var(--preke-green);
}

.connection-dot--amber {
  background: var(--preke-amber);
  box-shadow: 0 0 8px var(--preke-amber);
}

.connection-dot--red {
  background: var(--preke-red);
  box-shadow: 0 0 8px var(--preke-red);
}

.connection-dot--pulse {
  animation: dot-pulse 2s ease-in-out infinite;
}

@keyframes dot-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(0.85); }
}

.connection-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--preke-text-dim, #ccc);
}

.connection-latency {
  font-size: 11px;
  color: var(--preke-text-muted, #888);
  font-family: var(--preke-font-mono, monospace);
}

.sidebar__divider {
  height: 1px;
  background: var(--preke-border, rgba(255,255,255,0.1));
  margin: 10px 0;
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

.camera__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.camera__status {
  font-size: 10px;
  margin-left: 8px;
}

.camera__status--connected {
  color: var(--preke-green, #22c55e);
}

.camera__status--disconnected {
  color: var(--preke-red, #d45a5a);
}

.camera__control-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px;
  margin-top: 8px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--preke-border, rgba(255,255,255,0.1));
  border-radius: 6px;
  color: var(--preke-text-muted, #888);
  cursor: pointer;
  transition: all 0.15s ease;
  font-size: 12px;
  font-weight: 500;
}

.camera__control-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.1);
  color: var(--preke-text, #fff);
  border-color: var(--preke-gold, #e0a030);
}

.camera__control-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.camera__control-icon {
  width: 16px;
  height: 16px;
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
