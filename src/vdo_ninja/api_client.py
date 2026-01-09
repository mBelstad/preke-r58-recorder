"""
Minimal VDO.ninja HTTP API client for Companion/Stream Deck integration

Based on Companion-Ninja: https://github.com/steveseguin/Companion-Ninja
VDO.ninja HTTP API format: https://vdo.ninja/api/{apiID}/{action}
"""
import logging
import asyncio
from typing import Optional, Dict, Any, List
import httpx
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)


class VdoNinjaApiClient:
    """Simple HTTP client for VDO.ninja API"""
    
    _client: Optional[httpx.AsyncClient] = None
    _client_lock = asyncio.Lock()
    
    def __init__(self, api_key: str, api_url: str = "https://r58-vdo.itagenten.no"):
        """
        Initialize VDO.ninja API client
        
        Args:
            api_key: API key (must match &api= parameter in VDO.ninja URL)
            api_url: Base URL for VDO.ninja instance
        """
        self.api_key = api_key
        self.api_url = api_url.rstrip('/')
        self.base_url = f"{self.api_url}/api/{api_key}"
        self.timeout = 5.0
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with connection pooling"""
        async with self._client_lock:
            if self._client is None:
                self._client = httpx.AsyncClient(
                    timeout=self.timeout,
                    limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
                )
            return self._client
    
    async def close(self):
        """Close HTTP client"""
        async with self._client_lock:
            if self._client:
                await self._client.aclose()
                self._client = None
    
    async def switch_scene(self, scene_id: int) -> bool:
        """
        Switch to scene (0-8 or custom scene name)
        
        Args:
            scene_id: Scene number (0-8) or custom scene identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            client = await self._get_client()
            response = await client.post(
                f"{self.base_url}/scene/{scene_id}",
                timeout=self.timeout
            )
            response.raise_for_status()
            logger.info(f"Switched to scene {scene_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to switch scene {scene_id}: {e}")
            return False
    
    async def toggle_mute(self, guest_id: str) -> Optional[bool]:
        """
        Toggle microphone mute for a guest
        
        Args:
            guest_id: Guest stream ID or slot number
            
        Returns:
            New mute state (True/False) or None if failed
        """
        try:
            client = await self._get_client()
            response = await client.post(
                f"{self.base_url}/mic/{guest_id}",
                timeout=self.timeout
            )
            response.raise_for_status()
            # VDO.ninja returns "true" or "false" as text
            result = response.text.strip().lower()
            muted = result == "true"
            logger.info(f"Toggled mute for guest {guest_id}: {muted}")
            return muted
        except Exception as e:
            logger.error(f"Failed to toggle mute for guest {guest_id}: {e}")
            return None
    
    async def set_volume(self, guest_id: str, volume: int) -> bool:
        """
        Set volume for a guest (0-200)
        
        Args:
            guest_id: Guest stream ID or slot number
            volume: Volume level (0-200, where 100 = normal)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            volume = max(0, min(200, volume))  # Clamp to valid range
            client = await self._get_client()
            response = await client.post(
                f"{self.base_url}/volume/{guest_id}",
                params={"value": volume},
                timeout=self.timeout
            )
            response.raise_for_status()
            logger.info(f"Set volume for guest {guest_id} to {volume}")
            return True
        except Exception as e:
            logger.error(f"Failed to set volume for guest {guest_id}: {e}")
            return False
    
    async def start_recording(self) -> bool:
        """
        Start recording
        
        Returns:
            True if successful, False otherwise
        """
        try:
            client = await self._get_client()
            response = await client.post(
                f"{self.base_url}/record",
                params={"value": "true"},
                timeout=self.timeout
            )
            response.raise_for_status()
            logger.info("Started recording")
            return True
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            return False
    
    async def stop_recording(self) -> bool:
        """
        Stop recording
        
        Returns:
            True if successful, False otherwise
        """
        try:
            client = await self._get_client()
            response = await client.post(
                f"{self.base_url}/record",
                params={"value": "false"},
                timeout=self.timeout
            )
            response.raise_for_status()
            logger.info("Stopped recording")
            return True
        except Exception as e:
            logger.error(f"Failed to stop recording: {e}")
            return False
    
    async def get_guests(self) -> List[Dict[str, Any]]:
        """
        Get list of connected guests
        
        Returns:
            List of guest information dictionaries
        """
        try:
            client = await self._get_client()
            response = await client.get(
                f"{self.base_url}/getGuestList",
                timeout=self.timeout
            )
            response.raise_for_status()
            # VDO.ninja returns JSON array of guest objects
            guests = response.json()
            logger.debug(f"Retrieved {len(guests)} guests")
            return guests if isinstance(guests, list) else []
        except Exception as e:
            logger.error(f"Failed to get guest list: {e}")
            return []


def get_vdo_ninja_client_from_config(config_path: Optional[str] = None) -> Optional[VdoNinjaApiClient]:
    """
    Create VDO.ninja API client from config.yml
    
    Args:
        config_path: Path to config.yml (defaults to ./config.yml)
        
    Returns:
        VdoNinjaApiClient instance or None if config not found/invalid
    """
    if config_path is None:
        config_path = Path(__file__).parent.parent.parent / "config.yml"
    else:
        config_path = Path(config_path)
    
    if not config_path.exists():
        logger.warning(f"Config file not found: {config_path}")
        return None
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        vdo_config = config.get('vdo_ninja', {})
        api_key = vdo_config.get('api_key')
        api_url = vdo_config.get('api_url', 'https://r58-vdo.itagenten.no')
        
        if not api_key:
            logger.warning("VDO.ninja API key not found in config")
            return None
        
        return VdoNinjaApiClient(api_key=api_key, api_url=api_url)
    except Exception as e:
        logger.error(f"Failed to load VDO.ninja config: {e}")
        return None
