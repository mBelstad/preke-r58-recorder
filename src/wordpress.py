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

    def _parse_content_type(self, value: Optional[str]) -> Optional[ContentType]:
        if not value:
            return None
        normalized = value.strip().lower()
        mapping = {
            "podcast": ContentType.VIDEO_PROJECT,
            "video_project": ContentType.VIDEO_PROJECT,
            "video-project": ContentType.VIDEO_PROJECT,
            "recording": ContentType.RECORDING,
            "recordings": ContentType.RECORDING,
            "course": ContentType.COURSE,
            "courses": ContentType.COURSE,
            "webinar": ContentType.WEBINAR,
            "webinars": ContentType.WEBINAR,
        }
        if normalized in mapping:
            return mapping[normalized]
        try:
            return ContentType(normalized)
        except Exception:
            return None

    # ==================== JetAppointments API ====================

    async def get_appointments(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        status: Optional[BookingStatus] = None,
        limit: int = 20,
        page: int = 1,
    ) -> List[Booking]:
        """Fetch appointments from JetAppointments"""
        params: Dict[str, Any] = {
            "per_page": limit,
            "page": page,
        }
        if date_from:
            params["date_from"] = date_from.isoformat()
        if date_to:
            params["date_to"] = date_to.isoformat()
        if status:
            params["status"] = status.value

        try:
            result = await self._request("GET", "/jet-apb/v1/appointments", params=params)
            items = result if isinstance(result, list) else result.get("items", [])
            bookings: List[Booking] = []
            for item in items:
                booking = await self._parse_appointment(item)
                if booking:
                    bookings.append(booking)
            return bookings
        except Exception as e:
            logger.error(f"Failed to fetch appointments: {e}")
            return []

    async def get_appointment(self, appointment_id: int) -> Optional[Booking]:
        """Fetch a single appointment by ID"""
        try:
            result = await self._request("GET", f"/jet-apb/v1/appointments/{appointment_id}")
            return await self._parse_appointment(result)
        except Exception as e:
            logger.error(f"Failed to fetch appointment {appointment_id}: {e}")
            return None

    async def get_todays_appointments(self) -> List[Booking]:
        """Get all appointments for today"""
        today = date.today()
        return await self.get_appointments(date_from=today, date_to=today)

    async def get_active_appointment(self) -> Optional[Booking]:
        """Get the currently active appointment (if any)"""
        now = datetime.now()
        today = now.date()
        current_time = now.strftime("%H:%M")

        appointments = await self.get_appointments(
            date_from=today,
            date_to=today,
            status=BookingStatus.PROCESSING,
            limit=50,
            page=1,
        )

        for appointment in appointments:
            if appointment.slot_start <= current_time <= appointment.slot_end:
                return appointment
        return None

    async def update_appointment_status(self, appointment_id: int, status: BookingStatus) -> bool:
        """Update appointment status in WordPress"""
        try:
            await self._request(
                "PUT",
                f"/jet-apb/v1/appointments/{appointment_id}",
                json_data={"status": status.value},
            )
            logger.info(f"Updated appointment {appointment_id} status to {status.value}")
            return True
        except Exception as e:
            logger.error(f"Failed to update appointment status: {e}")
            return False

    async def _parse_appointment(self, data: Dict[str, Any]) -> Optional[Booking]:
        """Parse appointment data from JetAppointments API response"""
        try:
            meta = data.get("meta") or {}
            slot = data.get("slot") or ""
            slot_parts = slot.split("-") if "-" in slot else []
            slot_start = slot_parts[0].strip() if slot_parts else data.get("slot_start", "")
            slot_end = slot_parts[1].strip() if len(slot_parts) > 1 else data.get("slot_end", "")

            status_value = data.get("status", "pending")
            try:
                status = BookingStatus(status_value)
            except Exception:
                status = BookingStatus.PENDING

            booking = Booking(
                id=data.get("ID") or data.get("id"),
                status=status,
                date=data.get("date", ""),
                slot_start=slot_start,
                slot_end=slot_end,
                service_id=data.get("service"),
                service_name=data.get("service_title"),
                provider_id=data.get("provider"),
                provider_name=data.get("provider_title"),
                notes=data.get("comments") or data.get("notes"),
            )

            if data.get("user_id") or data.get("user_email") or data.get("user_name"):
                booking.customer = CustomerInfo(
                    id=data.get("user_id"),
                    name=data.get("user_name", ""),
                    email=data.get("user_email"),
                    phone=data.get("user_phone"),
                )

            client_id = meta.get("client_id") or data.get("client_id")
            if client_id:
                booking.client = await self.get_client_info(int(client_id))

            content_type_raw = (
                meta.get("content_type")
                or meta.get("recording_type")
                or data.get("content_type")
                or data.get("recording_type")
            )
            booking.content_type = self._parse_content_type(content_type_raw)
            booking.content_id = meta.get("content_id") or data.get("content_id")
            booking.teleprompter_script = (
                meta.get("teleprompter_script")
                or meta.get("script")
                or data.get("teleprompter_script")
            )

            return booking
        except Exception as e:
            logger.error(f"Failed to parse appointment data: {e}")
            return None

    # ==================== Client CPT API ====================

    async def get_client_info(self, client_id: int) -> Optional[ClientInfo]:
        """Fetch client CPT information"""
        try:
            result = await self._request("GET", f"/wp/v2/client/{client_id}")
            meta = result.get("meta") or {}
            default_project_id = meta.get("default_project_id") or meta.get("default_project") or meta.get("project_id")
            return ClientInfo(
                id=result.get("id"),
                slug=result.get("slug", ""),
                name=result.get("title", {}).get("rendered", ""),
                logo_url=meta.get("logo_url"),
                contact_email=meta.get("contact_email"),
                contact_phone=meta.get("contact_phone"),
                default_project_id=int(default_project_id) if default_project_id else None,
            )
        except Exception as e:
            logger.error(f"Failed to fetch client {client_id}: {e}")
            return None

    async def get_clients(self, limit: int = 100) -> List[ClientInfo]:
        """Fetch all clients"""
        try:
            result = await self._request("GET", "/wp/v2/client", params={"per_page": limit})
            clients = []
            for item in result:
                meta = item.get("meta") or {}
                default_project_id = meta.get("default_project_id") or meta.get("default_project") or meta.get("project_id")
                clients.append(ClientInfo(
                    id=item.get("id"),
                    slug=item.get("slug", ""),
                    name=item.get("title", {}).get("rendered", ""),
                    logo_url=meta.get("logo_url"),
                    contact_email=meta.get("contact_email"),
                    contact_phone=meta.get("contact_phone"),
                    default_project_id=int(default_project_id) if default_project_id else None,
                ))
            return clients
        except Exception as e:
            logger.error(f"Failed to fetch clients: {e}")
            return []

    # ==================== Video Project CPT API ====================

    async def get_video_project(self, project_id: int) -> Optional[VideoProject]:
        """Fetch video project CPT information"""
        try:
            result = await self._request("GET", f"/wp/v2/video_project/{project_id}")
            graphics = await self.get_project_graphics(project_id)
            return VideoProject(
                id=result.get("id"),
                slug=result.get("slug", ""),
                name=result.get("title", {}).get("rendered", ""),
                client_id=result.get("meta", {}).get("client_id"),
                description=result.get("content", {}).get("rendered", ""),
                graphics=graphics,
            )
        except Exception as e:
            logger.error(f"Failed to fetch video project {project_id}: {e}")
            return None

    async def get_client_default_project(self, client_id: int) -> Optional[VideoProject]:
        """Get the default video project for a client"""
        try:
            client = await self.get_client_info(client_id)
            if client and client.default_project_id:
                return await self.get_video_project(client.default_project_id)
            projects = await self.get_client_projects(client_id)
            return projects[0] if projects else None
        except Exception as e:
            logger.error(f"Failed to get default project for client {client_id}: {e}")
            return None

    async def get_project_graphics(self, project_id: int) -> List[GraphicsFile]:
        """Fetch graphics files associated with a project"""
        try:
            result = await self._request(
                "GET",
                "/wp/v2/media",
                params={
                    "parent": project_id,
                    "per_page": 50,
                    "media_type": "image",
                },
            )
            graphics = []
            for item in result:
                media_details = item.get("media_details", {})
                graphics.append(GraphicsFile(
                    id=item.get("id"),
                    url=item.get("source_url", ""),
                    filename=item.get("slug", "") + "." + item.get("mime_type", "").split("/")[-1],
                    mime_type=item.get("mime_type", ""),
                    width=media_details.get("width"),
                    height=media_details.get("height"),
                ))
            return graphics
        except Exception as e:
            logger.error(f"Failed to fetch project graphics: {e}")
            return []

    async def get_content_graphics(self, content_id: int) -> List[GraphicsFile]:
        """Fetch graphics files associated with any content type"""
        try:
            result = await self._request(
                "GET",
                "/wp/v2/media",
                params={
                    "parent": content_id,
                    "per_page": 50,
                    "media_type": "image",
                },
            )
            graphics = []
            for item in result:
                media_details = item.get("media_details", {})
                graphics.append(GraphicsFile(
                    id=item.get("id"),
                    url=item.get("source_url", ""),
                    filename=item.get("slug", "") + "." + item.get("mime_type", "").split("/")[-1],
                    mime_type=item.get("mime_type", ""),
                    width=media_details.get("width"),
                    height=media_details.get("height"),
                ))
            return graphics
        except Exception as e:
            logger.error(f"Failed to fetch content graphics for {content_id}: {e}")
            return []

    async def get_client_projects(self, client_id: int) -> List[VideoProject]:
        """Get all projects for a specific client"""
        try:
            result = await self._request(
                "GET",
                "/wp/v2/video_project",
                params={
                    "per_page": 100,
                    "meta_key": "client_id",
                    "meta_value": str(client_id),
                },
            )
            projects = []
            for item in result:
                projects.append(VideoProject(
                    id=item.get("id"),
                    slug=item.get("slug", ""),
                    name=item.get("title", {}).get("rendered", ""),
                    client_id=client_id,
                    description=item.get("content", {}).get("rendered", ""),
                    graphics=[],
                ))
            return projects
        except Exception as e:
            logger.error(f"Failed to fetch projects for client {client_id}: {e}")
            return []

    async def create_video_project(self, client_id: int, name: str, project_type: str = "podcast") -> Optional[VideoProject]:
        """Create a new video project CPT"""
        try:
            result = await self._request(
                "POST",
                "/wp/v2/video_project",
                json_data={
                    "title": name,
                    "status": "publish",
                    "meta": {
                        "client_id": client_id,
                        "project_type": project_type,
                    },
                },
            )
            return VideoProject(
                id=result.get("id"),
                slug=result.get("slug", ""),
                name=result.get("title", {}).get("rendered", name),
                client_id=client_id,
                description="",
                graphics=[],
            )
        except Exception as e:
            logger.error(f"Failed to create project: {e}")
            return None

    # ==================== Recording CPT API ====================

    async def create_recording(
        self,
        project_id: int,
        booking_id: int,
        title: str,
    ) -> Optional[RecordingInfo]:
        """Create a new Recording CPT in WordPress"""
        try:
            result = await self._request(
                "POST",
                "/wp/v2/recordings",
                json_data={
                    "title": title,
                    "status": "draft",
                    "meta": {
                        "project_id": project_id,
                        "booking_id": booking_id,
                    },
                },
            )
            return RecordingInfo(
                id=result.get("id"),
                title=result.get("title", {}).get("rendered", title),
                project_id=project_id,
                booking_id=booking_id,
                status=result.get("status", "draft"),
                created_at=datetime.now(),
            )
        except Exception as e:
            logger.error(f"Failed to create recording: {e}")
            return None

    async def attach_media_to_recording(self, recording_id: int, media_id: int) -> bool:
        """Attach a media file to a Recording CPT"""
        try:
            await self._request(
                "POST",
                f"/wp/v2/media/{media_id}",
                json_data={"post": recording_id},
            )
            logger.info(f"Attached media {media_id} to recording {recording_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to attach media to recording: {e}")
            return False

    # ==================== Media Upload API ====================

    async def upload_recording(
        self,
        file_path: Path,
        title: str,
        parent_post_id: Optional[int] = None,
    ) -> Optional[int]:
        """Upload a recording file to WordPress media library"""
        if not file_path.exists():
            logger.error(f"Recording file not found: {file_path}")
            return None
        try:
            client = await self.get_client()
            with open(file_path, "rb") as f:
                files = {
                    "file": (file_path.name, f, "video/x-matroska"),
                }
                data = {
                    "title": title,
                    "status": "private",
                }
                if parent_post_id:
                    data["post"] = str(parent_post_id)

                response = await client.post(
                    f"{self.api_url}/wp/v2/media",
                    files=files,
                    data=data,
                    headers={
                        "Authorization": self.auth_header,
                    },
                    timeout=300.0,
                )
                response.raise_for_status()
                result = response.json()
                media_id = result.get("id")
                logger.info(f"Uploaded recording to WordPress: {media_id}")
                return media_id
        except Exception as e:
            logger.error(f"Failed to upload recording: {e}")
            return None

    async def download_graphics(self, graphics: List[GraphicsFile], destination_dir: Path) -> List[str]:
        """Download graphics files to local directory"""
        downloaded_paths = []
        destination_dir.mkdir(parents=True, exist_ok=True)
        client = await self.get_client()

        for graphic in graphics:
            try:
                response = await client.get(graphic.url, timeout=60.0)
                response.raise_for_status()
                local_path = destination_dir / graphic.filename
                with open(local_path, "wb") as f:
                    f.write(response.content)
                downloaded_paths.append(str(local_path))
                logger.info(f"Downloaded graphic: {graphic.filename}")
            except Exception as e:
                logger.error(f"Failed to download graphic {graphic.url}: {e}")

        return downloaded_paths


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
    if not hasattr(config, 'wordpress') or not config.wordpress.enabled:
        return None
    
    if _wordpress_client is None:
        wp_config = config.wordpress
        _wordpress_client = WordPressClient(
            base_url=wp_config.url,
            username=wp_config.username,
            app_password=wp_config.app_password
        )
    
    return _wordpress_client
