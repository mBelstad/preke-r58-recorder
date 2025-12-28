"""Recording session management endpoints"""
import asyncio
import json
import logging
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ...config import Settings, get_settings
from ...media.pipeline_client import get_pipeline_client

router = APIRouter(prefix="/api/v1/recorder", tags=["Recorder"])
logger = logging.getLogger(__name__)

# Recordings directory
RECORDINGS_DIR = Path("/mnt/sdcard/recordings")

# Minimum disk space required to start recording (in GB)
MIN_DISK_SPACE_GB = 2.0

# Lock to prevent concurrent start/stop operations
_recording_lock = asyncio.Lock()


class StartRecordingRequest(BaseModel):
    """Request to start recording"""
    name: Optional[str] = None
    inputs: Optional[List[str]] = None  # If None, use all available


class StartRecordingResponse(BaseModel):
    """Response after starting recording"""
    session_id: str
    name: Optional[str]
    started_at: datetime
    inputs: List[str]
    status: str


class StopRecordingResponse(BaseModel):
    """Response after stopping recording"""
    session_id: str
    duration_ms: int
    files: dict
    status: str


class RecorderStatus(BaseModel):
    """Current recorder status"""
    status: str  # "idle", "recording", "starting", "stopping"
    session_id: Optional[str] = None
    duration_ms: int = 0
    inputs: List[str] = []


class RecordingSession(BaseModel):
    """Recording session details"""
    id: str
    name: Optional[str]
    started_at: datetime
    ended_at: Optional[datetime]
    status: str
    total_bytes: int
    files: List[dict]


class InputStatus(BaseModel):
    """Input status with signal detection"""
    id: str
    label: str
    has_signal: bool
    is_recording: bool
    resolution: Optional[str] = None
    framerate: Optional[int] = None
    device_path: Optional[str] = None


@router.get("/inputs", response_model=List[InputStatus])
async def get_inputs_status(
    settings: Settings = Depends(get_settings)
) -> List[InputStatus]:
    """
    Get real-time input status with signal detection.

    Returns status for all configured inputs including:
    - has_signal: Whether HDMI signal is detected
    - resolution: Detected resolution if signal present
    - framerate: Detected framerate if signal present
    - is_recording: Whether this input is currently recording
    """
    client = get_pipeline_client()

    # Get device check from pipeline manager
    device_check = await client.check_devices()

    # Get recording status to know which inputs are recording
    recording_status = await client.get_recording_status()
    recording_inputs = set()
    if recording_status.get("recording"):
        recording_inputs = set(recording_status.get("bytes_written", {}).keys())

    inputs = []

    if device_check.get("devices"):
        # Build from real device data
        for idx, (input_id, info) in enumerate(device_check["devices"].items()):
            caps = info.get("capabilities", {})
            has_signal = caps.get("has_signal", False)

            # Get resolution/framerate only if signal present
            resolution = None
            framerate = None
            if has_signal:
                width = caps.get("width", 0)
                height = caps.get("height", 0)
                resolution = f"{width}x{height}" if width and height else None
                framerate = caps.get("framerate")

            inputs.append(InputStatus(
                id=input_id,
                label=f"HDMI {idx + 1}",
                has_signal=has_signal,
                is_recording=input_id in recording_inputs,
                resolution=resolution,
                framerate=framerate,
                device_path=info.get("device"),
            ))
    else:
        # Fallback to configured inputs if pipeline manager unavailable
        for idx, input_id in enumerate(settings.enabled_inputs):
            inputs.append(InputStatus(
                id=input_id,
                label=f"HDMI {idx + 1}",
                has_signal=False,  # Unknown
                is_recording=input_id in recording_inputs,
                resolution=None,
                framerate=None,
            ))

    return inputs


@router.get("/status", response_model=RecorderStatus)
async def get_recorder_status(
    settings: Settings = Depends(get_settings)
) -> RecorderStatus:
    """Get current recorder status"""
    client = get_pipeline_client()
    status = await client.get_recording_status()

    if status.get("error"):
        return RecorderStatus(status="idle")

    if status.get("recording"):
        return RecorderStatus(
            status="recording",
            session_id=status.get("session_id"),
            duration_ms=status.get("duration_ms", 0),
            inputs=list(status.get("bytes_written", {}).keys()),
        )

    return RecorderStatus(status="idle")


def check_disk_space(path: str = "/opt/r58/recordings") -> tuple[float, bool]:
    """
    Check available disk space.
    Returns (available_gb, is_sufficient).
    """
    try:
        usage = shutil.disk_usage(path)
        available_gb = usage.free / (1024 ** 3)
        return available_gb, available_gb >= MIN_DISK_SPACE_GB
    except OSError as e:
        logger.warning(f"Failed to check disk space: {e}")
        # If we can't check, assume it's OK but log warning
        return 0.0, True


@router.post("/start", response_model=StartRecordingResponse)
async def start_recording(
    request: StartRecordingRequest,
    settings: Settings = Depends(get_settings),
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key"),
) -> StartRecordingResponse:
    """
    Start recording on all or specified inputs.

    Supports idempotency via X-Idempotency-Key header - if the same key is sent
    while already recording, returns the existing session instead of an error.
    """
    # Acquire lock to prevent race conditions
    try:
        await asyncio.wait_for(_recording_lock.acquire(), timeout=5.0)
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=503,
            detail="Recording operation in progress, please retry"
        )

    try:
        return await _start_recording_impl(request, settings, x_idempotency_key)
    finally:
        _recording_lock.release()


async def _start_recording_impl(
    request: StartRecordingRequest,
    settings: Settings,
    idempotency_key: Optional[str],
) -> StartRecordingResponse:
    """Internal implementation of start_recording with all checks."""
    client = get_pipeline_client()

    # 1. Check disk space first
    available_gb, is_sufficient = check_disk_space()
    if not is_sufficient:
        logger.error(f"Insufficient disk space: {available_gb:.1f}GB available, need {MIN_DISK_SPACE_GB}GB")
        raise HTTPException(
            status_code=507,  # Insufficient Storage
            detail=f"Insufficient disk space: {available_gb:.1f}GB available, need {MIN_DISK_SPACE_GB}GB minimum"
        )

    # 2. Check if already recording
    current_status = await client.get_recording_status()
    if current_status.get("recording"):
        current_session = current_status.get("session_id")

        # If same idempotency key, return existing session (idempotent)
        if idempotency_key and current_session == idempotency_key:
            logger.info(f"Idempotent request for existing session: {current_session}")
            return StartRecordingResponse(
                session_id=current_session,
                name=request.name,
                started_at=datetime.now(),  # Approximate
                inputs=list(current_status.get("bytes_written", {}).keys()),
                status="recording",
            )

        # Different session already running
        raise HTTPException(
            status_code=409,  # Conflict
            detail=f"Already recording session: {current_session}"
        )

    # 3. Use configured inputs if not specified
    inputs = request.inputs or settings.enabled_inputs
    if not inputs:
        raise HTTPException(
            status_code=400,
            detail="No inputs specified and no default inputs configured"
        )

    # 4. Use idempotency key as session ID if provided
    session_id = idempotency_key if idempotency_key else None

    # 5. Start recording
    logger.info(f"Starting recording with inputs: {inputs}, session_id: {session_id}")
    result = await client.start_recording(session_id=session_id, inputs=inputs)

    if result.get("error"):
        logger.error(f"Failed to start recording: {result['error']}")
        raise HTTPException(status_code=400, detail=result["error"])

    logger.info(f"Recording started: session_id={result['session_id']}")
    return StartRecordingResponse(
        session_id=result["session_id"],
        name=request.name,
        started_at=datetime.now(),
        inputs=list(result.get("inputs", {}).keys()),
        status="recording",
    )


@router.post("/stop", response_model=StopRecordingResponse)
async def stop_recording(
    session_id: Optional[str] = None,
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key"),
) -> StopRecordingResponse:
    """
    Stop current recording.

    Supports idempotency - if already stopped, returns success.
    """
    # Acquire lock to prevent race conditions
    try:
        await asyncio.wait_for(_recording_lock.acquire(), timeout=5.0)
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=503,
            detail="Recording operation in progress, please retry"
        )

    try:
        return await _stop_recording_impl(session_id)
    finally:
        _recording_lock.release()


async def _stop_recording_impl(session_id: Optional[str]) -> StopRecordingResponse:
    """Internal implementation of stop_recording."""
    client = get_pipeline_client()

    # Check if currently recording
    current_status = await client.get_recording_status()
    if not current_status.get("recording"):
        # Already stopped - return idempotent success
        logger.info("Stop requested but not recording - returning success (idempotent)")
        return StopRecordingResponse(
            session_id=session_id or "",
            duration_ms=0,
            files={},
            status="stopped",
        )

    # If session_id specified, verify it matches
    current_session = current_status.get("session_id")
    if session_id and current_session != session_id:
        raise HTTPException(
            status_code=409,
            detail=f"Session mismatch: expected {session_id}, current is {current_session}"
        )

    logger.info(f"Stopping recording: session_id={current_session}")
    result = await client.stop_recording(session_id=session_id)

    if result.get("error"):
        logger.error(f"Failed to stop recording: {result['error']}")
        raise HTTPException(status_code=400, detail=result["error"])

    logger.info(f"Recording stopped: session_id={result.get('session_id')}")
    return StopRecordingResponse(
        session_id=result.get("session_id", ""),
        duration_ms=result.get("duration_ms", 0),
        files=result.get("files", {}),
        status="stopped",
    )


class RecordingFile(BaseModel):
    """Single recording file"""
    filename: str
    path: str
    size_bytes: int
    camera_id: str
    created_at: datetime


class SessionWithFiles(BaseModel):
    """Session with all its files for library view"""
    id: str
    name: Optional[str]
    date: str
    duration: str
    file_count: int
    total_size: str
    files: List[RecordingFile]


def parse_recording_filename(filename: str) -> Optional[Dict]:
    """Parse recording filename to extract session info.

    Format: {session_id}_{camera_id}_{timestamp}.mkv
    Example: abc123_cam1_20251228_120000.mkv
    """
    pattern = r'^([^_]+)_([^_]+)_(\d{8})_(\d{6})\.mkv$'
    match = re.match(pattern, filename)
    if match:
        session_id, camera_id, date_str, time_str = match.groups()
        try:
            timestamp = datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
            return {
                'session_id': session_id,
                'camera_id': camera_id,
                'timestamp': timestamp,
            }
        except ValueError:
            pass
    return None


def get_session_metadata(session_id: str) -> Dict:
    """Get or create session metadata file."""
    metadata_path = RECORDINGS_DIR / f"{session_id}.json"
    if metadata_path.exists():
        try:
            with open(metadata_path) as f:
                return json.load(f)
        except Exception:
            pass
    return {'name': None}


def save_session_metadata(session_id: str, metadata: Dict) -> bool:
    """Save session metadata file."""
    metadata_path = RECORDINGS_DIR / f"{session_id}.json"
    try:
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Failed to save metadata for {session_id}: {e}")
        return False


def format_duration(seconds: float) -> str:
    """Format duration as HH:MM:SS."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours}:{minutes:02d}:{secs:02d}"


def format_size(bytes: int) -> str:
    """Format size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes < 1024:
            return f"{bytes:.1f} {unit}"
        bytes /= 1024
    return f"{bytes:.1f} PB"


@router.get("/sessions", response_model=List[SessionWithFiles])
async def list_sessions(
    limit: int = 50,
    offset: int = 0,
) -> List[SessionWithFiles]:
    """List recording sessions from the recordings directory."""
    if not RECORDINGS_DIR.exists():
        return []

    # Scan recordings directory for .mkv files
    sessions_map: Dict[str, List[RecordingFile]] = {}

    for file_path in RECORDINGS_DIR.glob("*.mkv"):
        parsed = parse_recording_filename(file_path.name)
        if not parsed:
            continue

        session_id = parsed['session_id']
        stat = file_path.stat()

        recording_file = RecordingFile(
            filename=file_path.name,
            path=str(file_path),
            size_bytes=stat.st_size,
            camera_id=parsed['camera_id'],
            created_at=parsed['timestamp'],
        )

        if session_id not in sessions_map:
            sessions_map[session_id] = []
        sessions_map[session_id].append(recording_file)

    # Build session list
    sessions = []
    for session_id, files in sessions_map.items():
        if not files:
            continue

        metadata = get_session_metadata(session_id)
        files_sorted = sorted(files, key=lambda f: f.created_at)

        # Calculate total size and duration estimate
        total_size = sum(f.size_bytes for f in files)
        first_file = files_sorted[0]
        _last_file = files_sorted[-1] if len(files_sorted) > 1 else first_file

        # Estimate duration from first file creation time
        # For more accurate duration, we'd need to probe the files with ffprobe
        duration_estimate = 0.0  # Placeholder

        sessions.append(SessionWithFiles(
            id=session_id,
            name=metadata.get('name'),
            date=first_file.created_at.strftime("%Y-%m-%d"),
            duration=format_duration(duration_estimate) if duration_estimate else "Unknown",
            file_count=len(files),
            total_size=format_size(total_size),
            files=files,
        ))

    # Sort by date (newest first)
    sessions.sort(key=lambda s: s.files[0].created_at if s.files else datetime.min, reverse=True)

    # Apply pagination
    return sessions[offset:offset + limit]


@router.get("/sessions/{session_id}", response_model=SessionWithFiles)
async def get_session(session_id: str) -> SessionWithFiles:
    """Get details of a specific session."""
    if not RECORDINGS_DIR.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    # Find files matching this session
    files = []
    for file_path in RECORDINGS_DIR.glob(f"{session_id}_*.mkv"):
        parsed = parse_recording_filename(file_path.name)
        if not parsed:
            continue

        stat = file_path.stat()
        files.append(RecordingFile(
            filename=file_path.name,
            path=str(file_path),
            size_bytes=stat.st_size,
            camera_id=parsed['camera_id'],
            created_at=parsed['timestamp'],
        ))

    if not files:
        raise HTTPException(status_code=404, detail="Session not found")

    metadata = get_session_metadata(session_id)
    files_sorted = sorted(files, key=lambda f: f.created_at)
    total_size = sum(f.size_bytes for f in files)
    first_file = files_sorted[0]

    return SessionWithFiles(
        id=session_id,
        name=metadata.get('name'),
        date=first_file.created_at.strftime("%Y-%m-%d"),
        duration="Unknown",  # Would need ffprobe for accurate duration
        file_count=len(files),
        total_size=format_size(total_size),
        files=files,
    )


class RenameSessionRequest(BaseModel):
    """Request to rename a session"""
    name: str


@router.patch("/sessions/{session_id}")
async def rename_session(
    session_id: str,
    request: RenameSessionRequest,
) -> Dict:
    """Rename a recording session."""
    # Verify session exists
    session_files = list(RECORDINGS_DIR.glob(f"{session_id}_*.mkv"))
    if not session_files:
        raise HTTPException(status_code=404, detail="Session not found")

    # Save metadata
    metadata = get_session_metadata(session_id)
    metadata['name'] = request.name

    if save_session_metadata(session_id, metadata):
        return {"success": True, "session_id": session_id, "name": request.name}
    else:
        raise HTTPException(status_code=500, detail="Failed to save session metadata")


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str) -> Dict:
    """Delete a recording session and all its files."""
    if not RECORDINGS_DIR.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    # Find all files for this session
    files_to_delete = list(RECORDINGS_DIR.glob(f"{session_id}_*.mkv"))
    metadata_file = RECORDINGS_DIR / f"{session_id}.json"

    if not files_to_delete:
        raise HTTPException(status_code=404, detail="Session not found")

    deleted_count = 0
    total_bytes = 0

    for file_path in files_to_delete:
        try:
            total_bytes += file_path.stat().st_size
            file_path.unlink()
            deleted_count += 1
            logger.info(f"Deleted recording file: {file_path}")
        except Exception as e:
            logger.error(f"Failed to delete {file_path}: {e}")

    # Delete metadata file if exists
    if metadata_file.exists():
        try:
            metadata_file.unlink()
        except Exception:
            pass

    return {
        "success": True,
        "session_id": session_id,
        "deleted_files": deleted_count,
        "freed_bytes": total_bytes,
    }


@router.get("/sessions/{session_id}/files/{filename}")
async def download_file(session_id: str, filename: str):
    """Download a specific recording file."""
    file_path = RECORDINGS_DIR / filename

    # Security check - ensure file is within recordings directory
    if not file_path.resolve().is_relative_to(RECORDINGS_DIR.resolve()):
        raise HTTPException(status_code=403, detail="Access denied")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    # Verify filename matches session
    if not filename.startswith(f"{session_id}_"):
        raise HTTPException(status_code=403, detail="File does not belong to session")

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="video/x-matroska",
    )

