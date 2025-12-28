"""Camera control manager to coordinate external camera triggers."""
import logging
from typing import Dict, List, Optional, Any
import asyncio

from .blackmagic import BlackmagicCamera
from .obsbot import ObsbotTail2

logger = logging.getLogger(__name__)


class CameraControlManager:
    """Manages external camera control for synchronized recording."""
    
    def __init__(self, external_cameras_config: List[Dict[str, Any]]):
        """Initialize camera control manager.
        
        Args:
            external_cameras_config: List of camera configurations
                Each dict should have: name, type, ip, enabled, and optional port
        """
        self.cameras: Dict[str, Any] = {}
        self._initialize_cameras(external_cameras_config)
    
    def _initialize_cameras(self, config: List[Dict[str, Any]]):
        """Initialize camera controllers from configuration."""
        for cam_config in config:
            if not cam_config.get("enabled", True):
                logger.info(f"Skipping disabled camera: {cam_config.get('name')}")
                continue
            
            cam_type = cam_config.get("type")
            cam_name = cam_config.get("name")
            cam_ip = cam_config.get("ip")
            
            if not all([cam_type, cam_name, cam_ip]):
                logger.error(f"Invalid camera config: {cam_config}")
                continue
            
            try:
                if cam_type == "blackmagic":
                    port = cam_config.get("port", 80)
                    camera = BlackmagicCamera(ip=cam_ip, name=cam_name, port=port)
                    self.cameras[cam_name] = camera
                    logger.info(f"Initialized Blackmagic camera: {cam_name} at {cam_ip}")
                
                elif cam_type == "obsbot_tail2":
                    port = cam_config.get("port", 52381)
                    camera = ObsbotTail2(ip=cam_ip, name=cam_name, port=port)
                    self.cameras[cam_name] = camera
                    logger.info(f"Initialized Obsbot Tail 2 camera: {cam_name} at {cam_ip}")
                
                else:
                    logger.error(f"Unknown camera type: {cam_type}")
            
            except Exception as e:
                logger.error(f"Failed to initialize camera {cam_name}: {e}")
    
    async def start_all_recordings(self, session_id: Optional[str] = None) -> Dict[str, bool]:
        """Start recording on all external cameras.
        
        Args:
            session_id: Optional session ID to use as clip name for Blackmagic cameras
        
        Returns:
            Dict mapping camera name to success status
        """
        if not self.cameras:
            logger.info("No external cameras configured")
            return {}
        
        logger.info(f"Starting recording on {len(self.cameras)} external camera(s)")
        
        # Start all cameras in parallel
        tasks = []
        camera_names = []
        
        for name, camera in self.cameras.items():
            if isinstance(camera, BlackmagicCamera):
                # Use session_id as clip name for Blackmagic cameras
                tasks.append(camera.start_recording(clip_name=session_id))
            else:
                tasks.append(camera.start_recording())
            camera_names.append(name)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Build result dict
        result_dict = {}
        for name, result in zip(camera_names, results):
            if isinstance(result, Exception):
                logger.error(f"Exception starting {name}: {result}")
                result_dict[name] = False
            else:
                result_dict[name] = result
        
        # Log summary
        success_count = sum(1 for v in result_dict.values() if v)
        logger.info(
            f"External camera start results: {success_count}/{len(result_dict)} successful"
        )
        
        return result_dict
    
    async def stop_all_recordings(self) -> Dict[str, bool]:
        """Stop recording on all external cameras.
        
        Returns:
            Dict mapping camera name to success status
        """
        if not self.cameras:
            logger.info("No external cameras configured")
            return {}
        
        logger.info(f"Stopping recording on {len(self.cameras)} external camera(s)")
        
        # Stop all cameras in parallel
        tasks = []
        camera_names = []
        
        for name, camera in self.cameras.items():
            tasks.append(camera.stop_recording())
            camera_names.append(name)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Build result dict
        result_dict = {}
        for name, result in zip(camera_names, results):
            if isinstance(result, Exception):
                logger.error(f"Exception stopping {name}: {result}")
                result_dict[name] = False
            else:
                result_dict[name] = result
        
        # Log summary
        success_count = sum(1 for v in result_dict.values() if v)
        logger.info(
            f"External camera stop results: {success_count}/{len(result_dict)} successful"
        )
        
        return result_dict
    
    async def check_connections(self) -> Dict[str, bool]:
        """Check connectivity to all external cameras.
        
        Returns:
            Dict mapping camera name to connection status
        """
        if not self.cameras:
            return {}
        
        tasks = []
        camera_names = []
        
        for name, camera in self.cameras.items():
            tasks.append(camera.check_connection())
            camera_names.append(name)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        result_dict = {}
        for name, result in zip(camera_names, results):
            if isinstance(result, Exception):
                result_dict[name] = False
            else:
                result_dict[name] = result
        
        return result_dict
    
    def get_camera_count(self) -> int:
        """Get number of configured external cameras."""
        return len(self.cameras)

