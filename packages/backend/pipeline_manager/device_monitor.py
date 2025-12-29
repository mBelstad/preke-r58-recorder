"""Device monitor for hot-plug detection.

Periodically polls configured devices to detect signal changes
(camera connected/disconnected) and emits events.
"""
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict, Optional

from .config import CameraConfig, get_config, get_enabled_cameras
from .gstreamer.pipelines import get_device_capabilities, initialize_rkcif_device, RKCIF_SUBDEV_MAP

logger = logging.getLogger(__name__)

# Polling interval for device state checks
POLL_INTERVAL_SECONDS = 10


@dataclass
class DeviceState:
    """Tracked state for a device."""
    input_id: str
    device_path: str
    has_signal: bool = False
    width: int = 0
    height: int = 0
    format: str = ""
    last_checked: Optional[datetime] = None


class DeviceMonitor:
    """Monitors configured devices for signal changes.
    
    Periodically polls each configured camera device to detect:
    - New camera connections (signal goes from False to True)
    - Camera disconnections (signal goes from True to False)
    
    Emits callbacks when changes are detected.
    """
    
    def __init__(
        self,
        on_connected: Optional[Callable[[str, Dict[str, Any]], Awaitable[None]]] = None,
        on_disconnected: Optional[Callable[[str], Awaitable[None]]] = None,
    ):
        """Initialize the device monitor.
        
        Args:
            on_connected: Callback when device gains signal. Args: (input_id, capabilities)
            on_disconnected: Callback when device loses signal. Args: (input_id,)
        """
        self.on_connected = on_connected
        self.on_disconnected = on_disconnected
        
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._device_states: Dict[str, DeviceState] = {}
        
    def start(self) -> None:
        """Start the device monitor."""
        if self._running:
            return
            
        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("Device monitor started")
        
    def stop(self) -> None:
        """Stop the device monitor."""
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None
        logger.info("Device monitor stopped")
        
    def get_device_states(self) -> Dict[str, Dict[str, Any]]:
        """Get current device states.
        
        Returns:
            Dict mapping input_id to device state info
        """
        return {
            input_id: {
                "input_id": state.input_id,
                "device_path": state.device_path,
                "has_signal": state.has_signal,
                "width": state.width,
                "height": state.height,
                "format": state.format,
                "last_checked": state.last_checked.isoformat() if state.last_checked else None,
            }
            for input_id, state in self._device_states.items()
        }
    
    async def _poll_loop(self) -> None:
        """Main polling loop."""
        # Initial scan to populate states
        await self._scan_devices(initial=True)
        
        while self._running:
            try:
                await asyncio.sleep(POLL_INTERVAL_SECONDS)
                if self._running:
                    await self._scan_devices(initial=False)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in device monitor poll loop: {e}")
                await asyncio.sleep(POLL_INTERVAL_SECONDS)
    
    async def _scan_devices(self, initial: bool = False) -> None:
        """Scan all configured devices for signal changes.
        
        Args:
            initial: If True, don't emit events (just populate initial state)
        """
        config = get_config()
        enabled_cameras = get_enabled_cameras(config)
        
        for input_id, cam_config in enabled_cameras.items():
            try:
                await self._check_device(input_id, cam_config, initial)
            except Exception as e:
                logger.warning(f"Error checking device {input_id}: {e}")
    
    async def _check_device(
        self, 
        input_id: str, 
        cam_config: CameraConfig,
        initial: bool
    ) -> None:
        """Check a single device for signal changes.
        
        Args:
            input_id: Camera/input identifier
            cam_config: Camera configuration
            initial: If True, don't emit events
        """
        # Get current capabilities (runs in executor to avoid blocking)
        # For rkcif devices, use initialize_rkcif_device which queries subdev and sets format
        loop = asyncio.get_event_loop()
        device = cam_config.device
        if device in RKCIF_SUBDEV_MAP:
            caps = await loop.run_in_executor(
                None,
                lambda: initialize_rkcif_device(device)
            )
        else:
            caps = await loop.run_in_executor(
                None,
                lambda: get_device_capabilities(device)
            )
        
        now = datetime.now()
        has_signal = caps.get('has_signal', False)
        width = caps.get('width', 0)
        height = caps.get('height', 0)
        fmt = caps.get('format', '')
        
        # Get or create state
        prev_state = self._device_states.get(input_id)
        
        if prev_state is None:
            # First time seeing this device
            self._device_states[input_id] = DeviceState(
                input_id=input_id,
                device_path=cam_config.device,
                has_signal=has_signal,
                width=width,
                height=height,
                format=fmt,
                last_checked=now,
            )
            
            if not initial and has_signal and self.on_connected:
                logger.info(f"Device {input_id} detected with signal: {width}x{height} {fmt}")
                await self.on_connected(input_id, caps)
        else:
            # Check for state change
            was_connected = prev_state.has_signal
            
            # Update state
            prev_state.has_signal = has_signal
            prev_state.width = width
            prev_state.height = height
            prev_state.format = fmt
            prev_state.last_checked = now
            
            if not initial:
                if not was_connected and has_signal:
                    # Device just connected
                    logger.info(f"Device {input_id} connected: {width}x{height} {fmt}")
                    if self.on_connected:
                        await self.on_connected(input_id, caps)
                        
                elif was_connected and not has_signal:
                    # Device just disconnected
                    logger.info(f"Device {input_id} disconnected")
                    if self.on_disconnected:
                        await self.on_disconnected(input_id)


# Singleton instance
_monitor: Optional[DeviceMonitor] = None


def get_device_monitor() -> DeviceMonitor:
    """Get the singleton DeviceMonitor instance."""
    global _monitor
    if _monitor is None:
        _monitor = DeviceMonitor()
    return _monitor

