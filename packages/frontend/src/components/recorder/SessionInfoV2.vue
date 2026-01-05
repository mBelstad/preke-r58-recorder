<script setup lang="ts">
/**
 * SessionInfo v2 - Clean sidebar for recorder
 * Shows contextual info: session details during recording, helpful tips when idle
 */
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useRecorderStore } from '@/stores/recorder'
import { useCapabilitiesStore } from '@/stores/capabilities'
import SettingsPanel from '@/components/shared/SettingsPanel.vue'

const router = useRouter()
const recorderStore = useRecorderStore()
const capabilitiesStore = useCapabilitiesStore()

const currentSession = computed(() => recorderStore.currentSession)
const activeInputs = computed(() => recorderStore.activeInputs)
const isRecording = computed(() => recorderStore.isRecording)
const recordingInputs = computed(() => recorderStore.inputs.filter(i => i.isRecording))

// Settings panel visibility
const showSettings = ref(false)

// Storage info
const storageInfo = computed(() => {
  const caps = capabilitiesStore.capabilities
  if (!caps) return null
  
  const usedGB = caps.storage_used_gb || 0
  const totalGB = caps.storage_total_gb || 1
  const freeGB = totalGB - usedGB
  const percent = Math.round((usedGB / totalGB) * 100)
  
  // Estimate recording time at ~10GB/hour for 4K
  const hoursRemaining = freeGB / 10
  
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
</script>

<template>
  <div class="session-sidebar">
    
    <!-- RECORDING STATE: Show active recording info -->
    <template v-if="isRecording">
      <!-- Recording Status -->
      <section class="sidebar-card sidebar-card--recording">
        <div class="recording-header">
          <span class="recording-dot"></span>
          <span class="recording-label">Recording</span>
        </div>
        <div class="recording-duration">{{ recorderStore.formattedDuration }}</div>
        <div class="recording-meta">
          {{ recordingInputs.length }} camera{{ recordingInputs.length !== 1 ? 's' : '' }} recording
        </div>
      </section>
      
      <!-- Recording Stats -->
      <section class="sidebar-card">
        <h3 class="sidebar-title">Recording Stats</h3>
        <div class="stats-grid">
          <div 
            v-for="input in recordingInputs" 
            :key="input.id"
            class="stat-item"
          >
            <span class="stat-label">{{ input.label }}</span>
            <span class="stat-value">{{ formatBytes(input.bytesWritten) }}</span>
          </div>
        </div>
      </section>
      
      <!-- Storage Warning (only show if low) -->
      <section v-if="storageInfo?.isLow" class="sidebar-card sidebar-card--warning">
        <div class="warning-icon">⚠️</div>
        <div class="warning-text">
          <strong>Low storage</strong>
          <span>{{ storageInfo.freeGB }} GB remaining (~{{ storageInfo.hoursRemaining }}h)</span>
        </div>
      </section>
    </template>
    
    <!-- IDLE STATE: Show helpful info and actions -->
    <template v-else>
      <!-- Ready to Record -->
      <section class="sidebar-card">
        <h3 class="sidebar-title">Ready to Record</h3>
        <p class="sidebar-hint">
          {{ activeInputs.length }} input{{ activeInputs.length !== 1 ? 's' : '' }} with signal detected.
          Press <kbd>Space</kbd> or click Start Recording to begin.
        </p>
      </section>
      
      <!-- Storage Overview -->
      <section v-if="storageInfo" class="sidebar-card">
        <h3 class="sidebar-title">Storage</h3>
        <div class="storage-info">
          <div class="storage-bar">
            <div 
              class="storage-fill"
              :class="{
                'storage-fill--ok': !storageInfo.isLow,
                'storage-fill--low': storageInfo.isLow && !storageInfo.isCritical,
                'storage-fill--critical': storageInfo.isCritical
              }"
              :style="{ width: `${storageInfo.percent}%` }"
            ></div>
          </div>
          <div class="storage-text">
            <span class="storage-free">{{ storageInfo.freeGB }} GB free</span>
            <span class="storage-estimate">~{{ storageInfo.hoursRemaining }}h recording</span>
          </div>
        </div>
      </section>
      
      <!-- Quick Actions -->
      <section class="sidebar-card">
        <h3 class="sidebar-title">Quick Actions</h3>
        <div class="action-buttons">
          <button 
            @click="openInputConfig"
            class="action-btn"
          >
            ⚙️ Configure Inputs
          </button>
          <button 
            @click="showSettings = !showSettings"
            class="action-btn"
          >
            {{ showSettings ? '✕ Hide Settings' : '🎨 Interface Settings' }}
          </button>
        </div>
      </section>
      
      <!-- Settings Panel (collapsible) -->
      <Transition name="slide-fade">
        <section v-if="showSettings" class="sidebar-card">
          <SettingsPanel />
        </section>
      </Transition>
    </template>
  </div>
</template>

<style scoped>
@import '@/styles/design-system-v2.css';

.session-sidebar {
  display: flex;
  flex-direction: column;
  gap: var(--preke-space-md);
}

.sidebar-card {
  background: var(--preke-glass-bg-light);
  border: 1px solid var(--preke-border);
  border-radius: var(--preke-radius-lg);
  padding: var(--preke-space-md);
}

.sidebar-card--recording {
  background: linear-gradient(135deg, rgba(212, 90, 90, 0.15) 0%, rgba(212, 90, 90, 0.05) 100%);
  border-color: rgba(212, 90, 90, 0.3);
  text-align: center;
}

.sidebar-card--warning {
  background: rgba(245, 158, 11, 0.1);
  border-color: rgba(245, 158, 11, 0.3);
  display: flex;
  align-items: flex-start;
  gap: var(--preke-space-sm);
}

.sidebar-title {
  font-size: var(--preke-text-xs);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--preke-text-muted);
  margin-bottom: var(--preke-space-sm);
}

.sidebar-hint {
  font-size: var(--preke-text-sm);
  color: var(--preke-text-dim);
  line-height: 1.5;
}

.sidebar-hint kbd {
  display: inline-block;
  padding: 2px 6px;
  font-family: var(--preke-font-mono);
  font-size: var(--preke-text-xs);
  background: var(--preke-bg-base);
  border: 1px solid var(--preke-border);
  border-radius: var(--preke-radius-sm);
}

/* Recording state */
.recording-header {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--preke-space-sm);
  margin-bottom: var(--preke-space-xs);
}

.recording-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--preke-red);
  animation: pulse-recording 1.5s ease-in-out infinite;
}

@keyframes pulse-recording {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.6; transform: scale(0.9); }
}

.recording-label {
  font-size: var(--preke-text-sm);
  font-weight: 600;
  color: var(--preke-red);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.recording-duration {
  font-family: var(--preke-font-mono);
  font-size: var(--preke-text-3xl);
  font-weight: 700;
  color: var(--preke-text-primary);
  margin: var(--preke-space-sm) 0;
}

.recording-meta {
  font-size: var(--preke-text-sm);
  color: var(--preke-text-muted);
}

/* Stats grid */
.stats-grid {
  display: flex;
  flex-direction: column;
  gap: var(--preke-space-sm);
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--preke-space-xs) 0;
  border-bottom: 1px solid var(--preke-border);
}

.stat-item:last-child {
  border-bottom: none;
}

.stat-label {
  font-size: var(--preke-text-sm);
  color: var(--preke-text-dim);
}

.stat-value {
  font-family: var(--preke-font-mono);
  font-size: var(--preke-text-sm);
  color: var(--preke-text-primary);
}

/* Warning */
.warning-icon {
  font-size: 20px;
  flex-shrink: 0;
}

.warning-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: var(--preke-text-sm);
}

.warning-text strong {
  color: var(--preke-amber);
}

.warning-text span {
  color: var(--preke-text-muted);
}

/* Storage */
.storage-info {
  display: flex;
  flex-direction: column;
  gap: var(--preke-space-sm);
}

.storage-bar {
  height: 6px;
  background: var(--preke-bg-base);
  border-radius: 3px;
  overflow: hidden;
}

.storage-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.3s ease;
}

.storage-fill--ok { background: var(--preke-green); }
.storage-fill--low { background: var(--preke-amber); }
.storage-fill--critical { background: var(--preke-red); }

.storage-text {
  display: flex;
  justify-content: space-between;
  font-size: var(--preke-text-xs);
}

.storage-free {
  color: var(--preke-text-dim);
}

.storage-estimate {
  color: var(--preke-text-muted);
}

/* Action buttons */
.action-buttons {
  display: flex;
  flex-direction: column;
  gap: var(--preke-space-sm);
}

.action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--preke-space-sm);
  padding: var(--preke-space-sm) var(--preke-space-md);
  font-size: var(--preke-text-sm);
  font-weight: 500;
  color: var(--preke-text-dim);
  background: var(--preke-glass-bg-light);
  border: 1px solid var(--preke-border);
  border-radius: var(--preke-radius-md);
  cursor: pointer;
  transition: all 0.15s ease;
}

.action-btn:hover {
  background: var(--preke-glass-bg-hover);
  color: var(--preke-text-primary);
}

/* Slide fade transition */
.slide-fade-enter-active {
  transition: all 0.2s ease-out;
}
.slide-fade-leave-active {
  transition: all 0.15s ease-in;
}
.slide-fade-enter-from,
.slide-fade-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}
</style>

