"""
Fleet Management Server Configuration
"""
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Fleet server configuration"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="FLEET_",
        extra="ignore",
    )
    
    # Server
    # Note: Using 8180 to avoid conflict with Coolify relay (8080)
    host: str = "0.0.0.0"
    port: int = 8180
    debug: bool = False
    
    # Database
    database_url: str = "postgresql://fleet:fleet@localhost:5432/fleet"
    
    # Authentication
    jwt_secret: str = "change-this-secret-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24  # 24 hours
    
    # CORS
    cors_origins: List[str] = ["*"]
    
    # Storage (for support bundles)
    storage_provider: str = "local"  # local, s3
    storage_path: str = "/var/lib/fleet/bundles"
    s3_bucket: Optional[str] = None
    s3_region: Optional[str] = None
    
    # Releases storage
    releases_base_url: str = "https://releases.r58.itagenten.no"
    releases_path: str = "/var/lib/fleet/releases"
    
    # Device management
    heartbeat_timeout_seconds: int = 180  # 3 minutes
    command_default_expiry_hours: int = 24
    
    # Rate limiting
    rate_limit_requests: int = 100
    rate_limit_period: int = 60  # seconds


settings = Settings()

