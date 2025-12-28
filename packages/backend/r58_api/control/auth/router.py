"""Authentication endpoints"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from jose import JWTError, jwt
from passlib.context import CryptContext

from ...config import Settings, get_settings

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


class Token(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str
    expires_in: int


class TokenData(BaseModel):
    """Decoded token data"""
    username: Optional[str] = None
    role: str = "operator"


class User(BaseModel):
    """User model"""
    username: str
    role: str  # "admin", "operator", "viewer"
    disabled: bool = False


class UserInDB(User):
    """User model with hashed password"""
    hashed_password: str


class LoginRequest(BaseModel):
    """Login request"""
    username: str
    password: str


class UserResponse(BaseModel):
    """Current user response"""
    username: str
    role: str


# Fake users database - in production, use real database
FAKE_USERS_DB = {
    "admin": {
        "username": "admin",
        "hashed_password": pwd_context.hash("admin"),  # Change in production!
        "role": "admin",
        "disabled": False,
    },
    "operator": {
        "username": "operator",
        "hashed_password": pwd_context.hash("operator"),  # Change in production!
        "role": "operator",
        "disabled": False,
    },
}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_user(username: str) -> Optional[UserInDB]:
    """Get user from database"""
    if username in FAKE_USERS_DB:
        user_dict = FAKE_USERS_DB[username]
        return UserInDB(**user_dict)
    return None


def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    """Authenticate user with username and password"""
    user = get_user(username)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


def create_access_token(
    data: dict,
    settings: Settings,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes)
    
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    settings: Settings = Depends(get_settings)
) -> Optional[User]:
    """Get current user from JWT token"""
    if not token:
        return None
    
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm]
        )
        username: str = payload.get("sub")
        if username is None:
            return None
        
        token_data = TokenData(username=username, role=payload.get("role", "operator"))
    except JWTError:
        return None
    
    user = get_user(token_data.username)
    if user is None or user.disabled:
        return None
    
    return User(username=user.username, role=user.role)


async def require_auth(
    user: Optional[User] = Depends(get_current_user)
) -> User:
    """Require authenticated user"""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def require_admin(
    user: User = Depends(require_auth)
) -> User:
    """Require admin role"""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    settings: Settings = Depends(get_settings)
) -> Token:
    """Login and get access token"""
    user = authenticate_user(form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role},
        settings=settings,
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.jwt_expire_minutes * 60,
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    user: User = Depends(require_auth),
    settings: Settings = Depends(get_settings)
) -> Token:
    """Refresh access token"""
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role},
        settings=settings,
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.jwt_expire_minutes * 60,
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    user: User = Depends(require_auth)
) -> UserResponse:
    """Get current user information"""
    return UserResponse(username=user.username, role=user.role)

