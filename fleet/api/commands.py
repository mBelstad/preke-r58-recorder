"""
Remote command endpoints for Fleet Management.
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db
from ..models.schemas import (
    Command,
    CommandCreate,
    CommandUpdate,
    CommandStatus,
    CommandType,
    PaginatedResponse,
)
from .auth import get_device_from_token, get_current_user, require_role
from .devices import _devices

logger = logging.getLogger(__name__)
router = APIRouter()


# In-memory command storage (replace with actual database)
_commands: List[dict] = []


@router.post("/devices/{device_id}/commands", response_model=Command)
async def create_command(
    device_id: str,
    command: CommandCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Queue a command for a device.
    
    Commands are picked up by the device agent on next poll.
    Operators can create most commands, admin required for updates.
    """
    if device_id not in _devices:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device {device_id} not found",
        )
    
    # Validate permissions for command type
    if command.type == CommandType.UPDATE and user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required to issue update commands",
        )
    
    # Set default expiry
    expires_at = command.expires_at
    if not expires_at:
        expires_at = datetime.utcnow() + timedelta(hours=settings.command_default_expiry_hours)
    
    command_record = {
        "id": str(uuid4()),
        "device_id": device_id,
        "type": command.type,
        "payload": command.payload,
        "status": CommandStatus.PENDING,
        "priority": command.priority,
        "created_at": datetime.utcnow(),
        "sent_at": None,
        "acked_at": None,
        "completed_at": None,
        "expires_at": expires_at,
        "result": None,
        "error": None,
        "created_by": user.get("id"),
        "notes": command.notes,
    }
    
    _commands.append(command_record)
    
    logger.info(f"Created command {command_record['id']} for device {device_id}: {command.type}")
    
    return Command(
        id=UUID(command_record["id"]),
        device_id=UUID(_devices[device_id]["id"]),
        type=command_record["type"],
        payload=command_record["payload"],
        status=command_record["status"],
        priority=command_record["priority"],
        created_at=command_record["created_at"],
        expires_at=command_record["expires_at"],
    )


@router.get("/devices/{device_id}/commands", response_model=List[Command])
async def list_device_commands(
    device_id: str,
    status_filter: Optional[CommandStatus] = Query(None, alias="status"),
    device: dict = Depends(get_device_from_token),
    db: AsyncSession = Depends(get_db),
):
    """
    List pending commands for a device.
    
    Called by device agent to poll for commands.
    Returns commands sorted by priority (highest first).
    """
    # Verify device_id matches token
    if device["device_id"] != device_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token does not match device_id",
        )
    
    # Filter commands
    device_commands = [
        c for c in _commands
        if c["device_id"] == device_id
    ]
    
    # Apply status filter (default to pending)
    if status_filter:
        device_commands = [c for c in device_commands if c["status"] == status_filter]
    else:
        # Default: return pending commands
        device_commands = [c for c in device_commands if c["status"] == CommandStatus.PENDING]
    
    # Remove expired commands
    now = datetime.utcnow()
    device_commands = [
        c for c in device_commands
        if not c.get("expires_at") or c["expires_at"] > now
    ]
    
    # Sort by priority (lower number = higher priority)
    device_commands.sort(key=lambda c: c["priority"])
    
    # Mark as sent
    for c in device_commands:
        if c["status"] == CommandStatus.PENDING:
            c["status"] = CommandStatus.SENT
            c["sent_at"] = now
    
    return [
        Command(
            id=UUID(c["id"]),
            device_id=UUID(_devices[device_id]["id"]),
            type=c["type"],
            payload=c["payload"],
            status=c["status"],
            priority=c["priority"],
            created_at=c["created_at"],
            sent_at=c.get("sent_at"),
            expires_at=c.get("expires_at"),
        )
        for c in device_commands
    ]


@router.patch("/commands/{command_id}", response_model=Command)
async def update_command(
    command_id: str,
    update: CommandUpdate,
    device: dict = Depends(get_device_from_token),
    db: AsyncSession = Depends(get_db),
):
    """
    Update command status.
    
    Called by device agent to acknowledge, report progress, or complete commands.
    """
    # Find command
    command = None
    for c in _commands:
        if c["id"] == command_id:
            command = c
            break
    
    if not command:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Command {command_id} not found",
        )
    
    # Verify device owns this command
    if command["device_id"] != device["device_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this command",
        )
    
    # Update status
    now = datetime.utcnow()
    
    if update.status == CommandStatus.ACKED:
        command["status"] = CommandStatus.ACKED
        command["acked_at"] = now
    elif update.status == CommandStatus.RUNNING:
        command["status"] = CommandStatus.RUNNING
    elif update.status == CommandStatus.COMPLETED:
        command["status"] = CommandStatus.COMPLETED
        command["completed_at"] = now
        command["result"] = update.result
    elif update.status == CommandStatus.FAILED:
        command["status"] = CommandStatus.FAILED
        command["completed_at"] = now
        command["error"] = update.error
        command["result"] = update.result
    
    logger.info(f"Command {command_id} updated to {update.status}")
    
    return Command(
        id=UUID(command["id"]),
        device_id=UUID(_devices[command["device_id"]]["id"]),
        type=command["type"],
        payload=command["payload"],
        status=command["status"],
        priority=command["priority"],
        created_at=command["created_at"],
        sent_at=command.get("sent_at"),
        acked_at=command.get("acked_at"),
        completed_at=command.get("completed_at"),
        expires_at=command.get("expires_at"),
        result=command.get("result"),
        error=command.get("error"),
    )


@router.get("/commands/{command_id}", response_model=Command)
async def get_command(
    command_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get details of a specific command.
    """
    command = None
    for c in _commands:
        if c["id"] == command_id:
            command = c
            break
    
    if not command:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Command {command_id} not found",
        )
    
    device_id = command["device_id"]
    
    return Command(
        id=UUID(command["id"]),
        device_id=UUID(_devices[device_id]["id"]) if device_id in _devices else UUID(int=0),
        type=command["type"],
        payload=command["payload"],
        status=command["status"],
        priority=command["priority"],
        created_at=command["created_at"],
        sent_at=command.get("sent_at"),
        acked_at=command.get("acked_at"),
        completed_at=command.get("completed_at"),
        expires_at=command.get("expires_at"),
        result=command.get("result"),
        error=command.get("error"),
    )


@router.post("/commands/{command_id}/cancel", response_model=Command)
async def cancel_command(
    command_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Cancel a pending command.
    
    Only pending or sent commands can be cancelled.
    """
    command = None
    for c in _commands:
        if c["id"] == command_id:
            command = c
            break
    
    if not command:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Command {command_id} not found",
        )
    
    if command["status"] not in [CommandStatus.PENDING, CommandStatus.SENT]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel command in {command['status']} status",
        )
    
    command["status"] = CommandStatus.CANCELLED
    command["completed_at"] = datetime.utcnow()
    
    logger.info(f"Command {command_id} cancelled by user {user.get('id')}")
    
    device_id = command["device_id"]
    
    return Command(
        id=UUID(command["id"]),
        device_id=UUID(_devices[device_id]["id"]) if device_id in _devices else UUID(int=0),
        type=command["type"],
        payload=command["payload"],
        status=command["status"],
        priority=command["priority"],
        created_at=command["created_at"],
        completed_at=command.get("completed_at"),
    )

