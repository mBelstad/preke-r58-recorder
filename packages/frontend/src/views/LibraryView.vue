<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { buildApiUrl, isElectron } from '@/lib/api'

// Local storage key for session names (since device API doesn't support renaming)
const SESSION_NAMES_KEY = 'preke-session-names'

function getLocalSessionNames(): Record<string, string> {
  try {
    const stored = localStorage.getItem(SESSION_NAMES_KEY)
    return stored ? JSON.parse(stored) : {}
  } catch {
    return {}
  }
}

function setLocalSessionName(sessionId: string, name: string): void {
  const names = getLocalSessionNames()
  names[sessionId] = name
  localStorage.setItem(SESSION_NAMES_KEY, JSON.stringify(names))
}

interface RecordingFile {
  filename: string
  path: string
  size: number
  cam_id: string
  time: string
  url: string
}

interface DateSession {
  session_id: string
  name: string | null
  start_time: string
  end_time: string
  recordings: RecordingFile[]
  count: number
  total_size: number
}

interface DateGroup {
  date: string
  date_sessions: DateSession[]
  count: number
  total_size: number
}

interface Session {
  id: string
  name: string | null
  date: string
  duration: string
  file_count: number
  total_size: string
  files: RecordingFile[]
}

const sessions = ref<Session[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const selectedSession = ref<Session | null>(null)
const editingName = ref<string | null>(null)
const newName = ref('')
const playingVideo = ref<{ url: string; label: string } | null>(null)

// Camera ID to friendly name mapping
const cameraLabels: Record<string, string> = {
  'cam0': 'HDMI 1',
  'cam1': 'HDMI 2',
  'cam2': 'HDMI 3',
  'cam3': 'HDMI 4',
}

function getCameraLabel(camId: string): string {
  return cameraLabels[camId] || camId.toUpperCase()
}

function getCameraColor(camId: string): string {
  const colors: Record<string, string> = {
    'cam0': 'bg-blue-500/20 text-blue-400',
    'cam1': 'bg-green-500/20 text-green-400',
    'cam2': 'bg-purple-500/20 text-purple-400',
    'cam3': 'bg-amber-500/20 text-amber-400',
  }
  return colors[camId] || 'bg-r58-bg-tertiary text-r58-text-secondary'
}

function playVideo(file: RecordingFile) {
  const url = buildApiUrl(file.url)
  playingVideo.value = { url, label: `${getCameraLabel(file.cam_id)} - ${file.filename}` }
}

function closeVideoPlayer() {
  playingVideo.value = null
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

function formatDuration(startTime: string, endTime: string): string {
  // Simple duration format
  return `${startTime} - ${endTime}`
}

async function fetchSessions() {
  loading.value = true
  error.value = null
  
  try {
    const url = buildApiUrl('/api/recordings')
    const response = await fetch(url)
    if (!response.ok) {
      throw new Error(`Failed to fetch sessions: ${response.status}`)
    }
    const data = await response.json()
    
    // Transform the API response to our Session format
    const transformedSessions: Session[] = []
    const localNames = getLocalSessionNames()
    
    for (const dateGroup of (data.sessions || []) as DateGroup[]) {
      for (const session of dateGroup.date_sessions) {
        // Use local name if available, otherwise use API name
        const displayName = localNames[session.session_id] || session.name
        transformedSessions.push({
          id: session.session_id,
          name: displayName,
          date: dateGroup.date,
          duration: formatDuration(session.start_time, session.end_time),
          file_count: session.count,
          total_size: formatBytes(session.total_size),
          files: session.recordings.map(r => ({
            ...r,
            size_bytes: r.size,
            camera_id: r.cam_id,
            created_at: r.time,
          })) as any,
        })
      }
    }
    
    sessions.value = transformedSessions
  } catch (e) {
    console.error('Failed to fetch sessions:', e)
    error.value = e instanceof Error ? e.message : 'Failed to load recordings'
  } finally {
    loading.value = false
  }
}

function openSession(session: Session) {
  selectedSession.value = session
}

function closeSession() {
  selectedSession.value = null
}

async function downloadFile(session: Session, file: RecordingFile) {
  // Use fetch + blob for proper download with correct filename
  const fullUrl = buildApiUrl(file.url)
  try {
    const response = await fetch(fullUrl)
    if (!response.ok) {
      throw new Error(`Download failed: ${response.status}`)
    }
    const blob = await response.blob()
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = file.filename
    link.click()
    URL.revokeObjectURL(link.href)
  } catch (e) {
    console.error('Failed to download file:', e)
    // Fallback to opening in new tab
    window.open(fullUrl, '_blank')
  }
}

function startRename(session: Session) {
  editingName.value = session.id
  newName.value = session.name || ''
}

async function saveRename(session: Session) {
  if (!newName.value.trim()) {
    editingName.value = null
    return
  }
  
  // Store name locally since device API doesn't support renaming
  const trimmedName = newName.value.trim()
  setLocalSessionName(session.id, trimmedName)
  session.name = trimmedName
  editingName.value = null
}

function cancelRename() {
  editingName.value = null
  newName.value = ''
}

async function deleteSession(session: Session) {
  if (!confirm(`Delete "${session.name || session.id}"? This will permanently delete ${session.file_count} recording files (${session.total_size}).`)) {
    return
  }
  
  try {
    const url = buildApiUrl(`/api/sessions/${session.id}`)
    const response = await fetch(url, {
      method: 'DELETE',
    })
    
    if (response.ok) {
      sessions.value = sessions.value.filter(s => s.id !== session.id)
      if (selectedSession.value?.id === session.id) {
        selectedSession.value = null
      }
    }
  } catch (e) {
    console.error('Failed to delete session:', e)
  }
}

onMounted(() => {
  fetchSessions()
})
</script>

<template>
  <div class="h-full flex flex-col">
    <!-- Header -->
    <header class="flex items-center justify-between px-6 py-4 border-b border-r58-bg-tertiary bg-r58-bg-secondary">
      <h1 class="text-xl font-semibold">Recording Library</h1>
      <div class="flex items-center gap-4">
        <button @click="fetchSessions" class="btn" :disabled="loading">
          <svg v-if="loading" class="animate-spin w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          <span v-else>Refresh</span>
        </button>
      </div>
    </header>
    
    <!-- Content -->
    <div class="flex-1 p-6 overflow-y-auto">
      <!-- Loading state -->
      <div v-if="loading" class="flex items-center justify-center h-64">
        <div class="animate-spin w-8 h-8 border-2 border-r58-accent-primary border-t-transparent rounded-full"></div>
      </div>
      
      <!-- Error state -->
      <div v-else-if="error" class="flex flex-col items-center justify-center h-64 text-center">
        <svg class="w-12 h-12 text-r58-accent-danger mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        <p class="text-r58-text-secondary">{{ error }}</p>
        <button @click="fetchSessions" class="btn mt-4">Try Again</button>
      </div>
      
      <!-- Empty state -->
      <div v-else-if="sessions.length === 0" class="flex flex-col items-center justify-center h-64 text-center">
        <svg class="w-16 h-16 text-r58-text-secondary mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
        </svg>
        <p class="text-lg font-medium">No Recordings Yet</p>
        <p class="text-sm text-r58-text-secondary mt-2">Recordings will appear here after you record from the Recorder page.</p>
      </div>
      
      <!-- Session list -->
      <div v-else class="grid gap-4">
        <div 
          v-for="session in sessions" 
          :key="session.id"
          class="card flex items-center justify-between hover:border-r58-accent-primary/50 transition-colors"
        >
          <div class="flex items-center gap-4">
            <!-- Thumbnail: show camera icons for files in session -->
            <div class="flex -space-x-2">
              <div 
                v-for="(file, index) in session.files.slice(0, 3)" 
                :key="file.filename"
                class="w-10 h-10 rounded-lg flex items-center justify-center text-xs font-bold border-2 border-r58-bg-secondary"
                :class="getCameraColor(file.cam_id)"
                :style="{ zIndex: 3 - index }"
              >
                {{ getCameraLabel(file.cam_id).replace('HDMI ', '') }}
              </div>
              <div 
                v-if="session.files.length > 3" 
                class="w-10 h-10 rounded-lg bg-r58-bg-tertiary flex items-center justify-center text-xs font-medium text-r58-text-secondary border-2 border-r58-bg-secondary"
              >
                +{{ session.files.length - 3 }}
              </div>
            </div>
            <div class="flex-1">
              <!-- Editable name -->
              <div v-if="editingName === session.id" class="flex items-center gap-2">
                <input 
                  v-model="newName"
                  @keyup.enter="saveRename(session)"
                  @keyup.escape="cancelRename"
                  class="input text-sm py-1"
                  placeholder="Session name..."
                  autofocus
                />
                <button @click="saveRename(session)" class="text-r58-accent-primary text-sm">Save</button>
                <button @click="cancelRename" class="text-r58-text-secondary text-sm">Cancel</button>
              </div>
              <div v-else class="flex items-center gap-2">
                <h3 class="font-medium">{{ session.name || session.id.substring(0, 8) }}</h3>
                <button 
                  @click.stop="startRename(session)"
                  class="text-r58-text-secondary hover:text-r58-text-primary"
                  title="Rename session"
                >
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                  </svg>
                </button>
              </div>
              <p class="text-sm text-r58-text-secondary">{{ session.date }} · {{ session.duration }}</p>
            </div>
          </div>
          
          <div class="flex items-center gap-4 text-sm text-r58-text-secondary">
            <span>{{ session.file_count }} files</span>
            <span>{{ session.total_size }}</span>
            <button @click="openSession(session)" class="btn">Open</button>
            <button 
              @click.stop="deleteSession(session)" 
              class="btn text-r58-accent-danger hover:bg-r58-accent-danger/10"
              title="Delete session"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Session Detail Modal -->
    <Teleport to="body">
      <div 
        v-if="selectedSession"
        class="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-8"
        @click.self="closeSession"
      >
        <div class="bg-r58-bg-secondary rounded-xl max-w-2xl w-full max-h-[80vh] overflow-hidden flex flex-col">
          <!-- Modal Header -->
          <div class="px-6 py-4 border-b border-r58-bg-tertiary flex items-center justify-between">
            <div>
              <h2 class="text-lg font-semibold">{{ selectedSession.name || selectedSession.id.substring(0, 8) }}</h2>
              <p class="text-sm text-r58-text-secondary">{{ selectedSession.date }} · {{ selectedSession.file_count }} files · {{ selectedSession.total_size }}</p>
            </div>
            <button @click="closeSession" class="text-r58-text-secondary hover:text-r58-text-primary">
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          
          <!-- Modal Content -->
          <div class="flex-1 overflow-y-auto p-6">
            <h3 class="text-sm font-semibold text-r58-text-secondary uppercase tracking-wide mb-3">Recording Files</h3>
            <div class="space-y-2">
              <div 
                v-for="file in selectedSession.files"
                :key="file.filename"
                class="flex items-center justify-between p-3 bg-r58-bg-tertiary rounded-lg"
              >
                <div class="flex items-center gap-3">
                  <div 
                    class="w-10 h-10 rounded-lg flex items-center justify-center text-sm font-bold"
                    :class="getCameraColor(file.cam_id)"
                  >
                    {{ getCameraLabel(file.cam_id).replace('HDMI ', '') }}
                  </div>
                  <div>
                    <p class="font-medium text-sm">{{ getCameraLabel(file.cam_id) }}</p>
                    <p class="text-xs text-r58-text-secondary">{{ file.filename }}</p>
                  </div>
                </div>
                <div class="flex items-center gap-3">
                  <span class="text-sm text-r58-text-secondary">{{ (file.size_bytes / (1024 * 1024 * 1024)).toFixed(2) }} GB</span>
                  <button 
                    @click="playVideo(file)"
                    class="btn btn-primary text-sm"
                    title="Play video"
                  >
                    <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M8 5v14l11-7z"/>
                    </svg>
                  </button>
                  <button 
                    @click="downloadFile(selectedSession, file)"
                    class="btn text-sm"
                    title="Download"
                  >
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
    
    <!-- Video Player Modal -->
    <Teleport to="body">
      <div 
        v-if="playingVideo"
        class="fixed inset-0 bg-black/90 flex items-center justify-center z-[60] p-4"
        @click.self="closeVideoPlayer"
      >
        <div class="relative max-w-5xl w-full">
          <!-- Close button -->
          <button 
            @click="closeVideoPlayer" 
            class="absolute -top-12 right-0 text-white/80 hover:text-white"
          >
            <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
          
          <!-- Video title -->
          <p class="absolute -top-12 left-0 text-white/80 font-medium">{{ playingVideo.label }}</p>
          
          <!-- Video player -->
          <video 
            :src="playingVideo.url" 
            controls 
            autoplay 
            class="w-full rounded-lg shadow-2xl bg-black"
          >
            Your browser does not support video playback.
          </video>
        </div>
      </div>
    </Teleport>
  </div>
</template>

