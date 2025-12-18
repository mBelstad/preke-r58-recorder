"""Blackmagic Design camera control via REST API."""
import logging
from typing import Optional
import httpx

logger = logging.getLogger(__name__)


class BlackmagicCamera:
    """Control Blackmagic Design Studio cameras via REST API.
    
    Supports Studio Camera 4K Pro and Plus G2 models.
    API documentation: https://documents.blackmagicdesign.com/DeveloperManuals/BlackmagicCameraControl.pdf
    """
    
    def __init__(self, ip: str, name: str, port: int = 80):
        """Initialize Blackmagic camera controller.
        
        Args:
            ip: Camera IP address
            name: Human-readable camera name
            port: HTTP port (default: 80)
        """
        self.ip = ip
        self.name = name
        self.port = port
        self.base_url = f"http://{ip}:{port}/control/api/v1"
        self.timeout = 5.0
    
    async def start_recording(self, clip_name: Optional[str] = None) -> bool:
        """Start recording on the camera.
        
        Args:
            clip_name: Optional clip name (will be auto-generated if not provided)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            payload = {}
            if clip_name:
                payload["clipName"] = clip_name
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/transports/0/record",
                    json=payload
                )
                
                if response.status_code == 200:
                    logger.info(f"Started recording on {self.name} ({self.ip})")
                    return True
                else:
                    logger.error(
                        f"Failed to start recording on {self.name}: "
                        f"HTTP {response.status_code} - {response.text}"
                    )
                    return False
        
        except Exception as e:
            logger.error(f"Error starting recording on {self.name} ({self.ip}): {e}")
            return False
    
    async def stop_recording(self) -> bool:
        """Stop recording on the camera.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/transports/0/stop"
                )
                
                if response.status_code == 200:
                    logger.info(f"Stopped recording on {self.name} ({self.ip})")
                    return True
                else:
                    logger.error(
                        f"Failed to stop recording on {self.name}: "
                        f"HTTP {response.status_code} - {response.text}"
                    )
                    return False
        
        except Exception as e:
            logger.error(f"Error stopping recording on {self.name} ({self.ip}): {e}")
            return False
    
    async def get_status(self) -> Optional[dict]:
        """Get camera status.
        
        Returns:
            Status dict if successful, None otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/transports/0"
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(
                        f"Failed to get status from {self.name}: "
                        f"HTTP {response.status_code}"
                    )
                    return None
        
        except Exception as e:
            logger.error(f"Error getting status from {self.name} ({self.ip}): {e}")
            return None
    
    async def check_connection(self) -> bool:
        """Check if camera is reachable.
        
        Returns:
            True if camera responds, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(f"http://{self.ip}:{self.port}/")
                return response.status_code < 500
        except Exception:
            return False
