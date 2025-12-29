/**
 * VDO.ninja TypeScript Type Definitions
 * 
 * Comprehensive types for VDO.ninja postMessage API communication.
 * Based on VDO.ninja iframe API documentation and observed message formats.
 * 
 * @see https://docs.vdo.ninja/guides/iframe-api-documentation
 */

// ==========================================
// SOURCE TYPES
// ==========================================

/** Types of video/audio sources in VDO.ninja */
export type VdoSourceType = 'camera' | 'guest' | 'screen' | 'media' | 'whep' | 'rtmp' | 'srt'

/** Information about a connected source */
export interface VdoSource {
  /** Unique stream identifier */
  id: string
  /** Display label for the source */
  label: string
  /** Type of source */
  type: VdoSourceType
  /** Whether source has video */
  hasVideo: boolean
  /** Whether source has audio */
  hasAudio: boolean
  /** Whether audio is muted */
  muted: boolean
  /** Current audio level (0-100) */
  audioLevel?: number
  /** Video width in pixels */
  width?: number
  /** Video height in pixels */
  height?: number
  /** Video framerate */
  framerate?: number
  /** Video bitrate in kbps */
  videoBitrate?: number
  /** Audio bitrate in kbps */
  audioBitrate?: number
  /** Whether source is in the waiting room */
  inWaitingRoom?: boolean
  /** Whether source is visible in scene */
  inScene?: boolean
}

/** Guest information with additional metadata */
export interface VdoGuest extends VdoSource {
  /** Guest's display name */
  displayName?: string
  /** Whether guest has camera permission */
  cameraAllowed: boolean
  /** Whether guest has microphone permission */
  micAllowed: boolean
  /** Whether guest has screen share permission */
  screenShareAllowed: boolean
  /** Guest's connection quality (0-100) */
  connectionQuality?: number
  /** Time when guest joined (ISO string) */
  joinedAt?: string
}

// ==========================================
// OUTGOING COMMANDS (UI → VDO.ninja iframe)
// ==========================================

/** Base structure for all outgoing commands */
export interface VdoCommandBase {
  /** Command action name */
  action: string
  /** Target stream ID (optional) */
  target?: string
  /** Command value/payload (optional) */
  value?: unknown
}

// --- Scene/Layout Commands ---

export interface VdoChangeSceneCommand extends VdoCommandBase {
  action: 'changeScene'
  value: string | number
}

export interface VdoLayoutCommand extends VdoCommandBase {
  action: 'layout'
  value: 'grid' | 'solo' | 'pip' | 'custom' | string
}

export interface VdoSoloVideoCommand extends VdoCommandBase {
  action: 'soloVideo'
  target: string
}

export interface VdoPipCommand extends VdoCommandBase {
  action: 'pip'
  target: string
  value: 'enable' | 'disable'
}

export interface VdoSetSlotsCommand extends VdoCommandBase {
  action: 'setSlots'
  value: VdoSlotConfig
}

export interface VdoFullscreenCommand extends VdoCommandBase {
  action: 'fullscreen'
  target: string
}

// --- Audio Commands ---

export interface VdoMuteCommand extends VdoCommandBase {
  action: 'mute'
  target: string
  value: boolean
}

export interface VdoVolumeCommand extends VdoCommandBase {
  action: 'volume'
  target: string
  /** Volume level 0-100 */
  value: number
}

export interface VdoSoloChatCommand extends VdoCommandBase {
  action: 'soloChat'
  target: string
}

export interface VdoGainCommand extends VdoCommandBase {
  action: 'gain'
  target: string
  /** Gain multiplier (1.0 = normal) */
  value: number
}

// --- Guest Management Commands ---

export interface VdoHangupCommand extends VdoCommandBase {
  action: 'hangup'
  target: string
}

export interface VdoSendChatCommand extends VdoCommandBase {
  action: 'sendChat'
  target: string
  value: string
}

export interface VdoRequestScreenCommand extends VdoCommandBase {
  action: 'requestScreen'
  target: string
}

export interface VdoHighlightCommand extends VdoCommandBase {
  action: 'highlight'
  target: string
}

export interface VdoAddToSceneCommand extends VdoCommandBase {
  action: 'addToScene'
  target: string
}

export interface VdoRemoveFromSceneCommand extends VdoCommandBase {
  action: 'removeFromScene'
  target: string
}

export interface VdoReloadCommand extends VdoCommandBase {
  action: 'reload'
  target: string
}

// --- Recording Commands ---

export interface VdoRecordCommand extends VdoCommandBase {
  action: 'record'
  value: boolean
}

// --- Transition Commands ---

export interface VdoTransitionCommand extends VdoCommandBase {
  action: 'transition'
  value: {
    type: VdoTransitionType
    duration: number
  }
}

/** Union of all outgoing command types */
export type VdoCommand =
  | VdoChangeSceneCommand
  | VdoLayoutCommand
  | VdoSoloVideoCommand
  | VdoPipCommand
  | VdoSetSlotsCommand
  | VdoFullscreenCommand
  | VdoMuteCommand
  | VdoVolumeCommand
  | VdoSoloChatCommand
  | VdoGainCommand
  | VdoHangupCommand
  | VdoSendChatCommand
  | VdoRequestScreenCommand
  | VdoHighlightCommand
  | VdoAddToSceneCommand
  | VdoRemoveFromSceneCommand
  | VdoReloadCommand
  | VdoRecordCommand
  | VdoTransitionCommand
  | VdoCommandBase

// ==========================================
// INCOMING EVENTS (VDO.ninja iframe → UI)
// ==========================================

/** Base structure for all incoming events */
export interface VdoEventBase {
  /** Event type */
  type: string
  /** Stream ID if applicable */
  streamID?: string
  /** Alternative stream ID formats */
  UUID?: string
  streamId?: string
  /** Event data payload */
  data?: unknown
  /** Alternative value format */
  value?: unknown
  /** Source label */
  label?: string
}

// --- Ready Events ---

export interface VdoReadyEvent extends VdoEventBase {
  type: 'director-ready' | 'loaded' | 'ready' | 'started'
}

// --- Guest Connection Events ---

export interface VdoGuestConnectedEvent extends VdoEventBase {
  type: 'new-guest' | 'guest-connected' | 'push' | 'view' | 'joined'
  streamID: string
  data?: {
    label?: string
    type?: VdoSourceType
    video?: boolean
    audio?: boolean
  }
}

export interface VdoGuestDisconnectedEvent extends VdoEventBase {
  type: 'guest-left' | 'guest-disconnected' | 'left' | 'disconnect'
  streamID: string
}

// --- Audio Events ---

export interface VdoAudioLevelEvent extends VdoEventBase {
  type: 'audio-level' | 'loudness'
  streamID: string
  data?: {
    level: number
  }
}

export interface VdoMuteStateEvent extends VdoEventBase {
  type: 'mute-state' | 'muted'
  streamID: string
  data?: {
    muted: boolean
  }
}

// --- Scene Events ---

export interface VdoSceneChangedEvent extends VdoEventBase {
  type: 'scene-changed' | 'scene'
  data?: {
    scene: string
  }
}

// --- Recording Events ---

export interface VdoRecordingStartedEvent extends VdoEventBase {
  type: 'recording-started'
}

export interface VdoRecordingStoppedEvent extends VdoEventBase {
  type: 'recording-stopped'
  data?: {
    /** Recording duration in milliseconds */
    duration?: number
    /** Download URL if available */
    downloadUrl?: string
  }
}

// --- Error Events ---

export interface VdoErrorEvent extends VdoEventBase {
  type: 'error'
  data: {
    message: string
    code?: string
  }
}

// --- Stats Events ---

export interface VdoStatsEvent extends VdoEventBase {
  type: 'stats'
  streamID: string
  data: {
    /** Video bitrate in kbps */
    videoBitrate?: number
    /** Audio bitrate in kbps */
    audioBitrate?: number
    /** Packet loss percentage */
    packetLoss?: number
    /** Latency in ms */
    latency?: number
    /** Video resolution */
    resolution?: string
    /** Video framerate */
    framerate?: number
  }
}

// --- Chat Events ---

export interface VdoChatMessageEvent extends VdoEventBase {
  type: 'chat'
  streamID: string
  data: {
    message: string
    from: string
  }
}

/** Union of all incoming event types */
export type VdoEvent =
  | VdoReadyEvent
  | VdoGuestConnectedEvent
  | VdoGuestDisconnectedEvent
  | VdoAudioLevelEvent
  | VdoMuteStateEvent
  | VdoSceneChangedEvent
  | VdoRecordingStartedEvent
  | VdoRecordingStoppedEvent
  | VdoErrorEvent
  | VdoStatsEvent
  | VdoChatMessageEvent
  | VdoEventBase

// ==========================================
// LAYOUT & SLOT CONFIGURATION
// ==========================================

/** Position and size for a source slot */
export interface VdoSlotPosition {
  /** X position (0-100 percentage) */
  x: number
  /** Y position (0-100 percentage) */
  y: number
  /** Width (0-100 percentage) */
  width: number
  /** Height (0-100 percentage) */
  height: number
  /** Z-index for layering */
  zIndex?: number
  /** Border radius in pixels */
  borderRadius?: number
  /** Whether to crop to fit */
  cover?: boolean
}

/** Configuration for layout slots */
export interface VdoSlotConfig {
  /** Mapping of stream IDs to slot positions */
  [streamId: string]: VdoSlotPosition
}

/** Preset layout configuration */
export interface VdoLayoutPreset {
  /** Unique preset ID */
  id: string
  /** Display name */
  name: string
  /** Layout type */
  type: 'grid' | 'solo' | 'pip' | 'split' | 'custom'
  /** Number of slots (for grid layouts) */
  slots?: number
  /** Custom slot configuration */
  slotConfig?: VdoSlotConfig
  /** Thumbnail/preview URL */
  thumbnailUrl?: string
}

// ==========================================
// TRANSITION TYPES
// ==========================================

/** Available transition types */
export type VdoTransitionType = 
  | 'cut'
  | 'fade'
  | 'wipe-left'
  | 'wipe-right'
  | 'wipe-up'
  | 'wipe-down'
  | 'slide-left'
  | 'slide-right'
  | 'zoom'
  | 'stinger'

/** Transition configuration */
export interface VdoTransitionConfig {
  /** Transition type */
  type: VdoTransitionType
  /** Duration in milliseconds */
  duration: number
  /** Easing function */
  easing?: 'linear' | 'ease' | 'ease-in' | 'ease-out' | 'ease-in-out'
  /** Stinger URL for stinger transitions */
  stingerUrl?: string
}

// ==========================================
// URL PARAMETERS
// ==========================================

/** Common VDO.ninja URL parameters */
export interface VdoUrlParams {
  // Room/Identity
  room?: string
  director?: string
  push?: string
  view?: string
  scene?: boolean
  
  // Display
  cover?: boolean
  cleanoutput?: boolean
  hideheader?: boolean
  nologo?: boolean
  darkmode?: boolean
  hidesolo?: boolean
  
  // Quality
  quality?: 0 | 1 | 2
  bitrate?: number
  width?: number
  height?: number
  framerate?: number
  
  // Audio
  noaudio?: boolean
  audiodevice?: number | string
  
  // Video
  videodevice?: number | string
  webcam?: boolean
  
  // MediaMTX Integration
  mediamtx?: string
  whepshare?: string
  whipout?: string
  
  // Auto-behavior
  autostart?: boolean
  autoadd?: string
  
  // Styling
  css?: string
  
  // Animation
  fadein?: number
  animated?: boolean
  
  // Grid
  grid?: boolean
  
  // Labels
  label?: string
  
  // Effects
  effects?: boolean
}

// ==========================================
// DEBUG & INSTRUMENTATION
// ==========================================

/** Debug log entry for VDO.ninja events */
export interface VdoDebugEntry {
  /** Timestamp of the event */
  timestamp: number
  /** Direction of the message */
  direction: 'incoming' | 'outgoing'
  /** Event/command type */
  type: string
  /** Target stream ID */
  target?: string
  /** Parsed data */
  data: unknown
  /** Raw message for debugging */
  raw?: unknown
}

/** Statistics about VDO.ninja events */
export interface VdoEventStats {
  /** Total events logged */
  total: number
  /** Incoming events count */
  incoming: number
  /** Outgoing events count */
  outgoing: number
  /** Events by type */
  byType: Record<string, number>
  /** Timestamp of last activity */
  lastActivity: number | null
}

// ==========================================
// CONNECTION STATE
// ==========================================

/** VDO.ninja connection states */
export type VdoConnectionState = 'disconnected' | 'connecting' | 'connected' | 'error'

/** VDO.ninja composable state */
export interface VdoState {
  /** Whether the iframe is ready */
  isReady: boolean
  /** Current connection state */
  connectionState: VdoConnectionState
  /** Map of connected sources */
  sources: Map<string, VdoSource>
  /** Currently active scene */
  activeScene: string | null
  /** Whether recording is active */
  isRecording: boolean
  /** Last error message */
  lastError: string | null
}

// ==========================================
// SCENE PRESETS
// ==========================================

/** Saved scene preset */
export interface VdoScenePreset {
  /** Unique preset ID */
  id: string
  /** Display name */
  name: string
  /** Scene/layout ID */
  sceneId: string
  /** Layout type */
  layoutType: 'grid' | 'solo' | 'pip' | 'custom'
  /** Slot configuration */
  slots?: VdoSlotConfig
  /** Source ordering */
  sourceOrder?: string[]
  /** Created timestamp */
  createdAt: string
  /** Last used timestamp */
  lastUsedAt?: string
  /** Keyboard shortcut */
  hotkey?: string
}

/** Scene presets storage */
export interface VdoScenePresetsStorage {
  version: number
  presets: VdoScenePreset[]
  activePresetId?: string
}

