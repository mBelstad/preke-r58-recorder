"""GStreamer pipeline runner with lifecycle management.

Manages GStreamer pipeline lifecycle: start, stop, EOS handling, error recovery.
Ported from src/recorder.py with adaptations for the new backend architecture.
"""
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from . import get_gst, get_glib, ensure_gst_initialized

logger = logging.getLogger(__name__)


class PipelineState(str, Enum):
    """Pipeline state enumeration."""
    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class PipelineInfo:
    """Information about a running pipeline."""
    pipeline_id: str
    pipeline_type: str  # "preview", "recording"
    pipeline: Any  # Gst.Pipeline
    state: PipelineState = PipelineState.IDLE
    started_at: Optional[datetime] = None
    output_path: Optional[str] = None
    device: Optional[str] = None
    error_message: Optional[str] = None
    last_bytes: int = 0
    stall_count: int = 0


class PipelineRunner:
    """Manages GStreamer pipeline lifecycle.
    
    Provides start/stop/restart functionality with error handling,
    bus message processing, and health monitoring.
    """
    
    def __init__(self, on_state_change: Optional[Callable[[str, PipelineState, Optional[str]], None]] = None):
        """Initialize the pipeline runner.
        
        Args:
            on_state_change: Callback for state changes (pipeline_id, new_state, error_msg)
        """
        self._pipelines: Dict[str, PipelineInfo] = {}
        self._lock = threading.Lock()
        self._gst_ready = False
        self._glib_loop: Optional[Any] = None
        self._glib_thread: Optional[threading.Thread] = None
        self._on_state_change = on_state_change
        
        # Monitoring
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
    
    def _ensure_gst(self) -> bool:
        """Ensure GStreamer is initialized."""
        if self._gst_ready:
            return True
        
        if ensure_gst_initialized():
            self._gst_ready = True
            self._start_glib_mainloop()
            return True
        
        logger.error("GStreamer initialization failed")
        return False
    
    def _start_glib_mainloop(self):
        """Start the GLib main loop in a background thread."""
        if self._glib_loop is not None:
            return
        
        GLib = get_glib()
        if GLib is None:
            return
        
        self._glib_loop = GLib.MainLoop()
        
        def run_loop():
            try:
                self._glib_loop.run()
            except Exception as e:
                logger.error(f"GLib main loop error: {e}")
        
        self._glib_thread = threading.Thread(target=run_loop, daemon=True)
        self._glib_thread.start()
        logger.info("GLib main loop started")
    
    def _stop_glib_mainloop(self):
        """Stop the GLib main loop."""
        if self._glib_loop is not None:
            self._glib_loop.quit()
            self._glib_loop = None
        if self._glib_thread is not None:
            self._glib_thread.join(timeout=2.0)
            self._glib_thread = None
    
    def _notify_state_change(self, pipeline_id: str, state: PipelineState, error: Optional[str] = None):
        """Notify about pipeline state change."""
        if self._on_state_change:
            try:
                self._on_state_change(pipeline_id, state, error)
            except Exception as e:
                logger.error(f"Error in state change callback: {e}")
    
    def _on_bus_message(self, bus, message, pipeline_id: str):
        """Handle GStreamer bus messages."""
        Gst = get_gst()
        if not Gst:
            return True
        
        with self._lock:
            info = self._pipelines.get(pipeline_id)
            if not info:
                return True
        
        if message.type == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            logger.error(f"Pipeline error for {pipeline_id}: {err.message} - {debug}")
            info.state = PipelineState.ERROR
            info.error_message = err.message
            self._notify_state_change(pipeline_id, PipelineState.ERROR, err.message)
            
        elif message.type == Gst.MessageType.EOS:
            logger.info(f"End of stream for {pipeline_id}")
            if info.state == PipelineState.STOPPING:
                # Expected EOS during stop
                pass
            else:
                # Unexpected EOS
                info.state = PipelineState.ERROR
                info.error_message = "Unexpected end of stream"
                self._notify_state_change(pipeline_id, PipelineState.ERROR, "Unexpected EOS")
                
        elif message.type == Gst.MessageType.STATE_CHANGED:
            if message.src == info.pipeline:
                old_state, new_state, pending = message.parse_state_changed()
                logger.debug(
                    f"State changed for {pipeline_id}: "
                    f"{old_state.value_nick} -> {new_state.value_nick}"
                )
                
                if new_state == Gst.State.PLAYING and info.state == PipelineState.STARTING:
                    info.state = PipelineState.RUNNING
                    info.started_at = datetime.now()
                    self._notify_state_change(pipeline_id, PipelineState.RUNNING)
                    
        elif message.type == Gst.MessageType.WARNING:
            warn, debug = message.parse_warning()
            logger.warning(f"Pipeline warning for {pipeline_id}: {warn.message} - {debug}")
        
        return True
    
    def start_pipeline(
        self,
        pipeline_id: str,
        pipeline_string: str,
        pipeline_type: str = "recording",
        output_path: Optional[str] = None,
        device: Optional[str] = None
    ) -> bool:
        """Start a GStreamer pipeline.
        
        Args:
            pipeline_id: Unique identifier for this pipeline
            pipeline_string: GStreamer pipeline description
            pipeline_type: Type of pipeline ("preview", "recording")
            output_path: Output file path (for recording)
            device: Source device (for reference)
            
        Returns:
            True if pipeline started successfully
        """
        if not self._ensure_gst():
            logger.error("Cannot start pipeline - GStreamer not available")
            return False
        
        Gst = get_gst()
        if not Gst:
            return False
        
        with self._lock:
            # Stop existing pipeline if any
            if pipeline_id in self._pipelines:
                self._stop_pipeline_unsafe(pipeline_id)
            
            try:
                logger.info(f"Starting pipeline {pipeline_id}: {pipeline_string}")
                
                # Create pipeline
                pipeline = Gst.parse_launch(pipeline_string)
                if not pipeline:
                    logger.error(f"Failed to parse pipeline for {pipeline_id}")
                    return False
                
                # Create pipeline info
                info = PipelineInfo(
                    pipeline_id=pipeline_id,
                    pipeline_type=pipeline_type,
                    pipeline=pipeline,
                    state=PipelineState.STARTING,
                    output_path=output_path,
                    device=device
                )
                
                # Set up bus message handler
                bus = pipeline.get_bus()
                bus.add_signal_watch()
                bus.connect("message", self._on_bus_message, pipeline_id)
                
                # Start pipeline
                ret = pipeline.set_state(Gst.State.PLAYING)
                if ret == Gst.StateChangeReturn.FAILURE:
                    # Get more detailed error from bus
                    bus = pipeline.get_bus()
                    msg = bus.timed_pop_filtered(Gst.SECOND, Gst.MessageType.ERROR)
                    if msg:
                        err, debug = msg.parse_error()
                        logger.error(f"Failed to start pipeline {pipeline_id}: {err.message}")
                        logger.error(f"Debug info: {debug}")
                    else:
                        logger.error(f"Failed to start pipeline {pipeline_id} (no error message)")
                    pipeline.set_state(Gst.State.NULL)
                    return False
                
                self._pipelines[pipeline_id] = info
                self._notify_state_change(pipeline_id, PipelineState.STARTING)
                
                logger.info(f"Pipeline {pipeline_id} starting")
                return True
                
            except Exception as e:
                logger.error(f"Failed to start pipeline {pipeline_id}: {e}")
                return False
    
    def stop_pipeline(self, pipeline_id: str, timeout: float = 15.0) -> bool:
        """Stop a running pipeline gracefully.
        
        Sends EOS and waits for clean shutdown.
        
        Args:
            pipeline_id: Pipeline to stop
            timeout: Maximum seconds to wait for EOS
            
        Returns:
            True if pipeline stopped successfully
        """
        with self._lock:
            return self._stop_pipeline_unsafe(pipeline_id, timeout)
    
    def _stop_pipeline_unsafe(self, pipeline_id: str, timeout: float = 15.0) -> bool:
        """Stop pipeline (must be called with lock held)."""
        info = self._pipelines.get(pipeline_id)
        if not info:
            logger.debug(f"Pipeline {pipeline_id} not found")
            return True
        
        Gst = get_gst()
        if not Gst:
            return False
        
        info.state = PipelineState.STOPPING
        self._notify_state_change(pipeline_id, PipelineState.STOPPING)
        
        pipeline = info.pipeline
        
        try:
            # Send EOS to flush the pipeline
            pipeline.send_event(Gst.Event.new_eos())
            
            # Wait for EOS or timeout
            bus = pipeline.get_bus()
            msg = bus.timed_pop_filtered(
                int(timeout * Gst.SECOND),
                Gst.MessageType.EOS | Gst.MessageType.ERROR
            )
            
            if msg and msg.type == Gst.MessageType.ERROR:
                err, debug = msg.parse_error()
                logger.error(f"Pipeline error during stop for {pipeline_id}: {err.message}")
            
            # Set to NULL state
            pipeline.set_state(Gst.State.NULL)
            
            # Wait for state change
            ret = pipeline.get_state(Gst.CLOCK_TIME_NONE)
            
            # Clean up
            del self._pipelines[pipeline_id]
            
            logger.info(f"Stopped pipeline {pipeline_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping pipeline {pipeline_id}: {e}")
            # Force stop
            try:
                pipeline.set_state(Gst.State.NULL)
                pipeline.get_state(Gst.CLOCK_TIME_NONE)
                del self._pipelines[pipeline_id]
            except:
                pass
            return False
    
    def stop_all(self) -> None:
        """Stop all running pipelines."""
        with self._lock:
            pipeline_ids = list(self._pipelines.keys())
        
        for pipeline_id in pipeline_ids:
            self.stop_pipeline(pipeline_id)
    
    def get_pipeline_state(self, pipeline_id: str) -> Optional[PipelineState]:
        """Get the state of a pipeline."""
        with self._lock:
            info = self._pipelines.get(pipeline_id)
            return info.state if info else None
    
    def get_pipeline_info(self, pipeline_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a pipeline."""
        with self._lock:
            info = self._pipelines.get(pipeline_id)
            if not info:
                return None
            return {
                "pipeline_id": info.pipeline_id,
                "pipeline_type": info.pipeline_type,
                "state": info.state.value,
                "started_at": info.started_at.isoformat() if info.started_at else None,
                "output_path": info.output_path,
                "device": info.device,
                "error_message": info.error_message
            }
    
    def get_all_pipelines(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all pipelines."""
        with self._lock:
            result = {}
            for pid, info in self._pipelines.items():
                result[pid] = {
                    "pipeline_id": info.pipeline_id,
                    "pipeline_type": info.pipeline_type,
                    "state": info.state.value,
                    "started_at": info.started_at.isoformat() if info.started_at else None,
                    "output_path": info.output_path,
                    "device": info.device,
                    "error_message": info.error_message
                }
            return result
    
    def is_running(self, pipeline_id: str) -> bool:
        """Check if a pipeline is running."""
        state = self.get_pipeline_state(pipeline_id)
        return state in (PipelineState.STARTING, PipelineState.RUNNING)
    
    def start_monitoring(self, check_interval: float = 10.0):
        """Start background monitoring of pipeline health."""
        if self._monitoring:
            return
        
        self._monitoring = True
        
        def monitor():
            while self._monitoring:
                self._check_pipeline_health()
                time.sleep(check_interval)
        
        self._monitor_thread = threading.Thread(target=monitor, daemon=True)
        self._monitor_thread.start()
        logger.info("Pipeline health monitoring started")
    
    def stop_monitoring(self):
        """Stop background monitoring."""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2.0)
            self._monitor_thread = None
    
    def _check_pipeline_health(self):
        """Check health of all running pipelines."""
        with self._lock:
            for pipeline_id, info in list(self._pipelines.items()):
                if info.state != PipelineState.RUNNING:
                    continue
                
                if info.pipeline_type != "recording":
                    continue
                
                # Check if output file is growing (recording only)
                if info.output_path:
                    try:
                        path = Path(info.output_path)
                        if path.exists():
                            current_bytes = path.stat().st_size
                            if current_bytes == info.last_bytes and info.last_bytes > 0:
                                info.stall_count += 1
                                if info.stall_count >= 3:
                                    logger.warning(
                                        f"Recording stalled for {pipeline_id} "
                                        f"(no growth for {info.stall_count * 10}s)"
                                    )
                                    # Could implement auto-restart here
                            else:
                                info.stall_count = 0
                            info.last_bytes = current_bytes
                    except Exception as e:
                        logger.error(f"Error checking file size for {pipeline_id}: {e}")
    
    def shutdown(self):
        """Shutdown the pipeline runner."""
        self.stop_monitoring()
        self.stop_all()
        self._stop_glib_mainloop()
        logger.info("Pipeline runner shutdown complete")


# Global singleton instance
_runner: Optional[PipelineRunner] = None
_runner_lock = threading.Lock()


def get_runner(on_state_change: Optional[Callable[[str, PipelineState, Optional[str]], None]] = None) -> PipelineRunner:
    """Get the global pipeline runner instance.
    
    Args:
        on_state_change: Optional callback for state changes
        
    Returns:
        The global PipelineRunner instance
    """
    global _runner
    with _runner_lock:
        if _runner is None:
            _runner = PipelineRunner(on_state_change=on_state_change)
        return _runner

