"""
Heartbeat endpoints for Fleet Management.
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db
from ..models.schemas import (
    HeartbeatCreate,
    HeartbeatResponse,
    Heartbeat,
    DeviceStatus,
    PaginatedResponse,
)
from .auth import get_device_from_token, get_current_user
from .devices import _devices

logger = logging.getLogger(__name__)
router = APIRouter()


# In-memory heartbeat storage (replace with actual database)
_heartbeats: List[dict] = []


@router.post("/devices/{device_id}/heartbeat", response_model=HeartbeatResponse)
async def receive_heartbeat(
    device_id: str,
    heartbeat: HeartbeatCreate,
    device: dict = Depends(get_device_from_token),
    db: AsyncSession = Depends(get_db),
):
    """
    Receive heartbeat from a device.
    
    Devices should send heartbeats every 60 seconds.
    The response includes pending command count and update target if any.
    """
    # Verify device_id matches token
    if device["device_id"] != device_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token does not match device_id",
        )
    
    # Update device status
    if device_id in _devices:
        _devices[device_id]["status"] = DeviceStatus.ONLINE
        _devices[device_id]["last_heartbeat"] = datetime.utcnow()
        _devices[device_id]["current_version"] = heartbeat.version
        
        # Update capabilities if changed significantly
        # _devices[device_id]["capabilities"] = ...
    
    # Store heartbeat
    heartbeat_record = {
        "id": len(_heartbeats) + 1,
        "device_id": device_id,
        "received_at": datetime.utcnow(),
        "cpu_percent": heartbeat.metrics.cpu_percent,
        "mem_percent": heartbeat.metrics.mem_percent,
        "disk_free_gb": heartbeat.metrics.disk_free_gb,
        "disk_total_gb": heartbeat.metrics.disk_total_gb,
        "temperature_c": heartbeat.metrics.temperature_c,
        "uptime_seconds": heartbeat.uptime_seconds,
        "recording_active": heartbeat.status.recording_active,
        "mixer_active": heartbeat.status.mixer_active,
        "active_inputs": heartbeat.status.active_inputs,
        "degradation_level": heartbeat.status.degradation_level,
        "errors": heartbeat.errors,
    }
    _heartbeats.append(heartbeat_record)
    
    # Keep only last 1000 heartbeats in memory
    if len(_heartbeats) > 1000:
        _heartbeats.pop(0)
    
    # Log warnings for concerning metrics
    if heartbeat.metrics.disk_free_gb < 1.0:
        logger.warning(f"Device {device_id}: Low disk space ({heartbeat.metrics.disk_free_gb:.1f}GB)")
    if heartbeat.metrics.cpu_percent > 90:
        logger.warning(f"Device {device_id}: High CPU usage ({heartbeat.metrics.cpu_percent:.1f}%)")
    if heartbeat.errors:
        logger.warning(f"Device {device_id}: Errors reported: {heartbeat.errors}")
    
    # Check for pending commands
    from .commands import _commands
    pending_count = sum(
        1 for c in _commands
        if c["device_id"] == device_id and c["status"] == "pending"
    )
    
    # Check for update target
    target_version = None
    if device_id in _devices:
        target_version = _devices[device_id].get("target_version")
    
    return HeartbeatResponse(
        ack=True,
        commands_pending=pending_count,
        target_version=target_version,
        server_time=datetime.utcnow(),
    )


@router.get("/devices/{device_id}/heartbeats", response_model=PaginatedResponse)
async def get_heartbeat_history(
    device_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    since: Optional[datetime] = None,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get heartbeat history for a device.
    
    Returns recent heartbeats with metrics and status information.
    """
    if device_id not in _devices:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device {device_id} not found",
        )
    
    # Filter heartbeats for this device
    device_heartbeats = [
        h for h in _heartbeats
        if h["device_id"] == device_id
    ]
    
    # Filter by time if specified
    if since:
        device_heartbeats = [
            h for h in device_heartbeats
            if h["received_at"] >= since
        ]
    
    # Sort by time (newest first)
    device_heartbeats.sort(key=lambda h: h["received_at"], reverse=True)
    
    # Paginate
    total = len(device_heartbeats)
    start = (page - 1) * page_size
    end = start + page_size
    page_heartbeats = device_heartbeats[start:end]
    
    return PaginatedResponse(
        items=page_heartbeats,
        total=total,
        page=page,
        page_size=page_size,
        has_more=end < total,
    )


@router.get("/devices/{device_id}/metrics")
async def get_device_metrics(
    device_id: str,
    hours: int = Query(24, ge=1, le=168),  # Max 1 week
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get aggregated metrics for a device.
    
    Returns metrics over the specified time period for charting.
    """
    if device_id not in _devices:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device {device_id} not found",
        )
    
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    
    # Filter heartbeats
    device_heartbeats = [
        h for h in _heartbeats
        if h["device_id"] == device_id and h["received_at"] >= cutoff
    ]
    
    if not device_heartbeats:
        return {
            "device_id": device_id,
            "period_hours": hours,
            "data_points": 0,
            "metrics": {},
        }
    
    # Calculate aggregates
    cpu_values = [h["cpu_percent"] for h in device_heartbeats if h.get("cpu_percent")]
    mem_values = [h["mem_percent"] for h in device_heartbeats if h.get("mem_percent")]
    disk_values = [h["disk_free_gb"] for h in device_heartbeats if h.get("disk_free_gb")]
    temp_values = [h["temperature_c"] for h in device_heartbeats if h.get("temperature_c")]
    
    def calc_stats(values):
        if not values:
            return None
        return {
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "latest": values[-1] if values else None,
        }
    
    return {
        "device_id": device_id,
        "period_hours": hours,
        "data_points": len(device_heartbeats),
        "metrics": {
            "cpu_percent": calc_stats(cpu_values),
            "mem_percent": calc_stats(mem_values),
            "disk_free_gb": calc_stats(disk_values),
            "temperature_c": calc_stats(temp_values),
        },
        "recording_time_minutes": sum(
            1 for h in device_heartbeats if h.get("recording_active")
        ),
        "mixer_active_minutes": sum(
            1 for h in device_heartbeats if h.get("mixer_active")
        ),
    }

