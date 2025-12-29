/**
 * Device Discovery - Find R58/Preke devices on local network
 * 
 * Uses multiple methods:
 * 1. mDNS/Bonjour (if available) - looks for _http._tcp services with preke/r58 names
 * 2. HTTP probing - scans local subnet for R58 API endpoints
 * 3. Known hostnames - tries common names like r58.local, preke.local
 */

import { ipcMain, BrowserWindow } from 'electron'
import log from 'electron-log/main'
import * as http from 'http'
import * as https from 'https'
import * as dns from 'dns'
import * as os from 'os'

export interface DiscoveredDevice {
  id: string
  name: string
  host: string
  port: number
  url: string
  source: 'mdns' | 'probe' | 'hostname'
  status?: string
  version?: string
}

let isScanning = false
let scanAbortController: AbortController | null = null

/**
 * Get local IP address(es) to determine network to scan
 * Filters out virtual/VPN interfaces for faster scanning
 */
function getLocalNetworks(): { ip: string; subnet: string }[] {
  const networks: { ip: string; subnet: string }[] = []
  const interfaces = os.networkInterfaces()

  // Skip virtual/VPN/container interfaces
  const skipPatterns = [
    /^feth/i,      // macOS sharing
    /^vmnet/i,     // VMware
    /^vboxnet/i,   // VirtualBox
    /^docker/i,    // Docker
    /^br-/i,       // Docker bridges
    /^veth/i,      // Container veth
    /^utun/i,      // macOS VPN tunnels
    /^tun/i,       // VPN tunnels
    /^tap/i,       // VPN taps
    /^tailscale/i, // Tailscale VPN
    /^wg/i,        // WireGuard
  ]

  for (const [name, addrs] of Object.entries(interfaces)) {
    if (!addrs) continue
    
    // Skip virtual interfaces
    if (skipPatterns.some(p => p.test(name))) {
      log.debug(`Skipping virtual interface: ${name}`)
      continue
    }

    for (const addr of addrs) {
      // Only IPv4, non-internal addresses
      if (addr.family === 'IPv4' && !addr.internal) {
        const parts = addr.address.split('.')
        const subnet = parts.slice(0, 3).join('.')
        
        // Skip link-local addresses (169.254.x.x)
        if (parts[0] === '169' && parts[1] === '254') {
          log.debug(`Skipping link-local address: ${addr.address}`)
          continue
        }

        networks.push({ ip: addr.address, subnet })
        log.info(`Found scannable network: ${name} (${addr.address})`)
      }
    }
  }

  return networks
}

/**
 * Try to resolve common R58 hostnames via mDNS/DNS
 */
async function tryKnownHostnames(): Promise<DiscoveredDevice[]> {
  const hostnames = [
    'r58.local',
    'preke.local',
    'preke-r58.local',
    'recorder.local',
    'r58-api.local'
  ]

  const devices: DiscoveredDevice[] = []

  for (const hostname of hostnames) {
    try {
      const addresses = await new Promise<string[]>((resolve) => {
        dns.resolve4(hostname, (err, addrs) => {
          if (err) resolve([])
          else resolve(addrs || [])
        })
      })

      if (addresses.length > 0) {
        const ip = addresses[0]
        log.info(`Resolved ${hostname} to ${ip}`)
        
        // Probe to verify it's actually an R58
        const device = await probeDevice(ip, 8000)
        if (device) {
          device.source = 'hostname'
          device.host = hostname
          devices.push(device)
        }
      }
    } catch (error) {
      // Hostname not found, continue
    }
  }

  return devices
}

/**
 * Probe a single IP:port for R58 API
 */
async function probeDevice(
  ip: string, 
  port: number, 
  timeout: number = 800  // Fast timeout for LAN
): Promise<DiscoveredDevice | null> {
  // Only probe the primary port first for speed
  const urls = [
    `http://${ip}:${port}`,
  ]

  for (const baseUrl of urls) {
    try {
      const result = await probeUrl(`${baseUrl}/api/v1/health`, timeout)
      if (result) {
        return {
          id: `preke-${ip.replace(/\./g, '-')}`,
          name: result.device_name || 'Preke Device',
          host: ip,
          port: parseInt(baseUrl.split(':').pop() || '8000'),
          url: baseUrl,
          source: 'probe',
          status: result.status,
          version: result.api_version
        }
      }
    } catch (error) {
      // Continue trying other URLs
    }
  }

  return null
}

/**
 * HTTP probe a specific URL
 */
function probeUrl(url: string, timeout: number): Promise<any | null> {
  return new Promise((resolve) => {
    const isHttps = url.startsWith('https://')
    const client = isHttps ? https : http

    const options = {
      timeout,
      rejectUnauthorized: false, // Accept self-signed certs for LAN devices
    }

    const req = client.get(url, options, (res) => {
      if (res.statusCode !== 200) {
        resolve(null)
        return
      }

      let data = ''
      res.on('data', chunk => data += chunk)
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

/**
 * Scan local subnet for devices
 * Optimized: larger batches, shorter timeouts, skip broadcast addresses
 */
async function scanSubnet(
  subnet: string,
  onDeviceFound: (device: DiscoveredDevice) => void,
  abortSignal?: AbortSignal
): Promise<void> {
  const batchSize = 50 // Probe 50 IPs at a time for speed
  const port = 8000
  const timeout = 600 // 600ms is plenty for LAN

  for (let i = 1; i <= 254; i += batchSize) {
    if (abortSignal?.aborted) break

    const batch: Promise<DiscoveredDevice | null>[] = []
    for (let j = i; j < Math.min(i + batchSize, 255); j++) {
      const ip = `${subnet}.${j}`
      batch.push(probeDevice(ip, port, timeout))
    }

    const results = await Promise.all(batch)
    for (const device of results) {
      if (device) {
        onDeviceFound(device)
      }
    }
  }
}

/**
 * Start device discovery
 */
async function startDiscovery(window: BrowserWindow): Promise<void> {
  if (isScanning) {
    log.warn('Discovery already in progress')
    return
  }

  isScanning = true
  scanAbortController = new AbortController()

  log.info('Starting device discovery...')
  window.webContents.send('discovery:started')

  const foundDevices = new Map<string, DiscoveredDevice>()

  const onDeviceFound = (device: DiscoveredDevice) => {
    if (!foundDevices.has(device.id)) {
      foundDevices.set(device.id, device)
      log.info(`Discovered device: ${device.name} at ${device.url}`)
      window.webContents.send('discovery:device-found', device)
    }
  }

  try {
    // Phase 1: Try known hostnames (fast)
    log.info('Phase 1: Trying known hostnames...')
    const hostnameDevices = await tryKnownHostnames()
    for (const device of hostnameDevices) {
      onDeviceFound(device)
    }

    // Phase 2: Scan local networks (slower)
    if (!scanAbortController.signal.aborted) {
      log.info('Phase 2: Scanning local network...')
      const networks = getLocalNetworks()
      
      for (const network of networks) {
        if (scanAbortController.signal.aborted) break
        log.info(`Scanning subnet ${network.subnet}.x...`)
        window.webContents.send('discovery:scanning-subnet', network.subnet)
        await scanSubnet(network.subnet, onDeviceFound, scanAbortController.signal)
      }
    }

  } catch (error) {
    log.error('Discovery error:', error)
  } finally {
    isScanning = false
    scanAbortController = null
    log.info(`Discovery complete. Found ${foundDevices.size} device(s)`)
    window.webContents.send('discovery:complete', Array.from(foundDevices.values()))
  }
}

/**
 * Stop ongoing discovery
 */
function stopDiscovery(): void {
  if (scanAbortController) {
    scanAbortController.abort()
    log.info('Discovery stopped by user')
  }
  isScanning = false
}

/**
 * Quick probe a specific URL (for manual entry validation)
 */
async function probeSpecificUrl(url: string): Promise<DiscoveredDevice | null> {
  try {
    const urlObj = new URL(url)
    const result = await probeUrl(`${url}/api/v1/health`, 5000)
    
    if (result) {
      return {
        id: `preke-${urlObj.host.replace(/[.:]/g, '-')}`,
        name: result.device_name || 'Preke Device',
        host: urlObj.hostname,
        port: parseInt(urlObj.port) || (urlObj.protocol === 'https:' ? 443 : 80),
        url: url.replace(/\/$/, ''),
        source: 'probe',
        status: result.status,
        version: result.api_version
      }
    }
  } catch (error) {
    log.debug(`Probe failed for ${url}:`, error)
  }
  
  return null
}

/**
 * Setup IPC handlers for discovery
 */
export function setupDiscoveryHandlers(getWindow: () => BrowserWindow | null): void {
  // Start scanning
  ipcMain.on('discovery:start', () => {
    const window = getWindow()
    if (window) {
      startDiscovery(window)
    }
  })

  // Stop scanning
  ipcMain.on('discovery:stop', () => {
    stopDiscovery()
  })

  // Probe specific URL
  ipcMain.handle('discovery:probe', async (_event, url: string) => {
    return probeSpecificUrl(url)
  })

  // Check if scanning
  ipcMain.handle('discovery:is-scanning', () => {
    return isScanning
  })

  log.info('Discovery IPC handlers registered')
}

