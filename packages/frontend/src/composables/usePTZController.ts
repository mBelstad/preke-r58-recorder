/**
 * usePTZController - Composable for PTZ controller support (gamepad/joystick)
 * 
 * Supports:
 * - Web Gamepad API for USB and Bluetooth gamepads/joysticks
 * - WebSocket for real-time PTZ control
 * - Auto-detection and reconnection handling
 */
import { ref, onMounted, onUnmounted } from 'vue'
import { r58Api } from '@/lib/api'

export interface PTZCommand {
  pan: number  // -1.0 to 1.0
  tilt: number  // -1.0 to 1.0
  zoom: number  // -1.0 to 1.0
  focus?: number  // -1.0 to 1.0 (optional)
  speed?: number  // 0.0 to 1.0
}

export function usePTZController(cameraName: string | null = null) {
  const connected = ref(false)
  const active = ref(false)
  const currentCamera = ref<string | null>(cameraName)
  const gamepadIndex = ref<number | null>(null)
  const gamepadInfo = ref<{ id: string; index: number; mapping: string } | null>(null)
  
  let ws: WebSocket | null = null
  let animationFrame: number | null = null
  let lastCommandTime = 0
  const minCommandInterval = 33 // ~30Hz max update rate (ms)
  let reconnectTimeout: number | null = null

  // Connect WebSocket for real-time PTZ control
  async function connect() {
    if (ws?.readyState === WebSocket.OPEN) {
      return
    }

    try {
      const wsUrl = await r58Api.buildApiUrl('/api/v1/ptz-controller/ws')
      ws = new WebSocket(wsUrl.replace('http', 'ws').replace('https', 'wss'))
      
      ws.onopen = () => {
        connected.value = true
        if (currentCamera.value) {
          setCamera(currentCamera.value)
        }
      }
      
      ws.onerror = (error) => {
        console.error('[PTZController] WebSocket error:', error)
        connected.value = false
      }
      
      ws.onclose = () => {
        connected.value = false
      }
    } catch (error) {
      console.error('[PTZController] Failed to connect:', error)
    }
  }

  function disconnect() {
    if (ws) {
      ws.close()
      ws = null
    }
    connected.value = false
    stopGamepad()
  }

  function setCamera(cameraName: string) {
    currentCamera.value = cameraName
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'set_camera',
        camera_name: cameraName
      }))
    }
  }

  // Send PTZ command via WebSocket (fastest path)
  function sendPTZCommand(command: PTZCommand) {
    if (!connected.value || !currentCamera.value || !ws) {
      return
    }

    // Throttle commands
    const now = Date.now()
    if (now - lastCommandTime < minCommandInterval) {
      return
    }
    lastCommandTime = now

    ws.send(JSON.stringify({
      type: 'ptz_command',
      pan: command.pan,
      tilt: command.tilt,
      zoom: command.zoom,
      focus: command.focus,
      speed: command.speed || 1.0
    }))
  }

  // Gamepad support
  function startGamepad(index: number = 0) {
    if (animationFrame) {
      return // Already running
    }

    gamepadIndex.value = index
    active.value = true

    function pollGamepad() {
      if (!active.value) {
        return
      }

      const gamepads = navigator.getGamepads()
      const gamepad = gamepads[gamepadIndex.value!]

      if (!gamepad) {
        // Gamepad disconnected (USB or Bluetooth)
        console.log('[PTZController] Gamepad disconnected during polling')
        stopGamepad()
        // Schedule reconnection check (Bluetooth gamepads may reconnect)
        scheduleReconnectCheck()
        return
      }
      
      // Update gamepad info (useful for debugging Bluetooth connections)
      if (!gamepadInfo.value || gamepadInfo.value.index !== gamepad.index) {
        gamepadInfo.value = {
          id: gamepad.id,
          index: gamepad.index,
          mapping: gamepad.mapping || 'standard'
        }
      }

      // Map gamepad axes to PTZ
      // Left stick (axes 0, 1): Pan/Tilt
      // Right stick (axes 2, 3): Zoom/Focus
      const axes = Array.from(gamepad.axes)
      const buttons = Array.from(gamepad.buttons)

      const pan = applyDeadzone(axes[0] || 0, 0.1)
      const tilt = applyDeadzone(-(axes[1] || 0), 0.1) // Invert Y
      const zoom = applyDeadzone(axes[2] || 0, 0.1)
      const focus = axes[3] ? applyDeadzone(axes[3], 0.1) : undefined

      // Speed control from triggers (buttons 6, 7)
      let speed = 0.5 // Default speed
      if (buttons[6]?.value) {
        speed += buttons[6].value * 0.5 // Left trigger
      }
      if (buttons[7]?.value) {
        speed += buttons[7].value * 0.5 // Right trigger
      }
      speed = Math.min(1.0, speed)

      // Apply speed multiplier
      const command: PTZCommand = {
        pan: pan * speed,
        tilt: tilt * speed,
        zoom: zoom * speed,
        focus: focus ? focus * speed : undefined,
        speed
      }

      // Only send if there's movement
      if (Math.abs(command.pan) > 0.01 || Math.abs(command.tilt) > 0.01 || Math.abs(command.zoom) > 0.01) {
        sendPTZCommand(command)
      }

      animationFrame = requestAnimationFrame(pollGamepad)
    }

    pollGamepad()
  }

  function stopGamepad() {
    active.value = false
    gamepadIndex.value = null
    if (animationFrame) {
      cancelAnimationFrame(animationFrame)
      animationFrame = null
    }
  }

  function applyDeadzone(value: number, deadzone: number): number {
    if (Math.abs(value) < deadzone) {
      return 0
    }
    const sign = value >= 0 ? 1 : -1
    const normalized = (Math.abs(value) - deadzone) / (1 - deadzone)
    return sign * normalized
  }

  // Schedule reconnection check (for Bluetooth gamepads that may reconnect)
  function scheduleReconnectCheck() {
    if (reconnectTimeout) {
      clearTimeout(reconnectTimeout)
    }
    // Check for reconnection after 1 second
    reconnectTimeout = window.setTimeout(() => {
      const gamepads = navigator.getGamepads()
      for (let i = 0; i < gamepads.length; i++) {
        if (gamepads[i] && gamepadIndex.value === null) {
          console.log('[PTZController] Gamepad reconnected:', gamepads[i].id)
          startGamepad(i)
          break
        }
      }
      reconnectTimeout = null
    }, 1000)
  }

  // Auto-detect gamepad connection (USB or Bluetooth)
  function handleGamepadConnected(event: GamepadEvent) {
    const gamepad = event.gamepad
    const connectionType = gamepad.id.toLowerCase().includes('bluetooth') || 
                          gamepad.id.toLowerCase().includes('wireless') 
                          ? 'Bluetooth' : 'USB'
    
    console.log(`[PTZController] ${connectionType} gamepad connected:`, gamepad.id, {
      index: gamepad.index,
      mapping: gamepad.mapping || 'standard',
      axes: gamepad.axes.length,
      buttons: gamepad.buttons.length
    })
    
    if (gamepadIndex.value === null) {
      startGamepad(gamepad.index)
    }
  }

  function handleGamepadDisconnected(event: GamepadEvent) {
    const gamepad = event.gamepad
    const connectionType = gamepad.id.toLowerCase().includes('bluetooth') || 
                          gamepad.id.toLowerCase().includes('wireless') 
                          ? 'Bluetooth' : 'USB'
    
    console.log(`[PTZController] ${connectionType} gamepad disconnected:`, gamepad.id)
    
    if (gamepadIndex.value === event.gamepad.index) {
      stopGamepad()
      gamepadInfo.value = null
      // Schedule reconnection check for Bluetooth gamepads
      scheduleReconnectCheck()
    }
  }

  onMounted(() => {
    connect()
    window.addEventListener('gamepadconnected', handleGamepadConnected)
    window.addEventListener('gamepaddisconnected', handleGamepadDisconnected)
    
    // Check for already connected gamepads
    const gamepads = navigator.getGamepads()
    for (let i = 0; i < gamepads.length; i++) {
      if (gamepads[i]) {
        startGamepad(i)
        break
      }
    }
  })

  onUnmounted(() => {
    disconnect()
    stopGamepad()
    if (reconnectTimeout) {
      clearTimeout(reconnectTimeout)
    }
    window.removeEventListener('gamepadconnected', handleGamepadConnected)
    window.removeEventListener('gamepaddisconnected', handleGamepadDisconnected)
  })

  return {
    connected,
    active,
    currentCamera,
    gamepadIndex,
    gamepadInfo,
    connect,
    disconnect,
    setCamera,
    sendPTZCommand,
    startGamepad,
    stopGamepad
  }
}
