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
from .realtime.handlers import router as websocket_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    import logging
    from .media.pipeline_client import get_pipeline_client
    
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
    
    # Auto-start preview pipelines for enabled inputs
    try:
        client = get_pipeline_client()
        for input_id in settings.enabled_inputs:
            try:
                result = await client.start_preview(input_id)
                if result.get("error"):
                    logger.warning(f"Failed to start preview for {input_id}: {result['error']}")
                else:
                    logger.info(f"Started preview pipeline for {input_id}")
            except Exception as e:
                logger.warning(f"Error starting preview for {input_id}: {e}")
    except Exception as e:
        logger.warning(f"Could not auto-start previews: {e}")

    yield
    
    # Cleanup on shutdown


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

