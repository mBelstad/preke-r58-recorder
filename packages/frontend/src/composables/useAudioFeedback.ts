/**
 * Audio Feedback System
 * 
 * Provides optional audio cues for important actions.
 * Uses Web Audio API for low-latency playback.
 */
import { ref } from 'vue'

// Sound enabled state (persisted in localStorage)
const enabled = ref(localStorage.getItem('r58_audio_feedback') !== 'false')

// Audio context (lazy initialized)
let audioContext: AudioContext | null = null

function getAudioContext(): AudioContext {
  if (!audioContext) {
    audioContext = new (window.AudioContext || (window as any).webkitAudioContext)()
  }
  return audioContext
}

/**
 * Play a simple beep tone
 */
function playTone(frequency: number, duration: number, type: OscillatorType = 'sine', volume: number = 0.3) {
  if (!enabled.value) return
  
  try {
    const ctx = getAudioContext()
    
    // Resume context if suspended (browser autoplay policy)
    if (ctx.state === 'suspended') {
      ctx.resume()
    }
    
    const oscillator = ctx.createOscillator()
    const gainNode = ctx.createGain()
    
    oscillator.connect(gainNode)
    gainNode.connect(ctx.destination)
    
    oscillator.type = type
    oscillator.frequency.value = frequency
    
    // Fade in/out to avoid clicks
    const now = ctx.currentTime
    gainNode.gain.setValueAtTime(0, now)
    gainNode.gain.linearRampToValueAtTime(volume, now + 0.01)
    gainNode.gain.linearRampToValueAtTime(0, now + duration)
    
    oscillator.start(now)
    oscillator.stop(now + duration)
  } catch (e) {
    console.warn('Audio feedback failed:', e)
  }
}

/**
 * Play a success sound (ascending tone)
 */
function playSuccess() {
  if (!enabled.value) return
  
  playTone(440, 0.1, 'sine', 0.2) // A4
  setTimeout(() => playTone(554, 0.1, 'sine', 0.2), 100) // C#5
  setTimeout(() => playTone(659, 0.15, 'sine', 0.25), 200) // E5
}

/**
 * Play a recording start sound (deep beep)
 */
function playRecordStart() {
  if (!enabled.value) return
  
  // Two short beeps
  playTone(880, 0.08, 'sine', 0.3) // A5
  setTimeout(() => playTone(880, 0.15, 'sine', 0.3), 120)
}

/**
 * Play a recording stop sound (descending tone)
 */
function playRecordStop() {
  if (!enabled.value) return
  
  playTone(659, 0.1, 'sine', 0.25) // E5
  setTimeout(() => playTone(554, 0.1, 'sine', 0.2), 100) // C#5
  setTimeout(() => playTone(440, 0.15, 'sine', 0.2), 200) // A4
}

/**
 * Play an error sound (low buzz)
 */
function playError() {
  if (!enabled.value) return
  
  playTone(200, 0.15, 'square', 0.15)
  setTimeout(() => playTone(180, 0.2, 'square', 0.15), 180)
}

/**
 * Play a warning sound (two short high beeps)
 */
function playWarning() {
  if (!enabled.value) return
  
  playTone(1000, 0.08, 'sine', 0.2)
  setTimeout(() => playTone(1000, 0.08, 'sine', 0.2), 150)
}

/**
 * Play a click sound (very short)
 */
function playClick() {
  if (!enabled.value) return
  
  playTone(1200, 0.03, 'sine', 0.1)
}

/**
 * Trigger haptic feedback if available
 */
function vibrate(pattern: number | number[] = 50) {
  if (!enabled.value) return
  
  if ('vibrate' in navigator) {
    try {
      navigator.vibrate(pattern)
    } catch (e) {
      // Vibration not supported or blocked
    }
  }
}

export function useAudioFeedback() {
  function setEnabled(value: boolean) {
    enabled.value = value
    localStorage.setItem('r58_audio_feedback', String(value))
  }
  
  function toggle() {
    setEnabled(!enabled.value)
    if (enabled.value) {
      playClick() // Confirm audio is working
    }
  }

  return {
    enabled,
    setEnabled,
    toggle,
    playSuccess,
    playError,
    playWarning,
    playClick,
    playRecordStart,
    playRecordStop,
    vibrate,
  }
}

// Export singleton for direct use
export const audioFeedback = {
  get enabled() { return enabled.value },
  setEnabled: (v: boolean) => { enabled.value = v; localStorage.setItem('r58_audio_feedback', String(v)) },
  playSuccess,
  playError,
  playWarning,
  playClick,
  playRecordStart,
  playRecordStop,
  vibrate,
}

