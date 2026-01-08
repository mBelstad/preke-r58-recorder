"""Graceful degradation policy for R58 system resource management"""
import asyncio
import logging
import shutil
from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum
from typing import Awaitable, Callable, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1", tags=["System"])
logger = logging.getLogger(__name__)


class DegradationLevel(IntEnum):
    """
    System degradation levels.

    Higher level = more degraded = more aggressive resource shedding.
    """
    NORMAL = 0      # All features enabled
    WARN = 1        # Warning state, monitoring closely
    DEGRADE = 2     # Some features disabled to preserve core function
    CRITICAL = 3    # Emergency mode, only essential functions


@dataclass
class ResourceThresholds:
    """Thresholds for each degradation level"""
    # CPU thresholds (percent)
    cpu_warn: float = 70.0
    cpu_degrade: float = 85.0
    cpu_critical: float = 95.0

    # Memory thresholds (percent)
    mem_warn: float = 70.0
    mem_degrade: float = 85.0
    mem_critical: float = 95.0

    # Disk thresholds (GB free)
    disk_warn_gb: float = 10.0
    disk_degrade_gb: float = 5.0
    disk_critical_gb: float = 1.0


class DegradationPolicy:
    """
    Monitors system resources and manages degradation levels.

    Features:
    - Real-time resource monitoring
    - Automatic level transitions
    - Configurable actions per level
    - Hysteresis to prevent oscillation
    """

    CHECK_INTERVAL_SECONDS = 5
    HYSTERESIS_SECONDS = 30  # Minimum time before downgrading

    def __init__(self, thresholds: Optional[ResourceThresholds] = None):
        self.thresholds = thresholds or ResourceThresholds()
        self.current_level = DegradationLevel.NORMAL
        self._last_level_change = datetime.now()
        self._running = False
        self._check_task: Optional[asyncio.Task] = None

        # Callbacks for level changes
        self._on_level_change: List[Callable[[DegradationLevel, DegradationLevel], Awaitable[None]]] = []

        # Current resource readings
        self._cpu_percent: float = 0.0
        self._mem_percent: float = 0.0
        self._disk_free_gb: float = 100.0

    @property
    def level_name(self) -> str:
        """Human-readable level name"""
        return self.current_level.name

    @property
    def should_reduce_quality(self) -> bool:
        """Whether to reduce preview/stream quality"""
        return self.current_level >= DegradationLevel.DEGRADE

    @property
    def should_disable_previews(self) -> bool:
        """Whether to disable non-essential previews"""
        return self.current_level >= DegradationLevel.CRITICAL

    @property
    def can_start_recording(self) -> bool:
        """Whether new recordings should be allowed"""
        # Only block in critical if disk is the issue
        if self.current_level >= DegradationLevel.CRITICAL:
            return self._disk_free_gb >= self.thresholds.disk_critical_gb
        return True

    def on_level_change(self, callback: Callable[[DegradationLevel, DegradationLevel], Awaitable[None]]):
        """Register a callback for level changes"""
        self._on_level_change.append(callback)

    async def start(self):
        """Start background monitoring"""
        if self._running:
            return

        self._running = True
        self._check_task = asyncio.create_task(self._monitor_loop())
        logger.info("[Degradation] Started resource monitoring")

    def stop(self):
        """Stop background monitoring"""
        self._running = False
        if self._check_task:
            self._check_task.cancel()
        logger.info("[Degradation] Stopped resource monitoring")

    async def _monitor_loop(self):
        """Background monitoring loop"""
        while self._running:
            try:
                await asyncio.sleep(self.CHECK_INTERVAL_SECONDS)
                await self.evaluate()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[Degradation] Monitor error: {e}")

    async def evaluate(self) -> DegradationLevel:
        """
        Evaluate current resource state and update degradation level.

        Returns the current degradation level.
        """
        # Collect resource metrics
        self._cpu_percent = await self._get_cpu_percent()
        self._mem_percent = self._get_mem_percent()
        self._disk_free_gb = self._get_disk_free_gb()

        # Determine target level based on worst resource
        target_level = self._calculate_level()

        # Apply hysteresis for downgrade (returning to normal)
        if target_level < self.current_level:
            time_at_level = (datetime.now() - self._last_level_change).total_seconds()
            if time_at_level < self.HYSTERESIS_SECONDS:
                # Not enough time at current level, don't downgrade yet
                return self.current_level

        # Update level if changed
        if target_level != self.current_level:
            await self._set_level(target_level)

        return self.current_level

    def _calculate_level(self) -> DegradationLevel:
        """Calculate target level based on current resources"""
        # Check each resource and take the worst level
        level = DegradationLevel.NORMAL

        # CPU check
        if self._cpu_percent >= self.thresholds.cpu_critical:
            level = max(level, DegradationLevel.CRITICAL)
        elif self._cpu_percent >= self.thresholds.cpu_degrade:
            level = max(level, DegradationLevel.DEGRADE)
        elif self._cpu_percent >= self.thresholds.cpu_warn:
            level = max(level, DegradationLevel.WARN)

        # Memory check
        if self._mem_percent >= self.thresholds.mem_critical:
            level = max(level, DegradationLevel.CRITICAL)
        elif self._mem_percent >= self.thresholds.mem_degrade:
            level = max(level, DegradationLevel.DEGRADE)
        elif self._mem_percent >= self.thresholds.mem_warn:
            level = max(level, DegradationLevel.WARN)

        # Disk check (most important for recording)
        if self._disk_free_gb <= self.thresholds.disk_critical_gb:
            level = max(level, DegradationLevel.CRITICAL)
        elif self._disk_free_gb <= self.thresholds.disk_degrade_gb:
            level = max(level, DegradationLevel.DEGRADE)
        elif self._disk_free_gb <= self.thresholds.disk_warn_gb:
            level = max(level, DegradationLevel.WARN)

        return level

    async def _set_level(self, new_level: DegradationLevel):
        """Update degradation level and notify listeners"""
        old_level = self.current_level
        self.current_level = new_level
        self._last_level_change = datetime.now()

        # Log the change
        if new_level > old_level:
            logger.warning(
                f"[Degradation] Level INCREASED: {old_level.name} -> {new_level.name} "
                f"(CPU: {self._cpu_percent:.0f}%, Mem: {self._mem_percent:.0f}%, "
                f"Disk: {self._disk_free_gb:.1f}GB)"
            )
        else:
            logger.info(
                f"[Degradation] Level decreased: {old_level.name} -> {new_level.name}"
            )

        # Notify callbacks
        for callback in self._on_level_change:
            try:
                await callback(old_level, new_level)
            except Exception as e:
                logger.error(f"[Degradation] Callback error: {e}")

    async def _get_cpu_percent(self) -> float:
        """Get CPU usage (async to avoid blocking)"""
        try:
            import psutil
            # Use non-blocking call
            return psutil.cpu_percent(interval=0.1)
        except ImportError:
            return 0.0
        except Exception:
            return 0.0

    def _get_mem_percent(self) -> float:
        """Get memory usage percent"""
        try:
            import psutil
            return psutil.virtual_memory().percent
        except ImportError:
            return 0.0
        except Exception:
            return 0.0

    def _get_disk_free_gb(self) -> float:
        """Get free disk space in GB.
        
        Checks storage in order of priority:
        1. /data - NVMe SSD mount point on R58 (where recordings are stored)
        2. /opt/r58/recordings - Legacy recordings path
        3. / - Root filesystem fallback
        """
        try:
            # Priority: NVMe SSD at /data, then legacy path, then root
            import os
            paths_to_check = ["/data", "/opt/r58/recordings", "/"]
            
            for path in paths_to_check:
                try:
                    if os.path.exists(path):
                        usage = shutil.disk_usage(path)
                        if usage.total > 0:
                            return usage.free / (1024 ** 3)
                except (FileNotFoundError, OSError):
                    continue
            
            return shutil.disk_usage("/").free / (1024 ** 3)
        except Exception:
            return 100.0  # Assume OK if can't check

    def get_status(self) -> dict:
        """Get current degradation status"""
        return {
            "level": self.current_level.value,
            "level_name": self.current_level.name,
            "resources": {
                "cpu_percent": round(self._cpu_percent, 1),
                "mem_percent": round(self._mem_percent, 1),
                "disk_free_gb": round(self._disk_free_gb, 2),
            },
            "flags": {
                "should_reduce_quality": self.should_reduce_quality,
                "should_disable_previews": self.should_disable_previews,
                "can_start_recording": self.can_start_recording,
            },
            "thresholds": {
                "cpu": {
                    "warn": self.thresholds.cpu_warn,
                    "degrade": self.thresholds.cpu_degrade,
                    "critical": self.thresholds.cpu_critical,
                },
                "mem": {
                    "warn": self.thresholds.mem_warn,
                    "degrade": self.thresholds.mem_degrade,
                    "critical": self.thresholds.mem_critical,
                },
                "disk_gb": {
                    "warn": self.thresholds.disk_warn_gb,
                    "degrade": self.thresholds.disk_degrade_gb,
                    "critical": self.thresholds.disk_critical_gb,
                },
            },
        }


# Singleton instance
_policy: Optional[DegradationPolicy] = None


def get_degradation_policy() -> DegradationPolicy:
    """Get or create degradation policy singleton"""
    global _policy
    if _policy is None:
        _policy = DegradationPolicy()
    return _policy


# --- API Endpoints ---

class DegradationStatus(BaseModel):
    """Degradation status response"""
    level: int
    level_name: str
    resources: dict
    flags: dict
    thresholds: dict


@router.get("/degradation", response_model=DegradationStatus)
async def get_degradation_status():
    """
    Get current system degradation status.

    Returns:
    - level: 0=NORMAL, 1=WARN, 2=DEGRADE, 3=CRITICAL
    - resources: Current CPU, memory, disk readings
    - flags: Boolean flags for feature decisions
    - thresholds: Configured thresholds for each level
    """
    policy = get_degradation_policy()

    # Trigger evaluation to get fresh readings
    await policy.evaluate()

    return DegradationStatus(**policy.get_status())


@router.post("/degradation/evaluate")
async def trigger_evaluation():
    """Manually trigger a degradation evaluation"""
    policy = get_degradation_policy()
    level = await policy.evaluate()
    return {
        "level": level.value,
        "level_name": level.name,
    }

