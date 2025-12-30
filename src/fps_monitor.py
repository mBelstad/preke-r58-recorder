"""FPS Monitor for GStreamer Pipelines.

Provides real-time framerate monitoring and logging for video pipelines.
Uses GStreamer's identity element with handoff signal for accurate frame counting.
"""

import logging
import time
import threading
from typing import Dict, Optional, Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class FpsStats:
    """Framerate statistics for a single pipeline."""
    cam_id: str
    frame_count: int = 0
    last_frame_time: float = 0.0
    last_log_time: float = 0.0
    last_log_frame_count: int = 0
    
    # Rolling stats
    current_fps: float = 0.0
    avg_fps: float = 0.0
    min_fps: float = float('inf')
    max_fps: float = 0.0
    
    # Lifetime stats
    total_frames: int = 0
    start_time: float = field(default_factory=time.time)
    dropped_frames: int = 0
    
    def update(self):
        """Calculate FPS from recent frames."""
        now = time.time()
        elapsed = now - self.last_log_time
        
        if elapsed >= 1.0:  # Calculate FPS every second
            frames_since_last = self.frame_count - self.last_log_frame_count
            self.current_fps = frames_since_last / elapsed
            
            # Update rolling stats
            if self.current_fps > 0:
                if self.current_fps < self.min_fps:
                    self.min_fps = self.current_fps
                if self.current_fps > self.max_fps:
                    self.max_fps = self.current_fps
                
                # Running average
                total_elapsed = now - self.start_time
                if total_elapsed > 0:
                    self.avg_fps = self.total_frames / total_elapsed
            
            self.last_log_time = now
            self.last_log_frame_count = self.frame_count
            return True
        return False
    
    def on_frame(self):
        """Called for each frame received."""
        self.frame_count += 1
        self.total_frames += 1
        self.last_frame_time = time.time()


class FpsMonitor:
    """
    Monitors framerate for multiple GStreamer pipelines.
    
    Usage:
        monitor = FpsMonitor(log_interval=5.0)
        
        # For each pipeline:
        identity = monitor.create_identity_element(pipeline, "cam0")
        # Insert identity element into pipeline
        
        monitor.start()
        # ... pipeline runs ...
        monitor.stop()
    """
    
    _instance: Optional['FpsMonitor'] = None
    
    def __init__(self, log_interval: float = 5.0):
        """
        Initialize FPS monitor.
        
        Args:
            log_interval: How often to log FPS stats (seconds)
        """
        self.log_interval = log_interval
        self.stats: Dict[str, FpsStats] = {}
        self._running = False
        self._log_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
    
    @classmethod
    def get_instance(cls) -> 'FpsMonitor':
        """Get singleton instance of FpsMonitor."""
        if cls._instance is None:
            cls._instance = FpsMonitor()
        return cls._instance
    
    def register_pipeline(self, cam_id: str) -> FpsStats:
        """Register a pipeline for FPS monitoring."""
        with self._lock:
            if cam_id not in self.stats:
                self.stats[cam_id] = FpsStats(cam_id=cam_id)
                logger.info(f"[FPS Monitor] Registered {cam_id} for monitoring")
            return self.stats[cam_id]
    
    def unregister_pipeline(self, cam_id: str):
        """Unregister a pipeline from FPS monitoring."""
        with self._lock:
            if cam_id in self.stats:
                stats = self.stats[cam_id]
                logger.info(
                    f"[FPS Monitor] {cam_id} final stats: "
                    f"total_frames={stats.total_frames}, "
                    f"avg_fps={stats.avg_fps:.1f}, "
                    f"min={stats.min_fps:.1f}, max={stats.max_fps:.1f}"
                )
                del self.stats[cam_id]
    
    def on_frame(self, cam_id: str):
        """Called when a frame is received for a camera."""
        with self._lock:
            if cam_id in self.stats:
                self.stats[cam_id].on_frame()
    
    def create_handoff_callback(self, cam_id: str) -> Callable:
        """Create a handoff callback for identity element."""
        def on_handoff(identity, buffer):
            self.on_frame(cam_id)
        return on_handoff
    
    def get_fps_element_string(self, cam_id: str) -> str:
        """
        Get GStreamer element string for FPS monitoring.
        
        This returns an identity element with a unique name that can be
        connected to the handoff signal after pipeline creation.
        
        Returns:
            GStreamer element string like "identity name=fps_cam0"
        """
        return f"identity name=fps_{cam_id} signal-handoffs=true"
    
    def connect_to_pipeline(self, pipeline, cam_id: str) -> bool:
        """
        Connect FPS monitoring to a pipeline's identity element.
        
        Call this after Gst.parse_launch() to connect the handoff signal.
        
        Args:
            pipeline: GStreamer pipeline object
            cam_id: Camera identifier
            
        Returns:
            True if successfully connected, False otherwise
        """
        try:
            # Register this camera
            self.register_pipeline(cam_id)
            
            # Find the identity element
            identity = pipeline.get_by_name(f"fps_{cam_id}")
            if identity is None:
                logger.warning(f"[FPS Monitor] No identity element 'fps_{cam_id}' found in pipeline")
                return False
            
            # Connect handoff signal
            def on_handoff(element, buffer):
                self.on_frame(cam_id)
            
            identity.connect("handoff", on_handoff)
            logger.info(f"[FPS Monitor] Connected to pipeline for {cam_id}")
            return True
            
        except Exception as e:
            logger.error(f"[FPS Monitor] Failed to connect to pipeline for {cam_id}: {e}")
            return False
    
    def start(self):
        """Start the FPS logging thread."""
        if self._running:
            return
        
        self._running = True
        self._log_thread = threading.Thread(target=self._log_loop, daemon=True)
        self._log_thread.start()
        logger.info(f"[FPS Monitor] Started (logging every {self.log_interval}s)")
    
    def stop(self):
        """Stop the FPS logging thread."""
        self._running = False
        if self._log_thread:
            self._log_thread.join(timeout=2.0)
            self._log_thread = None
        logger.info("[FPS Monitor] Stopped")
    
    def _log_loop(self):
        """Background thread that logs FPS stats periodically."""
        last_log = time.time()
        
        while self._running:
            time.sleep(0.1)  # Check every 100ms
            
            now = time.time()
            if now - last_log >= self.log_interval:
                self._log_stats()
                last_log = now
    
    def _log_stats(self):
        """Log current FPS stats for all pipelines."""
        with self._lock:
            if not self.stats:
                return
            
            log_lines = ["[FPS Monitor] Current framerates:"]
            
            for cam_id, stats in sorted(self.stats.items()):
                # Update stats
                stats.update()
                
                # Determine status
                if stats.current_fps >= 29:
                    status = "✓"
                elif stats.current_fps >= 24:
                    status = "~"
                elif stats.current_fps > 0:
                    status = "!"
                else:
                    status = "?"
                
                log_lines.append(
                    f"  {status} {cam_id}: {stats.current_fps:.1f} fps "
                    f"(avg: {stats.avg_fps:.1f}, min: {stats.min_fps:.1f}, max: {stats.max_fps:.1f}, "
                    f"frames: {stats.total_frames})"
                )
            
            logger.info("\n".join(log_lines))
    
    def get_stats(self, cam_id: str) -> Optional[FpsStats]:
        """Get current stats for a camera."""
        with self._lock:
            return self.stats.get(cam_id)
    
    def get_all_stats(self) -> Dict[str, dict]:
        """Get stats for all cameras as a dictionary."""
        with self._lock:
            result = {}
            for cam_id, stats in self.stats.items():
                stats.update()
                result[cam_id] = {
                    "current_fps": round(stats.current_fps, 1),
                    "avg_fps": round(stats.avg_fps, 1),
                    "min_fps": round(stats.min_fps, 1) if stats.min_fps != float('inf') else 0,
                    "max_fps": round(stats.max_fps, 1),
                    "total_frames": stats.total_frames,
                    "uptime_seconds": round(time.time() - stats.start_time, 1)
                }
            return result


# Global instance for easy access
_fps_monitor: Optional[FpsMonitor] = None


def get_fps_monitor() -> FpsMonitor:
    """Get the global FPS monitor instance."""
    global _fps_monitor
    if _fps_monitor is None:
        _fps_monitor = FpsMonitor()
    return _fps_monitor
