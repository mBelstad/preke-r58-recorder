"""WordPress/JetAppointments API endpoints"""
import logging
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from ...config import Settings, get_settings
from .client import WordPressClient, get_wordpress_client
from .models import (
    ActivateBookingRequest,
    ActivateBookingResponse,
    Booking,
    BookingDetailResponse,
    BookingListResponse,
    BookingStatus,
    CompleteBookingRequest,
    CompleteBookingResponse,
    CustomerPortalStatus,
    DisplayMode,
    GraphicsFile,
    ValidateTokenRequest,
    ValidateTokenResponse,
    WordPressStatusResponse,
    ActiveBookingContext,
)

router = APIRouter(prefix="/api/v1/wordpress", tags=["WordPress"])
logger = logging.getLogger(__name__)

# Active booking context (in-memory state)
_active_booking: Optional[ActiveBookingContext] = None


def get_active_booking() -> Optional[ActiveBookingContext]:
    """Get the currently active booking context"""
    return _active_booking


def set_active_booking(context: Optional[ActiveBookingContext]) -> None:
    """Set the active booking context"""
    global _active_booking
    _active_booking = context


# ==================== Status Endpoints ====================


@router.get("/status", response_model=WordPressStatusResponse)
async def get_wordpress_status(
    settings: Settings = Depends(get_settings),
    client: WordPressClient = Depends(get_wordpress_client),
) -> WordPressStatusResponse:
    """
    Get WordPress integration status.
    
    Returns connection status and configuration info.
    """
    if not settings.wordpress_enabled:
        return WordPressStatusResponse(
            enabled=False,
            connected=False,
            wordpress_url=settings.wordpress_url,
            error="WordPress integration is disabled",
        )

    if not client.is_configured:
        return WordPressStatusResponse(
            enabled=True,
            connected=False,
            wordpress_url=settings.wordpress_url,
            error="WordPress credentials not configured",
        )

    # Test connection
    connected = await client.test_connection()

    return WordPressStatusResponse(
        enabled=True,
        connected=connected,
        wordpress_url=settings.wordpress_url,
        last_sync=datetime.now() if connected else None,
        error=client._last_error if not connected else None,
    )


# ==================== Booking/Appointment Endpoints ====================


@router.get("/appointments", response_model=BookingListResponse)
async def list_appointments(
    date_from: Optional[date] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    date_to: Optional[date] = Query(None, description="Filter to date (YYYY-MM-DD)"),
    status: Optional[BookingStatus] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    settings: Settings = Depends(get_settings),
    client: WordPressClient = Depends(get_wordpress_client),
) -> BookingListResponse:
    """
    List appointments from JetAppointments.
    
    Supports filtering by date range and status.
    """
    if not settings.wordpress_enabled:
        raise HTTPException(status_code=503, detail="WordPress integration is disabled")

    bookings = await client.get_appointments(
        date_from=date_from,
        date_to=date_to,
        status=status,
        limit=per_page,
        page=page,
    )

    return BookingListResponse(
        bookings=bookings,
        total=len(bookings),  # Note: Would need separate count query for accurate total
        page=page,
        per_page=per_page,
    )


@router.get("/appointments/today", response_model=BookingListResponse)
async def list_todays_appointments(
    settings: Settings = Depends(get_settings),
    client: WordPressClient = Depends(get_wordpress_client),
) -> BookingListResponse:
    """
    Get all appointments for today.
    
    Convenience endpoint for the device to show today's schedule.
    """
    if not settings.wordpress_enabled:
        raise HTTPException(status_code=503, detail="WordPress integration is disabled")

    bookings = await client.get_todays_appointments()

    return BookingListResponse(
        bookings=bookings,
        total=len(bookings),
        page=1,
        per_page=len(bookings),
    )


@router.get("/appointments/active", response_model=Optional[Booking])
async def get_active_appointment(
    settings: Settings = Depends(get_settings),
    client: WordPressClient = Depends(get_wordpress_client),
) -> Optional[Booking]:
    """
    Get the currently active appointment (if any).
    
    Returns the appointment that is currently in progress based on time.
    """
    if not settings.wordpress_enabled:
        raise HTTPException(status_code=503, detail="WordPress integration is disabled")

    return await client.get_active_appointment()


@router.get("/appointments/{appointment_id}", response_model=BookingDetailResponse)
async def get_appointment(
    appointment_id: int,
    settings: Settings = Depends(get_settings),
    client: WordPressClient = Depends(get_wordpress_client),
) -> BookingDetailResponse:
    """
    Get details of a specific appointment.
    
    Includes customer, client, project, and graphics information.
    """
    if not settings.wordpress_enabled:
        raise HTTPException(status_code=503, detail="WordPress integration is disabled")

    booking = await client.get_appointment(appointment_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Appointment not found")

    # Get graphics from project if available
    graphics: List[GraphicsFile] = []
    if booking.project:
        graphics = booking.project.graphics

    return BookingDetailResponse(
        booking=booking,
        graphics=graphics,
    )


# ==================== Booking Activation Endpoints ====================


@router.post("/appointments/{appointment_id}/activate", response_model=ActivateBookingResponse)
async def activate_booking(
    appointment_id: int,
    request: ActivateBookingRequest,
    settings: Settings = Depends(get_settings),
    client: WordPressClient = Depends(get_wordpress_client),
) -> ActivateBookingResponse:
    """
    Activate a booking session on the device.
    
    This:
    1. Fetches the booking details from WordPress
    2. Gets the client's default video project
    3. Creates a Recording CPT in WordPress
    4. Creates the recording directory structure
    5. Downloads graphics if requested
    6. Generates access token for customer/display
    7. Sets this as the active booking context
    
    After activation, recordings will be saved to the booking-specific folder.
    """
    if not settings.wordpress_enabled:
        raise HTTPException(status_code=503, detail="WordPress integration is disabled")

    # Check if another booking is already active
    current = get_active_booking()
    if current and current.booking.id != appointment_id:
        raise HTTPException(
            status_code=409,
            detail=f"Another booking is already active: {current.booking.id}"
        )

    # Fetch booking details
    booking = await client.get_appointment(appointment_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Appointment not found")

    if not booking.client:
        raise HTTPException(status_code=400, detail="Booking has no associated client")

    # Get client's default project
    project = await client.get_client_default_project(booking.client.id)
    if not project:
        raise HTTPException(
            status_code=400,
            detail=f"Client {booking.client.name} has no default project configured"
        )

    # Create Recording CPT in WordPress
    recording_title = f"{booking.client.name} - {booking.date} {booking.slot_start}"
    recording = await client.create_recording(
        project_id=project.id,
        booking_id=booking.id,
        title=recording_title,
    )
    
    if not recording:
        raise HTTPException(status_code=500, detail="Failed to create recording in WordPress")

    logger.info(f"Created Recording CPT #{recording.id} for booking #{booking.id}")

    # Build recording path using recording ID
    client_slug = booking.client.slug
    project_slug = project.slug
    
    recording_path = Path(settings.booking_recordings_base) / client_slug / project_slug / str(recording.id)
    recording_path.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Created recording directory: {recording_path}")

    # Download graphics if requested
    graphics_downloaded = 0
    graphics_paths: List[str] = []
    
    if request.download_graphics and project.graphics:
        graphics_dir = recording_path / "graphics"
        graphics_paths = await client.download_graphics(
            project.graphics,
            graphics_dir,
        )
        graphics_downloaded = len(graphics_paths)
        logger.info(f"Downloaded {graphics_downloaded} graphics files")

    # Generate access token for customer portal and studio display
    import secrets
    access_token = secrets.token_urlsafe(32)

    # Create and set active booking context
    context = ActiveBookingContext(
        booking=booking,
        recording_id=recording.id,
        project=project,
        recording_path=str(recording_path),
        graphics_downloaded=graphics_downloaded > 0,
        graphics_paths=graphics_paths,
        access_token=access_token,
        display_mode=booking.display_mode,
        teleprompter_script=booking.teleprompter_script,
    )
    set_active_booking(context)

    # Update booking status to processing
    await client.update_appointment_status(appointment_id, BookingStatus.PROCESSING)

    return ActivateBookingResponse(
        success=True,
        booking=booking,
        recording_path=str(recording_path),
        graphics_downloaded=graphics_downloaded,
        message=f"Booking activated. Recording #{recording.id} created. Access token: {access_token}",
    )


@router.post("/appointments/{appointment_id}/deactivate")
async def deactivate_booking(
    appointment_id: int,
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    Deactivate the current booking session.
    
    Does not complete or upload - just clears the active booking context.
    """
    current = get_active_booking()
    if not current:
        return {"success": True, "message": "No active booking to deactivate"}

    if current.booking.id != appointment_id:
        raise HTTPException(
            status_code=409,
            detail=f"Booking {appointment_id} is not the active booking"
        )

    set_active_booking(None)
    logger.info(f"Deactivated booking {appointment_id}")

    return {"success": True, "message": f"Booking {appointment_id} deactivated"}


@router.get("/booking/current")
async def get_current_booking(
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    Get the currently active booking context on this device.
    
    Returns the booking details and recording path if a booking is active.
    """
    current = get_active_booking()
    if not current:
        return {"active": False, "booking": None}

    return {
        "active": True,
        "booking": current.booking,
        "recording_path": current.recording_path,
        "graphics_downloaded": current.graphics_downloaded,
        "graphics_paths": current.graphics_paths,
        "activated_at": current.activated_at.isoformat(),
    }


@router.get("/booking/recording-path")
async def get_active_recording_path(
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    Get the recording path for the active booking.
    
    Used by the recording system to determine where to save files.
    Returns the default path if no booking is active.
    """
    current = get_active_booking()
    
    if current:
        return {
            "path": current.recording_path,
            "booking_id": current.booking.id,
            "is_booking_path": True,
        }
    
    # Return default recordings path
    return {
        "path": "/data/recordings",
        "booking_id": None,
        "is_booking_path": False,
    }


# ==================== Booking Completion Endpoints ====================


@router.post("/appointments/{appointment_id}/complete", response_model=CompleteBookingResponse)
async def complete_booking(
    appointment_id: int,
    request: CompleteBookingRequest,
    settings: Settings = Depends(get_settings),
    client: WordPressClient = Depends(get_wordpress_client),
) -> CompleteBookingResponse:
    """
    Complete a booking session.
    
    This:
    1. Optionally uploads recordings to WordPress and attaches to Recording CPT
    2. Updates the booking status in WordPress
    3. Clears the active booking context
    """
    if not settings.wordpress_enabled:
        raise HTTPException(status_code=503, detail="WordPress integration is disabled")

    current = get_active_booking()
    if not current or current.booking.id != appointment_id:
        raise HTTPException(
            status_code=404,
            detail=f"Booking {appointment_id} is not currently active"
        )

    recordings_uploaded = 0
    wordpress_updated = False

    # Upload recordings if requested
    if request.upload_recordings:
        recording_dir = Path(current.recording_path)
        if recording_dir.exists():
            for recording_file in recording_dir.glob("*.mkv"):
                # Upload to WordPress media library
                media_id = await client.upload_recording(
                    recording_file,
                    title=f"Recording - {current.booking.client.name} - {recording_file.stem}",
                    parent_post_id=current.recording_id,  # Attach to Recording CPT
                )
                if media_id:
                    # Also explicitly attach to recording
                    await client.attach_media_to_recording(current.recording_id, media_id)
                    recordings_uploaded += 1
                    logger.info(f"Uploaded recording: {recording_file.name} -> Recording #{current.recording_id}")

    # Update WordPress status
    if request.update_status:
        wordpress_updated = await client.update_appointment_status(
            appointment_id,
            BookingStatus.COMPLETED,
        )

    # Clear active booking
    set_active_booking(None)

    return CompleteBookingResponse(
        success=True,
        booking_id=appointment_id,
        recordings_uploaded=recordings_uploaded,
        wordpress_status_updated=wordpress_updated,
        message=f"Booking completed. {recordings_uploaded} recordings uploaded to Recording #{current.recording_id}.",
    )


# ==================== Graphics Endpoints ====================


@router.post("/appointments/{appointment_id}/download-graphics")
async def download_booking_graphics(
    appointment_id: int,
    settings: Settings = Depends(get_settings),
    client: WordPressClient = Depends(get_wordpress_client),
) -> dict:
    """
    Download graphics for a booking.
    
    Can be called separately from activation to refresh graphics.
    """
    if not settings.wordpress_enabled:
        raise HTTPException(status_code=503, detail="WordPress integration is disabled")

    # Get booking details
    booking = await client.get_appointment(appointment_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Appointment not found")

    if not booking.project or not booking.project.graphics:
        return {
            "success": True,
            "downloaded": 0,
            "message": "No graphics associated with this booking",
        }

    # Determine download path
    current = get_active_booking()
    if current and current.booking.id == appointment_id:
        graphics_dir = Path(current.recording_path) / "graphics"
    else:
        # Use temporary path if not active booking
        client_slug = booking.client.slug if booking.client else "unknown_client"
        project_slug = booking.project.slug if booking.project else "unknown_project"
        graphics_dir = Path(settings.booking_recordings_base) / client_slug / project_slug / str(booking.id) / "graphics"

    # Download graphics
    downloaded_paths = await client.download_graphics(
        booking.project.graphics,
        graphics_dir,
    )

    # Update active booking context if applicable
    if current and current.booking.id == appointment_id:
        current.graphics_downloaded = True
        current.graphics_paths = downloaded_paths

    return {
        "success": True,
        "downloaded": len(downloaded_paths),
        "paths": downloaded_paths,
        "message": f"Downloaded {len(downloaded_paths)} graphics files",
    }


@router.get("/appointments/{appointment_id}/graphics")
async def list_booking_graphics(
    appointment_id: int,
    settings: Settings = Depends(get_settings),
    client: WordPressClient = Depends(get_wordpress_client),
) -> dict:
    """
    List graphics files for a booking.
    
    Returns both WordPress URLs and local paths if downloaded.
    """
    if not settings.wordpress_enabled:
        raise HTTPException(status_code=503, detail="WordPress integration is disabled")

    booking = await client.get_appointment(appointment_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Appointment not found")

    graphics = []
    if booking.project and booking.project.graphics:
        for g in booking.project.graphics:
            graphics.append({
                "id": g.id,
                "url": g.url,
                "filename": g.filename,
                "mime_type": g.mime_type,
                "width": g.width,
                "height": g.height,
                "local_path": g.local_path,
            })

    # Check if graphics are downloaded locally
    current = get_active_booking()
    local_paths = []
    if current and current.booking.id == appointment_id:
        local_paths = current.graphics_paths

    return {
        "booking_id": appointment_id,
        "graphics": graphics,
        "local_paths": local_paths,
        "downloaded": len(local_paths) > 0,
    }


# ==================== Customer Portal Endpoints ====================


@router.post("/customer/validate", response_model=ValidateTokenResponse)
async def validate_customer_token(
    request: ValidateTokenRequest,
    settings: Settings = Depends(get_settings),
) -> ValidateTokenResponse:
    """
    Validate a customer access token.
    
    Returns booking and project info if valid.
    """
    current = get_active_booking()
    
    if not current:
        return ValidateTokenResponse(
            valid=False,
            error="No active booking session"
        )
    
    if current.access_token != request.token:
        return ValidateTokenResponse(
            valid=False,
            error="Invalid or expired token"
        )
    
    return ValidateTokenResponse(
        valid=True,
        booking=current.booking,
        project=current.project,
    )


@router.get("/customer/{token}/status", response_model=CustomerPortalStatus)
async def get_customer_portal_status(
    token: str,
    settings: Settings = Depends(get_settings),
) -> CustomerPortalStatus:
    """
    Get current status for customer portal/studio display.
    
    Returns booking info, recording status, and presentation state.
    """
    current = get_active_booking()
    
    if not current or current.access_token != token:
        raise HTTPException(status_code=404, detail="Invalid or expired token")
    
    # TODO: Get actual recording status from recording system
    # For now, return placeholder values
    import shutil
    disk_usage = shutil.disk_usage("/data")
    disk_free_gb = disk_usage.free / (1024 ** 3)
    
    return CustomerPortalStatus(
        booking=current.booking,
        project=current.project,
        recording_active=False,  # TODO: Check actual recording status
        recording_duration_ms=0,
        current_slide_index=0,
        total_slides=len(current.project.graphics),
        disk_space_gb=disk_free_gb,
        display_mode=current.display_mode,
        teleprompter_script=current.teleprompter_script,
        teleprompter_scroll_speed=current.teleprompter_scroll_speed,
    )


@router.post("/customer/{token}/recording/start")
async def customer_start_recording(
    token: str,
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    Start recording (customer-initiated).
    
    TODO: Integrate with actual recording system.
    """
    current = get_active_booking()
    
    if not current or current.access_token != token:
        raise HTTPException(status_code=404, detail="Invalid or expired token")
    
    # TODO: Call actual recording start API
    logger.info(f"Customer initiated recording start for booking #{current.booking.id}")
    
    return {
        "success": True,
        "message": "Recording started",
        "recording_path": current.recording_path,
    }


@router.post("/customer/{token}/recording/stop")
async def customer_stop_recording(
    token: str,
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    Stop recording (customer-initiated).
    
    TODO: Integrate with actual recording system.
    """
    current = get_active_booking()
    
    if not current or current.access_token != token:
        raise HTTPException(status_code=404, detail="Invalid or expired token")
    
    # TODO: Call actual recording stop API
    logger.info(f"Customer initiated recording stop for booking #{current.booking.id}")
    
    return {
        "success": True,
        "message": "Recording stopped",
    }


@router.post("/customer/{token}/presentation/goto/{index}")
async def customer_goto_slide(
    token: str,
    index: int,
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    Jump to a specific slide in the presentation.
    
    TODO: Integrate with presentation system to display on R58 output.
    """
    current = get_active_booking()
    
    if not current or current.access_token != token:
        raise HTTPException(status_code=404, detail="Invalid or expired token")
    
    if index < 0 or index >= len(current.project.graphics):
        raise HTTPException(status_code=400, detail="Invalid slide index")
    
    # TODO: Update presentation display
    logger.info(f"Customer navigated to slide {index} for booking #{current.booking.id}")
    
    return {
        "success": True,
        "current_index": index,
        "total_slides": len(current.project.graphics),
    }


# ==================== Display Mode Endpoints ====================


@router.get("/customer/{token}/display-mode")
async def get_display_mode(
    token: str,
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    Get current display mode for the active booking.
    """
    current = get_active_booking()
    
    if not current or current.access_token != token:
        raise HTTPException(status_code=404, detail="Invalid or expired token")
    
    return {
        "display_mode": current.display_mode.value,
        "content_type": current.booking.content_type.value if current.booking.content_type else None,
    }


@router.post("/customer/{token}/teleprompter/script")
async def update_teleprompter_script(
    token: str,
    script: str,
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    Update teleprompter script for the active booking.
    """
    current = get_active_booking()
    
    if not current or current.access_token != token:
        raise HTTPException(status_code=404, detail="Invalid or expired token")
    
    if current.display_mode != DisplayMode.TELEPROMPTER:
        raise HTTPException(status_code=400, detail="Not in teleprompter mode")
    
    current.teleprompter_script = script
    logger.info(f"Updated teleprompter script for booking #{current.booking.id}")
    
    return {
        "success": True,
        "script_length": len(script),
    }


@router.post("/customer/{token}/teleprompter/speed")
async def set_teleprompter_speed(
    token: str,
    speed: int,
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    Set teleprompter scroll speed (1-100).
    """
    current = get_active_booking()
    
    if not current or current.access_token != token:
        raise HTTPException(status_code=404, detail="Invalid or expired token")
    
    if current.display_mode != DisplayMode.TELEPROMPTER:
        raise HTTPException(status_code=400, detail="Not in teleprompter mode")
    
    if speed < 1 or speed > 100:
        raise HTTPException(status_code=400, detail="Speed must be between 1 and 100")
    
    current.teleprompter_scroll_speed = speed
    logger.info(f"Set teleprompter speed to {speed} for booking #{current.booking.id}")
    
    return {
        "success": True,
        "speed": speed,
    }


@router.get("/customer/{token}/vdoninja/status")
async def check_vdoninja_status(
    token: str,
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    Check if VDO.ninja VPS is available.
    """
    current = get_active_booking()
    
    if not current or current.access_token != token:
        raise HTTPException(status_code=404, detail="Invalid or expired token")
    
    if not settings.vdoninja_vps_enabled:
        return {
            "available": False,
            "error": "VDO.ninja VPS is disabled",
        }
    
    # Try to check VDO.ninja availability
    import httpx
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.head(settings.vdoninja_vps_url)
            available = response.status_code < 500
    except Exception as e:
        logger.warning(f"VDO.ninja VPS check failed: {e}")
        available = False
    
    return {
        "available": available,
        "url": settings.vdoninja_vps_url if available else None,
        "error": None if available else "VDO.ninja VPS is offline",
    }


# ==================== Client/Project Endpoints ====================


@router.get("/clients")
async def list_clients(
    client: WordPressClient = Depends(get_wordpress_client),
) -> dict:
    """
    List all clients.
    """
    if not client.is_configured:
        raise HTTPException(status_code=503, detail="WordPress integration not configured")
    
    clients = await client.get_clients()
    
    return {
        "clients": clients,
        "total": len(clients),
    }


@router.get("/clients/{client_id}/projects")
async def list_client_projects(
    client_id: int,
    client: WordPressClient = Depends(get_wordpress_client),
) -> dict:
    """
    List all projects for a specific client.
    """
    if not client.is_configured:
        raise HTTPException(status_code=503, detail="WordPress integration not configured")
    
    projects = await client.get_client_projects(client_id)
    
    return {
        "projects": projects,
        "total": len(projects),
    }


@router.post("/projects")
async def create_project(
    request: dict,
    client: WordPressClient = Depends(get_wordpress_client),
) -> dict:
    """
    Create a new video project.
    """
    if not client.is_configured:
        raise HTTPException(status_code=503, detail="WordPress integration not configured")
    
    client_id = request.get("client_id")
    name = request.get("name")
    project_type = request.get("type", "podcast")
    
    if not client_id or not name:
        raise HTTPException(status_code=400, detail="client_id and name are required")
    
    project = await client.create_video_project(client_id, name, project_type)
    
    if not project:
        raise HTTPException(status_code=500, detail="Failed to create project")
    
    return {
        "id": project.id,
        "name": project.name,
        "slug": project.slug,
        "client_id": project.client_id,
    }


# ==================== Calendar Endpoints ====================


@router.get("/calendar/today")
async def get_calendar_today(
    settings: Settings = Depends(get_settings),
    client: WordPressClient = Depends(get_wordpress_client),
) -> dict:
    """
    Get today's calendar with time slots and bookings.
    """
    if not client.is_configured:
        raise HTTPException(status_code=503, detail="WordPress integration not configured")
    
    from datetime import date, time, timedelta
    
    today = date.today()
    bookings = await client.get_todays_appointments()
    
    # Generate time slots (9 AM to 5 PM, 30-minute intervals)
    slots = []
    start_hour = 9
    end_hour = 17
    
    current_time = time(start_hour, 0)
    end_time = time(end_hour, 0)
    
    while current_time < end_time:
        slot_start = current_time.strftime("%H:%M")
        
        # Calculate end time (30 minutes later)
        next_time = (datetime.combine(today, current_time) + timedelta(minutes=30)).time()
        slot_end = next_time.strftime("%H:%M")
        
        # Check if this slot has a booking
        slot_booking = None
        for booking in bookings:
            if booking.slot_start <= slot_start < booking.slot_end:
                slot_booking = booking
                break
        
        # Check if lunch break (12:00-13:00)
        is_lunch = current_time.hour == 12
        
        slots.append({
            "start_time": slot_start,
            "end_time": slot_end,
            "available": slot_booking is None and not is_lunch,
            "booking": slot_booking,
            "is_lunch": is_lunch,
        })
        
        current_time = next_time
    
    return {
        "date": today.isoformat(),
        "slots": slots,
    }


@router.post("/calendar/book")
async def create_walk_in_booking(
    request: dict,
    settings: Settings = Depends(get_settings),
    client: WordPressClient = Depends(get_wordpress_client),
) -> dict:
    """
    Create a walk-in booking for the calendar kiosk.
    """
    if not client.is_configured:
        raise HTTPException(status_code=503, detail="WordPress integration not configured")
    
    from datetime import date
    
    slot_start = request.get("slot_start")
    slot_end = request.get("slot_end")
    customer_name = request.get("customer_name")
    customer_email = request.get("customer_email")
    customer_phone = request.get("customer_phone")
    recording_type = request.get("recording_type", "podcast")
    
    if not all([slot_start, slot_end, customer_name, customer_email]):
        raise HTTPException(status_code=400, detail="Missing required fields")
    
    # Create booking via JetAppointments API
    today = date.today()
    
    try:
        result = await client._request(
            "POST",
            "/jet-apb/v1/appointments",
            json_data={
                "date": today.isoformat(),
                "slot": f"{slot_start}-{slot_end}",
                "status": "pending",
                "user_name": customer_name,
                "user_email": customer_email,
                "user_phone": customer_phone or "",
                "meta": {
                    "recording_type": recording_type,
                    "walk_in": True,
                },
            },
        )
        
        booking_id = result.get("ID") or result.get("id")
        
        return {
            "success": True,
            "booking_id": booking_id,
            "message": f"Booking created for {slot_start}-{slot_end}",
        }
    except Exception as e:
        logger.error(f"Failed to create walk-in booking: {e}")
        raise HTTPException(status_code=500, detail=str(e))
