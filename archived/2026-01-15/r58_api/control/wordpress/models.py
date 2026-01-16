"""Pydantic models for WordPress/JetAppointments integration"""
from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class BookingStatus(str, Enum):
    """JetAppointments booking status values"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ON_HOLD = "on-hold"
    REFUNDED = "refunded"
    FAILED = "failed"


class DisplayMode(str, Enum):
    """Studio display modes"""
    PODCAST = "podcast"
    TELEPROMPTER = "teleprompter"
    WEBINAR = "webinar"


class ContentType(str, Enum):
    """WordPress CPT types that determine display mode"""
    VIDEO_PROJECT = "video_project"  # -> Podcast mode
    RECORDING = "recordings"          # -> Teleprompter mode
    COURSE = "courses"                # -> Teleprompter mode
    WEBINAR = "webinars"              # -> Webinar mode


class GraphicsFile(BaseModel):
    """Graphics file from WordPress media library"""
    id: int
    url: str
    filename: str
    mime_type: str
    width: Optional[int] = None
    height: Optional[int] = None
    local_path: Optional[str] = None  # Path on device after download


class CustomerInfo(BaseModel):
    """Customer information from booking"""
    id: Optional[int] = None
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None


class ClientInfo(BaseModel):
    """Client CPT information"""
    id: int
    slug: str
    name: str
    logo_url: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    default_project_id: Optional[int] = None


class VideoProject(BaseModel):
    """Video Project CPT information"""
    id: int
    slug: str
    name: str
    client_id: Optional[int] = None
    description: Optional[str] = None
    graphics: List[GraphicsFile] = Field(default_factory=list)


class RecordingInfo(BaseModel):
    """Recording CPT information"""
    id: int
    title: str
    project_id: int
    booking_id: Optional[int] = None
    status: str = "draft"  # draft, publish, private
    created_at: Optional[datetime] = None
    media_files: List[int] = Field(default_factory=list)  # WordPress media IDs


class Booking(BaseModel):
    """JetAppointments booking/appointment"""
    id: int
    status: BookingStatus
    date: str  # YYYY-MM-DD
    slot_start: str  # HH:MM
    slot_end: str  # HH:MM
    service_id: Optional[int] = None
    service_name: Optional[str] = None
    provider_id: Optional[int] = None
    provider_name: Optional[str] = None
    
    # Related entities - booking links to Client only (not project directly)
    customer: Optional[CustomerInfo] = None
    client: Optional[ClientInfo] = None
    
    # Custom fields from JetEngine
    notes: Optional[str] = None
    
    # Content type and display mode
    content_type: Optional[ContentType] = None
    content_id: Optional[int] = None
    teleprompter_script: Optional[str] = None
    
    # Computed
    @property
    def datetime_start(self) -> datetime:
        return datetime.strptime(f"{self.date} {self.slot_start}", "%Y-%m-%d %H:%M")
    
    @property
    def datetime_end(self) -> datetime:
        return datetime.strptime(f"{self.date} {self.slot_end}", "%Y-%m-%d %H:%M")
    
    @property
    def display_mode(self) -> DisplayMode:
        """Determine display mode based on content type"""
        if self.content_type == ContentType.WEBINAR:
            return DisplayMode.WEBINAR
        elif self.content_type in (ContentType.RECORDING, ContentType.COURSE):
            return DisplayMode.TELEPROMPTER
        return DisplayMode.PODCAST  # default for video_project


class ActiveBookingContext(BaseModel):
    """Context for an active booking session on the device"""
    booking: Booking
    recording_id: int  # WordPress Recording CPT ID
    project: VideoProject  # Client's default project
    recording_path: str  # Path where recordings should be saved
    graphics_downloaded: bool = False
    graphics_paths: List[str] = Field(default_factory=list)
    activated_at: datetime = Field(default_factory=datetime.now)
    access_token: str = ""  # Token for customer/display access
    display_mode: DisplayMode = DisplayMode.PODCAST
    teleprompter_script: Optional[str] = None
    teleprompter_scroll_speed: int = 50  # 1-100
    
    @property
    def folder_structure(self) -> str:
        """Get the folder structure for this booking"""
        client_slug = self.booking.client.slug if self.booking.client else "unknown_client"
        project_slug = self.project.slug
        return f"clients/{client_slug}/{project_slug}/{self.recording_id}"


# Request/Response models for API endpoints

class BookingListResponse(BaseModel):
    """Response for listing bookings"""
    bookings: List[Booking]
    total: int
    page: int = 1
    per_page: int = 20


class BookingDetailResponse(BaseModel):
    """Response for single booking details"""
    booking: Booking
    graphics: List[GraphicsFile] = Field(default_factory=list)


class ActivateBookingRequest(BaseModel):
    """Request to activate a booking session"""
    booking_id: int
    download_graphics: bool = True


class ActivateBookingResponse(BaseModel):
    """Response after activating a booking"""
    success: bool
    booking: Booking
    recording_path: str
    graphics_downloaded: int = 0
    message: str = ""


class CompleteBookingRequest(BaseModel):
    """Request to complete a booking and upload recordings"""
    booking_id: int
    upload_recordings: bool = True
    update_status: bool = True


class CompleteBookingResponse(BaseModel):
    """Response after completing a booking"""
    success: bool
    booking_id: int
    recordings_uploaded: int = 0
    wordpress_status_updated: bool = False
    message: str = ""


class WordPressStatusResponse(BaseModel):
    """WordPress integration status"""
    enabled: bool
    connected: bool
    wordpress_url: str
    last_sync: Optional[datetime] = None
    error: Optional[str] = None


# Customer Portal Models

class CustomerPortalStatus(BaseModel):
    """Status for customer portal/studio display"""
    booking: Booking
    project: VideoProject
    recording_active: bool = False
    recording_duration_ms: int = 0
    current_slide_index: int = 0
    total_slides: int = 0
    disk_space_gb: float = 0.0
    display_mode: DisplayMode = DisplayMode.PODCAST
    teleprompter_script: Optional[str] = None
    teleprompter_scroll_speed: int = 50


class ValidateTokenRequest(BaseModel):
    """Request to validate customer access token"""
    token: str


class ValidateTokenResponse(BaseModel):
    """Response after validating token"""
    valid: bool
    booking: Optional[Booking] = None
    project: Optional[VideoProject] = None
    error: Optional[str] = None


# Calendar Models

class TimeSlot(BaseModel):
    """Time slot for calendar view"""
    start_time: str  # HH:MM
    end_time: str    # HH:MM
    available: bool
    booking: Optional[Booking] = None


class CalendarDay(BaseModel):
    """Calendar day with time slots"""
    date: str  # YYYY-MM-DD
    slots: List[TimeSlot]


class WalkInBookingRequest(BaseModel):
    """Request to create a walk-in booking"""
    slot_start: str  # HH:MM
    slot_end: str    # HH:MM
    customer_name: str
    customer_email: str
    customer_phone: Optional[str] = None
    recording_type: str  # podcast, recording, course, webinar


class WalkInBookingResponse(BaseModel):
    """Response after creating walk-in booking"""
    success: bool
    booking_id: int
    message: str
