"""Mode manager for R58 recorder.

Note: The dual-mode system (recorder/vdoninja) has been simplified.
VDO.ninja now works via WHEP streams from MediaMTX, eliminating the need
for separate raspberry.ninja publisher services or mode switching.

The R58 always runs in "recorder" mode, which:
- Runs ingest pipelines to stream cameras to MediaMTX via RTSP
- MediaMTX exposes cameras via WHEP endpoints
- VDO.ninja connects to MediaMTX using &mediamtx= parameter
- Works both locally and remotely through FRP tunnels

DEPRECATED: raspberry.ninja P2P publishers - they don't work through tunnels.
"""
import asyncio
import logging
import json
from typing import Dict, Optional, List
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ModeStatus:
    """Status information for recorder mode."""
    current_mode: str
    available_modes: List[str]
    recorder_services: Dict[str, str]  # service_name -> status
    can_switch: bool
    message: Optional[str] = None


class ModeManager:
    """Manages recorder mode.
    
    Recorder Mode (only mode):
    - preke-recorder ingest pipelines active (internal)
    - MediaMTX receives streams via RTSP
    - Used for recording and WHEP viewing (local and remote)
    - VDO.ninja integration via WHEP using &mediamtx= parameter
    
    Note: raspberry.ninja P2P publishers have been deprecated because
    P2P WebRTC does NOT work through FRP tunnels. Use MediaMTX WHEP instead.
    """
    
    MODES = ["recorder"]  # Single mode only
    STATE_FILE = Path("/tmp/r58_mode_state.json")
    
    def __init__(self, ingest_manager=None, config=None):
        """Initialize mode manager.
        
        Args:
            ingest_manager: Reference to IngestManager for controlling recorder pipelines
            config: Application configuration object
        """
        self.ingest_manager = ingest_manager
        self.config = config
        self._current_mode: str = "recorder"
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
        return self._current_mode
    
    async def get_status(self) -> ModeStatus:
        """Get detailed status of recorder mode."""
        current_mode = await self.get_current_mode()
        
        # Check recorder services (ingest pipelines)
        recorder_services = {}
        if self.ingest_manager:
            for cam_id, state in self.ingest_manager.states.items():
                recorder_services[f"ingest-{cam_id}"] = state
        else:
            recorder_services = {"ingest": "unavailable"}
        
        return ModeStatus(
            current_mode=current_mode,
            available_modes=self.MODES,
            recorder_services=recorder_services,
            can_switch=False,  # No mode switching needed
            message="VDO.ninja uses MediaMTX WHEP mode. No mode switching required."
        )
    
    async def switch_to_recorder(self) -> Dict[str, any]:
        """Switch to Recorder Mode.
        
        Note: This is now a no-op since recorder mode is always active.
        VDO.ninja connects via MediaMTX WHEP, not separate publishers.
        
        Returns:
            Dict with success status and message
        """
        logger.info("Recorder mode is already active (MediaMTX WHEP mode)")
        
        return {
            "success": True,
            "mode": "recorder",
            "message": "Recorder mode is always active. VDO.ninja uses MediaMTX WHEP."
        }
    
    async def switch_to_vdoninja(self) -> Dict[str, any]:
        """Switch to VDO.ninja Mode - DEPRECATED.
        
        VDO.ninja now uses MediaMTX WHEP mode, no separate mode needed.
        raspberry.ninja P2P publishers have been deprecated.
        
        Returns:
            Dict with info message
        """
        logger.info("VDO.ninja mode switch not needed - use &mediamtx= parameter instead")
        
        return {
            "success": True,
            "mode": "recorder",
            "message": "VDO.ninja now uses MediaMTX WHEP mode. Open mixer/director with &mediamtx= parameter. No mode switch required."
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
