"""Recording session management endpoints"""
from typing import List, Optional
from datetime import datetime
import asyncio
import shutil
import logging

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel

from ...config import Settings, get_settings
from ...media.pipeline_client import get_pipeline_client

router = APIRouter(prefix="/api/v1/recorder", tags=["Recorder"])
logger = logging.getLogger(__name__)

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
        async with asyncio.wait_for(_recording_lock.acquire(), timeout=5.0):
            try:
                return await _start_recording_impl(request, settings, x_idempotency_key)
            finally:
                _recording_lock.release()
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=503,
            detail="Recording operation in progress, please retry"
        )


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
        async with asyncio.wait_for(_recording_lock.acquire(), timeout=5.0):
            try:
                return await _stop_recording_impl(session_id)
            finally:
                _recording_lock.release()
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=503,
            detail="Recording operation in progress, please retry"
        )


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


@router.get("/sessions", response_model=List[RecordingSession])
async def list_sessions(
    limit: int = 50,
    offset: int = 0,
) -> List[RecordingSession]:
    """List recording sessions"""
    # TODO: Fetch from database
    return []


@router.get("/sessions/{session_id}", response_model=RecordingSession)
async def get_session(session_id: str) -> RecordingSession:
    """Get details of a specific session"""
    # TODO: Fetch from database
    raise HTTPException(status_code=404, detail="Session not found")

