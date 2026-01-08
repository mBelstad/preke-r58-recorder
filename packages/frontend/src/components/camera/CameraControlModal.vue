<script setup lang="ts">
/**
 * CameraControlModal - Modal for controlling external cameras
 */
import { ref, computed, onMounted, watch } from 'vue'
import BaseModal from '@/components/shared/BaseModal.vue'
import { useCameraControls, type CameraInfo } from '@/composables/useCameraControls'

const props = defineProps<{
  cameraName: string | null
}>()

const emit = defineEmits<{
  (e: 'close'): void
}>()

const modalRef = ref<InstanceType<typeof BaseModal> | null>(null)
const { cameras, loading, error, supportsFeature, loadCameras, getCamera } = useCameraControls()

const activeTab = ref<'basic' | 'advanced' | 'ptz' | 'color'>('basic')
const camera = computed(() => props.cameraName ? getCamera.value(props.cameraName) : null)

// Control state
const focusMode = ref<'auto' | 'manual'>('auto')
const focusValue = ref(0.5)
const whiteBalanceMode = ref<'auto' | 'manual' | 'preset'>('auto')
const whiteBalanceTemp = ref(5600)
const exposureMode = ref<'auto' | 'manual'>('auto')
const exposureValue = ref(0.5)
const isoValue = ref(400)
const shutterValue = ref(1/60)
const irisMode = ref<'auto' | 'manual'>('auto')
const irisValue = ref(2.8)
const gainValue = ref(0)
const ptzPan = ref(0)
const ptzTilt = ref(0)
const ptzZoom = ref(0)

const saving = ref(false)

// Load cameras and camera settings on mount
onMounted(async () => {
  await loadCameras()
  if (props.cameraName && camera.value) {
    await loadCameraSettings()
  }
})

watch(() => props.cameraName, async (newName) => {
  if (newName && camera.value) {
    await loadCameraSettings()
  }
})

async function loadCameraSettings() {
  if (!props.cameraName || !camera.value) return
  
  // Load current settings from camera
  // This would be implemented to fetch actual values from the API
  // For now, we'll use defaults
}

function open() {
  modalRef.value?.open()
}

function close() {
  modalRef.value?.close()
  emit('close')
}

// Get control methods from composable
const {
  setFocus: setFocusControl,
  setWhiteBalance: setWhiteBalanceControl,
  setExposure: setExposureControl,
  setISO: setISOControl,
  setShutter: setShutterControl,
  setIris: setIrisControl,
  setGain: setGainControl,
  setPTZ: setPTZControl,
} = useCameraControls()

// Control methods
async function saveFocus() {
  if (!props.cameraName) return
  saving.value = true
  try {
    await setFocusControl(props.cameraName, focusMode.value, focusMode.value === 'manual' ? focusValue.value : undefined)
  } catch (e: any) {
    alert(`Failed to set focus: ${e.message}`)
  } finally {
    saving.value = false
  }
}

async function saveWhiteBalance() {
  if (!props.cameraName) return
  saving.value = true
  try {
    await setWhiteBalanceControl(props.cameraName, whiteBalanceMode.value, whiteBalanceMode.value === 'manual' ? whiteBalanceTemp.value : undefined)
  } catch (e: any) {
    alert(`Failed to set white balance: ${e.message}`)
  } finally {
    saving.value = false
  }
}

async function saveExposure() {
  if (!props.cameraName) return
  saving.value = true
  try {
    await setExposureControl(props.cameraName, exposureMode.value, exposureMode.value === 'manual' ? exposureValue.value : undefined)
  } catch (e: any) {
    alert(`Failed to set exposure: ${e.message}`)
  } finally {
    saving.value = false
  }
}

async function saveISO() {
  if (!props.cameraName) return
  saving.value = true
  try {
    await setISOControl(props.cameraName, isoValue.value)
  } catch (e: any) {
    alert(`Failed to set ISO: ${e.message}`)
  } finally {
    saving.value = false
  }
}

async function saveShutter() {
  if (!props.cameraName) return
  saving.value = true
  try {
    await setShutterControl(props.cameraName, shutterValue.value)
  } catch (e: any) {
    alert(`Failed to set shutter: ${e.message}`)
  } finally {
    saving.value = false
  }
}

async function saveIris() {
  if (!props.cameraName) return
  saving.value = true
  try {
    await setIrisControl(props.cameraName, irisMode.value, irisMode.value === 'manual' ? irisValue.value : undefined)
  } catch (e: any) {
    alert(`Failed to set iris: ${e.message}`)
  } finally {
    saving.value = false
  }
}

async function saveGain() {
  if (!props.cameraName) return
  saving.value = true
  try {
    await setGainControl(props.cameraName, gainValue.value)
  } catch (e: any) {
    alert(`Failed to set gain: ${e.message}`)
  } finally {
    saving.value = false
  }
}

async function movePTZ() {
  if (!props.cameraName) return
  try {
    await setPTZControl(props.cameraName, ptzPan.value, ptzTilt.value, ptzZoom.value)
  } catch (e: any) {
    alert(`Failed to move PTZ: ${e.message}`)
  }
}

defineExpose({ open, close })
</script>

<template>
  <BaseModal
    ref="modalRef"
    title="Camera Controls"
    size="xl"
    @close="emit('close')"
  >
    <template #header>
      <div class="flex items-center justify-between w-full">
        <div>
          <h2 class="text-lg font-semibold text-preke-text">
            {{ cameraName || 'Camera Controls' }}
          </h2>
          <p v-if="camera" class="text-sm text-preke-text-muted mt-1">
            {{ camera.type === 'blackmagic' ? 'Blackmagic Design' : 'OBSbot Tail 2' }}
            <span :class="camera.connected ? 'text-green-500' : 'text-red-500'" class="ml-2">
              {{ camera.connected ? '● Connected' : '○ Disconnected' }}
            </span>
          </p>
        </div>
      </div>
    </template>

    <div v-if="loading" class="py-8 text-center text-preke-text-muted">
      Loading camera settings...
    </div>

    <div v-else-if="error" class="py-8 text-center text-red-400">
      {{ error }}
    </div>

    <div v-else-if="!camera" class="py-8 text-center text-preke-text-muted">
      Camera not found
    </div>

    <div v-else class="camera-controls">
      <!-- Tabs -->
      <div class="tabs">
        <button
          v-if="supportsFeature(cameraName!, 'focus') || supportsFeature(cameraName!, 'whiteBalance') || supportsFeature(cameraName!, 'exposure')"
          :class="['tab', { 'tab--active': activeTab === 'basic' }]"
          @click="activeTab = 'basic'"
        >
          Basic
        </button>
        <button
          v-if="supportsFeature(cameraName!, 'iso') || supportsFeature(cameraName!, 'shutter') || supportsFeature(cameraName!, 'iris') || supportsFeature(cameraName!, 'gain')"
          :class="['tab', { 'tab--active': activeTab === 'advanced' }]"
          @click="activeTab = 'advanced'"
        >
          Advanced
        </button>
        <button
          v-if="supportsFeature(cameraName!, 'ptz')"
          :class="['tab', { 'tab--active': activeTab === 'ptz' }]"
          @click="activeTab = 'ptz'"
        >
          PTZ
        </button>
        <button
          v-if="supportsFeature(cameraName!, 'colorCorrection')"
          :class="['tab', { 'tab--active': activeTab === 'color' }]"
          @click="activeTab = 'color'"
        >
          Color
        </button>
      </div>

      <!-- Basic Tab -->
      <div v-if="activeTab === 'basic'" class="tab-content">
        <!-- Focus -->
        <div v-if="supportsFeature(cameraName!, 'focus')" class="control-group">
          <label class="control-label">Focus</label>
          <div class="control-row">
            <button
              :class="['mode-btn', { 'mode-btn--active': focusMode === 'auto' }]"
              @click="focusMode = 'auto'"
            >
              Auto
            </button>
            <button
              :class="['mode-btn', { 'mode-btn--active': focusMode === 'manual' }]"
              @click="focusMode = 'manual'"
            >
              Manual
            </button>
          </div>
          <div v-if="focusMode === 'manual'" class="control-slider">
            <input
              v-model.number="focusValue"
              type="range"
              min="0"
              max="1"
              step="0.01"
              class="slider"
            />
            <span class="slider-value">{{ Math.round(focusValue * 100) }}%</span>
          </div>
          <button @click="saveFocus" :disabled="saving" class="save-btn">
            {{ saving ? 'Saving...' : 'Save Focus' }}
          </button>
        </div>

        <!-- White Balance -->
        <div v-if="supportsFeature(cameraName!, 'whiteBalance')" class="control-group">
          <label class="control-label">White Balance</label>
          <div class="control-row">
            <button
              :class="['mode-btn', { 'mode-btn--active': whiteBalanceMode === 'auto' }]"
              @click="whiteBalanceMode = 'auto'"
            >
              Auto
            </button>
            <button
              :class="['mode-btn', { 'mode-btn--active': whiteBalanceMode === 'manual' }]"
              @click="whiteBalanceMode = 'manual'"
            >
              Manual
            </button>
          </div>
          <div v-if="whiteBalanceMode === 'manual'" class="control-input">
            <input
              v-model.number="whiteBalanceTemp"
              type="number"
              min="2000"
              max="10000"
              step="100"
              class="input"
            />
            <span class="input-unit">K</span>
          </div>
          <button @click="saveWhiteBalance" :disabled="saving" class="save-btn">
            {{ saving ? 'Saving...' : 'Save White Balance' }}
          </button>
        </div>

        <!-- Exposure (OBSbot) -->
        <div v-if="supportsFeature(cameraName!, 'exposure')" class="control-group">
          <label class="control-label">Exposure</label>
          <div class="control-row">
            <button
              :class="['mode-btn', { 'mode-btn--active': exposureMode === 'auto' }]"
              @click="exposureMode = 'auto'"
            >
              Auto
            </button>
            <button
              :class="['mode-btn', { 'mode-btn--active': exposureMode === 'manual' }]"
              @click="exposureMode = 'manual'"
            >
              Manual
            </button>
          </div>
          <div v-if="exposureMode === 'manual'" class="control-slider">
            <input
              v-model.number="exposureValue"
              type="range"
              min="0"
              max="1"
              step="0.01"
              class="slider"
            />
            <span class="slider-value">{{ Math.round(exposureValue * 100) }}%</span>
          </div>
          <button @click="saveExposure" :disabled="saving" class="save-btn">
            {{ saving ? 'Saving...' : 'Save Exposure' }}
          </button>
        </div>
      </div>

      <!-- Advanced Tab -->
      <div v-if="activeTab === 'advanced'" class="tab-content">
        <!-- ISO -->
        <div v-if="supportsFeature(cameraName!, 'iso')" class="control-group">
          <label class="control-label">ISO</label>
          <div class="control-input">
            <input
              v-model.number="isoValue"
              type="number"
              min="100"
              max="25600"
              step="100"
              class="input"
            />
          </div>
          <button @click="saveISO" :disabled="saving" class="save-btn">
            {{ saving ? 'Saving...' : 'Save ISO' }}
          </button>
        </div>

        <!-- Shutter -->
        <div v-if="supportsFeature(cameraName!, 'shutter')" class="control-group">
          <label class="control-label">Shutter Speed</label>
          <div class="control-input">
            <input
              v-model.number="shutterValue"
              type="number"
              min="0.0001"
              max="1"
              step="0.0001"
              class="input"
            />
            <span class="input-unit">s</span>
          </div>
          <button @click="saveShutter" :disabled="saving" class="save-btn">
            {{ saving ? 'Saving...' : 'Save Shutter' }}
          </button>
        </div>

        <!-- Iris -->
        <div v-if="supportsFeature(cameraName!, 'iris')" class="control-group">
          <label class="control-label">Iris</label>
          <div class="control-row">
            <button
              :class="['mode-btn', { 'mode-btn--active': irisMode === 'auto' }]"
              @click="irisMode = 'auto'"
            >
              Auto
            </button>
            <button
              :class="['mode-btn', { 'mode-btn--active': irisMode === 'manual' }]"
              @click="irisMode = 'manual'"
            >
              Manual
            </button>
          </div>
          <div v-if="irisMode === 'manual'" class="control-input">
            <input
              v-model.number="irisValue"
              type="number"
              min="1.4"
              max="22"
              step="0.1"
              class="input"
            />
            <span class="input-unit">f/</span>
          </div>
          <button @click="saveIris" :disabled="saving" class="save-btn">
            {{ saving ? 'Saving...' : 'Save Iris' }}
          </button>
        </div>

        <!-- Gain -->
        <div v-if="supportsFeature(cameraName!, 'gain')" class="control-group">
          <label class="control-label">Gain</label>
          <div class="control-input">
            <input
              v-model.number="gainValue"
              type="number"
              min="-12"
              max="36"
              step="0.1"
              class="input"
            />
            <span class="input-unit">dB</span>
          </div>
          <button @click="saveGain" :disabled="saving" class="save-btn">
            {{ saving ? 'Saving...' : 'Save Gain' }}
          </button>
        </div>
      </div>

      <!-- PTZ Tab -->
      <div v-if="activeTab === 'ptz'" class="tab-content">
        <div class="control-group">
          <label class="control-label">Pan/Tilt/Zoom</label>
          <div class="ptz-controls">
            <div class="ptz-axis">
              <label>Pan</label>
              <input
                v-model.number="ptzPan"
                type="range"
                min="-1"
                max="1"
                step="0.1"
                class="slider"
              />
              <span class="slider-value">{{ ptzPan.toFixed(1) }}</span>
            </div>
            <div class="ptz-axis">
              <label>Tilt</label>
              <input
                v-model.number="ptzTilt"
                type="range"
                min="-1"
                max="1"
                step="0.1"
                class="slider"
              />
              <span class="slider-value">{{ ptzTilt.toFixed(1) }}</span>
            </div>
            <div class="ptz-axis">
              <label>Zoom</label>
              <input
                v-model.number="ptzZoom"
                type="range"
                min="-1"
                max="1"
                step="0.1"
                class="slider"
              />
              <span class="slider-value">{{ ptzZoom.toFixed(1) }}</span>
            </div>
          </div>
          <button @click="movePTZ" class="save-btn">
            Move PTZ
          </button>
        </div>
      </div>

      <!-- Color Tab -->
      <div v-if="activeTab === 'color'" class="tab-content">
        <div class="control-group">
          <p class="text-preke-text-muted text-sm">
            Color correction controls coming soon
          </p>
        </div>
      </div>
    </div>
  </BaseModal>
</template>

<style scoped>
.camera-controls {
  min-height: 400px;
}

.tabs {
  display: flex;
  gap: 8px;
  border-bottom: 1px solid var(--preke-border, rgba(255,255,255,0.1));
  margin-bottom: 24px;
}

.tab {
  padding: 12px 20px;
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  color: var(--preke-text-muted, #888);
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;
}

.tab:hover {
  color: var(--preke-text, #fff);
}

.tab--active {
  color: var(--preke-text, #fff);
  border-bottom-color: var(--preke-gold, #e0a030);
}

.tab-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.control-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.control-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--preke-text, #fff);
}

.control-row {
  display: flex;
  gap: 8px;
}

.mode-btn {
  flex: 1;
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--preke-border, rgba(255,255,255,0.1));
  border-radius: 6px;
  color: var(--preke-text-muted, #888);
  cursor: pointer;
  transition: all 0.2s;
}

.mode-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: var(--preke-text, #fff);
}

.mode-btn--active {
  background: rgba(34, 197, 94, 0.2);
  border-color: rgba(34, 197, 94, 0.4);
  color: var(--preke-green, #22c55e);
}

.control-slider {
  display: flex;
  align-items: center;
  gap: 12px;
}

.slider {
  flex: 1;
  height: 6px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
  outline: none;
  -webkit-appearance: none;
}

.slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 16px;
  height: 16px;
  background: var(--preke-gold, #e0a030);
  border-radius: 50%;
  cursor: pointer;
}

.slider::-moz-range-thumb {
  width: 16px;
  height: 16px;
  background: var(--preke-gold, #e0a030);
  border-radius: 50%;
  cursor: pointer;
  border: none;
}

.slider-value {
  min-width: 50px;
  text-align: right;
  font-size: 13px;
  color: var(--preke-text-muted, #888);
  font-family: monospace;
}

.control-input {
  display: flex;
  align-items: center;
  gap: 8px;
}

.input {
  flex: 1;
  padding: 8px 12px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid var(--preke-border, rgba(255,255,255,0.1));
  border-radius: 6px;
  color: var(--preke-text, #fff);
  font-size: 14px;
}

.input:focus {
  outline: none;
  border-color: var(--preke-gold, #e0a030);
}

.input-unit {
  font-size: 13px;
  color: var(--preke-text-muted, #888);
}

.save-btn {
  padding: 10px 20px;
  background: var(--preke-gold, #e0a030);
  border: none;
  border-radius: 6px;
  color: #000;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.save-btn:hover:not(:disabled) {
  background: #f0b040;
}

.save-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.ptz-controls {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.ptz-axis {
  display: flex;
  align-items: center;
  gap: 12px;
}

.ptz-axis label {
  min-width: 60px;
  font-size: 13px;
  color: var(--preke-text-muted, #888);
}
</style>
