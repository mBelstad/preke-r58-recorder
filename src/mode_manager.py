"""Mode manager for switching between Recorder and VDO.ninja modes."""
import asyncio
import logging
import subprocess
import json
from typing import Dict, Optional, List
from pathlib import Path
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class ModeStatus:
    """Status information for a mode."""
    current_mode: str
    available_modes: List[str]
    recorder_services: Dict[str, str]  # service_name -> status
    vdoninja_services: Dict[str, str]  # service_name -> status
    can_switch: bool
    message: Optional[str] = None


class ModeManager:
    """Manages switching between Recorder and VDO.ninja modes.
    
    Recorder Mode:
    - preke-recorder ingest pipelines active (internal)
    - MediaMTX receives streams via RTSP
    - Used for recording and direct WHEP viewing
    
    VDO.ninja Mode:
    - raspberry.ninja publishers active (systemd services)
    - VDO.ninja signaling server receives streams
    - Used for full VDO.ninja mixer/director features
    """
    
    MODES = ["recorder", "vdoninja"]
    STATE_FILE = Path("/tmp/r58_mode_state.json")
    
    # VDO.ninja publisher services (systemd)
    VDONINJA_SERVICES = [
        "ninja-publish-cam1",
        "ninja-publish-cam2", 
        "ninja-publish-cam3",
    ]
    
    def __init__(self, ingest_manager=None, config=None):
        """Initialize mode manager.
        
        Args:
            ingest_manager: Reference to IngestManager for controlling recorder pipelines
            config: Application configuration object
        """
        self.ingest_manager = ingest_manager
        self.config = config
        self._current_mode: Optional[str] = None
        self._load_state()
    
    def _load_state(self):
        """Load mode state from file."""
        try:
            if self.STATE_FILE.exists():
                with open(self.STATE_FILE, 'r') as f:
                    data = json.load(f)
                    self._current_mode = data.get('mode', 'recorder')
                    logger.info(f"Loaded mode state: {self._current_mode}")
            else:
                # Default to recorder mode
                self._current_mode = 'recorder'
                self._save_state()
        except Exception as e:
            logger.error(f"Failed to load mode state: {e}")
            self._current_mode = 'recorder'
    
    def _save_state(self):
        """Save mode state to file."""
        try:
            self.STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(self.STATE_FILE, 'w') as f:
                json.dump({'mode': self._current_mode}, f)
            logger.info(f"Saved mode state: {self._current_mode}")
        except Exception as e:
            logger.error(f"Failed to save mode state: {e}")
    
    async def get_current_mode(self) -> str:
        """Get the current active mode."""
        if self._current_mode is None:
            self._load_state()
        return self._current_mode
    
    async def get_status(self) -> ModeStatus:
        """Get detailed status of both modes."""
        current_mode = await self.get_current_mode()
        
        # Check recorder services (ingest pipelines)
        recorder_services = {}
        if self.ingest_manager:
            for cam_id, state in self.ingest_manager.states.items():
                recorder_services[f"ingest-{cam_id}"] = state
        else:
            recorder_services = {"ingest": "unavailable"}
        
        # Check VDO.ninja services (systemd)
        vdoninja_services = {}
        for service in self.VDONINJA_SERVICES:
            status = await self._get_service_status(service)
            vdoninja_services[service] = status
        
        # Determine if we can switch
        can_switch = True
        message = None
        
        return ModeStatus(
            current_mode=current_mode,
            available_modes=self.MODES,
            recorder_services=recorder_services,
            vdoninja_services=vdoninja_services,
            can_switch=can_switch,
            message=message
        )
    
    async def switch_to_recorder(self) -> Dict[str, any]:
        """Switch to Recorder Mode.
        
        Returns:
            Dict with success status and message
        """
        logger.info("Switching to Recorder Mode...")
        
        try:
            # Stop VDO.ninja services
            await self._stop_vdoninja_services()
            
            # Wait a moment for services to stop and release devices
            await asyncio.sleep(2)
            
            # Start recorder services
            await self._start_recorder_services()
            
            # Update state
            self._current_mode = 'recorder'
            self._save_state()
            
            logger.info("Successfully switched to Recorder Mode")
            return {
                "success": True,
                "mode": "recorder",
                "message": "Switched to Recorder Mode. Cameras streaming to MediaMTX."
            }
        
        except Exception as e:
            logger.error(f"Failed to switch to Recorder Mode: {e}")
            return {
                "success": False,
                "mode": self._current_mode,
                "message": f"Failed to switch: {str(e)}"
            }
    
    async def switch_to_vdoninja(self) -> Dict[str, any]:
        """Switch to VDO.ninja Mode.
        
        Returns:
            Dict with success status and message
        """
        logger.info("Switching to VDO.ninja Mode...")
        
        try:
            # Stop recorder services
            await self._stop_recorder_services()
            
            # Wait a moment for pipelines to stop and release devices
            await asyncio.sleep(2)
            
            # Start VDO.ninja services
            await self._start_vdoninja_services()
            
            # Update state
            self._current_mode = 'vdoninja'
            self._save_state()
            
            logger.info("Successfully switched to VDO.ninja Mode")
            return {
                "success": True,
                "mode": "vdoninja",
                "message": "Switched to VDO.ninja Mode. Cameras publishing to VDO.ninja signaling."
            }
        
        except Exception as e:
            logger.error(f"Failed to switch to VDO.ninja Mode: {e}")
            return {
                "success": False,
                "mode": self._current_mode,
                "message": f"Failed to switch: {str(e)}"
            }
    
    async def _stop_recorder_services(self):
        """Stop recorder ingest pipelines."""
        if not self.ingest_manager:
            logger.warning("IngestManager not available, cannot stop recorder services")
            return
        
        logger.info("Stopping recorder ingest pipelines...")
        
        # Get list of cameras that are streaming
        streaming_cameras = [
            cam_id for cam_id, state in self.ingest_manager.states.items()
            if state == "streaming"
        ]
        
        # Stop each streaming camera
        for cam_id in streaming_cameras:
            logger.info(f"Stopping ingest for {cam_id}")
            self.ingest_manager.stop_ingest(cam_id)
        
        logger.info(f"Stopped {len(streaming_cameras)} recorder ingest pipelines")
    
    async def _start_recorder_services(self):
        """Start recorder ingest pipelines."""
        if not self.ingest_manager:
            logger.warning("IngestManager not available, cannot start recorder services")
            return
        
        logger.info("Starting recorder ingest pipelines...")
        
        # Get list of enabled cameras from config
        enabled_cameras = [
            cam_id for cam_id, cam_config in self.ingest_manager.config.cameras.items()
            if cam_config.enabled
        ]
        
        # Start each enabled camera
        started = 0
        for cam_id in enabled_cameras:
            logger.info(f"Starting ingest for {cam_id}")
            if self.ingest_manager.start_ingest(cam_id):
                started += 1
            else:
                logger.warning(f"Failed to start ingest for {cam_id}")
        
        logger.info(f"Started {started}/{len(enabled_cameras)} recorder ingest pipelines")
    
    async def _stop_vdoninja_services(self):
        """Stop VDO.ninja publisher services."""
        logger.info("Stopping VDO.ninja publisher services...")
        
        for service in self.VDONINJA_SERVICES:
            try:
                logger.info(f"Stopping {service}")
                result = await self._run_systemctl("stop", service)
                if result.returncode != 0:
                    logger.warning(f"Failed to stop {service}: {result.stderr}")
            except Exception as e:
                logger.error(f"Error stopping {service}: {e}")
        
        logger.info("Stopped VDO.ninja publisher services")
    
    async def _start_vdoninja_services(self):
        """Start VDO.ninja publisher services."""
        logger.info("Starting VDO.ninja publisher services...")
        
        started = 0
        for service in self.VDONINJA_SERVICES:
            try:
                logger.info(f"Starting {service}")
                result = await self._run_systemctl("start", service)
                if result.returncode == 0:
                    started += 1
                else:
                    logger.warning(f"Failed to start {service}: {result.stderr}")
            except Exception as e:
                logger.error(f"Error starting {service}: {e}")
        
        logger.info(f"Started {started}/{len(self.VDONINJA_SERVICES)} VDO.ninja publisher services")
    
    async def _run_systemctl(self, action: str, service: str):
        """Run systemctl command.
        
        Args:
            action: systemctl action (start, stop, status, etc.)
            service: service name
            
        Returns:
            CompletedProcess result
        """
        cmd = ["sudo", "systemctl", action, service]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        
        return type('Result', (), {
            'returncode': proc.returncode,
            'stdout': stdout.decode(),
            'stderr': stderr.decode()
        })()
    
    async def _get_service_status(self, service: str) -> str:
        """Get systemd service status.
        
        Args:
            service: service name
            
        Returns:
            Status string: active, inactive, failed, not-found
        """
        try:
            result = await self._run_systemctl("is-active", service)
            status = result.stdout.strip()
            
            if status == "active":
                return "active"
            elif status == "inactive":
                return "inactive"
            elif status == "failed":
                return "failed"
            else:
                return "unknown"
        except Exception as e:
            logger.error(f"Error getting status for {service}: {e}")
            return "error"

