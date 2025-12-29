"""Client for communicating with the pipeline manager via IPC"""
import asyncio
import json
import logging
import random
from typing import Any, Dict, List, Optional

from ..config import get_settings

logger = logging.getLogger(__name__)

# IPC Configuration
IPC_CONNECT_TIMEOUT = 5.0  # seconds to wait for connection
IPC_READ_TIMEOUT = 10.0    # seconds to wait for response
IPC_MAX_RETRIES = 3        # max retry attempts
IPC_BASE_DELAY = 0.1       # base delay for exponential backoff
IPC_MAX_DELAY = 2.0        # max delay between retries


class PipelineConnectionError(Exception):
    """Raised when pipeline manager is not reachable"""
    pass


class PipelineTimeoutError(Exception):
    """Raised when pipeline manager doesn't respond in time"""
    pass


class PipelineClient:
    """Async client for pipeline-manager IPC with retry and timeout support"""

    def __init__(self):
        self.settings = get_settings()
        self.socket_path = self.settings.pipeline_socket_path
        self._consecutive_failures = 0

    async def _send_command(
        self,
        cmd: Dict[str, Any],
        timeout: Optional[float] = None,
        retries: int = IPC_MAX_RETRIES,
    ) -> Dict[str, Any]:
        """
        Send a command to the pipeline manager and get response.

        Args:
            cmd: Command dictionary to send
            timeout: Override default read timeout
            retries: Number of retry attempts on failure

        Returns:
            Response dictionary from pipeline manager

        Raises:
            Returns error dict on failure (for backward compatibility)
        """
        read_timeout = timeout or IPC_READ_TIMEOUT
        last_error: Optional[Exception] = None

        for attempt in range(retries + 1):
            try:
                result = await self._send_command_once(cmd, read_timeout)

                # Success - reset failure counter
                if self._consecutive_failures > 0:
                    logger.info(f"Pipeline connection restored after {self._consecutive_failures} failures")
                self._consecutive_failures = 0

                return result

            except (PipelineConnectionError, PipelineTimeoutError) as e:
                last_error = e
                self._consecutive_failures += 1

                if attempt < retries:
                    # Exponential backoff with jitter
                    delay = min(
                        IPC_BASE_DELAY * (2 ** attempt) + random.uniform(0, 0.1),
                        IPC_MAX_DELAY
                    )
                    logger.warning(
                        f"Pipeline command failed (attempt {attempt + 1}/{retries + 1}): {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"Pipeline command failed after {retries + 1} attempts: {e}. "
                        f"Consecutive failures: {self._consecutive_failures}"
                    )

        # Return error dict for backward compatibility
        return {"error": str(last_error)}

    async def _send_command_once(
        self,
        cmd: Dict[str, Any],
        read_timeout: float,
    ) -> Dict[str, Any]:
        """
        Single attempt to send command and get response.

        Raises:
            PipelineConnectionError: If cannot connect
            PipelineTimeoutError: If response times out
        """
        writer: Optional[asyncio.StreamWriter] = None

        try:
            # Connect with timeout
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_unix_connection(self.socket_path),
                    timeout=IPC_CONNECT_TIMEOUT
                )
            except asyncio.TimeoutError:
                raise PipelineConnectionError(
                    f"Timeout connecting to pipeline manager at {self.socket_path}"
                )
            except FileNotFoundError:
                raise PipelineConnectionError(
                    "Pipeline manager not running (socket not found)"
                )
            except ConnectionRefusedError:
                raise PipelineConnectionError(
                    "Pipeline manager connection refused"
                )

            # Send command
            cmd_bytes = json.dumps(cmd).encode() + b"\n"
            writer.write(cmd_bytes)
            await writer.drain()

            # Read response with timeout
            try:
                response = await asyncio.wait_for(
                    reader.readline(),
                    timeout=read_timeout
                )
            except asyncio.TimeoutError:
                raise PipelineTimeoutError(
                    f"Timeout waiting for pipeline response ({read_timeout}s)"
                )

            if not response:
                raise PipelineConnectionError(
                    "Pipeline manager closed connection unexpectedly"
                )

            return json.loads(response)

        except json.JSONDecodeError as e:
            raise PipelineConnectionError(f"Invalid JSON response: {e}")

        finally:
            # Always clean up the writer
            if writer is not None:
                writer.close()
                try:
                    await asyncio.wait_for(writer.wait_closed(), timeout=1.0)
                except asyncio.TimeoutError:
                    pass  # Force close

    @property
    def is_healthy(self) -> bool:
        """Check if pipeline connection is healthy"""
        return self._consecutive_failures < 3

    async def get_status(self) -> Dict[str, Any]:
        """Get current pipeline status"""
        return await self._send_command({"cmd": "status"})

    async def start_recording(
        self,
        session_id: Optional[str] = None,
        inputs: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Start recording on specified inputs"""
        cmd = {
            "cmd": "recording.start",
        }
        if session_id:
            cmd["session_id"] = session_id
        if inputs:
            cmd["inputs"] = inputs

        return await self._send_command(cmd)

    async def stop_recording(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Stop current recording"""
        cmd = {"cmd": "recording.stop"}
        if session_id:
            cmd["session_id"] = session_id

        return await self._send_command(cmd)

    async def get_recording_status(self) -> Dict[str, Any]:
        """Get current recording status"""
        return await self._send_command({"cmd": "recording.status"})

    async def start_preview(self, input_id: str) -> Dict[str, Any]:
        """Start preview pipeline for an input"""
        return await self._send_command({
            "cmd": "preview.start",
            "input_id": input_id,
        })

    async def stop_preview(self, input_id: str) -> Dict[str, Any]:
        """Stop preview pipeline for an input"""
        return await self._send_command({
            "cmd": "preview.stop",
            "input_id": input_id,
        })

    async def get_preview_status(self, input_id: Optional[str] = None) -> Dict[str, Any]:
        """Get preview status for one or all inputs"""
        cmd = {"cmd": "preview.status"}
        if input_id:
            cmd["input_id"] = input_id
        return await self._send_command(cmd)

    async def get_pipeline_status(self) -> Dict[str, Any]:
        """Get status of all pipelines (preview and recording)"""
        return await self._send_command({"cmd": "pipeline.status"})

    async def check_devices(self, device: Optional[str] = None) -> Dict[str, Any]:
        """
        Check device capabilities and signal status.

        Args:
            device: Optional specific device path. If None, checks all enabled cameras.

        Returns:
            Dict with device capabilities including has_signal for each input.
        """
        cmd = {"cmd": "device.check"}
        if device:
            cmd["device"] = device
        return await self._send_command(cmd)

    async def poll_events(self, last_seq: int = 0) -> Dict[str, Any]:
        """
        Poll for pending events from the pipeline manager.

        Args:
            last_seq: The last event sequence number received

        Returns:
            Dict with events list and latest_seq
        """
        # Use shorter timeout for poll - it's a fast read-only operation
        return await self._send_command({
            "cmd": "events.poll",
            "last_seq": last_seq,
        }, timeout=2.0, retries=0)  # Fast fail, don't retry


# Singleton instance
_client: Optional[PipelineClient] = None


def get_pipeline_client() -> PipelineClient:
    """Get or create pipeline client singleton"""
    global _client
    if _client is None:
        _client = PipelineClient()
    return _client

