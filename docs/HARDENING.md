# Hardening Review

> Stability improvements for production R58 deployments.

## Table of Contents

1. [Failure Mode Analysis](#1-failure-mode-analysis)
2. [Recommended Safeguards](#2-recommended-safeguards)
3. [Observability Plan](#3-observability-plan)
4. [Performance Checks](#4-performance-checks)
5. [Prioritized Code Changes](#5-prioritized-code-changes)

---

## 1. Failure Mode Analysis

### 1.1 MediaMTX Dies

| Aspect | Current Behavior | Risk Level | Impact |
|--------|-----------------|------------|--------|
| **Detection** | No active monitoring | High | Silent failure |
| **Preview Streams** | WHEP requests fail with connection error | High | No video preview in UI |
| **Recording** | Continues (uses GStreamer directly) | Low | None |
| **Recovery** | Manual restart required | High | Downtime |

**Failure Chain:**
```
MediaMTX crash → WHEP 502/Connection refused → Frontend shows black preview
                                             → No automatic retry
                                             → User confusion
```

### 1.2 GStreamer Pipeline Stalls

| Aspect | Current Behavior | Risk Level | Impact |
|--------|-----------------|------------|--------|
| **Detection** | None - no pipeline health checks | Critical | Data loss |
| **File Writing** | Stops but state shows "recording" | Critical | Orphaned partial files |
| **User Feedback** | Duration timer continues | High | False confidence |
| **Recovery** | Requires manual stop + restart | High | Lost recording |

**Failure Chain:**
```
Encoder stall → Bytes written stops → No alert
             → Duration timer continues (fake progress)
             → User thinks recording is fine
             → Stop reveals corrupted/truncated file
```

### 1.3 WebSocket Disconnects

| Aspect | Current Behavior | Risk Level | Impact |
|--------|-----------------|------------|--------|
| **Detection** | Client-side only | Medium | UI shows stale data |
| **Reconnection** | Exponential backoff (good) | Low | OK |
| **State Sync** | Requests sync but sync not implemented | High | State desync |
| **Multi-tab** | No coordination | Medium | Conflicting state |

**Failure Chain:**
```
Network flap → WS close event → Reconnect attempt (good)
                             → sync_request sent
                             → sync_response returns empty events (bug)
                             → UI may show wrong recording state
```

### 1.4 Disk Fills

| Aspect | Current Behavior | Risk Level | Impact |
|--------|-----------------|------------|--------|
| **Pre-check** | None on start_recording | Critical | Recording may fail mid-session |
| **Monitoring** | Health endpoint shows space | Low | Passive |
| **During Recording** | No active monitoring | Critical | File corruption |
| **Alerts** | None | High | Silent failure |

**Failure Chain:**
```
Disk fills → Write fails → GStreamer reports error (maybe)
                        → Pipeline state not updated
                        → API returns stale "recording" status
                        → File truncated or corrupted
```

### 1.5 CPU Spikes

| Aspect | Current Behavior | Risk Level | Impact |
|--------|-----------------|------------|--------|
| **Detection** | Metrics endpoint only | Medium | Passive |
| **Throttling** | None | Medium | All operations slow |
| **Prioritization** | OS default | Medium | Recording may drop frames |
| **Graceful Degradation** | None | High | Everything fails together |

**Failure Chain:**
```
CPU spike (other process) → Encoder falls behind → Frames dropped
                         → No user notification
                         → Poor quality recording
```

### 1.6 System Time Changes (NTP Jump, Timezone)

| Aspect | Current Behavior | Risk Level | Impact |
|--------|-----------------|------------|--------|
| **File Naming** | Uses datetime → Duplicate filenames possible | High | Overwrites |
| **Duration Calc** | Uses wall clock → Negative duration possible | Medium | UI confusion |
| **Session Timestamps** | Wall clock → Non-monotonic | Medium | Ordering bugs |
| **JWT Expiry** | Wall clock → Premature expiry or never expires | High | Auth issues |

**Failure Chain:**
```
NTP backward jump → File with same timestamp exists → Overwrite or error
                 → Duration becomes negative → UI shows 00:00:00
                 → JWT issued "in future" → Immediate expiry
```

### 1.7 Network Flaps

| Aspect | Current Behavior | Risk Level | Impact |
|--------|-----------------|------------|--------|
| **API Requests** | No retry logic | Medium | Failed operations |
| **WebSocket** | Reconnects (good) | Low | Temporary desync |
| **MediaMTX WHEP** | No retry, no fallback | High | Lost preview |
| **VDO.ninja Signaling** | Depends on VDO.ninja | Medium | Mixer disruption |

**Failure Chain:**
```
Network blip → API POST /start fails → Frontend shows error
            → User retries → May double-start (no idempotency)
            → WHEP connection dies → Preview black
            → VDO.ninja peer disconnects → Mixer loses sources
```

---

## 2. Recommended Safeguards

### 2.1 Watchdogs

#### Service Watchdog (systemd)

```ini
# services/r58-api.service
[Service]
WatchdogSec=30
WatchdogSignal=SIGTERM
Restart=always
RestartSec=5

# Requires app to call sd_notify("WATCHDOG=1") periodically
```

```python
# r58_api/watchdog.py
import asyncio
import os

async def watchdog_loop():
    """Notify systemd watchdog periodically"""
    sd_notify = os.environ.get("NOTIFY_SOCKET")
    if not sd_notify:
        return
    
    import socket
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    
    while True:
        sock.sendto(b"WATCHDOG=1", sd_notify)
        await asyncio.sleep(10)
```

#### Pipeline Health Watchdog

```python
# pipeline_manager/watchdog.py
class PipelineWatchdog:
    """Monitors GStreamer pipelines for stalls"""
    
    def __init__(self, state: PipelineState, stall_threshold_sec: int = 10):
        self.state = state
        self.threshold = stall_threshold_sec
        self.last_bytes: Dict[str, int] = {}
        self.last_update: Dict[str, float] = {}
    
    async def check_health(self) -> List[str]:
        """Returns list of stalled inputs"""
        stalled = []
        now = time.monotonic()
        
        if not self.state.active_recording:
            return stalled
        
        for input_id, bytes_written in self.state.active_recording.bytes_written.items():
            prev = self.last_bytes.get(input_id, 0)
            
            if bytes_written == prev:
                # No progress
                last_change = self.last_update.get(input_id, now)
                if now - last_change > self.threshold:
                    stalled.append(input_id)
            else:
                self.last_bytes[input_id] = bytes_written
                self.last_update[input_id] = now
        
        return stalled
```

#### MediaMTX Health Check

```python
# r58_api/observability/health.py
async def check_mediamtx_health() -> ServiceStatus:
    """Check if MediaMTX is responding"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.mediamtx_api_url}/v3/paths/list")
            if resp.status_code == 200:
                return ServiceStatus(name="mediamtx", status="healthy")
            return ServiceStatus(name="mediamtx", status="degraded", message=f"HTTP {resp.status_code}")
    except Exception as e:
        return ServiceStatus(name="mediamtx", status="unhealthy", message=str(e))
```

### 2.2 Retries with Backoff

#### IPC Client Retry

```python
# r58_api/media/pipeline_client.py
import asyncio
from typing import Optional

class PipelineClient:
    MAX_RETRIES = 3
    RETRY_DELAYS = [0.1, 0.5, 1.0]  # Exponential-ish backoff
    
    async def _send_command(self, cmd: dict, retries: int = MAX_RETRIES) -> dict:
        """Send command with retry logic"""
        last_error = None
        
        for attempt in range(retries):
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_unix_connection(self.socket_path),
                    timeout=5.0
                )
                
                writer.write(json.dumps(cmd).encode() + b"\n")
                await asyncio.wait_for(writer.drain(), timeout=5.0)
                
                response = await asyncio.wait_for(reader.readline(), timeout=10.0)
                writer.close()
                await writer.wait_closed()
                
                return json.loads(response)
                
            except asyncio.TimeoutError:
                last_error = "Timeout"
            except FileNotFoundError:
                return {"error": "Pipeline manager not running"}
            except Exception as e:
                last_error = str(e)
            
            if attempt < retries - 1:
                await asyncio.sleep(self.RETRY_DELAYS[attempt])
        
        return {"error": f"Failed after {retries} attempts: {last_error}"}
```

#### Frontend API Retry

```typescript
// lib/api.ts
export async function apiRequest<T>(
  url: string,
  options: RequestInit = {},
  retries = 3
): Promise<T> {
  const delays = [100, 500, 1000]
  let lastError: Error | null = null
  
  for (let i = 0; i < retries; i++) {
    try {
      const resp = await fetch(url, {
        ...options,
        signal: AbortSignal.timeout(10000),
      })
      
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`)
      }
      
      return await resp.json()
    } catch (e) {
      lastError = e as Error
      
      if (i < retries - 1) {
        await new Promise(r => setTimeout(r, delays[i]))
      }
    }
  }
  
  throw lastError
}
```

### 2.3 Idempotent Commands

#### Recording Start Idempotency

```python
# r58_api/control/sessions/router.py
@router.post("/start", response_model=StartRecordingResponse)
async def start_recording(
    request: StartRecordingRequest,
    idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key"),
):
    """Start recording with idempotency support"""
    client = get_pipeline_client()
    
    # Check current status first
    status = await client.get_recording_status()
    
    if status.get("recording"):
        current_session = status.get("session_id")
        
        # If same idempotency key or same session, return existing
        if idempotency_key and current_session == idempotency_key:
            return StartRecordingResponse(
                session_id=current_session,
                name=request.name,
                started_at=status.get("started_at"),
                inputs=list(status.get("bytes_written", {}).keys()),
                status="recording",
            )
        
        # Different session already running
        raise HTTPException(status_code=409, detail="Already recording different session")
    
    # Use idempotency key as session ID if provided
    session_id = idempotency_key or str(uuid.uuid4())
    
    result = await client.start_recording(
        session_id=session_id,
        inputs=request.inputs,
    )
    
    # ... rest of handler
```

#### Frontend Idempotency

```typescript
// stores/recorder.ts
async function startRecording(sessionName?: string) {
  // Generate idempotency key
  const idempotencyKey = crypto.randomUUID()
  
  // Store in session storage for retry
  sessionStorage.setItem('pending_recording_key', idempotencyKey)
  
  status.value = 'starting'
  
  try {
    const response = await fetch('/api/v1/recorder/start', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Idempotency-Key': idempotencyKey,
      },
      body: JSON.stringify({ name: sessionName }),
    })
    
    // Success - clear pending key
    sessionStorage.removeItem('pending_recording_key')
    
    // ... handle response
  } catch (error) {
    // Keep idempotency key for retry
    status.value = 'idle'
    throw error
  }
}
```

### 2.4 Authoritative State

#### State Reconciliation Pattern

```python
# pipeline_manager/state.py
class PipelineState:
    """
    AUTHORITATIVE state for recording operations.
    
    Design principles:
    1. This file is the source of truth, not GStreamer
    2. On startup, reconcile with actual filesystem
    3. All mutations must persist before returning
    """
    
    @classmethod
    def load_and_reconcile(cls) -> "PipelineState":
        """Load state and reconcile with reality"""
        state = cls.load()
        
        if state.active_recording:
            # Verify files actually exist and are being written
            all_files_exist = all(
                Path(path).exists() 
                for path in state.active_recording.inputs.values()
            )
            
            if not all_files_exist:
                # Files don't exist - orphaned state
                logging.warning("Orphaned recording state detected, cleaning up")
                state.active_recording = None
                state.current_mode = "idle"
                state.last_error = "Recovered from orphaned recording state"
                state.save()
        
        return state
```

### 2.5 Lock/Queue Strategy for Shared Resources

#### Recording Operation Lock

```python
# r58_api/control/sessions/router.py
import asyncio

# Module-level lock for recording operations
_recording_lock = asyncio.Lock()

@router.post("/start")
async def start_recording(request: StartRecordingRequest):
    """Start recording with operation lock"""
    async with _recording_lock:
        # Check status and start within lock
        client = get_pipeline_client()
        status = await client.get_recording_status()
        
        if status.get("recording"):
            raise HTTPException(status_code=409, detail="Already recording")
        
        result = await client.start_recording(...)
        return result

@router.post("/stop")
async def stop_recording():
    """Stop recording with operation lock"""
    async with _recording_lock:
        client = get_pipeline_client()
        status = await client.get_recording_status()
        
        if not status.get("recording"):
            raise HTTPException(status_code=400, detail="Not recording")
        
        result = await client.stop_recording()
        return result
```

#### Pipeline Command Queue

```python
# pipeline_manager/queue.py
import asyncio
from dataclasses import dataclass
from typing import Any, Dict

@dataclass
class PipelineCommand:
    cmd: str
    params: Dict[str, Any]
    response_future: asyncio.Future

class CommandQueue:
    """Serializes pipeline commands to prevent race conditions"""
    
    def __init__(self):
        self.queue: asyncio.Queue[PipelineCommand] = asyncio.Queue()
        self._running = False
    
    async def submit(self, cmd: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Submit command and wait for result"""
        future = asyncio.get_event_loop().create_future()
        await self.queue.put(PipelineCommand(cmd, params, future))
        return await future
    
    async def process_loop(self, handler):
        """Process commands sequentially"""
        self._running = True
        while self._running:
            command = await self.queue.get()
            try:
                result = await handler(command.cmd, command.params)
                command.response_future.set_result(result)
            except Exception as e:
                command.response_future.set_exception(e)
```

---

## 3. Observability Plan

### 3.1 Structured Logging

```python
# r58_api/logging.py
import logging
import json
import sys
from datetime import datetime
from typing import Any, Dict
import uuid

# Request-local trace ID
_trace_id: str = ""

def set_trace_id(trace_id: str):
    global _trace_id
    _trace_id = trace_id

def get_trace_id() -> str:
    return _trace_id or str(uuid.uuid4())[:8]

class StructuredFormatter(logging.Formatter):
    """JSON structured log formatter"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "trace_id": get_trace_id(),
        }
        
        # Add extra fields
        if hasattr(record, 'extra'):
            log_entry.update(record.extra)
        
        # Add exception info
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry)

def setup_logging(debug: bool = False):
    """Configure structured logging"""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter())
    
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(logging.DEBUG if debug else logging.INFO)
    
    # Reduce noise from libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
```

#### Middleware for Trace IDs

```python
# r58_api/middleware.py
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import uuid
from .logging import set_trace_id

class TraceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        trace_id = request.headers.get("X-Trace-ID", str(uuid.uuid4())[:8])
        set_trace_id(trace_id)
        
        response = await call_next(request)
        response.headers["X-Trace-ID"] = trace_id
        
        return response
```

### 3.2 Metrics Snapshot Endpoints

#### Enhanced Metrics

```python
# r58_api/observability/metrics.py
@router.get("/metrics/recording")
async def get_recording_metrics():
    """Recording-specific metrics"""
    client = get_pipeline_client()
    status = await client.get_recording_status()
    
    return {
        "recording": status.get("recording", False),
        "session_id": status.get("session_id"),
        "duration_ms": status.get("duration_ms", 0),
        "bytes_written": status.get("bytes_written", {}),
        "bytes_per_second": calculate_write_rate(status),
        "estimated_file_sizes": estimate_final_sizes(status),
    }

@router.get("/metrics/streams")
async def get_stream_metrics():
    """MediaMTX stream metrics"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.mediamtx_api_url}/v3/paths/list")
            paths = resp.json().get("items", [])
            
            return {
                "active_streams": len([p for p in paths if p.get("ready")]),
                "total_paths": len(paths),
                "paths": [
                    {
                        "name": p["name"],
                        "ready": p.get("ready", False),
                        "readers": p.get("readers", 0),
                    }
                    for p in paths
                ],
            }
    except Exception as e:
        return {"error": str(e), "active_streams": 0}
```

### 3.3 Log Rotation

```ini
# /etc/logrotate.d/r58
/var/log/r58/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 r58 r58
    postrotate
        systemctl reload r58-api 2>/dev/null || true
    endscript
}
```

#### Application-Level Rotation (if not using journald)

```python
# r58_api/logging.py
from logging.handlers import RotatingFileHandler

def setup_file_logging():
    handler = RotatingFileHandler(
        "/var/log/r58/api.log",
        maxBytes=50 * 1024 * 1024,  # 50MB
        backupCount=5,
    )
    handler.setFormatter(StructuredFormatter())
    logging.getLogger().addHandler(handler)
```

### 3.4 Alerting Rules

#### Health Check Alerter

```python
# r58_api/alerting.py
from dataclasses import dataclass
from typing import List, Optional
import asyncio

@dataclass
class Alert:
    level: str  # "warning", "critical"
    source: str
    message: str
    timestamp: datetime

class AlertManager:
    def __init__(self):
        self.alerts: List[Alert] = []
        self.max_alerts = 100
    
    async def check_and_alert(self):
        """Run all alert checks"""
        # Storage alert
        metrics = await get_metrics()
        for disk in metrics.disks:
            if disk.path == "/opt/r58/recordings":
                if disk.percent > 95:
                    self.add_alert("critical", "storage", f"Disk {disk.percent}% full")
                elif disk.percent > 80:
                    self.add_alert("warning", "storage", f"Disk {disk.percent}% full")
        
        # Pipeline stall alert
        recording_status = await get_recording_metrics()
        if recording_status.get("recording"):
            write_rate = recording_status.get("bytes_per_second", 0)
            if write_rate < 1000:  # Less than 1KB/s
                self.add_alert("critical", "pipeline", "Recording stall detected")
        
        # Memory alert
        if metrics.memory.used_percent > 90:
            self.add_alert("warning", "memory", f"Memory {metrics.memory.used_percent}% used")
    
    def add_alert(self, level: str, source: str, message: str):
        alert = Alert(level=level, source=source, message=message, timestamp=datetime.now())
        self.alerts.insert(0, alert)
        self.alerts = self.alerts[:self.max_alerts]
        
        # Log alert
        if level == "critical":
            logging.critical(f"[ALERT] {source}: {message}")
        else:
            logging.warning(f"[ALERT] {source}: {message}")
```

#### Alert Endpoint

```python
@router.get("/alerts")
async def get_active_alerts():
    """Get recent alerts"""
    return {
        "alerts": [
            {
                "level": a.level,
                "source": a.source,
                "message": a.message,
                "timestamp": a.timestamp.isoformat(),
            }
            for a in alert_manager.alerts[:20]
        ],
        "critical_count": len([a for a in alert_manager.alerts if a.level == "critical"]),
        "warning_count": len([a for a in alert_manager.alerts if a.level == "warning"]),
    }
```

---

## 4. Performance Checks

### 4.1 Latency Budgets

| Operation | Target | Acceptable | Action if Exceeded |
|-----------|--------|------------|-------------------|
| Preview load (WHEP) | < 200ms | < 500ms | Log warning, show loading state |
| API response (read) | < 50ms | < 200ms | Log warning |
| API response (write) | < 100ms | < 500ms | Log warning, show spinner |
| WebSocket event delivery | < 50ms | < 200ms | Buffer events |
| Recording start | < 1s | < 3s | Show progress indicator |
| Recording stop | < 2s | < 5s | Show finalizing state |

#### Latency Tracking Middleware

```python
# r58_api/middleware.py
import time

class LatencyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        
        response = await call_next(request)
        
        latency_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Response-Time-Ms"] = f"{latency_ms:.2f}"
        
        # Log slow requests
        if latency_ms > 200:
            logging.warning(f"Slow request: {request.method} {request.url.path} took {latency_ms:.0f}ms")
        
        return response
```

### 4.2 Resource Budgets Per Stream

| Resource | Per Stream | Max Total | Action if Exceeded |
|----------|------------|-----------|-------------------|
| CPU | 15% | 60% | Reduce quality/framerate |
| Memory | 200MB | 800MB | Stop oldest stream |
| Disk Write | 5 MB/s | 20 MB/s | Reduce bitrate |
| Network | 10 Mbps | 40 Mbps | Switch to lower quality |

#### Resource Governor

```python
# pipeline_manager/governor.py
class ResourceGovernor:
    """Monitors and enforces resource limits"""
    
    LIMITS = {
        "cpu_per_stream": 15.0,  # %
        "cpu_total": 60.0,
        "memory_per_stream_mb": 200,
        "memory_total_mb": 800,
        "disk_write_mbps": 20,
    }
    
    async def check_limits(self, stream_count: int) -> List[str]:
        """Check if within limits, return violations"""
        violations = []
        
        cpu = psutil.cpu_percent(interval=0.5)
        if cpu > self.LIMITS["cpu_total"]:
            violations.append(f"CPU {cpu}% exceeds limit")
        
        mem = psutil.virtual_memory()
        used_mb = (mem.total - mem.available) / (1024 ** 2)
        limit_mb = self.LIMITS["memory_total_mb"]
        if used_mb > limit_mb:
            violations.append(f"Memory {used_mb:.0f}MB exceeds {limit_mb}MB")
        
        return violations
    
    def should_degrade(self) -> bool:
        """Return True if should reduce quality"""
        cpu = psutil.cpu_percent(interval=0.1)
        return cpu > 70
```

### 4.3 Graceful Degradation Rules

| Trigger | Level 1 Action | Level 2 Action | Level 3 Action |
|---------|---------------|----------------|----------------|
| CPU > 70% | Reduce preview to 720p | Reduce to 15fps | Disable 2 previews |
| CPU > 85% | Pause non-essential tasks | Reduce recording bitrate | Alert only |
| Memory > 80% | Force GC | Stop HLS streaming | Alert + reduce quality |
| Memory > 95% | Emergency stop lowest priority | Stop previews | Keep recording only |
| Disk < 5GB | Warning alert | Stop new recordings | Emergency stop all |
| Disk < 1GB | Critical alert | Force stop recording | System protection |

```python
# r58_api/degradation.py
from enum import IntEnum

class DegradationLevel(IntEnum):
    NORMAL = 0
    WARN = 1
    DEGRADE = 2
    CRITICAL = 3

class DegradationPolicy:
    """Implements graceful degradation"""
    
    def __init__(self):
        self.current_level = DegradationLevel.NORMAL
    
    async def evaluate(self) -> DegradationLevel:
        """Evaluate current system state"""
        cpu = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory().percent
        disk = psutil.disk_usage("/opt/r58/recordings")
        disk_gb_free = disk.free / (1024 ** 3)
        
        level = DegradationLevel.NORMAL
        
        if cpu > 85 or mem > 95 or disk_gb_free < 1:
            level = DegradationLevel.CRITICAL
        elif cpu > 70 or mem > 80 or disk_gb_free < 5:
            level = DegradationLevel.DEGRADE
        elif cpu > 60 or mem > 70 or disk_gb_free < 10:
            level = DegradationLevel.WARN
        
        if level != self.current_level:
            await self.apply_degradation(level)
            self.current_level = level
        
        return level
    
    async def apply_degradation(self, level: DegradationLevel):
        """Apply degradation actions"""
        if level >= DegradationLevel.DEGRADE:
            # Reduce preview quality
            await self.set_preview_quality("720p")
        
        if level >= DegradationLevel.CRITICAL:
            # Protect recording at all costs
            await self.stop_all_previews()
            logging.critical("CRITICAL: Degradation active, previews disabled")
```

---

## 5. Prioritized Code Changes

### Priority 1: Critical (Data Loss Prevention)

#### 1.1 Add Recording Write Watchdog

**File:** `packages/backend/pipeline_manager/watchdog.py` (new)

**Change:** Create watchdog that monitors bytes_written and detects stalls

**Acceptance Criteria:**
- [ ] Detects when bytes_written unchanged for 10+ seconds
- [ ] Emits `recording.stall` event via WebSocket
- [ ] Auto-stops recording after 30s stall (configurable)
- [ ] Unit test covers stall detection

**Effort:** 2 hours

---

#### 1.2 Add Disk Space Pre-Check

**File:** `packages/backend/r58_api/control/sessions/router.py`

**Change:** Check disk space before allowing recording start

```python
MIN_DISK_GB = 2  # Minimum 2GB to start

@router.post("/start")
async def start_recording(request: StartRecordingRequest):
    # Pre-check disk space
    disk = shutil.disk_usage("/opt/r58/recordings")
    free_gb = disk.free / (1024 ** 3)
    
    if free_gb < MIN_DISK_GB:
        raise HTTPException(
            status_code=507,  # Insufficient Storage
            detail=f"Insufficient disk space: {free_gb:.1f}GB free, need {MIN_DISK_GB}GB"
        )
    
    # Continue with start...
```

**Acceptance Criteria:**
- [ ] Returns 507 when < 2GB free
- [ ] Error message shows available space
- [ ] Frontend shows appropriate error

**Effort:** 30 minutes

---

#### 1.3 Add IPC Timeout and Retry

**File:** `packages/backend/r58_api/media/pipeline_client.py`

**Change:** Add timeout and retry logic to IPC calls

**Acceptance Criteria:**
- [ ] Commands timeout after 10 seconds
- [ ] Automatic retry with backoff (3 attempts)
- [ ] Returns structured error on failure
- [ ] Unit test covers timeout scenario

**Effort:** 1 hour

---

### Priority 2: High (State Consistency)

#### 2.1 Implement WebSocket State Sync

**File:** `packages/backend/r58_api/realtime/handlers.py`

**Change:** Implement actual sync_response with current state

```python
async def handle_client_message(websocket, client_id, message):
    if message.get("type") == "sync_request":
        # Get current state
        client = get_pipeline_client()
        recording_status = await client.get_recording_status()
        
        await websocket.send_json({
            "type": "sync_response",
            "payload": {
                "recording": recording_status.get("recording", False),
                "session_id": recording_status.get("session_id"),
                "duration_ms": recording_status.get("duration_ms", 0),
                "inputs": list(recording_status.get("bytes_written", {}).keys()),
            }
        })
```

**Acceptance Criteria:**
- [ ] sync_response includes current recording state
- [ ] Frontend correctly restores state on reconnect
- [ ] Test verifies state sync after disconnect

**Effort:** 2 hours

---

#### 2.2 Add Recording Operation Lock

**File:** `packages/backend/r58_api/control/sessions/router.py`

**Change:** Add asyncio.Lock to prevent race conditions

**Acceptance Criteria:**
- [ ] Only one start/stop can execute at a time
- [ ] Second request waits or fails gracefully
- [ ] No deadlocks (timeout on lock acquisition)

**Effort:** 1 hour

---

#### 2.3 Add Idempotency Key Support

**File:** `packages/backend/r58_api/control/sessions/router.py`

**Change:** Accept X-Idempotency-Key header, return same response for same key

**Acceptance Criteria:**
- [ ] Same key returns same session_id
- [ ] Different key while recording returns 409
- [ ] Frontend sends idempotency key on start

**Effort:** 2 hours

---

### Priority 3: Medium (Observability)

#### 3.1 Add Structured Logging

**Files:** 
- `packages/backend/r58_api/logging.py` (new)
- `packages/backend/r58_api/main.py`

**Change:** JSON structured logs with trace IDs

**Acceptance Criteria:**
- [ ] All logs output as JSON
- [ ] X-Trace-ID header propagated
- [ ] Trace ID visible in log output
- [ ] Configurable via R58_LOG_FORMAT env var

**Effort:** 2 hours

---

#### 3.2 Add MediaMTX Health Check

**File:** `packages/backend/r58_api/observability/health.py`

**Change:** Actually check MediaMTX connectivity in detailed health

**Acceptance Criteria:**
- [ ] Pings MediaMTX API endpoint
- [ ] Returns "unhealthy" if MediaMTX down
- [ ] Includes MediaMTX version in response

**Effort:** 1 hour

---

#### 3.3 Add Alert Endpoint

**File:** `packages/backend/r58_api/observability/alerts.py` (new)

**Change:** Create /api/v1/alerts endpoint with recent alerts

**Acceptance Criteria:**
- [ ] Tracks last 100 alerts
- [ ] Includes critical/warning counts
- [ ] Background task generates alerts

**Effort:** 3 hours

---

### Priority 4: Low (Performance)

#### 4.1 Add Response Time Header

**File:** `packages/backend/r58_api/main.py`

**Change:** Add middleware for X-Response-Time-Ms header

**Acceptance Criteria:**
- [ ] All responses include header
- [ ] Slow requests (>200ms) logged

**Effort:** 30 minutes

---

#### 4.2 Add Degradation Policy

**File:** `packages/backend/r58_api/degradation.py` (new)

**Change:** Create system resource monitoring with degradation levels

**Acceptance Criteria:**
- [ ] Monitors CPU, memory, disk
- [ ] Defines 4 degradation levels
- [ ] Logs level changes
- [ ] Exposes current level via /api/v1/health

**Effort:** 4 hours

---

#### 4.3 Add Frontend API Retry

**File:** `packages/frontend/src/lib/api.ts` (new)

**Change:** Create fetch wrapper with retry logic

**Acceptance Criteria:**
- [ ] 3 retries with exponential backoff
- [ ] Timeout after 10 seconds
- [ ] Used by all API calls in stores

**Effort:** 1 hour

---

## Implementation Order

| Week | Tasks | Total Hours |
|------|-------|-------------|
| 1 | 1.1 (Watchdog), 1.2 (Disk check), 1.3 (IPC retry) | 3.5h |
| 2 | 2.1 (WS sync), 2.2 (Lock), 2.3 (Idempotency) | 5h |
| 3 | 3.1 (Logging), 3.2 (MediaMTX health), 3.3 (Alerts) | 6h |
| 4 | 4.1 (Response time), 4.2 (Degradation), 4.3 (API retry) | 5.5h |

**Total:** ~20 hours of development

---

## Quick Reference

### Failure Prevention Checklist

- [ ] Disk space checked before recording
- [ ] IPC calls have timeout and retry
- [ ] Recording writes monitored for stalls
- [ ] MediaMTX health verified
- [ ] WebSocket state synced on reconnect
- [ ] Operations protected by locks
- [ ] Idempotency keys prevent duplicate starts

### Monitoring Checklist

- [ ] Structured JSON logging enabled
- [ ] Trace IDs in all requests
- [ ] Alert endpoint available
- [ ] Metrics endpoint covers all services
- [ ] Log rotation configured
- [ ] Degradation level exposed

