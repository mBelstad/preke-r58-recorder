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

/**
 * VDO.ninja URL parameter profiles for each embed scenario
 */
export const embedProfiles = {
  // DIRECTOR VIEW - Full control panel for operator (no video previews)
  director: {
    base: '/',
    params: {
      director: VDO_ROOM,
      hidesolo: true,
      hideheader: true,
      cleanoutput: true,
      darkmode: true,
      nologo: true,
    }
  },
  
  // MIXER VIEW - Director view with video previews enabled
  // Uses the main VDO.ninja director interface with previewmode
  // This gives us: controls + video previews for each source
  mixer: {
    base: '/',
    params: {
      director: VDO_ROOM,
      previewmode: true,      // Activates preview layout with video thumbnails
      hidesolo: true,
      darkmode: true,
      nologo: true,
      api: 'r58api',          // API key for postMessage control
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
  // Use same origin as the page (works for both local dev and production)
  return `${window.location.origin}/static/css/vdo-theme.css`
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
  
  // Always add custom CSS for reskin
  url.searchParams.set('css', getVdoCssUrl())
  
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
      for (const [varName, varValue] of Object.entries(vars)) {
        finalValue = finalValue.replace(`{${varName}}`, varValue)
      }
      // Only add if no unsubstituted variables remain
      if (!finalValue.includes('{')) {
        url.searchParams.set(key, finalValue)
      }
    }
  }
  
  // Add any additional vars as params
  if (vars.push_id) {
    url.searchParams.set('push', vars.push_id)
  }
  if (vars.view_id) {
    url.searchParams.set('view', vars.view_id)
  }
  if (vars.source_ids) {
    url.searchParams.set('autoadd', vars.source_ids)
  }
  if (vars.whep_url) {
    url.searchParams.set('whepshare', encodeURIComponent(vars.whep_url))
  }
  if (vars.label) {
    url.searchParams.set('label', vars.label)
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
 * Build a camera contribution URL (WHEP share)
 */
export function buildCameraContributionUrl(
  cameraId: string,
  whepUrl: string,
  label: string
): string {
  const VDO_HOST = getVdoHost()
  const VDO_PROTOCOL = getVdoProtocol()
  const url = new URL(`${VDO_PROTOCOL}://${VDO_HOST}/`)
  
  url.searchParams.set('push', cameraId)
  url.searchParams.set('room', VDO_ROOM)
  url.searchParams.set('whepshare', whepUrl)
  url.searchParams.set('label', label)
  url.searchParams.set('videodevice', '0')
  url.searchParams.set('audiodevice', '0')
  url.searchParams.set('autostart', '')
  url.searchParams.set('css', getVdoCssUrl())
  
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

