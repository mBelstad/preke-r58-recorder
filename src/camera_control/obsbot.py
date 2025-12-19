"""Obsbot Tail 2 camera control via VISCA over IP."""
import logging
import socket
from typing import Optional

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
        
        # VISCA commands for Obsbot Tail 2
        # Format: 8x 01 04 18 0y FF
        # where x = camera address (1), y = command (2=start, 3=stop)
        self.CMD_START_RECORDING = bytes([0x81, 0x01, 0x04, 0x18, 0x02, 0xFF])
        self.CMD_STOP_RECORDING = bytes([0x81, 0x01, 0x04, 0x18, 0x03, 0xFF])
    
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

