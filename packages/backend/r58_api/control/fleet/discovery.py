"""LAN Device Discovery - Find R58 devices on local network"""
import asyncio
import socket
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ...config import Settings, get_settings

# Note: This is for LOCAL network discovery (same subnet).
# For centralized fleet management, see the separate fleet/ server.
router = APIRouter(prefix="/api/v1/lan-devices", tags=["LAN Discovery"])


class DeviceInfo(BaseModel):
    """Discovered device information"""
    id: str
    name: str
    ip: str
    port: int
    status: str  # "online", "offline", "unknown"
    last_seen: datetime
    api_version: Optional[str] = None
    capabilities: Optional[dict] = None


class DeviceConnection(BaseModel):
    """Device connection request"""
    device_id: str
    address: str  # IP:port or hostname


class DeviceConnectionResponse(BaseModel):
    """Device connection response"""
    connected: bool
    device: Optional[DeviceInfo] = None
    error: Optional[str] = None


# In-memory device registry
_discovered_devices: dict[str, DeviceInfo] = {}


async def probe_device(ip: str, port: int = 8000, timeout: float = 2.0) -> Optional[DeviceInfo]:
    """Probe a potential R58 device"""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            # Try to get capabilities
            response = await client.get(f"http://{ip}:{port}/api/v1/capabilities")
            if response.status_code == 200:
                data = response.json()
                return DeviceInfo(
                    id=data.get("device_id", f"r58-{ip.replace('.', '-')}"),
                    name=data.get("device_name", "R58 Device"),
                    ip=ip,
                    port=port,
                    status="online",
                    last_seen=datetime.now(),
                    api_version=data.get("api_version"),
                    capabilities=data,
                )
    except Exception:
        pass

    return None


async def scan_network_range(
    base_ip: str,
    start: int,
    end: int,
    port: int = 8000
) -> List[DeviceInfo]:
    """Scan a range of IP addresses for R58 devices"""
    # Parse base IP (e.g., "192.168.1" from "192.168.1.0")
    parts = base_ip.rsplit('.', 1)
    if len(parts) != 2:
        parts = [base_ip, "0"]
    base = parts[0]

    # Create scan tasks
    tasks = []
    for i in range(start, end + 1):
        ip = f"{base}.{i}"
        tasks.append(probe_device(ip, port))

    # Run all probes concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Filter successful probes
    devices = []
    for result in results:
        if isinstance(result, DeviceInfo):
            devices.append(result)
            _discovered_devices[result.id] = result

    return devices


def get_local_ip() -> str:
    """Get the local IP address"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


@router.get("", response_model=List[DeviceInfo])
async def list_devices(
    settings: Settings = Depends(get_settings)
) -> List[DeviceInfo]:
    """
    List all discovered R58 devices.

    Returns cached device list from previous discovery scans.
    """
    # Always include self
    local_ip = get_local_ip()
    self_device = DeviceInfo(
        id=settings.device_id,
        name="This Device",
        ip=local_ip,
        port=settings.api_port,
        status="online",
        last_seen=datetime.now(),
        api_version="2.0.0",
    )

    devices = [self_device]
    devices.extend(_discovered_devices.values())

    return devices


@router.post("/scan", response_model=List[DeviceInfo])
async def scan_for_devices(
    settings: Settings = Depends(get_settings)
) -> List[DeviceInfo]:
    """
    Scan the local network for R58 devices.

    Scans the local subnet (e.g., 192.168.1.1-254) for devices
    with an R58 API running on port 8000.
    """
    local_ip = get_local_ip()
    base_ip = ".".join(local_ip.split(".")[:3])

    # Scan common range
    devices = await scan_network_range(base_ip, 1, 254, port=8000)

    return devices


@router.get("/{device_id}", response_model=DeviceInfo)
async def get_device(device_id: str) -> DeviceInfo:
    """Get details for a specific device"""
    if device_id in _discovered_devices:
        return _discovered_devices[device_id]

    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Device not found")


@router.post("/{device_id}/connect", response_model=DeviceConnectionResponse)
async def connect_to_device(device_id: str) -> DeviceConnectionResponse:
    """
    Establish connection to a remote device.

    Returns device information if connection is successful.
    """
    if device_id not in _discovered_devices:
        return DeviceConnectionResponse(
            connected=False,
            error="Device not found in discovery cache",
        )

    device = _discovered_devices[device_id]

    # Probe device to verify it's still online
    probed = await probe_device(device.ip, device.port)

    if probed:
        _discovered_devices[device_id] = probed
        return DeviceConnectionResponse(
            connected=True,
            device=probed,
        )

    # Mark as offline
    device.status = "offline"
    device.last_seen = datetime.now()

    return DeviceConnectionResponse(
        connected=False,
        device=device,
        error="Device is not responding",
    )

