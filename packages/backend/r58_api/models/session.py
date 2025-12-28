"""Recording session models"""
from datetime import datetime
from typing import Optional, List
import uuid

from sqlmodel import SQLModel, Field, Relationship


class RecordingSessionBase(SQLModel):
    """Base recording session fields"""
    name: Optional[str] = None
    started_at: datetime
    ended_at: Optional[datetime] = None
    status: str = "recording"  # recording, completed, failed
    total_bytes: int = 0


class RecordingSession(RecordingSessionBase, table=True):
    """Recording session database model"""
    __tablename__ = "recording_sessions"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    
    # Relationship to recordings
    recordings: List["Recording"] = Relationship(back_populates="session")


class RecordingSessionCreate(SQLModel):
    """Create recording session request"""
    name: Optional[str] = None
    inputs: Optional[List[str]] = None


class RecordingSessionRead(RecordingSessionBase):
    """Read recording session response"""
    id: str
    recordings: List["RecordingRead"] = []


class RecordingBase(SQLModel):
    """Base recording fields"""
    input_id: str
    file_path: str
    duration_ms: int = 0
    bytes: int = 0
    codec: str = "h264"
    resolution: str = "1920x1080"


class Recording(RecordingBase, table=True):
    """Recording database model"""
    __tablename__ = "recordings"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    session_id: str = Field(foreign_key="recording_sessions.id")
    
    # Relationship to session
    session: RecordingSession = Relationship(back_populates="recordings")


class RecordingRead(RecordingBase):
    """Read recording response"""
    id: str
    session_id: str


# Update forward references
RecordingSessionRead.model_rebuild()

