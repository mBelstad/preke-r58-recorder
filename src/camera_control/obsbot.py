"""Obsbot Tail 2 camera control via VISCA over IP."""
import logging
import socket
from typing import Optional
import httpx

logger = logging.getLogger(__name__)


class ObsbotTail2:
    """Control Obsbot Tail 2 camera via VISCA over IP (UDP).
    
    VISCA protocol documentation:
    - Standard VISCA commands for PTZ cameras
    - Obsbot uses UDP port 52381 for VISCA control
    """
    
    def __init__(self, ip: str, name: str, port: int = 52381):
        """Initialize Obsbot camera controller.
        
        Args:
            ip: Camera IP address
            name: Human-readable camera name
            port: VISCA UDP port (default: 52381)
        """
        self.ip = ip
        self.name = name
        self.port = port
        self.timeout = 2.0
        self.http_port = 80  # HTTP API port (if available)
        self.http_timeout = 5.0
        
        # VISCA commands for Obsbot Tail 2
        # Format: 8x 01 04 18 0y FF
        # where x = camera address (1), y = command (2=start, 3=stop)
        self.CMD_START_RECORDING = bytes([0x81, 0x01, 0x04, 0x18, 0x02, 0xFF])
        self.CMD_STOP_RECORDING = bytes([0x81, 0x01, 0x04, 0x18, 0x03, 0xFF])
        
        # VISCA PTZ commands
        # Pan/Tilt: 8x 01 06 01 VV WW 0Y 0Z FF
        # Zoom: 8x 01 04 07 2p FF
        # where VV/WW = pan/tilt speed, YZ = pan/tilt position
    
    async def start_recording(self) -> bool:
        """Start recording on the camera.
        
        Returns:
            True if successful, False otherwise
        """
        return await self._send_command(self.CMD_START_RECORDING, "start recording")
    
    async def stop_recording(self) -> bool:
        """Stop recording on the camera.
        
        Returns:
            True if successful, False otherwise
        """
        return await self._send_command(self.CMD_STOP_RECORDING, "stop recording")
    
    async def _send_command(self, command: bytes, action: str) -> bool:
        """Send a VISCA command to the camera.
        
        Args:
            command: VISCA command bytes
            action: Human-readable action description
        
        Returns:
            True if successful, False otherwise
        """
        sock = None
        try:
            # Create UDP socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(self.timeout)
            
            # Send command
            sock.sendto(command, (self.ip, self.port))
            logger.info(f"Sent {action} command to {self.name} ({self.ip}:{self.port})")
            
            # Wait for ACK (optional - some cameras don't send ACK for UDP)
            try:
                response, _ = sock.recvfrom(1024)
                if len(response) > 0:
                    # Check for ACK (0x90 0x4x 0xFF) or completion (0x90 0x5x 0xFF)
                    if response[0] == 0x90 and (response[1] & 0xF0 in [0x40, 0x50]):
                        logger.debug(f"Received ACK from {self.name}")
                        return True
                    else:
                        logger.warning(f"Unexpected response from {self.name}: {response.hex()}")
                        return True  # Still consider it successful if we got a response
            except socket.timeout:
                # No response - this is normal for some cameras over UDP
                logger.debug(f"No ACK received from {self.name} (timeout)")
                return True  # Consider it successful if command was sent
            
            return True
        
        except Exception as e:
            logger.error(f"Error sending {action} to {self.name} ({self.ip}): {e}")
            return False
        
        finally:
            if sock:
                sock.close()
    
    async def check_connection(self) -> bool:
        """Check if camera is reachable via UDP.
        
        Note: This sends a simple inquiry command to test connectivity.
        
        Returns:
            True if camera responds, False otherwise
        """
        sock = None
        try:
            # Send CAM_VersionInq command (0x81 0x09 0x00 0x02 0xFF)
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(1.0)
            
            inquiry = bytes([0x81, 0x09, 0x00, 0x02, 0xFF])
            sock.sendto(inquiry, (self.ip, self.port))
            
            # Wait for response
            try:
                response, _ = sock.recvfrom(1024)
                return len(response) > 0
            except socket.timeout:
                return False
        
        except Exception as e:
            logger.debug(f"Connection check failed for {self.name}: {e}")
            return False
        
        finally:
            if sock:
                sock.close()
    
    async def set_focus(self, mode: str, value: Optional[float] = None) -> bool:
        """Set focus mode and value.
        
        Args:
            mode: 'auto' or 'manual'
            value: Focus value (0.0-1.0) for manual mode
        
        Returns:
            True if successful, False otherwise
        """
        # Try HTTP API first, fallback to VISCA if needed
        try:
            async with httpx.AsyncClient(timeout=self.http_timeout) as client:
                payload = {"mode": mode}
                if mode == "manual" and value is not None:
                    payload["value"] = value
                
                response = await client.put(
                    f"http://{self.ip}:{self.http_port}/api/camera/focus",
                    json=payload
                )
                
                if response.status_code == 200:
                    logger.info(f"Set focus on {self.name}: {mode}" + (f"={value}" if value else ""))
                    return True
        except Exception as e:
            logger.debug(f"HTTP focus control failed for {self.name}, trying VISCA: {e}")
        
        # Fallback: VISCA command for focus (if supported)
        # Note: Standard VISCA doesn't have direct focus control, this may need camera-specific commands
        logger.warning(f"Focus control via HTTP not available for {self.name}, VISCA fallback not implemented")
        return False
    
    async def set_exposure(self, mode: str, value: Optional[float] = None) -> bool:
        """Set exposure mode and value.
        
        Args:
            mode: 'auto' or 'manual'
            value: Exposure value for manual mode
        
        Returns:
            True if successful, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=self.http_timeout) as client:
                payload = {"mode": mode}
                if mode == "manual" and value is not None:
                    payload["value"] = value
                
                response = await client.put(
                    f"http://{self.ip}:{self.http_port}/api/camera/exposure",
                    json=payload
                )
                
                if response.status_code == 200:
                    logger.info(f"Set exposure on {self.name}: {mode}" + (f"={value}" if value else ""))
                    return True
                else:
                    logger.error(f"Failed to set exposure on {self.name}: HTTP {response.status_code}")
                    return False
        except Exception as e:
            logger.error(f"Error setting exposure on {self.name}: {e}")
            return False
    
    async def set_white_balance(self, mode: str, temperature: Optional[int] = None) -> bool:
        """Set white balance mode and temperature.
        
        Args:
            mode: 'auto', 'manual', or 'preset'
            temperature: Color temperature in Kelvin for manual mode
        
        Returns:
            True if successful, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=self.http_timeout) as client:
                payload = {"mode": mode}
                if mode == "manual" and temperature is not None:
                    payload["temperature"] = temperature
                
                response = await client.put(
                    f"http://{self.ip}:{self.http_port}/api/camera/whiteBalance",
                    json=payload
                )
                
                if response.status_code == 200:
                    logger.info(f"Set white balance on {self.name}: {mode}" + (f"={temperature}K" if temperature else ""))
                    return True
                else:
                    logger.error(f"Failed to set white balance on {self.name}: HTTP {response.status_code}")
                    return False
        except Exception as e:
            logger.error(f"Error setting white balance on {self.name}: {e}")
            return False
    
    async def ptz_move(self, pan: float, tilt: float, zoom: float) -> bool:
        """Move PTZ camera (pan, tilt, zoom).
        
        Args:
            pan: Pan speed (-1.0 to 1.0, 0 = stop)
            tilt: Tilt speed (-1.0 to 1.0, 0 = stop)
            zoom: Zoom speed (-1.0 to 1.0, 0 = stop)
        
        Returns:
            True if successful, False otherwise
        """
        # VISCA PTZ command format
        # Pan/Tilt: 8x 01 06 01 VV WW 0Y 0Z FF
        # VV = pan speed (0x01-0x18), WW = tilt speed (0x01-0x18)
        # YZ = pan/tilt position (0x00-0xFF)
        
        try:
            # Convert normalized values to VISCA speeds (0x01-0x18)
            pan_speed = max(0x01, min(0x18, int(abs(pan) * 0x18)))
            tilt_speed = max(0x01, min(0x18, int(abs(tilt) * 0x18)))
            
            # Direction bits: 0x01 = left/up, 0x02 = right/down
            pan_dir = 0x01 if pan < 0 else 0x02 if pan > 0 else 0x03  # 0x03 = stop
            tilt_dir = 0x01 if tilt < 0 else 0x02 if tilt > 0 else 0x03
            
            # Build VISCA command
            if pan == 0 and tilt == 0:
                # Stop pan/tilt
                cmd = bytes([0x81, 0x01, 0x06, 0x01, 0x00, 0x00, 0x03, 0x03, 0xFF])
            else:
                cmd = bytes([0x81, 0x01, 0x06, 0x01, pan_speed, tilt_speed, pan_dir, tilt_dir, 0xFF])
            
            # Zoom command (separate)
            if zoom != 0:
                zoom_speed = max(0x01, min(0x07, int(abs(zoom) * 0x07)))
                zoom_dir = 0x20 if zoom > 0 else 0x30  # 0x20 = tele, 0x30 = wide
                zoom_cmd = bytes([0x81, 0x01, 0x04, 0x07, zoom_dir | zoom_speed, 0xFF])
            else:
                zoom_cmd = bytes([0x81, 0x01, 0x04, 0x07, 0x00, 0xFF])  # Stop zoom
            
            # Send commands
            result1 = await self._send_command(cmd, "PTZ move")
            result2 = await self._send_command(zoom_cmd, "zoom")
            
            return result1 and result2
            
        except Exception as e:
            logger.error(f"Error moving PTZ on {self.name}: {e}")
            return False
    
    async def ptz_preset(self, preset_id: int) -> bool:
        """Recall a PTZ preset.
        
        Args:
            preset_id: Preset number (0-15)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # VISCA preset recall: 8x 01 04 3F 02 0p FF
            # where p = preset number (0x00-0x0F)
            preset_byte = min(0x0F, max(0x00, preset_id))
            cmd = bytes([0x81, 0x01, 0x04, 0x3F, 0x02, preset_byte, 0xFF])
            
            return await self._send_command(cmd, f"PTZ preset {preset_id}")
        except Exception as e:
            logger.error(f"Error recalling preset on {self.name}: {e}")
            return False
    
    async def get_settings(self) -> Optional[dict]:
        """Get all camera settings.
        
        Returns:
            Dict with current camera settings, None on error
        """
        try:
            async with httpx.AsyncClient(timeout=self.http_timeout) as client:
                response = await client.get(f"http://{self.ip}:{self.http_port}/api/camera/settings")
                
                if response.status_code == 200:
                    return response.json()
                else:
                    # Fallback: return basic status
                    logger.debug(f"HTTP settings not available for {self.name}, returning basic status")
                    return {
                        "connected": await self.check_connection(),
                        "name": self.name,
                        "ip": self.ip
                    }
        except Exception as e:
            logger.debug(f"Error getting settings from {self.name}: {e}")
            # Return basic status
            return {
                "connected": await self.check_connection(),
                "name": self.name,
                "ip": self.ip
            }

