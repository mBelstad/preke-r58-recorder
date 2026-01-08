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
  pollIntervalMs: 2000,
  projectNamePrefix: 'Preke',
  autoCreateProject: true,
  autoImportMedia: true,
  createMulticamTimeline: true,
}

let pollInterval: NodeJS.Timeout | null = null
let lastSessionId: string | null = null
let isResolveConnected = false
let mainWindow: (() => BrowserWindow | null) | null = null

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
 */
async function checkResolveConnection(): Promise<boolean> {
  const scriptPath = getResolveScriptPath()
  if (!scriptPath) {
    log.debug('DaVinci Resolve scripting path not found')
    return false
  }
  
  if (!isResolveRunning()) {
    log.debug('DaVinci Resolve is not running')
    return false
  }
  
  // Try to connect via Python script
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
      timeout: 5000,
    })
    
    let output = ''
    python.stdout.on('data', (data) => { output += data.toString() })
    python.stderr.on('data', (data) => { output += data.toString() })
    
    python.on('close', (code) => {
      const connected = code === 0 && output.includes('CONNECTED')
      log.debug(`DaVinci Resolve connection check: ${connected ? 'OK' : 'Failed'} (${output.trim()})`)
      resolve(connected)
    })
    
    python.on('error', () => {
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
  // Check Resolve connection periodically
  const wasConnected = isResolveConnected
  isResolveConnected = await checkResolveConnection()
  
  if (wasConnected !== isResolveConnected) {
    log.info(`DaVinci Resolve connection: ${isResolveConnected ? 'Connected' : 'Disconnected'}`)
    notifyRenderer('davinci-connection-changed', { connected: isResolveConnected })
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
    // Also do a fresh connection check
    status.resolveConnected = await checkResolveConnection()
    return status
  })
  
  ipcMain.handle('davinci-config', (_event, config?: Partial<DaVinciConfig>) => {
    if (config) {
      updateDaVinciConfig(config)
    }
    return davinciConfig
  })
  
  ipcMain.handle('davinci-check-resolve', async () => {
    const connected = await checkResolveConnection()
    isResolveConnected = connected
    return { connected, scriptPath: getResolveScriptPath() }
  })
  
  log.info('DaVinci IPC handlers registered')
}
