/**
 * Auto-update service using electron-updater
 * 
 * Handles checking for updates, downloading, and installing new versions
 * from GitHub Releases.
 */

import { autoUpdater } from 'electron-updater'
import { getMainWindow } from './window'
import { log } from './logger'

// Configure auto-updater
autoUpdater.autoDownload = false // Don't auto-download, let user decide
autoUpdater.autoInstallOnAppQuit = true // Install on quit if update is ready

// Log update events
autoUpdater.logger = {
  info: (message: string) => log.info(`[Updater] ${message}`),
  warn: (message: string) => log.warn(`[Updater] ${message}`),
  error: (message: string) => log.error(`[Updater] ${message}`),
  debug: (message: string) => log.debug(`[Updater] ${message}`),
}

/**
 * Check for updates (manual check)
 * Returns update info if available, null if up to date
 */
export async function checkForUpdates(): Promise<{
  updateAvailable: boolean
  version?: string
  releaseDate?: Date
  releaseNotes?: string
  error?: string
}> {
  try {
    log.info('Checking for updates...')
    const result = await autoUpdater.checkForUpdates()
    
    if (!result || !result.updateInfo) {
      return { updateAvailable: false }
    }

    const updateInfo = result.updateInfo
    const updateAvailable = updateInfo.version !== autoUpdater.currentVersion.version

    if (updateAvailable) {
      log.info(`Update available: ${updateInfo.version} (current: ${autoUpdater.currentVersion.version})`)
      return {
        updateAvailable: true,
        version: updateInfo.version,
        releaseDate: updateInfo.releaseDate ? new Date(updateInfo.releaseDate) : undefined,
        releaseNotes: updateInfo.releaseNotes as string | undefined,
      }
    } else {
      log.info('App is up to date')
      return { updateAvailable: false }
    }
  } catch (error) {
    log.error('Failed to check for updates:', error)
    return {
      updateAvailable: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    }
  }
}

/**
 * Download the available update
 */
export async function downloadUpdate(): Promise<{
  success: boolean
  error?: string
}> {
  try {
    log.info('Downloading update...')
    await autoUpdater.downloadUpdate()
    return { success: true }
  } catch (error) {
    log.error('Failed to download update:', error)
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    }
  }
}

/**
 * Install the downloaded update and restart the app
 */
export function installUpdate(): void {
  log.info('Installing update and restarting...')
  autoUpdater.quitAndInstall(false, true) // isSilent=false, isForceRunAfter=true
}

/**
 * Get current app version
 */
export function getCurrentVersion(): string {
  return autoUpdater.currentVersion.version
}

/**
 * Setup update event listeners
 */
export function setupUpdateListeners(): void {
  const win = getMainWindow()

  autoUpdater.on('checking-for-update', () => {
    log.info('Checking for update...')
    win?.webContents.send('update-checking')
  })

  autoUpdater.on('update-available', (info) => {
    log.info('Update available:', info.version)
    win?.webContents.send('update-available', {
      version: info.version,
      releaseDate: info.releaseDate,
      releaseNotes: info.releaseNotes,
    })
  })

  autoUpdater.on('update-not-available', (info) => {
    log.info('Update not available. Current version:', info.version)
    win?.webContents.send('update-not-available', {
      version: info.version,
    })
  })

  autoUpdater.on('error', (error) => {
    log.error('Update error:', error)
    win?.webContents.send('update-error', {
      message: error.message,
    })
  })

  autoUpdater.on('download-progress', (progress) => {
    log.debug(`Download progress: ${Math.round(progress.percent)}%`)
    win?.webContents.send('update-download-progress', {
      percent: progress.percent,
      transferred: progress.transferred,
      total: progress.total,
    })
  })

  autoUpdater.on('update-downloaded', (info) => {
    log.info('Update downloaded:', info.version)
    win?.webContents.send('update-downloaded', {
      version: info.version,
      releaseDate: info.releaseDate,
      releaseNotes: info.releaseNotes,
    })
  })
}
