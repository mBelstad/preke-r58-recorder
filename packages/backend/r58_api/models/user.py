"""User models"""
from typing import Optional
import uuid

from sqlmodel import SQLModel, Field


class UserBase(SQLModel):
    """Base user fields"""
    username: str = Field(unique=True, index=True)
    role: str = "operator"  # admin, operator, viewer
    disabled: bool = False


class User(UserBase, table=True):
    """User database model"""
    __tablename__ = "users"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    hashed_password: str


class UserCreate(SQLModel):
    """Create user request"""
    username: str
    password: str
    role: str = "operator"


class UserRead(UserBase):
    """Read user response"""
    id: str


class UserUpdate(SQLModel):
    """Update user request"""
    role: Optional[str] = None
    disabled: Optional[bool] = None
    password: Optional[str] = None

