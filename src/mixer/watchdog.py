"""Watchdog for monitoring mixer pipeline health."""
import logging
import threading
import time
from typing import Optional, Callable
from enum import Enum

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Pipeline health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    FAILED = "failed"


class MixerWatchdog:
    """Monitors mixer pipeline health and triggers recovery."""

    def __init__(
        self,
        health_check_interval: float = 5.0,
        buffer_timeout: float = 10.0,
        on_unhealthy: Optional[Callable[[], None]] = None
    ):
        """Initialize watchdog.
        
        Args:
            health_check_interval: Seconds between health checks
            buffer_timeout: Seconds without buffers before marking unhealthy
            on_unhealthy: Callback when pipeline becomes unhealthy
        """
        self.health_check_interval = health_check_interval
        self.buffer_timeout = buffer_timeout
        self.on_unhealthy = on_unhealthy
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_buffer_time: Optional[float] = None
        self._last_error: Optional[str] = None
        self._health_status = HealthStatus.HEALTHY
        self._lock = threading.Lock()

    def start(self) -> None:
        """Start the watchdog thread."""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._watchdog_loop, daemon=True)
        self._thread.start()
        logger.info("Mixer watchdog started")

    def stop(self) -> None:
        """Stop the watchdog thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        logger.info("Mixer watchdog stopped")

    def record_buffer(self) -> None:
        """Record that a buffer was processed (call from pipeline)."""
        with self._lock:
            self._last_buffer_time = time.time()
            if self._health_status != HealthStatus.HEALTHY:
                logger.info("Pipeline recovered - buffers flowing again")
                self._health_status = HealthStatus.HEALTHY
                self._last_error = None

    def record_error(self, error: str) -> None:
        """Record an error from the pipeline."""
        with self._lock:
            self._last_error = error
            if self._health_status == HealthStatus.HEALTHY:
                self._health_status = HealthStatus.DEGRADED
            elif self._health_status == HealthStatus.DEGRADED:
                self._health_status = HealthStatus.UNHEALTHY

    def check_health(self, pipeline_state: str, expected_state: str = "PLAYING") -> HealthStatus:
        """Check pipeline health based on state and buffer activity.
        
        Args:
            pipeline_state: Current GStreamer pipeline state
            expected_state: Expected state (usually "PLAYING")
        
        Returns:
            Current health status
        """
        with self._lock:
            # Check state mismatch
            if pipeline_state != expected_state and expected_state == "PLAYING":
                if self._health_status == HealthStatus.HEALTHY:
                    self._health_status = HealthStatus.DEGRADED
                    logger.warning(f"Pipeline state mismatch: {pipeline_state} != {expected_state}")
                elif self._health_status == HealthStatus.DEGRADED:
                    self._health_status = HealthStatus.UNHEALTHY
                    logger.error(f"Pipeline still in wrong state: {pipeline_state}")
            
            # Check buffer timeout
            if self._last_buffer_time:
                time_since_buffer = time.time() - self._last_buffer_time
                if time_since_buffer > self.buffer_timeout:
                    if self._health_status == HealthStatus.HEALTHY:
                        self._health_status = HealthStatus.DEGRADED
                        logger.warning(f"No buffers for {time_since_buffer:.1f}s")
                    elif self._health_status == HealthStatus.DEGRADED:
                        self._health_status = HealthStatus.UNHEALTHY
                        logger.error(f"No buffers for {time_since_buffer:.1f}s - pipeline may be hung")
            
            return self._health_status

    def get_status(self) -> dict:
        """Get current watchdog status."""
        with self._lock:
            time_since_buffer = None
            if self._last_buffer_time:
                time_since_buffer = time.time() - self._last_buffer_time
            
            return {
                "health": self._health_status.value,
                "last_buffer_seconds_ago": time_since_buffer,
                "last_error": self._last_error,
                "running": self._running
            }

    def _watchdog_loop(self) -> None:
        """Main watchdog loop."""
        while self._running:
            try:
                time.sleep(self.health_check_interval)
                # Health check is done by calling check_health from the mixer
                # This loop just ensures the watchdog stays alive
            except Exception as e:
                logger.error(f"Watchdog loop error: {e}")

