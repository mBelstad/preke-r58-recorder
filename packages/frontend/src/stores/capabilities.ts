import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface DeviceCapabilities {
  device_id: string
  device_name: string
  platform: string
  api_version: string
  mixer_available: boolean
  recorder_available: boolean
  graphics_available: boolean
  fleet_agent_connected: boolean
  inputs: InputCapability[]
  codecs: CodecCapability[]
  preview_modes: PreviewMode[]
  vdoninja: VdoNinjaCapability
  mediamtx_base_url: string
  max_simultaneous_recordings: number
  max_output_resolution: string
  storage_total_gb: number
  storage_available_gb: number
}

export interface InputCapability {
  id: string
  type: string
  label: string
  max_resolution: string
  supports_audio: boolean
  device_path: string | null
}

export interface CodecCapability {
  id: string
  name: string
  hardware_accelerated: boolean
  max_bitrate_kbps: number
}

export interface PreviewMode {
  id: string
  protocol: string
  latency_ms: number
  url_template: string
}

export interface VdoNinjaCapability {
  enabled: boolean
  host: string
  port: number
  room: string
}

export const useCapabilitiesStore = defineStore('capabilities', () => {
  const capabilities = ref<DeviceCapabilities | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const mixerEnabled = computed(() => capabilities.value?.mixer_available ?? false)
  const recorderEnabled = computed(() => capabilities.value?.recorder_available ?? true)
  const vdoNinjaEnabled = computed(() => capabilities.value?.vdoninja.enabled ?? false)
  const storagePercent = computed(() => {
    if (!capabilities.value) return 0
    const used = capabilities.value.storage_total_gb - capabilities.value.storage_available_gb
    return Math.round((used / capabilities.value.storage_total_gb) * 100)
  })

  async function fetchCapabilities() {
    loading.value = true
    error.value = null
    
    try {
      const response = await fetch('/api/v1/capabilities')
      if (!response.ok) throw new Error('Failed to fetch capabilities')
      
      capabilities.value = await response.json()
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Unknown error'
      console.error('Failed to fetch capabilities:', e)
    } finally {
      loading.value = false
    }
  }

  return {
    capabilities,
    loading,
    error,
    mixerEnabled,
    recorderEnabled,
    vdoNinjaEnabled,
    storagePercent,
    fetchCapabilities,
  }
})

