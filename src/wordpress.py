"""
WordPress/JetAppointments Integration Module

This module provides WordPress REST API integration for the R58 recorder,
including booking management, client/project handling, and calendar functionality.

Configuration in config.yml:
  wordpress:
    enabled: true
    url: "https://preke.no"
    username: "api_user"
    app_password: "xxxx xxxx xxxx xxxx"
"""
import asyncio
import base64
import logging
import secrets
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from enum import Enum

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 1.0  # seconds
REQUEST_TIMEOUT = 30.0  # seconds


# ==================== Pydantic Models ====================


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
    local_path: Optional[str] = None


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
    status: str = "draft"
    created_at: Optional[datetime] = None
    media_files: List[int] = Field(default_factory=list)


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
    customer: Optional[CustomerInfo] = None
    client: Optional[ClientInfo] = None
    notes: Optional[str] = None
    content_type: Optional[ContentType] = None
    content_id: Optional[int] = None
    teleprompter_script: Optional[str] = None
    
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
        return DisplayMode.PODCAST


class ActiveBookingContext(BaseModel):
    """Context for an active booking session on the device"""
    booking: Booking
    recording_id: int
    project: VideoProject
    recording_path: str
    graphics_downloaded: bool = False
    graphics_paths: List[str] = Field(default_factory=list)
    activated_at: datetime = Field(default_factory=datetime.now)
    access_token: str = ""
    display_mode: DisplayMode = DisplayMode.PODCAST
    teleprompter_script: Optional[str] = None
    teleprompter_scroll_speed: int = 50
    
    @property
    def folder_structure(self) -> str:
        """Get the folder structure for this booking"""
        client_slug = self.booking.client.slug if self.booking.client else "unknown_client"
        project_slug = self.project.slug
        return f"clients/{client_slug}/{project_slug}/{self.recording_id}"


# ==================== WordPress API Client ====================


class WordPressClient:
    """Client for WordPress REST API with JetAppointments support"""

    def __init__(self, base_url: str, username: str, app_password: str):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.app_password = app_password
        self._client: Optional[httpx.AsyncClient] = None
        self._last_error: Optional[str] = None

    @property
    def api_url(self) -> str:
        return f"{self.base_url}/wp-json"

    @property
    def auth_header(self) -> str:
        """Generate Basic Auth header"""
        credentials = f"{self.username}:{self.app_password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"

    @property
    def is_configured(self) -> bool:
        return bool(self.base_url and self.username and self.app_password)

    async def get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=REQUEST_TIMEOUT,
                headers={
                    "Authorization": self.auth_header,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
        return self._client

    async def close(self):
        """Close the HTTP client"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        retries: int = MAX_RETRIES,
    ) -> Dict[str, Any]:
        """Make an authenticated request with retry logic"""
        client = await self.get_client()
        url = f"{self.api_url}{endpoint}"

        for attempt in range(retries):
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data,
                )

                if response.status_code == 401:
                    self._last_error = "Authentication failed"
                    raise httpx.HTTPStatusError(
                        "Authentication failed",
                        request=response.request,
                        response=response,
                    )

                response.raise_for_status()
                return response.json()

            except httpx.TimeoutException:
                self._last_error = f"Request timeout (attempt {attempt + 1}/{retries})"
                logger.warning(f"WordPress API timeout: {url}")
                if attempt < retries - 1:
                    await asyncio.sleep(RETRY_DELAY * (attempt + 1))
                else:
                    raise

            except httpx.HTTPStatusError as e:
                self._last_error = f"HTTP {e.response.status_code}"
                logger.error(f"WordPress API error: {e}")
                raise

            except httpx.RequestError as e:
                self._last_error = f"Connection error: {str(e)}"
                logger.warning(f"WordPress API connection error: {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(RETRY_DELAY * (attempt + 1))
                else:
                    raise

        return {}

    async def test_connection(self) -> bool:
        """Test WordPress API connection"""
        try:
            result = await self._request("GET", "/wp/v2/users/me")
            logger.info(f"WordPress connection successful: {result.get('name', 'Unknown')}")
            self._last_error = None
            return True
        except Exception as e:
            self._last_error = str(e)
            logger.error(f"WordPress connection test failed: {e}")
            return False

    # Simplified methods - add full implementation as needed
    async def get_appointments(self, date_from: Optional[date] = None, date_to: Optional[date] = None) -> List[Booking]:
        """Fetch appointments from JetAppointments"""
        try:
            params = {}
            if date_from:
                params["date_from"] = date_from.isoformat()
            if date_to:
                params["date_to"] = date_to.isoformat()
            
            result = await self._request("GET", "/jet-apb/v1/appointments", params=params)
            # Parse and return bookings (simplified)
            return []
        except Exception as e:
            logger.error(f"Failed to fetch appointments: {e}")
            return []

    async def get_clients(self) -> List[ClientInfo]:
        """Fetch all clients"""
        try:
            result = await self._request("GET", "/wp/v2/client", params={"per_page": 100})
            clients = []
            for item in result:
                clients.append(ClientInfo(
                    id=item.get("id"),
                    slug=item.get("slug", ""),
                    name=item.get("title", {}).get("rendered", ""),
                ))
            return clients
        except Exception as e:
            logger.error(f"Failed to fetch clients: {e}")
            return []


# ==================== Global State ====================

# Active booking context (in-memory)
_active_booking: Optional[ActiveBookingContext] = None
_wordpress_client: Optional[WordPressClient] = None


def get_active_booking() -> Optional[ActiveBookingContext]:
    """Get the currently active booking context"""
    return _active_booking


def set_active_booking(context: Optional[ActiveBookingContext]) -> None:
    """Set the active booking context"""
    global _active_booking
    _active_booking = context


def get_wordpress_client(config) -> Optional[WordPressClient]:
    """Get or create WordPress client from config"""
    global _wordpress_client
    
    # Check if WordPress is enabled in config
    if not hasattr(config, 'wordpress') or not config.wordpress.get('enabled'):
        return None
    
    if _wordpress_client is None:
        wp_config = config.wordpress
        _wordpress_client = WordPressClient(
            base_url=wp_config.get('url', ''),
            username=wp_config.get('username', ''),
            app_password=wp_config.get('app_password', '')
        )
    
    return _wordpress_client
