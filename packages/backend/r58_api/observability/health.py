"""Health check endpoints for observability"""
import asyncio
import logging
import shutil
import socket
import subprocess
from datetime import datetime
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel

from ..config import Settings, get_settings
from ..media.pipeline_client import get_pipeline_client

router = APIRouter(prefix="/api/v1", tags=["Health"])
logger = logging.getLogger(__name__)


class ServiceStatus(BaseModel):
    """Individual service status"""
    name: str
    status: str  # "healthy", "degraded", "unhealthy"
    message: Optional[str] = None


class StorageStatus(BaseModel):
    """Storage status information"""
    total_gb: float
    available_gb: float
    used_percent: float


class DetailedHealth(BaseModel):
    """Detailed health check response"""
    status: str  # "healthy", "degraded", "unhealthy"
    timestamp: datetime
    services: list[ServiceStatus]
    storage: StorageStatus
    uptime_seconds: float


# Track startup time
_startup_time = datetime.now()


async def check_service_health(name: str) -> ServiceStatus:
    """Check health of a specific service"""
    settings = get_settings()

    if name == "pipeline_manager":
        return await _check_pipeline_manager()

    elif name == "mediamtx":
        return await _check_mediamtx(settings)

    elif name == "vdoninja":
        return await _check_vdoninja(settings)
    
    elif name == "frp_tunnel":
        return await _check_frp_tunnel()

    # Default healthy status for unknown services
    return ServiceStatus(
        name=name,
        status="healthy",
        message=None,
    )


async def _check_pipeline_manager() -> ServiceStatus:
    """Check pipeline manager health via IPC"""
    client = get_pipeline_client()

    try:
        result = await client._send_command(
            {"cmd": "status"},
            timeout=2.0,
            retries=0,  # No retries for health check
        )

        if result.get("error"):
            return ServiceStatus(
                name="pipeline_manager",
                status="unhealthy",
                message=str(result.get("error")),
            )

        # Check if pipeline is healthy based on IPC consecutive failures
        if not client.is_healthy:
            return ServiceStatus(
                name="pipeline_manager",
                status="degraded",
                message=f"Intermittent failures ({client._consecutive_failures})",
            )

        return ServiceStatus(
            name="pipeline_manager",
            status="healthy",
            message=None,
        )
    except Exception as e:
        return ServiceStatus(
            name="pipeline_manager",
            status="unhealthy",
            message=str(e),
        )


async def _check_mediamtx(settings: Settings) -> ServiceStatus:
    """
    Check MediaMTX health by calling its API.

    MediaMTX API endpoints:
    - GET /v3/paths/list - List all paths
    - GET /v3/config/global/get - Get global config
    """
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            # Try to list paths - this confirms MediaMTX is running
            url = f"{settings.mediamtx_api_url}/v3/paths/list"
            resp = await client.get(url)

            if resp.status_code == 200:
                data = resp.json()
                items = data.get("items", [])
                active_paths = len([p for p in items if p.get("ready")])

                return ServiceStatus(
                    name="mediamtx",
                    status="healthy",
                    message=f"{active_paths} active paths",
                )
            else:
                return ServiceStatus(
                    name="mediamtx",
                    status="degraded",
                    message=f"API returned HTTP {resp.status_code}",
                )

    except httpx.ConnectError:
        return ServiceStatus(
            name="mediamtx",
            status="unhealthy",
            message="Connection refused - MediaMTX not running",
        )
    except httpx.TimeoutException:
        return ServiceStatus(
            name="mediamtx",
            status="degraded",
            message="API timeout",
        )
    except Exception as e:
        logger.warning(f"MediaMTX health check failed: {e}")
        return ServiceStatus(
            name="mediamtx",
            status="unhealthy",
            message=str(e),
        )


async def _check_vdoninja(settings: Settings) -> ServiceStatus:
    """
    Check VDO.ninja local server health.

    VDO.ninja runs on HTTPS port 8443 on the R58.
    """
    if not settings.vdoninja_enabled:
        return ServiceStatus(
            name="vdoninja",
            status="healthy",
            message="Disabled in config",
        )

    try:
        # VDO.ninja is served over HTTPS, might have self-signed cert
        async with httpx.AsyncClient(timeout=3.0, verify=False) as client:
            url = f"https://localhost:{settings.vdoninja_port}/"
            resp = await client.get(url)

            if resp.status_code == 200:
                return ServiceStatus(
                    name="vdoninja",
                    status="healthy",
                    message=f"Running on port {settings.vdoninja_port}",
                )
            else:
                return ServiceStatus(
                    name="vdoninja",
                    status="degraded",
                    message=f"HTTP {resp.status_code}",
                )

    except httpx.ConnectError:
        return ServiceStatus(
            name="vdoninja",
            status="unhealthy",
            message="Connection refused - VDO.ninja not running",
        )
    except httpx.TimeoutException:
        return ServiceStatus(
            name="vdoninja",
            status="degraded",
            message="Timeout",
        )
    except Exception as e:
        logger.warning(f"VDO.ninja health check failed: {e}")
        return ServiceStatus(
            name="vdoninja",
            status="unhealthy",
            message=str(e),
        )


async def _check_frp_tunnel() -> ServiceStatus:
    """
    Check FRP tunnel health by verifying connection to VPS.
    
    Checks:
    1. frpc systemd service is running
    2. TCP connectivity to VPS port 10022
    """
    try:
        # Check if frpc service is running
        result = subprocess.run(
            ["systemctl", "is-active", "frpc"],
            capture_output=True,
            text=True,
            timeout=2.0,
        )
        
        service_running = result.returncode == 0 and result.stdout.strip() == "active"
        
        if not service_running:
            return ServiceStatus(
                name="frp_tunnel",
                status="unhealthy",
                message="frpc service not running",
            )
        
        # Test TCP connectivity to VPS
        vps_host = "65.109.32.111"
        vps_port = 10022
        
        try:
            # Create socket with 3 second timeout
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3.0)
            
            # Try to connect
            result = sock.connect_ex((vps_host, vps_port))
            sock.close()
            
            if result == 0:
                return ServiceStatus(
                    name="frp_tunnel",
                    status="healthy",
                    message=f"Connected to {vps_host}:{vps_port}",
                )
            else:
                return ServiceStatus(
                    name="frp_tunnel",
                    status="degraded",
                    message=f"Service running but port {vps_port} not reachable",
                )
        
        except socket.timeout:
            return ServiceStatus(
                name="frp_tunnel",
                status="degraded",
                message="Connection timeout to VPS",
            )
        except Exception as e:
            return ServiceStatus(
                name="frp_tunnel",
                status="degraded",
                message=f"Connection test failed: {str(e)}",
            )
    
    except subprocess.TimeoutExpired:
        return ServiceStatus(
            name="frp_tunnel",
            status="unhealthy",
            message="systemctl check timed out",
        )
    except Exception as e:
        logger.warning(f"FRP tunnel health check failed: {e}")
        return ServiceStatus(
            name="frp_tunnel",
            status="unhealthy",
            message=str(e),
        )


def get_storage_status() -> StorageStatus:
    """Get current storage status"""
    try:
        usage = shutil.disk_usage("/")
        total_gb = usage.total / (1024 ** 3)
        available_gb = usage.free / (1024 ** 3)
        used_percent = ((usage.total - usage.free) / usage.total) * 100
        return StorageStatus(
            total_gb=round(total_gb, 2),
            available_gb=round(available_gb, 2),
            used_percent=round(used_percent, 1),
        )
    except Exception:
        return StorageStatus(
            total_gb=0.0,
            available_gb=0.0,
            used_percent=0.0,
        )


@router.get("/health")
async def health_check(response: Response):
    """
    Simple health check endpoint.

    Returns 200 if the API is running, 503 if unhealthy.
    Checks pipeline manager connectivity.
    """
    # Check pipeline manager health
    pipeline_status = await check_service_health("pipeline_manager")

    if pipeline_status.status == "unhealthy":
        response.status_code = 503
        return {
            "status": "unhealthy",
            "message": f"Pipeline manager: {pipeline_status.message}",
        }

    # Check disk space
    storage = get_storage_status()
    if storage.available_gb < 1.0:  # Less than 1GB warning
        response.status_code = 503
        return {
            "status": "unhealthy",
            "message": f"Low disk space: {storage.available_gb:.1f}GB available",
        }

    if pipeline_status.status == "degraded":
        return {
            "status": "degraded",
            "message": pipeline_status.message,
        }

    return {"status": "healthy"}


@router.get("/health/detailed", response_model=DetailedHealth)
async def detailed_health_check(
    settings: Settings = Depends(get_settings)
) -> DetailedHealth:
    """
    Detailed health check with service status.

    Checks all dependent services and returns overall health.
    """
    services = [
        ServiceStatus(name="api", status="healthy"),  # If we're here, API is healthy
        await check_service_health("pipeline_manager"),
        await check_service_health("mediamtx"),
        await check_service_health("frp_tunnel"),
    ]

    if settings.vdoninja_enabled:
        services.append(await check_service_health("vdoninja"))

    # Determine overall status
    if any(s.status == "unhealthy" for s in services):
        overall_status = "unhealthy"
    elif any(s.status == "degraded" for s in services):
        overall_status = "degraded"
    else:
        overall_status = "healthy"

    uptime = (datetime.now() - _startup_time).total_seconds()

    return DetailedHealth(
        status=overall_status,
        timestamp=datetime.now(),
        services=services,
        storage=get_storage_status(),
        uptime_seconds=uptime,
    )

