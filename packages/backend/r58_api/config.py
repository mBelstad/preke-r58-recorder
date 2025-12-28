"""Configuration management using Pydantic Settings"""
from pathlib import Path
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """R58 API Configuration"""

    model_config = SettingsConfigDict(
        env_file="/etc/r58/r58.env",
        env_prefix="R58_",
    )

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False

    # Auth
    jwt_secret: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days

    # Database
    db_path: Path = Path("/var/lib/r58/r58.db")

    # MediaMTX
    mediamtx_api_url: str = "http://localhost:9997"
    # Use HTTPS for WHEP since MediaMTX has TLS enabled
    mediamtx_whep_base: str = "https://localhost:8889"
    mediamtx_whep_port: int = 8889

    # VDO.ninja (LOCAL on R58)
    vdoninja_enabled: bool = True
    vdoninja_port: int = 8443
    vdoninja_room: str = "studio"

    # Fleet
    fleet_enabled: bool = False
    fleet_api_url: str = "https://fleet.r58.itagenten.no"
    device_id: str = "r58-dev-001"

    # Inputs (detected or configured)
    enabled_inputs: List[str] = ["cam1", "cam2"]

    # Pipeline Manager IPC
    pipeline_socket_path: str = "/run/r58/pipeline.sock"


# Singleton settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create settings singleton"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

