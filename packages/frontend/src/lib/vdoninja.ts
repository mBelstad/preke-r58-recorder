/**
 * VDO.ninja URL builder and configuration
 * 
 * VDO.ninja host is configurable via device configuration or environment variable.
 * Returns null if not configured (disables VDO.ninja features).
 */

// Cached VDO.ninja host from device config
let cachedVdoHost: string | null = null

/**
 * Get VDO.ninja host from device configuration or environment variable
 * Returns null if not configured
 */
export async function getVdoHost(): Promise<string | null> {
  // If already cached, return it
  if (cachedVdoHost) {
    return cachedVdoHost
  }

  // Check environment variable first
  const envHost = import.meta.env.VITE_VDO_HOST || import.meta.env.VDO_HOST
  if (envHost) {
    cachedVdoHost = envHost
    return cachedVdoHost
  }

  // Try to get from device configuration
  try {
    const { getDeviceUrl } = await import('./api')
    const deviceUrl = getDeviceUrl()
    if (deviceUrl) {
      const controller = new AbortController()
      const timeout = setTimeout(() => controller.abort(), 3000)
      
      const response = await fetch(`${deviceUrl}/api/config`, {
        signal: controller.signal,
        mode: 'cors',
        cache: 'no-cache'
      })
      clearTimeout(timeout)
      
      if (response.ok) {
        const config = await response.json()
        if (config.vdo_host || config.vdoninja_host) {
          cachedVdoHost = config.vdo_host || config.vdoninja_host
          return cachedVdoHost
        }
      }
    }
  } catch (e) {
    // Device doesn't support /api/config or not reachable
    console.log('[VDO.ninja] Device does not provide VDO.ninja host configuration')
  }
  
  // Default fallback to r58-vdo.itagenten.no
  const defaultHost = 'r58-vdo.itagenten.no'
  cachedVdoHost = defaultHost
  console.log(`[VDO.ninja] Using default host: ${defaultHost}`)
  return defaultHost
}

// Protocol for VDO.ninja URLs
export function getVdoProtocol(): string {
  return 'https'
}

export const VDO_ROOM = 'studio'

// Director password for VDO.ninja room - ensures this app is the authenticated director
// This allows the mixer to control the room even if other sessions exist
export const VDO_DIRECTOR_PASSWORD = 'preke-r58-2024'

/**
 * VDO.ninja URL parameter profiles for each embed scenario
 * 
 * NOTE: We do NOT use &mediamtx= parameter here because:
 * 1. It causes VDO.ninja to connect directly to MediaMTX:8889 which fails through nginx proxy
 * 2. CameraPushBar handles camera bridging via &whepplay= which works correctly
 * 3. The cameras appear as P2P room guests, which is more reliable through tunnels
 */
export const embedProfiles = {
  // DIRECTOR VIEW - Full control panel for operator
  // Camera sources are pushed via CameraPushBar using &whepplay= parameter
  // Uses password to authenticate as the room director
  director: {
    base: '/',
    params: {
      director: VDO_ROOM,
      password: VDO_DIRECTOR_PASSWORD,  // Authenticate as director
      hidesolo: true,
      hideheader: true,
      cleanoutput: true,
      darkmode: true,
      nologo: true,
      api: true,  // Enable postMessage API
    }
  },
  
  // MIXER VIEW - For embedded control without visible UI
  // Camera sources are pushed via CameraPushBar using &whepplay= parameter
  // Uses password to authenticate as the room director
  mixer: {
    base: '/',
    params: {
      director: VDO_ROOM,
      password: VDO_DIRECTOR_PASSWORD,  // Authenticate as director
      hidesolo: true,
      hideheader: true,
      cleanoutput: true,
      darkmode: true,
      nologo: true,
      api: true,
    }
  },
  
  // PREVIEW VIEW - For PVW monitor (hidden, receives scene output)
  preview: {
    base: '/',
    params: {
      scene: true,
      room: VDO_ROOM,
      cover: true,
      cleanoutput: true,
      hideheader: true,
      nologo: true,
      muted: true,  // Muted for preview
    }
  },
  
  // PROGRAM VIEW - For PGM monitor (live output)
  program: {
    base: '/',
    params: {
      scene: true,
      room: VDO_ROOM,
      cover: true,
      cleanoutput: true,
      hideheader: true,
      nologo: true,
      quality: 2,
    }
  },
  
  // SCENE OUTPUT - Clean program output for OBS/streaming
  scene: {
    base: '/',
    params: {
      scene: true,
      room: VDO_ROOM,
      cover: true,
      fadein: 500,
      animated: true,
      quality: 2,
      cleanoutput: true,
      hideheader: true,
      nologo: true,
    }
  },
  
  // MULTIVIEW - Grid of all sources
  multiview: {
    base: '/',
    params: {
      room: VDO_ROOM,
      scene: true,
      grid: true,
      autoadd: '*',
      cleanoutput: true,
      hideheader: true,
      nologo: true,
    }
  },
  
  // WHEP SHARE - Add R58 camera to VDO.ninja room via WHEP
  cameraContribution: {
    base: '/',
    params: {
      room: VDO_ROOM,
      videodevice: 0,
      audiodevice: 0,
      autostart: true,
      noaudio: false,
    }
  },
  
  // GUEST INVITE - Link for remote guests to join
  guestInvite: {
    base: '/',
    params: {
      room: VDO_ROOM,
      webcam: true,
      mic: true,
      quality: 1,
      effects: true,
    }
  },
  
  // SOLO VIEW - View single source fullscreen
  soloView: {
    base: '/',
    params: {
      room: VDO_ROOM,
      cover: true,
      cleanoutput: true,
    }
  },
  
  // PROGRAM OUTPUT - Push mixed output via WHIP to MediaMTX
  programOutput: {
    base: '/',
    params: {
      scene: true,
      room: VDO_ROOM,
      cover: true,
      quality: 2,
      cleanoutput: true,
      hideheader: true,
      nologo: true,
      autostart: true,
    }
  },
}

/**
 * Get base64-encoded CSS for VDO.ninja minimal theme
 * 
 * Uses inline base64 CSS via &b64css= parameter for cross-origin compatibility.
 * Per docs/MIXER_STYLING_ATTEMPT.md: "Minimal Styling Only" approach - colors only, no layout changes.
 */
export function getVdoCssUrl(): string {
  // Minimal CSS - colors only, no layout changes (per docs/MIXER_STYLING_ATTEMPT.md)
  const css = `
/* R58 VDO.ninja Theme - Colors Only */
:root {
  --r58-bg: #0f172a;
  --r58-bg2: #1e293b;
  --r58-bg3: #334155;
  --r58-text: #f8fafc;
  --r58-muted: #94a3b8;
  --r58-blue: #3b82f6;
  --r58-green: #22c55e;
  --r58-gold: #f59e0b;
  --r58-border: #475569;
}
body { background: var(--r58-bg); color: var(--r58-text); }
#mainmenu, .controlButtons, #guestFeatures { background: var(--r58-bg2); }
button, .button { background: var(--r58-bg3); color: var(--r58-text); border-color: var(--r58-border); }
button:hover { background: var(--r58-blue); }
input, select, textarea { background: var(--r58-bg3); color: var(--r58-text); border-color: var(--r58-border); }
a { color: var(--r58-blue); }
.vidcon { background: var(--r58-bg2); border-color: var(--r58-border); border-radius: 8px; }
video { border-radius: 6px; }
`
  
  // Return empty in Electron (file:// origin)
  if (typeof window !== 'undefined' && window.location?.origin?.startsWith('file://')) {
    return ''
  }
  
  // Base64 encode for &b64css= parameter
  try {
    return 'b64:' + btoa(unescape(encodeURIComponent(css)))
  } catch {
    return ''
  }
}

/**
 * Build VDO.ninja theming parameters using official design parameters
 * 
 * Official VDO.ninja design parameters:
 * - &darkmode - Enable built-in dark theme
 * - &nologo - Hide VDO.ninja logo
 * - &hideheader - Hide top header bar
 * - &cleanoutput - Minimal UI for clean output
 * - &css=<url> - External CSS injection
 * - &bgimage=<url> - Custom background image
 * - &cover - Video cover mode (fill container)
 * - &style=<n> - Built-in style preset (0-9)
 * 
 * @param options - Theming options
 * @returns Record of URL parameters for theming
 */
export function buildVdoThemeParams(options: {
  darkMode?: boolean
  hideBranding?: boolean
  cleanOutput?: boolean
  customCss?: boolean
  coverMode?: boolean
  style?: number
} = {}): Record<string, string | boolean> {
  const params: Record<string, string | boolean> = {}
  
  // Dark mode (matches R58 dark theme)
  if (options.darkMode !== false) {
    params.darkmode = true
  }
  
  // Hide VDO.ninja branding for seamless integration
  if (options.hideBranding !== false) {
    params.nologo = true
    params.hideheader = true
  }
  
  // Clean output mode (minimal UI)
  if (options.cleanOutput) {
    params.cleanoutput = true
  }
  
  // Custom CSS injection
  if (options.customCss !== false) {
    const cssUrl = getVdoCssUrl()
    if (cssUrl) {
      params.css = cssUrl
    }
  }
  
  // Cover mode for proper video scaling
  if (options.coverMode) {
    params.cover = true
  }
  
  // Built-in style preset
  if (typeof options.style === 'number') {
    params.style = options.style.toString()
  }
  
  return params
}

/**
 * Apply theme parameters to existing URL params
 * 
 * @param profile - VDO.ninja profile
 * @param additionalParams - Additional URL parameters
 * @returns Combined parameters with theming
 */
export function applyVdoTheme(
  profile: keyof typeof embedProfiles,
  additionalParams: Record<string, string> = {}
): Record<string, string> {
  const themeParams = buildVdoThemeParams({
    darkMode: true,
    hideBranding: true,
    cleanOutput: profile === 'scene' || profile === 'program' || profile === 'preview',
    coverMode: profile === 'scene' || profile === 'program',
  })
  
  // Convert boolean params to strings
  const stringParams: Record<string, string> = {}
  for (const [key, value] of Object.entries(themeParams)) {
    if (typeof value === 'boolean') {
      if (value) {
        stringParams[key] = ''
      }
    } else {
      stringParams[key] = value
    }
  }
  
  // Merge with additional params (additional params take precedence)
  return { ...stringParams, ...additionalParams }
}

/**
 * Build a VDO.ninja URL from a profile and variable substitutions
 * Returns null if VDO.ninja is not configured
 */
export async function buildVdoUrl(
  profile: keyof typeof embedProfiles,
  vars: Record<string, string> = {}
): Promise<string | null> {
  const VDO_HOST = await getVdoHost()
  if (!VDO_HOST) {
    return null
  }
  const VDO_PROTOCOL = getVdoProtocol()
  const config = embedProfiles[profile]
  const basePath = config.base || '/'
  const url = new URL(`${VDO_PROTOCOL}://${VDO_HOST}${basePath}`)
  
  const effectiveVars = { ...vars }
  
  // Add custom CSS for reskin if available
  const cssUrl = getVdoCssUrl()
  if (cssUrl) {
    url.searchParams.set('css', cssUrl)
  }
  
  // Add profile-specific params
  for (const [key, value] of Object.entries(config.params)) {
    if (typeof value === 'boolean') {
      if (value) {
        url.searchParams.set(key, '')
      }
    } else if (typeof value === 'number') {
      url.searchParams.set(key, value.toString())
    } else if (typeof value === 'string') {
      // Check for variable substitution
      let finalValue = value
      for (const [varName, varValue] of Object.entries(effectiveVars)) {
        finalValue = finalValue.replace(`{${varName}}`, varValue)
      }
      // Only add if no unsubstituted variables remain
      if (!finalValue.includes('{')) {
        url.searchParams.set(key, finalValue)
      }
    }
  }
  
  // Add any additional vars as params
  if (effectiveVars.push_id) {
    url.searchParams.set('push', effectiveVars.push_id)
  }
  if (effectiveVars.view_id) {
    url.searchParams.set('view', effectiveVars.view_id)
  }
  if (effectiveVars.source_ids) {
    url.searchParams.set('autoadd', effectiveVars.source_ids)
  }
  if (effectiveVars.whep_url) {
    url.searchParams.set('whepshare', encodeURIComponent(effectiveVars.whep_url))
  }
  if (effectiveVars.label) {
    url.searchParams.set('label', effectiveVars.label)
  }
  
  return url.toString()
}

/**
 * Build a guest invite URL
 * Returns null if VDO.ninja is not configured
 */
export async function buildGuestInviteUrl(guestName: string, guestId?: string): Promise<string | null> {
  const VDO_HOST = await getVdoHost()
  if (!VDO_HOST) {
    return null
  }
  const VDO_PROTOCOL = getVdoProtocol()
  const url = new URL(`${VDO_PROTOCOL}://${VDO_HOST}/`)
  
  url.searchParams.set('room', VDO_ROOM)
  url.searchParams.set('push', guestId || guestName.toLowerCase().replace(/\s+/g, '-'))
  url.searchParams.set('label', guestName)
  url.searchParams.set('webcam', '')
  url.searchParams.set('mic', '')
  url.searchParams.set('quality', '1')
  
  return url.toString()
}

/**
 * Build a camera contribution URL (WHEP bridge to VDO.ninja room)
 * 
 * Uses &whepplay= to pull the WHEP stream and &push= + &room= to share it
 * to the VDO.ninja room. 
 * 
 * IMPORTANT: The &mediamtx= parameter is added so that the camera guest
 * uses MediaMTX SFU for transport instead of P2P WebRTC. This is required
 * for working through FRP tunnels where P2P doesn't work.
 */
export async function buildCameraContributionUrl(
  cameraId: string,
  whepUrl: string,
  label: string
): Promise<string | null> {
  const VDO_HOST = await getVdoHost()
  if (!VDO_HOST) {
    return null
  }
  const VDO_PROTOCOL = getVdoProtocol()
  const url = new URL(`${VDO_PROTOCOL}://${VDO_HOST}/`)
  
  // Use whepplay (not whepshare) - this pulls the WHEP stream from MediaMTX
  url.searchParams.set('whepplay', whepUrl)
  url.searchParams.set('push', cameraId)
  url.searchParams.set('room', VDO_ROOM)
  url.searchParams.set('password', VDO_DIRECTOR_PASSWORD)  // Required to join the director's room
  url.searchParams.set('label', label)
  url.searchParams.set('autostart', 'true')
  url.searchParams.set('stereo', '2')  // Audio channels
  url.searchParams.set('whepwait', '2000')  // Wait time for WHEP connection
  
  // CRITICAL: Use MediaMTX SFU instead of P2P for sharing to the room
  // Without this, the camera's video won't reach the director through FRP tunnels
  const mediamtxHost = await getMediaMtxHost()
  if (mediamtxHost) {
    url.searchParams.set('mediamtx', mediamtxHost)
  }
  
  // Add custom CSS only if available
  const cssUrl = getVdoCssUrl()
  if (cssUrl) {
    url.searchParams.set('css', cssUrl)
  }
  
  return url.toString()
}

/**
 * Build a program output URL (WHIP push to MediaMTX)
 * 
 * Uses VDO.ninja's scene output to capture the mixed program
 * and push it via WHIP to MediaMTX using the &whipout parameter.
 * 
 * Note: &whip= is for VIEWING a WHIP stream published TO VDO.ninja
 *       &whipout= is for PUBLISHING FROM VDO.ninja TO an external WHIP server
 */
export async function buildProgramOutputUrl(whipUrl: string): Promise<string | null> {
  const VDO_HOST = await getVdoHost()
  if (!VDO_HOST) {
    return null
  }
  const VDO_PROTOCOL = getVdoProtocol()
  const url = new URL(`${VDO_PROTOCOL}://${VDO_HOST}/`)
  
  // Scene output params
  url.searchParams.set('scene', '')
  url.searchParams.set('room', VDO_ROOM)
  url.searchParams.set('cover', '')
  url.searchParams.set('quality', '0')  // 0=auto matches canvas resolution (720p)
  url.searchParams.set('width', '1280')  // Force 720p output
  url.searchParams.set('height', '720')
  url.searchParams.set('cleanoutput', '')
  url.searchParams.set('hideheader', '')
  url.searchParams.set('nologo', '')
  
  // WHIP OUTPUT - push scene to external MediaMTX WHIP endpoint
  // Uses &whipout (not &whip) to publish FROM VDO.ninja TO MediaMTX
  url.searchParams.set('whipout', whipUrl)
  
  // Auto-start without user interaction
  url.searchParams.set('autostart', '')
  url.searchParams.set('videodevice', '0')
  url.searchParams.set('audiodevice', '0')
  
  // Custom CSS
  url.searchParams.set('css', getVdoCssUrl())
  
  return url.toString()
}

/**
 * Build a mixer URL with MediaMTX integration
 * 
 * Uses the standard mixer.html which has all dependencies bundled.
 * The &mediamtx= parameter tells VDO.ninja to use MediaMTX for
 * WHEP/WHIP transport instead of P2P WebRTC, which is required
 * for working through FRP tunnels.
 */
/**
 * Get VDO.ninja API key from config
 * Falls back to default if not configured
 */
async function getVdoApiKey(): Promise<string | null> {
  try {
    const { getDeviceUrl } = await import('./api')
    const deviceUrl = getDeviceUrl()
    if (deviceUrl) {
      const controller = new AbortController()
      const timeout = setTimeout(() => controller.abort(), 3000)
      
      const response = await fetch(`${deviceUrl}/api/config`, {
        signal: controller.signal,
        mode: 'cors',
        cache: 'no-cache'
      })
      clearTimeout(timeout)
      
      if (response.ok) {
        const config = await response.json()
        if (config.vdo_ninja?.api_key) {
          return config.vdo_ninja.api_key
        }
      }
    }
  } catch (e) {
    // Device doesn't support /api/config or not reachable
    console.log('[VDO.ninja] Could not fetch API key from config')
  }
  
  // Default fallback (matches config.yml default)
  return 'preke-r58-2024-secure-key'
}

export async function buildMixerUrl(options: {
  mediamtxHost?: string
  room?: string
} = {}): Promise<string | null> {
  const VDO_HOST = await getVdoHost()
  if (!VDO_HOST) {
    return null
  }
  const VDO_PROTOCOL = getVdoProtocol()
  
  // Use director view instead of mixer.html
  // mixer.html has JavaScript issues ("digest" error) that prevent cameras from showing
  // Director view works correctly and shows all connected cameras
  const url = new URL(`${VDO_PROTOCOL}://${VDO_HOST}/`)
  
  // Room name - director mode
  const room = options.room || VDO_ROOM
  url.searchParams.set('director', room)
  
  // Room password for authentication
  url.searchParams.set('password', VDO_DIRECTOR_PASSWORD)
  
  // API key for HTTP API control (Companion/Stream Deck integration)
  const apiKey = await getVdoApiKey()
  if (apiKey) {
    url.searchParams.set('api', apiKey)
  }
  
  // UI preferences for cleaner look
  url.searchParams.set('cleandirector', '')
  url.searchParams.set('showlabels', '')
  url.searchParams.set('darkmode', '')
  
  // MediaMTX integration - enables WHEP/WHIP transport instead of P2P
  // This is critical for working through FRP tunnels
  if (options.mediamtxHost) {
    url.searchParams.set('mediamtx', options.mediamtxHost)
  }
  
  // Custom CSS for R58 reskin
  url.searchParams.set('css', getVdoCssUrl())
  
  return url.toString()
}

/**
 * Get the MediaMTX host for VDO.ninja's &mediamtx= parameter
 * 
 * This host is used by VDO.ninja for MediaMTX SFU mode, which requires HTTPS.
 * Gets from device configuration or constructs from FRP URL.
 */
export async function getMediaMtxHost(): Promise<string | null> {
  // Try to get from device config
  try {
    const { getDeviceUrl, getFrpUrl } = await import('./api')
    const frpUrl = await getFrpUrl()
    if (frpUrl) {
      try {
        const url = new URL(frpUrl)
        // Use same-domain architecture: app.itagenten.no for all services
        // The WHEP/WHIP endpoints are proxied through app.itagenten.no
        // VDO.ninja's &mediamtx= parameter expects just the hostname (no protocol)
        if (url.hostname.includes('itagenten.no')) {
          return 'app.itagenten.no'
        }
        // Fallback for other domains (legacy)
        const mediamtxHost = url.hostname.replace('api', 'mediamtx')
        return mediamtxHost
      } catch (e) {
        console.warn('[VDO.ninja] Failed to construct MediaMTX host from FRP URL')
      }
    }
  } catch (e) {
    // Not available
  }
  return null
}

/**
 * Get the public R58 API host for external services (like VDO.ninja)
 * This is the URL that external services can use to reach the R58 device
 * 
 * Gets from device configuration (FRP URL)
 */
export async function getPublicR58Host(): Promise<string | null> {
  const { getFrpUrl } = await import('./api')
  return await getFrpUrl()
}

/**
 * Build a WHEP URL for a camera that VDO.ninja can access
 * 
 * In Electron: We enable allowRunningInsecureContent, so VDO.ninja can
 * load HTTP content (direct connection) for much better performance.
 * 
 * In Browser: Must use FRP-proxied HTTPS URL due to mixed content security.
 * 
 * On Pi Kiosk: Uses nginx proxy path (same as buildWhepUrl in whepConnectionManager)
 */
export async function getPublicWhepUrl(cameraId: string): Promise<string | null> {
  const { getDeviceUrl, getFrpUrl } = await import('./api')
  
  // Check if running on Pi kiosk (nginx proxy setup)
  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname
    const port = window.location.port
    const protocol = window.location.protocol
    
    const isPiKiosk = (hostname === 'localhost' || 
                       hostname === '127.0.0.1' || 
                       hostname === '192.168.1.81' || // Pi local IP
                       hostname === '192.168.68.53' || // Pi alternate local IP
                       hostname === '100.107.248.29') && // Pi Tailscale IP (when available)
                       (!port || port === '80' || port === '')
    
    if (isPiKiosk) {
      // Use nginx proxy path (nginx proxies /cam*/whep to R58)
      console.log(`[VDO.ninja] Using nginx proxy WHEP for ${cameraId} (hostname: ${hostname})`)
      return `${protocol}//${hostname}${port ? ':' + port : ''}/${cameraId}/whep`
    }
  }
  
  // In Electron, use direct connection when available (mixed content allowed)
  if (typeof window !== 'undefined' && (window as any).electronAPI) {
    const deviceUrl = getDeviceUrl()
    if (deviceUrl) {
      try {
        const url = new URL(deviceUrl)
        // Direct connection - bypasses FRP tunnel for much better performance!
        console.log(`[VDO.ninja] Using direct WHEP for ${cameraId}`)
        return `http://${url.hostname}:8889/${cameraId}/whep`
      } catch (e) {
        // Invalid URL, fall through to FRP
      }
    }
  }
  
  // Browser fallback: Use FRP-proxied MediaMTX (HTTPS required)
  const frpUrl = await getFrpUrl()
  if (frpUrl) {
    try {
      const url = new URL(frpUrl)
      // Use same-domain architecture: app.itagenten.no for all services
      if (url.hostname.includes('itagenten.no')) {
        return `https://app.itagenten.no/${cameraId}/whep`
      }
      // Fallback for other domains (legacy)
      const mediamtxHost = url.hostname.replace('api', 'mediamtx')
      return `https://${mediamtxHost}/${cameraId}/whep`
    } catch (e) {
      console.warn('[VDO.ninja] Failed to construct MediaMTX WHEP URL')
    }
  }
  
  return null
}

/**
 * Build a VDO.ninja scene output URL for a specific scene number
 * Used for PVW/PGM monitors - displays what a specific VDO.ninja scene shows
 * 
 * The director uses postMessage API (addScene command) to add sources to scenes.
 * This scene viewer URL then displays the sources that have been added to the scene.
 * 
 * VDO.ninja scene URL format:
 * - &scene (no value) - shows scene 1 (the default/program scene)
 * - &scene=1 - explicitly shows scene 1
 * - &scene=2 - shows scene 2, etc.
 * 
 * @param sceneNumber - VDO.ninja scene number (1-8, or 0 for default)
 * @param options - Additional options
 * @param options.muted - Mute audio (default: false, use true for preview)
 * @param options.quality - Video quality 0-2 (default: 2 for program, 1 for preview)
 */
export async function buildSceneOutputUrl(
  sceneNumber: number,
  options: {
    muted?: boolean
    quality?: number
    room?: string
  } = {}
): Promise<string | null> {
  const VDO_HOST = await getVdoHost()
  if (!VDO_HOST) {
    return null
  }
  const VDO_PROTOCOL = getVdoProtocol()
  const url = new URL(`${VDO_PROTOCOL}://${VDO_HOST}/`)
  
  // Use &scene for OBS-style output - shows sources added via director API addToScene command
  // Scene 1 = program output, Scene 2 = preview, etc.
  // The director iframe uses addToScene API to populate scenes
  // &scene (no value) or &scene=0 auto-adds all room guests to the scene
  if (sceneNumber === 0) {
    url.searchParams.set('scene', '')  // Empty value auto-adds all guests
  } else {
    url.searchParams.set('scene', sceneNumber.toString())
  }
  url.searchParams.set('room', options.room || VDO_ROOM)
  url.searchParams.set('password', VDO_DIRECTOR_PASSWORD)  // Required for room access
  
  // Display options for clean output
  url.searchParams.set('cover', '')
  url.searchParams.set('cleanoutput', '')
  url.searchParams.set('hideheader', '')
  url.searchParams.set('nologo', '')
  
  // Quality: 0=low, 1=medium, 2=high
  url.searchParams.set('quality', (options.quality ?? 2).toString())
  
  // Audio
  if (options.muted) {
    url.searchParams.set('muted', '')
  }
  
  // Custom CSS
  const cssUrl = getVdoCssUrl()
  if (cssUrl) {
    url.searchParams.set('css', cssUrl)
  }
  
  return url.toString()
}

/**
 * Build a VDO.ninja preview monitor URL (PVW)
 * Muted, lower quality for preview purposes
 */
export async function buildPreviewUrl(sceneNumber: number, room?: string): Promise<string | null> {
  return buildSceneOutputUrl(sceneNumber, { muted: true, quality: 1, room })
}

/**
 * Build a VDO.ninja program monitor URL (PGM)
 * Full quality, audio enabled for live output
 * Uses scene=1 which receives sources added via addToScene director command
 */
export async function buildProgramUrl(sceneNumber: number = 1, room?: string): Promise<string | null> {
  return buildSceneOutputUrl(sceneNumber, { muted: false, quality: 2, room })
}

/**
 * Open program output in a popup window for local viewing
 * Opens a new browser window with the program feed
 * 
 * @param sceneNumber - VDO.ninja scene number (default: 1 for program)
 * @returns Window reference or null if popup blocked or VDO.ninja not configured
 */
export async function openProgramPopup(sceneNumber: number = 1): Promise<Window | null> {
  const url = await buildProgramUrl(sceneNumber)
  if (!url) {
    console.warn('[VDO.ninja] Cannot open popup - VDO.ninja not configured')
    return null
  }
  const windowFeatures = 'width=1280,height=720,menubar=no,toolbar=no,location=no,status=no'
  const popup = window.open(url, 'R58_Program_Output', windowFeatures)
  
  if (!popup) {
    console.warn('[VDO.ninja] Popup blocked - please allow popups for this site')
  }
  
  return popup
}

