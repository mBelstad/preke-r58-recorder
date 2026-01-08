"""Companion Bridge Service

Bridges existing Companion modules (like Sony VISCA) to work with R58 API.
This allows using standard Companion modules while maintaining centralized control.
"""
import asyncio
import logging
import socket
import json
from typing import Dict, Any, Optional
from pathlib import Path
import httpx
import yaml

logger = logging.getLogger(__name__)


class CompanionBridge:
    """Bridge service that translates Companion module commands to R58 API calls.
    
    Supports:
    - VISCA over UDP (for Sony VISCA module → OBSbot cameras)
    - HTTP commands (for HTTP module → any camera via R58 API)
    """
    
    def __init__(
        self,
        r58_api_url: str = "http://localhost:8000",
        visca_port: int = 52381,
        http_port: int = 8080
    ):
        """Initialize bridge service.
        
        Args:
            r58_api_url: Base URL for R58 API
            visca_port: UDP port to listen for VISCA commands
            http_port: HTTP port for bridge API
        """
        self.r58_api_url = r58_api_url.rstrip('/')
        self.visca_port = visca_port
        self.http_port = http_port
        self.camera_map: Dict[str, Dict[str, str]] = {}  # IP -> {name, type}
        self.running = False
        
    def load_camera_config(self, config_path: Optional[Path] = None):
        """Load camera configuration from config.yml to map IPs to camera names."""
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config.yml"
        
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            external_cameras = config.get("external_cameras", [])
            for cam in external_cameras:
                if cam.get("enabled", True):
                    ip = cam.get("ip")
                    if ip:
                        self.camera_map[ip] = {
                            "name": cam.get("name"),
                            "type": cam.get("type")
                        }
            
            logger.info(f"Loaded {len(self.camera_map)} cameras for bridge mapping")
        except Exception as e:
            logger.error(f"Failed to load camera config: {e}")
    
    def visca_to_api(self, visca_command: bytes, camera_ip: str) -> Optional[Dict[str, Any]]:
        """Translate VISCA command to R58 API call.
        
        Args:
            visca_command: Raw VISCA command bytes
            camera_ip: Source camera IP address
            
        Returns:
            API call dict or None if command not supported
        """
        if camera_ip not in self.camera_map:
            logger.warning(f"Unknown camera IP: {camera_ip}")
            return None
        
        camera_info = self.camera_map[camera_ip]
        camera_name = camera_info["name"]
        camera_type = camera_info["type"]
        
        # Parse VISCA command
        if len(visca_command) < 3:
            return None
        
        # VISCA command structure: 8x 01 [command] ... FF
        cmd_type = visca_command[2] if len(visca_command) > 2 else 0
        
        # PTZ commands (0x06 = Pan/Tilt, 0x04 = Zoom)
        if cmd_type == 0x06 and len(visca_command) >= 9:
            # Pan/Tilt command: 8x 01 06 01 VV WW 0Y 0Z FF
            pan_speed = visca_command[4] if len(visca_command) > 4 else 0
            tilt_speed = visca_command[5] if len(visca_command) > 5 else 0
            
            # Convert speed to normalized value (-1.0 to 1.0)
            pan = (pan_speed - 7) / 7.0 if pan_speed != 0 else 0
            tilt = (tilt_speed - 7) / 7.0 if tilt_speed != 0 else 0
            
            if camera_type == "obsbot_tail2":
                return {
                    "url": f"{self.r58_api_url}/api/v1/cameras/{camera_name}/settings/ptz",
                    "method": "PUT",
                    "body": {"pan": pan, "tilt": tilt, "zoom": 0}
                }
        
        elif cmd_type == 0x04 and len(visca_command) >= 5:
            # Zoom command: 8x 01 04 07 2p FF
            if visca_command[3] == 0x07:
                zoom_speed = visca_command[4] if len(visca_command) > 4 else 0
                zoom = (zoom_speed - 7) / 7.0 if zoom_speed != 0 else 0
                
                if camera_type == "obsbot_tail2":
                    return {
                        "url": f"{self.r58_api_url}/api/v1/cameras/{camera_name}/settings/ptz",
                        "method": "PUT",
                        "body": {"pan": 0, "tilt": 0, "zoom": zoom}
                    }
        
        # Focus commands (if supported)
        elif cmd_type == 0x04 and len(visca_command) >= 5:
            if visca_command[3] == 0x08:  # Focus command
                focus_speed = visca_command[4] if len(visca_command) > 4 else 0
                # Convert to normalized value
                focus_value = (focus_speed - 7) / 7.0 if focus_speed != 0 else 0.5
                
                return {
                    "url": f"{self.r58_api_url}/api/v1/cameras/{camera_name}/settings/focus",
                    "method": "PUT",
                    "body": {"mode": "manual", "value": focus_value}
                }
        
        return None
    
    async def handle_visca_command(
        self,
        command: bytes,
        client_addr: tuple,
        sock: socket.socket
    ):
        """Handle incoming VISCA command from Companion module.
        
        Args:
            command: VISCA command bytes
            client_addr: Client address (IP, port)
            sock: UDP socket for response
        """
        client_ip = client_addr[0]
        
        # Translate VISCA to API call
        api_call = self.visca_to_api(command, client_ip)
        
        if api_call:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.request(
                        api_call["method"],
                        api_call["url"],
                        json=api_call["body"],
                        timeout=5.0
                    )
                    
                    if response.is_success:
                        logger.info(f"VISCA command translated and executed: {api_call['url']}")
                        # Send VISCA acknowledgment
                        ack = bytes([0x90, 0x50, 0xFF])  # VISCA ACK
                        sock.sendto(ack, client_addr)
                    else:
                        logger.warning(f"API call failed: {response.status_code}")
                        # Send VISCA error
                        error = bytes([0x90, 0x60, 0xFF])  # VISCA ERROR
                        sock.sendto(error, client_addr)
            except Exception as e:
                logger.error(f"Error executing API call: {e}")
                error = bytes([0x90, 0x60, 0xFF])
                sock.sendto(error, client_addr)
        else:
            logger.debug(f"Unsupported VISCA command from {client_ip}")
            # Send VISCA error for unsupported commands
            error = bytes([0x90, 0x60, 0xFF])
            sock.sendto(error, client_addr)
    
    async def visca_server(self):
        """UDP server for receiving VISCA commands from Companion modules."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('0.0.0.0', self.visca_port))
        sock.setblocking(False)
        
        logger.info(f"VISCA bridge server listening on UDP port {self.visca_port}")
        
        loop = asyncio.get_event_loop()
        
        while self.running:
            try:
                data, addr = await loop.sock_recvfrom(sock, 1024)
                await self.handle_visca_command(data, addr, sock)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in VISCA server: {e}")
        
        sock.close()
    
    async def start(self):
        """Start bridge service."""
        self.load_camera_config()
        self.running = True
        
        # Start VISCA server
        await self.visca_server()
    
    async def stop(self):
        """Stop bridge service."""
        self.running = False


async def main():
    """Main entry point for bridge service."""
    bridge = CompanionBridge(
        r58_api_url="http://localhost:8000",
        visca_port=52381
    )
    
    try:
        await bridge.start()
    except KeyboardInterrupt:
        logger.info("Stopping bridge service...")
        await bridge.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
