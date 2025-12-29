"""Device monitor for hot-plug detection.

Periodically polls configured devices to detect signal changes
(camera connected/disconnected) and emits events.

IMPORTANT: This monitor uses READ-ONLY queries for ongoing monitoring.
It does NOT reinitialize devices that already have active pipelines.
Device initialization only happens:
1. At startup (before pipelines start)
2. When a device transitions from no-signal to signal (hot-plug)

The `rkcif_s_fmt_vid_cap_mplane queue busy` kernel error and crashes
occur when trying to set format on a device with an active pipeline.
"""
import asyncio
import logging
import subprocess
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict, Optional, Set

from .config import CameraConfig, get_config, get_enabled_cameras
from .gstreamer.pipelines import get_device_capabilities, initialize_rkcif_device, RKCIF_SUBDEV_MAP

logger = logging.getLogger(__name__)

# Polling interval for device state checks
POLL_INTERVAL_SECONDS = 10

# Map of subdevs for read-only signal detection (no format setting!)
RKCIF_SUBDEV_MAP_READONLY = {
    "/dev/video0": "/dev/v4l-subdev2",   # HDMI IN0 (LT6911 7-002b)
    "/dev/video11": "/dev/v4l-subdev7",  # HDMI IN11 (LT6911 4-002b)
    "/dev/video22": "/dev/v4l-subdev12", # HDMI IN21 (LT6911 2-002b)
}


def _get_subdev_resolution_readonly(subdev_path: str) -> tuple[int, int]:
    """Query subdev for resolution WITHOUT setting format on video device.
    
    This is safe to call while a pipeline is running.
    
    Returns:
        (width, height) tuple, or (0, 0) if no signal
    """
    try:
        result = subprocess.run(
            ["v4l2-ctl", "-d", subdev_path, "--get-subdev-fmt", "pad=0"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            match = re.search(r"Width/Height\s*:\s*(\d+)/(\d+)", result.stdout)
            if match:
                return int(match.group(1)), int(match.group(2))
    except Exception as e:
        logger.debug(f"Error querying subdev {subdev_path}: {e}")
    return 0, 0


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
    
    CRITICAL: Uses READ-ONLY queries for devices with active pipelines
    to avoid `rkcif_s_fmt_vid_cap_mplane queue busy` errors and crashes.
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
        self._active_pipelines: Set[str] = set()  # Track devices with active pipelines
    
    def mark_pipeline_active(self, input_id: str) -> None:
        """Mark a device as having an active pipeline.
        
        When a pipeline is active, we use read-only queries to avoid
        interfering with the running stream.
        """
        self._active_pipelines.add(input_id)
        logger.debug(f"Marked {input_id} as having active pipeline")
    
    def mark_pipeline_inactive(self, input_id: str) -> None:
        """Mark a device as no longer having an active pipeline."""
        self._active_pipelines.discard(input_id)
        logger.debug(f"Marked {input_id} as inactive")
        
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
            
        CRITICAL: For devices with active pipelines, we use READ-ONLY queries
        to avoid interfering with the running stream and causing crashes.
        """
        loop = asyncio.get_event_loop()
        device = cam_config.device
        
        # Check if this device has an active pipeline
        has_active_pipeline = input_id in self._active_pipelines
        
        if has_active_pipeline:
            # USE READ-ONLY QUERY - don't reinitialize or set format!
            # This prevents "queue busy" errors and kernel crashes
            subdev = RKCIF_SUBDEV_MAP_READONLY.get(device)
            if subdev:
                # Query subdev directly without setting format
                width, height = await loop.run_in_executor(
                    None,
                    lambda: _get_subdev_resolution_readonly(subdev)
                )
                has_signal = width > 640 and height > 480
                caps = {
                    'has_signal': has_signal,
                    'width': width,
                    'height': height,
                    'format': 'UYVY',  # rkcif devices use UYVY (LT6911 bridges)
                }
            else:
                # hdmirx or other device - just get capabilities without init
                caps = await loop.run_in_executor(
                    None,
                    lambda: get_device_capabilities(device)
                )
            logger.debug(f"Read-only check for {input_id} (pipeline active): {caps.get('width')}x{caps.get('height')}")
        else:
            # No active pipeline - safe to initialize if needed
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

