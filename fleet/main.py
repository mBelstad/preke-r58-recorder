"""
R58 Fleet Management Server

Main FastAPI application for managing R58 device fleet.
"""
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api import auth, devices, commands, releases, heartbeats, bundles, users
from .config import settings
from .database import init_db, close_db

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    logger.info("Starting R58 Fleet Management Server...")
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    yield
    
    # Cleanup
    await close_db()
    logger.info("Fleet server shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""
    
    app = FastAPI(
        title="R58 Fleet Management",
        description="Device fleet management and remote control for R58 devices",
        version="1.0.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(auth.router, prefix="/api/v1", tags=["Authentication"])
    app.include_router(users.router, prefix="/api/v1", tags=["Users"])
    app.include_router(devices.router, prefix="/api/v1", tags=["Devices"])
    app.include_router(heartbeats.router, prefix="/api/v1", tags=["Heartbeats"])
    app.include_router(commands.router, prefix="/api/v1", tags=["Commands"])
    app.include_router(releases.router, prefix="/api/v1", tags=["Releases"])
    app.include_router(bundles.router, prefix="/api/v1", tags=["Support Bundles"])
    
    @app.get("/", tags=["Health"])
    async def root():
        return {
            "service": "R58 Fleet Management",
            "version": "1.0.0",
            "status": "running",
        }
    
    @app.get("/health", tags=["Health"])
    async def health():
        return {"status": "healthy"}
    
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.exception(f"Unhandled exception: {exc}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )
    
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "fleet.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )

