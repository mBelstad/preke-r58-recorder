"""R58 Control API - FastAPI Application Factory"""
import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .db.database import init_db
from .logging import setup_logging
from .middleware import TraceMiddleware, LatencyMiddleware, RequestLoggingMiddleware

# Import routers
from .control.devices.capabilities import router as capabilities_router
from .control.vdoninja import router as vdoninja_router
from .control.sessions.router import router as sessions_router
from .control.auth.router import router as auth_router
from .control.fleet.discovery import router as fleet_router
from .observability.health import router as health_router
from .observability.metrics import router as metrics_router
from .observability.support import router as support_router
from .observability.alerts import router as alerts_router
from .realtime.handlers import router as websocket_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
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
    
    yield
    
    # Cleanup on shutdown


def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""
    settings = get_settings()
    
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
    app.include_router(fleet_router)
    app.include_router(vdoninja_router)
    app.include_router(sessions_router)
    app.include_router(health_router)
    app.include_router(metrics_router)
    app.include_router(support_router)
    app.include_router(alerts_router)
    app.include_router(websocket_router)
    
    return app


# Application instance
app = create_app()


@app.get("/")
async def root():
    """Root endpoint with API info"""
    return {
        "name": "R58 API",
        "version": "2.0.0",
        "docs": "/docs",
        "openapi": "/openapi.json",
    }

