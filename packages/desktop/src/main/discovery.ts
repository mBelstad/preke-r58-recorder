/**
 * Device Discovery - Find R58/Preke devices on local network
 * 
 * Uses multiple methods:
 * 1. Tailscale (preferred) - P2P mesh network for reliable connectivity
 * 2. mDNS/Bonjour (if available) - looks for _http._tcp services with preke/r58 names
 * 3. HTTP probing - scans local subnet for R58 API endpoints
 * 4. Known hostnames - tries common names like r58.local, preke.local
 */

import { ipcMain, BrowserWindow } from 'electron'
import log from 'electron-log/main'
import * as http from 'http'
import * as https from 'https'
import * as dns from 'dns'
import * as os from 'os'
import { 
  getTailscaleStatus, 
  findR58DevicesOnTailscale, 
  getR58TailscaleUrl,
  TailscaleDevice,
  TailscaleStatus
} from './tailscale'
import { deviceStore } from './deviceStore'

export interface DiscoveredDevice {
  id: string
  name: string
  host: string
  port: number
  url: string
  /** Stable device ID from capabilities (if available) */
  deviceId?: string
  /** Optional fallback URL (e.g. Tailscale) */
  fallbackUrl?: string
  source: 'mdns' | 'probe' | 'hostname' | 'tailscale'
  status?: string
  version?: string
  /** Tailscale-specific: whether connection is P2P or via DERP relay */
  isP2P?: boolean
  /** Tailscale-specific: latency in ms */
  latencyMs?: number
  /** Tailscale IP if discovered via Tailscale */
  tailscaleIp?: string
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
 * Discover R58 devices via Tailscale (P2P preferred)
 */
async function discoverViaTailscale(): Promise<DiscoveredDevice[]> {
  try {
    const tailscaleDevices = await findR58DevicesOnTailscale()
    const devices: DiscoveredDevice[] = []

    for (const tsDevice of tailscaleDevices) {
      const { url, isP2P, latencyMs } = await getR58TailscaleUrl(tsDevice)
      const capability = await fetchCapabilities(url)
      
      devices.push({
        id: capability?.deviceId || `tailscale-${tsDevice.tailscaleIp.replace(/\./g, '-')}`,
        name: `${tsDevice.name} ${isP2P ? '(P2P)' : '(Relay)'}`,
        host: tsDevice.tailscaleIp,
        port: 8000,
        url,
        deviceId: capability?.deviceId,
        source: 'tailscale',
        status: 'healthy',
        version: tsDevice.os,
        isP2P,
        latencyMs,
        tailscaleIp: tsDevice.tailscaleIp,
      })
    }

    return devices
  } catch (error) {
    log.error('Tailscale discovery error:', error)
    return []
  }
}

/**
 * Try to resolve common R58 hostnames and known IPs via mDNS/DNS
 */
async function tryKnownHostnames(): Promise<DiscoveredDevice[]> {
  const hostnames = [
    'r58.local',
    'preke.local',
    'preke-r58.local',
    'recorder.local',
    'r58-api.local'
  ]

  // Known direct connection IPs (USB-C gadget, hotspot)
  const knownIPs = [
    '192.168.42.1',   // USB-C gadget mode (highest priority)
    '192.168.4.1',    // Wi-Fi hotspot mode
  ]

  const devices: DiscoveredDevice[] = []

  // First, try known direct connection IPs (fastest)
  for (const ip of knownIPs) {
    try {
      const device = await probeDevice(ip, 8000)
      if (device) {
        device.source = 'probe'
        if (ip === '192.168.42.1') {
          device.name = `${device.name} (USB-C)`
        } else if (ip === '192.168.4.1') {
          device.name = `${device.name} (Hotspot)`
        }
        devices.push(device)
        log.info(`Found device via direct connection: ${ip}`)
      }
    } catch (error) {
      // IP not reachable, continue
    }
  }

  // Then try mDNS/DNS hostnames
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
  timeout: number = 1200  // Reasonable timeout for reliable LAN discovery
): Promise<DiscoveredDevice | null> {
  // Only probe the primary port first for speed
  const urls = [
    `http://${ip}:${port}`,
  ]

  for (const baseUrl of urls) {
    try {
      const result = await probeUrl(`${baseUrl}/health`, timeout)
      if (result && result.status === 'healthy') {
        const capability = await fetchCapabilities(baseUrl)
        return {
          id: capability?.deviceId || `preke-${ip.replace(/\./g, '-')}`,
          name: capability?.deviceName || `Preke Device (${ip})`,
          host: ip,
          port: parseInt(baseUrl.split(':').pop() || '8000'),
          url: baseUrl,
          deviceId: capability?.deviceId,
          source: 'probe',
          status: result.status,
          version: capability?.platform || result.platform || 'unknown'
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

async function fetchCapabilities(baseUrl: string): Promise<{ deviceId?: string; deviceName?: string; platform?: string } | null> {
  try {
    const result = await probeUrl(`${baseUrl}/api/v1/capabilities`, 1200)
    if (!result) return null
    return {
      deviceId: result.device_id,
      deviceName: result.device_name,
      platform: result.platform
    }
  } catch {
    return null
  }
}

/**
 * Scan local subnet for devices
 * Uses reasonable batch sizes and timeouts for reliable LAN discovery
 */
async function scanSubnet(
  subnet: string,
  onDeviceFound: (device: DiscoveredDevice) => void,
  abortSignal?: AbortSignal
): Promise<void> {
  const batchSize = 25 // Smaller batches for more reliable scanning
  const port = 8000
  const timeout = 1200 // 1.2 seconds - gives slower devices time to respond

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

    // Small delay between batches to avoid overwhelming the network
    if (i + batchSize <= 254) {
      await new Promise(resolve => setTimeout(resolve, 100))
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
  const foundDevicesById = new Map<string, DiscoveredDevice>()

  const isLocalSource = (source: DiscoveredDevice['source']) => source !== 'tailscale'

  const onDeviceFound = (device: DiscoveredDevice) => {
    const key = device.deviceId || device.id
    const existing = foundDevicesById.get(key)
    if (!existing) {
      foundDevices.set(device.id, device)
      foundDevicesById.set(key, device)
      log.info(`Discovered device: ${device.name} at ${device.url}`)
      window.webContents.send('discovery:device-found', device)
      return
    }

    // Merge devices: prefer local connection, keep tailscale as fallback
    const incomingIsLocal = isLocalSource(device.source)
    const existingIsLocal = isLocalSource(existing.source)

    if (incomingIsLocal && !existingIsLocal) {
      const merged = {
        ...device,
        fallbackUrl: existing.url
      }
      foundDevices.delete(existing.id)
      foundDevices.set(merged.id, merged)
      foundDevicesById.set(key, merged)
      window.webContents.send('discovery:device-found', merged)
      return
    }

    if (!incomingIsLocal && existingIsLocal && !existing.fallbackUrl) {
      const merged = {
        ...existing,
        fallbackUrl: device.url
      }
      foundDevices.set(existing.id, merged)
      foundDevicesById.set(key, merged)
      window.webContents.send('discovery:device-found', merged)
      return
    }
  }

  try {
    // Phase 0: Tailscale (fastest, P2P preferred)
    log.info('Phase 0: Checking Tailscale for P2P devices...')
    window.webContents.send('discovery:phase', { phase: 'tailscale', message: 'Checking Tailscale...' })
    const tailscaleDevices = await discoverViaTailscale()
    for (const device of tailscaleDevices) {
      onDeviceFound(device)
      // Note: No auto-selection - let the user choose from the device setup page
    }
    if (tailscaleDevices.length > 0) {
      log.info(`Found ${tailscaleDevices.length} device(s) via Tailscale`)
    }

    // Phase 1: Try known hostnames (fast)
    log.info('Phase 1: Trying known hostnames...')
    window.webContents.send('discovery:phase', { phase: 'hostname', message: 'Trying known hostnames...' })
    const hostnameDevices = await tryKnownHostnames()
    for (const device of hostnameDevices) {
      onDeviceFound(device)
    }

    // Phase 2: Scan local networks (slower)
    if (!scanAbortController.signal.aborted) {
      log.info('Phase 2: Scanning local network...')
      window.webContents.send('discovery:phase', { phase: 'lan', message: 'Scanning local network...' })
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
    const result = await probeUrl(`${url}/health`, 5000)
    
    if (result && result.status === 'healthy') {
      return {
        id: `preke-${urlObj.host.replace(/[.:]/g, '-')}`,
        name: `Preke Device (${urlObj.hostname})`,
        host: urlObj.hostname,
        port: parseInt(urlObj.port) || (urlObj.protocol === 'https:' ? 443 : 8000),
        url: url.replace(/\/$/, ''),
        source: 'probe',
        status: result.status,
        version: result.platform || 'unknown'
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

  // Get Tailscale status
  ipcMain.handle('tailscale:status', async () => {
    return getTailscaleStatus()
  })

  // Find R58 devices on Tailscale
  ipcMain.handle('tailscale:find-devices', async () => {
    return findR58DevicesOnTailscale()
  })

  log.info('Discovery IPC handlers registered')
}

// Re-export Tailscale types for preload
export type { TailscaleStatus, TailscaleDevice }

