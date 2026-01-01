/**
 * VDO.ninja URL builder and configuration
 * 
 * Uses self-hosted VDO.ninja instance at r58-vdo.itagenten.no
 */

// VDO.ninja host - self-hosted instance with HTTPS
export function getVdoHost(): string {
  return 'r58-vdo.itagenten.no'
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
 * Get the CSS URL for VDO.ninja reskin
 */
export function getVdoCssUrl(): string {
  // In Electron, window.location.origin is file:// which won't work
  // Use the VDO.ninja host for CSS or skip if in Electron
  const origin = window.location.origin
  if (origin.startsWith('file://')) {
    // Skip custom CSS in Electron - VDO.ninja will use its default theme
    return ''
  }
  // Use same origin as the page (works for web browser access)
  return `${origin}/static/css/vdo-theme.css`
}

/**
 * Build a VDO.ninja URL from a profile and variable substitutions
 */
export function buildVdoUrl(
  profile: keyof typeof embedProfiles,
  vars: Record<string, string> = {}
): string {
  const VDO_HOST = getVdoHost()
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
 */
export function buildGuestInviteUrl(guestName: string, guestId?: string): string {
  const VDO_HOST = getVdoHost()
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
 * to the VDO.ninja room. This is the approach used by camera-bridge.html
 * which is known to work through FRP tunnels.
 */
export function buildCameraContributionUrl(
  cameraId: string,
  whepUrl: string,
  label: string
): string {
  const VDO_HOST = getVdoHost()
  const VDO_PROTOCOL = getVdoProtocol()
  const url = new URL(`${VDO_PROTOCOL}://${VDO_HOST}/`)
  
  // Use whepplay (not whepshare) - this is the working approach from camera-bridge.html
  url.searchParams.set('whepplay', whepUrl)
  url.searchParams.set('push', cameraId)
  url.searchParams.set('room', VDO_ROOM)
  url.searchParams.set('label', label)
  url.searchParams.set('autostart', 'true')
  url.searchParams.set('stereo', '2')  // Audio channels
  url.searchParams.set('whepwait', '2000')  // Wait time for WHEP connection
  
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
export function buildProgramOutputUrl(whipUrl: string): string {
  const VDO_HOST = getVdoHost()
  const VDO_PROTOCOL = getVdoProtocol()
  const url = new URL(`${VDO_PROTOCOL}://${VDO_HOST}/`)
  
  // Scene output params
  url.searchParams.set('scene', '')
  url.searchParams.set('room', VDO_ROOM)
  url.searchParams.set('cover', '')
  url.searchParams.set('quality', '2')
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
 * Uses the alpha mixer's built-in MediaMTX support for WHEP input
 * and optional WHIP output via Scene Output Options.
 */
export function buildMixerUrl(options: {
  mediamtxHost?: string
  room?: string
} = {}): string {
  const VDO_HOST = getVdoHost()
  const VDO_PROTOCOL = getVdoProtocol()
  const url = new URL(`${VDO_PROTOCOL}://${VDO_HOST}/mixer.html`)
  
  // Room name
  const room = options.room || VDO_ROOM
  url.searchParams.set('room', room)
  
  // MediaMTX integration - enables WHEP input from MediaMTX
  if (options.mediamtxHost) {
    url.searchParams.set('mediamtx', options.mediamtxHost)
  }
  
  // Custom CSS for R58 reskin
  url.searchParams.set('css', getVdoCssUrl())
  
  return url.toString()
}

/**
 * Get the default MediaMTX host for the R58 system
 */
export function getMediaMtxHost(): string {
  // Use the public MediaMTX endpoint
  return 'r58-mediamtx.itagenten.no'
}

/**
 * Get the public R58 API host for external services (like VDO.ninja)
 * This is the URL that external services can use to reach the R58 device
 */
export function getPublicR58Host(): string {
  return 'https://r58-api.itagenten.no'
}

/**
 * Build a public WHEP URL for a camera
 * VDO.ninja needs this public URL to fetch the stream
 */
export function getPublicWhepUrl(cameraId: string): string {
  return `${getPublicR58Host()}/${cameraId}/whep`
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
export function buildSceneOutputUrl(
  sceneNumber: number,
  options: {
    muted?: boolean
    quality?: number
    room?: string
  } = {}
): string {
  const VDO_HOST = getVdoHost()
  const VDO_PROTOCOL = getVdoProtocol()
  const url = new URL(`${VDO_PROTOCOL}://${VDO_HOST}/`)
  
  // VDO.ninja scene viewer - uses the scene number directly
  // - scene=0: auto-adds all videos (recommended for PGM)
  // - scene=1+: empty scene, videos added manually by director
  // - scene (empty): defaults to scene 1
  if (sceneNumber === 0) {
    // Scene 0: auto-add all room guests (best for program output)
    url.searchParams.set('scene', '0')
  } else if (sceneNumber === 1) {
    // Scene 1: can use empty value (VDO.ninja default)
    url.searchParams.set('scene', '')
  } else {
    // Scene 2-8 need explicit number
    url.searchParams.set('scene', sceneNumber.toString())
  }
  
  url.searchParams.set('room', options.room || VDO_ROOM)
  url.searchParams.set('password', VDO_DIRECTOR_PASSWORD)  // Required for scene access
  
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
export function buildPreviewUrl(sceneNumber: number, room?: string): string {
  return buildSceneOutputUrl(sceneNumber, { muted: true, quality: 1, room })
}

/**
 * Build a VDO.ninja program monitor URL (PGM)
 * Full quality, audio enabled for live output
 * Uses scene=0 by default which auto-adds all room guests
 */
export function buildProgramUrl(sceneNumber: number = 0, room?: string): string {
  return buildSceneOutputUrl(sceneNumber, { muted: false, quality: 2, room })
}

