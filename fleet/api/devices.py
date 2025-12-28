"""
Device management endpoints for Fleet Management.
"""
import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from ..config import settings
from ..database import get_db
from ..models.schemas import (
    Device,
    DeviceRegister,
    DeviceRegisterResponse,
    DeviceUpdate,
    DeviceSummary,
    DeviceStatus,
    PaginatedResponse,
)
from .auth import (
    get_current_user,
    get_device_from_token,
    require_role,
    generate_device_token,
    hash_token,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# In-memory storage for demo (replace with actual database in production)
_devices: dict[str, dict] = {}


@router.post("/devices/register", response_model=DeviceRegisterResponse)
async def register_device(
    device: DeviceRegister,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new device with the fleet.
    
    This endpoint is called by devices during initial setup.
    Returns a unique device token that must be stored securely.
    """
    # Check if device_id already exists
    if device.device_id in _devices:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Device {device.device_id} is already registered",
        )
    
    # Generate secure token
    token = generate_device_token()
    token_hash = hash_token(token)
    
    # Create device record
    device_record = {
        "id": str(UUID(int=len(_devices) + 1)),
        "device_id": device.device_id,
        "name": device.name,
        "org_id": "00000000-0000-0000-0000-000000000001",  # Default org
        "token_hash": token_hash,
        "status": DeviceStatus.OFFLINE,
        "current_version": device.current_version,
        "platform": device.platform,
        "arch": device.arch,
        "serial_number": device.serial_number,
        "mac_address": device.mac_address,
        "capabilities": device.capabilities or {},
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "last_heartbeat": None,
        "tags": [],
        "metadata": {},
        "update_channel": "stable",
        "target_version": None,
        "location": None,
    }
    
    _devices[device.device_id] = device_record
    
    logger.info(f"Registered new device: {device.device_id}")
    
    return DeviceRegisterResponse(
        device_id=device.device_id,
        token=token,  # Only returned once!
        fleet_url=settings.releases_base_url,
    )


@router.get("/devices", response_model=PaginatedResponse)
async def list_devices(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    status_filter: Optional[DeviceStatus] = Query(None, alias="status"),
    search: Optional[str] = None,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all devices in the organization.
    
    Supports filtering by status and searching by name/device_id.
    """
    # Filter devices
    devices = list(_devices.values())
    
    # Filter by org (in production)
    # devices = [d for d in devices if d["org_id"] == user["org_id"]]
    
    # Filter by status
    if status_filter:
        devices = [d for d in devices if d["status"] == status_filter]
    
    # Search
    if search:
        search_lower = search.lower()
        devices = [
            d for d in devices
            if search_lower in d["device_id"].lower()
            or search_lower in d["name"].lower()
        ]
    
    # Paginate
    total = len(devices)
    start = (page - 1) * page_size
    end = start + page_size
    page_devices = devices[start:end]
    
    return PaginatedResponse(
        items=page_devices,
        total=total,
        page=page,
        page_size=page_size,
        has_more=end < total,
    )


@router.get("/devices/{device_id}", response_model=DeviceSummary)
async def get_device(
    device_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed information about a specific device.
    """
    if device_id not in _devices:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device {device_id} not found",
        )
    
    device = _devices[device_id]
    
    # In production, join with latest heartbeat data
    return DeviceSummary(
        **{
            "id": UUID(device["id"]),
            "device_id": device["device_id"],
            "name": device["name"],
            "org_id": UUID(device["org_id"]),
            "status": device["status"],
            "last_heartbeat": device.get("last_heartbeat"),
            "current_version": device.get("current_version"),
            "target_version": device.get("target_version"),
            "update_channel": device.get("update_channel", "stable"),
            "platform": device.get("platform"),
            "arch": device.get("arch", "arm64"),
            "capabilities": device.get("capabilities", {}),
            "location": device.get("location"),
            "tags": device.get("tags", []),
            "metadata": device.get("metadata", {}),
            "created_at": device["created_at"],
            "updated_at": device["updated_at"],
            # Metrics from latest heartbeat
            "cpu_percent": None,
            "mem_percent": None,
            "disk_free_gb": None,
            "temperature_c": None,
            "recording_active": False,
            "mixer_active": False,
            "uptime_seconds": None,
            "pending_commands": 0,
            "active_alerts": 0,
        }
    )


@router.patch("/devices/{device_id}", response_model=Device)
async def update_device(
    device_id: str,
    update: DeviceUpdate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update device metadata.
    
    Operators can update name, location, tags, and metadata.
    Admins can also change update_channel and target_version.
    """
    if device_id not in _devices:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device {device_id} not found",
        )
    
    device = _devices[device_id]
    
    # Apply updates
    update_data = update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        device[key] = value
    
    device["updated_at"] = datetime.utcnow()
    
    logger.info(f"Updated device {device_id}: {list(update_data.keys())}")
    
    return Device(
        id=UUID(device["id"]),
        device_id=device["device_id"],
        name=device["name"],
        org_id=UUID(device["org_id"]),
        status=device["status"],
        last_heartbeat=device.get("last_heartbeat"),
        current_version=device.get("current_version"),
        target_version=device.get("target_version"),
        update_channel=device.get("update_channel", "stable"),
        platform=device.get("platform"),
        arch=device.get("arch", "arm64"),
        capabilities=device.get("capabilities", {}),
        location=device.get("location"),
        tags=device.get("tags", []),
        metadata=device.get("metadata", {}),
        created_at=device["created_at"],
        updated_at=device["updated_at"],
    )


@router.delete("/devices/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(
    device_id: str,
    user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """
    Decommission a device.
    
    Removes the device from fleet management.
    This action requires admin privileges.
    """
    if device_id not in _devices:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device {device_id} not found",
        )
    
    del _devices[device_id]
    
    logger.info(f"Deleted device {device_id}")


@router.post("/devices/{device_id}/rotate-token", response_model=dict)
async def rotate_device_token(
    device_id: str,
    user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """
    Rotate the device authentication token.
    
    The new token must be updated on the device.
    This action requires admin privileges.
    """
    if device_id not in _devices:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device {device_id} not found",
        )
    
    # Generate new token
    new_token = generate_device_token()
    _devices[device_id]["token_hash"] = hash_token(new_token)
    _devices[device_id]["updated_at"] = datetime.utcnow()
    
    logger.warning(f"Rotated token for device {device_id}")
    
    return {
        "device_id": device_id,
        "token": new_token,  # Only returned once!
        "message": "Token rotated. Update the device configuration immediately.",
    }

