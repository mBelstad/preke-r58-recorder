/**
 * DaVinci Resolve Integration
 * 
 * Monitors R58 recording sessions and automatically:
 * - Creates new DaVinci projects when recording starts
 * - Imports media files as they're recorded
 * - Sets up multi-camera timelines
 * 
 * This runs in the Electron main process, eliminating firewall issues
 * since the app initiates all connections (polling R58, not receiving webhooks).
 */

import { ipcMain, BrowserWindow } from 'electron'
import { spawn, execSync } from 'child_process'
import * as path from 'path'
import * as fs from 'fs'
import * as http from 'http'
import { log } from './logger'
import { deviceStore } from './deviceStore'

// ============================================
// Types
// ============================================

interface RecordingSession {
  active: boolean
  session_id: string | null
  start_time: string | null
  duration: number
  cameras: Record<string, CameraStatus>
}

interface CameraStatus {
  status: string
  file?: string
  resolution?: string
}

interface DaVinciConfig {
  enabled: boolean
  pollIntervalMs: number
  projectNamePrefix: string
  autoCreateProject: boolean
  autoImportMedia: boolean
  createMulticamTimeline: boolean
  autoRefreshClips: boolean
  refreshIntervalMs: number
}

// ============================================
// State
// ============================================

let davinciConfig: DaVinciConfig = {
  enabled: false,
  pollIntervalMs: 5000, // Poll every 5 seconds (was 2)
  projectNamePrefix: 'Preke',
  autoCreateProject: true,
  autoImportMedia: true,
  createMulticamTimeline: true,
  autoRefreshClips: false, // DISABLED by default - causes Resolve freezes. Use manual refresh.
  refreshIntervalMs: 30000, // Refresh every 30 seconds (was 20, increased for stability)
}

let pollInterval: NodeJS.Timeout | null = null
let refreshInterval: NodeJS.Timeout | null = null
let lastSessionId: string | null = null
let isResolveConnected = false
let mainWindow: (() => BrowserWindow | null) | null = null
let lastResolveCheck = 0
let lastRefreshTime = 0
let isRefreshing = false // Prevent overlapping refresh operations
let lastErrorTime = 0 // Track last error for cooldown
let clipsImported = false // Track if Create Multicam has been used (clips exist in Resolve)
let consecutiveTimeouts = 0 // Track consecutive timeouts to detect Resolve issues
const RESOLVE_CHECK_INTERVAL = 30000 // Only check Resolve connection every 30 seconds
const ERROR_COOLDOWN_MS = 60000 // Wait 60 seconds after a serious error (was 30)
const MAX_CONSECUTIVE_TIMEOUTS = 2 // After 2 timeouts, assume Resolve is having issues

// Reset state when module loads (app starts)
function resetRefreshState() {
  clipsImported = false
  consecutiveTimeouts = 0
  lastErrorTime = 0
  isRefreshing = false
  log.info('Refresh state reset')
}

// Call immediately on module load
resetRefreshState()

// R58 recordings mount path - where SMB share is mounted on Mac
const R58_MOUNT_PATHS = [
  `${process.env.HOME}/r58-recordings`,
  '/Volumes/r58-recordings',
  '/Volumes/recordings',
]

/**
 * Find mounted R58 recordings path
 */
function findR58MountPath(): string | null {
  for (const mountPath of R58_MOUNT_PATHS) {
    if (fs.existsSync(mountPath) && fs.existsSync(path.join(mountPath, 'cam0'))) {
      return mountPath
    }
  }
  return null
}

/**
 * Map R58 file path to local mounted path
 * e.g., /data/recordings/cam0/file.mkv -> ~/r58-recordings/cam0/file.mkv
 */
function mapR58PathToLocal(r58Path: string): string | null {
  const mountPath = findR58MountPath()
  if (!mountPath) return null
  
  // Extract relative path from R58 path
  // R58 paths: /data/recordings/cam0/file.mkv or /userdata/recordings/cam0/file.mkv
  const match = r58Path.match(/(?:\/data|\/userdata)?\/recordings\/(.+)/)
  if (match) {
    return path.join(mountPath, match[1])
  }
  
  // Try just the filename in cam folders
  const filename = path.basename(r58Path)
  for (const camDir of ['cam0', 'cam1', 'cam2', 'cam3']) {
    const localPath = path.join(mountPath, camDir, filename)
    if (fs.existsSync(localPath)) {
      return localPath
    }
  }
  
  return null
}

// ============================================
// DaVinci Resolve Detection
// ============================================

/**
 * Check if DaVinci Resolve is running
 */
function isResolveRunning(): boolean {
  try {
    if (process.platform === 'darwin') {
      const result = execSync('pgrep -x "Resolve"', { stdio: 'pipe' }).toString()
      return result.trim().length > 0
    } else if (process.platform === 'win32') {
      const result = execSync('tasklist /FI "IMAGENAME eq Resolve.exe"', { stdio: 'pipe' }).toString()
      return result.includes('Resolve.exe')
    }
    return false
  } catch {
    return false
  }
}

/**
 * Get DaVinci Resolve scripting API path
 */
function getResolveScriptPath(): string | null {
  const paths = {
    darwin: '/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting',
    win32: 'C:\\ProgramData\\Blackmagic Design\\DaVinci Resolve\\Support\\Developer\\Scripting',
    linux: '/opt/resolve/Developer/Scripting',
  }
  
  const scriptPath = paths[process.platform as keyof typeof paths]
  if (scriptPath && fs.existsSync(scriptPath)) {
    return scriptPath
  }
  return null
}

/**
 * Check if we can connect to DaVinci Resolve
 * Uses a simple process check for regular polling, only does full Python check when explicitly requested
 */
async function checkResolveConnection(forceFullCheck = false): Promise<boolean> {
  // Simple check: is Resolve running?
  if (!isResolveRunning()) {
    return false
  }
  
  // For regular polling, just check if process is running (no Python spawn)
  if (!forceFullCheck) {
    return true
  }
  
  // Full check: actually connect via Python (only do this on explicit request)
  const scriptPath = getResolveScriptPath()
  if (!scriptPath) {
    log.debug('DaVinci Resolve scripting path not found')
    return false
  }
  
  return new Promise((resolve) => {
    const pythonScript = `
import sys
sys.path.append('${scriptPath.replace(/\\/g, '/')}')
sys.path.append('${scriptPath.replace(/\\/g, '/')}/Modules')
try:
    import DaVinciResolveScript as dvr
    resolve = dvr.scriptapp("Resolve")
    if resolve:
        print("CONNECTED")
        sys.exit(0)
    else:
        print("NOT_CONNECTED")
        sys.exit(1)
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
`
    
    const python = spawn('python3', ['-c', pythonScript], {
      stdio: ['pipe', 'pipe', 'pipe'],
      env: { ...process.env, PYTHONDONTWRITEBYTECODE: '1' },
    })
    
    let output = ''
    let timedOut = false
    
    const timeout = setTimeout(() => {
      timedOut = true
      python.kill('SIGTERM')
      resolve(false)
    }, 5000)
    
    python.stdout.on('data', (data) => { output += data.toString() })
    python.stderr.on('data', (data) => { output += data.toString() })
    
    python.on('close', (code) => {
      clearTimeout(timeout)
      if (timedOut) return
      const connected = code === 0 && output.includes('CONNECTED')
      log.debug(`DaVinci Resolve connection check: ${connected ? 'OK' : 'Failed'} (${output.trim()})`)
      resolve(connected)
    })
    
    python.on('error', (err) => {
      clearTimeout(timeout)
      log.debug(`DaVinci Python error: ${err.message}`)
      resolve(false)
    })
  })
}

// ============================================
// R58 Communication
// ============================================

/**
 * Fetch recording status from R58
 */
async function fetchRecordingStatus(): Promise<RecordingSession | null> {
  const device = deviceStore.getActiveDevice()
  if (!device) {
    return null
  }
  
  return new Promise((resolve) => {
    const url = new URL('/api/trigger/status', device.url)
    const protocol = url.protocol === 'https:' ? require('https') : http
    
    const req = protocol.get(url.toString(), { timeout: 3000 }, (res: http.IncomingMessage) => {
      if (res.statusCode !== 200) {
        resolve(null)
        return
      }
      
      let data = ''
      res.on('data', (chunk: Buffer) => { data += chunk.toString() })
      res.on('end', () => {
        try {
          const parsed = JSON.parse(data)
          // #region agent log
          fetch('http://127.0.0.1:7242/ingest/1c530d06-93f3-4719-9f2a-db5838c77d56',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'davinci.ts:fetchRecordingStatus',message:'R58 status response',data:{active:parsed.active,cameras:Object.keys(parsed.cameras||{}),sessionId:parsed.session_id},timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'H2'})}).catch(()=>{});
          // #endregion
          resolve(parsed)
        } catch {
          resolve(null)
        }
      })
    })
    
    req.on('error', () => resolve(null))
    req.on('timeout', () => {
      req.destroy()
      resolve(null)
    })
  })
}

// ============================================
// DaVinci Automation Actions
// ============================================

/**
 * Create a new DaVinci project for a recording session
 */
async function createProject(sessionId: string, startTime: string): Promise<boolean> {
  const scriptPath = getResolveScriptPath()
  if (!scriptPath) return false
  
  const projectName = `${davinciConfig.projectNamePrefix}_${sessionId}`
  
  log.info(`Creating DaVinci project: ${projectName}`)
  
  const pythonScript = `
import sys
sys.path.append('${scriptPath.replace(/\\/g, '/')}')
sys.path.append('${scriptPath.replace(/\\/g, '/')}/Modules')

import DaVinciResolveScript as dvr

resolve = dvr.scriptapp("Resolve")
if not resolve:
    print("ERROR: Cannot connect to Resolve")
    sys.exit(1)

pm = resolve.GetProjectManager()
if not pm:
    print("ERROR: Cannot get Project Manager")
    sys.exit(1)

# Create new project
project = pm.CreateProject("${projectName}")
if not project:
    # Project might already exist, try to load it
    project = pm.LoadProject("${projectName}")
    if not project:
        print("ERROR: Cannot create or load project")
        sys.exit(1)

print("SUCCESS: Project ready")
sys.exit(0)
`
  
  return new Promise((resolve) => {
    const python = spawn('python3', ['-c', pythonScript], {
      stdio: ['pipe', 'pipe', 'pipe'],
      timeout: 10000,
    })
    
    let output = ''
    python.stdout.on('data', (data) => { output += data.toString() })
    python.stderr.on('data', (data) => { output += data.toString() })
    
    python.on('close', (code) => {
      const success = code === 0 && output.includes('SUCCESS')
      log.info(`DaVinci project creation: ${success ? 'OK' : 'Failed'} - ${output.trim()}`)
      resolve(success)
    })
    
    python.on('error', (err) => {
      log.error('Failed to run DaVinci script:', err)
      resolve(false)
    })
  })
}

/**
 * Import media files into current project
 */
async function importMedia(filePaths: string[]): Promise<boolean> {
  if (filePaths.length === 0) return true
  
  const scriptPath = getResolveScriptPath()
  if (!scriptPath) return false
  
  log.info(`Importing ${filePaths.length} files to DaVinci`)
  
  // Filter to only existing files
  const existingFiles = filePaths.filter(f => {
    try {
      return fs.existsSync(f)
    } catch {
      return false
    }
  })
  
  if (existingFiles.length === 0) {
    log.warn('No existing files to import')
    return true
  }
  
  const filesJson = JSON.stringify(existingFiles)
  
  const pythonScript = `
import sys
import json
sys.path.append('${scriptPath.replace(/\\/g, '/')}')
sys.path.append('${scriptPath.replace(/\\/g, '/')}/Modules')

import DaVinciResolveScript as dvr

resolve = dvr.scriptapp("Resolve")
if not resolve:
    print("ERROR: Cannot connect to Resolve")
    sys.exit(1)

pm = resolve.GetProjectManager()
project = pm.GetCurrentProject()
if not project:
    print("ERROR: No project open")
    sys.exit(1)

media_pool = project.GetMediaPool()
if not media_pool:
    print("ERROR: Cannot get media pool")
    sys.exit(1)

root_folder = media_pool.GetRootFolder()

files = json.loads('${filesJson.replace(/'/g, "\\'")}')
imported = media_pool.ImportMedia(files)

if imported:
    print(f"SUCCESS: Imported {len(imported)} files")
    sys.exit(0)
else:
    print("WARNING: Import returned empty")
    sys.exit(0)
`
  
  return new Promise((resolve) => {
    const python = spawn('python3', ['-c', pythonScript], {
      stdio: ['pipe', 'pipe', 'pipe'],
      timeout: 30000,
    })
    
    let output = ''
    python.stdout.on('data', (data) => { output += data.toString() })
    python.stderr.on('data', (data) => { output += data.toString() })
    
    python.on('close', (code) => {
      log.info(`DaVinci import: ${output.trim()}`)
      resolve(code === 0)
    })
    
    python.on('error', (err) => {
      log.error('Failed to run DaVinci import script:', err)
      resolve(false)
    })
  })
}

// ============================================
// Polling Logic
// ============================================

/**
 * Handle recording session state change
 */
async function handleSessionChange(session: RecordingSession): Promise<void> {
  const currentSessionId = session.session_id
  
  // Session started
  if (session.active && currentSessionId && currentSessionId !== lastSessionId) {
    log.info(`New recording session detected: ${currentSessionId}`)
    lastSessionId = currentSessionId
    
    // Reset auto-refresh state for new session
    clipsImported = false // Will be set to true after Create Multicam
    consecutiveTimeouts = 0
    lastErrorTime = 0
    
    // Notify renderer
    notifyRenderer('davinci-session-start', {
      sessionId: currentSessionId,
      startTime: session.start_time,
      cameras: session.cameras,
    })
    
    // Create project if enabled
    if (davinciConfig.autoCreateProject && isResolveConnected) {
      await createProject(currentSessionId, session.start_time || new Date().toISOString())
    }
  }
  
  // Session stopped
  if (!session.active && lastSessionId) {
    log.info(`Recording session ended: ${lastSessionId}`)
    
    // Collect file paths from cameras
    const filePaths = Object.values(session.cameras)
      .map(cam => cam.file)
      .filter((f): f is string => !!f)
    
    // Notify renderer
    notifyRenderer('davinci-session-stop', {
      sessionId: lastSessionId,
      cameras: session.cameras,
      filePaths,
    })
    
    // Import media if enabled
    if (davinciConfig.autoImportMedia && isResolveConnected && filePaths.length > 0) {
      await importMedia(filePaths)
    }
    
    lastSessionId = null
  }
}

/**
 * Poll R58 for recording status
 */
async function pollRecordingStatus(): Promise<void> {
  // Only check Resolve connection periodically (every 30 seconds), not every poll
  const now = Date.now()
  if (now - lastResolveCheck > RESOLVE_CHECK_INTERVAL) {
    lastResolveCheck = now
    const wasConnected = isResolveConnected
    // Use simple process check, not full Python check
    isResolveConnected = await checkResolveConnection(false)
    
    if (wasConnected !== isResolveConnected) {
      log.info(`DaVinci Resolve connection: ${isResolveConnected ? 'Connected' : 'Disconnected'}`)
      notifyRenderer('davinci-connection-changed', { connected: isResolveConnected })
    }
  }
  
  // Fetch recording status from R58
  const status = await fetchRecordingStatus()
  if (status) {
    await handleSessionChange(status)
    
    // Auto-refresh growing clips if enabled and recording is active
    // IMPORTANT: Only auto-refresh if clips have been imported via Create Multicam
    // #region agent log
    fetch('http://127.0.0.1:7242/ingest/1c530d06-93f3-4719-9f2a-db5838c77d56',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'davinci.ts:506',message:'Auto-refresh check',data:{autoRefreshEnabled:davinciConfig.autoRefreshClips,statusActive:status.active,resolveConnected:isResolveConnected,clipsImported,timeSinceLastRefresh:now-lastRefreshTime,refreshInterval:davinciConfig.refreshIntervalMs,isRefreshing,timeSinceLastError:now-lastErrorTime,consecutiveTimeouts},timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'H2'})}).catch(()=>{});
    // #endregion
    if (davinciConfig.autoRefreshClips && status.active && isResolveConnected && clipsImported) {
      // Skip if already refreshing (prevent overlapping operations that crash Resolve)
      if (isRefreshing) {
        log.debug('Skipping auto-refresh: previous refresh still in progress')
        return
      }
      // Skip if too many consecutive timeouts (Resolve is probably frozen)
      if (consecutiveTimeouts >= MAX_CONSECUTIVE_TIMEOUTS) {
        log.debug(`Skipping auto-refresh: too many timeouts (${consecutiveTimeouts}), Resolve may be frozen`)
        return
      }
      // Skip if in error cooldown period
      if (now - lastErrorTime < ERROR_COOLDOWN_MS) {
        log.debug(`Skipping auto-refresh: in cooldown (${Math.round((ERROR_COOLDOWN_MS - (now - lastErrorTime)) / 1000)}s remaining)`)
        return
      }
      if (now - lastRefreshTime > davinciConfig.refreshIntervalMs) {
        lastRefreshTime = now
        isRefreshing = true
        log.debug('Auto-refreshing growing clips...')
        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/1c530d06-93f3-4719-9f2a-db5838c77d56',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'davinci.ts:512',message:'Auto-refresh triggered',data:{lastRefreshTime,now},timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'H2'})}).catch(()=>{});
        // #endregion
        try {
          const result = await refreshGrowingClips()
          // #region agent log
          fetch('http://127.0.0.1:7242/ingest/1c530d06-93f3-4719-9f2a-db5838c77d56',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'davinci.ts:518',message:'Auto-refresh result',data:{result},timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'H2'})}).catch(()=>{});
          // #endregion
          if (result.success && result.clipsRefreshed) {
            log.debug(`Auto-refreshed ${result.clipsRefreshed} clip(s)`)
            consecutiveTimeouts = 0 // Reset on success
          } else if (!result.success) {
            const isTimeout = result.error?.includes('Timeout')
            const isNoClipsError = result.error?.includes('No R58 clips found') || 
                                   result.error?.includes('found 0 clips')
            
            if (isTimeout) {
              consecutiveTimeouts++
              lastErrorTime = now
              log.warn(`Auto-refresh timeout (${consecutiveTimeouts}/${MAX_CONSECUTIVE_TIMEOUTS}), entering cooldown`)
            } else if (!isNoClipsError) {
              lastErrorTime = now
              log.warn(`Auto-refresh failed, entering cooldown: ${result.error}`)
            } else {
              log.debug('No clips found yet, will retry')
            }
          }
        } catch (err) {
          lastErrorTime = now
          consecutiveTimeouts++
          log.debug('Auto-refresh failed (non-critical):', err)
        } finally {
          isRefreshing = false
        }
      }
    }
  }
}

/**
 * Notify renderer process
 */
function notifyRenderer(event: string, data: unknown): void {
  const win = mainWindow?.()
  if (win && !win.isDestroyed()) {
    win.webContents.send(event, data)
  }
}

// ============================================
// Project and Multicam Functions
// ============================================

/**
 * Open DaVinci Resolve and load/create a project
 */
async function openOrCreateProject(projectName?: string): Promise<{ success: boolean; error?: string; projectName?: string }> {
  const scriptPath = getResolveScriptPath()
  if (!scriptPath) {
    return { success: false, error: 'DaVinci Resolve scripting path not found' }
  }
  
  // Launch Resolve if not running
  if (!isResolveRunning()) {
    log.info('Launching DaVinci Resolve...')
    try {
      if (process.platform === 'darwin') {
        execSync('open -a "DaVinci Resolve"', { stdio: 'pipe' })
      } else if (process.platform === 'win32') {
        spawn('cmd.exe', ['/c', 'start', '', 'C:\\Program Files\\Blackmagic Design\\DaVinci Resolve\\Resolve.exe'], { detached: true, stdio: 'ignore' })
      }
      // Wait for Resolve to fully start (it takes ~10-15 seconds)
      log.info('Waiting for DaVinci Resolve to initialize...')
      await new Promise(resolve => setTimeout(resolve, 12000))
      
      // Check if it's running now
      let attempts = 0
      while (!isResolveRunning() && attempts < 10) {
        await new Promise(resolve => setTimeout(resolve, 2000))
        attempts++
      }
      
      if (!isResolveRunning()) {
        return { success: false, error: 'DaVinci Resolve failed to start. Please try again.' }
      }
      
      // Give it a bit more time to be fully ready for scripting API
      await new Promise(resolve => setTimeout(resolve, 3000))
    } catch (err) {
      log.error('Failed to launch DaVinci Resolve:', err)
      return { success: false, error: 'Failed to launch DaVinci Resolve' }
    }
  }
  
  const name = projectName || `${davinciConfig.projectNamePrefix}_${new Date().toISOString().split('T')[0]}`
  
  const pythonScript = `
import sys
sys.path.append('${scriptPath.replace(/\\/g, '/')}')
sys.path.append('${scriptPath.replace(/\\/g, '/')}/Modules')

import DaVinciResolveScript as dvr

resolve = dvr.scriptapp("Resolve")
if not resolve:
    print("ERROR: Cannot connect to Resolve")
    sys.exit(1)

pm = resolve.GetProjectManager()
if not pm:
    print("ERROR: Cannot get Project Manager")
    sys.exit(1)

# Try to load existing project first
project = pm.LoadProject("${name}")
if not project:
    # Create new project
    project = pm.CreateProject("${name}")
    if not project:
        print("ERROR: Cannot create project")
        sys.exit(1)
    print("CREATED: ${name}")
else:
    print("LOADED: ${name}")

sys.exit(0)
`
  
  return new Promise((resolve) => {
    const python = spawn('python3', ['-c', pythonScript], {
      stdio: ['pipe', 'pipe', 'pipe'],
      env: { ...process.env, PYTHONDONTWRITEBYTECODE: '1' },
    })
    
    let output = ''
    let timedOut = false
    
    const timeout = setTimeout(() => {
      timedOut = true
      python.kill('SIGTERM')
      resolve({ success: false, error: 'Timeout connecting to Resolve' })
    }, 15000)
    
    python.stdout.on('data', (data) => { output += data.toString() })
    python.stderr.on('data', (data) => { output += data.toString() })
    
    python.on('close', (code) => {
      clearTimeout(timeout)
      if (timedOut) return
      
      if (code === 0) {
        log.info(`DaVinci project: ${output.trim()}`)
        resolve({ success: true, projectName: name })
      } else {
        log.error(`DaVinci project error: ${output.trim()}`)
        resolve({ success: false, error: output.trim() })
      }
    })
    
    python.on('error', (err) => {
      clearTimeout(timeout)
      resolve({ success: false, error: err.message })
    })
  })
}

/**
 * Get recording files from the most recent session
 * Only returns files with matching timestamps (same recording session)
 */
function getRecentRecordings(sessionPattern?: string): string[] {
  const mountPath = findR58MountPath()
  if (!mountPath) {
    log.warn('R58 recordings mount not found. Mount via: mount_smbfs //guest@100.65.219.117/recordings ~/r58-recordings')
    return []
  }
  
  // Collect all files with their timestamps
  let files: { path: string; mtime: number; timestamp: string; cam: string }[] = []
  
  for (const camDir of ['cam0', 'cam1', 'cam2', 'cam3']) {
    const camPath = path.join(mountPath, camDir)
    if (!fs.existsSync(camPath)) continue
    
    try {
      const entries = fs.readdirSync(camPath)
      for (const entry of entries) {
        if (!entry.endsWith('.mkv') && !entry.endsWith('.mp4') && !entry.endsWith('.mov')) continue
        if (sessionPattern && !entry.includes(sessionPattern)) continue
        
        const filePath = path.join(camPath, entry)
        const stat = fs.statSync(filePath)
        
        // Only include files > 1MB (skip empty/failed recordings)
        if (stat.size > 1024 * 1024) {
          // Extract timestamp from filename: recording_YYYYMMDD_HHMMSS.mkv
          const match = entry.match(/recording_(\d{8}_\d{6})/)
          const timestamp = match ? match[1] : ''
          files.push({ path: filePath, mtime: stat.mtimeMs, timestamp, cam: camDir })
        }
      }
    } catch (err) {
      log.debug(`Error reading ${camPath}: ${err}`)
    }
  }
  
  if (files.length === 0) return []
  
  // Sort by modification time (newest first)
  files.sort((a, b) => b.mtime - a.mtime)
  
  // Strategy 1: If sessionPattern provided, filter by it first
  if (sessionPattern) {
    const patternFiles = files.filter(f => f.timestamp && f.timestamp.includes(sessionPattern.replace(/[^0-9_]/g, '')))
    if (patternFiles.length > 0) {
      log.info(`Found ${patternFiles.length} files matching session pattern: ${sessionPattern}`)
      files = patternFiles
    }
  }
  
  // Strategy 2: Try to find files with matching timestamp (same session)
  const newestTimestamp = files[0].timestamp
  if (newestTimestamp) {
    log.info(`Most recent recording session: ${newestTimestamp}`)
    const sessionFiles = files.filter(f => f.timestamp === newestTimestamp)
    
    if (sessionFiles.length > 0) {
      // Deduplicate by camera, keeping newest file per camera
      const byCamera = new Map<string, string>()
      for (const file of sessionFiles) {
        if (!byCamera.has(file.cam)) {
          byCamera.set(file.cam, file.path)
        } else {
          // If we already have a file for this camera, keep the newer one
          const existing = files.find(f => f.path === byCamera.get(file.cam))
          if (existing && file.mtime > existing.mtime) {
            byCamera.set(file.cam, file.path)
          }
        }
      }
      
      log.info(`Found ${byCamera.size} camera(s) for session ${newestTimestamp}`)
      return Array.from(byCamera.values())
    }
  }
  
  // Strategy 3: Fallback - get most recent file from each camera
  log.info('No matching timestamp found, using most recent file from each camera')
  const byCamera = new Map<string, string>()
  for (const file of files) {
    if (!byCamera.has(file.cam)) {
      byCamera.set(file.cam, file.path)
    } else {
      // Keep the newer file
      const existing = files.find(f => f.path === byCamera.get(file.cam))
      if (existing && file.mtime > existing.mtime) {
        byCamera.set(file.cam, file.path)
      }
    }
  }
  
  log.info(`Found ${byCamera.size} camera(s) using most recent files`)
  return Array.from(byCamera.values())
}

/**
 * Create a multicam timeline from media files
 * Supports growing files for edit-while-record workflow
 */
async function createMulticamTimeline(options: {
  projectName?: string
  clipName?: string
  filePaths?: string[]
  syncMethod?: string
  sessionId?: string
}): Promise<{ success: boolean; error?: string; timelineName?: string; filesImported?: number }> {
  const scriptPath = getResolveScriptPath()
  if (!scriptPath) {
    return { success: false, error: 'DaVinci Resolve scripting path not found' }
  }
  
  if (!isResolveRunning()) {
    return { success: false, error: 'DaVinci Resolve is not running' }
  }
  
  // Get file paths - either provided, or find from mounted share
  let filePaths = options.filePaths || []
  if (filePaths.length === 0) {
    // Try to find recent recordings from mounted share
    filePaths = getRecentRecordings(options.sessionId)
    if (filePaths.length === 0) {
      const mountPath = findR58MountPath()
      if (!mountPath) {
        return { 
          success: false, 
          error: 'R58 recordings not mounted. Connect via Finder: smb://100.65.219.117/recordings or mount_smbfs //guest@100.65.219.117/recordings ~/r58-recordings' 
        }
      }
      return { success: false, error: 'No recording files found' }
    }
    log.info(`Found ${filePaths.length} recording files: ${filePaths.map(f => path.basename(f)).join(', ')}`)
  }
  
  const clipName = options.clipName || `Multicam_${new Date().toISOString().replace(/[:.]/g, '-')}`
  const syncMethod = options.syncMethod || 'timecode' // timecode, audio, in_point
  const filesJson = JSON.stringify(filePaths)
  
  const pythonScript = `
import sys
import json
sys.path.append('${scriptPath.replace(/\\/g, '/')}')
sys.path.append('${scriptPath.replace(/\\/g, '/')}/Modules')

import DaVinciResolveScript as dvr

resolve = dvr.scriptapp("Resolve")
if not resolve:
    print("ERROR: Cannot connect to Resolve")
    sys.exit(1)

pm = resolve.GetProjectManager()
project = pm.GetCurrentProject()
if not project:
    print("ERROR: No project open")
    sys.exit(1)

media_pool = project.GetMediaPool()
root_folder = media_pool.GetRootFolder()

# Import files if provided
import os
files = json.loads('${filesJson.replace(/'/g, "\\'")}')
clips = []

print(f"Files to import: {files}")

# Helper function to find clips recursively in all bins
def find_clips_in_folder(folder, target_paths):
    found = []
    # Build a set of full paths AND unique symlink names to match
    target_set = set()
    for p in target_paths:
        target_set.add(p)  # Full path
        target_set.add(os.path.basename(p))  # Symlink name (cam0_recording...)
    
    folder_clips = folder.GetClipList()
    if folder_clips:
        for clip in folder_clips:
            clip_path = clip.GetClipProperty("File Path") or ""
            clip_name = clip.GetName()
            # Match by full path OR symlink name
            if clip_path in target_set or clip_name in target_set:
                found.append(clip)
                print(f"Found clip: {clip_name} at {clip_path}")
                # Don't break - might have multiple matches, but we deduplicate by checking if already in found
    # Search subfolders
    subfolders = folder.GetSubFolderList()
    if subfolders:
        for subfolder in subfolders:
            found.extend(find_clips_in_folder(subfolder, target_paths))
    return found

if files:
    import shutil
    import tempfile
    
    # Check if files exist on disk
    valid_files = []
    for f in files:
        if os.path.exists(f):
            size = os.path.getsize(f)
            print(f"File exists: {f} ({size} bytes)")
            if size > 1000:  # Skip empty/tiny files
                valid_files.append(f)
        else:
            print(f"File NOT found: {f}")
    
    if not valid_files:
        print("ERROR: No valid files to import")
        sys.exit(1)
    
    # Create symlinks with unique names (cam_id prefix) to ensure DaVinci imports them as separate clips
    # DaVinci Resolve identifies clips by filename, not full path, so same-named files from different cameras
    # get deduplicated. Symlinks with unique names solve this while preserving growing file support.
    import subprocess
    import_files = []
    symlink_dir = os.path.expanduser("~/Movies/R58_Import/links")
    os.makedirs(symlink_dir, exist_ok=True)
    
    for i, f in enumerate(valid_files):
        parts = f.split('/')
        cam_id = next((p for p in parts if p.startswith('cam')), f"cam{i}")
        base_name = os.path.basename(f)
        
        is_mov = f.lower().endswith('.mov')
        is_mkv = f.lower().endswith('.mkv')
        
        # Create unique filename: cam0_recording_20260109.mov
        unique_name = f"{cam_id}_{base_name}"
        
        if is_mov:
            # MOV files: Create symlink to source for growing file support!
            # Symlink preserves growing file capability while giving unique name
            symlink_path = os.path.join(symlink_dir, unique_name)
            if os.path.islink(symlink_path) or os.path.exists(symlink_path):
                os.unlink(symlink_path)
            os.symlink(f, symlink_path)
            import_files.append(symlink_path)
            print(f"Created symlink for growing file: {unique_name} -> {f}")
        elif is_mkv:
            # MKV files: remux locally (no growing file support)
            local_dir = os.path.expanduser("~/Movies/R58_Import")
            os.makedirs(local_dir, exist_ok=True)
            local_path = os.path.join(local_dir, unique_name)
            
            source_size = os.path.getsize(f)
            needs_remux = not os.path.exists(local_path) or abs(os.path.getsize(local_path) - source_size) > 10000
            
            if needs_remux:
                print(f"Remuxing MKV {base_name} ({cam_id})...")
                try:
                    result = subprocess.run([
                        'ffmpeg', '-y', '-i', f, '-c', 'copy', local_path
                    ], capture_output=True, text=True, timeout=60)
                    if result.returncode != 0:
                        print(f"ffmpeg error: {result.stderr[:200]}")
                        shutil.copy(f, local_path)
                except Exception as e:
                    print(f"Remux error: {e}")
                    shutil.copy(f, local_path)
            import_files.append(local_path)
        else:
            # MP4 or other: Create symlink for unique naming
            symlink_path = os.path.join(symlink_dir, unique_name)
            if os.path.islink(symlink_path) or os.path.exists(symlink_path):
                os.unlink(symlink_path)
            os.symlink(f, symlink_path)
            import_files.append(symlink_path)
            print(f"Created symlink: {unique_name} -> {f}")
    
    local_files = import_files
    print(f"Files to import: {len(local_files)}")
    
    # Method 1: Try MediaStorage.AddItemListToMediaPool (more reliable)
    print(f"Attempting to import {len(local_files)} files via MediaStorage...")
    try:
        media_storage = resolve.GetMediaStorage()
        if media_storage:
            imported = media_storage.AddItemListToMediaPool(local_files)
            if imported and len(imported) > 0:
                clips = list(imported)
                print(f"MediaStorage import succeeded: {len(clips)} clips")
        else:
            print("MediaStorage not available")
    except Exception as e:
        print(f"MediaStorage error: {e}")
    
    # Method 2: Fallback to media_pool.ImportMedia
    if not clips:
        print("Trying media_pool.ImportMedia...")
        try:
            imported = media_pool.ImportMedia(local_files)
            if imported and len(imported) > 0:
                clips = list(imported)
                print(f"MediaPool import succeeded: {len(clips)} clips")
        except Exception as e:
            print(f"MediaPool error: {e}")
    
    # Method 3: Search existing clips in media pool (may already be imported)
    if not clips:
        print("Searching media pool for existing clips...")
        clips = find_clips_in_folder(root_folder, local_files + valid_files)
        if clips:
            print(f"Found {len(clips)} existing clips in media pool")

if not clips:
    # Last resort: use selected clips
    print("No clips found via import, checking for selected clips...")
    try:
        selected = media_pool.GetSelectedClips()
        if selected and len(selected) > 0:
            clips = list(selected)
            print(f"Using {len(clips)} selected clips")
    except Exception as e:
        print(f"GetSelectedClips error: {e}")
    
    if not clips:
        # Get ALL clips from media pool as last resort
        try:
            all_clips = root_folder.GetClipList()
            if all_clips and len(all_clips) > 0:
                clips = list(all_clips)
                print(f"Using all {len(clips)} clips from root folder")
        except Exception as e:
            print(f"GetClipList error: {e}")
    
    if not clips:
        print("ERROR: Could not import files into DaVinci Resolve.")
        print("Files were copied to: ~/Movies/R58_Import/")
        print("WORKAROUND: Manually drag these files into DaVinci's Media Pool:")
        for f in local_files:
            print(f"  - {f}")
        sys.exit(1)

print(f"Creating multicam timeline from {len(clips)} clips")

# Check if timeline already exists and delete it
timeline_name = "${clipName}_Timeline"
timeline_to_delete = None

try:
    # Method 1: Try project.GetTimelineCount() (most reliable)
    timeline_count = project.GetTimelineCount()
    for i in range(1, timeline_count + 1):
        timeline = project.GetTimelineByIndex(i)
        if timeline and timeline.GetName() == timeline_name:
            timeline_to_delete = timeline
            break
except:
    try:
        # Method 2: Try media_pool.GetTimelineCount() (alternative)
        timeline_count = media_pool.GetTimelineCount()
        for i in range(1, timeline_count + 1):
            timeline = media_pool.GetTimelineByIndex(i)
            if timeline and timeline.GetName() == timeline_name:
                timeline_to_delete = timeline
                break
    except:
        # Method 3: Check current timeline
        try:
            current_timeline = project.GetCurrentTimeline()
            if current_timeline and current_timeline.GetName() == timeline_name:
                timeline_to_delete = current_timeline
        except:
            pass  # If all methods fail, just try to create (might fail if duplicate exists)

# Delete existing timeline if found
if timeline_to_delete:
    try:
        print(f"Deleting existing timeline: {timeline_name}")
        media_pool.DeleteTimelines([timeline_to_delete])
    except Exception as e:
        print(f"Warning: Could not delete existing timeline: {e}")
        # Continue anyway - CreateEmptyTimeline might still work

# Create empty timeline
timeline = media_pool.CreateEmptyTimeline(timeline_name)
if not timeline:
    print("ERROR: Could not create timeline")
    sys.exit(1)

project.SetCurrentTimeline(timeline)

# Add video tracks (we need one per camera)
num_clips = len(clips)
current_tracks = timeline.GetTrackCount("video")
print(f"Current video tracks: {current_tracks}, need: {num_clips}")

for i in range(current_tracks, num_clips):
    result = timeline.AddTrack("video")
    print(f"Added video track: {result}")

# Get timeline frame rate to calculate positions
fps = float(timeline.GetSetting("timelineFrameRate") or 24)
print(f"Timeline FPS: {fps}")

# NEW APPROACH: Set playhead to frame 0, then use AppendToTimeline for each track
# This should place all clips at the current playhead position

# First, set the playhead/current timecode to the start
try:
    timeline.SetCurrentTimecode("00:00:00:00")
    print("Set playhead to 00:00:00:00")
except Exception as e:
    print(f"Could not set playhead: {e}")

added_clips = []
for i, clip in enumerate(clips):
    track_index = i + 1  # V1, V2, V3, etc.
    clip_name = clip.GetName()
    
    print(f"Adding {clip_name} to track V{track_index}...")
    
    # CRITICAL: Reset playhead to frame 0 BEFORE each clip insertion
    # This ensures all clips start at the same position
    try:
        timeline.SetCurrentTimecode("00:00:00:00")
    except:
        pass
    
    # Method 1: Try InsertMediaPoolItemsIntoTimeline with explicit recordFrame
    try:
        result = media_pool.InsertMediaPoolItemsIntoTimeline([{
            "mediaPoolItem": clip,
            "recordFrame": 0,       # Timeline position: frame 0 (absolute)
            "startFrame": 0,        # Clip in point: frame 0
            "trackIndex": track_index,
            "mediaType": 1          # 1 = video
        }])
        
        if result and len(result) > 0:
            added_clips.extend(result)
            print(f"  InsertMediaPoolItemsIntoTimeline: Added to V{track_index}")
            continue  # Success, move to next clip
    except Exception as e:
        print(f"  InsertMediaPoolItemsIntoTimeline error: {e}")
    
    # Method 2: Fallback to AppendToTimeline
    try:
        result = media_pool.AppendToTimeline([{
            "mediaPoolItem": clip,
            "trackIndex": track_index,
            "startFrame": 0,
            "mediaType": 1
        }])
        if result:
            added_clips.extend(result if isinstance(result, list) else [])
            print(f"  AppendToTimeline: Added to V{track_index}")
    except Exception as e2:
        print(f"  AppendToTimeline error: {e2}")

# ALWAYS verify and fix clip positions - DaVinci API often doesn't place clips correctly
print("Verifying and fixing clip positions on timeline...")

# Get all timeline items and FORCE them to frame 0
clips_fixed = 0
for track_idx in range(1, num_clips + 1):
    items = timeline.GetItemListInTrack("video", track_idx)
    if items:
        for item in items:
            try:
                current_start = item.GetStart()
                item_name = item.GetName() if hasattr(item, 'GetName') else f"item_{track_idx}"
                
                if current_start != 0:
                    print(f"V{track_idx}: Moving '{item_name}' from frame {current_start} to frame 0")
                    
                    # Try multiple methods to move the clip
                    # Method 1: SetStart
                    try:
                        item.SetStart(0)
                        clips_fixed += 1
                    except:
                        pass
                    
                    # Verify it moved
                    new_start = item.GetStart()
                    if new_start != 0:
                        print(f"  WARNING: Clip still at frame {new_start} after SetStart(0)")
                else:
                    print(f"V{track_idx}: '{item_name}' already at frame 0 ✓")
            except Exception as e:
                print(f"V{track_idx}: Error checking/moving item: {e}")
    else:
        print(f"V{track_idx}: No items found on this track")

if clips_fixed > 0:
    print(f"Fixed position of {clips_fixed} clip(s)")

print(f"SUCCESS: Created timeline {timeline_name} with {num_clips} clips")
sys.exit(0)
`
  
  return new Promise((resolve) => {
    const python = spawn('python3', ['-c', pythonScript], {
      stdio: ['pipe', 'pipe', 'pipe'],
      env: { ...process.env, PYTHONDONTWRITEBYTECODE: '1' },
    })
    
    let output = ''
    let timedOut = false
    
    const timeout = setTimeout(() => {
      timedOut = true
      python.kill('SIGTERM')
      resolve({ success: false, error: 'Timeout' })
    }, 30000)
    
    python.stdout.on('data', (data) => { output += data.toString() })
    python.stderr.on('data', (data) => { output += data.toString() })
    
    python.on('close', (code) => {
      clearTimeout(timeout)
      if (timedOut) return
      
      if (code === 0 && output.includes('SUCCESS')) {
        log.info(`Multicam created: ${output.trim()}`)
        resolve({ success: true, timelineName: `${clipName}_Timeline`, filesImported: filePaths.length })
      } else {
        log.error(`Multicam error: ${output.trim()}`)
        resolve({ success: false, error: output.trim() })
      }
    })
    
    python.on('error', (err) => {
      clearTimeout(timeout)
      resolve({ success: false, error: err.message })
    })
  })
}

/**
 * Refresh growing clips in DaVinci Resolve by relinking them
 * Forces DaVinci to re-read file metadata (duration, etc.)
 */
async function refreshGrowingClips(): Promise<{ success: boolean; error?: string; clipsRefreshed?: number }> {
  // #region agent log
  fetch('http://127.0.0.1:7242/ingest/1c530d06-93f3-4719-9f2a-db5838c77d56',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'davinci.ts:refreshGrowingClips',message:'refreshGrowingClips called',data:{},timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'H2,H3'})}).catch(()=>{});
  // #endregion
  const scriptPath = getResolveScriptPath()
  if (!scriptPath) {
    return { success: false, error: 'DaVinci Resolve scripting path not found' }
  }
  
  if (!isResolveRunning()) {
    return { success: false, error: 'DaVinci Resolve is not running' }
  }
  
  const pythonScript = `
import sys
import os
sys.path.append('${scriptPath.replace(/\\/g, '/')}')
sys.path.append('${scriptPath.replace(/\\/g, '/')}/Modules')

import DaVinciResolveScript as dvr

resolve = dvr.scriptapp("Resolve")
if not resolve:
    print("ERROR: Cannot connect to Resolve")
    sys.exit(1)

pm = resolve.GetProjectManager()
project = pm.GetCurrentProject()
if not project:
    print("ERROR: No project open")
    sys.exit(1)

media_pool = project.GetMediaPool()
root_folder = media_pool.GetRootFolder()

# Find clips from R58 recordings path
r58_clips = []
clip_original_paths = {}  # Store original (resolved) paths by clip index
seen_paths = set()  # Track unique file paths to prevent duplicates

def find_r58_clips(folder, folder_name="root"):
    """Recursively find clips from R58 recordings path"""
    folder_clips = folder.GetClipList()
    print(f"DEBUG: Searching folder '{folder_name}', found {len(folder_clips) if folder_clips else 0} clips")
    if folder_clips:
        for clip in folder_clips:
            path = clip.GetClipProperty("File Path") or ""
            clip_name = clip.GetName()
            
            # Skip if we've already seen this exact path
            if path in seen_paths:
                print(f"DEBUG: Skipping duplicate clip (by path): {clip_name} -> {path}")
                continue
            
            # Check multiple conditions:
            # 1. Direct path contains r58-recordings or recordings mount
            # 2. Path is in symlink directory (R58_Import/links)
            # 3. Clip name matches symlink pattern (cam0_recording_..., cam2_recording_..., etc.)
            is_r58_clip = False
            original_path = path
            match_reason = ""
            
            if "r58-recordings" in path or ("recordings" in path and ("cam0" in path or "cam1" in path or "cam2" in path or "cam3" in path)):
                is_r58_clip = True
                match_reason = "direct_path"
            elif "R58_Import/links" in path or "R58_Import\\\\links" in path:
                # This is a symlink - try to resolve it to get original path
                is_r58_clip = True
                match_reason = "symlink_path"
                try:
                    if os.path.islink(path):
                        original_path = os.readlink(path)
                        print(f"Resolved symlink: {path} -> {original_path}")
                except:
                    pass
            elif clip_name.startswith("cam0_") or clip_name.startswith("cam1_") or clip_name.startswith("cam2_") or clip_name.startswith("cam3_"):
                # Clip name matches symlink pattern - likely an R58 clip
                is_r58_clip = True
                match_reason = "symlink_name"
                # Try to find original path by checking if symlink exists
                try:
                    symlink_path = os.path.expanduser("~/Movies/R58_Import/links/" + clip_name)
                    if os.path.islink(symlink_path):
                        original_path = os.readlink(symlink_path)
                        print(f"Found symlink for {clip_name}: {symlink_path} -> {original_path}")
                except:
                    pass
            
            if is_r58_clip:
                # Use PATH as the unique key, not clip name (clips can have same name from different cameras)
                seen_paths.add(path)
                clip_index = len(r58_clips)  # Index before appending
                r58_clips.append(clip)
                
                # Store original path by clip index (can't set attributes on Resolve clip objects!)
                clip_original_paths[clip_index] = original_path
                
                # Get clip duration info
                duration = clip.GetClipProperty("Duration") or "unknown"
                frames = clip.GetClipProperty("Frames") or "unknown"
                print(f"Found R58 clip #{clip_index + 1}: {clip_name} (match: {match_reason}) - Path: {path}, Original: {original_path}, Duration: {duration}, Frames: {frames}")
    
    # Search subfolders
    subfolders = folder.GetSubFolderList()
    if subfolders:
        print(f"DEBUG: Found {len(subfolders)} subfolders in '{folder_name}'")
        for subfolder in subfolders:
            subfolder_name = subfolder.GetName() if hasattr(subfolder, 'GetName') else 'unknown'
            find_r58_clips(subfolder, subfolder_name)

find_r58_clips(root_folder)

if not r58_clips:
    print("WARNING: No R58 clips found in media pool")
    print("Make sure clips are imported from ~/r58-recordings or mounted SMB share")
    sys.exit(1)

print(f"Found {len(r58_clips)} R58 clips to refresh")

# ALWAYS use ReplaceClip - RelinkClips reports success but doesn't actually update duration!
# ReplaceClip forces DaVinci to completely re-read the file metadata
refreshed = 0

print(f"Refreshing {len(r58_clips)} clips using ReplaceClip...")

for idx, clip in enumerate(r58_clips):
    clip_name = clip.GetName()
    
    # Get the original file path from our dictionary
    file_path = clip_original_paths.get(idx, "")
    
    if not file_path:
        # Fallback: try to get from clip property
        file_path = clip.GetClipProperty("File Path") or ""
        # If it's a symlink, resolve it
        if file_path and os.path.islink(file_path):
            try:
                file_path = os.readlink(file_path)
                print(f"Resolved symlink for {clip_name}: {file_path}")
            except:
                pass
    
    if not file_path or not os.path.exists(file_path):
        print(f"Skipping {clip_name}: path not found ({file_path})")
        continue
    
    # Get current file info
    try:
        file_size = os.path.getsize(file_path)
        print(f"Refreshing {clip_name}: {file_size} bytes at {file_path}")
    except:
        print(f"Refreshing {clip_name} at {file_path}")
    
    # Use ReplaceClip - this ACTUALLY forces DaVinci to re-read the file
    # It may cause a brief red blink but it's the only reliable way
    try:
        result = clip.ReplaceClip(file_path)
        if result:
            print(f"ReplaceClip succeeded for {clip_name}")
            refreshed += 1
        else:
            print(f"ReplaceClip returned False for {clip_name}")
    except Exception as e:
        print(f"ReplaceClip failed for {clip_name}: {e}")

# Method 3: If still nothing worked, suggest manual refresh
if refreshed == 0:
    print("")
    print("MANUAL WORKAROUND: In DaVinci Resolve:")
    print("1. Right-click on clips in Media Pool")
    print("2. Select 'Replace Selected Clip...'")
    print("3. Navigate to the same file and select it")
    print("This forces DaVinci to re-read the file metadata.")
    sys.exit(1)

print(f"SUCCESS: Refreshed {refreshed} clips")
sys.exit(0)
`
  
  return new Promise((resolve) => {
    const python = spawn('python3', ['-c', pythonScript], {
      stdio: ['pipe', 'pipe', 'pipe'],
      env: { ...process.env, PYTHONDONTWRITEBYTECODE: '1' },
    })
    
    let output = ''
    let timedOut = false
    
    // Shorter timeout (15s) to detect stuck operations faster
    const timeout = setTimeout(() => {
      timedOut = true
      log.warn('Refresh script timeout - killing Python process')
      python.kill('SIGTERM')
      // Force kill after 2 seconds if SIGTERM doesn't work
      setTimeout(() => {
        if (!python.killed) {
          log.warn('SIGTERM failed, sending SIGKILL')
          python.kill('SIGKILL')
        }
      }, 2000)
      resolve({ success: false, error: 'Timeout refreshing clips' })
    }, 15000) // Reduced from 30s to 15s
    
    python.stdout.on('data', (data) => { output += data.toString() })
    python.stderr.on('data', (data) => { output += data.toString() })
    
    python.on('close', (code) => {
      clearTimeout(timeout)
      if (timedOut) return
      
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/1c530d06-93f3-4719-9f2a-db5838c77d56',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'davinci.ts:1382',message:'Refresh clips Python output',data:{code,outputLength:output.length,outputPreview:output.substring(0,2000),hasSuccess:output.includes('SUCCESS')},timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'H1,H3,H4'})}).catch(()=>{});
      // #endregion
      
      if (code === 0 && output.includes('SUCCESS')) {
        // Extract number of clips refreshed
        const match = output.match(/Refreshed (\d+) clips/)
        const clipsRefreshed = match ? parseInt(match[1], 10) : undefined
        log.info(`Refreshed growing clips: ${output.trim()}`)
        resolve({ success: true, clipsRefreshed })
      } else {
        log.error(`Refresh clips error: ${output.trim()}`)
        resolve({ success: false, error: output.trim() })
      }
    })
    
    python.on('error', (err) => {
      clearTimeout(timeout)
      resolve({ success: false, error: err.message })
    })
  })
}

// ============================================
// Public API
// ============================================

/**
 * Start DaVinci integration
 */
export function startDaVinciIntegration(): void {
  if (pollInterval) {
    log.warn('DaVinci integration already running')
    return
  }
  
  davinciConfig.enabled = true
  log.info('Starting DaVinci Resolve integration')
  
  // Initial poll
  pollRecordingStatus()
  
  // Start polling
  pollInterval = setInterval(pollRecordingStatus, davinciConfig.pollIntervalMs)
}

/**
 * Stop DaVinci integration
 */
export function stopDaVinciIntegration(): void {
  if (pollInterval) {
    clearInterval(pollInterval)
    pollInterval = null
  }
  if (refreshInterval) {
    clearInterval(refreshInterval)
    refreshInterval = null
  }
  davinciConfig.enabled = false
  log.info('Stopped DaVinci Resolve integration')
}

/**
 * Get DaVinci integration status
 */
export function getDaVinciStatus(): {
  enabled: boolean
  resolveConnected: boolean
  currentSession: string | null
} {
  return {
    enabled: davinciConfig.enabled,
    resolveConnected: isResolveConnected,
    currentSession: lastSessionId,
  }
}

/**
 * Update DaVinci config
 */
export function updateDaVinciConfig(config: Partial<DaVinciConfig>): void {
  // When enabling DaVinci integration, also enable auto-refresh by default
  if (config.enabled === true && davinciConfig.enabled === false) {
    config.autoRefreshClips = true
    log.info('DaVinci integration enabled - auto-refresh also enabled')
  }
  // When disabling DaVinci integration, also disable auto-refresh
  if (config.enabled === false) {
    config.autoRefreshClips = false
  }
  
  Object.assign(davinciConfig, config)
  log.info('DaVinci config updated:', davinciConfig)
}

/**
 * Setup IPC handlers for DaVinci integration
 */
export function setupDaVinciHandlers(getWindow: () => BrowserWindow | null): void {
  mainWindow = getWindow
  
  ipcMain.handle('davinci-start', () => {
    startDaVinciIntegration()
    return { success: true }
  })
  
  ipcMain.handle('davinci-stop', () => {
    stopDaVinciIntegration()
    return { success: true }
  })
  
  ipcMain.handle('davinci-status', async () => {
    const status = getDaVinciStatus()
    // Do a full Python scripting API check (not just process check)
    status.resolveConnected = await checkResolveConnection(true)
    isResolveConnected = status.resolveConnected  // Keep module state in sync
    lastResolveCheck = Date.now()
    return status
  })
  
  ipcMain.handle('davinci-config', (_event, config?: Partial<DaVinciConfig>) => {
    if (config) {
      updateDaVinciConfig(config)
    }
    return davinciConfig
  })
  
  ipcMain.handle('davinci-check-resolve', async () => {
    // Do a full Python check when explicitly requested
    const connected = await checkResolveConnection(true)
    isResolveConnected = connected
    lastResolveCheck = Date.now()
    return { connected, scriptPath: getResolveScriptPath() }
  })
  
  ipcMain.handle('davinci-open-project', async (_event, projectName?: string) => {
    return await openOrCreateProject(projectName)
  })
  
  ipcMain.handle('davinci-create-multicam', async (_event, options: {
    projectName?: string
    clipName?: string
    filePaths?: string[]
    syncMethod?: string
    sessionId?: string
  }) => {
    const result = await createMulticamTimeline(options)
    // Enable auto-refresh now that clips are imported
    if (result.success && result.filesImported && result.filesImported > 0) {
      clipsImported = true
      consecutiveTimeouts = 0 // Reset timeout counter for fresh start
      log.info('Clips imported successfully, auto-refresh enabled')
    }
    return result
  })
  
  ipcMain.handle('davinci-check-mount', () => {
    const mountPath = findR58MountPath()
    return {
      mounted: !!mountPath,
      path: mountPath,
      hint: mountPath ? null : 'Mount via: smb://100.65.219.117/recordings or run: mount_smbfs //guest@100.65.219.117/recordings ~/r58-recordings'
    }
  })
  
  ipcMain.handle('davinci-get-recordings', (_event, sessionPattern?: string) => {
    return getRecentRecordings(sessionPattern)
  })
  
  ipcMain.handle('davinci-refresh-clips', async () => {
    // #region agent log
    fetch('http://127.0.0.1:7242/ingest/1c530d06-93f3-4719-9f2a-db5838c77d56',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'davinci.ts:IPC:refresh-clips',message:'Manual refresh button clicked',data:{},timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'H1,H3'})}).catch(()=>{});
    // #endregion
    const result = await refreshGrowingClips()
    log.info('Manual refresh result:', result)
    return result
  })
  
  log.info('DaVinci IPC handlers registered')
}
