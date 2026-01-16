<script setup lang="ts">
/**
 * PTZControllerPanel - Hardware joystick/gamepad PTZ control panel
 * 
 * Provides real-time PTZ control via WebSocket for hardware controllers.
 * Can be used in both Recorder and Mixer views.
 */
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { usePTZController } from '@/composables/usePTZController'
import { useCameraControls } from '@/composables/useCameraControls'
import { toast } from '@/composables/useToast'

const props = defineProps<{
  cameraName?: string | null
}>()

const emit = defineEmits<{
  (e: 'close'): void
}>()

// Camera controls for listing cameras
const { cameras, loadCameras } = useCameraControls()

// PTZ Controller composable
const ptz = usePTZController(props.cameraName || null)

// Selected camera
const selectedCamera = ref<string | null>(props.cameraName || null)

// Gamepad state
const gamepadConnected = computed(() => ptz.gamepadInfo.value !== null)
const gamepadName = computed(() => ptz.gamepadInfo.value?.id || '')

// Available PTZ cameras
const ptzCameras = computed(() => {
  return cameras.value.filter(cam => {
    // Check if camera supports PTZ (OBSbot cameras)
    return cam.type === 'obsbot_tail2' || cam.name.toLowerCase().includes('obsbot')
  })
})

// Connect/disconnect
async function connect() {
  if (!selectedCamera.value) {
    toast.error('Please select a camera first')
    return
  }
  
  await ptz.connect()
  if (ptz.connected.value) {
    ptz.setCamera(selectedCamera.value)
    toast.success('PTZ Controller connected')
  } else {
    toast.error('Failed to connect PTZ controller')
  }
}

function disconnect() {
  ptz.disconnect()
  toast.info('PTZ Controller disconnected')
}

// Start/stop gamepad
function startGamepad() {
  // Try to find first available gamepad
  const gamepads = navigator.getGamepads()
  let gamepadIndex = null
  for (let i = 0; i < gamepads.length; i++) {
    if (gamepads[i]) {
      gamepadIndex = i
      break
    }
  }
  
  if (gamepadIndex === null) {
    toast.error('No gamepad detected. Please connect a gamepad/joystick first.')
    return
  }
  
  ptz.startGamepad(gamepadIndex)
  // Check after a short delay if gamepad was detected
  setTimeout(() => {
    if (ptz.gamepadInfo.value) {
      toast.success(`Gamepad connected: ${ptz.gamepadInfo.value.id}`)
    }
  }, 100)
}

function stopGamepad() {
  ptz.stopGamepad()
  toast.info('Gamepad disconnected')
}

// Manual PTZ control (for testing without gamepad)
const manualPan = ref(0)
const manualTilt = ref(0)
const manualZoom = ref(0)

function sendManualPTZ() {
  if (!selectedCamera.value) {
    toast.error('Please select a camera first')
    return
  }
  
  if (!ptz.connected.value) {
    toast.error('PTZ Controller not connected')
    return
  }
  
  ptz.sendPTZCommand({
    pan: manualPan.value,
    tilt: manualTilt.value,
    zoom: manualZoom.value
  })
}

function handleCameraChange() {
  if (selectedCamera.value && ptz.connected.value) {
    ptz.setCamera(selectedCamera.value)
  }
}

// Load cameras on mount
onMounted(async () => {
  await loadCameras()
  
  // Auto-select first PTZ camera if none selected
  if (!selectedCamera.value && ptzCameras.value.length > 0) {
    selectedCamera.value = ptzCameras.value[0].name
  }
  
  // Don't auto-connect - let user click Connect button
})

// Cleanup on unmount
onUnmounted(() => {
  disconnect()
  stopGamepad()
})

// Watch for camera prop changes
watch(() => props.cameraName, (newName) => {
  if (newName) {
    selectedCamera.value = newName
    if (ptz.connected.value) {
      ptz.setCamera(newName)
    }
  }
})
</script>

<template>
  <div class="ptz-controller-panel">
    <div class="ptz-controller-panel__header">
      <h3 class="ptz-controller-panel__title">PTZ Controller</h3>
      <button
        @click="emit('close')"
        class="ptz-controller-panel__close"
        title="Close"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <div class="ptz-controller-panel__content">
      <!-- Camera Selection -->
      <div class="ptz-controller-panel__section">
        <label class="ptz-controller-panel__label">Camera</label>
        <select
          v-model="selectedCamera"
          class="ptz-controller-panel__select"
          @change="handleCameraChange"
        >
          <option :value="null">Select camera...</option>
          <option
            v-for="cam in ptzCameras"
            :key="cam.name"
            :value="cam.name"
          >
            {{ cam.name }} ({{ cam.connected ? 'Connected' : 'Disconnected' }})
          </option>
        </select>
      </div>

      <!-- Connection Status -->
      <div class="ptz-controller-panel__section">
        <div class="ptz-controller-panel__status">
          <span
            class="ptz-controller-panel__status-dot"
            :class="{
              'ptz-controller-panel__status-dot--connected': ptz.connected.value,
              'ptz-controller-panel__status-dot--disconnected': !ptz.connected.value
            }"
          ></span>
          <span class="ptz-controller-panel__status-text">
            {{ ptz.connected.value ? 'Connected' : 'Disconnected' }}
          </span>
        </div>
        
        <div class="ptz-controller-panel__buttons">
          <button
            @click="connect"
            :disabled="!selectedCamera || ptz.connected.value"
            class="ptz-controller-panel__btn ptz-controller-panel__btn--primary"
          >
            Connect
          </button>
          <button
            @click="disconnect"
            :disabled="!ptz.connected.value"
            class="ptz-controller-panel__btn"
          >
            Disconnect
          </button>
        </div>
      </div>

      <!-- Gamepad Status -->
      <div v-if="gamepadConnected" class="ptz-controller-panel__section">
        <div class="ptz-controller-panel__status">
          <span class="ptz-controller-panel__status-dot ptz-controller-panel__status-dot--connected"></span>
          <span class="ptz-controller-panel__status-text">
            Gamepad: {{ gamepadName }}
          </span>
        </div>
      </div>

      <!-- Manual Controls (for testing) -->
      <div class="ptz-controller-panel__section">
        <label class="ptz-controller-panel__label">Manual Control (Testing)</label>
        <div class="ptz-controller-panel__manual-controls">
          <div class="ptz-controller-panel__axis">
            <label>Pan</label>
            <input
              v-model.number="manualPan"
              type="range"
              min="-1"
              max="1"
              step="0.1"
              class="ptz-controller-panel__slider"
            />
            <span class="ptz-controller-panel__value">{{ manualPan.toFixed(1) }}</span>
          </div>
          <div class="ptz-controller-panel__axis">
            <label>Tilt</label>
            <input
              v-model.number="manualTilt"
              type="range"
              min="-1"
              max="1"
              step="0.1"
              class="ptz-controller-panel__slider"
            />
            <span class="ptz-controller-panel__value">{{ manualTilt.toFixed(1) }}</span>
          </div>
          <div class="ptz-controller-panel__axis">
            <label>Zoom</label>
            <input
              v-model.number="manualZoom"
              type="range"
              min="-1"
              max="1"
              step="0.1"
              class="ptz-controller-panel__slider"
            />
            <span class="ptz-controller-panel__value">{{ manualZoom.toFixed(1) }}</span>
          </div>
          <button
            @click="sendManualPTZ"
            :disabled="!ptz.connected.value || !selectedCamera"
            class="ptz-controller-panel__btn ptz-controller-panel__btn--primary"
          >
            Send Command
          </button>
        </div>
      </div>

      <!-- Gamepad Controls -->
      <div class="ptz-controller-panel__section">
        <div class="ptz-controller-panel__buttons">
          <button
            @click="startGamepad"
            :disabled="gamepadConnected"
            class="ptz-controller-panel__btn"
          >
            Start Gamepad
          </button>
          <button
            @click="stopGamepad"
            :disabled="!gamepadConnected"
            class="ptz-controller-panel__btn"
          >
            Stop Gamepad
          </button>
        </div>
        <p class="ptz-controller-panel__hint">
          Connect a gamepad/joystick and use left stick for pan/tilt, triggers for zoom
        </p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.ptz-controller-panel {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--preke-border, rgba(255,255,255,0.1));
  border-radius: 10px;
  padding: 16px;
  min-width: 320px;
}

.ptz-controller-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.ptz-controller-panel__title {
  font-size: 16px;
  font-weight: 600;
  color: var(--preke-text, #fff);
}

.ptz-controller-panel__close {
  padding: 4px;
  color: var(--preke-text-muted, #888);
  background: transparent;
  border: none;
  cursor: pointer;
  transition: color 0.2s;
}

.ptz-controller-panel__close:hover {
  color: var(--preke-text, #fff);
}

.ptz-controller-panel__content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.ptz-controller-panel__section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ptz-controller-panel__label {
  font-size: 12px;
  font-weight: 500;
  color: var(--preke-text-dim, #aaa);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.ptz-controller-panel__select {
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--preke-border, rgba(255,255,255,0.1));
  border-radius: 6px;
  color: var(--preke-text, #fff);
  font-size: 14px;
}

.ptz-controller-panel__select:focus {
  outline: none;
  border-color: var(--preke-gold, #e0a030);
}

.ptz-controller-panel__status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 6px;
}

.ptz-controller-panel__status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.ptz-controller-panel__status-dot--connected {
  background: var(--preke-green, #4ade80);
  box-shadow: 0 0 8px var(--preke-green, #4ade80);
}

.ptz-controller-panel__status-dot--disconnected {
  background: var(--preke-red, #ef4444);
}

.ptz-controller-panel__status-text {
  font-size: 14px;
  color: var(--preke-text, #fff);
}

.ptz-controller-panel__buttons {
  display: flex;
  gap: 8px;
}

.ptz-controller-panel__btn {
  flex: 1;
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--preke-border, rgba(255,255,255,0.1));
  border-radius: 6px;
  color: var(--preke-text, #fff);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.ptz-controller-panel__btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.1);
  border-color: var(--preke-gold, #e0a030);
}

.ptz-controller-panel__btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.ptz-controller-panel__btn--primary {
  background: var(--preke-gold, #e0a030);
  border-color: var(--preke-gold, #e0a030);
  color: #000;
}

.ptz-controller-panel__btn--primary:hover:not(:disabled) {
  background: #f0b040;
}

.ptz-controller-panel__manual-controls {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.ptz-controller-panel__axis {
  display: flex;
  align-items: center;
  gap: 12px;
}

.ptz-controller-panel__axis label {
  min-width: 50px;
  font-size: 12px;
  color: var(--preke-text-dim, #aaa);
}

.ptz-controller-panel__slider {
  flex: 1;
  height: 4px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
  outline: none;
  -webkit-appearance: none;
}

.ptz-controller-panel__slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 16px;
  height: 16px;
  background: var(--preke-gold, #e0a030);
  border-radius: 50%;
  cursor: pointer;
}

.ptz-controller-panel__slider::-moz-range-thumb {
  width: 16px;
  height: 16px;
  background: var(--preke-gold, #e0a030);
  border-radius: 50%;
  cursor: pointer;
  border: none;
}

.ptz-controller-panel__value {
  min-width: 40px;
  text-align: right;
  font-size: 12px;
  font-family: monospace;
  color: var(--preke-text, #fff);
}

.ptz-controller-panel__hint {
  font-size: 11px;
  color: var(--preke-text-muted, #888);
  margin-top: 4px;
  line-height: 1.4;
}
</style>
