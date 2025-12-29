"""R58 Control API - FastAPI Application Factory"""
import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .control.auth.router import router as auth_router

# Import routers
from .control.devices.capabilities import router as capabilities_router
from .control.lan_discovery.discovery import router as lan_discovery_router
from .control.sessions.router import router as sessions_router
from .control.vdoninja import router as vdoninja_router
from .db.database import init_db
from .degradation import router as degradation_router
from .logging import setup_logging
from .media.whep_proxy import router as whep_proxy_router
from .middleware import LatencyMiddleware, RequestLoggingMiddleware, TraceMiddleware
from .observability.alerts import router as alerts_router
from .observability.health import router as health_router
from .observability.metrics import router as metrics_router
from .observability.support import router as support_router
from .observability.system import router as system_router
from .realtime.handlers import router as websocket_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    import asyncio
    import logging
    from .media.pipeline_client import get_pipeline_client
    from .realtime.manager import get_connection_manager
    from .realtime.events import BaseEvent, EventType
    
    logger = logging.getLogger(__name__)
    settings = get_settings()
    
    # Setup logging first
    setup_logging(
        level="DEBUG" if settings.debug else "INFO",
        json_format=not settings.debug,  # JSON in production, text in dev
    )
    
    # Initialize database
    init_db()
    
    # Export OpenAPI schema for client generation
    openapi_path = Path(__file__).parent.parent.parent.parent / "openapi" / "openapi.json"
    openapi_path.parent.mkdir(parents=True, exist_ok=True)
    
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    openapi_path.write_text(json.dumps(schema, indent=2))
    
    # Note: Preview auto-start is handled by the pipeline manager
    # The pipeline manager has better signal detection and avoids starting
    # pipelines for devices without a valid signal

    # Background task to poll for pipeline events and broadcast them
    _event_poll_task = None
    _last_event_seq = 0
    
    async def poll_pipeline_events():
        """Poll pipeline manager for events and broadcast to WebSocket clients"""
        nonlocal _last_event_seq
        client = get_pipeline_client()
        manager = get_connection_manager()
        
        while True:
            try:
                await asyncio.sleep(1.0)  # Poll every second
                
                # Skip if no active WebSocket connections
                if not manager.active_connections:
                    continue
                
                # Poll for events from pipeline manager
                result = await client.poll_events(last_seq=_last_event_seq)
                
                if result.get("error"):
                    continue
                
                events = result.get("events", [])
                if events:
                    _last_event_seq = result.get("latest_seq", _last_event_seq)
                    
                    # Broadcast each event to WebSocket clients
                    for event_data in events:
                        event_type = event_data.get("type", "")
                        payload = event_data.get("payload", {})
                        
                        # Map pipeline event types to WebSocket event types
                        ws_event_type = None
                        if event_type == "pipeline.error":
                            ws_event_type = EventType.PIPELINE_ERROR
                        elif event_type == "preview.started":
                            ws_event_type = EventType.PREVIEW_STARTED
                        elif event_type == "preview.stopped":
                            ws_event_type = EventType.PREVIEW_STOPPED
                        elif event_type == "storage.warning":
                            ws_event_type = EventType.STORAGE_WARNING
                        elif event_type in ("recording.stall", "recording.emergency_stop"):
                            ws_event_type = EventType.ERROR
                            payload["error_type"] = event_type
                        elif event_type == "recording.recovered":
                            ws_event_type = EventType.HEALTH_CHANGED
                        elif event_type == "recording.progress":
                            ws_event_type = EventType.RECORDING_PROGRESS
                            logger.info(f"[API] Received recording.progress event: {payload}")
                        
                        if ws_event_type:
                            event = BaseEvent(
                                type=ws_event_type,
                                payload=payload,
                            )
                            await manager.broadcast(event)
                            if event_type == "recording.progress":
                                logger.info(f"[API] Broadcasted recording.progress to {len(manager.active_connections)} clients")
                            else:
                                logger.debug(f"Broadcasted pipeline event: {event_type}")
                
            except Exception as e:
                logger.debug(f"Event polling error (retrying): {e}")
                await asyncio.sleep(5.0)  # Back off on error
    
    # Start the event polling background task
    _event_poll_task = asyncio.create_task(poll_pipeline_events())
    logger.info("Started pipeline event polling background task")

    yield
    
    # Cleanup on shutdown
    if _event_poll_task:
        _event_poll_task.cancel()
        try:
            await _event_poll_task
        except asyncio.CancelledError:
            pass


def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""
    _settings = get_settings()
    
    app = FastAPI(
        title="R58 API",
        version="2.0.0",
        description="R58 Recorder/Mixer Control API",
        lifespan=lifespan,
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Permissive for local network
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add observability middleware (order matters - first added = outermost)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(LatencyMiddleware)
    app.add_middleware(TraceMiddleware)
    
    # Mount static files for CSS and assets
    static_path = Path(__file__).parent / "static"
    if static_path.exists():
        app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
    
    # Include routers
    app.include_router(auth_router)
    app.include_router(capabilities_router)
    app.include_router(lan_discovery_router)
    app.include_router(vdoninja_router)
    app.include_router(sessions_router)
    app.include_router(health_router)
    app.include_router(metrics_router)
    app.include_router(support_router)
    app.include_router(alerts_router)
    app.include_router(system_router)
    app.include_router(degradation_router)
    app.include_router(websocket_router)
    app.include_router(whep_proxy_router)
    
    return app


# Application instance
app = create_app()

# Frontend SPA serving
# Look for frontend dist in multiple locations
_frontend_dist_paths = [
    Path(__file__).parent.parent.parent / "frontend" / "dist",  # monorepo: packages/frontend/dist
    Path("/opt/r58-app/current/packages/frontend/dist"),  # device deployment
    Path("/opt/preke-r58-recorder/packages/frontend/dist"),  # alternative deployment
]

_frontend_dist: Path | None = None
for p in _frontend_dist_paths:
    if p.exists() and (p / "index.html").exists():
        _frontend_dist = p
        break


@app.get("/api")
async def api_info():
    """API info endpoint"""
    return {
        "name": "R58 API",
        "version": "2.0.0",
        "docs": "/docs",
        "openapi": "/openapi.json",
    }


# Serve frontend if dist exists
if _frontend_dist:
    # Mount assets separately for proper caching
    app.mount("/assets", StaticFiles(directory=str(_frontend_dist / "assets")), name="frontend_assets")
    
    @app.get("/", response_class=HTMLResponse)
    async def serve_frontend():
        """Serve frontend SPA"""
        return FileResponse(_frontend_dist / "index.html")
    
    @app.get("/sw.js")
    async def serve_sw():
        """Serve service worker"""
        return FileResponse(_frontend_dist / "sw.js", media_type="application/javascript")
    
    @app.get("/manifest.webmanifest")
    async def serve_manifest():
        """Serve PWA manifest"""
        return FileResponse(_frontend_dist / "manifest.webmanifest", media_type="application/manifest+json")
    
    @app.get("/registerSW.js")
    async def serve_register_sw():
        """Serve SW registration script"""
        return FileResponse(_frontend_dist / "registerSW.js", media_type="application/javascript")
    
    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        """SPA fallback - serve index.html for Vue Router history mode"""
        # Skip API routes
        if full_path.startswith("api/"):
            return {"detail": "Not found"}
        
        # Try to serve static file first
        file_path = _frontend_dist / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        
        # Fallback to index.html for SPA routing
        return FileResponse(_frontend_dist / "index.html")
else:
    @app.get("/")
    async def root():
        """Root endpoint with API info (no frontend)"""
        return {
            "name": "R58 API",
            "version": "2.0.0",
            "docs": "/docs",
            "openapi": "/openapi.json",
            "frontend": "not installed",
        }

