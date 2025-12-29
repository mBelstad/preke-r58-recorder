/**
 * Logging utility using electron-log
 * Provides file-based logging and support bundle export
 */

import electronLog from 'electron-log'
import { app } from 'electron'
import * as fs from 'fs'
import * as path from 'path'
import { deviceStore } from './deviceStore'

// Re-export the log object for convenience
export const log = electronLog

/**
 * Initialize the logger with proper configuration
 */
export function initializeLogger(): void {
  // File transport configuration
  log.transports.file.level = 'info'
  log.transports.file.maxSize = 10 * 1024 * 1024 // 10MB
  log.transports.file.format = '[{y}-{m}-{d} {h}:{i}:{s}.{ms}] [{level}] {text}'
  
  // Console transport (for development)
  log.transports.console.level = app.isPackaged ? 'warn' : 'debug'
  log.transports.console.format = '[{h}:{i}:{s}] [{level}] {text}'

  // Log file location
  const logPath = log.transports.file.getFile().path
  log.info(`Log file: ${logPath}`)
}

/**
 * Get the path to the log file
 */
export function getLogFilePath(): string {
  return log.transports.file.getFile().path
}

/**
 * Get the log directory
 */
export function getLogDirectory(): string {
  return path.dirname(getLogFilePath())
}

/**
 * Read recent log entries
 */
export function readRecentLogs(maxLines = 1000): string {
  try {
    const logPath = getLogFilePath()
    if (!fs.existsSync(logPath)) {
      return ''
    }

    const content = fs.readFileSync(logPath, 'utf-8')
    const lines = content.split('\n')
    
    // Return last N lines
    return lines.slice(-maxLines).join('\n')
  } catch (error) {
    log.error('Failed to read logs:', error)
    return ''
  }
}

/**
 * Create a support bundle with logs and configuration
 */
export async function exportSupportBundle(outputPath: string): Promise<void> {
  const archiver = await import('archiver')
  
  return new Promise((resolve, reject) => {
    const output = fs.createWriteStream(outputPath)
    const archive = archiver.default('zip', { zlib: { level: 9 } })

    output.on('close', () => {
      log.info(`Support bundle created: ${outputPath} (${archive.pointer()} bytes)`)
      resolve()
    })

    archive.on('error', (err: Error) => {
      log.error('Failed to create support bundle:', err)
      reject(err)
    })

    archive.pipe(output)

    // Add app info
    const appInfo = {
      version: app.getVersion(),
      electron: process.versions.electron,
      chrome: process.versions.chrome,
      node: process.versions.node,
      platform: process.platform,
      arch: process.arch,
      exportedAt: new Date().toISOString()
    }
    archive.append(JSON.stringify(appInfo, null, 2), { name: 'app-info.json' })

    // Add device configuration (with potential sensitive data awareness)
    const deviceConfig = deviceStore.getConfigForExport()
    archive.append(JSON.stringify(deviceConfig, null, 2), { name: 'device-config.json' })

    // Add log files
    const logDir = getLogDirectory()
    if (fs.existsSync(logDir)) {
      archive.directory(logDir, 'logs')
    }

    // Finalize the archive
    archive.finalize()
  })
}

/**
 * Simple support bundle export without archiver dependency
 * (Fallback for when archiver is not available)
 */
export async function exportSupportBundleSimple(outputPath: string): Promise<void> {
  // If archiver is not installed, create a simple JSON export
  const bundleData = {
    appInfo: {
      version: app.getVersion(),
      electron: process.versions.electron,
      chrome: process.versions.chrome,
      node: process.versions.node,
      platform: process.platform,
      arch: process.arch,
      exportedAt: new Date().toISOString()
    },
    deviceConfig: deviceStore.getConfigForExport(),
    recentLogs: readRecentLogs(500)
  }

  fs.writeFileSync(
    outputPath.replace('.zip', '.json'),
    JSON.stringify(bundleData, null, 2)
  )
  
  log.info(`Support bundle (JSON) created: ${outputPath}`)
}

