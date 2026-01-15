"""WordPress/JetAppointments API client"""
import asyncio
import base64
import logging
from datetime import datetime, date
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from ...config import Settings, get_settings
from .models import (
    Booking,
    BookingStatus,
    ClientInfo,
    CustomerInfo,
    GraphicsFile,
    RecordingInfo,
    VideoProject,
)

logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 1.0  # seconds
REQUEST_TIMEOUT = 30.0  # seconds


class WordPressClient:
    """Client for WordPress REST API with JetAppointments support"""

    def __init__(self, settings: Optional[Settings] = None):
        self._settings = settings or get_settings()
        self._client: Optional[httpx.AsyncClient] = None
        self._last_error: Optional[str] = None

    @property
    def base_url(self) -> str:
        return self._settings.wordpress_url.rstrip("/")

    @property
    def api_url(self) -> str:
        return f"{self.base_url}/wp-json"

    @property
    def auth_header(self) -> str:
        """Generate Basic Auth header from username and app password"""
        credentials = f"{self._settings.wordpress_username}:{self._settings.wordpress_app_password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"

    @property
    def is_configured(self) -> bool:
        """Check if WordPress integration is properly configured"""
        return bool(
            self._settings.wordpress_enabled
            and self._settings.wordpress_url
            and self._settings.wordpress_username
            and self._settings.wordpress_app_password
        )

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
        """Make an authenticated request to WordPress API with retry logic"""
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
                    self._last_error = "Authentication failed - check WordPress credentials"
                    raise httpx.HTTPStatusError(
                        "Authentication failed",
                        request=response.request,
                        response=response,
                    )

                response.raise_for_status()
                return response.json()

            except httpx.TimeoutException:
                self._last_error = f"Request timeout (attempt {attempt + 1}/{retries})"
                logger.warning(f"WordPress API timeout: {url} (attempt {attempt + 1})")
                if attempt < retries - 1:
                    await asyncio.sleep(RETRY_DELAY * (attempt + 1))
                else:
                    raise

            except httpx.HTTPStatusError as e:
                self._last_error = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
                logger.error(f"WordPress API error: {e}")
                raise

            except httpx.RequestError as e:
                self._last_error = f"Connection error: {str(e)}"
                logger.warning(f"WordPress API connection error: {e} (attempt {attempt + 1})")
                if attempt < retries - 1:
                    await asyncio.sleep(RETRY_DELAY * (attempt + 1))
                else:
                    raise

        return {}

    async def test_connection(self) -> bool:
        """Test WordPress API connection"""
        try:
            # Try to fetch current user to verify authentication
            result = await self._request("GET", "/wp/v2/users/me")
            logger.info(f"WordPress connection successful: {result.get('name', 'Unknown')}")
            self._last_error = None
            return True
        except Exception as e:
            self._last_error = str(e)
            logger.error(f"WordPress connection test failed: {e}")
            return False

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
            # JetAppointments REST API endpoint
            result = await self._request(
                "GET",
                "/jet-apb/v1/appointments",
                params=params,
            )

            bookings = []
            items = result if isinstance(result, list) else result.get("items", [])

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
            result = await self._request(
                "GET",
                f"/jet-apb/v1/appointments/{appointment_id}",
            )
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
        )

        for apt in appointments:
            if apt.slot_start <= current_time <= apt.slot_end:
                return apt

        return None

    async def update_appointment_status(
        self,
        appointment_id: int,
        status: BookingStatus,
    ) -> bool:
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

    async def _parse_appointment(self, data: Dict) -> Optional[Booking]:
        """Parse appointment data from JetAppointments API response"""
        try:
            # Extract basic appointment info
            booking = Booking(
                id=data.get("ID") or data.get("id"),
                status=BookingStatus(data.get("status", "pending")),
                date=data.get("date", ""),
                slot_start=data.get("slot", "").split("-")[0].strip() if data.get("slot") else data.get("slot_start", ""),
                slot_end=data.get("slot", "").split("-")[1].strip() if data.get("slot") and "-" in data.get("slot", "") else data.get("slot_end", ""),
                service_id=data.get("service"),
                service_name=data.get("service_title"),
                provider_id=data.get("provider"),
                provider_name=data.get("provider_title"),
                notes=data.get("comments") or data.get("notes"),
            )

            # Parse customer info
            if data.get("user_id") or data.get("user_email"):
                booking.customer = CustomerInfo(
                    id=data.get("user_id"),
                    name=data.get("user_name", ""),
                    email=data.get("user_email"),
                    phone=data.get("user_phone"),
                )

            # Fetch related client and project if available (from meta fields)
            client_id = data.get("meta", {}).get("client_id") or data.get("client_id")
            project_id = data.get("meta", {}).get("project_id") or data.get("project_id")

            if client_id:
                booking.client = await self.get_client_info(int(client_id))
            if project_id:
                booking.project = await self.get_video_project(int(project_id))

            return booking

        except Exception as e:
            logger.error(f"Failed to parse appointment data: {e}")
            return None

    # ==================== Client CPT API ====================

    async def get_client_info(self, client_id: int) -> Optional[ClientInfo]:
        """Fetch client CPT information"""
        try:
            result = await self._request("GET", f"/wp/v2/client/{client_id}")
            return ClientInfo(
                id=result.get("id"),
                slug=result.get("slug", ""),
                name=result.get("title", {}).get("rendered", ""),
                logo_url=result.get("meta", {}).get("logo_url"),
                contact_email=result.get("meta", {}).get("contact_email"),
                contact_phone=result.get("meta", {}).get("contact_phone"),
            )
        except Exception as e:
            logger.error(f"Failed to fetch client {client_id}: {e}")
            return None

    async def get_clients(self, limit: int = 100) -> List[ClientInfo]:
        """Fetch all clients"""
        try:
            result = await self._request(
                "GET",
                "/wp/v2/client",
                params={"per_page": limit},
            )
            clients = []
            for item in result:
                clients.append(ClientInfo(
                    id=item.get("id"),
                    slug=item.get("slug", ""),
                    name=item.get("title", {}).get("rendered", ""),
                    logo_url=item.get("meta", {}).get("logo_url"),
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
            
            # Fetch graphics attached to this project
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
            # First get the client to find default_project_id
            client = await self.get_client_info(client_id)
            if not client or not client.default_project_id:
                logger.warning(f"Client {client_id} has no default project")
                return None
            
            # Fetch the default project
            return await self.get_video_project(client.default_project_id)
        except Exception as e:
            logger.error(f"Failed to get default project for client {client_id}: {e}")
            return None

    async def get_project_graphics(self, project_id: int) -> List[GraphicsFile]:
        """Fetch graphics files associated with a project"""
        try:
            # Try to get graphics from project meta or attached media
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

    # ==================== Content Type CPT APIs ====================

    async def get_recording_cpt(self, recording_id: int) -> Optional[Dict[str, Any]]:
        """Fetch recording CPT (talking head)"""
        try:
            result = await self._request("GET", f"/wp/v2/recordings/{recording_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to fetch recording CPT {recording_id}: {e}")
            return None

    async def get_course(self, course_id: int) -> Optional[Dict[str, Any]]:
        """Fetch course CPT (e-learning)"""
        try:
            result = await self._request("GET", f"/wp/v2/courses/{course_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to fetch course {course_id}: {e}")
            return None

    async def get_webinar(self, webinar_id: int) -> Optional[Dict[str, Any]]:
        """Fetch webinar CPT"""
        try:
            result = await self._request("GET", f"/wp/v2/webinars/{webinar_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to fetch webinar {webinar_id}: {e}")
            return None

    async def get_content_graphics(self, content_type: str, content_id: int) -> List[GraphicsFile]:
        """Fetch graphics files associated with any content type (recording/course/webinar)"""
        try:
            # Try to get graphics from content meta or attached media
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
            logger.error(f"Failed to fetch content graphics for {content_type} {content_id}: {e}")
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

    async def create_podcast(self, client_id: int, title: str) -> Optional[dict]:
        """Create a new Podcast CPT"""
        try:
            result = await self._request(
                "POST",
                "/wp/v2/podcasts",
                json_data={
                    "title": title,
                    "status": "publish",
                    "meta": {
                        "client_id": client_id,
                    },
                },
            )
            return result
        except Exception as e:
            logger.error(f"Failed to create podcast: {e}")
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

    async def attach_media_to_recording(
        self,
        recording_id: int,
        media_id: int,
    ) -> bool:
        """Attach a media file to a Recording CPT"""
        try:
            # Update the media's parent to be the recording
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
            
            # Read file and prepare multipart upload
            with open(file_path, "rb") as f:
                files = {
                    "file": (file_path.name, f, "video/x-matroska"),
                }
                data = {
                    "title": title,
                    "status": "private",  # Keep recordings private by default
                }
                if parent_post_id:
                    data["post"] = str(parent_post_id)

                response = await client.post(
                    f"{self.api_url}/wp/v2/media",
                    files=files,
                    data=data,
                    headers={
                        "Authorization": self.auth_header,
                        # Don't set Content-Type - httpx will set it for multipart
                    },
                    timeout=300.0,  # 5 minute timeout for large files
                )
                response.raise_for_status()
                result = response.json()
                
                media_id = result.get("id")
                logger.info(f"Uploaded recording to WordPress: {media_id}")
                return media_id

        except Exception as e:
            logger.error(f"Failed to upload recording: {e}")
            return None

    async def download_graphics(
        self,
        graphics: List[GraphicsFile],
        destination_dir: Path,
    ) -> List[str]:
        """Download graphics files to local directory"""
        downloaded_paths = []
        destination_dir.mkdir(parents=True, exist_ok=True)

        client = await self.get_client()

        for graphic in graphics:
            try:
                # Download file
                response = await client.get(graphic.url, timeout=60.0)
                response.raise_for_status()

                # Save to local path
                local_path = destination_dir / graphic.filename
                with open(local_path, "wb") as f:
                    f.write(response.content)

                downloaded_paths.append(str(local_path))
                logger.info(f"Downloaded graphic: {graphic.filename}")

            except Exception as e:
                logger.error(f"Failed to download graphic {graphic.url}: {e}")

        return downloaded_paths


# Singleton client instance
_wordpress_client: Optional[WordPressClient] = None


def get_wordpress_client() -> WordPressClient:
    """Get or create WordPress client singleton"""
    global _wordpress_client
    if _wordpress_client is None:
        _wordpress_client = WordPressClient()
    return _wordpress_client
