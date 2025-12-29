"""Recording watchdog to detect stalled writes"""
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Awaitable, Callable, Dict, Optional

logger = logging.getLogger(__name__)

# Watchdog configuration
STALL_THRESHOLD_SECONDS = 30  # No bytes written for this long = stalled
CHECK_INTERVAL_SECONDS = 5   # How often to check
DISK_LOW_THRESHOLD_GB = 1.0  # Alert when disk falls below this


class RecordingWatchdog:
    """
    Monitors active recordings and detects stalls.

    Detects:
    - No bytes written for STALL_THRESHOLD_SECONDS
    - Disk space critically low
    - File size unchanged when it should be growing

    Callbacks are invoked when problems are detected.
    """

    def __init__(
        self,
        on_stall: Optional[Callable[[str, str], Awaitable[None]]] = None,
        on_disk_low: Optional[Callable[[float], Awaitable[None]]] = None,
        on_progress: Optional[Callable[[str, Dict[str, int]], Awaitable[None]]] = None,
    ):
        """
        Initialize watchdog.

        Args:
            on_stall: Callback(session_id, input_id) when recording stalls
            on_disk_low: Callback(available_gb) when disk space is low
            on_progress: Callback(session_id, bytes_written_dict) for progress updates
        """
        self.on_stall = on_stall
        self.on_disk_low = on_disk_low
        self.on_progress = on_progress

        # State tracking
        self._running = False
        self._task: Optional[asyncio.Task] = None

        # Per-input tracking: input_id -> (last_bytes, last_change_time)
        self._input_state: Dict[str, tuple[int, datetime]] = {}

        # Current recording info
        self._session_id: Optional[str] = None
        self._recording_paths: Dict[str, str] = {}  # input_id -> file_path

        # Disk low notification cooldown
        self._last_disk_low_alert: Optional[datetime] = None

    def start_watching(
        self,
        session_id: str,
        recording_paths: Dict[str, str],
    ) -> None:
        """
        Start watching a recording session.

        Args:
            session_id: Recording session ID
            recording_paths: Dict of input_id -> file_path being recorded
        """
        logger.info(f"[Watchdog] Starting watch for session {session_id}")

        self._session_id = session_id
        self._recording_paths = recording_paths

        # Initialize state for each input
        now = datetime.now()
        self._input_state = {
            input_id: (0, now)
            for input_id in recording_paths
        }

        # Start background task
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._watch_loop())

    def stop_watching(self) -> None:
        """Stop watching the current recording."""
        logger.info(f"[Watchdog] Stopping watch for session {self._session_id}")

        self._running = False
        self._session_id = None
        self._recording_paths = {}
        self._input_state = {}

        if self._task:
            self._task.cancel()
            self._task = None

    def update_bytes(self, input_id: str, bytes_written: int) -> None:
        """
        Update bytes written for an input (called by recording process).

        This resets the stall timer for this input.
        """
        if input_id in self._input_state:
            old_bytes, _ = self._input_state[input_id]
            if bytes_written > old_bytes:
                # Progress made - update timestamp
                self._input_state[input_id] = (bytes_written, datetime.now())

    async def _watch_loop(self) -> None:
        """Main watchdog loop."""
        logger.info("[Watchdog] Watch loop started")

        while self._running:
            try:
                await asyncio.sleep(CHECK_INTERVAL_SECONDS)

                if not self._running:
                    break

                await self._check_recording_health()
                await self._check_disk_space()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[Watchdog] Error in watch loop: {e}")
                # Don't crash the watchdog on individual check errors
                await asyncio.sleep(1)

        logger.info("[Watchdog] Watch loop ended")

    async def _check_recording_health(self) -> None:
        """Check if any recording inputs have stalled and report progress."""
        if not self._session_id:
            return

        now = datetime.now()
        stall_threshold = timedelta(seconds=STALL_THRESHOLD_SECONDS)
        
        # Collect current file sizes for progress reporting
        current_bytes: Dict[str, int] = {}

        for input_id, (last_bytes, last_change) in list(self._input_state.items()):
                file_path = self._recording_paths.get(input_id)
                if file_path:
                    actual_bytes = self._get_file_size(file_path)
                current_bytes[input_id] = actual_bytes

                    if actual_bytes > last_bytes:
                    # File grew - update our state
                        self._input_state[input_id] = (actual_bytes, now)
                        logger.debug(
                            f"[Watchdog] {input_id} file grew to {actual_bytes} bytes"
                        )
                else:
                    # File hasn't grown, check for stall
                    time_since_change = now - last_change
                    if time_since_change > stall_threshold:
                # Confirmed stall
                logger.warning(
                    f"[Watchdog] STALL DETECTED: {input_id} has not grown for "
                    f"{time_since_change.total_seconds():.0f}s (session: {self._session_id})"
                )

                if self.on_stall:
                    try:
                        await self.on_stall(self._session_id, input_id)
                    except Exception as e:
                        logger.error(f"[Watchdog] Stall callback failed: {e}")
        
        # Emit progress update with all current file sizes
        if current_bytes and self.on_progress:
            total_bytes = sum(current_bytes.values())
            logger.info(f"[Watchdog] Emitting progress: session={self._session_id}, total_bytes={total_bytes}, inputs={list(current_bytes.keys())}")
            try:
                await self.on_progress(self._session_id, current_bytes)
            except Exception as e:
                logger.error(f"[Watchdog] Progress callback failed: {e}")

    async def _check_disk_space(self) -> None:
        """Check if disk space is critically low."""
        try:
            import shutil
            usage = shutil.disk_usage("/opt/r58/recordings")
            available_gb = usage.free / (1024 ** 3)

            if available_gb < DISK_LOW_THRESHOLD_GB:
                # Limit how often we send alerts
                now = datetime.now()
                if (
                    self._last_disk_low_alert is None or
                    (now - self._last_disk_low_alert).total_seconds() > 60
                ):
                    logger.error(
                        f"[Watchdog] DISK LOW: Only {available_gb:.2f}GB remaining"
                    )
                    self._last_disk_low_alert = now

                    if self.on_disk_low:
                        try:
                            await self.on_disk_low(available_gb)
                        except Exception as e:
                            logger.error(f"[Watchdog] Disk low callback failed: {e}")

        except Exception as e:
            logger.warning(f"[Watchdog] Failed to check disk space: {e}")

    @staticmethod
    def _get_file_size(file_path: str) -> int:
        """Get file size in bytes, returns 0 if file doesn't exist."""
        try:
            return Path(file_path).stat().st_size
        except (FileNotFoundError, OSError):
            return 0


# Singleton instance for the pipeline manager
_watchdog: Optional[RecordingWatchdog] = None


def get_watchdog() -> RecordingWatchdog:
    """Get or create the watchdog singleton."""
    global _watchdog
    if _watchdog is None:
        _watchdog = RecordingWatchdog()
    return _watchdog

