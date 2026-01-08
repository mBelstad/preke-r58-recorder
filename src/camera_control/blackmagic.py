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
        self.timeout = 2.0  # Reduced for faster response
        self._http_client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with connection pooling for speed."""
        if self._http_client is None:
            # Use connection pooling for better performance
            limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
            self._http_client = httpx.AsyncClient(
                timeout=self.timeout,
                limits=limits,
                http2=True  # Use HTTP/2 if available
            )
        return self._http_client
    
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
    
    async def set_focus(self, mode: str, value: Optional[float] = None) -> bool:
        """Set focus mode and value.
        
        Args:
            mode: 'auto' or 'manual'
            value: Focus value (0.0-1.0) for manual mode
        
        Returns:
            True if successful, False otherwise
        """
        try:
            payload = {"mode": mode}
            if mode == "manual" and value is not None:
                payload["value"] = value
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.put(
                    f"{self.base_url}/camera/0/focus",
                    json=payload
                )
                
                if response.status_code == 200:
                    logger.info(f"Set focus on {self.name}: {mode}" + (f"={value}" if value else ""))
                    return True
                else:
                    logger.error(f"Failed to set focus on {self.name}: HTTP {response.status_code}")
                    return False
        except Exception as e:
            logger.error(f"Error setting focus on {self.name}: {e}")
            return False
    
    async def set_iris(self, mode: str, value: Optional[float] = None) -> bool:
        """Set iris mode and value.
        
        Args:
            mode: 'auto' or 'manual'
            value: Iris value (f-stop) for manual mode
        
        Returns:
            True if successful, False otherwise
        """
        try:
            payload = {"mode": mode}
            if mode == "manual" and value is not None:
                payload["value"] = value
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.put(
                    f"{self.base_url}/camera/0/iris",
                    json=payload
                )
                
                if response.status_code == 200:
                    logger.info(f"Set iris on {self.name}: {mode}" + (f"={value}" if value else ""))
                    return True
                else:
                    logger.error(f"Failed to set iris on {self.name}: HTTP {response.status_code}")
                    return False
        except Exception as e:
            logger.error(f"Error setting iris on {self.name}: {e}")
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
            payload = {"mode": mode}
            if mode == "manual" and temperature is not None:
                payload["temperature"] = temperature
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.put(
                    f"{self.base_url}/camera/0/whiteBalance",
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
    
    async def set_gain(self, value: float) -> bool:
        """Set gain value.
        
        Args:
            value: Gain in dB
        
        Returns:
            True if successful, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.put(
                    f"{self.base_url}/camera/0/gain",
                    json={"value": value}
                )
                
                if response.status_code == 200:
                    logger.info(f"Set gain on {self.name}: {value}dB")
                    return True
                else:
                    logger.error(f"Failed to set gain on {self.name}: HTTP {response.status_code}")
                    return False
        except Exception as e:
            logger.error(f"Error setting gain on {self.name}: {e}")
            return False
    
    async def set_iso(self, value: int) -> bool:
        """Set ISO value.
        
        Args:
            value: ISO value (e.g., 400, 800, 1600)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.put(
                    f"{self.base_url}/camera/0/iso",
                    json={"value": value}
                )
                
                if response.status_code == 200:
                    logger.info(f"Set ISO on {self.name}: {value}")
                    return True
                else:
                    logger.error(f"Failed to set ISO on {self.name}: HTTP {response.status_code}")
                    return False
        except Exception as e:
            logger.error(f"Error setting ISO on {self.name}: {e}")
            return False
    
    async def set_shutter(self, value: float) -> bool:
        """Set shutter speed.
        
        Args:
            value: Shutter speed in seconds (e.g., 1/60 = 0.0167)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.put(
                    f"{self.base_url}/camera/0/shutter",
                    json={"value": value}
                )
                
                if response.status_code == 200:
                    logger.info(f"Set shutter on {self.name}: {value}s")
                    return True
                else:
                    logger.error(f"Failed to set shutter on {self.name}: HTTP {response.status_code}")
                    return False
        except Exception as e:
            logger.error(f"Error setting shutter on {self.name}: {e}")
            return False
    
    async def set_color_correction(self, settings: dict) -> bool:
        """Set color correction parameters.
        
        Args:
            settings: Dict with color correction parameters:
                - lift: [r, g, b] (optional)
                - gamma: [r, g, b] (optional)
                - gain: [r, g, b] (optional)
                - offset: [r, g, b] (optional)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.put(
                    f"{self.base_url}/camera/0/colorCorrection",
                    json=settings
                )
                
                if response.status_code == 200:
                    logger.info(f"Set color correction on {self.name}")
                    return True
                else:
                    logger.error(f"Failed to set color correction on {self.name}: HTTP {response.status_code}")
                    return False
        except Exception as e:
            logger.error(f"Error setting color correction on {self.name}: {e}")
            return False
    
    async def get_settings(self) -> Optional[dict]:
        """Get all camera settings.
        
        Returns:
            Dict with current camera settings, None on error
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Get camera info endpoint
                response = await client.get(f"{self.base_url}/camera/0")
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Failed to get settings from {self.name}: HTTP {response.status_code}")
                    return None
        except Exception as e:
            logger.error(f"Error getting settings from {self.name}: {e}")
            return None

