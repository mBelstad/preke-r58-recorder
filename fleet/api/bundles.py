"""
Support bundle endpoints for Fleet Management.
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db
from ..models.schemas import (
    BundleRequest,
    SupportBundle,
    CommandType,
    PaginatedResponse,
)
from .auth import get_current_user, get_device_from_token, require_role
from .devices import _devices
from .commands import _commands

logger = logging.getLogger(__name__)
router = APIRouter()


# In-memory bundle storage (replace with actual database)
_bundles: List[dict] = []


@router.post("/devices/{device_id}/bundles", response_model=SupportBundle)
async def request_bundle(
    device_id: str,
    request: BundleRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Request a support bundle from a device.
    
    Creates a command for the device to generate and upload a bundle.
    """
    if device_id not in _devices:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device {device_id} not found",
        )
    
    # Create bundle record
    bundle_id = str(uuid4())
    bundle_record = {
        "id": bundle_id,
        "device_id": device_id,
        "storage_path": f"{settings.storage_path}/{device_id}/{bundle_id}.tar.gz",
        "size_bytes": None,
        "device_version": _devices[device_id].get("current_version"),
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(days=30),
        "status": "pending",
        "includes_logs": request.include_logs,
        "includes_config": request.include_config,
        "includes_recordings": request.include_recordings,
        "includes_diagnostics": request.include_diagnostics,
        "requested_by": user.get("id"),
        "notes": request.notes,
    }
    
    _bundles.append(bundle_record)
    
    # Create command for device
    command_record = {
        "id": str(uuid4()),
        "device_id": device_id,
        "type": CommandType.BUNDLE,
        "payload": {
            "bundle_id": bundle_id,
            "include_logs": request.include_logs,
            "include_config": request.include_config,
            "include_recordings": request.include_recordings,
            "include_diagnostics": request.include_diagnostics,
        },
        "status": "pending",
        "priority": 5,
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(hours=1),
        "created_by": user.get("id"),
    }
    
    _commands.append(command_record)
    
    logger.info(f"Requested support bundle {bundle_id} from device {device_id}")
    
    return SupportBundle(
        id=UUID(bundle_record["id"]),
        device_id=UUID(_devices[device_id]["id"]),
        storage_path=bundle_record["storage_path"],
        size_bytes=None,
        device_version=bundle_record.get("device_version"),
        created_at=bundle_record["created_at"],
        expires_at=bundle_record.get("expires_at"),
        status=bundle_record["status"],
        includes_logs=bundle_record["includes_logs"],
        includes_config=bundle_record["includes_config"],
        includes_recordings=bundle_record["includes_recordings"],
    )


@router.get("/devices/{device_id}/bundles", response_model=PaginatedResponse)
async def list_device_bundles(
    device_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List support bundles for a device.
    """
    if device_id not in _devices:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device {device_id} not found",
        )
    
    # Filter bundles
    device_bundles = [
        b for b in _bundles
        if b["device_id"] == device_id
    ]
    
    # Sort by creation time (newest first)
    device_bundles.sort(key=lambda b: b["created_at"], reverse=True)
    
    # Paginate
    total = len(device_bundles)
    start = (page - 1) * page_size
    end = start + page_size
    page_bundles = device_bundles[start:end]
    
    return PaginatedResponse(
        items=page_bundles,
        total=total,
        page=page,
        page_size=page_size,
        has_more=end < total,
    )


@router.post("/devices/{device_id}/bundles/upload")
async def upload_bundle(
    device_id: str,
    bundle_id: str = Query(...),
    bundle: UploadFile = File(...),
    device: dict = Depends(get_device_from_token),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a support bundle from a device.
    
    Called by the device agent after generating a bundle.
    """
    # Verify device_id matches token
    if device["device_id"] != device_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token does not match device_id",
        )
    
    # Find bundle record
    bundle_record = None
    for b in _bundles:
        if b["id"] == bundle_id:
            bundle_record = b
            break
    
    if not bundle_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bundle {bundle_id} not found",
        )
    
    if bundle_record["device_id"] != device_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bundle does not belong to this device",
        )
    
    # Save bundle file
    # In production, upload to S3 or similar
    import os
    os.makedirs(os.path.dirname(bundle_record["storage_path"]), exist_ok=True)
    
    content = await bundle.read()
    with open(bundle_record["storage_path"], "wb") as f:
        f.write(content)
    
    # Update bundle record
    bundle_record["status"] = "ready"
    bundle_record["size_bytes"] = len(content)
    
    logger.info(f"Received support bundle {bundle_id} from device {device_id} ({len(content)} bytes)")
    
    return {
        "id": bundle_id,
        "status": "ready",
        "size_bytes": len(content),
    }


@router.get("/bundles/{bundle_id}")
async def get_bundle(
    bundle_id: str,
    user: dict = Depends(get_current_user),
):
    """
    Get details of a support bundle.
    """
    for b in _bundles:
        if b["id"] == bundle_id:
            return SupportBundle(
                id=UUID(b["id"]),
                device_id=UUID(_devices[b["device_id"]]["id"]) if b["device_id"] in _devices else UUID(int=0),
                storage_path=b["storage_path"],
                size_bytes=b.get("size_bytes"),
                device_version=b.get("device_version"),
                created_at=b["created_at"],
                expires_at=b.get("expires_at"),
                status=b["status"],
                includes_logs=b.get("includes_logs", True),
                includes_config=b.get("includes_config", True),
                includes_recordings=b.get("includes_recordings", False),
            )
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Bundle {bundle_id} not found",
    )


@router.get("/bundles/{bundle_id}/download")
async def download_bundle(
    bundle_id: str,
    user: dict = Depends(get_current_user),
):
    """
    Download a support bundle.
    """
    for b in _bundles:
        if b["id"] == bundle_id:
            if b["status"] != "ready":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Bundle is not ready (status: {b['status']})",
                )
            
            import os
            if not os.path.exists(b["storage_path"]):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Bundle file not found",
                )
            
            # Update download stats
            b["download_count"] = b.get("download_count", 0) + 1
            b["last_downloaded_at"] = datetime.utcnow()
            
            return FileResponse(
                path=b["storage_path"],
                filename=f"r58-bundle-{bundle_id[:8]}.tar.gz",
                media_type="application/gzip",
            )
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Bundle {bundle_id} not found",
    )


@router.delete("/bundles/{bundle_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bundle(
    bundle_id: str,
    user: dict = Depends(get_current_user),
):
    """
    Delete a support bundle.
    """
    for i, b in enumerate(_bundles):
        if b["id"] == bundle_id:
            # Delete file if exists
            import os
            if os.path.exists(b["storage_path"]):
                os.remove(b["storage_path"])
            
            _bundles.pop(i)
            logger.info(f"Deleted bundle {bundle_id}")
            return
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Bundle {bundle_id} not found",
    )

