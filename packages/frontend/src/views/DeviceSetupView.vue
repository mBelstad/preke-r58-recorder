<script setup lang="ts">
/**
 * Device Setup View
 * Professional branded first-run experience for Preke Studio
 */
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { isElectron, setDeviceUrl } from '@/lib/api'

interface DeviceConfig {
  id: string
  name: string
  url: string
  lastConnected?: string
  createdAt: string
}

const router = useRouter()

const devices = ref<DeviceConfig[]>([])
const activeDeviceId = ref<string | null>(null)
const isLoading = ref(false)
const isTesting = ref(false)
const testResult = ref<{ success: boolean; message: string } | null>(null)
const showAddForm = ref(false)
const newDeviceName = ref('')
const newDeviceUrl = ref('')
const formError = ref('')
const editingDevice = ref<DeviceConfig | null>(null)

const hasDevices = computed(() => devices.value.length > 0)
const activeDevice = computed(() => devices.value.find(d => d.id === activeDeviceId.value))
const inElectron = computed(() => isElectron())

async function loadDevices() {
  if (!window.electronAPI) return
  try {
    devices.value = await window.electronAPI.getDevices()
    const active = await window.electronAPI.getActiveDevice()
    activeDeviceId.value = active?.id || null
  } catch (error) {
    console.error('Failed to load devices:', error)
  }
}

async function testConnection(url: string): Promise<{ success: boolean; message: string }> {
  isTesting.value = true
  testResult.value = null
  try {
    const normalizedUrl = url.replace(/\/+$/, '')
    const response = await fetch(`${normalizedUrl}/api/v1/health`, {
      method: 'GET',
      headers: { 'Accept': 'application/json' },
      signal: AbortSignal.timeout(10000),
    })
    if (response.ok) {
      const data = await response.json()
      return { success: true, message: `Connected! Status: ${data.status || 'OK'}` }
    }
    return { success: false, message: `HTTP ${response.status}: ${response.statusText}` }
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Connection failed'
    return { success: false, message: message.includes('timeout') ? 'Connection timed out' : message }
  } finally {
    isTesting.value = false
  }
}

async function addDevice() {
  if (!window.electronAPI) return
  formError.value = ''
  if (!newDeviceUrl.value.trim()) {
    formError.value = 'Device URL is required'
    return
  }
  try { new URL(newDeviceUrl.value) } catch {
    formError.value = 'Invalid URL format'
    return
  }
  isLoading.value = true
  try {
    const result = await testConnection(newDeviceUrl.value)
    testResult.value = result
    if (!result.success) formError.value = 'Connection failed. You can still save for later.'
    const device = await window.electronAPI.addDevice(newDeviceName.value.trim() || 'Preke Device', newDeviceUrl.value.trim())
    await loadDevices()
    if (devices.value.length === 1) await selectDevice(device.id)
    newDeviceName.value = ''
    newDeviceUrl.value = ''
    showAddForm.value = false
    testResult.value = null
  } catch (error) {
    formError.value = 'Failed to save device'
  } finally {
    isLoading.value = false
  }
}

async function removeDevice(deviceId: string) {
  if (!window.electronAPI || !confirm('Remove this device?')) return
  try {
    await window.electronAPI.removeDevice(deviceId)
    await loadDevices()
  } catch (error) {
    console.error('Failed to remove device:', error)
  }
}

async function selectDevice(deviceId: string) {
  if (!window.electronAPI) return
  isLoading.value = true
  try {
    await window.electronAPI.setActiveDevice(deviceId)
    activeDeviceId.value = deviceId
    const device = devices.value.find(d => d.id === deviceId)
    if (device) setDeviceUrl(device.url)
    router.push('/')
  } catch (error) {
    console.error('Failed to select device:', error)
  } finally {
    isLoading.value = false
  }
}

function startEdit(device: DeviceConfig) { editingDevice.value = { ...device } }

async function saveEdit() {
  if (!window.electronAPI || !editingDevice.value) return
  try {
    await window.electronAPI.updateDevice(editingDevice.value.id, { name: editingDevice.value.name, url: editingDevice.value.url })
    await loadDevices()
    editingDevice.value = null
  } catch (error) {
    console.error('Failed to update device:', error)
  }
}

function cancelEdit() { editingDevice.value = null }
function goBack() { if (activeDevice.value) router.push('/') }

onMounted(() => loadDevices())
</script>

<template>
  <div class="page">
    <!-- Layered background -->
    <div class="page__bg">
      <div class="page__bg-base" />
      <div class="page__bg-texture" />
      <div class="page__bg-gradient" />
    </div>
    
    <div class="page__content">
      <!-- Hero: Large Logo -->
      <header class="hero">
        <img src="/logo-white.svg" alt="Preke" class="hero__logo" />
        
        <!-- Subtle animated soundwave -->
        <div class="hero__wave">
          <span v-for="i in 32" :key="i" class="hero__bar" :style="{ '--i': i }" />
        </div>
      </header>
      
      <!-- Main Card -->
      <main class="card" :class="{ 'card--wide': hasDevices }">
        <!-- First run welcome -->
        <template v-if="!hasDevices && !showAddForm">
          <p class="card__intro">Connect your first device to get started</p>
        </template>
        
        <!-- Devices list header -->
        <h2 v-if="hasDevices && !showAddForm" class="card__heading">Your Devices</h2>

        <!-- Device List -->
        <div v-if="hasDevices && !showAddForm" class="devices">
          <div v-for="device in devices" :key="device.id" class="device" :class="{ 'device--active': device.id === activeDeviceId }">
            <template v-if="editingDevice?.id === device.id">
              <input v-model="editingDevice.name" type="text" placeholder="Name" class="input" />
              <input v-model="editingDevice.url" type="url" placeholder="URL" class="input" />
              <div class="device__edit-btns">
                <button @click="saveEdit" class="btn btn--primary btn--sm">Save</button>
                <button @click="cancelEdit" class="btn btn--ghost btn--sm">Cancel</button>
              </div>
            </template>
            <template v-else>
              <div class="device__icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="3" width="20" height="14" rx="2" /><path d="M8 21h8M12 17v4" /></svg>
              </div>
              <div class="device__info">
                <span class="device__name">{{ device.name }}</span>
                <span v-if="device.id === activeDeviceId" class="device__badge">Connected</span>
                <span class="device__url">{{ device.url }}</span>
              </div>
              <div class="device__actions">
                <button v-if="device.id !== activeDeviceId" @click="selectDevice(device.id)" :disabled="isLoading" class="btn btn--primary">Connect</button>
                <button v-else @click="goBack" class="btn btn--success">Open Studio</button>
                <button @click="startEdit(device)" class="icon-btn" title="Edit"><svg viewBox="0 0 20 20" fill="currentColor"><path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" /></svg></button>
                <button @click="removeDevice(device.id)" class="icon-btn icon-btn--danger" title="Remove"><svg viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" /></svg></button>
              </div>
            </template>
          </div>
          <button @click="showAddForm = true" class="add-btn">
            <svg viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clip-rule="evenodd" /></svg>
            Add Device
          </button>
        </div>

        <!-- Add/Edit Form -->
        <form v-if="showAddForm || !hasDevices" @submit.prevent="addDevice" class="form">
          <h3 v-if="hasDevices" class="form__title">Add Device</h3>
          
          <label class="field">
            <span class="field__label">Name <span class="field__opt">(optional)</span></span>
            <input v-model="newDeviceName" type="text" placeholder="e.g., Studio Recorder" class="input" />
          </label>
          
          <label class="field">
            <span class="field__label">URL <span class="field__req">*</span></span>
            <input v-model="newDeviceUrl" type="url" placeholder="https://r58-api.itagenten.no" class="input" :class="{ 'input--error': formError }" />
            <span v-if="formError" class="field__error">{{ formError }}</span>
          </label>

          <div v-if="testResult" class="result" :class="testResult.success ? 'result--success' : 'result--error'">
            <svg v-if="testResult.success" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" /></svg>
            <svg v-else viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" /></svg>
            {{ testResult.message }}
          </div>

          <div class="form__actions">
            <button type="submit" :disabled="isLoading || isTesting" class="btn btn--primary btn--lg">
              <svg v-if="isLoading || isTesting" class="spinner" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none" opacity="0.25" /><path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" opacity="0.75" /></svg>
              {{ isTesting ? 'Testing...' : 'Connect Device' }}
            </button>
            <button v-if="hasDevices" type="button" @click="showAddForm = false; testResult = null; formError = ''" class="btn btn--ghost">Cancel</button>
          </div>
        </form>

        <div v-if="!inElectron" class="warning">
          <svg viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" /></svg>
          Device management requires the <strong>Preke Studio</strong> desktop app.
        </div>
      </main>
      
      <footer class="footer">Preke Studio · Desktop v2.0</footer>
    </div>
  </div>
</template>

<style scoped>
/* ═══════════════════════════════════════════
   TOKENS
   ═══════════════════════════════════════════ */
.page {
  --gold: #d9981e;
  --gold-light: #f5c842;
  --gold-glow: rgba(217, 152, 30, 0.35);
  --bg-dark: #05080f;
  --bg-card: rgba(12, 18, 30, 0.92);
  --border: rgba(255, 255, 255, 0.07);
  --text: #f1f5f9;
  --text-dim: #94a3b8;
  --text-muted: #64748b;
  --blue: #3b82f6;
  --green: #10b981;
  --red: #ef4444;
}

/* ═══════════════════════════════════════════
   PAGE LAYOUT
   ═══════════════════════════════════════════ */
.page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  position: relative;
}

.page__content {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 400px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2rem;
  animation: fadeUp 0.7s ease-out;
}

/* ═══════════════════════════════════════════
   BACKGROUND LAYERS
   ═══════════════════════════════════════════ */
.page__bg {
  position: fixed;
  inset: 0;
  z-index: 0;
}

.page__bg-base {
  position: absolute;
  inset: 0;
  background: var(--bg-dark);
}

.page__bg-texture {
  position: absolute;
  inset: 0;
  background-image: url('/background_image.webp');
  background-size: 400px;
  opacity: 0.04;
}

.page__bg-gradient {
  position: absolute;
  inset: 0;
  background: 
    radial-gradient(ellipse 120% 60% at 50% -10%, rgba(59, 130, 246, 0.08), transparent 60%),
    radial-gradient(ellipse 80% 60% at 90% 100%, rgba(217, 152, 30, 0.06), transparent 50%),
    linear-gradient(180deg, transparent, rgba(5, 8, 15, 0.8));
}

/* ═══════════════════════════════════════════
   HERO: LARGE LOGO + SUBTLE WAVE
   ═══════════════════════════════════════════ */
.hero {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1.5rem;
}

.hero__logo {
  height: 120px;
  width: auto;
  filter: drop-shadow(0 8px 32px rgba(255, 255, 255, 0.08));
  animation: logoFade 1s ease-out;
}

/* Subtle, elegant soundwave */
.hero__wave {
  display: flex;
  align-items: flex-end;
  justify-content: center;
  gap: 2px;
  height: 20px;
  opacity: 0.7;
}

.hero__bar {
  --delay: calc(var(--i) * 0.08s);
  display: block;
  width: 2px;
  background: linear-gradient(0deg, var(--gold) 0%, var(--gold-light) 100%);
  border-radius: 1px;
  animation: gentleWave 2.5s ease-in-out infinite;
  animation-delay: var(--delay);
}

/* Create smooth wave pattern */
.hero__bar:nth-child(1), .hero__bar:nth-child(32) { height: 3px; }
.hero__bar:nth-child(2), .hero__bar:nth-child(31) { height: 4px; }
.hero__bar:nth-child(3), .hero__bar:nth-child(30) { height: 5px; }
.hero__bar:nth-child(4), .hero__bar:nth-child(29) { height: 6px; }
.hero__bar:nth-child(5), .hero__bar:nth-child(28) { height: 8px; }
.hero__bar:nth-child(6), .hero__bar:nth-child(27) { height: 9px; }
.hero__bar:nth-child(7), .hero__bar:nth-child(26) { height: 11px; }
.hero__bar:nth-child(8), .hero__bar:nth-child(25) { height: 13px; }
.hero__bar:nth-child(9), .hero__bar:nth-child(24) { height: 14px; }
.hero__bar:nth-child(10), .hero__bar:nth-child(23) { height: 16px; }
.hero__bar:nth-child(11), .hero__bar:nth-child(22) { height: 17px; }
.hero__bar:nth-child(12), .hero__bar:nth-child(21) { height: 18px; }
.hero__bar:nth-child(13), .hero__bar:nth-child(20) { height: 19px; }
.hero__bar:nth-child(14), .hero__bar:nth-child(19) { height: 20px; }
.hero__bar:nth-child(15), .hero__bar:nth-child(18) { height: 20px; }
.hero__bar:nth-child(16), .hero__bar:nth-child(17) { height: 20px; }

@keyframes gentleWave {
  0%, 100% {
    transform: scaleY(0.5);
    opacity: 0.5;
  }
  50% {
    transform: scaleY(1);
    opacity: 1;
  }
}

@keyframes logoFade {
  from { opacity: 0; transform: scale(0.95); }
  to { opacity: 1; transform: scale(1); }
}

/* ═══════════════════════════════════════════
   CARD
   ═══════════════════════════════════════════ */
.card {
  width: 100%;
  background: var(--bg-card);
  backdrop-filter: blur(20px);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 1.75rem;
  box-shadow: 0 20px 50px -15px rgba(0, 0, 0, 0.5);
}

.card--wide { max-width: 480px; }

.card__intro {
  text-align: center;
  color: var(--text-dim);
  font-size: 0.9375rem;
  margin-bottom: 1.5rem;
}

.card__heading {
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 1rem;
}

/* ═══════════════════════════════════════════
   DEVICES
   ═══════════════════════════════════════════ */
.devices {
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
}

.device {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
  padding: 0.875rem;
  background: rgba(255, 255, 255, 0.025);
  border: 1px solid var(--border);
  border-radius: 10px;
  transition: all 0.15s;
}

.device:hover { background: rgba(255, 255, 255, 0.04); }

.device--active {
  border-color: var(--gold);
  background: rgba(217, 152, 30, 0.06);
}

.device__icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.04);
  display: grid;
  place-items: center;
  flex-shrink: 0;
}

.device__icon svg {
  width: 20px;
  height: 20px;
  color: var(--text-muted);
}

.device--active .device__icon { background: rgba(217, 152, 30, 0.15); }
.device--active .device__icon svg { color: var(--gold); }

.device__info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.375rem 0.5rem;
}

.device__name {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text);
}

.device__badge {
  font-size: 0.625rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: 0.125rem 0.375rem;
  border-radius: 999px;
  background: rgba(16, 185, 129, 0.15);
  color: var(--green);
}

.device__url {
  width: 100%;
  font-size: 0.75rem;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.device__actions {
  display: flex;
  gap: 0.375rem;
  flex-shrink: 0;
}

.device__edit-btns {
  width: 100%;
  display: flex;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.add-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.375rem;
  padding: 0.625rem;
  margin-top: 0.375rem;
  background: transparent;
  border: 1px dashed rgba(255, 255, 255, 0.12);
  border-radius: 10px;
  color: var(--text-muted);
  font-size: 0.8125rem;
  cursor: pointer;
  transition: all 0.15s;
}

.add-btn:hover {
  border-color: var(--gold);
  color: var(--gold);
  background: rgba(217, 152, 30, 0.04);
}

.add-btn svg { width: 14px; height: 14px; }

/* ═══════════════════════════════════════════
   FORM
   ═══════════════════════════════════════════ */
.form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.form__title {
  font-size: 0.9375rem;
  font-weight: 500;
  color: var(--text);
}

.form__actions {
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
  margin-top: 0.5rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.field__label {
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--text);
}

.field__opt { color: var(--text-muted); font-weight: 400; }
.field__req { color: var(--gold); }
.field__error { font-size: 0.75rem; color: var(--red); }

.input {
  width: 100%;
  padding: 0.625rem 0.875rem;
  font-size: 0.875rem;
  color: var(--text);
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--border);
  border-radius: 8px;
  outline: none;
  transition: all 0.15s;
}

.input::placeholder { color: var(--text-muted); }
.input:focus { border-color: var(--blue); box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15); }
.input--error { border-color: var(--red); }

.result {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 0.75rem;
  border-radius: 8px;
  font-size: 0.8125rem;
}

.result svg { width: 16px; height: 16px; flex-shrink: 0; }
.result--success { background: rgba(16, 185, 129, 0.1); color: var(--green); }
.result--error { background: rgba(239, 68, 68, 0.1); color: var(--red); }

/* ═══════════════════════════════════════════
   BUTTONS
   ═══════════════════════════════════════════ */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.375rem;
  padding: 0.5rem 0.875rem;
  font-size: 0.8125rem;
  font-weight: 500;
  border-radius: 8px;
  border: none;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
}

.btn:disabled { opacity: 0.5; cursor: not-allowed; }

.btn--primary { background: var(--blue); color: white; }
.btn--primary:hover:not(:disabled) { background: #2563eb; }

.btn--success { background: var(--green); color: white; }
.btn--success:hover:not(:disabled) { background: #059669; }

.btn--ghost { background: transparent; color: var(--text-dim); border: 1px solid var(--border); }
.btn--ghost:hover:not(:disabled) { background: rgba(255, 255, 255, 0.04); color: var(--text); }

.btn--sm { padding: 0.375rem 0.625rem; font-size: 0.75rem; }
.btn--lg { padding: 0.75rem 1.25rem; font-size: 0.875rem; width: 100%; }

.icon-btn {
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border-radius: 6px;
  border: none;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.15s;
}

.icon-btn:hover { background: rgba(255, 255, 255, 0.06); color: var(--text); }
.icon-btn--danger:hover { background: rgba(239, 68, 68, 0.12); color: var(--red); }
.icon-btn svg { width: 14px; height: 14px; }

.spinner { width: 16px; height: 16px; animation: spin 1s linear infinite; }

/* ═══════════════════════════════════════════
   WARNING & FOOTER
   ═══════════════════════════════════════════ */
.warning {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem;
  margin-top: 1rem;
  background: rgba(245, 158, 11, 0.08);
  border: 1px solid rgba(245, 158, 11, 0.15);
  border-radius: 8px;
  font-size: 0.75rem;
  color: #fbbf24;
}

.warning svg { width: 16px; height: 16px; flex-shrink: 0; }
.warning strong { color: #fcd34d; }

.footer {
  font-size: 0.6875rem;
  color: var(--text-muted);
  letter-spacing: 0.02em;
}

/* ═══════════════════════════════════════════
   ANIMATIONS
   ═══════════════════════════════════════════ */
@keyframes fadeUp {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* ═══════════════════════════════════════════
   RESPONSIVE
   ═══════════════════════════════════════════ */
@media (max-width: 480px) {
  .page { padding: 1rem; }
  .hero__logo { height: 100px; }
  .card { padding: 1.25rem; }
  .device__actions { width: 100%; margin-top: 0.5rem; justify-content: flex-end; }
}
</style>
