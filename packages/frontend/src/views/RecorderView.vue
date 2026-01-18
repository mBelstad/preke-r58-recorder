<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useRecorderStore } from '@/stores/recorder'
import { useCapabilitiesStore } from '@/stores/capabilities'
import { useRecordingGuard } from '@/composables/useRecordingGuard'
import { buildApiUrl, hasDeviceConfigured } from '@/lib/api'
import { toast } from '@/composables/useToast'
import { probeConnections } from '@/lib/connectionProbe'
import RecorderControls from '@/components/recorder/RecorderControls.vue'
import RecordingHealth from '@/components/recorder/RecordingHealth.vue'
import InputGrid from '@/components/recorder/InputGrid.vue'
import SessionInfo from '@/components/recorder/SessionInfoV2.vue'
import ConfirmDialog from '@/components/shared/ConfirmDialog.vue'
import ModeLoadingScreen from '@/components/shared/ModeLoadingScreen.vue'

const router = useRouter()
const recorderStore = useRecorderStore()
const capabilitiesStore = useCapabilitiesStore()
const { showLeaveConfirmation, confirmLeave, cancelLeave } = useRecordingGuard()

// Project selection state
const showProjectPanel = ref(false)
const showNewProjectDialog = ref(false)
const newProjectName = ref('')
const creatingProject = ref(false)

// Handle loading screen cancel - navigate back to studio
function handleLoadingCancel() {
  router.push('/')
}

const isRecording = computed(() => recorderStore.status === 'recording')
const duration = computed(() => recorderStore.formattedDuration)

// Loading state
const isLoading = ref(true)
const dataLoaded = ref(false)
const videosReady = ref(false)
const loadingStatus = ref('Starting recorder...')
const loadingProgress = ref<number | undefined>(undefined)
const connectionMethod = ref<string | undefined>(undefined)

// Content is ready when BOTH data is loaded AND videos are displaying
const contentReady = computed(() => dataLoaded.value && videosReady.value)

function handleLoadingReady() {
  isLoading.value = false
}

// Auto-switch to recorder mode if not already in it
async function ensureRecorderMode() {
  if (!hasDeviceConfigured()) return
  
  // Fetch current capabilities to get mode
  await capabilitiesStore.fetchCapabilities()
  
  const currentMode = capabilitiesStore.capabilities?.current_mode
  if (currentMode && currentMode !== 'recorder') {
    console.log('[Recorder] Not in recorder mode, switching...')
    try {
      const response = await fetch(await buildApiUrl('/api/mode/recorder'), { method: 'POST' })
      if (response.ok) {
        await capabilitiesStore.fetchCapabilities()
        toast.success('Switched to Recorder mode')
      }
    } catch (e) {
      console.warn('[Recorder] Failed to switch mode:', e)
    }
  }
}

// Initialize connection (fast - no preloading)
async function initializeConnection() {
  if (!hasDeviceConfigured()) {
    loadingStatus.value = 'No device configured'
    return
  }
  
  loadingStatus.value = 'Finding best connection...'
  
  // Race all connection methods - total max wait ~3s
  const result = await probeConnections((status) => {
    loadingStatus.value = status
  })
  
  connectionMethod.value = result.method.toUpperCase()
  // Status is already set by the probe callback, don't duplicate
  
  // Note: Camera connections are handled by InputPreview components
  // We don't preload here to avoid blocking on 404 errors when streams aren't ready
}

// Called by InputGrid when all videos have their first frame
function handleAllVideosReady() {
  console.log('[Recorder] All videos ready!')
  videosReady.value = true
}

// Project selection functions
async function handleClientChange() {
  if (recorderStore.selectedClient) {
    await recorderStore.loadProjects(recorderStore.selectedClient.id)
  } else {
    recorderStore.projects = []
  }
  recorderStore.setProject(null)
}

async function handleProjectChange(event: Event) {
  const value = (event.target as HTMLSelectElement).value
  if (value === 'new') {
    showNewProjectDialog.value = true
  } else if (value) {
    const project = recorderStore.projects.find(p => p.id === parseInt(value))
    recorderStore.setProject(project)
  } else {
    recorderStore.setProject(null)
  }
}

async function createNewProject() {
  if (!recorderStore.selectedClient || !newProjectName.value.trim()) {
    toast.error('Please enter a project name')
    return
  }
  
  creatingProject.value = true
  try {
    const project = await recorderStore.createProject(
      recorderStore.selectedClient.id,
      newProjectName.value.trim(),
      recorderStore.recordingType || 'podcast'
    )
    
    await recorderStore.loadProjects(recorderStore.selectedClient.id)
    recorderStore.setProject(project)
    
    showNewProjectDialog.value = false
    newProjectName.value = ''
    toast.success('Project created')
  } catch (e: any) {
    toast.error(e.message || 'Failed to create project')
  } finally {
    creatingProject.value = false
  }
}

// Fetch real input status on mount - parallelized for speed
onMounted(async () => {
  const startTime = performance.now()
  
  // Phase 0: Probe connection and preload cameras (parallel with data fetch)
  const connectionPromise = initializeConnection()
  
  // Phase 1: Fetch data (mode, inputs, status) in parallel
  await Promise.all([
    connectionPromise,
    ensureRecorderMode(),
    recorderStore.fetchInputs(),
    recorderStore.fetchStatus(),
    recorderStore.loadClients()
  ])
  
  const camerasWithSignal = recorderStore.inputs.filter(i => i.hasSignal).length
  console.log(`[Recorder] Data loaded: ${recorderStore.inputs.length} inputs, ${camerasWithSignal} with signal (${Math.round(performance.now() - startTime)}ms)`)
  
  // Mark data as loaded - videos are loading in parallel via InputPreview
  // (but they should already be preloaded from connection probe)
  dataLoaded.value = true
  
  // If no cameras with signal, mark videos as ready immediately
  if (camerasWithSignal === 0) {
    videosReady.value = true
  }
})

// Ref for leave confirmation dialog
const leaveDialog = ref<InstanceType<typeof ConfirmDialog> | null>(null)

// Watch for leave confirmation request
watch(showLeaveConfirmation, (show) => {
  if (show) {
    leaveDialog.value?.open()
  } else {
    leaveDialog.value?.close()
  }
})
</script>

<template>
  <!-- Loading Screen -->
  <Transition name="fade">
    <ModeLoadingScreen
      v-if="isLoading"
      mode="recorder"
      :content-ready="contentReady"
      :min-time="1500"
      :max-time="12000"
      :show-cancel="true"
      :status-text="loadingStatus"
      :progress="loadingProgress"
      :connection-method="connectionMethod"
      @ready="handleLoadingReady"
      @cancel="handleLoadingCancel"
    />
  </Transition>
  
  <!-- Content fades in when loading complete -->
  <Transition name="content-fade">
    <div v-show="!isLoading" class="h-full flex flex-col">
    <!-- Header - minimal, clean -->
    <header class="recorder-header">
      <div class="recorder-header__left">
        <div class="recorder-header__title">
          <span 
            class="recorder-header__indicator"
            :class="{ 'recorder-header__indicator--active': isRecording }"
          ></span>
          <span class="recorder-header__label">Recorder</span>
        </div>
        <span v-if="isRecording" class="recorder-header__badge">
          REC
        </span>
        <RecordingHealth />
      </div>
      
      <RecorderControls />
    </header>
    
    <!-- Main content - fills available space without scroll -->
    <div class="flex-1 flex min-h-0 overflow-hidden">
      <!-- Input grid - fills all available space -->
      <div class="flex-1 min-h-0 min-w-0 p-3 overflow-hidden">
        <InputGrid @all-videos-ready="handleAllVideosReady" />
      </div>
      
      <!-- Sidebar -->
      <aside class="w-72 flex-shrink-0 border-l border-preke-surface-border bg-preke-surface/80 backdrop-blur-lg p-4 overflow-y-auto">
        <!-- Project Selection Panel -->
        <div class="mb-4">
          <button
            @click="showProjectPanel = !showProjectPanel"
            class="w-full flex items-center justify-between p-3 bg-preke-bg-elevated border border-preke-border rounded-lg hover:border-preke-border-gold transition-colors"
          >
            <span class="text-sm font-medium text-preke-text-dim">Project (Optional)</span>
            <svg 
              class="w-4 h-4 text-preke-text-muted transition-transform"
              :class="{ 'rotate-180': showProjectPanel }"
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24"
            >
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
            </svg>
          </button>
          
          <div v-if="showProjectPanel" class="mt-2 space-y-3 p-3 bg-preke-bg-base border border-preke-border rounded-lg">
            <!-- Recording Type -->
            <div>
              <label class="block text-xs font-medium text-preke-text-subtle mb-1">Recording Type</label>
              <select
                v-model="recorderStore.recordingType"
                @change="recorderStore.setRecordingType($event.target.value)"
                class="w-full px-3 py-2 bg-preke-bg-elevated border border-preke-border rounded text-sm text-preke-text-primary focus:outline-none focus:ring-2 focus:ring-preke-gold"
              >
                <option :value="null">Select type...</option>
                <option value="podcast">Podcast</option>
                <option value="recording">Talking Head</option>
                <option value="course">Course</option>
                <option value="webinar">Webinar</option>
              </select>
            </div>
            
            <!-- Client -->
            <div>
              <label class="block text-xs font-medium text-preke-text-subtle mb-1">Client</label>
              <select
                v-model="recorderStore.selectedClient"
                @change="handleClientChange"
                class="w-full px-3 py-2 bg-preke-bg-elevated border border-preke-border rounded text-sm text-preke-text-primary focus:outline-none focus:ring-2 focus:ring-preke-gold"
              >
                <option :value="null">Select client...</option>
                <option v-for="client in recorderStore.clients" :key="client.id" :value="client">
                  {{ client.name }}
                </option>
              </select>
            </div>
            
            <!-- Project -->
            <div v-if="recorderStore.selectedClient">
              <label class="block text-xs font-medium text-preke-text-subtle mb-1">Project</label>
              <select
                :value="recorderStore.selectedProject?.id || ''"
                @change="handleProjectChange"
                class="w-full px-3 py-2 bg-preke-bg-elevated border border-preke-border rounded text-sm text-preke-text-primary focus:outline-none focus:ring-2 focus:ring-preke-gold"
              >
                <option value="">Select project...</option>
                <option v-for="project in recorderStore.projects" :key="project.id" :value="project.id">
                  {{ project.name }}
                </option>
                <option value="new">+ Create New Project</option>
              </select>
            </div>
            
            <!-- New Project Dialog -->
            <div v-if="showNewProjectDialog" class="p-3 bg-preke-bg-elevated border border-preke-border-gold rounded">
              <label class="block text-xs font-medium text-preke-text-subtle mb-1">New Project Name</label>
              <input
                v-model="newProjectName"
                type="text"
                placeholder="Project name"
                class="w-full px-3 py-2 bg-preke-bg-base border border-preke-border rounded text-sm text-preke-text-primary focus:outline-none focus:ring-2 focus:ring-preke-gold mb-2"
                @keyup.enter="createNewProject"
              />
              <div class="flex gap-2">
                <button
                  @click="createNewProject"
                  :disabled="creatingProject || !newProjectName.trim()"
                  class="flex-1 px-3 py-1.5 bg-preke-gold text-preke-bg-base rounded text-xs font-medium hover:bg-preke-gold-hover disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {{ creatingProject ? 'Creating...' : 'Create' }}
                </button>
                <button
                  @click="showNewProjectDialog = false; newProjectName = ''"
                  class="flex-1 px-3 py-1.5 bg-preke-bg-base border border-preke-border rounded text-xs font-medium hover:bg-preke-bg-elevated"
                >
                  Cancel
                </button>
              </div>
            </div>
            
            <!-- Recording Path Info -->
            <div v-if="recorderStore.selectedClient && recorderStore.selectedProject" class="text-xs text-preke-text-muted">
              <span class="font-mono">{{ recorderStore.recordingPath }}</span>
            </div>
          </div>
        </div>
        
        <SessionInfo />
      </aside>
    </div>
    
    <!-- Leave Confirmation Dialog -->
    <ConfirmDialog
      ref="leaveDialog"
      title="Recording in Progress"
      :message="`You are currently recording (${duration}). Leaving will stop the recording and save all files.`"
      confirm-text="Leave and Stop Recording"
      cancel-text="Stay"
      :danger="true"
      @confirm="confirmLeave"
      @cancel="cancelLeave"
    />
    </div>
  </Transition>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* Content fade in animation */
.content-fade-enter-active {
  transition: opacity 0.4s ease-out, transform 0.4s ease-out;
}

.content-fade-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.content-fade-enter-to {
  opacity: 1;
  transform: translateY(0);
}

/* Recorder Header */
.recorder-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: var(--preke-surface);
  border-bottom: 1px solid var(--preke-surface-border);
}

.recorder-header__left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.recorder-header__title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.recorder-header__indicator {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--preke-border);
  transition: all 0.3s ease;
}

.recorder-header__indicator--active {
  background: var(--preke-red);
  box-shadow: 0 0 12px var(--preke-red);
  animation: recording-pulse 1.5s ease-in-out infinite;
}

@keyframes recording-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.7; transform: scale(0.9); }
}

.recorder-header__label {
  font-size: 16px;
  font-weight: 600;
  color: var(--preke-text);
}

.recorder-header__badge {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.1em;
  padding: 4px 10px;
  background: rgba(212, 90, 90, 0.15);
  color: var(--preke-red);
  border: 1px solid rgba(212, 90, 90, 0.3);
  border-radius: 6px;
}
</style>

