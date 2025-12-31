/**
 * Tailscale Integration for R58 Discovery
 * 
 * Enables P2P connectivity to R58 devices via Tailscale mesh network.
 * This provides reliable connectivity across different networks without
 * routing video through a VPS.
 * 
 * How it works:
 * 1. Detects if Tailscale is installed and running
 * 2. Gets list of peers on the tailnet
 * 3. Probes R58 devices (by hostname pattern or service port)
 * 4. Returns discovered devices with Tailscale IPs for P2P connection
 */

import { exec, execSync } from 'child_process'
import { promisify } from 'util'
import log from 'electron-log/main'
import * as http from 'http'
import * as fs from 'fs'

const execAsync = promisify(exec)

/**
 * Get the Tailscale CLI command path
 * Handles different installation methods (macOS app, brew, linux package)
 */
function getTailscaleCommand(): string {
  // Check various locations
  const possiblePaths = [
    '/usr/local/bin/tailscale',
    '/opt/homebrew/bin/tailscale',
    '/usr/bin/tailscale',
    // macOS App Store version
    '/Applications/Tailscale.app/Contents/MacOS/Tailscale',
  ]

  // Check if tailscale is in PATH
  try {
    execSync('which tailscale', { stdio: 'pipe' })
    return 'tailscale'
  } catch {
    // Not in PATH, check known locations
  }

  for (const path of possiblePaths) {
    if (fs.existsSync(path)) {
      log.info(`Found Tailscale CLI at: ${path}`)
      return `"${path}"`
    }
  }

  // Default, may fail
  return 'tailscale'
}

// Cache the tailscale command
let tailscaleCmd: string | null = null
function getTailscale(): string {
  if (!tailscaleCmd) {
    tailscaleCmd = getTailscaleCommand()
  }
  return tailscaleCmd
}

export interface TailscaleDevice {
  id: string
  name: string
  hostname: string
  tailscaleIp: string
  online: boolean
  os?: string
  lastSeen?: string
  relay?: string  // If set, using DERP relay instead of P2P
  curAddr?: string  // Direct P2P address if hole-punched
  isP2P: boolean  // True if direct connection, false if via DERP
}

export interface TailscaleStatus {
  installed: boolean
  running: boolean
  loggedIn: boolean
  selfIp?: string
  selfHostname?: string
  version?: string
  error?: string
}

/**
 * Check if Tailscale is installed and get its status
 */
export async function getTailscaleStatus(): Promise<TailscaleStatus> {
  try {
    // Try to get Tailscale status
    const { stdout } = await execAsync(`${getTailscale()} status --json`, { timeout: 5000 })
    const status = JSON.parse(stdout)

    return {
      installed: true,
      running: true,
      loggedIn: !!status.Self,
      selfIp: status.Self?.TailscaleIPs?.[0],
      selfHostname: status.Self?.HostName,
      version: status.Version,
    }
  } catch (error: unknown) {
    const err = error as { code?: string; message?: string }
    
    // Check if Tailscale is installed but not running
    if (err.message?.includes('not running') || err.message?.includes('stopped')) {
      return {
        installed: true,
        running: false,
        loggedIn: false,
        error: 'Tailscale is not running',
      }
    }
    
    // Check if Tailscale is not logged in
    if (err.message?.includes('not logged in')) {
      return {
        installed: true,
        running: true,
        loggedIn: false,
        error: 'Tailscale is not logged in',
      }
    }

    // Tailscale not installed
    if (err.code === 'ENOENT' || err.message?.includes('command not found')) {
      return {
        installed: false,
        running: false,
        loggedIn: false,
        error: 'Tailscale is not installed',
      }
    }

    return {
      installed: false,
      running: false,
      loggedIn: false,
      error: err.message || 'Unknown error',
    }
  }
}

/**
 * Get all peers on the Tailscale network
 */
export async function getTailscalePeers(): Promise<TailscaleDevice[]> {
  try {
    const { stdout } = await execAsync(`${getTailscale()} status --json`, { timeout: 5000 })
    const status = JSON.parse(stdout)

    const peers: TailscaleDevice[] = []
    const peerMap = status.Peer || {}

    for (const [, peer] of Object.entries(peerMap)) {
      const p = peer as {
        ID?: string
        HostName?: string
        DNSName?: string
        TailscaleIPs?: string[]
        Online?: boolean
        OS?: string
        LastSeen?: string
        Relay?: string
        CurAddr?: string
      }
      
      // Skip funnel-ingress-node (Tailscale's internal nodes)
      if (p.HostName?.includes('funnel-ingress')) continue

      const tailscaleIp = p.TailscaleIPs?.[0]
      if (!tailscaleIp) continue

      // Determine if connection is P2P
      const isP2P = !!p.CurAddr && !p.CurAddr.includes('derp')

      peers.push({
        id: p.ID || `ts-${tailscaleIp.replace(/\./g, '-')}`,
        name: p.HostName || 'Unknown',
        hostname: p.DNSName || p.HostName || tailscaleIp,
        tailscaleIp,
        online: p.Online || false,
        os: p.OS,
        lastSeen: p.LastSeen,
        relay: p.Relay,
        curAddr: p.CurAddr,
        isP2P,
      })
    }

    return peers
  } catch (error) {
    log.error('Failed to get Tailscale peers:', error)
    return []
  }
}

/**
 * Probe a Tailscale peer to check if it's an R58 device
 */
async function probeR58Device(
  ip: string,
  port: number = 8000,
  timeout: number = 2000
): Promise<{ isR58: boolean; version?: string }> {
  return new Promise((resolve) => {
    const req = http.get(
      `http://${ip}:${port}/health`,
      { timeout },
      (res) => {
        if (res.statusCode !== 200) {
          resolve({ isR58: false })
          return
        }

        let data = ''
        res.on('data', (chunk) => (data += chunk))
        res.on('end', () => {
          try {
            const json = JSON.parse(data)
            // Check if it looks like an R58 health response
            if (json.status === 'healthy' && (json.platform || json.gstreamer)) {
              resolve({ isR58: true, version: json.platform })
            } else {
              resolve({ isR58: false })
            }
          } catch {
            resolve({ isR58: false })
          }
        })
      }
    )

    req.on('error', () => resolve({ isR58: false }))
    req.on('timeout', () => {
      req.destroy()
      resolve({ isR58: false })
    })
  })
}

/**
 * Find R58 devices on the Tailscale network
 * 
 * Discovery methods:
 * 1. Hostname matching (contains 'r58', 'preke', 'linaro', 'recorder')
 * 2. Probe port 8000 for R58 API
 */
export async function findR58DevicesOnTailscale(): Promise<TailscaleDevice[]> {
  const status = await getTailscaleStatus()
  
  if (!status.installed || !status.running || !status.loggedIn) {
    log.info('Tailscale not available:', status.error || 'not ready')
    return []
  }

  log.info('Searching for R58 devices on Tailscale...')
  const peers = await getTailscalePeers()
  const onlinePeers = peers.filter((p) => p.online)
  
  log.info(`Found ${onlinePeers.length} online Tailscale peers`)

  // R58-related hostname patterns
  const r58Patterns = [/r58/i, /preke/i, /linaro/i, /recorder/i]
  
  const r58Devices: TailscaleDevice[] = []

  // Check each online peer
  const probePromises = onlinePeers.map(async (peer) => {
    // First, check hostname pattern
    const matchesPattern = r58Patterns.some((p) => p.test(peer.name) || p.test(peer.hostname))
    
    // Probe the device
    const probeResult = await probeR58Device(peer.tailscaleIp)
    
    if (probeResult.isR58 || matchesPattern) {
      if (probeResult.isR58) {
        log.info(`Found R58 device: ${peer.name} at ${peer.tailscaleIp} (${peer.isP2P ? 'P2P' : 'DERP relay'})`)
        r58Devices.push(peer)
      } else if (matchesPattern) {
        log.debug(`Hostname matches R58 pattern but probe failed: ${peer.name}`)
      }
    }
  })

  await Promise.all(probePromises)

  return r58Devices
}

/**
 * Ping a Tailscale peer to establish P2P connection
 * Returns the connection type (P2P or DERP)
 */
export async function pingTailscalePeer(hostname: string): Promise<{
  success: boolean
  latencyMs?: number
  isP2P?: boolean
  peerAddr?: string
}> {
  try {
    const { stdout } = await execAsync(`${getTailscale()} ping --c 3 "${hostname}"`, { timeout: 10000 })
    
    // Parse ping output
    // Example: "pong from hostname (100.x.x.x) via DERP(ams) in 51ms"
    // Example: "pong from hostname (100.x.x.x) via 192.168.1.78:41641 in 1ms"
    
    const lines = stdout.trim().split('\n')
    const lastLine = lines[lines.length - 1]
    
    const isP2P = lastLine.includes('via ') && !lastLine.includes('DERP')
    const latencyMatch = lastLine.match(/in (\d+)ms/)
    const addrMatch = lastLine.match(/via ([^\s]+)/)
    
    return {
      success: true,
      latencyMs: latencyMatch ? parseInt(latencyMatch[1]) : undefined,
      isP2P,
      peerAddr: addrMatch ? addrMatch[1] : undefined,
    }
  } catch (error) {
    log.error('Tailscale ping failed:', error)
    return { success: false }
  }
}

/**
 * Get direct P2P URL for an R58 device
 * Pings the device first to establish P2P connection
 */
export async function getR58TailscaleUrl(device: TailscaleDevice): Promise<{
  url: string
  isP2P: boolean
  latencyMs?: number
}> {
  // Ping to establish/verify P2P connection
  const pingResult = await pingTailscalePeer(device.hostname || device.tailscaleIp)
  
  const url = `http://${device.tailscaleIp}:8000`
  
  return {
    url,
    isP2P: pingResult.isP2P || false,
    latencyMs: pingResult.latencyMs,
  }
}

