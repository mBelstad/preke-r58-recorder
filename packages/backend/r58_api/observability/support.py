"""Support bundle generation"""
import io
import json
import zipfile
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ..config import get_settings
from .health import check_service_health, get_storage_status
from .metrics import get_cpu_metrics, get_disk_metrics, get_memory_metrics

router = APIRouter(prefix="/api/v1/support", tags=["Support"])


def get_recent_logs(service: str, lines: int = 500) -> str:
    """Get recent logs from journald"""
    import subprocess
    try:
        result = subprocess.run(
            ["journalctl", "-u", service, "-n", str(lines), "--no-pager"],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
        return f"Failed to get logs: {e}"


def get_system_info() -> dict:
    """Get system information"""
    import os
    import platform

    return {
        "hostname": platform.node(),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "architecture": platform.machine(),
        "processors": os.cpu_count(),
    }


def get_config_info() -> dict:
    """Get configuration (sanitized)"""
    settings = get_settings()
    return {
        "api_port": settings.api_port,
        "device_id": settings.device_id,
        "vdoninja_enabled": settings.vdoninja_enabled,
        "vdoninja_port": settings.vdoninja_port,
        "fleet_enabled": settings.fleet_enabled,
        "enabled_inputs": settings.enabled_inputs,
        # Don't include secrets
    }


@router.post("/bundle")
async def create_support_bundle() -> StreamingResponse:
    """
    Generate a support bundle ZIP file.

    Contains system info, logs, configuration, and diagnostic data.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Create in-memory ZIP file
    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        # System info
        system_info = {
            "generated_at": datetime.now().isoformat(),
            "system": get_system_info(),
            "config": get_config_info(),
        }
        zf.writestr("system_info.json", json.dumps(system_info, indent=2))

        # Metrics snapshot
        metrics = {
            "cpu": get_cpu_metrics().model_dump(),
            "memory": get_memory_metrics().model_dump(),
            "disks": [d.model_dump() for d in get_disk_metrics()],
            "storage": get_storage_status().model_dump(),
        }
        zf.writestr("metrics.json", json.dumps(metrics, indent=2))

        # Service health
        services = ["r58-api", "r58-pipeline", "mediamtx"]
        health = {}
        for service in services:
            health[service] = check_service_health(service).model_dump()
        zf.writestr("health.json", json.dumps(health, indent=2))

        # Recent logs
        for service in services:
            logs = get_recent_logs(service)
            zf.writestr(f"logs/{service}.log", logs)

        # Config file (if exists)
        config_path = Path("/etc/r58/r58.env")
        if config_path.exists():
            try:
                # Sanitize sensitive values
                content = config_path.read_text()
                sanitized = []
                for line in content.split("\n"):
                    if "SECRET" in line.upper() or "PASSWORD" in line.upper():
                        key = line.split("=")[0] if "=" in line else line
                        sanitized.append(f"{key}=***REDACTED***")
                    else:
                        sanitized.append(line)
                zf.writestr("config/r58.env", "\n".join(sanitized))
            except Exception as e:
                zf.writestr("config/r58.env", f"Error reading config: {e}")

        # MediaMTX config
        mediamtx_path = Path("/opt/r58/mediamtx.yml")
        if mediamtx_path.exists():
            try:
                zf.writestr("config/mediamtx.yml", mediamtx_path.read_text())
            except Exception as e:
                zf.writestr("config/mediamtx.yml", f"Error reading config: {e}")

    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=r58-support-bundle-{timestamp}.zip"
        }
    )


@router.get("/logs")
async def get_logs(
    service: str = "r58-api",
    lines: int = 100
) -> dict:
    """
    Get recent logs for a service.

    Args:
        service: Service name (r58-api, r58-pipeline, mediamtx)
        lines: Number of lines to return (max 1000)
    """
    lines = min(lines, 1000)
    logs = get_recent_logs(service, lines)

    return {
        "service": service,
        "lines": lines,
        "logs": logs,
    }

