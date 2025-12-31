<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { buildApiUrl } from '@/lib/api'

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
    
    for (const dateGroup of (data.sessions || []) as DateGroup[]) {
      for (const session of dateGroup.date_sessions) {
        transformedSessions.push({
          id: session.session_id,
          name: session.name,
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
  // Use the file's URL directly from the API response
  const url = buildApiUrl(file.url)
  window.open(url, '_blank')
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
  
  try {
    const url = buildApiUrl(`/api/sessions/${session.id}`)
    const response = await fetch(url, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: newName.value.trim() }),
    })
    
    if (response.ok) {
      session.name = newName.value.trim()
    }
  } catch (e) {
    console.error('Failed to rename session:', e)
  } finally {
    editingName.value = null
  }
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
            <div class="w-12 h-12 rounded-lg bg-r58-bg-tertiary flex items-center justify-center">
              <svg class="w-6 h-6 text-r58-text-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
              </svg>
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
                  <svg class="w-8 h-8 text-r58-text-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
                  </svg>
                  <div>
                    <p class="font-medium text-sm">{{ file.camera_id.toUpperCase() }}</p>
                    <p class="text-xs text-r58-text-secondary">{{ file.filename }}</p>
                  </div>
                </div>
                <div class="flex items-center gap-4">
                  <span class="text-sm text-r58-text-secondary">{{ (file.size_bytes / (1024 * 1024 * 1024)).toFixed(2) }} GB</span>
                  <button 
                    @click="downloadFile(selectedSession, file)"
                    class="btn text-sm"
                  >
                    Download
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

