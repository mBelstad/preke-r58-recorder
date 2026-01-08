"""PTZ Controller support for hardware joystick/controller devices.

Supports:
- USB Gamepad/Joystick controllers (via Web Gamepad API)
- Network PTZ controllers (VISCA over IP)
- WebSocket real-time PTZ control
"""
import logging
import asyncio
from typing import Optional, Dict, Any, Callable
import socket
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PTZCommand:
    """PTZ command from controller."""
    pan: float  # -1.0 to 1.0
    tilt: float  # -1.0 to 1.0
    zoom: float  # -1.0 to 1.0
    focus: Optional[float] = None  # -1.0 to 1.0 (optional)
    speed: float = 1.0  # Speed multiplier (0.0 to 1.0)


class PTZController:
    """Base class for PTZ controllers."""
    
    def __init__(self, controller_id: str, name: str):
        """Initialize PTZ controller.
        
        Args:
            controller_id: Unique controller identifier
            name: Human-readable controller name
        """
        self.controller_id = controller_id
        self.name = name
        self.active = False
        self.current_camera: Optional[str] = None
        self.callback: Optional[Callable[[PTZCommand], None]] = None
    
    async def start(self):
        """Start controller."""
        self.active = True
        logger.info(f"PTZ controller started: {self.name} ({self.controller_id})")
    
    async def stop(self):
        """Stop controller."""
        self.active = False
        logger.info(f"PTZ controller stopped: {self.name}")
    
    def set_camera(self, camera_name: str):
        """Set target camera for PTZ control."""
        self.current_camera = camera_name
        logger.info(f"PTZ controller {self.name} targeting camera: {camera_name}")
    
    def set_callback(self, callback: Callable[[PTZCommand], None]):
        """Set callback for PTZ commands."""
        self.callback = callback


class GamepadPTZController(PTZController):
    """USB Gamepad/Joystick PTZ controller.
    
    Maps gamepad axes/buttons to PTZ movements:
    - Left stick: Pan/Tilt
    - Right stick: Zoom/Focus (optional)
    - Triggers: Speed control
    """
    
    def __init__(self, controller_id: str, name: str, gamepad_index: int = 0):
        """Initialize gamepad controller.
        
        Args:
            controller_id: Unique controller identifier
            name: Controller name
            gamepad_index: Gamepad index (0-based)
        """
        super().__init__(controller_id, name)
        self.gamepad_index = gamepad_index
        self.deadzone = 0.1  # Deadzone for stick drift
        self.speed_multiplier = 0.5  # Default speed
        self._last_command: Optional[PTZCommand] = None
    
    async def process_gamepad_input(
        self,
        axes: list[float],
        buttons: list[bool],
        triggers: Optional[dict[str, float]] = None
    ):
        """Process gamepad input and generate PTZ commands.
        
        Args:
            axes: Gamepad axes values (-1.0 to 1.0)
            buttons: Button states
            triggers: Trigger values (optional)
        """
        if not self.active or not self.callback:
            return
        
        # Map axes to PTZ
        # Left stick (axes 0, 1): Pan/Tilt
        pan = self._apply_deadzone(axes[0] if len(axes) > 0 else 0.0)
        tilt = self._apply_deadzone(-axes[1] if len(axes) > 1 else 0.0)  # Invert Y
        
        # Right stick (axes 2, 3): Zoom/Focus
        zoom = self._apply_deadzone(axes[2] if len(axes) > 2 else 0.0)
        focus = self._apply_deadzone(axes[3] if len(axes) > 3 else 0.0) if len(axes) > 3 else None
        
        # Speed control from triggers or buttons
        speed = self.speed_multiplier
        if triggers:
            # Use right trigger for speed boost
            speed = min(1.0, self.speed_multiplier + triggers.get("right", 0.0) * 0.5)
        
        # Apply speed multiplier
        pan *= speed
        tilt *= speed
        zoom *= speed
        
        # Only send command if there's actual movement (avoid spam)
        if abs(pan) > 0.01 or abs(tilt) > 0.01 or abs(zoom) > 0.01:
            command = PTZCommand(
                pan=pan,
                tilt=tilt,
                zoom=zoom,
                focus=focus,
                speed=speed
            )
            
            # Throttle updates (max 30Hz for smooth control)
            if self._should_send_command(command):
                self._last_command = command
                self.callback(command)
    
    def _apply_deadzone(self, value: float) -> float:
        """Apply deadzone to axis value."""
        if abs(value) < self.deadzone:
            return 0.0
        # Normalize after deadzone
        sign = 1.0 if value >= 0 else -1.0
        normalized = (abs(value) - self.deadzone) / (1.0 - self.deadzone)
        return sign * normalized
    
    def _should_send_command(self, command: PTZCommand) -> bool:
        """Check if command should be sent (throttling)."""
        if self._last_command is None:
            return True
        
        # Send if movement changed significantly
        threshold = 0.05
        return (
            abs(command.pan - self._last_command.pan) > threshold or
            abs(command.tilt - self._last_command.tilt) > threshold or
            abs(command.zoom - self._last_command.zoom) > threshold
        )


class VISCAPTZController(PTZController):
    """Network-based VISCA PTZ controller.
    
    Receives VISCA commands over UDP and converts to PTZ commands.
    """
    
    def __init__(self, controller_id: str, name: str, port: int = 52381):
        """Initialize VISCA controller.
        
        Args:
            controller_id: Unique controller identifier
            name: Controller name
            port: UDP port to listen on
        """
        super().__init__(controller_id, name)
        self.port = port
        self.socket: Optional[socket.socket] = None
        self._running = False
    
    async def start(self):
        """Start VISCA controller."""
        await super().start()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(('0.0.0.0', self.port))
        self.socket.setblocking(False)
        self._running = True
        
        # Start listener task
        asyncio.create_task(self._listen_loop())
        logger.info(f"VISCA PTZ controller listening on port {self.port}")
    
    async def stop(self):
        """Stop VISCA controller."""
        await super().stop()
        self._running = False
        if self.socket:
            self.socket.close()
            self.socket = None
    
    async def _listen_loop(self):
        """Listen for VISCA commands."""
        loop = asyncio.get_event_loop()
        
        while self._running:
            try:
                data, addr = await loop.sock_recvfrom(self.socket, 1024)
                command = self._parse_visca_command(data)
                if command and self.callback:
                    self.callback(command)
            except asyncio.CancelledError:
                break
            except Exception as e:
                if self._running:
                    logger.error(f"Error in VISCA controller: {e}")
                await asyncio.sleep(0.01)
    
    def _parse_visca_command(self, data: bytes) -> Optional[PTZCommand]:
        """Parse VISCA command to PTZ command.
        
        VISCA PTZ format:
        - Pan/Tilt: 8x 01 06 01 VV WW 0Y 0Z FF
        - Zoom: 8x 01 04 07 2p FF
        """
        if len(data) < 3:
            return None
        
        cmd_type = data[2]
        pan = 0.0
        tilt = 0.0
        zoom = 0.0
        
        # Pan/Tilt command (0x06)
        if cmd_type == 0x06 and len(data) >= 9:
            pan_speed = data[4] if len(data) > 4 else 0
            tilt_speed = data[5] if len(data) > 5 else 0
            pan_dir = data[6] if len(data) > 6 else 0
            tilt_dir = data[7] if len(data) > 7 else 0
            
            # Convert to normalized values
            pan = self._visca_speed_to_normalized(pan_speed, pan_dir)
            tilt = self._visca_speed_to_normalized(tilt_speed, tilt_dir)
        
        # Zoom command (0x04 0x07)
        elif cmd_type == 0x04 and len(data) >= 5 and data[3] == 0x07:
            zoom_byte = data[4] if len(data) > 4 else 0
            zoom = self._visca_zoom_to_normalized(zoom_byte)
        
        if pan != 0.0 or tilt != 0.0 or zoom != 0.0:
            return PTZCommand(pan=pan, tilt=tilt, zoom=zoom)
        
        return None
    
    def _visca_speed_to_normalized(self, speed: int, direction: int) -> float:
        """Convert VISCA speed/direction to normalized value."""
        if speed == 0 or direction == 0x03:  # Stop
            return 0.0
        
        # Speed: 0x01-0x18 (1-24)
        normalized_speed = speed / 24.0
        
        # Direction: 0x01 = left/up, 0x02 = right/down
        if direction == 0x01:
            return -normalized_speed
        elif direction == 0x02:
            return normalized_speed
        
        return 0.0
    
    def _visca_zoom_to_normalized(self, zoom_byte: int) -> float:
        """Convert VISCA zoom byte to normalized value."""
        if zoom_byte == 0:
            return 0.0
        
        # Zoom: 0x20-0x27 = tele (zoom in), 0x30-0x37 = wide (zoom out)
        if 0x20 <= zoom_byte <= 0x27:
            # Tele (zoom in)
            speed = (zoom_byte & 0x0F) / 7.0
            return speed
        elif 0x30 <= zoom_byte <= 0x37:
            # Wide (zoom out)
            speed = (zoom_byte & 0x0F) / 7.0
            return -speed
        
        return 0.0


class PTZControllerManager:
    """Manages multiple PTZ controllers."""
    
    def __init__(self):
        """Initialize controller manager."""
        self.controllers: Dict[str, PTZController] = {}
        self.camera_callback: Optional[Callable[[str, PTZCommand], None]] = None
    
    def add_controller(self, controller: PTZController):
        """Add a PTZ controller."""
        controller.set_callback(self._handle_ptz_command)
        self.controllers[controller.controller_id] = controller
        logger.info(f"Added PTZ controller: {controller.name}")
    
    def remove_controller(self, controller_id: str):
        """Remove a PTZ controller."""
        if controller_id in self.controllers:
            controller = self.controllers.pop(controller_id)
            asyncio.create_task(controller.stop())
            logger.info(f"Removed PTZ controller: {controller.name}")
    
    def set_camera_callback(self, callback: Callable[[str, PTZCommand], None]):
        """Set callback for PTZ commands to cameras."""
        self.camera_callback = callback
    
    def _handle_ptz_command(self, command: PTZCommand):
        """Handle PTZ command from controller."""
        # Find which controller sent it
        for controller_id, controller in self.controllers.items():
            if controller.callback == self._handle_ptz_command:
                if controller.current_camera and self.camera_callback:
                    self.camera_callback(controller.current_camera, command)
                break
