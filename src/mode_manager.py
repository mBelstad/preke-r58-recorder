"""Mode manager for R58 recorder.

The R58 supports two mutually exclusive operating modes:

1. RECORDER MODE (default):
   - Individual camera recording to files
   - Ingest pipelines always running (preview via WHEP)
   - Each camera records independently to MKV files
   
2. MIXER MODE:
   - GStreamer compositor for scene-based mixing
   - Ingest pipelines always running (preview via WHEP)
   - Mixed output can be recorded as a single file
   - Individual camera recording is DISABLED in this mode

Ingest pipelines (camera → MediaMTX) run in BOTH modes.
Only the recording/mixing behavior changes between modes.
"""
import asyncio
import logging
import json
import subprocess
from typing import Dict, Optional, List
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ModeStatus:
    """Status information for current operating mode."""
    current_mode: str
    available_modes: List[str]
    ingest_services: Dict[str, str]  # service_name -> status (always running)
    recorder_active: bool  # Individual recording available
    mixer_active: bool  # Compositor running
    can_switch: bool
    message: Optional[str] = None


class ModeManager:
    """Manages operating mode switching between Recorder and Mixer modes.
    
    Recorder Mode:
    - Individual camera recording enabled
    - Mixer/compositor disabled
    
    Mixer Mode:
    - Compositor running for scene-based mixing
    - Individual camera recording disabled (to prevent CPU overload)
    - Mixed output can be recorded
    
    Ingest pipelines always run in both modes (for preview).
    """
    
    MODES = ["recorder", "mixer"]
    STATE_FILE = Path("/tmp/r58_mode_state.json")
    
    def __init__(self, ingest_manager=None, recorder=None, mixer_core=None, config=None):
        """Initialize mode manager.
        
        Args:
            ingest_manager: Reference to IngestManager (always running)
            recorder: Reference to Recorder instance (for stopping recordings)
            mixer_core: Reference to MixerCore instance (for starting/stopping mixer)
            config: Application configuration object
        """
        self.ingest_manager = ingest_manager
        self.recorder = recorder
        self.mixer_core = mixer_core
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
        """Get detailed status of current operating mode."""
        current_mode = await self.get_current_mode()
        
        # Check ingest services (always running in both modes)
        ingest_services = {}
        if self.ingest_manager:
            for cam_id, state in self.ingest_manager.states.items():
                ingest_services[f"ingest-{cam_id}"] = state
        else:
            ingest_services = {"ingest": "unavailable"}
        
        # Check if recorder is active (individual recording available)
        recorder_active = current_mode == "recorder"
        
        # Check if mixer is active
        mixer_active = False
        if self.mixer_core:
            try:
                mixer_status = self.mixer_core.get_status()
                mixer_active = mixer_status.get("state") == "PLAYING"
            except Exception:
                mixer_active = False
        
        return ModeStatus(
            current_mode=current_mode,
            available_modes=self.MODES,
            ingest_services=ingest_services,
            recorder_active=recorder_active,
            mixer_active=mixer_active,
            can_switch=True,
            message=f"Currently in {current_mode} mode. Ingest pipelines always running for preview."
        )
    
    async def switch_to_recorder(self) -> Dict[str, any]:
        """Switch to Recorder Mode.
        
        Stops mixer and VDO.ninja bridge, enables individual camera recording.
        
        Returns:
            Dict with success status and message
        """
        if self._current_mode == "recorder":
            logger.info("Already in recorder mode")
            return {
                "success": True,
                "mode": "recorder",
                "message": "Already in recorder mode"
            }
        
        logger.info("Switching to recorder mode...")
        
        # Stop VDO.ninja bridge service
        try:
            logger.info("Stopping VDO.ninja bridge service...")
            result = subprocess.run(
                ["sudo", "systemctl", "stop", "vdoninja-bridge"],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                logger.info("VDO.ninja bridge service stopped")
            else:
                logger.warning(f"Failed to stop vdoninja-bridge service: {result.stderr}")
        except Exception as e:
            logger.warning(f"Failed to stop vdoninja-bridge service: {e}")
        
        # Update mode
        self._current_mode = "recorder"
        self._save_state()
        
        logger.info("Switched to recorder mode")
        return {
            "success": True,
            "mode": "recorder",
            "message": "Switched to recorder mode. Mixer disabled, individual recording enabled."
        }
    
        """Switch to Recorder Mode.
        
        Stops the mixer/compositor and enables individual camera recording.
        Ingest pipelines continue running (preview always available).
        
        Returns:
            Dict with success status and message
        """
        if self._current_mode == "recorder":
            logger.info("Already in recorder mode")
            return {
                "success": True,
                "mode": "recorder",
                "message": "Already in recorder mode"
            }
        
        logger.info("Switching to recorder mode...")
        
        # Stop mixer if running
        if self.mixer_core:
            try:
                mixer_status = self.mixer_core.get_status()
                if mixer_status.get("state") == "PLAYING":
                    logger.info("Stopping mixer...")
                    self.mixer_core.stop()
            except Exception as e:
                logger.warning(f"Failed to stop mixer: {e}")
        
        # Stop VDO.ninja bridge service
        try:
            logger.info("Stopping VDO.ninja bridge service...")
            result = subprocess.run(
                ["sudo", "systemctl", "stop", "vdoninja-bridge"],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                logger.info("VDO.ninja bridge service stopped")
            else:
                logger.warning(f"Failed to stop vdoninja-bridge service: {result.stderr}")
        except Exception as e:
            logger.warning(f"Failed to stop vdoninja-bridge service: {e}")
        
        # Update mode
        self._current_mode = "recorder"
        self._save_state()
        
        logger.info("Switched to recorder mode")
        return {
            "success": True,
            "mode": "recorder",
            "message": "Switched to recorder mode. Individual camera recording enabled."
        }
    
    async def switch_to_mixer(self) -> Dict[str, any]:
        """Switch to Mixer Mode.
        
        Stops all individual camera recordings and enables the mixer/compositor.
        Ingest pipelines continue running (preview always available).
        
        Returns:
            Dict with success status and message
        """
        if self._current_mode == "mixer":
            logger.info("Already in mixer mode")
            return {
                "success": True,
                "mode": "mixer",
                "message": "Already in mixer mode"
            }
        
        logger.info("Switching to mixer mode...")
        
        # Stop all individual recordings
        if self.recorder:
            try:
                logger.info("Stopping all individual recordings...")
                stopped_cameras = []
                for cam_id, state in self.recorder.states.items():
                    if state == "recording":
                        self.recorder.stop_recording(cam_id)
                        stopped_cameras.append(cam_id)
                if stopped_cameras:
                    logger.info(f"Stopped recordings for: {', '.join(stopped_cameras)}")
            except Exception as e:
                logger.warning(f"Failed to stop recordings: {e}")
        
        # Start VDO.ninja bridge service (pushes cameras to VDO.ninja room)
        try:
            logger.info("Starting VDO.ninja bridge service...")
            result = subprocess.run(
                ["sudo", "systemctl", "start", "vdoninja-bridge"],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                logger.info("VDO.ninja bridge service started")
            else:
                logger.warning(f"Failed to start vdoninja-bridge service: {result.stderr}")
        except Exception as e:
            logger.warning(f"Failed to start vdoninja-bridge service: {e}")
        
        # Update mode
        self._current_mode = "mixer"
        self._save_state()
        
        logger.info("Switched to mixer mode")
        return {
            "success": True,
            "mode": "mixer",
            "message": "Switched to mixer mode. Individual recording disabled, mixer enabled.",
            "stopped_recordings": stopped_cameras if self.recorder else []
        }
    
    async def switch_to_vdoninja(self) -> Dict[str, any]:
        """Switch to VDO.ninja Mode - DEPRECATED.
        
        VDO.ninja now uses MediaMTX WHEP mode, no separate mode needed.
        This method is kept for backward compatibility.
        
        Returns:
            Dict with info message
        """
        logger.info("VDO.ninja mode switch not needed - use &mediamtx= parameter instead")
        
        return {
            "success": True,
            "mode": self._current_mode,
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
