"""Metrics snapshot endpoint"""
from datetime import datetime
from typing import List

import psutil
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1", tags=["Metrics"])


class CPUMetrics(BaseModel):
    """CPU metrics"""
    percent: float
    count: int
    frequency_mhz: float


class MemoryMetrics(BaseModel):
    """Memory metrics"""
    total_gb: float
    available_gb: float
    used_percent: float


class DiskMetrics(BaseModel):
    """Disk metrics"""
    path: str
    total_gb: float
    used_gb: float
    free_gb: float
    percent: float


class NetworkMetrics(BaseModel):
    """Network metrics"""
    bytes_sent: int
    bytes_recv: int
    packets_sent: int
    packets_recv: int


class ProcessMetrics(BaseModel):
    """Process-specific metrics"""
    name: str
    pid: int
    cpu_percent: float
    memory_mb: float
    status: str


class MetricsSnapshot(BaseModel):
    """Complete metrics snapshot"""
    timestamp: datetime
    cpu: CPUMetrics
    memory: MemoryMetrics
    disks: List[DiskMetrics]
    network: NetworkMetrics
    processes: List[ProcessMetrics]


def get_cpu_metrics() -> CPUMetrics:
    """Get CPU metrics"""
    freq = psutil.cpu_freq()
    return CPUMetrics(
        percent=psutil.cpu_percent(interval=0.1),
        count=psutil.cpu_count(),
        frequency_mhz=freq.current if freq else 0,
    )


def get_memory_metrics() -> MemoryMetrics:
    """Get memory metrics"""
    mem = psutil.virtual_memory()
    return MemoryMetrics(
        total_gb=mem.total / (1024 ** 3),
        available_gb=mem.available / (1024 ** 3),
        used_percent=mem.percent,
    )


def get_disk_metrics() -> List[DiskMetrics]:
    """Get disk metrics for all mounted partitions"""
    disks = []
    for partition in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            disks.append(DiskMetrics(
                path=partition.mountpoint,
                total_gb=usage.total / (1024 ** 3),
                used_gb=usage.used / (1024 ** 3),
                free_gb=usage.free / (1024 ** 3),
                percent=usage.percent,
            ))
        except (PermissionError, OSError):
            continue
    return disks


def get_network_metrics() -> NetworkMetrics:
    """Get network metrics"""
    net = psutil.net_io_counters()
    return NetworkMetrics(
        bytes_sent=net.bytes_sent,
        bytes_recv=net.bytes_recv,
        packets_sent=net.packets_sent,
        packets_recv=net.packets_recv,
    )


def get_process_metrics() -> List[ProcessMetrics]:
    """Get R58-related process metrics"""
    r58_processes = []
    target_names = ["r58", "python", "mediamtx", "gst-launch", "uvicorn"]

    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'status']):
        try:
            name = proc.info['name'].lower()
            if any(target in name for target in target_names):
                r58_processes.append(ProcessMetrics(
                    name=proc.info['name'],
                    pid=proc.info['pid'],
                    cpu_percent=proc.info['cpu_percent'] or 0,
                    memory_mb=(proc.info['memory_info'].rss / (1024 ** 2)) if proc.info['memory_info'] else 0,
                    status=proc.info['status'],
                ))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return r58_processes


@router.get("/metrics", response_model=MetricsSnapshot)
async def get_metrics() -> MetricsSnapshot:
    """
    Get current system metrics snapshot.

    Includes CPU, memory, disk, network, and R58-related process metrics.
    """
    return MetricsSnapshot(
        timestamp=datetime.now(),
        cpu=get_cpu_metrics(),
        memory=get_memory_metrics(),
        disks=get_disk_metrics(),
        network=get_network_metrics(),
        processes=get_process_metrics(),
    )

