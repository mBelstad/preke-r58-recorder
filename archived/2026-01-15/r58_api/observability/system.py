"""System control and monitoring endpoint.

Provides system-level controls including:
- Temperature monitoring
- Service restart
- System reboot
- Pipeline management
"""
import asyncio
import logging
import os
import subprocess
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/system", tags=["System"])


class TemperatureInfo(BaseModel):
    """Temperature sensor reading."""
    zone: str
    temp_celsius: float
    type: Optional[str] = None


class SystemInfo(BaseModel):
    """System information and status."""
    hostname: str
    uptime_seconds: float
    load_average: List[float]
    temperatures: List[TemperatureInfo]
    platform: str


class ServiceStatus(BaseModel):
    """Status of a systemd service."""
    name: str
    active: bool
    status: str
    pid: Optional[int] = None
    memory_mb: Optional[float] = None


class PipelineInfo(BaseModel):
    """Information about a running pipeline."""
    pipeline_id: str
    pipeline_type: str
    state: str
    started_at: Optional[str] = None
    device: Optional[str] = None


class SystemStatus(BaseModel):
    """Complete system status."""
    info: SystemInfo
    services: List[ServiceStatus]
    pipelines: List[PipelineInfo]
    timestamp: str


class RestartRequest(BaseModel):
    """Request to restart a service."""
    service: str  # "api", "pipeline", "all"


class RestartResponse(BaseModel):
    """Response from restart operation."""
    success: bool
    message: str
    restarted_services: List[str]


class RebootResponse(BaseModel):
    """Response from reboot operation."""
    success: bool
    message: str
    delay_seconds: int


def get_temperatures() -> List[TemperatureInfo]:
    """Read temperature from thermal zones."""
    temperatures = []
    
    # Check thermal zones
    thermal_base = "/sys/class/thermal"
    if os.path.exists(thermal_base):
        try:
            for zone in os.listdir(thermal_base):
                if zone.startswith("thermal_zone"):
                    zone_path = os.path.join(thermal_base, zone)
                    temp_path = os.path.join(zone_path, "temp")
                    type_path = os.path.join(zone_path, "type")
                    
                    if os.path.exists(temp_path):
                        try:
                            with open(temp_path) as f:
                                temp_raw = int(f.read().strip())
                                # Temperature is in millidegrees
                                temp_celsius = temp_raw / 1000.0
                            
                            zone_type = None
                            if os.path.exists(type_path):
                                with open(type_path) as f:
                                    zone_type = f.read().strip()
                            
                            temperatures.append(TemperatureInfo(
                                zone=zone,
                                temp_celsius=temp_celsius,
                                type=zone_type,
                            ))
                        except (ValueError, IOError):
                            continue
        except Exception as e:
            logger.warning(f"Error reading thermal zones: {e}")
    
    return temperatures


def get_uptime() -> float:
    """Get system uptime in seconds."""
    try:
        with open("/proc/uptime") as f:
            return float(f.read().split()[0])
    except Exception:
        return 0.0


def get_load_average() -> List[float]:
    """Get system load average."""
    try:
        return list(os.getloadavg())
    except Exception:
        return [0.0, 0.0, 0.0]


def get_hostname() -> str:
    """Get system hostname."""
    try:
        import socket
        return socket.gethostname()
    except Exception:
        return "unknown"


def get_platform() -> str:
    """Detect platform (r58 or macos)."""
    import platform
    if platform.system() == "Darwin":
        return "macos"
    elif os.path.exists("/sys/class/thermal"):
        return "r58"
    else:
        return "linux"


def get_service_status(service_name: str) -> ServiceStatus:
    """Get status of a systemd service."""
    try:
        result = subprocess.run(
            ["systemctl", "is-active", service_name],
            capture_output=True,
            text=True,
            timeout=5
        )
        is_active = result.stdout.strip() == "active"
        
        # Get more details
        status_result = subprocess.run(
            ["systemctl", "show", service_name, 
             "--property=MainPID,MemoryCurrent,SubState"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        pid = None
        memory_mb = None
        sub_state = "unknown"
        
        for line in status_result.stdout.splitlines():
            if line.startswith("MainPID="):
                try:
                    pid = int(line.split("=")[1])
                    if pid == 0:
                        pid = None
                except ValueError:
                    pass
            elif line.startswith("MemoryCurrent="):
                try:
                    mem_bytes = int(line.split("=")[1])
                    memory_mb = mem_bytes / (1024 * 1024)
                except ValueError:
                    pass
            elif line.startswith("SubState="):
                sub_state = line.split("=")[1]
        
        return ServiceStatus(
            name=service_name,
            active=is_active,
            status=sub_state,
            pid=pid,
            memory_mb=memory_mb,
        )
        
    except subprocess.TimeoutExpired:
        return ServiceStatus(name=service_name, active=False, status="timeout")
    except FileNotFoundError:
        # systemctl not available (macOS)
        return ServiceStatus(name=service_name, active=False, status="unsupported")
    except Exception as e:
        logger.warning(f"Error getting service status for {service_name}: {e}")
        return ServiceStatus(name=service_name, active=False, status="error")


async def get_pipeline_info() -> List[PipelineInfo]:
    """Get info about running pipelines from pipeline manager."""
    from ..media.pipeline_client import get_pipeline_client
    
    try:
        client = get_pipeline_client()
        result = await client.get_pipelines()
        
        pipelines = []
        for pid, info in result.get("pipelines", {}).items():
            pipelines.append(PipelineInfo(
                pipeline_id=pid,
                pipeline_type=info.get("pipeline_type", "unknown"),
                state=info.get("state", "unknown"),
                started_at=info.get("started_at"),
                device=info.get("device"),
            ))
        return pipelines
        
    except Exception as e:
        logger.warning(f"Error getting pipeline info: {e}")
        return []


@router.get("/status", response_model=SystemStatus)
async def get_system_status() -> SystemStatus:
    """
    Get complete system status.
    
    Includes system info, service status, and pipeline information.
    """
    # Get pipeline info asynchronously
    pipelines = await get_pipeline_info()
    
    # Get service status for R58 services
    services = [
        get_service_status("r58-api"),
        get_service_status("r58-pipeline"),
        get_service_status("mediamtx"),
    ]
    
    return SystemStatus(
        info=SystemInfo(
            hostname=get_hostname(),
            uptime_seconds=get_uptime(),
            load_average=get_load_average(),
            temperatures=get_temperatures(),
            platform=get_platform(),
        ),
        services=services,
        pipelines=pipelines,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.post("/restart", response_model=RestartResponse)
async def restart_services(request: RestartRequest) -> RestartResponse:
    """
    Restart R58 services.
    
    Args:
        request: Which service(s) to restart ("api", "pipeline", "all")
    
    Note: Restarting "api" will cause this request to not receive a response.
    """
    service_map = {
        "api": ["r58-api"],
        "pipeline": ["r58-pipeline"],
        "all": ["r58-pipeline", "r58-api"],  # Pipeline first, then API
    }
    
    services = service_map.get(request.service)
    if not services:
        raise HTTPException(status_code=400, detail=f"Unknown service: {request.service}")
    
    restarted = []
    
    for service in services:
        try:
            result = subprocess.run(
                ["sudo", "systemctl", "restart", service],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                restarted.append(service)
                logger.info(f"Restarted service: {service}")
            else:
                logger.error(f"Failed to restart {service}: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout restarting {service}")
        except FileNotFoundError:
            raise HTTPException(status_code=501, detail="systemctl not available on this platform")
        except Exception as e:
            logger.error(f"Error restarting {service}: {e}")
    
    return RestartResponse(
        success=len(restarted) > 0,
        message=f"Restarted {len(restarted)} of {len(services)} services",
        restarted_services=restarted,
    )


@router.post("/reboot", response_model=RebootResponse)
async def reboot_system() -> RebootResponse:
    """
    Reboot the R58 device.
    
    The reboot will be scheduled after a 5 second delay to allow
    this response to be sent to the client.
    
    Warning: This will cause all connections to be lost.
    """
    platform = get_platform()
    
    if platform == "macos":
        raise HTTPException(status_code=501, detail="Reboot not supported on macOS")
    
    delay_seconds = 5
    
    try:
        # Schedule reboot with delay
        subprocess.Popen(
            ["sudo", "shutdown", "-r", f"+{delay_seconds // 60}", "R58 API requested reboot"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        
        logger.warning(f"System reboot scheduled in {delay_seconds} seconds")
        
        return RebootResponse(
            success=True,
            message=f"Reboot scheduled in {delay_seconds} seconds",
            delay_seconds=delay_seconds,
        )
        
    except FileNotFoundError:
        raise HTTPException(status_code=501, detail="shutdown command not available")
    except Exception as e:
        logger.error(f"Error scheduling reboot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pipeline/{pipeline_id}/stop")
async def stop_pipeline(pipeline_id: str) -> Dict[str, Any]:
    """
    Stop a specific pipeline.
    
    Args:
        pipeline_id: The pipeline ID to stop (e.g., "preview_cam1", "recording_cam2")
    """
    from ..media.pipeline_client import get_pipeline_client
    
    try:
        client = get_pipeline_client()
        result = await client.stop_pipeline(pipeline_id)
        
        if result.get("error"):
            raise HTTPException(status_code=400, detail=result["error"])
        
        return {"success": True, "message": f"Pipeline {pipeline_id} stopped"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error stopping pipeline {pipeline_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

