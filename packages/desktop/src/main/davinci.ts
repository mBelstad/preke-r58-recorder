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
}

let pollInterval: NodeJS.Timeout | null = null
let lastSessionId: string | null = null
let isResolveConnected = false
let mainWindow: (() => BrowserWindow | null) | null = null
let lastResolveCheck = 0
const RESOLVE_CHECK_INTERVAL = 30000 // Only check Resolve connection every 30 seconds

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
          resolve(JSON.parse(data))
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
  const files: { path: string; mtime: number; timestamp: string; cam: string }[] = []
  
  for (const camDir of ['cam0', 'cam1', 'cam2', 'cam3']) {
    const camPath = path.join(mountPath, camDir)
    if (!fs.existsSync(camPath)) continue
    
    try {
      const entries = fs.readdirSync(camPath)
      for (const entry of entries) {
        if (!entry.endsWith('.mkv') && !entry.endsWith('.mp4')) continue
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
  
  // Find the most recent timestamp
  const newestTimestamp = files[0].timestamp
  log.info(`Most recent recording session: ${newestTimestamp}`)
  
  // Get all files with matching timestamp (same session)
  const sessionFiles = files.filter(f => f.timestamp === newestTimestamp)
  
  // Deduplicate by camera
  const byCamera = new Map<string, string>()
  for (const file of sessionFiles) {
    if (!byCamera.has(file.cam)) {
      byCamera.set(file.cam, file.path)
    }
  }
  
  log.info(`Found ${byCamera.size} camera(s) for session ${newestTimestamp}`)
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
def find_clips_in_folder(folder, target_names):
    found = []
    folder_clips = folder.GetClipList()
    if folder_clips:
        for clip in folder_clips:
            clip_name = clip.GetName()
            clip_path = clip.GetClipProperty("File Path") or ""
            for target in target_names:
                if target in clip_name or target in clip_path or os.path.basename(target) in clip_name:
                    found.append(clip)
                    print(f"Found existing clip: {clip_name}")
                    break
    # Search subfolders
    subfolders = folder.GetSubFolderList()
    if subfolders:
        for subfolder in subfolders:
            found.extend(find_clips_in_folder(subfolder, target_names))
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
    
    # Copy files locally for import
    # Fragmented MP4 files don't need remuxing - they have proper metadata
    # MKV files need remuxing to fix missing duration
    import subprocess
    local_dir = os.path.expanduser("~/Movies/R58_Import")
    os.makedirs(local_dir, exist_ok=True)
    local_files = []
    
    for i, f in enumerate(valid_files):
        # Extract camera ID from path (e.g., cam0, cam2, cam3)
        parts = f.split('/')
        cam_id = next((p for p in parts if p.startswith('cam')), f"cam{i}")
        base_name = os.path.basename(f)
        # Include camera ID in filename to avoid conflicts
        local_name = f"{cam_id}_{base_name}"
        local_path = os.path.join(local_dir, local_name)
        
        # Check if we need to process
        source_size = os.path.getsize(f)
        needs_copy = not os.path.exists(local_path) or abs(os.path.getsize(local_path) - source_size) > 10000
        
        is_mp4 = f.lower().endswith('.mp4')
        is_mkv = f.lower().endswith('.mkv')
        
        if needs_copy:
            if is_mkv:
                # MKV files need remuxing to fix missing duration metadata
                print(f"Remuxing MKV {base_name} ({cam_id})...")
                try:
                    result = subprocess.run([
                        'ffmpeg', '-y', '-i', f, '-c', 'copy', local_path
                    ], capture_output=True, text=True, timeout=60)
                    if result.returncode != 0:
                        print(f"ffmpeg error: {result.stderr[:200]}")
                        shutil.copy(f, local_path)
                except Exception as e:
                    print(f"Remux error: {e}, falling back to copy")
                    shutil.copy(f, local_path)
            else:
                # Fragmented MP4 files just need copying (have proper metadata)
                print(f"Copying {base_name} ({cam_id})...")
                shutil.copy(f, local_path)
        else:
            print(f"Using cached: {local_name}")
        
        local_files.append(local_path)
    
    print(f"Files ready in {local_dir}")
    
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

# Create empty timeline first
timeline = media_pool.CreateEmptyTimeline("${clipName}_Timeline")
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

# Add each clip to a separate video track, all starting at frame 0
for i, clip in enumerate(clips):
    track_index = i + 1  # V1, V2, V3, etc.
    clip_name = clip.GetName()
    
    # Use AppendToTimeline with clip info to specify track
    result = media_pool.AppendToTimeline([{
        "mediaPoolItem": clip,
        "trackIndex": track_index,
        "startFrame": 0,
        "mediaType": 1  # 1 = video
    }])
    
    if result:
        print(f"Added {clip_name} to track V{track_index}")
    else:
        # Fallback: simple append (will be on V1)
        media_pool.AppendToTimeline([clip])
        print(f"Fallback: Added {clip_name} (may be on wrong track)")

print(f"SUCCESS: Created timeline ${clipName}_Timeline with {len(clips)} clips on separate tracks")
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
    return await createMulticamTimeline(options)
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
  
  log.info('DaVinci IPC handlers registered')
}
