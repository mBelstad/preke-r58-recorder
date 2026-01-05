"""Recording integrity validation using ffprobe.

This module provides post-recording validation to ensure files are not corrupted.
"""
import asyncio
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class IntegrityResult:
    """Result of integrity check"""
    valid: bool
    file_path: Path
    file_size_bytes: int
    duration_seconds: Optional[float] = None
    has_video: bool = False
    has_audio: bool = False
    video_codec: Optional[str] = None
    audio_codec: Optional[str] = None
    error_message: Optional[str] = None


class RecordingIntegrityChecker:
    """Validates recording file integrity using ffprobe."""
    
    def __init__(self, ffprobe_path: str = "ffprobe"):
        """Initialize checker.
        
        Args:
            ffprobe_path: Path to ffprobe binary (default: system PATH)
        """
        self.ffprobe_path = ffprobe_path
    
    async def validate(
        self,
        file_path: Path,
        expected_duration: Optional[float] = None,
        duration_tolerance: float = 2.0,
    ) -> IntegrityResult:
        """Validate recording file integrity.
        
        Checks:
        1. File exists and size > 0
        2. File can be probed with ffprobe
        3. Duration matches expected (within tolerance)
        4. Has valid video stream
        
        Args:
            file_path: Path to recording file
            expected_duration: Expected duration in seconds (optional)
            duration_tolerance: Allowed difference in seconds (default: 2.0)
        
        Returns:
            IntegrityResult with validation details
        """
        # Check 1: File exists and has content
        if not file_path.exists():
            return IntegrityResult(
                valid=False,
                file_path=file_path,
                file_size_bytes=0,
                error_message="File does not exist",
            )
        
        file_size = file_path.stat().st_size
        if file_size == 0:
            return IntegrityResult(
                valid=False,
                file_path=file_path,
                file_size_bytes=0,
                error_message="File is empty (0 bytes)",
            )
        
        # Check 2: Probe file with ffprobe
        try:
            probe_data = await self._probe_file(file_path)
        except Exception as e:
            logger.error(f"ffprobe failed for {file_path}: {e}")
            return IntegrityResult(
                valid=False,
                file_path=file_path,
                file_size_bytes=file_size,
                error_message=f"ffprobe failed: {str(e)}",
            )
        
        # Extract stream information
        video_stream = None
        audio_stream = None
        
        for stream in probe_data.get("streams", []):
            if stream.get("codec_type") == "video" and not video_stream:
                video_stream = stream
            elif stream.get("codec_type") == "audio" and not audio_stream:
                audio_stream = stream
        
        # Check 3: Must have video stream
        if not video_stream:
            return IntegrityResult(
                valid=False,
                file_path=file_path,
                file_size_bytes=file_size,
                error_message="No video stream found",
            )
        
        # Extract duration
        duration = None
        format_info = probe_data.get("format", {})
        
        if "duration" in format_info:
            try:
                duration = float(format_info["duration"])
            except (ValueError, TypeError):
                pass
        
        # Check 4: Duration validation (if expected provided)
        duration_valid = True
        if expected_duration is not None and duration is not None:
            diff = abs(duration - expected_duration)
            if diff > duration_tolerance:
                logger.warning(
                    f"Duration mismatch for {file_path}: "
                    f"expected {expected_duration}s, got {duration}s (diff: {diff}s)"
                )
                duration_valid = False
        
        # Build result
        result = IntegrityResult(
            valid=duration_valid,
            file_path=file_path,
            file_size_bytes=file_size,
            duration_seconds=duration,
            has_video=video_stream is not None,
            has_audio=audio_stream is not None,
            video_codec=video_stream.get("codec_name") if video_stream else None,
            audio_codec=audio_stream.get("codec_name") if audio_stream else None,
            error_message=None if duration_valid else "Duration mismatch",
        )
        
        return result
    
    async def _probe_file(self, file_path: Path) -> dict:
        """Run ffprobe on file and return JSON output.
        
        Args:
            file_path: Path to file
        
        Returns:
            Parsed JSON from ffprobe
        
        Raises:
            Exception: If ffprobe fails or returns invalid JSON
        """
        cmd = [
            self.ffprobe_path,
            "-v", "error",  # Only show errors
            "-print_format", "json",  # Output as JSON
            "-show_format",  # Show container format
            "-show_streams",  # Show stream info
            str(file_path),
        ]
        
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            raise Exception(f"ffprobe exited with code {proc.returncode}: {error_msg}")
        
        try:
            return json.loads(stdout.decode())
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse ffprobe JSON: {e}")
    
    def log_result(self, result: IntegrityResult) -> None:
        """Log integrity check result.
        
        Args:
            result: IntegrityResult to log
        """
        if result.valid:
            logger.info(
                f"✓ Recording valid: {result.file_path.name} "
                f"({result.file_size_bytes / 1024 / 1024:.1f}MB, "
                f"{result.duration_seconds:.1f}s, "
                f"video: {result.video_codec}, "
                f"audio: {result.audio_codec or 'none'})"
            )
        else:
            logger.warning(
                f"✗ Recording integrity issue: {result.file_path.name} - "
                f"{result.error_message}"
            )

