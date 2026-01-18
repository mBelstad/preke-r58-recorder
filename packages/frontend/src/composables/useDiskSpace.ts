/**
 * Disk Space Monitor
 * 
 * Monitors available disk space and provides warnings before recording.
 * Thresholds:
 * - >= 10GB: OK (green)
 * - 2-10GB: Warning (yellow) - can proceed with caution
 * - < 2GB: Critical (red) - blocked from starting
 * 
 * FIXED: State is now lazily initialized to avoid TDZ issues
 * in minified builds.
 */
import { ref, computed, type Ref } from 'vue'
import { r58Api } from '@/lib/api'

export interface DiskSpaceStatus {
  available_gb: number
  total_gb: number
  used_percent: number
  recording_path: string
}

// Singleton state (lazily initialized)
let _diskSpace: Ref<DiskSpaceStatus | null> | null = null
let _isLoading: Ref<boolean> | null = null
let _lastCheck: Ref<Date | null> | null = null
let _error: Ref<string | null> | null = null

function getDiskSpaceRef(): Ref<DiskSpaceStatus | null> {
  if (!_diskSpace) _diskSpace = ref<DiskSpaceStatus | null>(null)
  return _diskSpace
}

function getIsLoading(): Ref<boolean> {
  if (!_isLoading) _isLoading = ref(false)
  return _isLoading
}

function getLastCheckRef(): Ref<Date | null> {
  if (!_lastCheck) _lastCheck = ref<Date | null>(null)
  return _lastCheck
}

function getError(): Ref<string | null> {
  if (!_error) _error = ref<string | null>(null)
  return _error
}

// Thresholds in GB
const WARNING_THRESHOLD_GB = 10
const CRITICAL_THRESHOLD_GB = 2

// Estimated recording rate (MB/s) for time estimation
const ESTIMATED_RATE_MBS = 25 // ~25 MB/s for 1080p30 x 4 inputs

export function useDiskSpace() {
  const diskSpace = getDiskSpaceRef()
  const isLoading = getIsLoading()
  const lastCheck = getLastCheckRef()
  const error = getError()
  const status = computed(() => {
    if (!diskSpace.value) return 'unknown'
    if (diskSpace.value.available_gb < CRITICAL_THRESHOLD_GB) return 'critical'
    if (diskSpace.value.available_gb < WARNING_THRESHOLD_GB) return 'warning'
    return 'ok'
  })

  const canStartRecording = computed(() => {
    if (!diskSpace.value) return true // Allow if unknown (API might be unavailable)
    return diskSpace.value.available_gb >= CRITICAL_THRESHOLD_GB
  })

  const estimatedRecordingTime = computed(() => {
    if (!diskSpace.value) return null
    
    const availableBytes = diskSpace.value.available_gb * 1024 * 1024 * 1024
    const rateBytes = ESTIMATED_RATE_MBS * 1024 * 1024
    const seconds = availableBytes / rateBytes
    
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    
    if (hours > 24) {
      return `${Math.floor(hours / 24)}d ${hours % 24}h`
    }
    if (hours > 0) {
      return `${hours}h ${minutes}m`
    }
    return `${minutes}m`
  })

  const statusColor = computed(() => {
    switch (status.value) {
      case 'ok': return 'emerald'
      case 'warning': return 'amber'
      case 'critical': return 'red'
      default: return 'zinc'
    }
  })

  const warningMessage = computed(() => {
    if (!diskSpace.value) return null
    
    if (status.value === 'critical') {
      return `Disk space critically low (${diskSpace.value.available_gb.toFixed(1)} GB). Cannot start recording.`
    }
    if (status.value === 'warning') {
      return `Low disk space (${diskSpace.value.available_gb.toFixed(1)} GB). Estimated recording time: ${estimatedRecordingTime.value}`
    }
    return null
  })

  async function checkDiskSpace(): Promise<DiskSpaceStatus | null> {
    isLoading.value = true
    error.value = null
    
    try {
      // Call the degradation API which includes disk info
      const response = await r58Api.getDegradation()
      
      // Extract disk info from degradation response
      if (response.resources && response.resources.disk_free_gb !== undefined) {
        // Use the actual disk_free_gb from degradation API
        const availableGb = response.resources.disk_free_gb
        // Estimate total from free (assume ~80% typical usage for estimation)
        const estimatedTotalGb = availableGb * 3 // Rough estimate
        
        diskSpace.value = {
          available_gb: availableGb,
          total_gb: estimatedTotalGb,
          used_percent: 100 - ((availableGb / estimatedTotalGb) * 100),
          recording_path: '/opt/r58-app/shared/recordings',
        }
      }
      
      lastCheck.value = new Date()
      return diskSpace.value
    } catch (e: any) {
      error.value = e.message || 'Failed to check disk space'
      console.error('Failed to check disk space:', e)
      return null
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Preflight check before starting recording
   * Returns true if recording can proceed, false otherwise
   */
  async function preflightCheck(): Promise<{ ok: boolean; message?: string }> {
    await checkDiskSpace()
    
    if (!diskSpace.value) {
      // If we can't check, allow recording but warn
      return { ok: true, message: 'Could not verify disk space. Proceeding with caution.' }
    }
    
    if (status.value === 'critical') {
      return { 
        ok: false, 
        message: `Insufficient disk space (${diskSpace.value.available_gb.toFixed(1)} GB). Need at least ${CRITICAL_THRESHOLD_GB} GB to start recording.` 
      }
    }
    
    if (status.value === 'warning') {
      return { 
        ok: true, 
        message: `Low disk space warning: ${diskSpace.value.available_gb.toFixed(1)} GB available. Estimated recording time: ${estimatedRecordingTime.value}` 
      }
    }
    
    return { ok: true }
  }

  return {
    diskSpace,
    isLoading,
    lastCheck,
    error,
    status,
    statusColor,
    canStartRecording,
    estimatedRecordingTime,
    warningMessage,
    checkDiskSpace,
    preflightCheck,
  }
}

