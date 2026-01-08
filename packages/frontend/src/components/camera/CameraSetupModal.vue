<script setup lang="ts">
/**
 * CameraSetupModal - Modal for configuring external cameras
 */
import { ref, computed, onMounted } from 'vue'
import BaseModal from '@/components/shared/BaseModal.vue'
import { r58Api } from '@/lib/api'
import { useToast } from '@/composables/useToast'

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'updated'): void
}>()

const modalRef = ref<InstanceType<typeof BaseModal> | null>(null)
const toast = useToast()

const loading = ref(false)
const saving = ref(false)
const testing = ref<string | null>(null)

interface CameraConfig {
  name: string
  type: 'blackmagic' | 'obsbot_tail2'
  ip: string
  port?: number
  enabled: boolean
}

const cameras = ref<CameraConfig[]>([])
const editingIndex = ref<number | null>(null)

const cameraTypes = [
  { value: 'blackmagic', label: 'Blackmagic Design Studio Camera 4K Pro' },
  { value: 'obsbot_tail2', label: 'OBSbot Tail 2' },
]

// Form state for new/edit
const formCamera = ref<CameraConfig>({
  name: '',
  type: 'blackmagic',
  ip: '',
  port: undefined,
  enabled: true,
})

const defaultPorts = {
  blackmagic: 80,
  obsbot_tail2: 52381,
}

// Computed
const isEditing = computed(() => editingIndex.value !== null)
const hasChanges = ref(false)

// Load camera configuration
async function loadConfig() {
  loading.value = true
  try {
    const config = await r58Api.cameras.getConfig()
    cameras.value = config.cameras.map((cam: any) => ({
      name: cam.name,
      type: cam.type,
      ip: cam.ip,
      port: cam.port,
      enabled: cam.enabled ?? true,
    }))
    hasChanges.value = false
  } catch (e: any) {
    console.error('[CameraSetup] Failed to load config:', e)
    toast.error('Failed to load camera configuration')
  } finally {
    loading.value = false
  }
}

// Reset form
function resetForm() {
  formCamera.value = {
    name: '',
    type: 'blackmagic',
    ip: '',
    port: undefined,
    enabled: true,
  }
  editingIndex.value = null
}

// Start editing
function startEdit(index: number) {
  editingIndex.value = index
  formCamera.value = { ...cameras.value[index] }
}

// Cancel editing
function cancelEdit() {
  resetForm()
}

// Add new camera
function startAdd() {
  resetForm()
  editingIndex.value = -1 // -1 means "new"
}

// Delete camera
async function deleteCamera(index: number) {
  if (!confirm(`Delete camera "${cameras.value[index].name}"?`)) {
    return
  }
  
  cameras.value.splice(index, 1)
  hasChanges.value = true
  await saveConfig()
}

// Test camera connection
async function testCamera(camera: CameraConfig) {
  testing.value = camera.name
  try {
    // Try to get status - this will test the connection
    const status = await r58Api.cameras.getStatus(camera.name)
    if (status.connected) {
      toast.success(`${camera.name} is connected!`)
    } else {
      toast.warning(`${camera.name} is not connected`)
    }
  } catch (e: any) {
    // Camera might not exist yet, try to ping the IP
    try {
      const response = await fetch(`http://${camera.ip}:${camera.port || defaultPorts[camera.type]}/`, {
        method: 'HEAD',
        mode: 'no-cors',
        signal: AbortSignal.timeout(3000),
      })
      toast.info(`${camera.name}: IP ${camera.ip} is reachable`)
    } catch {
      toast.error(`${camera.name}: Cannot reach ${camera.ip}`)
    }
  } finally {
    testing.value = null
  }
}

// Validate form
function validateForm(): boolean {
  if (!formCamera.value.name.trim()) {
    toast.error('Camera name is required')
    return false
  }
  
  if (!formCamera.value.ip.trim()) {
    toast.error('Camera IP address is required')
    return false
  }
  
  // Validate IP format (basic)
  const ipRegex = /^(\d{1,3}\.){3}\d{1,3}$/
  if (!ipRegex.test(formCamera.value.ip)) {
    toast.error('Invalid IP address format')
    return false
  }
  
  // Check for duplicate names
  const existingIndex = cameras.value.findIndex(
    (c, i) => c.name === formCamera.value.name && i !== editingIndex.value
  )
  if (existingIndex >= 0) {
    toast.error('Camera name already exists')
    return false
  }
  
  return true
}

// Save camera (add or update)
function saveCamera() {
  if (!validateForm()) {
    return
  }
  
  // Set default port if not provided
  if (!formCamera.value.port) {
    formCamera.value.port = defaultPorts[formCamera.value.type]
  }
  
  if (editingIndex.value === -1) {
    // Add new
    cameras.value.push({ ...formCamera.value })
  } else if (editingIndex.value !== null && editingIndex.value >= 0) {
    // Update existing
    cameras.value[editingIndex.value] = { ...formCamera.value }
  }
  
  hasChanges.value = true
  resetForm()
}

// Save configuration to server
async function saveConfig() {
  saving.value = true
  try {
    await r58Api.cameras.updateConfig(cameras.value)
    toast.success('Camera configuration saved!')
    hasChanges.value = false
    emit('updated')
  } catch (e: any) {
    console.error('[CameraSetup] Failed to save config:', e)
    toast.error('Failed to save configuration: ' + (e.message || 'Unknown error'))
  } finally {
    saving.value = false
  }
}

// Open/close
function open() {
  modalRef.value?.open()
  loadConfig()
}

function close() {
  if (hasChanges.value) {
    if (!confirm('You have unsaved changes. Close anyway?')) {
      return
    }
  }
  modalRef.value?.close()
  resetForm()
  hasChanges.value = false
  emit('close')
}

defineExpose({ open, close })

onMounted(() => {
  loadConfig()
})
</script>

<template>
  <BaseModal
    ref="modalRef"
    title="Camera Setup"
    size="xl"
    @close="close"
  >
    <template #header>
      <div class="flex items-center justify-between w-full">
        <div>
          <h2 class="text-lg font-semibold text-preke-text">Camera Setup</h2>
          <p class="text-sm text-preke-text-muted mt-1">
            Configure external cameras for control
          </p>
        </div>
      </div>
    </template>

    <div v-if="loading" class="py-8 text-center text-preke-text-muted">
      Loading camera configuration...
    </div>

    <div v-else class="camera-setup">
      <!-- Camera List -->
      <div class="camera-list">
        <div class="list-header">
          <h3 class="list-title">Configured Cameras</h3>
          <button
            @click="startAdd"
            class="btn-add"
            :disabled="isEditing"
          >
            <svg class="btn-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
            </svg>
            Add Camera
          </button>
        </div>

        <div v-if="cameras.length === 0 && !isEditing" class="empty-state">
          <svg class="empty-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
          <p class="empty-text">No cameras configured</p>
          <p class="empty-hint">Click "Add Camera" to get started</p>
        </div>

        <div v-else class="camera-items">
          <div
            v-for="(camera, index) in cameras"
            :key="index"
            class="camera-item"
            :class="{ 'camera-item--disabled': !camera.enabled }"
          >
            <div class="camera-item__info">
              <div class="camera-item__header">
                <span class="camera-item__name">{{ camera.name }}</span>
                <span
                  :class="[
                    'camera-item__badge',
                    camera.enabled ? 'camera-item__badge--enabled' : 'camera-item__badge--disabled'
                  ]"
                >
                  {{ camera.enabled ? 'Enabled' : 'Disabled' }}
                </span>
              </div>
              <div class="camera-item__details">
                <span class="camera-item__type">
                  {{ cameraTypes.find(t => t.value === camera.type)?.label || camera.type }}
                </span>
                <span class="camera-item__ip">{{ camera.ip }}:{{ camera.port || defaultPorts[camera.type] }}</span>
              </div>
            </div>
            <div class="camera-item__actions">
              <button
                @click="testCamera(camera)"
                :disabled="testing === camera.name"
                class="btn-test"
                title="Test Connection"
              >
                <svg v-if="testing !== camera.name" class="btn-icon-sm" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                <span v-else class="spinner"></span>
              </button>
              <button
                @click="startEdit(index)"
                :disabled="isEditing"
                class="btn-edit"
                title="Edit"
              >
                <svg class="btn-icon-sm" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
              </button>
              <button
                @click="deleteCamera(index)"
                :disabled="isEditing"
                class="btn-delete"
                title="Delete"
              >
                <svg class="btn-icon-sm" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Add/Edit Form -->
      <div v-if="isEditing" class="camera-form">
        <div class="form-header">
          <h3 class="form-title">{{ editingIndex === -1 ? 'Add Camera' : 'Edit Camera' }}</h3>
          <button @click="cancelEdit" class="btn-cancel-form">Cancel</button>
        </div>

        <div class="form-content">
          <div class="form-group">
            <label class="form-label">Camera Name *</label>
            <input
              v-model="formCamera.name"
              type="text"
              class="form-input"
              placeholder="e.g., BMD Cam 1"
            />
          </div>

          <div class="form-group">
            <label class="form-label">Camera Type *</label>
            <select v-model="formCamera.type" class="form-input">
              <option
                v-for="type in cameraTypes"
                :key="type.value"
                :value="type.value"
              >
                {{ type.label }}
              </option>
            </select>
          </div>

          <div class="form-group">
            <label class="form-label">IP Address *</label>
            <input
              v-model="formCamera.ip"
              type="text"
              class="form-input"
              placeholder="192.168.1.101"
            />
            <p class="form-hint">Camera's network IP address</p>
          </div>

          <div class="form-group">
            <label class="form-label">Port</label>
            <input
              v-model.number="formCamera.port"
              type="number"
              class="form-input"
              :placeholder="String(defaultPorts[formCamera.type])"
            />
            <p class="form-hint">Default: {{ defaultPorts[formCamera.type] }} for {{ formCamera.type }}</p>
          </div>

          <div class="form-group">
            <label class="form-checkbox">
              <input
                v-model="formCamera.enabled"
                type="checkbox"
                class="checkbox"
              />
              <span>Enabled</span>
            </label>
            <p class="form-hint">Disable to keep configuration but not use the camera</p>
          </div>

          <div class="form-actions">
            <button @click="saveCamera" class="btn-save-form">
              {{ editingIndex === -1 ? 'Add Camera' : 'Update Camera' }}
            </button>
            <button @click="cancelEdit" class="btn-cancel-form">
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>

    <template #footer>
      <div class="flex items-center justify-between w-full">
        <div v-if="hasChanges" class="text-sm text-amber-400">
          You have unsaved changes
        </div>
        <div v-else class="text-sm text-preke-text-muted">
          {{ cameras.length }} camera{{ cameras.length !== 1 ? 's' : '' }} configured
        </div>
        <div class="flex gap-3">
          <button
            @click="close"
            class="btn-secondary"
          >
            Close
          </button>
          <button
            @click="saveConfig"
            :disabled="!hasChanges || saving"
            class="btn-primary"
          >
            {{ saving ? 'Saving...' : 'Save Configuration' }}
          </button>
        </div>
      </div>
    </template>
  </BaseModal>
</template>

<style scoped>
.camera-setup {
  min-height: 400px;
  max-height: 70vh;
  overflow-y: auto;
}

.camera-list {
  margin-bottom: 24px;
}

.list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.list-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--preke-text, #fff);
}

.btn-add {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: var(--preke-gold, #e0a030);
  border: none;
  border-radius: 6px;
  color: #000;
  font-weight: 600;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-add:hover:not(:disabled) {
  background: #f0b040;
}

.btn-add:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-icon {
  width: 16px;
  height: 16px;
}

.empty-state {
  text-align: center;
  padding: 48px 24px;
  color: var(--preke-text-muted, #888);
}

.empty-icon {
  width: 64px;
  height: 64px;
  margin: 0 auto 16px;
  opacity: 0.5;
}

.empty-text {
  font-size: 16px;
  font-weight: 500;
  margin-bottom: 8px;
  color: var(--preke-text-muted, #888);
}

.empty-hint {
  font-size: 13px;
  color: var(--preke-text-subtle, #666);
}

.camera-items {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.camera-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--preke-border, rgba(255,255,255,0.1));
  border-radius: 8px;
  transition: all 0.2s;
}

.camera-item:hover {
  background: rgba(255, 255, 255, 0.05);
  border-color: var(--preke-border, rgba(255,255,255,0.2));
}

.camera-item--disabled {
  opacity: 0.6;
}

.camera-item__info {
  flex: 1;
}

.camera-item__header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 6px;
}

.camera-item__name {
  font-size: 15px;
  font-weight: 600;
  color: var(--preke-text, #fff);
}

.camera-item__badge {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
}

.camera-item__badge--enabled {
  background: rgba(34, 197, 94, 0.2);
  color: var(--preke-green, #22c55e);
}

.camera-item__badge--disabled {
  background: rgba(255, 255, 255, 0.1);
  color: var(--preke-text-muted, #888);
}

.camera-item__details {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 13px;
  color: var(--preke-text-muted, #888);
}

.camera-item__type {
  font-weight: 500;
}

.camera-item__ip {
  font-family: monospace;
  font-size: 12px;
}

.camera-item__actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-test,
.btn-edit,
.btn-delete {
  padding: 6px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--preke-border, rgba(255,255,255,0.1));
  border-radius: 6px;
  color: var(--preke-text-muted, #888);
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-test:hover:not(:disabled) {
  background: rgba(34, 197, 94, 0.1);
  border-color: rgba(34, 197, 94, 0.3);
  color: var(--preke-green, #22c55e);
}

.btn-edit:hover:not(:disabled) {
  background: rgba(59, 130, 246, 0.1);
  border-color: rgba(59, 130, 246, 0.3);
  color: #3b82f6;
}

.btn-delete:hover:not(:disabled) {
  background: rgba(239, 68, 68, 0.1);
  border-color: rgba(239, 68, 68, 0.3);
  color: #ef4444;
}

.btn-test:disabled,
.btn-edit:disabled,
.btn-delete:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-icon-sm {
  width: 16px;
  height: 16px;
}

.spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.2);
  border-top-color: currentColor;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Form Styles */
.camera-form {
  margin-top: 24px;
  padding: 20px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--preke-border, rgba(255,255,255,0.1));
  border-radius: 8px;
}

.form-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.form-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--preke-text, #fff);
}

.form-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--preke-text, #fff);
}

.form-input {
  padding: 10px 12px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid var(--preke-border, rgba(255,255,255,0.1));
  border-radius: 6px;
  color: var(--preke-text, #fff);
  font-size: 14px;
}

.form-input:focus {
  outline: none;
  border-color: var(--preke-gold, #e0a030);
}

.form-hint {
  font-size: 11px;
  color: var(--preke-text-muted, #888);
}

.form-checkbox {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 13px;
  color: var(--preke-text, #fff);
}

.checkbox {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.form-actions {
  display: flex;
  gap: 12px;
  margin-top: 8px;
}

.btn-save-form {
  padding: 10px 20px;
  background: var(--preke-gold, #e0a030);
  border: none;
  border-radius: 6px;
  color: #000;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-save-form:hover {
  background: #f0b040;
}

.btn-cancel-form {
  padding: 10px 20px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--preke-border, rgba(255,255,255,0.1));
  border-radius: 6px;
  color: var(--preke-text, #fff);
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-cancel-form:hover {
  background: rgba(255, 255, 255, 0.1);
}

.btn-primary {
  padding: 10px 20px;
  background: var(--preke-gold, #e0a030);
  border: none;
  border-radius: 6px;
  color: #000;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary:hover:not(:disabled) {
  background: #f0b040;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  padding: 10px 20px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--preke-border, rgba(255,255,255,0.1));
  border-radius: 6px;
  color: var(--preke-text, #fff);
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-secondary:hover {
  background: rgba(255, 255, 255, 0.1);
}
</style>
