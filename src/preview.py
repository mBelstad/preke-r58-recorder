"""Preview status manager (delegates to IngestManager)."""
import logging
from typing import Dict, Optional

from .config import AppConfig

logger = logging.getLogger(__name__)


class PreviewManager:
    """Manages preview status by delegating to IngestManager.
    
    In the always-on ingest architecture, preview is just a view of the ingest stream.
    This class provides a compatibility layer for existing API endpoints.
    """

    def __init__(self, config: AppConfig, ingest_manager):
        """Initialize preview manager with reference to ingest manager."""
        self.config = config
        self.ingest = ingest_manager

    def start_preview(self, cam_id: str) -> bool:
        """Start preview by ensuring ingest is running."""
        # Preview is automatically available when ingest is running
        return self.ingest.start_ingest(cam_id)

    def stop_preview(self, cam_id: str) -> bool:
        """Stop preview - NOTE: This does NOT stop ingest (which is always-on).
        
        This is a compatibility method. In the new architecture, ingest runs
        continuously and preview is just a consumer. Stopping preview doesn't
        actually do anything since ingest remains active.
        """
        logger.info(f"Preview stop requested for {cam_id} - ingest remains active")
        return True

    def start_all_previews(self) -> Dict[str, bool]:
        """Start all previews by ensuring all ingests are running."""
        return self.ingest.start_all()

    def stop_all_previews(self) -> Dict[str, bool]:
        """Stop all previews - compatibility method, ingest remains active."""
        logger.info("Preview stop-all requested - ingest remains active")
        results = {}
        for cam_id in self.config.cameras.keys():
            results[cam_id] = True
        return results

    def get_preview_status(self) -> Dict[str, str]:
        """Get preview status for all cameras (from ingest status)."""
        statuses = {}
        ingest_statuses = self.ingest.get_status()
        
        for cam_id, ingest_status in ingest_statuses.items():
            # Map ingest status to preview status
            if ingest_status.status == "streaming":
                statuses[cam_id] = "preview"  # Ingest streaming = preview available
            elif ingest_status.status == "no_signal":
                statuses[cam_id] = "no_signal"
            elif ingest_status.status == "error":
                statuses[cam_id] = "error"
            else:
                statuses[cam_id] = "idle"
        
        return statuses

    def get_camera_preview_status(self, cam_id: str) -> Optional[str]:
        """Get preview status for a specific camera."""
        ingest_status = self.ingest.get_camera_status(cam_id)
        if not ingest_status:
            return None
        
        # Map ingest status to preview status
        if ingest_status.status == "streaming":
            return "preview"
        elif ingest_status.status == "no_signal":
            return "no_signal"
        elif ingest_status.status == "error":
            return "error"
        else:
            return "idle"

    # Compatibility properties for existing code
    @property
    def preview_states(self) -> Dict[str, str]:
        """Compatibility property - returns preview status dict."""
        return self.get_preview_status()
    
    @property
    def current_resolutions(self) -> Dict[str, tuple[int, int]]:
        """Get current resolutions from ingest."""
        resolutions = {}
        ingest_statuses = self.ingest.get_status()
        for cam_id, status in ingest_statuses.items():
            if status.resolution:
                resolutions[cam_id] = status.resolution
        return resolutions
    
    @property
    def current_signal_status(self) -> Dict[str, bool]:
        """Get current signal status from ingest."""
        signals = {}
        ingest_statuses = self.ingest.get_status()
        for cam_id, status in ingest_statuses.items():
            signals[cam_id] = status.has_signal
        return signals
    
    @property
    def signal_loss_start_time(self) -> Dict[str, Optional[float]]:
        """Get signal loss times from ingest."""
        loss_times = {}
        for cam_id in self.config.cameras.keys():
            loss_times[cam_id] = self.ingest.signal_loss_times.get(cam_id)
        return loss_times
