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
import { useToast } from '@/composables/useToast'
import { isElectron } from '@/lib/api'
import CameraControlModal from '@/components/camera/CameraControlModal.vue'
import CameraSetupModal from '@/components/camera/CameraSetupModal.vue'
import PTZControllerPanel from '@/components/camera/PTZControllerPanel.vue'

const router = useRouter()
const recorderStore = useRecorderStore()
const capabilitiesStore = useCapabilitiesStore()
const toast = useToast()

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
const cameraSetupModalRef = ref<InstanceType<typeof CameraSetupModal> | null>(null)
const showPTZController = ref(false)

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

function openCameraSetup() {
  cameraSetupModalRef.value?.open()
}

function onCameraConfigUpdated() {
  // Reload cameras after config update
  loadCameras()
}

// Storage info
const storageInfo = computed(() => {
  const caps = capabilitiesStore.capabilities
  if (!caps) return null
  
  const totalGB = caps.storage_total_gb || 1
  const freeGB = caps.storage_available_gb || 0
  const usedGB = totalGB - freeGB
  const percent = Math.round((usedGB / totalGB) * 100)
  
  // Estimate recording hours based on actual bitrate (~18Mbps per camera, ~8GB/hour per camera)
  // With typical 3 cameras: ~24 GB/hour total
  const activeCameras = activeInputs.value.length || 1
  const gbPerHour = activeCameras * 8 // ~8 GB/hour per camera at 18Mbps
  const hoursRemaining = freeGB / gbPerHour
  
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

// DaVinci Resolve integration (Electron only)
const inElectron = computed(() => isElectron())
const davinciLoading = ref(false)
const davinciProjectName = computed(() => {
  const session = currentSession.value
  if (session?.id) {
    return `Preke_${session.id}`
  }
  return `Preke_${sessionName.value.replace(/\s+/g, '_')}`
})

// Type assertion for extended electronAPI
const electronAPI = window.electronAPI as typeof window.electronAPI & {
  davinciOpenProject?: (name?: string) => Promise<{ success: boolean; error?: string; projectName?: string }>
  davinciCreateMulticam?: (opts: { projectName?: string; clipName?: string; filePaths?: string[]; syncMethod?: string }) => Promise<{ success: boolean; error?: string; timelineName?: string }>
  davinciRefreshClips?: () => Promise<{ success: boolean; error?: string; clipsRefreshed?: number }>
}

async function openInDaVinci() {
  if (!electronAPI?.davinciOpenProject) return
  
  davinciLoading.value = true
  toast.info('Opening DaVinci Resolve...')
  try {
    const result = await electronAPI.davinciOpenProject(davinciProjectName.value)
    if (result.success) {
      toast.success(`Opened project: ${result.projectName}`)
    } else {
      toast.error(result.error || 'Failed to open DaVinci project')
    }
  } catch (error) {
    console.error('DaVinci error:', error)
    toast.error('Failed to connect to DaVinci Resolve')
  } finally {
    davinciLoading.value = false
  }
}

async function createMulticamInDaVinci() {
  if (!electronAPI?.davinciCreateMulticam) return
  
  davinciLoading.value = true
  try {
    // First ensure project is open
    if (electronAPI.davinciOpenProject) {
      await electronAPI.davinciOpenProject(davinciProjectName.value)
    }
    
    // Then create multicam timeline
    const result = await electronAPI.davinciCreateMulticam({
      projectName: davinciProjectName.value,
      clipName: `Multicam_${sessionName.value.replace(/\s+/g, '_')}`,
      syncMethod: 'timecode'
    })
    
    if (result.success) {
      toast.success(`Created timeline: ${result.timelineName}`)
    } else {
      toast.error(result.error || 'Failed to create multicam timeline')
    }
  } catch (error) {
    console.error('DaVinci error:', error)
    toast.error('Failed to create multicam timeline')
  } finally {
    davinciLoading.value = false
  }
}

async function refreshGrowingClips() {
  if (!electronAPI?.davinciRefreshClips) return
  
  davinciLoading.value = true
  toast.info('Refreshing growing clips...')
  try {
    const result = await electronAPI.davinciRefreshClips()
    if (result.success) {
      const count = result.clipsRefreshed || 0
      toast.success(`Refreshed ${count} clip${count !== 1 ? 's' : ''}`)
    } else {
      toast.error(result.error || 'Failed to refresh clips')
    }
  } catch (error) {
    console.error('DaVinci refresh error:', error)
    toast.error('Failed to refresh clips')
  } finally {
    davinciLoading.value = false
  }
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
      
      <!-- DaVinci Resolve Integration (Electron only, during recording) -->
      <div v-if="inElectron" class="sidebar__card sidebar__card--davinci">
        <div class="davinci__header">
          <svg class="davinci__icon" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
          </svg>
          <span class="davinci__label">DaVinci Resolve</span>
        </div>
        <p class="davinci__hint">Edit while recording (mount R58 recordings via SMB)</p>
        <div class="davinci__buttons">
          <button 
            @click="openInDaVinci" 
            :disabled="davinciLoading"
            class="davinci__btn"
          >
            {{ davinciLoading ? 'Opening...' : 'Open Project' }}
          </button>
          <button 
            @click="createMulticamInDaVinci" 
            :disabled="davinciLoading"
            class="davinci__btn davinci__btn--secondary"
          >
            Create Multicam
          </button>
          <button 
            @click="refreshGrowingClips" 
            :disabled="davinciLoading"
            class="davinci__btn davinci__btn--secondary"
            title="Refresh growing clips to update duration"
          >
            {{ davinciLoading ? 'Refreshing...' : 'Refresh Clips' }}
          </button>
        </div>
      </div>
    </template>
    
    <!-- IDLE STATE -->
    <template v-else>
      <!-- Camera Controls -->
      <div class="sidebar__card">
        <div class="sidebar__label">
          Camera Controls
          <button
            @click="openCameraSetup"
            class="camera-setup-btn"
            title="Setup Cameras"
          >
            <svg class="camera-setup-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
              <circle cx="12" cy="12" r="3"/>
            </svg>
          </button>
        </div>
        <div v-if="cameras.length > 0" class="cameras">
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
        <div v-else class="cameras-empty">
          <p class="cameras-empty__text">No cameras configured</p>
          <button @click="openCameraSetup" class="cameras-empty__btn">
            Setup Cameras
          </button>
        </div>
      </div>
      
      <!-- Camera Control Modal -->
      <CameraControlModal
        ref="cameraModalRef"
        :camera-name="selectedCameraForControl"
        @close="closeCameraControl"
      />
      
      <!-- Camera Setup Modal -->
      <CameraSetupModal
        ref="cameraSetupModalRef"
        @updated="onCameraConfigUpdated"
      />
      
      <!-- PTZ Controller Panel -->
      <div v-if="showPTZController" class="sidebar__card">
        <PTZControllerPanel
          :camera-name="selectedCameraForControl"
          @close="showPTZController = false"
        />
      </div>
      
      <!-- PTZ Controller Toggle -->
      <div v-else class="sidebar__card">
        <div class="sidebar__label">PTZ Controller</div>
        <button
          @click="showPTZController = true"
          class="sidebar__btn"
          title="Open PTZ Controller (Gamepad/Joystick)"
        >
          <svg class="sidebar__btn-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.8">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
          </svg>
          Open PTZ Controller
        </button>
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
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.camera-setup-btn {
  padding: 4px 6px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--preke-border, rgba(255,255,255,0.1));
  border-radius: 4px;
  color: var(--preke-text-muted, #888);
  cursor: pointer;
  transition: all 0.15s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.camera-setup-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: var(--preke-gold, #e0a030);
  color: var(--preke-gold, #e0a030);
}

.camera-setup-icon {
  width: 14px;
  height: 14px;
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

.cameras-empty {
  text-align: center;
  padding: 24px 12px;
  color: var(--preke-text-muted, #888);
}

.cameras-empty__text {
  font-size: 12px;
  margin-bottom: 12px;
}

.cameras-empty__btn {
  padding: 8px 16px;
  background: var(--preke-gold, #e0a030);
  border: none;
  border-radius: 6px;
  color: #000;
  font-weight: 600;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.cameras-empty__btn:hover {
  background: #f0b040;
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

/* DaVinci Resolve Integration */
.sidebar__card--davinci {
  background: linear-gradient(135deg, rgba(255, 90, 90, 0.1), rgba(255, 140, 50, 0.1));
  border-color: rgba(255, 100, 100, 0.2);
}

.davinci__header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.davinci__icon {
  width: 18px;
  height: 18px;
  color: #ff6b6b;
}

.davinci__label {
  font-size: 12px;
  font-weight: 600;
  color: var(--preke-text, #fff);
}

.davinci__hint {
  font-size: 11px;
  color: var(--preke-text-muted, #888);
  margin-bottom: 12px;
}

.davinci__buttons {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.davinci__btn {
  width: 100%;
  padding: 10px 12px;
  background: linear-gradient(135deg, #ff6b6b, #ff8c50);
  border: none;
  border-radius: 6px;
  color: #fff;
  font-weight: 600;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.davinci__btn:hover:not(:disabled) {
  filter: brightness(1.1);
  transform: translateY(-1px);
}

.davinci__btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.davinci__btn--secondary {
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 107, 107, 0.3);
  color: var(--preke-text, #fff);
}

.davinci__btn--secondary:hover:not(:disabled) {
  background: rgba(255, 107, 107, 0.2);
  border-color: rgba(255, 107, 107, 0.5);
}
</style>
