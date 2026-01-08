"""Sony camera control via REST API and VISCA over IP.

Supports Sony FX30 and other Sony cameras with network control.
Uses Sony's Camera Remote API (REST) and VISCA protocol for PTZ.
"""
import logging
from typing import Optional
import httpx
import socket
import asyncio

logger = logging.getLogger(__name__)


class SonyCamera:
    """Control Sony cameras (FX30, etc.) via REST API and VISCA.
    
    Sony cameras support:
    - REST API for most controls (focus, ISO, shutter, etc.)
    - VISCA over IP for PTZ (if supported)
    """
    
    def __init__(self, ip: str, name: str, port: int = 80, visca_port: int = 52381):
        """Initialize Sony camera controller.
        
        Args:
            ip: Camera IP address
            name: Human-readable camera name
            port: HTTP REST API port (default: 80)
            visca_port: VISCA UDP port (default: 52381)
        """
        self.ip = ip
        self.name = name
        self.port = port
        self.visca_port = visca_port
        self.base_url = f"http://{ip}:{port}"
        self.timeout = 2.0  # Fast timeout for responsiveness
        self._http_client: Optional[httpx.AsyncClient] = None
        self._visca_socket: Optional[socket.socket] = None
        
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with connection pooling."""
        if self._http_client is None:
            # Use connection pooling for speed
            limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
            self._http_client = httpx.AsyncClient(
                timeout=self.timeout,
                limits=limits,
                http2=True  # Use HTTP/2 if available for better performance
            )
        return self._http_client
    
    async def _send_visca(self, command: bytes) -> bool:
        """Send VISCA command over UDP (fast, no response needed for PTZ)."""
        try:
            if self._visca_socket is None:
                self._visca_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self._visca_socket.settimeout(0.1)  # Very short timeout
            
            self._visca_socket.sendto(command, (self.ip, self.visca_port))
            return True
        except Exception as e:
            logger.error(f"Error sending VISCA to {self.name}: {e}")
            return False
    
    async def check_connection(self) -> bool:
        """Quick connection check."""
        try:
            client = await self._get_client()
            # Fast health check endpoint (if available)
            response = await client.get(f"{self.base_url}/", timeout=1.0)
            return response.status_code < 500
        except:
            return False
    
    async def get_settings(self) -> dict:
        """Get current camera settings (cached for speed)."""
        # For now, return empty - would need Sony API endpoint
        return {}
    
    # Focus Control
    async def set_focus(self, mode: str, value: Optional[float] = None) -> bool:
        """Set focus mode and value.
        
        Args:
            mode: 'auto' or 'manual'
            value: Focus value (0.0-1.0) for manual mode
        """
        try:
            client = await self._get_client()
            # Sony API endpoint (adjust based on actual API)
            payload = {"focusMode": mode}
            if mode == "manual" and value is not None:
                payload["focusPosition"] = value
            
            response = await client.put(
                f"{self.base_url}/camera/focus",
                json=payload,
                timeout=self.timeout
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error setting focus on {self.name}: {e}")
            return False
    
    # Exposure Control
    async def set_exposure(self, mode: str, value: Optional[float] = None) -> bool:
        """Set exposure mode and value.
        
        Args:
            mode: 'auto' or 'manual'
            value: Exposure value (0.0-1.0) for manual mode
        """
        try:
            client = await self._get_client()
            payload = {"exposureMode": mode}
            if mode == "manual" and value is not None:
                payload["exposureValue"] = value
            
            response = await client.put(
                f"{self.base_url}/camera/exposure",
                json=payload,
                timeout=self.timeout
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error setting exposure on {self.name}: {e}")
            return False
    
    # ISO Control
    async def set_iso(self, value: int) -> bool:
        """Set ISO value.
        
        Args:
            value: ISO value (100-25600)
        """
        try:
            client = await self._get_client()
            response = await client.put(
                f"{self.base_url}/camera/iso",
                json={"iso": value},
                timeout=self.timeout
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error setting ISO on {self.name}: {e}")
            return False
    
    # Shutter Control
    async def set_shutter(self, value: float) -> bool:
        """Set shutter speed.
        
        Args:
            value: Shutter speed in seconds (e.g., 0.016 for 1/60)
        """
        try:
            client = await self._get_client()
            response = await client.put(
                f"{self.base_url}/camera/shutter",
                json={"shutterSpeed": value},
                timeout=self.timeout
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error setting shutter on {self.name}: {e}")
            return False
    
    # White Balance
    async def set_white_balance(self, mode: str, temperature: Optional[int] = None) -> bool:
        """Set white balance.
        
        Args:
            mode: 'auto', 'manual', or 'preset'
            temperature: Color temperature (2000-10000) for manual mode
        """
        try:
            client = await self._get_client()
            payload = {"whiteBalanceMode": mode}
            if mode == "manual" and temperature:
                payload["colorTemperature"] = temperature
            
            response = await client.put(
                f"{self.base_url}/camera/whiteBalance",
                json=payload,
                timeout=self.timeout
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error setting white balance on {self.name}: {e}")
            return False
    
    # PTZ Control (VISCA - fast UDP)
    async def ptz_move(self, pan: float, tilt: float, zoom: float) -> bool:
        """Move PTZ camera (fast VISCA UDP).
        
        Args:
            pan: Pan speed (-1.0 to 1.0, 0 = stop)
            tilt: Tilt speed (-1.0 to 1.0, 0 = stop)
            zoom: Zoom speed (-1.0 to 1.0, 0 = stop)
        """
        try:
            # Convert to VISCA speeds (0x01-0x18)
            pan_speed = max(0x01, min(0x18, int(abs(pan) * 0x18))) if pan != 0 else 0
            tilt_speed = max(0x01, min(0x18, int(abs(tilt) * 0x18))) if tilt != 0 else 0
            
            # Direction: 0x01 = left/up, 0x02 = right/down, 0x03 = stop
            pan_dir = 0x01 if pan < 0 else 0x02 if pan > 0 else 0x03
            tilt_dir = 0x01 if tilt < 0 else 0x02 if tilt > 0 else 0x03
            
            # Build VISCA pan/tilt command
            if pan != 0 or tilt != 0:
                cmd = bytes([0x81, 0x01, 0x06, 0x01, pan_speed, tilt_speed, pan_dir, tilt_dir, 0xFF])
                await self._send_visca(cmd)
            
            # Zoom command (separate)
            if zoom != 0:
                zoom_speed = max(0x01, min(0x07, int(abs(zoom) * 0x07)))
                zoom_dir = 0x20 if zoom > 0 else 0x30
                zoom_cmd = bytes([0x81, 0x01, 0x04, 0x07, zoom_dir | zoom_speed, 0xFF])
                await self._send_visca(zoom_cmd)
            elif pan == 0 and tilt == 0:
                # Stop zoom
                zoom_cmd = bytes([0x81, 0x01, 0x04, 0x07, 0x00, 0xFF])
                await self._send_visca(zoom_cmd)
            
            return True  # VISCA is fire-and-forget, assume success
        except Exception as e:
            logger.error(f"Error moving PTZ on {self.name}: {e}")
            return False
    
    async def ptz_preset(self, preset_id: int) -> bool:
        """Recall PTZ preset (fast VISCA).
        
        Args:
            preset_id: Preset number (0-15)
        """
        try:
            # VISCA preset recall: 8x 01 04 3F 0p 0q FF
            # p = preset number high nibble, q = low nibble
            preset_high = (preset_id >> 4) & 0x0F
            preset_low = preset_id & 0x0F
            cmd = bytes([0x81, 0x01, 0x04, 0x3F, preset_high, preset_low, 0xFF])
            return await self._send_visca(cmd)
        except Exception as e:
            logger.error(f"Error recalling preset on {self.name}: {e}")
            return False
    
    async def close(self):
        """Close connections."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
        if self._visca_socket:
            self._visca_socket.close()
            self._visca_socket = None
