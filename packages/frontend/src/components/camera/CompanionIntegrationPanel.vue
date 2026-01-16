<template>
  <div class="companion-panel">
    <div class="panel-header">
      <h3 class="panel-title">
        <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <rect x="3" y="3" width="18" height="18" rx="2" stroke-width="2"/>
          <path d="M9 9h6v6H9z" stroke-width="2"/>
        </svg>
        Bitfocus Companion Integration
      </h3>
      <button class="info-btn" @click="showHelp = !showHelp" :aria-label="showHelp ? 'Hide help' : 'Show help'">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"/>
          <path d="M12 16v-4M12 8h.01"/>
        </svg>
      </button>
    </div>

    <div v-if="showHelp" class="help-section">
      <p class="help-text">
        Control cameras via Bitfocus Companion using HTTP requests. Add an HTTP instance in Companion
        pointing to <code>{{ apiBaseUrl }}</code> and use the endpoints below.
      </p>
    </div>

    <div class="camera-list">
      <div v-for="camera in cameras" :key="camera.name" class="camera-card">
        <div class="camera-header">
          <div class="camera-info">
            <span class="camera-name">{{ camera.name }}</span>
            <span class="camera-type">{{ formatCameraType(camera.type) }}</span>
            <span :class="['status-indicator', camera.connected ? 'connected' : 'disconnected']">
              {{ camera.connected ? '● Connected' : '○ Disconnected' }}
            </span>
          </div>
        </div>

        <div class="endpoints-section">
          <h4 class="section-title">Available Endpoints</h4>
          
          <div class="endpoint-group">
            <div class="endpoint-item" v-for="endpoint in getEndpointsForCamera(camera)" :key="endpoint.method + endpoint.path">
              <div class="endpoint-method" :class="endpoint.method.toLowerCase()">
                {{ endpoint.method }}
              </div>
              <div class="endpoint-path">
                <code>{{ endpoint.path }}</code>
              </div>
              <button 
                class="copy-btn" 
                @click="copyToClipboard(endpoint.example)"
                :title="'Copy example to clipboard'"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
                </svg>
              </button>
            </div>
          </div>
        </div>

        <div class="quick-actions">
          <h4 class="section-title">Quick Actions</h4>
          <div class="action-buttons">
            <button 
              v-for="action in getQuickActionsForCamera(camera)" 
              :key="action.label"
              class="action-btn"
              @click="copyToClipboard(action.example)"
            >
              {{ action.label }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="cameras.length === 0" class="empty-state">
      <svg class="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>
        <circle cx="12" cy="10" r="3"/>
      </svg>
      <p>No external cameras configured</p>
      <p class="empty-hint">Add cameras in <code>config.yml</code> to enable Companion integration</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useCameraControls, type CameraInfo } from '@/composables/useCameraControls'

const { cameras, loadCameras } = useCameraControls()
const showHelp = ref(false)

const apiBaseUrl = computed(() => {
  if (typeof window !== 'undefined') {
    return window.location.origin
  }
  return 'https://app.itagenten.no'
})

function formatCameraType(type: string): string {
  const types: Record<string, string> = {
    blackmagic: 'Blackmagic Studio 4K Pro',
    obsbot_tail2: 'OBSbot Tail 2',
    sony_fx30: 'Sony FX30'
  }
  return types[type] || type
}

function getEndpointsForCamera(camera: CameraInfo) {
  const base = `${apiBaseUrl.value}/api/v1/cameras/${camera.name}`
  const endpoints: Array<{ method: string; path: string; example: string }> = []

  // Focus
  endpoints.push({
    method: 'PUT',
    path: `${base}/settings/focus`,
    example: JSON.stringify({ mode: 'auto' }, null, 2)
  })
  endpoints.push({
    method: 'PUT',
    path: `${base}/settings/focus`,
    example: JSON.stringify({ mode: 'manual', value: 0.5 }, null, 2)
  })

  // White Balance
  endpoints.push({
    method: 'PUT',
    path: `${base}/settings/whiteBalance`,
    example: JSON.stringify({ mode: 'auto' }, null, 2)
  })
  endpoints.push({
    method: 'PUT',
    path: `${base}/settings/whiteBalance`,
    example: JSON.stringify({ mode: 'manual', temperature: 5600 }, null, 2)
  })

  // Exposure (OBSbot/Sony)
  if (camera.type === 'obsbot_tail2' || camera.type === 'sony_fx30') {
    endpoints.push({
      method: 'PUT',
      path: `${base}/settings/exposure`,
      example: JSON.stringify({ mode: 'auto' }, null, 2)
    })
  }

  // ISO (Blackmagic/Sony)
  if (camera.type === 'blackmagic' || camera.type === 'sony_fx30') {
    endpoints.push({
      method: 'PUT',
      path: `${base}/settings/iso`,
      example: JSON.stringify({ value: 400 }, null, 2)
    })
  }

  // Shutter (Blackmagic/Sony)
  if (camera.type === 'blackmagic' || camera.type === 'sony_fx30') {
    endpoints.push({
      method: 'PUT',
      path: `${base}/settings/shutter`,
      example: JSON.stringify({ value: 0.0167 }, null, 2)
    })
  }

  // Iris (Blackmagic only)
  if (camera.type === 'blackmagic') {
    endpoints.push({
      method: 'PUT',
      path: `${base}/settings/iris`,
      example: JSON.stringify({ mode: 'auto' }, null, 2)
    })
    endpoints.push({
      method: 'PUT',
      path: `${base}/settings/gain`,
      example: JSON.stringify({ value: 0 }, null, 2)
    })
  }

  // PTZ (OBSbot/Sony)
  if (camera.type === 'obsbot_tail2' || camera.type === 'sony_fx30') {
    endpoints.push({
      method: 'PUT',
      path: `${base}/settings/ptz`,
      example: JSON.stringify({ pan: 0.5, tilt: -0.3, zoom: 0.2 }, null, 2)
    })
    endpoints.push({
      method: 'PUT',
      path: `${base}/settings/ptz/preset/1`,
      example: JSON.stringify({}, null, 2)
    })
  }

  return endpoints
}

function getQuickActionsForCamera(camera: CameraInfo) {
  const base = `${apiBaseUrl.value}/api/v1/cameras/${camera.name}`
  const actions: Array<{ label: string; example: string }> = []

  actions.push({
    label: 'Focus Auto',
    example: `PUT ${base}/settings/focus\nContent-Type: application/json\n\n{"mode":"auto"}`
  })

  actions.push({
    label: 'WB Auto',
    example: `PUT ${base}/settings/whiteBalance\nContent-Type: application/json\n\n{"mode":"auto"}`
  })

  if (camera.type === 'obsbot_tail2' || camera.type === 'sony_fx30') {
    actions.push({
      label: 'PTZ Center',
      example: `PUT ${base}/settings/ptz\nContent-Type: application/json\n\n{"pan":0,"tilt":0,"zoom":0}`
    })
  }

  return actions
}

async function copyToClipboard(text: string) {
  try {
    await navigator.clipboard.writeText(text)
    // Could add a toast notification here
  } catch (err) {
    console.error('Failed to copy:', err)
  }
}

onMounted(() => {
  loadCameras()
})
</script>

<style scoped>
.companion-panel {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  padding: 24px;
  margin: 24px 0;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 20px;
  font-weight: 600;
  color: var(--preke-text-primary);
  margin: 0;
}

.icon {
  width: 24px;
  height: 24px;
  color: var(--preke-accent);
}

.info-btn {
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  padding: 8px;
  cursor: pointer;
  color: var(--preke-text-secondary);
  transition: all 0.2s;
}

.info-btn:hover {
  background: rgba(255, 255, 255, 0.05);
  color: var(--preke-text-primary);
}

.info-btn svg {
  width: 20px;
  height: 20px;
}

.help-section {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 24px;
}

.help-text {
  color: var(--preke-text-secondary);
  font-size: 14px;
  line-height: 1.6;
  margin: 0;
}

.help-text code {
  background: rgba(0, 0, 0, 0.3);
  padding: 2px 8px;
  border-radius: 4px;
  font-family: 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  color: var(--preke-accent);
}

.camera-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.camera-card {
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 20px;
}

.camera-header {
  margin-bottom: 20px;
}

.camera-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.camera-name {
  font-size: 18px;
  font-weight: 600;
  color: var(--preke-text-primary);
}

.camera-type {
  font-size: 14px;
  color: var(--preke-text-secondary);
  background: rgba(255, 255, 255, 0.05);
  padding: 4px 12px;
  border-radius: 6px;
}

.status-indicator {
  font-size: 13px;
  font-weight: 500;
}

.status-indicator.connected {
  color: #10b981;
}

.status-indicator.disconnected {
  color: #ef4444;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--preke-text-primary);
  margin: 0 0 16px 0;
}

.endpoints-section,
.quick-actions {
  margin-top: 24px;
}

.endpoint-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.endpoint-item {
  display: flex;
  align-items: center;
  gap: 12px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 8px;
  padding: 12px;
}

.endpoint-method {
  font-size: 12px;
  font-weight: 700;
  padding: 4px 10px;
  border-radius: 4px;
  min-width: 60px;
  text-align: center;
  text-transform: uppercase;
}

.endpoint-method.put {
  background: #f59e0b;
  color: #000;
}

.endpoint-method.get {
  background: #3b82f6;
  color: #fff;
}

.endpoint-path {
  flex: 1;
  font-family: 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  color: var(--preke-text-primary);
  word-break: break-all;
}

.endpoint-path code {
  background: transparent;
  padding: 0;
  color: var(--preke-accent);
}

.copy-btn {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 6px;
  padding: 8px;
  cursor: pointer;
  color: var(--preke-text-secondary);
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.copy-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: var(--preke-text-primary);
}

.copy-btn svg {
  width: 16px;
  height: 16px;
}

.action-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.action-btn {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  padding: 10px 16px;
  font-size: 14px;
  font-weight: 500;
  color: var(--preke-text-primary);
  cursor: pointer;
  transition: all 0.2s;
}

.action-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: var(--preke-accent);
  color: var(--preke-accent);
}

.empty-state {
  text-align: center;
  padding: 48px 24px;
  color: var(--preke-text-secondary);
}

.empty-icon {
  width: 64px;
  height: 64px;
  margin: 0 auto 16px;
  opacity: 0.5;
}

.empty-state p {
  margin: 8px 0;
  font-size: 16px;
}

.empty-hint {
  font-size: 14px;
  color: var(--preke-text-muted);
}

.empty-hint code {
  background: rgba(0, 0, 0, 0.3);
  padding: 2px 8px;
  border-radius: 4px;
  font-family: 'Monaco', 'Courier New', monospace;
  font-size: 13px;
}
</style>
