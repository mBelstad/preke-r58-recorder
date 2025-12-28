"""
Authentication endpoints and utilities for Fleet Management.
"""
import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..config import settings
from ..database import get_db
from ..models.schemas import UserLogin, TokenResponse, User, UserRole

logger = logging.getLogger(__name__)
router = APIRouter()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Bearer scheme
bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """Hash a password for storage"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def hash_token(token: str) -> str:
    """Hash a device token for storage"""
    return hashlib.sha256(token.encode()).hexdigest()


def generate_device_token() -> str:
    """Generate a secure device token (64 chars)"""
    return secrets.token_hex(32)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.jwt_expire_minutes))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token"""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get current authenticated user from JWT token.
    
    Returns user dict with id, email, role, org_id.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    payload = decode_token(credentials.credentials)
    user_id = payload.get("sub")
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    
    # In production, fetch user from database
    # For now, return the payload
    return {
        "id": user_id,
        "email": payload.get("email"),
        "role": payload.get("role", "viewer"),
        "org_id": payload.get("org_id"),
    }


async def require_role(required_role: UserRole):
    """Dependency factory to require specific role"""
    async def role_checker(user: dict = Depends(get_current_user)) -> dict:
        role_hierarchy = {
            UserRole.VIEWER: 0,
            UserRole.OPERATOR: 1,
            UserRole.ADMIN: 2,
        }
        
        user_level = role_hierarchy.get(UserRole(user["role"]), 0)
        required_level = role_hierarchy.get(required_role, 0)
        
        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {required_role.value} role or higher",
            )
        
        return user
    
    return role_checker


async def get_device_from_token(
    x_device_token: Optional[str] = Header(None, alias="X-Device-Token"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Authenticate device from X-Device-Token header.
    
    Returns device dict with id, device_id, org_id.
    """
    if not x_device_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Device-Token header",
        )
    
    token_hash = hash_token(x_device_token)
    
    # In production, look up device by token hash
    # For now, return a placeholder
    # result = await db.execute(
    #     select(Device).where(Device.token_hash == token_hash)
    # )
    # device = result.scalar_one_or_none()
    
    # Placeholder - in real implementation, query database
    return {
        "id": "placeholder",
        "device_id": "r58-dev-001",
        "org_id": "00000000-0000-0000-0000-000000000001",
    }


@router.post("/auth/login", response_model=TokenResponse)
async def login(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate user and return JWT token.
    """
    # In production, look up user from database
    # result = await db.execute(
    #     select(User).where(User.email == credentials.email)
    # )
    # user = result.scalar_one_or_none()
    # if not user or not verify_password(credentials.password, user.password_hash):
    #     raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Placeholder for demo
    if credentials.email != "admin@example.com" or credentials.password != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    
    # Create token
    token_data = {
        "sub": "00000000-0000-0000-0000-000000000001",
        "email": credentials.email,
        "role": "admin",
        "org_id": "00000000-0000-0000-0000-000000000001",
    }
    
    access_token = create_access_token(token_data)
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.jwt_expire_minutes * 60,
    )


@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh_token(
    user: dict = Depends(get_current_user),
):
    """
    Refresh an existing JWT token.
    """
    token_data = {
        "sub": user["id"],
        "email": user["email"],
        "role": user["role"],
        "org_id": user["org_id"],
    }
    
    access_token = create_access_token(token_data)
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.jwt_expire_minutes * 60,
    )


@router.get("/auth/me")
async def get_me(user: dict = Depends(get_current_user)):
    """Get current user info"""
    return user

