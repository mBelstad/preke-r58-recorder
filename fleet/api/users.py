"""
User management endpoints for Fleet Management.
"""
import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db
from ..models.schemas import (
    User,
    UserCreate,
    UserUpdate,
    UserRole,
    PaginatedResponse,
)
from .auth import get_current_user, require_role, hash_password

logger = logging.getLogger(__name__)
router = APIRouter()


# In-memory user storage (replace with actual database)
_users: dict[str, dict] = {
    "admin@example.com": {
        "id": "00000000-0000-0000-0000-000000000001",
        "email": "admin@example.com",
        "password_hash": hash_password("admin"),
        "name": "Admin User",
        "role": UserRole.ADMIN,
        "org_id": "00000000-0000-0000-0000-000000000001",
        "created_at": datetime(2025, 1, 1),
        "is_active": True,
    }
}


@router.get("/users", response_model=PaginatedResponse)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    role: Optional[UserRole] = None,
    user: dict = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """
    List all users in the organization.
    
    Requires admin privileges.
    """
    users = list(_users.values())
    
    # Filter by org (in production)
    # users = [u for u in users if u["org_id"] == user["org_id"]]
    
    # Filter by role
    if role:
        users = [u for u in users if u["role"] == role]
    
    # Sort by creation time
    users.sort(key=lambda u: u["created_at"], reverse=True)
    
    # Remove password hashes from response
    safe_users = [
        {k: v for k, v in u.items() if k != "password_hash"}
        for u in users
    ]
    
    # Paginate
    total = len(safe_users)
    start = (page - 1) * page_size
    end = start + page_size
    page_users = safe_users[start:end]
    
    return PaginatedResponse(
        items=page_users,
        total=total,
        page=page,
        page_size=page_size,
        has_more=end < total,
    )


@router.post("/users", response_model=User)
async def create_user(
    user_create: UserCreate,
    current_user: dict = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new user.
    
    Requires admin privileges.
    """
    # Check if email already exists
    if user_create.email in _users:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
    
    # Create user
    user_record = {
        "id": str(uuid4()),
        "email": user_create.email,
        "password_hash": hash_password(user_create.password),
        "name": user_create.name,
        "role": user_create.role,
        "org_id": current_user["org_id"],
        "created_at": datetime.utcnow(),
        "is_active": True,
    }
    
    _users[user_create.email] = user_record
    
    logger.info(f"Created user {user_create.email} with role {user_create.role}")
    
    return User(
        id=UUID(user_record["id"]),
        email=user_record["email"],
        name=user_record["name"],
        role=user_record["role"],
        org_id=UUID(user_record["org_id"]),
        created_at=user_record["created_at"],
        is_active=user_record["is_active"],
    )


@router.get("/users/{user_id}", response_model=User)
async def get_user(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get details of a specific user.
    """
    # Find user by ID
    for email, user in _users.items():
        if user["id"] == user_id:
            return User(
                id=UUID(user["id"]),
                email=user["email"],
                name=user["name"],
                role=user["role"],
                org_id=UUID(user["org_id"]),
                created_at=user["created_at"],
                last_login=user.get("last_login"),
                is_active=user.get("is_active", True),
            )
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found",
    )


@router.patch("/users/{user_id}", response_model=User)
async def update_user(
    user_id: str,
    update: UserUpdate,
    current_user: dict = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a user.
    
    Requires admin privileges.
    """
    # Find user by ID
    for email, user in _users.items():
        if user["id"] == user_id:
            # Apply updates
            update_data = update.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                user[key] = value
            
            logger.info(f"Updated user {user_id}: {list(update_data.keys())}")
            
            return User(
                id=UUID(user["id"]),
                email=user["email"],
                name=user["name"],
                role=user["role"],
                org_id=UUID(user["org_id"]),
                created_at=user["created_at"],
                last_login=user.get("last_login"),
                is_active=user.get("is_active", True),
            )
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found",
    )


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    current_user: dict = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a user.
    
    Requires admin privileges.
    Cannot delete yourself.
    """
    if current_user["id"] == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself",
        )
    
    # Find and delete user by ID
    for email, user in list(_users.items()):
        if user["id"] == user_id:
            del _users[email]
            logger.warning(f"Deleted user {user_id}")
            return
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found",
    )


@router.post("/users/{user_id}/reset-password", response_model=dict)
async def reset_user_password(
    user_id: str,
    current_user: dict = Depends(require_role(UserRole.ADMIN)),
):
    """
    Reset a user's password.
    
    Generates a new random password.
    Requires admin privileges.
    """
    import secrets
    
    # Find user by ID
    for email, user in _users.items():
        if user["id"] == user_id:
            new_password = secrets.token_urlsafe(12)
            user["password_hash"] = hash_password(new_password)
            
            logger.warning(f"Reset password for user {user_id}")
            
            return {
                "user_id": user_id,
                "temporary_password": new_password,
                "message": "Password reset. User must change password on next login.",
            }
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found",
    )

