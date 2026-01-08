/**
 * Composable for camera control functionality
 */
import { ref, computed } from 'vue'
import { r58Api } from '@/lib/api'

export interface CameraInfo {
  name: string
  type: 'blackmagic' | 'obsbot_tail2'
  connected: boolean
  settings?: Record<string, any>
}

export interface CameraSettings {
  focus?: { mode: 'auto' | 'manual'; value?: number }
  whiteBalance?: { mode: 'auto' | 'manual' | 'preset'; temperature?: number }
  exposure?: { mode: 'auto' | 'manual'; value?: number }
  iso?: number
  shutter?: number
  iris?: { mode: 'auto' | 'manual'; value?: number }
  gain?: number
  ptz?: { pan: number; tilt: number; zoom: number }
  colorCorrection?: {
    lift?: number[]
    gamma?: number[]
    gain?: number[]
    offset?: number[]
  }
}

export function useCameraControls() {
  const cameras = ref<CameraInfo[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const selectedCamera = ref<string | null>(null)

  // Load list of cameras
  async function loadCameras() {
    loading.value = true
    error.value = null
    try {
      const cameraNames = await r58Api.cameras.list()
      cameras.value = await Promise.all(
        cameraNames.map(async (name) => {
          try {
            const status = await r58Api.cameras.getStatus(name)
            return {
              name: status.name,
              type: status.type as 'blackmagic' | 'obsbot_tail2',
              connected: status.connected,
              settings: status.settings,
            }
          } catch (e) {
            return {
              name,
              type: 'blackmagic' as const,
              connected: false,
            }
          }
        })
      )
    } catch (e: any) {
      error.value = e.message || 'Failed to load cameras'
      console.error('[CameraControls] Failed to load cameras:', e)
    } finally {
      loading.value = false
    }
  }

  // Get camera by name
  const getCamera = computed(() => {
    return (name: string) => cameras.value.find((c) => c.name === name)
  })

  // Check if camera supports a feature
  function supportsFeature(cameraName: string, feature: string): boolean {
    const camera = getCamera.value(cameraName)
    if (!camera) return false

    const bmdFeatures = ['focus', 'iris', 'whiteBalance', 'gain', 'iso', 'shutter', 'colorCorrection']
    const obsbotFeatures = ['focus', 'exposure', 'whiteBalance', 'ptz']

    if (camera.type === 'blackmagic') {
      return bmdFeatures.includes(feature)
    } else if (camera.type === 'obsbot_tail2') {
      return obsbotFeatures.includes(feature)
    }

    return false
  }

  // Control methods
  async function setFocus(cameraName: string, mode: 'auto' | 'manual', value?: number) {
    try {
      await r58Api.cameras.setFocus(cameraName, mode, value)
      await refreshCameraStatus(cameraName)
    } catch (e: any) {
      throw new Error(e.message || 'Failed to set focus')
    }
  }

  async function setWhiteBalance(cameraName: string, mode: 'auto' | 'manual' | 'preset', temperature?: number) {
    try {
      await r58Api.cameras.setWhiteBalance(cameraName, mode, temperature)
      await refreshCameraStatus(cameraName)
    } catch (e: any) {
      throw new Error(e.message || 'Failed to set white balance')
    }
  }

  async function setExposure(cameraName: string, mode: 'auto' | 'manual', value?: number) {
    try {
      await r58Api.cameras.setExposure(cameraName, mode, value)
      await refreshCameraStatus(cameraName)
    } catch (e: any) {
      throw new Error(e.message || 'Failed to set exposure')
    }
  }

  async function setISO(cameraName: string, value: number) {
    try {
      await r58Api.cameras.setISO(cameraName, value)
      await refreshCameraStatus(cameraName)
    } catch (e: any) {
      throw new Error(e.message || 'Failed to set ISO')
    }
  }

  async function setShutter(cameraName: string, value: number) {
    try {
      await r58Api.cameras.setShutter(cameraName, value)
      await refreshCameraStatus(cameraName)
    } catch (e: any) {
      throw new Error(e.message || 'Failed to set shutter')
    }
  }

  async function setIris(cameraName: string, mode: 'auto' | 'manual', value?: number) {
    try {
      await r58Api.cameras.setIris(cameraName, mode, value)
      await refreshCameraStatus(cameraName)
    } catch (e: any) {
      throw new Error(e.message || 'Failed to set iris')
    }
  }

  async function setGain(cameraName: string, value: number) {
    try {
      await r58Api.cameras.setGain(cameraName, value)
      await refreshCameraStatus(cameraName)
    } catch (e: any) {
      throw new Error(e.message || 'Failed to set gain')
    }
  }

  async function setPTZ(cameraName: string, pan: number, tilt: number, zoom: number) {
    try {
      await r58Api.cameras.setPTZ(cameraName, pan, tilt, zoom)
    } catch (e: any) {
      throw new Error(e.message || 'Failed to move PTZ')
    }
  }

  async function recallPTZPreset(cameraName: string, presetId: number) {
    try {
      await r58Api.cameras.recallPTZPreset(cameraName, presetId)
    } catch (e: any) {
      throw new Error(e.message || 'Failed to recall preset')
    }
  }

  async function setColorCorrection(cameraName: string, settings: {
    lift?: number[]
    gamma?: number[]
    gain?: number[]
    offset?: number[]
  }) {
    try {
      await r58Api.cameras.setColorCorrection(cameraName, settings)
      await refreshCameraStatus(cameraName)
    } catch (e: any) {
      throw new Error(e.message || 'Failed to set color correction')
    }
  }

  // Refresh camera status
  async function refreshCameraStatus(cameraName: string) {
    try {
      const status = await r58Api.cameras.getStatus(cameraName)
      const index = cameras.value.findIndex((c) => c.name === cameraName)
      if (index >= 0) {
        cameras.value[index] = {
          name: status.name,
          type: status.type as 'blackmagic' | 'obsbot_tail2',
          connected: status.connected,
          settings: status.settings,
        }
      }
    } catch (e) {
      console.error(`[CameraControls] Failed to refresh status for ${cameraName}:`, e)
    }
  }

  return {
    cameras,
    loading,
    error,
    selectedCamera,
    getCamera,
    supportsFeature,
    loadCameras,
    setFocus,
    setWhiteBalance,
    setExposure,
    setISO,
    setShutter,
    setIris,
    setGain,
    setPTZ,
    recallPTZPreset,
    setColorCorrection,
    refreshCameraStatus,
  }
}
