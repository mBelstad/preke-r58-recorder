"""Alert management for R58 system monitoring"""
import asyncio
import logging
import shutil
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Deque, List, Optional

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

from ..config import get_settings

router = APIRouter(prefix="/api/v1", tags=["Alerts"])
logger = logging.getLogger(__name__)


class AlertLevel(str, Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertSource(str, Enum):
    """Alert source categories"""
    STORAGE = "storage"
    PIPELINE = "pipeline"
    MEDIAMTX = "mediamtx"
    MEMORY = "memory"
    CPU = "cpu"
    NETWORK = "network"
    RECORDING = "recording"
    SYSTEM = "system"


@dataclass
class Alert:
    """Individual alert record"""
    id: str
    level: AlertLevel
    source: AlertSource
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    details: dict = field(default_factory=dict)


class AlertManager:
    """
    Manages system alerts and health monitoring.
    
    Features:
    - Tracks last 100 alerts
    - Deduplication (same source+message within 60s)
    - Auto-resolve for transient issues
    - Background health check loop
    """
    
    MAX_ALERTS = 100
    DEDUP_WINDOW_SECONDS = 60
    CHECK_INTERVAL_SECONDS = 30
    
    # Thresholds
    DISK_WARNING_PERCENT = 80
    DISK_CRITICAL_PERCENT = 95
    DISK_CRITICAL_GB = 2.0
    MEMORY_WARNING_PERCENT = 80
    MEMORY_CRITICAL_PERCENT = 95
    CPU_WARNING_PERCENT = 80
    CPU_CRITICAL_PERCENT = 95
    
    def __init__(self):
        self._alerts: Deque[Alert] = deque(maxlen=self.MAX_ALERTS)
        self._alert_counter = 0
        self._running = False
        self._check_task: Optional[asyncio.Task] = None
        self._last_alert_key: dict = {}  # For deduplication
    
    def add_alert(
        self,
        level: AlertLevel,
        source: AlertSource,
        message: str,
        details: Optional[dict] = None,
    ) -> Alert:
        """Add a new alert, with deduplication"""
        # Deduplication check
        key = f"{source.value}:{message}"
        now = datetime.now()
        
        if key in self._last_alert_key:
            last_time = self._last_alert_key[key]
            if (now - last_time).total_seconds() < self.DEDUP_WINDOW_SECONDS:
                # Skip duplicate
                return None
        
        self._last_alert_key[key] = now
        
        # Create alert
        self._alert_counter += 1
        alert = Alert(
            id=f"alert-{self._alert_counter:06d}",
            level=level,
            source=source,
            message=message,
            timestamp=now,
            details=details or {},
        )
        
        self._alerts.appendleft(alert)
        
        # Log alert
        if level == AlertLevel.CRITICAL:
            logger.critical(f"[ALERT] {source.value}: {message}", extra={"alert_id": alert.id})
        elif level == AlertLevel.WARNING:
            logger.warning(f"[ALERT] {source.value}: {message}", extra={"alert_id": alert.id})
        else:
            logger.info(f"[ALERT] {source.value}: {message}", extra={"alert_id": alert.id})
        
        return alert
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Mark an alert as resolved"""
        for alert in self._alerts:
            if alert.id == alert_id and not alert.resolved:
                alert.resolved = True
                alert.resolved_at = datetime.now()
                logger.info(f"[ALERT] Resolved: {alert.source.value} - {alert.message}")
                return True
        return False
    
    def get_alerts(
        self,
        limit: int = 20,
        level: Optional[AlertLevel] = None,
        source: Optional[AlertSource] = None,
        unresolved_only: bool = False,
    ) -> List[Alert]:
        """Get recent alerts with optional filtering"""
        alerts = list(self._alerts)
        
        if level:
            alerts = [a for a in alerts if a.level == level]
        
        if source:
            alerts = [a for a in alerts if a.source == source]
        
        if unresolved_only:
            alerts = [a for a in alerts if not a.resolved]
        
        return alerts[:limit]
    
    def get_counts(self) -> dict:
        """Get alert counts by level"""
        critical = sum(1 for a in self._alerts if a.level == AlertLevel.CRITICAL and not a.resolved)
        warning = sum(1 for a in self._alerts if a.level == AlertLevel.WARNING and not a.resolved)
        info = sum(1 for a in self._alerts if a.level == AlertLevel.INFO and not a.resolved)
        
        return {
            "critical": critical,
            "warning": warning,
            "info": info,
            "total_unresolved": critical + warning + info,
            "total": len(self._alerts),
        }
    
    async def start_background_checks(self):
        """Start background health check loop"""
        if self._running:
            return
        
        self._running = True
        self._check_task = asyncio.create_task(self._check_loop())
        logger.info("[AlertManager] Started background health checks")
    
    def stop_background_checks(self):
        """Stop background health check loop"""
        self._running = False
        if self._check_task:
            self._check_task.cancel()
        logger.info("[AlertManager] Stopped background health checks")
    
    async def _check_loop(self):
        """Background loop for health checks"""
        while self._running:
            try:
                await asyncio.sleep(self.CHECK_INTERVAL_SECONDS)
                await self.run_health_checks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[AlertManager] Health check error: {e}")
    
    async def run_health_checks(self):
        """Run all health checks and generate alerts"""
        await self._check_storage()
        await self._check_memory()
        await self._check_cpu()
        await self._check_pipeline()
    
    async def _check_storage(self):
        """Check disk storage"""
        try:
            # Check recordings directory
            path = "/opt/r58/recordings"
            try:
                usage = shutil.disk_usage(path)
            except FileNotFoundError:
                usage = shutil.disk_usage("/")
            
            percent = (usage.used / usage.total) * 100
            free_gb = usage.free / (1024 ** 3)
            
            if percent >= self.DISK_CRITICAL_PERCENT or free_gb < self.DISK_CRITICAL_GB:
                self.add_alert(
                    AlertLevel.CRITICAL,
                    AlertSource.STORAGE,
                    f"Disk critically full: {percent:.1f}% used ({free_gb:.1f}GB free)",
                    {"percent": percent, "free_gb": free_gb},
                )
            elif percent >= self.DISK_WARNING_PERCENT:
                self.add_alert(
                    AlertLevel.WARNING,
                    AlertSource.STORAGE,
                    f"Disk space low: {percent:.1f}% used ({free_gb:.1f}GB free)",
                    {"percent": percent, "free_gb": free_gb},
                )
        except Exception as e:
            logger.error(f"[AlertManager] Storage check failed: {e}")
    
    async def _check_memory(self):
        """Check memory usage"""
        try:
            import psutil
            mem = psutil.virtual_memory()
            
            if mem.percent >= self.MEMORY_CRITICAL_PERCENT:
                self.add_alert(
                    AlertLevel.CRITICAL,
                    AlertSource.MEMORY,
                    f"Memory critically high: {mem.percent:.1f}% used",
                    {"percent": mem.percent, "available_mb": mem.available / (1024**2)},
                )
            elif mem.percent >= self.MEMORY_WARNING_PERCENT:
                self.add_alert(
                    AlertLevel.WARNING,
                    AlertSource.MEMORY,
                    f"Memory usage high: {mem.percent:.1f}% used",
                    {"percent": mem.percent, "available_mb": mem.available / (1024**2)},
                )
        except ImportError:
            pass  # psutil not available
        except Exception as e:
            logger.error(f"[AlertManager] Memory check failed: {e}")
    
    async def _check_cpu(self):
        """Check CPU usage"""
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0.5)
            
            if cpu >= self.CPU_CRITICAL_PERCENT:
                self.add_alert(
                    AlertLevel.CRITICAL,
                    AlertSource.CPU,
                    f"CPU critically high: {cpu:.1f}%",
                    {"percent": cpu},
                )
            elif cpu >= self.CPU_WARNING_PERCENT:
                self.add_alert(
                    AlertLevel.WARNING,
                    AlertSource.CPU,
                    f"CPU usage high: {cpu:.1f}%",
                    {"percent": cpu},
                )
        except ImportError:
            pass  # psutil not available
        except Exception as e:
            logger.error(f"[AlertManager] CPU check failed: {e}")
    
    async def _check_pipeline(self):
        """Check pipeline manager health"""
        try:
            from ..media.pipeline_client import get_pipeline_client
            
            client = get_pipeline_client()
            
            # Check if pipeline is healthy
            if not client.is_healthy:
                self.add_alert(
                    AlertLevel.WARNING,
                    AlertSource.PIPELINE,
                    f"Pipeline manager connection unstable ({client._consecutive_failures} failures)",
                    {"consecutive_failures": client._consecutive_failures},
                )
        except Exception as e:
            logger.error(f"[AlertManager] Pipeline check failed: {e}")


# Singleton instance
_alert_manager: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    """Get or create alert manager singleton"""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager


# --- API Endpoints ---

class AlertResponse(BaseModel):
    """Alert response model"""
    id: str
    level: str
    source: str
    message: str
    timestamp: str
    resolved: bool
    resolved_at: Optional[str]
    details: dict


class AlertsListResponse(BaseModel):
    """Alerts list response"""
    alerts: List[AlertResponse]
    counts: dict


@router.get("/alerts", response_model=AlertsListResponse)
async def get_alerts(
    limit: int = 20,
    level: Optional[str] = None,
    source: Optional[str] = None,
    unresolved_only: bool = False,
):
    """
    Get recent alerts.
    
    Query parameters:
    - limit: Max alerts to return (default 20)
    - level: Filter by level (info, warning, critical)
    - source: Filter by source (storage, pipeline, etc.)
    - unresolved_only: Only show unresolved alerts
    """
    manager = get_alert_manager()
    
    alert_level = AlertLevel(level) if level else None
    alert_source = AlertSource(source) if source else None
    
    alerts = manager.get_alerts(
        limit=limit,
        level=alert_level,
        source=alert_source,
        unresolved_only=unresolved_only,
    )
    
    return AlertsListResponse(
        alerts=[
            AlertResponse(
                id=a.id,
                level=a.level.value,
                source=a.source.value,
                message=a.message,
                timestamp=a.timestamp.isoformat(),
                resolved=a.resolved,
                resolved_at=a.resolved_at.isoformat() if a.resolved_at else None,
                details=a.details,
            )
            for a in alerts
        ],
        counts=manager.get_counts(),
    )


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str):
    """Mark an alert as resolved"""
    manager = get_alert_manager()
    
    if manager.resolve_alert(alert_id):
        return {"status": "resolved", "alert_id": alert_id}
    
    return {"status": "not_found", "alert_id": alert_id}


@router.post("/alerts/check")
async def trigger_health_check(background_tasks: BackgroundTasks):
    """Manually trigger a health check"""
    manager = get_alert_manager()
    background_tasks.add_task(manager.run_health_checks)
    return {"status": "check_scheduled"}

