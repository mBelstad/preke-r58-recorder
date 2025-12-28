"""
Pydantic schemas for Fleet Management API.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field, EmailStr, field_validator


# =============================================================================
# Enums
# =============================================================================

class UserRole(str, Enum):
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


class DeviceStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    UPDATING = "updating"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class UpdateChannel(str, Enum):
    STABLE = "stable"
    BETA = "beta"
    DEV = "dev"


class CommandType(str, Enum):
    UPDATE = "update"
    REBOOT = "reboot"
    CONFIG = "config"
    BUNDLE = "bundle"
    RESTART_SERVICE = "restart_service"
    CUSTOM = "custom"


class CommandStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    ACKED = "acked"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SILENCED = "silenced"


# =============================================================================
# Organizations
# =============================================================================

class OrganizationBase(BaseModel):
    name: str
    slug: str


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None


class Organization(OrganizationBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    settings: Dict[str, Any] = {}
    max_devices: int = 10
    plan: str = "free"

    class Config:
        from_attributes = True


# =============================================================================
# Users
# =============================================================================

class UserBase(BaseModel):
    email: EmailStr
    name: str
    role: UserRole = UserRole.VIEWER


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class User(UserBase):
    id: UUID
    org_id: UUID
    created_at: datetime
    last_login: Optional[datetime] = None
    is_active: bool = True

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


# =============================================================================
# Devices
# =============================================================================

class DeviceBase(BaseModel):
    device_id: str
    name: str


class DeviceRegister(DeviceBase):
    """Request from device to register with fleet"""
    platform: Optional[str] = None
    arch: str = "arm64"
    serial_number: Optional[str] = None
    mac_address: Optional[str] = None
    current_version: Optional[str] = None
    capabilities: Optional[Dict[str, Any]] = None


class DeviceRegisterResponse(BaseModel):
    """Response after device registration"""
    device_id: str
    token: str  # Only returned once at registration
    fleet_url: str


class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    update_channel: Optional[UpdateChannel] = None
    target_version: Optional[str] = None


class Device(DeviceBase):
    id: UUID
    org_id: UUID
    status: DeviceStatus = DeviceStatus.OFFLINE
    last_heartbeat: Optional[datetime] = None
    current_version: Optional[str] = None
    target_version: Optional[str] = None
    update_channel: UpdateChannel = UpdateChannel.STABLE
    platform: Optional[str] = None
    arch: str = "arm64"
    capabilities: Dict[str, Any] = {}
    location: Optional[str] = None
    tags: List[str] = []
    metadata: Dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DeviceSummary(Device):
    """Device with latest metrics"""
    cpu_percent: Optional[float] = None
    mem_percent: Optional[float] = None
    disk_free_gb: Optional[float] = None
    temperature_c: Optional[float] = None
    recording_active: bool = False
    mixer_active: bool = False
    uptime_seconds: Optional[int] = None
    pending_commands: int = 0
    active_alerts: int = 0


# =============================================================================
# Heartbeats
# =============================================================================

class HeartbeatMetrics(BaseModel):
    cpu_percent: float
    mem_percent: float
    disk_free_gb: float
    disk_total_gb: Optional[float] = None
    temperature_c: Optional[float] = None
    load_avg: Optional[List[float]] = None


class HeartbeatStatus(BaseModel):
    recording_active: bool = False
    mixer_active: bool = False
    active_inputs: List[str] = []
    degradation_level: int = 0


class HeartbeatCreate(BaseModel):
    """Heartbeat payload from device"""
    ts: datetime
    version: str
    uptime_seconds: int
    metrics: HeartbeatMetrics
    status: HeartbeatStatus
    errors: List[str] = []


class HeartbeatResponse(BaseModel):
    """Response to heartbeat"""
    ack: bool = True
    commands_pending: int = 0
    target_version: Optional[str] = None
    server_time: datetime = Field(default_factory=datetime.utcnow)


class Heartbeat(BaseModel):
    id: int
    device_id: UUID
    received_at: datetime
    cpu_percent: Optional[float]
    mem_percent: Optional[float]
    disk_free_gb: Optional[float]
    temperature_c: Optional[float]
    uptime_seconds: Optional[int]
    recording_active: bool
    mixer_active: bool

    class Config:
        from_attributes = True


# =============================================================================
# Commands
# =============================================================================

class CommandCreate(BaseModel):
    """Create a new command for a device"""
    type: CommandType
    payload: Dict[str, Any] = {}
    priority: int = Field(default=5, ge=1, le=10)
    expires_at: Optional[datetime] = None
    notes: Optional[str] = None


class CommandUpdate(BaseModel):
    """Update command status (from device)"""
    status: CommandStatus
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class Command(BaseModel):
    id: UUID
    device_id: UUID
    type: CommandType
    payload: Dict[str, Any]
    status: CommandStatus
    priority: int
    created_at: datetime
    sent_at: Optional[datetime] = None
    acked_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    class Config:
        from_attributes = True


# =============================================================================
# Releases
# =============================================================================

class ReleaseCreate(BaseModel):
    version: str
    channel: UpdateChannel = UpdateChannel.STABLE
    artifact_url: str
    signature_url: Optional[str] = None
    checksum_sha256: str
    size_bytes: Optional[int] = None
    min_version: Optional[str] = None
    changelog: Optional[str] = None
    release_notes: Optional[str] = None
    manifest: Optional[Dict[str, Any]] = None


class Release(ReleaseCreate):
    id: UUID
    build_date: Optional[datetime] = None
    git_sha: Optional[str] = None
    arch: str = "arm64"
    is_active: bool = True
    is_latest: bool = False
    created_at: datetime
    published_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ReleaseLatest(BaseModel):
    """Response for latest release query"""
    version: str
    channel: str
    download_url: str
    signature_url: Optional[str] = None
    checksum_sha256: str
    size_bytes: Optional[int] = None
    changelog: Optional[str] = None


# =============================================================================
# Support Bundles
# =============================================================================

class BundleRequest(BaseModel):
    """Request to create a support bundle"""
    include_logs: bool = True
    include_config: bool = True
    include_recordings: bool = False
    include_diagnostics: bool = True
    notes: Optional[str] = None


class SupportBundle(BaseModel):
    id: UUID
    device_id: UUID
    storage_path: str
    size_bytes: Optional[int] = None
    device_version: Optional[str] = None
    created_at: datetime
    expires_at: Optional[datetime] = None
    status: str = "pending"
    includes_logs: bool
    includes_config: bool
    includes_recordings: bool

    class Config:
        from_attributes = True


# =============================================================================
# Alerts
# =============================================================================

class AlertCreate(BaseModel):
    type: str
    severity: AlertSeverity = AlertSeverity.WARNING
    title: str
    message: Optional[str] = None
    context: Dict[str, Any] = {}


class AlertUpdate(BaseModel):
    status: AlertStatus
    notes: Optional[str] = None


class Alert(AlertCreate):
    id: UUID
    device_id: UUID
    org_id: UUID
    status: AlertStatus = AlertStatus.ACTIVE
    created_at: datetime
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# =============================================================================
# Audit Log
# =============================================================================

class AuditLogEntry(BaseModel):
    id: int
    org_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    device_id: Optional[UUID] = None
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    details: Dict[str, Any] = {}
    ip_address: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# =============================================================================
# Pagination
# =============================================================================

class PaginatedResponse(BaseModel):
    """Generic paginated response"""
    items: List[Any]
    total: int
    page: int = 1
    page_size: int = 50
    has_more: bool = False

