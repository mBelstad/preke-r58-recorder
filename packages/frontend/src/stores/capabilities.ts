import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { buildApiUrl, hasDeviceConfigured, isUsingFrpFallback, tryDirectConnection } from '@/lib/api'
import { getCameraLabel } from '@/lib/cameraLabels'

export interface RevealJsInfo {
  available: boolean
  demo_url?: string
  graphics_url?: string
}

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
  current_mode: string
  reveal_js?: RevealJsInfo
}

export interface InputCapability {
  id: string
  type: string
  label: string
  max_resolution: string
  supports_audio: boolean
  device_path: string | null
  status: string
  has_signal: boolean
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

// Use shared camera labels from @/lib/cameraLabels

export const useCapabilitiesStore = defineStore('capabilities', () => {
  const capabilities = ref<DeviceCapabilities | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const mixerEnabled = computed(() => capabilities.value?.mixer_available ?? false)
  const recorderEnabled = computed(() => capabilities.value?.recorder_available ?? true)
  const vdoNinjaEnabled = computed(() => capabilities.value?.vdoninja?.enabled ?? true)
  const storagePercent = computed(() => {
    if (!capabilities.value || !capabilities.value.storage_total_gb) return 0
    const used = capabilities.value.storage_total_gb - capabilities.value.storage_available_gb
    return Math.round((used / capabilities.value.storage_total_gb) * 100)
  })

  async function fetchCapabilities() {
    // Don't fetch if no device is configured (Electron mode)
    if (!hasDeviceConfigured()) {
      console.log('[Capabilities] No device configured, skipping fetch')
      return
    }
    
    loading.value = true
    error.value = null
    
    try {
      // Try to fetch from /api/v1/capabilities first (more complete)
      // Fallback to individual endpoints if not available
      let fullCapabilities: any = null
      try {
        const capabilitiesRes = await fetch(await buildApiUrl('/api/v1/capabilities'))
        if (capabilitiesRes.ok) {
          fullCapabilities = await capabilitiesRes.json()
        }
      } catch (e) {
        console.log('[Capabilities] /api/v1/capabilities not available, using individual endpoints')
      }

      // Fetch from multiple endpoints and combine
      const [healthRes, modeRes, ingestRes, triggerRes] = await Promise.all([
        fetch(await buildApiUrl('/health')),
        fetch(await buildApiUrl('/api/mode/status')),
        fetch(await buildApiUrl('/api/ingest/status')),
        fetch(await buildApiUrl('/api/trigger/status')), // Includes disk info
      ])

      const health = healthRes.ok ? await healthRes.json() : {}
      const mode = modeRes.ok ? await modeRes.json() : {}
      const ingest = ingestRes.ok ? await ingestRes.json() : { cameras: {} }
      const trigger = triggerRes.ok ? await triggerRes.json() : { disk: null }

      // Build inputs from ingest status
      const inputs: InputCapability[] = Object.entries(ingest.cameras || {}).map(([id, cam]: [string, any]) => ({
        id,
        type: 'hdmi',
        label: getCameraLabel(id),
        max_resolution: cam.resolution?.formatted || '4K',
        supports_audio: true,
        device_path: cam.device || null,
        status: cam.status || 'unknown',
        has_signal: cam.has_signal || false,
      }))

      // Use full capabilities if available, otherwise construct from individual endpoints
      if (fullCapabilities) {
        // Use the complete capabilities from /api/v1/capabilities
        // IMPORTANT: Merge current_mode from mode endpoint since /api/v1/capabilities doesn't include it
        capabilities.value = {
          ...fullCapabilities,
          inputs, // Use inputs from ingest status (more detailed)
          current_mode: mode.current_mode || fullCapabilities.current_mode || 'recorder', // Merge from mode endpoint
          reveal_js: fullCapabilities.reveal_js || health.reveal_js || { available: false },
        }
      } else {
        // Construct capabilities from available data (fallback)
        // Get storage info from trigger status (disk field)
        const diskInfo = trigger.disk || {}
        const storageTotalGb = diskInfo.total_gb || 0
        const storageAvailableGb = diskInfo.free_gb || 0
        
        capabilities.value = {
          device_id: 'r58-device',
          device_name: 'Preke R58',
          platform: health.platform || 'R58',
          api_version: '2.0',
          mixer_available: mode.available_modes?.includes('mixer') ?? true,
          recorder_available: mode.available_modes?.includes('recorder') ?? true,
          graphics_available: true, // Graphics endpoints exist
          fleet_agent_connected: false,
          inputs,
          codecs: [
            { id: 'h264', name: 'H.264', hardware_accelerated: true, max_bitrate_kbps: 50000 },
          ],
          preview_modes: [
            { id: 'whep', protocol: 'WebRTC', latency_ms: 100, url_template: '/{cam_id}/whep' },
          ],
          vdoninja: {
            enabled: true,
            host: 'app.itagenten.no/vdo',
            port: 443,
            room: 'studio',
          },
          mediamtx_base_url: 'rtsp://127.0.0.1:8554',
          max_simultaneous_recordings: 4,
          max_output_resolution: '4K',
          storage_total_gb: storageTotalGb,
          storage_available_gb: storageAvailableGb,
          current_mode: mode.current_mode || 'recorder',
          reveal_js: health.reveal_js || { available: false },
        }
      }

      error.value = null
      
      // If using FRP fallback, periodically try to recover P2P connection
      if (isUsingFrpFallback()) {
        console.log('[Capabilities] Currently using FRP fallback, checking if P2P is available...')
        tryDirectConnection().then(success => {
          if (success) {
            console.log('[Capabilities] P2P connection recovered! WHEP will now use direct connection.')
          }
        }).catch(() => {
          // Ignore - P2P not available
        })
      }
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

