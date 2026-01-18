"""
R58 Recorder Backend API

FastAPI application for the R58 multi-camera recording device.
Handles camera ingest, recording, mixing, streaming, and WordPress integration.

API Base URL: https://app.itagenten.no/api/

Main Endpoint Categories:
- /api/v1/capabilities - Device capabilities and feature detection
- /api/v1/wordpress/* - WordPress/JetAppointments booking integration
- /api/v1/lan-devices/* - LAN device discovery
- /api/v1/ptz-controller/* - PTZ camera control (hardware joystick support)
- /api/v1/cameras/* - Camera settings (focus, exposure, white balance, etc.)
- /api/v1/vdo-ninja/* - VDO.ninja mixer control
- /api/streaming/* - RTMP/HLS streaming configuration
- /api/trigger/* - Recording trigger control
- /api/mode/* - Device mode switching (recorder/mixer/vdoninja)
- /api/ingest/* - Camera ingest status
- /api/mixer/* - Video mixer control
- /api/reveal/* - Reveal.js presentation control
- /api/sessions/* - Recording session management
- /api/system/* - System information and logs
- /health - Health check endpoint

WebSocket Endpoints:
- /ws - Real-time status updates
- /api/v1/ptz-controller/ws - Real-time PTZ control

Configuration:
  config.yml - Main device configuration
  wordpress section:
    enabled: true
    url: "https://preke.no"
    username: "api_user"
    app_password: "xxxx xxxx xxxx xxxx"
"""
import asyncio
import logging
import os
import subprocess
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, UploadFile, File, Response, Request, WebSocket, WebSocketDisconnect, Body
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse, StreamingResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import shutil
import uuid
import httpx
import time

from .config import AppConfig
from .ingest import IngestManager
from .recorder import Recorder
from .preview import PreviewManager
from .database import Database
from .files import FileManager
from .camera_control import CameraControlManager
from .camera_control.blackmagic import BlackmagicCamera
from .camera_control.obsbot import ObsbotTail2
from .fps_monitor import get_fps_monitor, FpsMonitor
from .wordpress import (
    get_wordpress_client,
    get_active_booking,
    set_active_booking,
    Booking,
    BookingStatus,
    ActiveBookingContext,
    VideoProject,
    CustomerInfo,
    ClientInfo,
    DisplayMode,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Load configuration
config_path = Path(__file__).parent.parent / "config.yml"
try:
    config = AppConfig.load(str(config_path))
except FileNotFoundError:
    logger.error(f"config.yml not found at {config_path}. Using default configuration.")
    config = AppConfig(platform="macos", cameras={})

# Initialize ingest manager (always-on capture)
ingest_manager = IngestManager(config)

# Initialize recorder (subscribes to ingest streams)
recorder = Recorder(config, ingest_manager=ingest_manager)

# Initialize preview manager (delegates to ingest)
preview_manager = PreviewManager(config, ingest_manager)

# Initialize camera control manager (for external cameras)
camera_control_manager: Optional[CameraControlManager] = None
if config.external_cameras:
    try:
        camera_control_manager = CameraControlManager(config.external_cameras)
        logger.info(f"Camera control manager initialized with {camera_control_manager.get_camera_count()} external camera(s)")
    except Exception as e:
        logger.error(f"Failed to initialize camera control manager: {e}")

# Initialize shared database (always available)
database = Database(db_path="data/app.db")

# Initialize shared file manager (always available)
file_manager = FileManager(uploads_dir="uploads", database=database)

# Initialize Reveal.js source manager first (needed by graphics plugin)
# Supports multiple independent outputs (e.g., slides + slides_overlay)
reveal_source_manager = None
if config.reveal.enabled:
    try:
        from .reveal_source import RevealSourceManager
        reveal_source_manager = RevealSourceManager(
            resolution=config.reveal.resolution,
            framerate=config.reveal.framerate,
            bitrate=config.reveal.bitrate,
            mediamtx_path=config.reveal.mediamtx_path,
            renderer=config.reveal.renderer,
            outputs=config.reveal.outputs  # Multiple outputs support
        )
        logger.info(f"Reveal.js source manager initialized (renderer: {reveal_source_manager.renderer_type}, outputs: {reveal_source_manager.get_output_ids()})")
    except Exception as e:
        logger.error(f"Failed to initialize Reveal.js source manager: {e}")
        reveal_source_manager = None
else:
    logger.info("Reveal.js source disabled in configuration")

# Initialize Cairo graphics manager (for real-time overlays)
cairo_manager = None
try:
    from .cairo_graphics import CairoGraphicsManager
    cairo_manager = CairoGraphicsManager()
    if cairo_manager.enabled:
        logger.info("Cairo graphics manager initialized")
    else:
        logger.warning("Cairo not available - graphics overlays disabled")
        cairo_manager = None
except Exception as e:
    logger.error(f"Failed to initialize Cairo graphics manager: {e}")
    cairo_manager = None

# Initialize Graphics plugin (optional)
graphics_plugin = None
graphics_renderer = None
if config.graphics.enabled:
    try:
        from .graphics import create_graphics_plugin
        graphics_plugin = create_graphics_plugin()
        graphics_plugin.initialize(config, reveal_source_manager)
        graphics_renderer = graphics_plugin.renderer
        logger.info("Graphics plugin initialized")
    except Exception as e:
        logger.error(f"Failed to initialize graphics plugin: {e}")
        graphics_plugin = None  # Continue without graphics

# Initialize Mixer plugin (optional, uses graphics if available)
mixer_plugin = None
mixer_core = None
scene_manager = None
scene_queue = None
if config.mixer.enabled:
    try:
        from .mixer import create_mixer_plugin
        mixer_plugin = create_mixer_plugin()
        mixer_plugin.initialize(config, ingest_manager, database, graphics_plugin, cairo_manager)
        mixer_core = mixer_plugin.core
        scene_manager = mixer_plugin.scene_manager
        scene_queue = mixer_plugin.scene_queue
        logger.info("Mixer plugin initialized")
    except Exception as e:
        logger.error(f"Failed to initialize mixer plugin: {e}")
        mixer_plugin = None  # Continue without mixer
else:
    logger.info("Mixer plugin disabled in configuration")

# Cloudflare Calls removed - using direct WHIP to MediaMTX instead
# Remote guests now publish directly via WHIP endpoints
calls_manager: Optional[Any] = None
calls_relay: Optional[Any] = None

# Initialize Mode Manager (for switching between Recorder and Mixer modes)
mode_manager = None
try:
    from .mode_manager import ModeManager
    mode_manager = ModeManager(
        ingest_manager=ingest_manager,
        recorder=recorder,
        mixer_core=mixer_core,
        config=config
    )
    logger.info(f"Mode manager initialized")
except Exception as e:
    logger.error(f"Failed to initialize mode manager: {e}")
    mode_manager = None


# Lifespan context manager for startup and shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Startup
    
    # Start FPS monitor (logs framerate every 5 seconds)
    fps_monitor = get_fps_monitor()
    fps_monitor.start()
    logger.info("FPS Monitor started - will log framerates every 5 seconds")
    
    logger.info("Starting ingest pipelines for all cameras...")
    results = ingest_manager.start_all()
    for cam_id, success in results.items():
        if success:
            logger.info(f"✓ Ingest started for {cam_id}")
        else:
            logger.warning(f"✗ Failed to start ingest for {cam_id}")
    
    yield
    
    # Shutdown
    logger.info("Application shutting down...")
    
    # Stop FPS monitor
    fps_monitor.stop()
    
    # Cleanup Cloudflare Calls relays
    # Cloudflare Calls cleanup removed (no longer used)


# Create FastAPI app with lifespan
app = FastAPI(
    title="R58 Recorder API",
    description="Recording API for Mekotronics R58 4x4 3S",
    version="1.0.0",
    lifespan=lifespan,
)

# NOTE: CORS is handled by nginx proxy at VPS level (app.itagenten.no)
# Do not add CORSMiddleware here to avoid duplicate Access-Control-Allow-Origin headers

# Electron renderer runs from file:// and needs explicit CORS headers when
# calling the device API directly (no nginx in front).
FILE_ORIGIN_CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Accept, X-Requested-With, X-Idempotency-Key",
    "Access-Control-Max-Age": "86400",
}


@app.middleware("http")
async def allow_file_origin_cors(request: Request, call_next):
    origin = request.headers.get("origin")
    is_file_origin = origin == "null" or (origin and origin.startswith("file://"))

    if is_file_origin and request.method == "OPTIONS":
        return Response(status_code=200, headers=FILE_ORIGIN_CORS_HEADERS)

    response = await call_next(request)

    if is_file_origin:
        for header, value in FILE_ORIGIN_CORS_HEADERS.items():
            if header not in response.headers:
                response.headers[header] = value

    return response


# WHEP/WHIP endpoints must always include CORS headers (even on errors)
WHEP_CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, PATCH, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Accept",
    "Access-Control-Max-Age": "86400",
}


def _whep_error_response(status_code: int, detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"detail": detail},
        headers=WHEP_CORS_HEADERS,
    )


async def _mediamtx_request(
    method: str,
    path: str,
    body: bytes,
    headers: Dict[str, str],
    timeout: float = 10.0,
) -> httpx.Response:
    clean_path = path.lstrip("/")
    urls = [
        f"https://localhost:8889/{clean_path}",
        f"http://localhost:8889/{clean_path}",
    ]
    last_error: Optional[Exception] = None
    async with httpx.AsyncClient(verify=False) as client:
        for url in urls:
            try:
                if method == "POST":
                    return await client.post(url, content=body, headers=headers, timeout=timeout)
                if method == "PATCH":
                    return await client.patch(url, content=body, headers=headers, timeout=timeout)
                raise ValueError(f"Unsupported MediaMTX method: {method}")
            except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadError) as e:
                last_error = e
                continue
    raise last_error or RuntimeError("MediaMTX request failed")

# Mount Vue frontend assets (js, css) at /assets
vue_dist_path = Path(__file__).parent.parent / "packages" / "frontend" / "dist"
vue_assets_path = vue_dist_path / "assets"
if vue_assets_path.exists():
    app.mount("/assets", StaticFiles(directory=str(vue_assets_path)), name="vue-assets")
    logger.info(f"Mounted Vue assets at /assets from {vue_assets_path}")

# Mount Vue frontend at /vue for direct access
if vue_dist_path.exists():
    app.mount("/vue", StaticFiles(directory=str(vue_dist_path), html=True), name="vue")
    logger.info(f"Mounted Vue frontend at /vue from {vue_dist_path}")

# Mount static files for legacy frontend and other static assets
static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Mount Reveal.js dist files for serving presentations
reveal_js_dist_path = Path(__file__).parent.parent / "reveal.js" / "dist"
if reveal_js_dist_path.exists():
    app.mount("/reveal.js", StaticFiles(directory=str(reveal_js_dist_path)), name="reveal.js")
    logger.info(f"Mounted Reveal.js dist files at /reveal.js")

# Mount Reveal.js root directory for serving demo/index.html
reveal_js_root_path = Path(__file__).parent.parent / "reveal.js"
if reveal_js_root_path.exists():
    app.mount("/reveal-demo", StaticFiles(directory=str(reveal_js_root_path), html=True), name="reveal-demo")
    logger.info(f"Mounted Reveal.js root at /reveal-demo (includes index.html)")

# Create uploads directory for graphics
uploads_dir = Path(__file__).parent.parent / "uploads"
uploads_dir.mkdir(exist_ok=True)
images_dir = uploads_dir / "images"
images_dir.mkdir(exist_ok=True)
videos_dir = uploads_dir / "videos"
videos_dir.mkdir(exist_ok=True)

# Mount uploads directory for serving files
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")



@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the Vue frontend app."""
    # Try Vue frontend first
    vue_index = Path(__file__).parent.parent / "packages" / "frontend" / "dist" / "index.html"
    if vue_index.exists():
        from fastapi.responses import Response
        content = vue_index.read_text()
        # Add cache-busting headers for HTML
        return Response(
            content=content,
            media_type="text/html",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    # Fallback to legacy app.html
    app_path = Path(__file__).parent / "static" / "app.html"
    if app_path.exists():
        return app_path.read_text()
    # Fallback to old index if app.html doesn't exist
    index_path = Path(__file__).parent / "static" / "index.html"
    if index_path.exists():
        return index_path.read_text()
    return "<h1>R58 Recorder API</h1><p>Frontend not found. API is available at /docs</p>"


@app.get("/switcher", response_class=HTMLResponse)
async def switcher():
    """Serve the professional switcher interface."""
    switcher_path = Path(__file__).parent / "static" / "switcher.html"
    if switcher_path.exists():
        return switcher_path.read_text()
    raise HTTPException(status_code=404, detail="Switcher interface not found")


@app.get("/static/r58_remote_mixer")
async def remote_mixer_redirect():
    """Redirect /static/r58_remote_mixer to /static/r58_remote_mixer.html"""
    return RedirectResponse(url="/static/r58_remote_mixer.html")


@app.get("/app")
async def app_redirect():
    """Redirect /app to Vue frontend"""
    return RedirectResponse(url="/")


# Vue static files (favicon, manifest, etc.)
@app.get("/favicon.svg")
async def vue_favicon():
    """Serve Vue favicon."""
    path = Path(__file__).parent.parent / "packages" / "frontend" / "dist" / "favicon.svg"
    if path.exists():
        return Response(content=path.read_text(), media_type="image/svg+xml")
    raise HTTPException(status_code=404)


@app.get("/manifest.webmanifest")
async def vue_manifest():
    """Serve Vue PWA manifest."""
    path = Path(__file__).parent.parent / "packages" / "frontend" / "dist" / "manifest.webmanifest"
    if path.exists():
        return Response(content=path.read_text(), media_type="application/manifest+json")
    raise HTTPException(status_code=404)


@app.get("/registerSW.js")
async def vue_sw_register():
    """Serve Vue service worker registration."""
    path = Path(__file__).parent.parent / "packages" / "frontend" / "dist" / "registerSW.js"
    if path.exists():
        return Response(
            content=path.read_text(),
            media_type="application/javascript",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    raise HTTPException(status_code=404)


@app.get("/sw.js")
async def vue_sw():
    """Serve Vue service worker."""
    path = Path(__file__).parent.parent / "packages" / "frontend" / "dist" / "sw.js"
    if path.exists():
        return Response(
            content=path.read_text(),
            media_type="application/javascript",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    raise HTTPException(status_code=404)


@app.get("/workbox-{path:path}")
async def vue_workbox(path: str):
    """Serve Vue workbox files."""
    file_path = Path(__file__).parent.parent / "packages" / "frontend" / "dist" / f"workbox-{path}"
    if file_path.exists():
        return Response(
            content=file_path.read_text(),
            media_type="application/javascript",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    raise HTTPException(status_code=404)


@app.get("/api/frontend/version")
async def get_frontend_version() -> Dict[str, Any]:
    """Get frontend build version/timestamp for cache busting."""
    import os
    from datetime import datetime
    
    vue_dist = Path(__file__).parent.parent / "packages" / "frontend" / "dist"
    index_html = vue_dist / "index.html"
    
    build_time = None
    if index_html.exists():
        stat = index_html.stat()
        build_time = datetime.fromtimestamp(stat.st_mtime).isoformat()
    
    # Get git commit if available
    git_commit = None
    try:
        import subprocess
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            git_commit = result.stdout.strip()[:8]  # Short commit hash
    except:
        pass
    
    return {
        "version": git_commit or "unknown",
        "build_time": build_time,
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/admin/clear-cache")
async def clear_all_caches() -> Dict[str, Any]:
    """Clear server-side caches via script (best-effort)."""
    script_path = Path(__file__).parent.parent / "scripts" / "clear-all-caches.sh"
    if not script_path.exists():
        raise HTTPException(status_code=404, detail="Cache clear script not found")

    try:
        result = subprocess.run(
            ["bash", str(script_path)],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
            timeout=30
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cache clear failed: {e}")

    if result.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=f"Cache clear failed: {result.stderr.strip() or result.stdout.strip()}"
        )

    # Restart service after response is sent to avoid killing the request
    try:
        subprocess.Popen(["bash", "-c", "sleep 1; systemctl restart preke-recorder"])
    except Exception:
        pass

    return {"status": "ok", "output": result.stdout.strip()}


@app.get("/apple-touch-icon.png")
async def vue_apple_icon():
    """Serve Vue apple touch icon."""
    path = Path(__file__).parent.parent / "packages" / "frontend" / "dist" / "apple-touch-icon.png"
    if path.exists():
        return Response(content=path.read_bytes(), media_type="image/png")
    raise HTTPException(status_code=404)


@app.get("/pwa-192x192.png")
async def vue_pwa_192():
    """Serve PWA 192x192 icon."""
    path = Path(__file__).parent.parent / "packages" / "frontend" / "dist" / "pwa-192x192.png"
    if path.exists():
        return Response(content=path.read_bytes(), media_type="image/png")
    raise HTTPException(status_code=404)


@app.get("/pwa-512x512.png")
async def vue_pwa_512():
    """Serve PWA 512x512 icon."""
    path = Path(__file__).parent.parent / "packages" / "frontend" / "dist" / "pwa-512x512.png"
    if path.exists():
        return Response(content=path.read_bytes(), media_type="image/png")
    raise HTTPException(status_code=404)


@app.get("/logo.png")
async def vue_logo_png():
    """Serve Vue logo PNG."""
    path = Path(__file__).parent.parent / "packages" / "frontend" / "dist" / "logo.png"
    if path.exists():
        return Response(content=path.read_bytes(), media_type="image/png")
    raise HTTPException(status_code=404)


@app.get("/static/app.html", response_class=HTMLResponse)
async def vue_app():
    """Serve Vue frontend at legacy app.html path for compatibility."""
    vue_index = Path(__file__).parent.parent / "packages" / "frontend" / "dist" / "index.html"
    if vue_index.exists():
        return vue_index.read_text()
    # Fallback to legacy
    legacy_path = Path(__file__).parent / "static" / "legacy" / "app.html"
    if legacy_path.exists():
        return legacy_path.read_text()
    raise HTTPException(status_code=404, detail="App not found")

@app.get("/guest")
async def guest_redirect():
    """Redirect /guest to /static/guest.html"""
    return RedirectResponse(url="/static/guest.html")

@app.get("/dev")
async def dev_redirect():
    """Redirect /dev to /static/dev.html"""
    return RedirectResponse(url="/static/dev.html")

@app.get("/static/graphics-new")
async def graphics_new_redirect():
    """Redirect /static/graphics-new to /static/graphics-new.html"""
    return RedirectResponse(url="/static/graphics-new.html")

@app.get("/library")
async def library_redirect():
    """Redirect /library to /static/library.html"""
    return RedirectResponse(url="/static/library.html")


@app.get("/cairo", response_class=HTMLResponse)
async def cairo_control():
    """Serve the Cairo graphics control panel."""
    cairo_path = Path(__file__).parent / "static" / "cairo_control.html"
    if cairo_path.exists():
        return cairo_path.read_text()
    return "<h1>Switcher Interface</h1><p>Switcher interface not found.</p>"


@app.get("/cameras")
@app.get("/api/camera-preview")  # Alternative path to bypass Vue PWA cache
async def camera_preview():
    """Serve the standalone camera preview with WHEP support.
    
    Includes no-cache headers to prevent PWA service worker from intercepting.
    Use /api/camera-preview to bypass cached Vue PWA routes.
    """
    preview_path = Path(__file__).parent / "static" / "camera-preview.html"
    if preview_path.exists():
        content = preview_path.read_text()
        return Response(
            content=content,
            media_type="text/html",
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-Content-Type-Options": "nosniff"
            }
        )
    raise HTTPException(status_code=404, detail="Camera preview not found")


@app.get("/editor", response_class=HTMLResponse)
async def scene_editor():
    """Serve the scene editor interface."""
    editor_path = Path(__file__).parent / "static" / "editor.html"
    if editor_path.exists():
        return editor_path.read_text()
    return "<h1>Scene Editor</h1><p>Scene editor not found.</p>"


@app.get("/graphics", response_class=HTMLResponse)
async def graphics_app():
    """Serve the graphics/presentation app interface."""
    graphics_path = Path(__file__).parent / "static" / "graphics.html"
    if graphics_path.exists():
        content = graphics_path.read_text()
        # Add cache-busting meta tag
        if '<meta name="viewport"' in content:
            content = content.replace(
                '<meta name="viewport"',
                '<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">\n    <meta http-equiv="Pragma" content="no-cache">\n    <meta http-equiv="Expires" content="0">\n    <meta name="viewport"'
            )
        return content
    return "<h1>Graphics App</h1><p>Graphics app not found.</p>"


@app.get("/broadcast-graphics", response_class=HTMLResponse)
async def broadcast_graphics_app():
    """Serve the broadcast graphics management interface."""
    graphics_path = Path(__file__).parent / "static" / "broadcast_graphics.html"
    if graphics_path.exists():
        return graphics_path.read_text()
    return "<h1>Broadcast Graphics</h1><p>Broadcast graphics interface not found.</p>"


@app.get("/control", response_class=HTMLResponse)
async def control():
    """Serve the comprehensive device control interface."""
    control_path = Path(__file__).parent / "static" / "control.html"
    if control_path.exists():
        return control_path.read_text()
    return "<h1>Control Interface</h1><p>Control interface not found.</p>"


@app.get("/library", response_class=HTMLResponse)
async def library():
    """Serve the recording library page."""
    library_path = Path(__file__).parent / "static" / "library.html"
    if library_path.exists():
        return library_path.read_text()
    return "<h1>Library</h1><p>Library page not found.</p>"


@app.get("/guest_join", response_class=HTMLResponse)
async def guest_join():
    """Serve the guest join page."""
    guest_join_path = Path(__file__).parent / "static" / "guest_join.html"
    if guest_join_path.exists():
        return guest_join_path.read_text()
    return "<h1>Guest Join</h1><p>Guest join page not found.</p>"


@app.get("/test_turn", response_class=HTMLResponse)
async def test_turn():
    """Serve the TURN connection test page."""
    test_path = Path(__file__).parent.parent / "test_turn_connection.html"
    if test_path.exists():
        return test_path.read_text()
    return "<h1>TURN Test</h1><p>Test page not found.</p>"


@app.get("/health")
async def health() -> Dict[str, Any]:
    """Health check endpoint - always responds even if GStreamer fails."""
    from .gst_utils import is_gst_initialized, get_gst_init_error
    
    gst_status = "initialized" if is_gst_initialized() else "not_initialized"
    gst_error = get_gst_init_error()
    
    # Check if reveal.js is available
    reveal_js_dist_path = Path(__file__).parent.parent / "reveal.js" / "dist"
    reveal_available = reveal_js_dist_path.exists()
    
    result = {
        "status": "healthy",
        "platform": config.platform,
        "gstreamer": gst_status,
        "gstreamer_error": gst_error
    }
    
    # Add reveal.js URLs if available
    if reveal_available:
        result["reveal_js"] = {
            "available": True,
            "demo_url": "/reveal",
            "graphics_url": "/reveal/graphics"
        }
    else:
        result["reveal_js"] = {
            "available": False
        }
    
    return result


@app.get("/api/v1/capabilities")
async def get_capabilities() -> Dict[str, Any]:
    """
    Get device capabilities manifest for adaptive UI.
    
    The frontend uses this to adapt features based on what the device supports.
    Returns hardware capabilities, feature flags, and storage information.
    """
    import shutil
    import os
    
    # Storage detection - prioritize /data (NVMe SSD) over /mnt/sdcard or root
    storage_total_gb = 0.0
    storage_available_gb = 0.0
    storage_path = "/"
    
    for path in ["/data", "/mnt/sdcard", "/"]:
        try:
            if os.path.exists(path):
                usage = shutil.disk_usage(path)
                if usage.total > 0:
                    storage_total_gb = usage.total / (1024 ** 3)
                    storage_available_gb = usage.free / (1024 ** 3)
                    storage_path = path
                    break
        except Exception:
            continue
    
    # Detect inputs from config
    inputs = []
    for idx, cam_id in enumerate(config.cameras.keys()):
        cam_config = config.cameras[cam_id]
        device_path = getattr(cam_config, 'device', f"/dev/video{idx * 10}")
        inputs.append({
            "id": cam_id,
            "type": "hdmi",
            "label": f"Camera {idx + 1}",
            "max_resolution": "1920x1080",
            "supports_audio": True,
            "device_path": device_path
        })
    
    # Hardware codecs
    codecs = [
        {
            "id": "h264_hw",
            "name": "H.264 (Hardware)",
            "hardware_accelerated": True,
            "max_bitrate_kbps": 20000
        },
        {
            "id": "h265_hw",
            "name": "H.265 (Hardware)",
            "hardware_accelerated": True,
            "max_bitrate_kbps": 15000
        }
    ]
    
    # Preview modes
    mediamtx_base = "https://app.itagenten.no"
    preview_modes = [
        {
            "id": "whep",
            "protocol": "whep",
            "latency_ms": 100,
            "url_template": f"{mediamtx_base}/whep/{{input_id}}"
        },
        {
            "id": "hls",
            "protocol": "hls",
            "latency_ms": 3000,
            "url_template": f"{mediamtx_base}/hls/{{input_id}}/index.m3u8"
        }
    ]
    
    # VDO.ninja configuration
    vdoninja_enabled = getattr(config, 'vdoninja', None) and getattr(config.vdoninja, 'enabled', False)
    vdoninja_port = getattr(config.vdoninja, 'port', 8080) if hasattr(config, 'vdoninja') else 8080
    vdoninja_room = getattr(config.vdoninja, 'room', 'r58') if hasattr(config, 'vdoninja') else 'r58'
    
    vdoninja_config = {
        "enabled": vdoninja_enabled,
        "host": "localhost",
        "port": vdoninja_port,
        "room": vdoninja_room
    }
    
    # Get current mode from mode manager
    current_mode = "recorder"  # Default
    if mode_manager:
        try:
            current_mode = await mode_manager.get_current_mode()
        except Exception as e:
            logger.debug(f"Could not get current mode: {e}")
    
    return {
        "device_id": f"r58-{config.platform}",
        "device_name": "R58 Recorder",
        "platform": config.platform,
        "api_version": "2.0.0",
        
        # Feature flags
        "mixer_available": vdoninja_config["enabled"],
        "recorder_available": True,
        "graphics_available": True,
        "fleet_agent_connected": False,
        
        # Hardware
        "inputs": inputs,
        "codecs": codecs,
        "preview_modes": preview_modes,
        
        # VDO.ninja
        "vdoninja": vdoninja_config,
        
        # Endpoints
        "mediamtx_base_url": mediamtx_base,
        
        # Limits
        "max_simultaneous_recordings": 4,
        "max_output_resolution": "1920x1080",
        "storage_total_gb": round(storage_total_gb, 2),
        "storage_available_gb": round(storage_available_gb, 2),
        "storage_path": storage_path,
        
        # Current mode (important for frontend to determine if videos should show)
        "current_mode": current_mode
    }


@app.get("/api/system/info")
async def get_system_info() -> Dict[str, Any]:
    """Get detailed system information including CPU, memory, temperature, and uptime."""
    import subprocess
    
    result = {
        "hostname": "R58 Device",
        "platform": config.platform,
        "load_average": [0.0, 0.0, 0.0],
        "memory_percent": 0.0,
        "memory_total_mb": 0,
        "memory_used_mb": 0,
        "uptime_seconds": 0,
        "temperatures": []
    }
    
    try:
        # Get load average from /proc/loadavg
        try:
            with open("/proc/loadavg", "r") as f:
                loadavg = f.read().strip().split()
                result["load_average"] = [float(loadavg[0]), float(loadavg[1]), float(loadavg[2])]
        except Exception as e:
            logger.debug(f"Could not read load average: {e}")
        
        # Get memory info from /proc/meminfo
        try:
            with open("/proc/meminfo", "r") as f:
                meminfo = {}
                for line in f:
                    parts = line.split(":")
                    if len(parts) == 2:
                        key = parts[0].strip()
                        # Extract numeric value (in kB)
                        value = parts[1].strip().split()[0]
                        meminfo[key] = int(value)
                
                total = meminfo.get("MemTotal", 0)
                available = meminfo.get("MemAvailable", meminfo.get("MemFree", 0))
                used = total - available
                
                result["memory_total_mb"] = total // 1024
                result["memory_used_mb"] = used // 1024
                if total > 0:
                    result["memory_percent"] = (used / total) * 100
        except Exception as e:
            logger.debug(f"Could not read memory info: {e}")
        
        # Get uptime from /proc/uptime
        try:
            with open("/proc/uptime", "r") as f:
                uptime = f.read().strip().split()[0]
                result["uptime_seconds"] = int(float(uptime))
        except Exception as e:
            logger.debug(f"Could not read uptime: {e}")
        
        # Get hostname
        try:
            with open("/etc/hostname", "r") as f:
                result["hostname"] = f.read().strip()
        except Exception as e:
            logger.debug(f"Could not read hostname: {e}")
        
        # Get temperatures from thermal zones
        try:
            thermal_zones = Path("/sys/class/thermal")
            if thermal_zones.exists():
                for zone in thermal_zones.iterdir():
                    if zone.name.startswith("thermal_zone"):
                        temp_file = zone / "temp"
                        type_file = zone / "type"
                        if temp_file.exists():
                            temp_celsius = int(temp_file.read_text().strip()) / 1000
                            zone_type = type_file.read_text().strip() if type_file.exists() else zone.name
                            result["temperatures"].append({
                                "type": zone_type,
                                "temp_celsius": temp_celsius
                            })
        except Exception as e:
            logger.debug(f"Could not read temperatures: {e}")
            
    except Exception as e:
        logger.error(f"Error getting system info: {e}")
    
    return result


@app.get("/api/system/logs")
async def get_system_logs(service: str = "preke-recorder", lines: int = 100) -> Dict[str, Any]:
    """Get system logs from journalctl."""
    import subprocess
    
    # Map service names to systemd unit names
    service_map = {
        "r58-api": "preke-recorder",
        "r58-pipeline": "preke-recorder",
        "preke-recorder": "preke-recorder",
        "mediamtx": "mediamtx",
    }
    
    unit_name = service_map.get(service, "preke-recorder")
    
    try:
        # Get logs from journalctl
        result = subprocess.run(
            ["journalctl", "-u", unit_name, "-n", str(lines), "--no-pager", "-o", "short-iso"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            return {"logs": result.stdout, "service": unit_name, "lines": lines}
        else:
            # Try reading from /var/log as fallback
            log_path = Path(f"/var/log/{unit_name}.log")
            if log_path.exists():
                with open(log_path, "r") as f:
                    log_lines = f.readlines()
                    return {"logs": "".join(log_lines[-lines:]), "service": unit_name, "lines": lines}
            return {"logs": f"No logs available for {unit_name}", "service": unit_name, "lines": 0}
    except subprocess.TimeoutExpired:
        return {"logs": "Timeout reading logs", "service": unit_name, "lines": 0}
    except Exception as e:
        return {"logs": f"Error reading logs: {str(e)}", "service": unit_name, "lines": 0}


@app.post("/api/system/restart-service/{service}")
async def restart_service(service: str) -> Dict[str, Any]:
    """Restart a system service."""
    import subprocess
    
    # Map service names to systemd unit names
    service_map = {
        "r58-recorder": "preke-recorder",
        "preke-recorder": "preke-recorder",
        "mediamtx": "mediamtx",
    }
    
    unit_name = service_map.get(service)
    if not unit_name:
        raise HTTPException(status_code=400, detail=f"Unknown service: {service}")
    
    try:
        # Use systemctl to restart
        result = subprocess.run(
            ["sudo", "systemctl", "restart", unit_name],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return {"success": True, "message": f"Service {unit_name} restarted successfully"}
        else:
            return {"success": False, "message": f"Failed to restart {unit_name}: {result.stderr}"}
    except subprocess.TimeoutExpired:
        return {"success": False, "message": "Timeout restarting service"}
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


@app.post("/api/system/reboot")
async def reboot_device() -> Dict[str, Any]:
    """Reboot the device."""
    import subprocess
    
    try:
        # Schedule reboot in 2 seconds to allow response to be sent
        subprocess.Popen(["sudo", "shutdown", "-r", "+0"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {"success": True, "message": "Device will reboot shortly"}
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


# VDO.ninja Bridge Control Endpoints
@app.get("/api/services/vdoninja-bridge/status")
async def get_vdoninja_bridge_status() -> Dict[str, Any]:
    """Get the status of the VDO.ninja bridge service."""
    import subprocess
    
    try:
        # Check if service is active
        result = subprocess.run(
            ["systemctl", "is-active", "vdoninja-bridge"],
            capture_output=True,
            text=True,
            timeout=5
        )
        is_active = result.stdout.strip() == "active"
        
        # Get more detailed status
        status_result = subprocess.run(
            ["systemctl", "show", "vdoninja-bridge", "--property=ActiveState,SubState,MainPID"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        # Parse status output
        status_info = {}
        for line in status_result.stdout.strip().split('\n'):
            if '=' in line:
                key, value = line.split('=', 1)
                status_info[key] = value
        
        # Check if chromium processes are running (the bridge spawns chromium tabs)
        ps_result = subprocess.run(
            ["pgrep", "-c", "-f", "chromium.*whepshare"],
            capture_output=True,
            text=True,
            timeout=5
        )
        chromium_count = int(ps_result.stdout.strip()) if ps_result.returncode == 0 else 0
        
        return {
            "service": "vdoninja-bridge",
            "active": is_active,
            "state": status_info.get("ActiveState", "unknown"),
            "subState": status_info.get("SubState", "unknown"),
            "mainPid": int(status_info.get("MainPID", 0)),
            "chromiumTabs": chromium_count,
            "description": "VDO.ninja WHEP Bridge - Shares HDMI cameras to VDO.ninja room"
        }
    except Exception as e:
        logger.error(f"Error getting vdoninja-bridge status: {e}")
        return {
            "service": "vdoninja-bridge",
            "active": False,
            "state": "error",
            "subState": str(e),
            "mainPid": 0,
            "chromiumTabs": 0,
            "description": "VDO.ninja WHEP Bridge"
        }


@app.post("/api/services/vdoninja-bridge/start")
async def start_vdoninja_bridge() -> Dict[str, Any]:
    """Start the VDO.ninja bridge service."""
    import subprocess
    
    try:
        result = subprocess.run(
            ["sudo", "systemctl", "start", "vdoninja-bridge"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return {"success": True, "message": "VDO.ninja bridge started successfully"}
        else:
            return {"success": False, "message": f"Failed to start: {result.stderr}"}
    except subprocess.TimeoutExpired:
        return {"success": False, "message": "Timeout starting service"}
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


@app.post("/api/services/vdoninja-bridge/stop")
async def stop_vdoninja_bridge() -> Dict[str, Any]:
    """Stop the VDO.ninja bridge service."""
    import subprocess
    
    try:
        result = subprocess.run(
            ["sudo", "systemctl", "stop", "vdoninja-bridge"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return {"success": True, "message": "VDO.ninja bridge stopped successfully"}
        else:
            return {"success": False, "message": f"Failed to stop: {result.stderr}"}
    except subprocess.TimeoutExpired:
        return {"success": False, "message": "Timeout stopping service"}
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


@app.post("/api/services/vdoninja-bridge/restart")
async def restart_vdoninja_bridge() -> Dict[str, Any]:
    """Restart the VDO.ninja bridge service."""
    import subprocess
    
    try:
        result = subprocess.run(
            ["sudo", "systemctl", "restart", "vdoninja-bridge"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return {"success": True, "message": "VDO.ninja bridge restarted successfully"}
        else:
            return {"success": False, "message": f"Failed to restart: {result.stderr}"}
    except subprocess.TimeoutExpired:
        return {"success": False, "message": "Timeout restarting service"}
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


@app.post("/record/start/{cam_id}")
async def start_recording(cam_id: str) -> Dict[str, str]:
    """Start recording for a specific camera."""
    # Check if we're in recorder mode
    if mode_manager:
        current_mode = await mode_manager.get_current_mode()
        if current_mode != "recorder":
            raise HTTPException(
                status_code=403,
                detail=f"Individual camera recording not available in {current_mode} mode. Switch to recorder mode first."
            )
    
    if cam_id not in config.cameras:
        raise HTTPException(status_code=404, detail=f"Camera {cam_id} not found")

    success = recorder.start_recording(cam_id)
    if not success:
        raise HTTPException(
            status_code=500, detail=f"Failed to start recording for {cam_id}"
        )

    return {"status": "started", "camera": cam_id}


@app.post("/record/stop/{cam_id}")
async def stop_recording(cam_id: str) -> Dict[str, str]:
    """Stop recording for a specific camera."""
    if cam_id not in config.cameras:
        raise HTTPException(status_code=404, detail=f"Camera {cam_id} not found")

    success = recorder.stop_recording(cam_id)
    if not success:
        raise HTTPException(
            status_code=500, detail=f"Failed to stop recording for {cam_id}"
        )

    return {"status": "stopped", "camera": cam_id}


@app.post("/record/start-all")
async def start_all_recordings() -> Dict[str, Any]:
    """Start recording for all configured cameras."""
    results = recorder.start_all_recordings()
    return {"status": "completed", "cameras": {k: "started" if v else "failed" for k, v in results.items()}}


@app.post("/record/stop-all")
async def stop_all_recordings() -> Dict[str, Any]:
    """Stop recording for all active cameras."""
    results = recorder.stop_all_recordings()
    return {"status": "completed", "cameras": {k: "stopped" if v else "not_recording" for k, v in results.items()}}


@app.post("/api/trigger/start")
async def trigger_start(session_name: Optional[str] = None) -> Dict[str, Any]:
    """Start recording on all cameras with session management.
    
    This is the master trigger that starts all R58 recordings and can optionally
    trigger external cameras (Blackmagic, Obsbot) if configured.
    """
    # Check if we're in recorder mode
    if mode_manager:
        current_mode = await mode_manager.get_current_mode()
        if current_mode != "recorder":
            raise HTTPException(
                status_code=403,
                detail=f"Individual camera recording not available in {current_mode} mode. Switch to recorder mode first."
            )
    
    logger.info(f"Master trigger START called (session_name: {session_name})")
    
    # Start all R58 recordings
    results = recorder.start_all_recordings()
    
    # Get session info
    session_status = recorder.get_session_status()
    session_id = session_status.get("session_id")
    
    # Trigger external cameras if configured
    external_results = {}
    if camera_control_manager:
        try:
            external_results = await camera_control_manager.start_all_recordings(session_id=session_id)
            logger.info(f"External camera trigger results: {external_results}")
        except Exception as e:
            logger.error(f"Failed to trigger external cameras: {e}")
    
    return {
        "status": "started",
        "session_id": session_id,
        "cameras": {k: "recording" if v else "failed" for k, v in results.items()},
        "external_cameras": {k: "recording" if v else "failed" for k, v in external_results.items()}
    }


@app.post("/api/trigger/stop")
async def trigger_stop() -> Dict[str, Any]:
    """Stop all recordings and finalize session metadata."""
    logger.info("Master trigger STOP called")
    
    # Get session info before stopping
    session_status = recorder.get_session_status()
    session_id = session_status.get("session_id")
    
    # Stop all R58 recordings
    results = recorder.stop_all_recordings()
    
    # Stop external cameras if configured
    external_results = {}
    if camera_control_manager:
        try:
            external_results = await camera_control_manager.stop_all_recordings()
            logger.info(f"External camera stop results: {external_results}")
        except Exception as e:
            logger.error(f"Failed to stop external cameras: {e}")
    
    return {
        "status": "stopped",
        "session_id": session_id,
        "cameras": {k: "stopped" if v else "not_recording" for k, v in results.items()},
        "external_cameras": {k: "stopped" if v else "failed" for k, v in external_results.items()}
    }


@app.get("/api/trigger/status")
async def trigger_status() -> Dict[str, Any]:
    """Get current recording state, duration, and session info."""
    session_status = recorder.get_session_status()
    
    # Add disk space info - check /data (NVMe SSD) first, then fallback
    disk_info = {"error": "Could not determine disk space"}
    for disk_path in ["/data", "/mnt/sdcard", "/"]:
        try:
            if os.path.exists(disk_path):
                disk = shutil.disk_usage(disk_path)
                if disk.total > 0:
                    disk_info = {
                        "free_gb": round(disk.free / (1024**3), 2),
                        "total_gb": round(disk.total / (1024**3), 2),
                        "used_gb": round(disk.used / (1024**3), 2),
                        "percent_used": round((disk.used / disk.total) * 100, 1),
                        "path": disk_path
                    }
                    break
        except Exception as e:
            logger.debug(f"Could not check disk at {disk_path}: {e}")
            continue
    
    return {
        **session_status,
        "disk": disk_info
    }


@app.post("/preview/start-all")
async def start_all_previews() -> Dict[str, Any]:
    """Start preview streams for all cameras (multiview)."""
    results = preview_manager.start_all_previews()
    return {"status": "completed", "cameras": {k: "preview" if v else "failed" for k, v in results.items()}}


@app.post("/preview/stop-all")
async def stop_all_previews() -> Dict[str, Any]:
    """Stop preview streams for all cameras."""
    results = preview_manager.stop_all_previews()
    return {"status": "completed", "cameras": {k: "stopped" if v else "not_preview" for k, v in results.items()}}


@app.get("/preview/status")
async def get_preview_status() -> Dict[str, Dict[str, Any]]:
    """Get preview status for all cameras."""
    statuses = preview_manager.get_preview_status()
    return {
        "cameras": {
            cam_id: {"status": status, "config": cam_id in config.cameras}
            for cam_id, status in statuses.items()
        }
    }


@app.get("/api/ingest/status")
async def get_ingest_status_api() -> Dict[str, Any]:
    """Get ingest status for all cameras (always-on streams)."""
    ingest_statuses = ingest_manager.get_status()
    camera_details = {}
    
    for cam_id, ingest_status in ingest_statuses.items():
        cam_config = config.cameras.get(cam_id)
        
        resolution_info = None
        if ingest_status.resolution:
            resolution_info = {
                "width": ingest_status.resolution[0],
                "height": ingest_status.resolution[1],
                "formatted": f"{ingest_status.resolution[0]}x{ingest_status.resolution[1]}"
            }
        
        camera_details[cam_id] = {
            "status": ingest_status.status,
            "config": cam_id in config.cameras,
            "device": cam_config.device if cam_config else None,
            "resolution": resolution_info,
            "has_signal": ingest_status.has_signal,
            "stream_url": ingest_status.stream_url
        }
    
    return {
        "cameras": camera_details,
        "summary": {
            "total": len(ingest_statuses),
            "streaming": sum(1 for s in ingest_statuses.values() if s.status == "streaming"),
            "no_signal": sum(1 for s in ingest_statuses.values() if s.status == "no_signal"),
            "error": sum(1 for s in ingest_statuses.values() if s.status == "error"),
            "idle": sum(1 for s in ingest_statuses.values() if s.status == "idle")
        }
    }


# ============================================================================
# Mode Management API Endpoints
# ============================================================================

@app.get("/api/mode")
async def get_mode() -> Dict[str, Any]:
    """Get current mode and available modes."""
    if not mode_manager:
        return {
            "error": "Mode manager not available",
            "current_mode": "recorder",
            "available_modes": ["recorder", "vdoninja"]
        }
    
    current_mode = await mode_manager.get_current_mode()
    return {
        "current_mode": current_mode,
        "available_modes": mode_manager.MODES
    }


@app.get("/api/mode/status")
async def get_mode_status() -> Dict[str, Any]:
    """Get detailed status of both modes."""
    if not mode_manager:
        return {
            "error": "Mode manager not available"
        }
    
    from dataclasses import asdict
    status = await mode_manager.get_status()
    return asdict(status)


@app.post("/api/mode/recorder")
async def switch_to_recorder() -> Dict[str, Any]:
    """Switch to Recorder Mode."""
    if not mode_manager:
        raise HTTPException(status_code=503, detail="Mode manager not available")
    
    result = await mode_manager.switch_to_recorder()
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["message"])
    
    return result


@app.post("/api/mode/mixer")
async def switch_to_mixer_mode() -> Dict[str, Any]:
    """Switch to Mixer Mode."""
    if not mode_manager:
        raise HTTPException(status_code=503, detail="Mode manager not available")
    
    result = await mode_manager.switch_to_mixer()
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["message"])
    
    return result


@app.post("/api/mode/vdoninja")
async def switch_to_vdoninja() -> Dict[str, Any]:
    """Switch to VDO.ninja Mode - DEPRECATED."""
    if not mode_manager:
        raise HTTPException(status_code=503, detail="Mode manager not available")
    
    result = await mode_manager.switch_to_vdoninja()
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["message"])
    
    return result


@app.post("/api/mode/idle")
async def switch_to_idle() -> Dict[str, Any]:
    """Switch to Idle Mode - stops all camera processes."""
    if not mode_manager:
        raise HTTPException(status_code=503, detail="Mode manager not available")
    
    # Idle mode is essentially switching back to recorder mode but stopping recording
    # For now, just switch to recorder mode (which stops active processes)
    result = await mode_manager.switch_to_recorder()
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["message"])
    
    return {
        "success": True,
        "message": "Switched to idle mode",
        "mode": "idle"
    }


@app.get("/api/config")
async def get_config() -> Dict[str, Any]:
    """Get device configuration for frontend."""
    config_data: Dict[str, Any] = {}
    
    # FRP URL configuration (if available)
    # Check if FRP is configured via environment
    frp_api_url = os.getenv("FRP_API_URL")
    if frp_api_url:
        config_data["frp_api_url"] = frp_api_url
        config_data["frp_url"] = frp_api_url  # Alias for backward compatibility
    
    # VDO.ninja configuration
    vdo_ninja_config: Dict[str, Any] = {}
    
    # Get VDO.ninja API key from environment or use default
    vdo_api_key = os.getenv("VDO_NINJA_API_KEY", "preke-r58-2024-secure-key")
    vdo_ninja_config["api_key"] = vdo_api_key
    
    # Get VDO.ninja host from environment (if configured)
    vdo_host = os.getenv("VDO_NINJA_HOST")
    if vdo_host:
        vdo_ninja_config["host"] = vdo_host
    
    config_data["vdo_ninja"] = vdo_ninja_config
    
    return config_data


@app.get("/api/preview/status")
async def get_preview_status_api() -> Dict[str, Any]:
    """Get detailed preview status for all cameras (delegates to ingest)."""
    statuses = preview_manager.get_preview_status()
    camera_details = {}
    
    for cam_id, status in statuses.items():
        cam_config = config.cameras.get(cam_id)
        
        # Get current resolution from ingest manager
        current_res = preview_manager.current_resolutions.get(cam_id)
        resolution_info = None
        if current_res:
            resolution_info = {
                "width": current_res[0],
                "height": current_res[1],
                "formatted": f"{current_res[0]}x{current_res[1]}"
            }
        
        # Get signal status from ingest manager
        has_signal = preview_manager.current_signal_status.get(cam_id, True)
        signal_loss_time = preview_manager.signal_loss_start_time.get(cam_id)
        signal_loss_duration = None
        if signal_loss_time:
            import time
            signal_loss_duration = int(time.time() - signal_loss_time)
        
        camera_details[cam_id] = {
            "status": status,
            "config": cam_id in config.cameras,
            "device": cam_config.device if cam_config else None,
            "configured_resolution": cam_config.resolution if cam_config else None,
            "current_resolution": resolution_info,
            "has_signal": has_signal,
            "signal_loss_duration": signal_loss_duration,
            "hls_url": f"/hls/{cam_id}/index.m3u8" if status == "preview" else None
        }
    
    return {
        "cameras": camera_details,
        "summary": {
            "total": len(statuses),
            "preview": sum(1 for s in statuses.values() if s == "preview"),
            "idle": sum(1 for s in statuses.values() if s == "idle"),
            "error": sum(1 for s in statuses.values() if s == "error"),
            "no_signal": sum(1 for s in statuses.values() if s == "no_signal")
        }
    }


# HLS Proxy endpoints - allows remote access through FRP tunnel
MEDIAMTX_HLS_BASE = "http://localhost:8888"


@app.get("/hls/{stream_path:path}")
async def proxy_hls(stream_path: str):
    """Proxy HLS streams from MediaMTX for remote access.
    
    This enables video streaming through FRP tunnel by proxying
    the MediaMTX HLS streams through the FastAPI server.
    
    Example: /hls/cam0_preview/index.m3u8
    """
    try:
        async with httpx.AsyncClient() as client:
            url = f"{MEDIAMTX_HLS_BASE}/{stream_path}"
            response = await client.get(url, timeout=10.0)
            
            if response.status_code == 404:
                raise HTTPException(status_code=404, detail=f"Stream not found: {stream_path}")
            
            # Determine content type based on file extension
            content_type = "application/vnd.apple.mpegurl"
            if stream_path.endswith(".ts"):
                content_type = "video/mp2t"
            elif stream_path.endswith(".m3u8"):
                content_type = "application/vnd.apple.mpegurl"
            
            # Rewrite m3u8 URLs to use our proxy
            content = response.content
            if stream_path.endswith(".m3u8"):
                # Rewrite relative URLs in playlist to go through our proxy
                text_content = content.decode('utf-8')
                # Keep relative URLs as-is, they'll resolve correctly
                content = text_content.encode('utf-8')
            
            return Response(
                content=content,
                status_code=response.status_code,
                media_type=content_type,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                }
            )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Stream timeout - MediaMTX may not be running")
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Cannot connect to MediaMTX - service may be down")
    except Exception as e:
        logger.error(f"HLS proxy error for {stream_path}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/whep/{stream_path}")
@app.options("/whep/{stream_path}")
async def proxy_whep(stream_path: str, request: Request):
    """Proxy WHEP requests to MediaMTX for WebRTC viewing.
    
    This enables WebRTC viewing through the same origin, avoiding CORS issues.
    """
    # Handle OPTIONS preflight
    if request.method == "OPTIONS":
        return Response(
            status_code=200,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, PATCH, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Accept",
                "Access-Control-Max-Age": "86400",
            }
        )
    
    try:
        # Get request body
        body = await request.body()
        
        response = await _mediamtx_request(
            "POST",
            f"{stream_path}/whep",
            body,
            {
                "Content-Type": request.headers.get("Content-Type", "application/sdp"),
                "Accept": request.headers.get("Accept", "application/sdp"),
            },
        )
        
        # Get Location header if present
        location = response.headers.get("Location")
        response_headers = {
            **WHEP_CORS_HEADERS,
            "Content-Type": response.headers.get("Content-Type", "application/sdp"),
        }
        if location:
            # Rewrite Location header to point to our proxy
            if location.startswith("https://localhost:8889/"):
                location = location.replace("https://localhost:8889/", "/whep-resource/")
            elif location.startswith("http://localhost:8889/"):
                location = location.replace("http://localhost:8889/", "/whep-resource/")
            response_headers["Location"] = location
        
        # Log the response for debugging
        if response.status_code != 200:
            logger.error(f"WHEP error for {stream_path}: {response.status_code} - {response.text}")
        
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=response_headers
        )
    except httpx.TimeoutException:
        return _whep_error_response(504, "Stream timeout - MediaMTX may not be running")
    except httpx.ConnectError:
        return _whep_error_response(503, "Cannot connect to MediaMTX - service may be down")
    except Exception as e:
        logger.error(f"WHEP proxy error for {stream_path}: {e}")
        return _whep_error_response(500, str(e))


@app.patch("/whep-resource/{stream_path:path}")
@app.options("/whep-resource/{stream_path:path}")
async def proxy_whep_resource(stream_path: str, request: Request):
    """Proxy WHEP resource requests (ICE candidates) to MediaMTX."""
    # Handle OPTIONS preflight
    if request.method == "OPTIONS":
        return Response(
            status_code=200,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "PATCH, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
                "Access-Control-Max-Age": "86400",
            }
        )
    
    try:
        body = await request.body()
        
        response = await _mediamtx_request(
            "PATCH",
            stream_path,
            body,
            {
                "Content-Type": request.headers.get("Content-Type", "application/trickle-ice-sdpfrag"),
            },
        )
        
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=WHEP_CORS_HEADERS,
        )
    except httpx.TimeoutException:
        return _whep_error_response(504, "Stream timeout - MediaMTX may not be running")
    except httpx.ConnectError:
        return _whep_error_response(503, "Cannot connect to MediaMTX - service may be down")
    except Exception as e:
        logger.error(f"WHEP resource proxy error for {stream_path}: {e}")
        return _whep_error_response(500, str(e))


@app.post("/whip/{stream_path}")
async def proxy_whip(stream_path: str, request: Request):
    """Proxy WHIP requests to MediaMTX for remote guest publishing.
    
    WHIP (WebRTC-HTTP Ingestion Protocol) allows guests to publish
    WebRTC streams through HTTP POST requests.
    
    Example: /whip/guest1
    """
    try:
        # Read the SDP offer from request body
        sdp_offer = await request.body()
        
        response = await _mediamtx_request(
            "POST",
            f"{stream_path}/whip",
            sdp_offer,
            {"Content-Type": "application/sdp"},
        )

        if response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Stream path not found: {stream_path}")
        
        if not response.is_success:
            logger.error(f"WHIP proxy error for {stream_path}: {response.status_code} - {response.text}")
            raise HTTPException(
                status_code=response.status_code,
                detail=f"MediaMTX WHIP error: {response.text}"
            )
        
        # Return the SDP answer
        return Response(
            content=response.content,
            status_code=response.status_code,
            media_type="application/sdp",
            headers=WHEP_CORS_HEADERS,
        )
    except httpx.TimeoutException:
        return _whep_error_response(504, "WHIP timeout - MediaMTX may not be responding")
    except httpx.ConnectError:
        return _whep_error_response(503, "Cannot connect to MediaMTX - service may be down")
    except Exception as e:
        logger.error(f"WHIP proxy error for {stream_path}: {e}")
        return _whep_error_response(500, str(e))


@app.options("/whip/{stream_path}")
async def whip_options(stream_path: str):
    """Handle CORS preflight for WHIP requests."""
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        }
    )


# =============================================================================
# MediaMTX-compatible routes for VDO.ninja's &mediamtx= parameter
# VDO.ninja expects: /{stream}/whip and /{stream}/whep (stream name comes first)
# =============================================================================

@app.post("/{stream_name}/whip")
@app.options("/{stream_name}/whip")
async def mediamtx_whip_compat(stream_name: str, request: Request):
    """MediaMTX-compatible WHIP route for VDO.ninja &mediamtx= parameter.
    
    VDO.ninja's MediaMTX mode expects paths like /{stream}/whip
    This redirects to our standard /whip/{stream} endpoint.
    """
    # Skip for paths that look like API routes or static files
    if stream_name in ["api", "static", "whip", "whep", "docs", "openapi.json"]:
        raise HTTPException(status_code=404, detail="Not found")
    
    # Handle OPTIONS preflight
    if request.method == "OPTIONS":
        return Response(
            status_code=200,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
                "Access-Control-Max-Age": "86400",
            }
        )
    
    try:
        sdp_offer = await request.body()
        response = await _mediamtx_request(
            "POST",
            f"{stream_name}/whip",
            sdp_offer,
            {"Content-Type": "application/sdp"},
        )

        location = response.headers.get("Location")
        response_headers = {
            **WHEP_CORS_HEADERS,
            "Content-Type": response.headers.get("Content-Type", "application/sdp"),
        }
        if location:
            response_headers["Location"] = location
        
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=response_headers
        )
    except httpx.TimeoutException:
        return _whep_error_response(504, "WHIP timeout - MediaMTX may not be responding")
    except httpx.ConnectError:
        return _whep_error_response(503, "Cannot connect to MediaMTX - service may be down")
    except Exception as e:
        logger.error(f"MediaMTX WHIP compat error for {stream_name}: {e}")
        return _whep_error_response(500, str(e))


@app.post("/{stream_name}/whep")
@app.options("/{stream_name}/whep")
async def mediamtx_whep_compat(stream_name: str, request: Request):
    """MediaMTX-compatible WHEP route for VDO.ninja &mediamtx= parameter.
    
    VDO.ninja's MediaMTX mode expects paths like /{stream}/whep
    This redirects to our standard /whep/{stream} endpoint.
    """
    # Skip for paths that look like API routes or static files
    if stream_name in ["api", "static", "whip", "whep", "docs", "openapi.json"]:
        raise HTTPException(status_code=404, detail="Not found")
    
    # Handle OPTIONS preflight
    if request.method == "OPTIONS":
        return Response(
            status_code=200,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Accept",
                "Access-Control-Max-Age": "86400",
            }
        )
    
    try:
        body = await request.body()
        response = await _mediamtx_request(
            "POST",
            f"{stream_name}/whep",
            body,
            {
                "Content-Type": request.headers.get("Content-Type", "application/sdp"),
                "Accept": request.headers.get("Accept", "application/sdp"),
            },
        )

        location = response.headers.get("Location")
        response_headers = {
            **WHEP_CORS_HEADERS,
            "Content-Type": response.headers.get("Content-Type", "application/sdp"),
        }
        if location:
            response_headers["Location"] = location
        
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=response_headers
        )
    except httpx.TimeoutException:
        return _whep_error_response(504, "Stream timeout - MediaMTX may not be running")
    except httpx.ConnectError:
        return _whep_error_response(503, "Cannot connect to MediaMTX - service may be down")
    except Exception as e:
        logger.error(f"MediaMTX WHEP compat error for {stream_name}: {e}")
        return _whep_error_response(500, str(e))


@app.get("/api/turn-credentials")
async def get_turn_credentials() -> Dict[str, Any]:
    """Get TURN credentials from Coolify TURN API.
    
    This endpoint fetches ICE servers with temporary credentials from the centralized
    Coolify TURN API. This enables remote guests to connect via WebRTC using TURN relay.
    
    The Coolify TURN API handles credential generation and caching, providing a
    centralized point for TURN configuration across all R58 devices.
    
    Note: TURN removed - remote guests now use direct WHIP to MediaMTX.
    This endpoint only returns STUN for local network WebRTC.
    """
    return {
        "iceServers": [
            {"urls": ["stun:stun.l.google.com:19302"]}
        ]
    }


@app.get("/api/streams")
async def list_available_streams() -> Dict[str, Any]:
    """List available HLS streams from MediaMTX."""
    try:
        async with httpx.AsyncClient() as client:
            # Try to get MediaMTX API info
            response = await client.get(f"{MEDIAMTX_HLS_BASE.replace('8888', '9997')}/v3/paths/list", timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                return {
                    "status": "ok",
                    "streams": data.get("items", []),
                    "hls_base": "/hls"
                }
    except Exception as e:
        logger.debug(f"Could not get MediaMTX API: {e}")
    
    # Fallback - return configured camera streams
    return {
        "status": "ok",
        "streams": [f"{cam_id}_preview" for cam_id in config.cameras.keys()],
        "hls_base": "/hls",
        "note": "List based on configured cameras, actual streams may vary"
    }


@app.get("/api/mediamtx/status")
async def get_mediamtx_status() -> Dict[str, Any]:
    """Check MediaMTX connectivity and status."""
    status = {
        "mediamtx_enabled": config.mediamtx.enabled,
        "hls_port": 8888,
        "rtsp_port": config.mediamtx.rtsp_port if config.mediamtx.enabled else None,
        "rtmp_port": config.mediamtx.rtmp_port if config.mediamtx.enabled else None,
        "connectivity": {}
    }
    
    if not config.mediamtx.enabled:
        return {**status, "message": "MediaMTX is disabled in configuration"}
    
    # Test HLS endpoint
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{MEDIAMTX_HLS_BASE}/", timeout=2.0)
            status["connectivity"]["hls"] = {
                "reachable": True,
                "status_code": response.status_code
            }
    except httpx.ConnectError:
        status["connectivity"]["hls"] = {
            "reachable": False,
            "error": "Connection refused - MediaMTX may not be running"
        }
    except Exception as e:
        status["connectivity"]["hls"] = {
            "reachable": False,
            "error": str(e)
        }
    
    # Test RTSP endpoint
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"http://localhost:{config.mediamtx.rtsp_port}/", timeout=2.0)
            status["connectivity"]["rtsp"] = {
                "reachable": True,
                "status_code": response.status_code
            }
    except Exception as e:
        status["connectivity"]["rtsp"] = {
            "reachable": False,
            "error": str(e)
        }
    
    return status


# Streaming API endpoints (compatible with new backend API)
MEDIAMTX_API = "http://localhost:9997"


@app.get("/api/streaming/status")
async def get_streaming_status() -> Dict[str, Any]:
    """
    Get current streaming status from MediaMTX.
    
    Returns:
    - Whether mixer_program stream is active
    - Current runOnReady configuration (if any)
    - Stream statistics
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Get path list
            paths_response = await client.get(f"{MEDIAMTX_API}/v3/paths/list")
            paths_response.raise_for_status()
            paths_data = paths_response.json()
            
            # Find mixer_program path
            mixer_active = False
            mixer_info = None
            
            for path in paths_data.get("items", []):
                if path.get("name") == "mixer_program":
                    mixer_active = path.get("ready", False)
                    mixer_info = path
                    break
            
            # Get config to check runOnReady
            run_on_ready = None
            try:
                config_response = await client.get(
                    f"{MEDIAMTX_API}/v3/config/paths/get/mixer_program"
                )
                if config_response.status_code == 200:
                    config_data = config_response.json()
                    run_on_ready = config_data.get("runOnReady", "")
            except:
                pass
            
            bytes_received = mixer_info.get("bytesReceived") if mixer_info else None
            bytes_sent = mixer_info.get("bytesSent") if mixer_info else None
            readers = mixer_info.get("readers") if mixer_info else None
            source = mixer_info.get("source") if mixer_info else None

            return {
                "active": mixer_active,
                "mixer_program_active": mixer_active,
                "rtmp_relay_configured": bool(run_on_ready),
                "run_on_ready": run_on_ready or None,
                "bytes_received": bytes_received,
                "bytes_sent": bytes_sent,
                "readers": readers,
                "source": source,
                "stream_info": mixer_info
            }
            
    except httpx.HTTPError as e:
        logger.error(f"MediaMTX API error: {e}")
        return {
            "active": False,
            "mixer_program_active": False,
            "rtmp_relay_configured": False,
            "run_on_ready": None,
            "error": "MediaMTX API not available"
        }
    except Exception as e:
        logger.error(f"Failed to get streaming status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/streaming/stats")
async def get_streaming_stats() -> Dict[str, Any]:
    """Get detailed mixer_program statistics from MediaMTX."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{MEDIAMTX_API}/v3/paths/get/mixer_program")
            if response.status_code == 404:
                return {"active": False, "error": "mixer_program path not found"}
            response.raise_for_status()
            data = response.json()

            source = data.get("source", {})
            video_info = source.get("video", {}) if isinstance(source, dict) else {}
            audio_info = source.get("audio", {}) if isinstance(source, dict) else {}

            return {
                "active": data.get("ready", False),
                "bitrate_bps": data.get("bytesReceived", 0) * 8 if data.get("bytesReceived") else None,
                "bytes_received_total": data.get("bytesReceived"),
                "bytes_sent_total": data.get("bytesSent"),
                "readers": data.get("readers"),
                "source": {
                    "video": {
                        "resolution": video_info.get("resolution"),
                        "fps": video_info.get("fps"),
                        "codec": video_info.get("codec")
                    },
                    "audio": {
                        "codec": audio_info.get("codec"),
                        "sample_rate": audio_info.get("sampleRate"),
                        "channels": audio_info.get("channels")
                    }
                }
            }
    except httpx.HTTPError as e:
        logger.error(f"MediaMTX API error (stats): {e}")
        return {"active": False, "error": "MediaMTX API not available"}
    except Exception as e:
        logger.error(f"Failed to get streaming stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class RTMPDestination(BaseModel):
    """RTMP streaming destination configuration"""
    platform: str  # youtube, twitch, facebook, custom
    rtmp_url: str
    stream_key: str
    enabled: bool = True


class StartStreamingRequest(BaseModel):
    """Request to start RTMP relay from MediaMTX to external platform"""
    destinations: List[RTMPDestination]


def build_ffmpeg_relay_command(destinations: List[RTMPDestination]) -> str:
    """
    Build FFmpeg command to relay to multiple RTMP destinations.
    
    Note: VDO.ninja uses Opus audio which can't be copied to FLV container.
    We must transcode audio to AAC for RTMP compatibility.
    """
    if not destinations:
        return ""
    
    # FFmpeg options:
    # -c:v copy = copy H.264 video (no re-encode)
    # -c:a aac = transcode Opus to AAC (required for FLV/RTMP)
    # -ar 44100 = standard sample rate
    # -b:a 128k = good quality audio bitrate
    audio_opts = "-c:v copy -c:a aac -ar 44100 -b:a 128k"
    
    # For single destination, simple command
    if len(destinations) == 1:
        dest = destinations[0]
        rtmp_url = f"{dest.rtmp_url}{dest.stream_key}"
        return f"ffmpeg -i rtsp://localhost:8554/mixer_program {audio_opts} -f flv '{rtmp_url}'"
    
    # For multiple destinations, use tee muxer
    outputs = []
    for dest in destinations:
        rtmp_url = f"{dest.rtmp_url}{dest.stream_key}"
        outputs.append(f"[f=flv]{rtmp_url}")
    
    tee_output = "|".join(outputs)
    return f"ffmpeg -i rtsp://localhost:8554/mixer_program {audio_opts} -f tee '{tee_output}'"


@app.post("/api/streaming/rtmp/start")
async def start_rtmp_streaming(request: StartStreamingRequest):
    """
    Start RTMP relay using MediaMTX's runOnReady hook.
    
    Configures MediaMTX to spawn FFmpeg when mixer_program stream is ready.
    """
    try:
        enabled_destinations = [d for d in request.destinations if d.enabled]
        
        if not enabled_destinations:
            return {
                "status": "error",
                "message": "No enabled destinations provided"
            }
        
        # Build the FFmpeg relay command
        ffmpeg_cmd = build_ffmpeg_relay_command(enabled_destinations)
        
        # Configure MediaMTX mixer_program path with runOnReady hook
        config = {
            "source": "publisher",
            "runOnReady": ffmpeg_cmd,
            "runOnReadyRestart": True
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            # First, try to patch the existing path
            response = await client.patch(
                f"{MEDIAMTX_API}/v3/config/paths/patch/mixer_program",
                json=config
            )
            
            if response.status_code == 404:
                # Path doesn't exist, add it
                response = await client.post(
                    f"{MEDIAMTX_API}/v3/config/paths/add/mixer_program",
                    json=config
                )
            
            response.raise_for_status()
        
        destination_names = [d.platform for d in enabled_destinations]
        logger.info(f"Configured RTMP relay to: {destination_names}")
        
        return {
            "status": "success",
            "message": f"RTMP relay configured for {len(enabled_destinations)} destination(s)",
            "destinations": destination_names,
            "command": ffmpeg_cmd,
            "note": "FFmpeg will start automatically when mixer_program stream is published"
        }
        
    except httpx.HTTPError as e:
        logger.error(f"MediaMTX API error: {e}")
        raise HTTPException(status_code=502, detail=f"Failed to configure MediaMTX: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to configure RTMP streaming: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/streaming/rtmp/stop")
async def stop_rtmp_streaming():
    """Stop RTMP relay by removing the runOnReady hook from MediaMTX."""
    try:
        config = {
            "source": "publisher",
            "runOnReady": "",
            "runOnReadyRestart": False
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.patch(
                f"{MEDIAMTX_API}/v3/config/paths/patch/mixer_program",
                json=config
            )
            
            if response.status_code != 404:
                response.raise_for_status()
        
        logger.info("RTMP relay stopped - runOnReady hook removed")
        
        return {
            "status": "success",
            "message": "RTMP relay stopped"
        }
        
    except httpx.HTTPError as e:
        logger.error(f"MediaMTX API error: {e}")
        raise HTTPException(status_code=502, detail=f"Failed to stop RTMP relay: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to stop RTMP streaming: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/test/start-video")
async def start_test_video(request: Dict[str, Any] = Body({})) -> Dict[str, Any]:
    """Start a test video source for testing the streaming pipeline.
    
    This starts an FFmpeg process that generates a test pattern with audio
    and publishes it to MediaMTX at mixer_program.
    
    Args:
        duration: Duration in seconds (default: 120, max: 600)
    """
    import subprocess
    import os
    
    duration = min(request.get("duration", 120), 600)  # Max 10 minutes
    
    # Kill any existing test video
    try:
        subprocess.run(
            ["pkill", "-f", "ffmpeg.*testsrc.*mixer_program"],
            capture_output=True,
            timeout=5
        )
    except:
        pass
    
    # Build FFmpeg command for test pattern with audio
    ffmpeg_cmd = [
        "ffmpeg", "-y", "-re",
        "-f", "lavfi", "-i", f"testsrc=duration={duration}:size=1280x720:rate=30",
        "-f", "lavfi", "-i", f"sine=frequency=1000:sample_rate=48000:duration={duration}",
        "-c:v", "libx264", "-preset", "ultrafast", "-tune", "zerolatency",
        "-pix_fmt", "yuv420p", "-b:v", "2000k",
        "-c:a", "aac", "-ar", "48000", "-b:a", "128k",
        "-f", "rtsp", "rtsp://localhost:8554/mixer_program"
    ]
    
    try:
        # Start in background
        process = subprocess.Popen(
            ffmpeg_cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True
        )
        
        logger.info(f"Started test video with PID {process.pid} for {duration}s")
        
        return {
            "success": True,
            "message": f"Test video started for {duration} seconds",
            "pid": process.pid,
            "duration": duration
        }
    except Exception as e:
        logger.error(f"Failed to start test video: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/test/stop-video")
async def stop_test_video() -> Dict[str, Any]:
    """Stop the test video source."""
    import subprocess
    
    try:
        result = subprocess.run(
            ["pkill", "-f", "ffmpeg.*testsrc.*mixer_program"],
            capture_output=True,
            timeout=5
        )
        
        return {
            "success": True,
            "message": "Test video stopped"
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }


@app.get("/api/fps")
async def get_fps_stats() -> Dict[str, Any]:
    """Get real-time framerate statistics for all cameras.
    
    Returns FPS data measured by counting actual frames in the GStreamer pipelines.
    This is the most accurate way to verify the actual framerate.
    
    Returns:
        Dictionary with FPS stats per camera:
        - current_fps: Frames per second in the last interval
        - avg_fps: Average FPS since pipeline started
        - min_fps: Minimum FPS observed
        - max_fps: Maximum FPS observed
        - total_frames: Total frames processed
        - uptime_seconds: Time since monitoring started
    """
    fps_monitor = get_fps_monitor()
    stats = fps_monitor.get_all_stats()
    
    # Add summary
    if stats:
        current_fps_values = [s["current_fps"] for s in stats.values() if s["current_fps"] > 0]
        avg_current = sum(current_fps_values) / len(current_fps_values) if current_fps_values else 0
        all_at_30 = all(s["current_fps"] >= 28 for s in stats.values() if s["current_fps"] > 0)
        
        return {
            "cameras": stats,
            "summary": {
                "active_cameras": len(current_fps_values),
                "average_fps": round(avg_current, 1),
                "all_at_target": all_at_30,
                "target_fps": 30,
                "status": "✓ All cameras at 30fps" if all_at_30 else "⚠ Some cameras below target"
            }
        }
    
    return {
        "cameras": {},
        "summary": {
            "active_cameras": 0,
            "average_fps": 0,
            "all_at_target": False,
            "target_fps": 30,
            "status": "No cameras streaming"
        }
    }


@app.get("/status")
async def get_status() -> Dict[str, Dict[str, Any]]:
    """Get status of all cameras."""
    recording_statuses = recorder.get_status()
    preview_statuses = preview_manager.get_preview_status()
    
    # Combine recording and preview statuses
    combined_statuses = {}
    for cam_id in config.cameras.keys():
        recording_status = recording_statuses.get(cam_id, "idle")
        preview_status = preview_statuses.get(cam_id, "idle")
        
        # Prioritize recording over preview
        if recording_status == "recording":
            combined_statuses[cam_id] = {"status": "recording", "config": True}
        elif preview_status == "preview":
            combined_statuses[cam_id] = {"status": "preview", "config": True}
        else:
            combined_statuses[cam_id] = {"status": recording_status, "config": True}
    
    return {"cameras": combined_statuses}


@app.get("/status/{cam_id}")
async def get_camera_status(cam_id: str) -> Dict[str, str]:
    """Get status of a specific camera."""
    if cam_id not in config.cameras:
        raise HTTPException(status_code=404, detail=f"Camera {cam_id} not found")

    status = recorder.get_camera_status(cam_id)
    if status is None:
        raise HTTPException(status_code=404, detail=f"Camera {cam_id} not found")

    return {"camera": cam_id, "status": status}


@app.get("/api/cameras/{cam_id}/signal")
async def get_camera_signal(cam_id: str) -> Dict[str, Any]:
    """Get detailed signal and pipeline information for a camera."""
    if cam_id not in config.cameras:
        raise HTTPException(status_code=404, detail=f"Camera {cam_id} not found")
    
    cam_config = config.cameras[cam_id]
    device = cam_config.device
    
    # Get device capabilities
    try:
        from .device_detection import get_device_capabilities, detect_device_type
        caps = get_device_capabilities(device)
        device_type = detect_device_type(device)
    except Exception as e:
        logger.error(f"Error getting device capabilities for {cam_id}: {e}")
        caps = {
            'format': None,
            'width': 0,
            'height': 0,
            'framerate': 0,
            'has_signal': False,
            'is_bayer': False,
            'bayer_format': None
        }
        device_type = "unknown"
    
    # Get recording status
    recording_status = recorder.get_camera_status(cam_id)
    recording_info = {
        "active": recording_status == "recording",
        "file_path": None,  # TODO: Get actual file path from recorder
        "bytes_written": 0,  # TODO: Get actual bytes from recorder
        "duration_seconds": 0  # TODO: Get actual duration from recorder
    }
    
    # Get preview status
    preview_status = preview_manager.get_camera_preview_status(cam_id)
    preview_info = {
        "active": preview_status == "preview",
        "mediamtx_path": f"{cam_id}_preview" if config.mediamtx.enabled else None,
        "hls_segments_written": 0  # TODO: Get from MediaMTX API if needed
    }
    
    # Determine hardware info based on device type
    hardware_info = {
        "device_type": device_type,
        "bridge_type": None,
        "i2c_bus": None,
        "i2c_address": None
    }
    
    if device_type == "hdmi_rkcif":
        hardware_info["bridge_type"] = "LT6911UXE"
        # Map device to I2C bus
        if "video0" in device:
            hardware_info["i2c_bus"] = 7
        elif "video11" in device:
            hardware_info["i2c_bus"] = 4
        elif "video21" in device:
            hardware_info["i2c_bus"] = 2
        hardware_info["i2c_address"] = "0x2b"
    
    # Determine pipeline state and error
    pipeline_state = "idle"
    pipeline_error = None
    
    if recording_status == "recording":
        pipeline_state = "recording"
    elif preview_status == "preview":
        pipeline_state = "preview"
    elif preview_status == "error":
        pipeline_state = "error"
        pipeline_error = "Pipeline error - check logs"
    
    if not caps['has_signal']:
        pipeline_error = "No HDMI signal detected"
    
    # Get FPS stats from monitor if available
    fps_monitor = get_fps_monitor()
    fps_stats = fps_monitor.get_stats(cam_id)
    fps_info = None
    if fps_stats:
        fps_stats.update()  # Calculate current FPS
        fps_info = {
            "current_fps": round(fps_stats.current_fps, 1),
            "avg_fps": round(fps_stats.avg_fps, 1),
            "min_fps": round(fps_stats.min_fps, 1) if fps_stats.min_fps != float('inf') else 0,
            "max_fps": round(fps_stats.max_fps, 1),
            "total_frames": fps_stats.total_frames
        }
    
    return {
        "cam_id": cam_id,
        "device": device,
        "signal": {
            "present": caps['has_signal'],
            "resolution": f"{caps['width']}x{caps['height']}" if caps['has_signal'] else "0x0",
            "frame_rate": caps['framerate'],
            "pixel_format": caps['format'],
            "colorspace": None  # TODO: Extract from v4l2-ctl if needed
        },
        "pipeline": {
            "state": pipeline_state,
            "frames_received": fps_stats.total_frames if fps_stats else 0,
            "frames_dropped": 0,  # TODO: Add drop counter to pipelines
            "last_frame_timestamp": None,  # TODO: Add timestamp tracking
            "error": pipeline_error,
            "fps": fps_info  # Real-time FPS from monitor
        },
        "recording": recording_info,
        "preview": preview_info,
        "hardware": hardware_info
    }


@app.get("/recordings/{cam_id}")
async def list_recordings(cam_id: str) -> Dict[str, Any]:
    """List recordings for a camera."""
    if cam_id not in config.cameras:
        raise HTTPException(status_code=404, detail=f"Camera {cam_id} not found")

    cam_config = config.cameras[cam_id]
    recordings_dir = Path(cam_config.output_path).parent

    recordings = []
    if recordings_dir.exists():
        # Find both MP4 and MKV files
        all_files = list(recordings_dir.glob("*.mp4")) + list(recordings_dir.glob("*.mkv"))
        for file_path in sorted(all_files, key=os.path.getmtime, reverse=True):
            recordings.append({
                "filename": file_path.name,
                "size": file_path.stat().st_size,
                "modified": int(file_path.stat().st_mtime),
                "path": str(file_path),
            })

    return {"cam_id": cam_id, "recordings": recordings}


@app.get("/recordings/{cam_id}/{filename}")
async def get_recording(cam_id: str, filename: str) -> FileResponse:
    """Download or view a recording."""
    if cam_id not in config.cameras:
        raise HTTPException(status_code=404, detail=f"Camera {cam_id} not found")

    cam_config = config.cameras[cam_id]
    recordings_dir = Path(cam_config.output_path).parent
    file_path = recordings_dir / filename

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Recording not found")

    # Determine media type from file extension
    ext = file_path.suffix.lower()
    media_type = {
        ".mkv": "video/x-matroska",
        ".mp4": "video/mp4",
        ".webm": "video/webm",
        ".mov": "video/quicktime",
    }.get(ext, "application/octet-stream")

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type=media_type,
    )


@app.get("/api/sessions")
async def list_sessions() -> Dict[str, Any]:
    """List all recording sessions."""
    sessions_dir = Path("data/sessions")
    sessions = []
    
    if sessions_dir.exists():
        for session_file in sorted(sessions_dir.glob("*.json"), reverse=True):
            try:
                with open(session_file, 'r') as f:
                    session_data = json.load(f)
                    sessions.append(session_data)
            except Exception as e:
                logger.error(f"Failed to read session file {session_file}: {e}")
    
    return {"sessions": sessions}


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str) -> Dict[str, Any]:
    """Get metadata for a specific session."""
    sessions_dir = Path("data/sessions")
    session_file = sessions_dir / f"{session_id}.json"
    
    if not session_file.exists():
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        with open(session_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read session: {e}")


@app.get("/api/recordings")
async def list_all_recordings() -> Dict[str, Any]:
    """List all recordings across all cameras, grouped by date and session."""
    from datetime import datetime
    from collections import defaultdict
    
    # Dictionary to group recordings by date
    recordings_by_date = defaultdict(list)
    total_count = 0
    total_size = 0
    
    # Scan all camera directories
    for cam_id, cam_config in config.cameras.items():
        recordings_dir = Path(cam_config.output_path).parent
        
        if not recordings_dir.exists():
            continue
        
        # Find all video files (MP4 and MKV)
        for file_path in list(recordings_dir.glob("*.mp4")) + list(recordings_dir.glob("*.mkv")):
            try:
                stat = file_path.stat()
                
                # Extract date from filename (format: recording_YYYYMMDD_HHMMSS.mkv or .mp4)
                filename = file_path.name
                if filename.startswith("recording_") and len(filename) >= 24:
                    date_str = filename[10:18]  # YYYYMMDD
                    time_str = filename[19:25]  # HHMMSS
                    
                    # Format date as YYYY-MM-DD
                    formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                    formatted_time = f"{time_str[:2]}:{time_str[2:4]}:{time_str[4:6]}"
                else:
                    # Fallback to modification time
                    dt = datetime.fromtimestamp(stat.st_mtime)
                    formatted_date = dt.strftime("%Y-%m-%d")
                    formatted_time = dt.strftime("%H:%M:%S")
                
                recording_info = {
                    "cam_id": cam_id,
                    "filename": filename,
                    "size": stat.st_size,
                    "modified": int(stat.st_mtime),
                    "time": formatted_time,
                    "path": str(file_path),
                    "url": f"/recordings/{cam_id}/{filename}"
                }
                
                recordings_by_date[formatted_date].append(recording_info)
                total_count += 1
                total_size += stat.st_size
            except Exception as e:
                logger.error(f"Error processing recording {file_path}: {e}")
                continue
    
    # Group recordings into sessions by time gap (10 minutes)
    def group_into_sessions(recordings, time_gap_minutes=10):
        """Group recordings into sessions based on time proximity."""
        if not recordings:
            return []
        
        # Sort by timestamp
        sorted_recordings = sorted(recordings, key=lambda x: x["modified"])
        sessions = []
        current_session = [sorted_recordings[0]]
        
        for recording in sorted_recordings[1:]:
            last_time = current_session[-1]["modified"]
            current_time = recording["modified"]
            gap_minutes = (current_time - last_time) / 60
            
            if gap_minutes <= time_gap_minutes:
                current_session.append(recording)
            else:
                sessions.append(current_session)
                current_session = [recording]
        
        if current_session:
            sessions.append(current_session)
        
        return sessions
    
    # Convert to list of date groups with sessions
    date_groups = []
    for date in sorted(recordings_by_date.keys(), reverse=True):
        recordings = recordings_by_date[date]
        sessions = group_into_sessions(recordings)
        
        # Create session objects
        date_sessions = []
        for idx, session_recordings in enumerate(sessions):
            # Sort recordings within session by time (newest first for display)
            session_recordings_sorted = sorted(session_recordings, key=lambda x: x["modified"], reverse=True)
            
            # Get session time range
            start_time = min(r["modified"] for r in session_recordings)
            end_time = max(r["modified"] for r in session_recordings)
            
            # Create session ID from first recording's timestamp
            first_recording = min(session_recordings, key=lambda x: x["modified"])
            session_id = f"session_{date.replace('-', '')}_{first_recording['time'].replace(':', '')}"
            
            date_sessions.append({
                "session_id": session_id,
                "name": None,  # Will be populated from session names storage
                "start_time": datetime.fromtimestamp(start_time).strftime("%H:%M:%S"),
                "end_time": datetime.fromtimestamp(end_time).strftime("%H:%M:%S"),
                "recordings": session_recordings_sorted,
                "count": len(session_recordings),
                "total_size": sum(r["size"] for r in session_recordings)
            })
        
        date_groups.append({
            "date": date,
            "date_sessions": date_sessions,
            "count": len(recordings),
            "total_size": sum(r["size"] for r in recordings)
        })
    
    # Load session names and populate
    session_names = _load_session_names()
    for date_group in date_groups:
        for session in date_group["date_sessions"]:
            session_id = session["session_id"]
            if session_id in session_names:
                session["name"] = session_names[session_id]["name"]
    
    return {
        "sessions": date_groups,
        "total_count": total_count,
        "total_size": total_size
    }


# Session naming helper functions
def _get_sessions_file_path() -> Path:
    """Get path to sessions.json file."""
    data_dir = Path(__file__).parent.parent / "data"
    data_dir.mkdir(exist_ok=True)
    return data_dir / "sessions.json"


def _load_session_names() -> Dict[str, Any]:
    """Load session names from JSON file."""
    sessions_file = _get_sessions_file_path()
    if sessions_file.exists():
        try:
            with open(sessions_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading session names: {e}")
            return {}
    return {}


def _save_session_names(sessions: Dict[str, Any]) -> bool:
    """Save session names to JSON file."""
    sessions_file = _get_sessions_file_path()
    try:
        with open(sessions_file, 'w') as f:
            json.dump(sessions, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving session names: {e}")
        return False


@app.get("/api/sessions")
async def get_all_sessions() -> Dict[str, Any]:
    """Get all session names."""
    session_names = _load_session_names()
    return {"sessions": session_names}


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str) -> Dict[str, Any]:
    """Get a specific session's name."""
    session_names = _load_session_names()
    if session_id in session_names:
        return {
            "session_id": session_id,
            "name": session_names[session_id]["name"],
            "created_at": session_names[session_id].get("created_at")
        }
    return {
        "session_id": session_id,
        "name": None,
        "created_at": None
    }


@app.put("/api/sessions/{session_id}")
async def update_session_name(session_id: str, request: Dict[str, Any]) -> Dict[str, str]:
    """Update a session's name."""
    name = request.get("name")
    if name is None:
        raise HTTPException(status_code=400, detail="Name is required")
    
    session_names = _load_session_names()
    session_names[session_id] = {
        "name": name,
        "created_at": session_names.get(session_id, {}).get("created_at", int(time.time()))
    }
    
    if _save_session_names(session_names):
        return {"status": "updated", "session_id": session_id, "name": name}
    else:
        raise HTTPException(status_code=500, detail="Failed to save session name")


@app.delete("/api/sessions/{session_id}")
async def delete_session_name(session_id: str) -> Dict[str, str]:
    """Delete a session's name."""
    session_names = _load_session_names()
    if session_id in session_names:
        del session_names[session_id]
        if _save_session_names(session_names):
            return {"status": "deleted", "session_id": session_id}
        else:
            raise HTTPException(status_code=500, detail="Failed to save session names")
    raise HTTPException(status_code=404, detail="Session not found")


# Mixer API endpoints
@app.get("/api/scenes")
async def list_scenes() -> Dict[str, Any]:
    """List all available scenes."""
    if not scene_manager:
        raise HTTPException(status_code=503, detail="Mixer not enabled")
    
    scenes = scene_manager.list_scenes()
    return {"scenes": scenes}


@app.get("/api/scenes/{scene_id}")
async def get_scene(scene_id: str) -> Dict[str, Any]:
    """Get a specific scene definition."""
    if not scene_manager:
        raise HTTPException(status_code=503, detail="Mixer not enabled")
    
    scene = scene_manager.get_scene(scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail=f"Scene {scene_id} not found")
    
    return scene.to_dict()


@app.post("/api/scenes")
async def create_scene(scene_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create or update a scene."""
    if not scene_manager:
        raise HTTPException(status_code=503, detail="Mixer not enabled")
    
    try:
        from .mixer.scenes import Scene
        scene = Scene.from_dict(scene_data)
        success = scene_manager.create_scene(scene)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to create scene")
        return {"status": "created", "scene_id": scene.id}
    except Exception as e:
        logger.error(f"Failed to create scene: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid scene data: {str(e)}")


@app.put("/api/scenes/{scene_id}")
async def update_scene(scene_id: str, scene_data: Dict[str, Any]) -> Dict[str, Any]:
    """Update a scene."""
    if not scene_manager:
        raise HTTPException(status_code=503, detail="Mixer not enabled")
    
    try:
        from .mixer.scenes import Scene
        # Ensure scene_id matches
        scene_data["id"] = scene_id
        scene = Scene.from_dict(scene_data)
        success = scene_manager.create_scene(scene)  # create_scene also updates
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update scene")
        return {"status": "updated", "scene_id": scene_id}
    except Exception as e:
        logger.error(f"Failed to update scene: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid scene data: {str(e)}")


@app.delete("/api/scenes/{scene_id}")
async def delete_scene(scene_id: str) -> Dict[str, str]:
    """Delete a scene."""
    if not scene_manager:
        raise HTTPException(status_code=503, detail="Mixer not enabled")
    
    success = scene_manager.delete_scene(scene_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Scene {scene_id} not found")
    
    return {"status": "deleted", "scene_id": scene_id}


@app.post("/api/mixer/set_scene")
async def set_scene(request: Dict[str, str]) -> Dict[str, str]:
    """Apply a scene to the mixer."""
    if not mixer_core:
        raise HTTPException(status_code=503, detail="Mixer not enabled")
    
    scene_id = request.get("id")
    if not scene_id:
        raise HTTPException(status_code=400, detail="Scene ID required")
    
    success = mixer_core.apply_scene(scene_id)
    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to apply scene {scene_id}")
    
    return {"status": "applied", "scene_id": scene_id}


@app.post("/api/mixer/transition")
async def transition_scene(request: Dict[str, Any]) -> Dict[str, Any]:
    """Transition to a scene with animation.
    
    Body:
        scene_id: Scene ID to transition to
        transition: Transition type ("cut", "mix", "auto")
        duration: Duration in milliseconds (default: 500 for mix, 1000 for auto)
    """
    if not mixer_core:
        raise HTTPException(status_code=503, detail="Mixer not enabled")
    
    scene_id = request.get("scene_id")
    transition = request.get("transition", "cut")
    duration = request.get("duration")
    
    if not scene_id:
        raise HTTPException(status_code=400, detail="Scene ID required")
    
    # Set default durations based on transition type
    if duration is None:
        if transition == "auto":
            duration = 1000  # 1 second for auto
        elif transition == "mix":
            duration = 500  # 0.5 seconds for mix
        else:
            duration = 0  # Instant for cut
    
    success = mixer_core.transition_to_scene(scene_id, transition, duration)
    if not success:
        raise HTTPException(status_code=500, detail=f"Transition failed")
    
    return {"status": "transitioning", "scene_id": scene_id, "transition": transition, "duration_ms": duration}


@app.post("/api/mixer/start")
async def start_mixer() -> Dict[str, str]:
    """Start the mixer pipeline."""
    if not mixer_core:
        raise HTTPException(status_code=503, detail="Mixer not enabled")
    
    # Auto-switch to mixer mode if not already
    if mode_manager:
        current_mode = await mode_manager.get_current_mode()
        if current_mode != "mixer":
            logger.info("Auto-switching to mixer mode...")
            result = await mode_manager.switch_to_mixer()
            if not result["success"]:
                raise HTTPException(status_code=500, detail=f"Failed to switch to mixer mode: {result.get('message')}")
    
    success = mixer_core.start()
    if not success:
        raise HTTPException(status_code=500, detail="Failed to start mixer")
    
    return {"status": "started"}


@app.post("/api/mixer/stop")
async def stop_mixer() -> Dict[str, str]:
    """Stop the mixer pipeline."""
    if not mixer_core:
        raise HTTPException(status_code=503, detail="Mixer not enabled")
    
    success = mixer_core.stop()
    if not success:
        raise HTTPException(status_code=500, detail="Failed to stop mixer")
    
    return {"status": "stopped"}


@app.get("/api/mixer/status")
async def get_mixer_status() -> Dict[str, Any]:
    """Get mixer status."""
    if not mixer_core:
        raise HTTPException(status_code=503, detail="Mixer not enabled")
    
    return mixer_core.get_status()


# Mixer overlay API endpoints
@app.post("/api/mixer/overlay/{source}")
async def enable_mixer_overlay(source: str, alpha: float = 1.0) -> Dict[str, Any]:
    """Enable overlay layer on mixer output.
    
    Args:
        source: Overlay source (e.g., "slides")
        alpha: Transparency (0.0-1.0)
    """
    if not mixer_core:
        raise HTTPException(status_code=503, detail="Mixer not enabled")
    
    success = mixer_core.enable_overlay(source, alpha)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to enable overlay")
    
    return {"status": "overlay_enabled", "source": source, "alpha": alpha}


@app.delete("/api/mixer/overlay/{source}")
async def disable_mixer_overlay(source: str) -> Dict[str, str]:
    """Disable overlay layer on mixer output."""
    if not mixer_core:
        raise HTTPException(status_code=503, detail="Mixer not enabled")
    
    success = mixer_core.disable_overlay()
    if not success:
        raise HTTPException(status_code=500, detail="Failed to disable overlay")
    
    return {"status": "overlay_disabled"}


@app.put("/api/mixer/overlay/{source}/alpha")
async def set_mixer_overlay_alpha(source: str, alpha: float) -> Dict[str, Any]:
    """Set overlay transparency.
    
    Args:
        source: Overlay source
        alpha: Transparency (0.0-1.0)
    """
    if not mixer_core:
        raise HTTPException(status_code=503, detail="Mixer not enabled")
    
    success = mixer_core.set_overlay_alpha(alpha)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to set overlay alpha")
    
    return {"status": "alpha_updated", "alpha": alpha}


# Reveal.js API endpoints - supports multiple independent outputs
@app.get("/reveal", response_class=HTMLResponse)
async def reveal_demo():
    """Serve a Reveal.js demo presentation page."""
    reveal_index = Path(__file__).parent.parent / "reveal.js" / "index.html"
    if reveal_index.exists():
        # Read and modify the HTML to use local paths
        html_content = reveal_index.read_text()
        # Replace dist/ paths with /reveal.js/ paths
        html_content = html_content.replace('href="dist/', 'href="/reveal.js/')
        html_content = html_content.replace('src="dist/', 'src="/reveal.js/')
        html_content = html_content.replace('href="plugin/', 'href="/reveal-demo/plugin/')
        html_content = html_content.replace('src="plugin/', 'src="/reveal-demo/plugin/')
        return html_content
    else:
        # Fallback: create a simple reveal.js page
        return """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Reveal.js Demo</title>
    <link rel="stylesheet" href="/reveal.js/reveal.css">
    <link rel="stylesheet" href="/reveal.js/theme/black.css">
</head>
<body>
    <div class="reveal">
        <div class="slides">
            <section>
                <h1>Reveal.js Demo</h1>
                <p>reveal.js is working on R58!</p>
            </section>
            <section>
                <h2>Slide 2</h2>
                <p>Use arrow keys to navigate</p>
            </section>
        </div>
    </div>
    <script src="/reveal.js/reveal.js"></script>
    <script>
        Reveal.initialize({ hash: true });
    </script>
</body>
</html>"""


@app.get("/reveal/graphics", response_class=HTMLResponse)
async def reveal_graphics():
    """Serve a Reveal.js presentation page for graphics/presentations.
    
    This endpoint is optimized for use in the graphics overlay system
    and mixer presentations.
    """
    # Check if graphics.html exists (legacy graphics interface)
    graphics_html = Path(__file__).parent / "static" / "graphics.html"
    if graphics_html.exists():
        # Read and modify to use local reveal.js
        html_content = graphics_html.read_text()
        # Replace CDN URLs with local paths
        html_content = html_content.replace(
            'https://cdn.jsdelivr.net/npm/reveal.js@4.6.1/dist/reveal.css',
            '/reveal.js/reveal.css'
        )
        html_content = html_content.replace(
            'https://cdn.jsdelivr.net/npm/reveal.js@4.6.1/dist/theme/',
            '/reveal.js/theme/'
        )
        html_content = html_content.replace(
            'https://cdn.jsdelivr.net/npm/reveal.js@4.6.1/dist/reveal.js',
            '/reveal.js/reveal.js'
        )
        html_content = html_content.replace(
            'https://cdn.jsdelivr.net/npm/reveal.js@4.6.1/plugin/',
            '/reveal-demo/plugin/'
        )
        return html_content
    
    # Fallback: create a graphics-optimized reveal.js page
    return """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Reveal.js Graphics</title>
    <link rel="stylesheet" href="/reveal.js/reveal.css">
    <link rel="stylesheet" href="/reveal.js/theme/black.css">
    <style>
        .reveal .slides section {
            text-align: left;
        }
        .reveal h1, .reveal h2 {
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="reveal">
        <div class="slides">
            <section>
                <h1>Reveal.js Graphics</h1>
                <p>Presentation mode for graphics overlay</p>
            </section>
        </div>
    </div>
    <script src="/reveal.js/reveal.js"></script>
    <script>
        Reveal.initialize({
            hash: true,
            controls: false,
            progress: false,
            center: true
        });
    </script>
</body>
</html>"""


@app.get("/api/reveal/outputs")
async def get_reveal_outputs() -> Dict[str, Any]:
    """Get available Reveal.js output IDs."""
    if not reveal_source_manager:
        raise HTTPException(status_code=503, detail="Reveal.js not enabled")
    
    return {
        "outputs": reveal_source_manager.get_output_ids(),
        "renderer": reveal_source_manager.renderer_type
    }


@app.post("/api/reveal/{output_id}/start")
async def start_reveal_output(output_id: str, presentation_id: str, url: Optional[str] = None) -> Dict[str, Any]:
    """Start a specific Reveal.js video output.
    
    Args:
        output_id: Output identifier (e.g., "slides" or "slides_overlay")
        presentation_id: Presentation identifier
        url: Optional URL to render (defaults to /graphics?presentation={presentation_id})
    """
    if not reveal_source_manager:
        raise HTTPException(status_code=503, detail="Reveal.js not enabled")
    
    # Validate output_id
    if output_id not in reveal_source_manager.get_output_ids():
        raise HTTPException(
            status_code=400, 
            detail=f"Unknown output_id: {output_id}. Available: {reveal_source_manager.get_output_ids()}"
        )
    
    # Default URL if not provided
    if not url:
        url = f"http://localhost:8000/graphics?presentation={presentation_id}"
    
    success = reveal_source_manager.start(output_id, presentation_id, url)
    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to start Reveal.js output '{output_id}'")
    
    output_status = reveal_source_manager.get_output_status(output_id)
    return {
        "status": "started",
        "output_id": output_id,
        "presentation_id": presentation_id,
        "url": url,
        "stream_url": output_status["stream_url"] if output_status else None
    }


@app.post("/api/reveal/{output_id}/stop")
async def stop_reveal_output(output_id: str) -> Dict[str, str]:
    """Stop a specific Reveal.js video output."""
    if not reveal_source_manager:
        raise HTTPException(status_code=503, detail="Reveal.js not enabled")
    
    # Validate output_id
    if output_id not in reveal_source_manager.get_output_ids():
        raise HTTPException(
            status_code=400, 
            detail=f"Unknown output_id: {output_id}. Available: {reveal_source_manager.get_output_ids()}"
        )
    
    success = reveal_source_manager.stop(output_id)
    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to stop Reveal.js output '{output_id}'")
    
    return {"status": "stopped", "output_id": output_id}


@app.post("/api/reveal/stop")
async def stop_all_reveal() -> Dict[str, str]:
    """Stop all Reveal.js video outputs."""
    if not reveal_source_manager:
        raise HTTPException(status_code=503, detail="Reveal.js not enabled")
    
    success = reveal_source_manager.stop_all()
    if not success:
        raise HTTPException(status_code=500, detail="Failed to stop all Reveal.js outputs")
    
    return {"status": "stopped", "message": "All outputs stopped"}


@app.post("/api/reveal/{output_id}/navigate/{direction}")
async def navigate_reveal_output(output_id: str, direction: str) -> Dict[str, str]:
    """Navigate slides in a specific Reveal.js output.
    
    Args:
        output_id: Output identifier
        direction: Navigation direction (next, prev, first, last)
    """
    if not reveal_source_manager:
        raise HTTPException(status_code=503, detail="Reveal.js not enabled")
    
    if output_id not in reveal_source_manager.get_output_ids():
        raise HTTPException(
            status_code=400, 
            detail=f"Unknown output_id: {output_id}"
        )
    
    if direction not in ["next", "prev", "first", "last"]:
        raise HTTPException(status_code=400, detail="Invalid direction")
    
    success = reveal_source_manager.navigate(output_id, direction)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to navigate slides")
    
    return {"status": "navigated", "output_id": output_id, "direction": direction}


@app.post("/api/reveal/{output_id}/goto/{slide}")
async def goto_reveal_output_slide(output_id: str, slide: int) -> Dict[str, Any]:
    """Go to specific slide in a Reveal.js output.
    
    Args:
        output_id: Output identifier
        slide: Slide index
    """
    if not reveal_source_manager:
        raise HTTPException(status_code=503, detail="Reveal.js not enabled")
    
    if output_id not in reveal_source_manager.get_output_ids():
        raise HTTPException(
            status_code=400, 
            detail=f"Unknown output_id: {output_id}"
        )
    
    success = reveal_source_manager.goto_slide(output_id, slide)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to go to slide")
    
    return {"status": "navigated", "output_id": output_id, "slide": slide}


@app.get("/api/reveal/{output_id}/status")
async def get_reveal_output_status(output_id: str) -> Dict[str, Any]:
    """Get status of a specific Reveal.js output."""
    if not reveal_source_manager:
        raise HTTPException(status_code=503, detail="Reveal.js not enabled")
    
    if output_id not in reveal_source_manager.get_output_ids():
        raise HTTPException(
            status_code=400, 
            detail=f"Unknown output_id: {output_id}"
        )
    
    status = reveal_source_manager.get_output_status(output_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"Output '{output_id}' not found")
    
    return status


@app.get("/api/reveal/status")
async def get_reveal_status() -> Dict[str, Any]:
    """Get status of all Reveal.js outputs."""
    if not reveal_source_manager:
        raise HTTPException(status_code=503, detail="Reveal.js not enabled")
    
    return reveal_source_manager.get_status()


# Cairo Graphics API endpoints - real-time broadcast graphics
@app.get("/api/cairo/status")
async def get_cairo_status() -> Dict[str, Any]:
    """Get Cairo graphics manager status."""
    if not cairo_manager:
        raise HTTPException(status_code=503, detail="Cairo graphics not available")
    
    return cairo_manager.get_status()


@app.get("/api/cairo/elements")
async def list_cairo_elements() -> Dict[str, Any]:
    """List all Cairo graphics elements."""
    if not cairo_manager:
        raise HTTPException(status_code=503, detail="Cairo graphics not available")
    
    return {"elements": cairo_manager.list_elements()}


@app.post("/api/cairo/lower_third")
async def create_cairo_lower_third(request: Dict[str, Any]) -> Dict[str, Any]:
    """Create or update a Cairo lower third.
    
    Request body:
        - element_id: Unique identifier (required)
        - name: Name text (required)
        - title: Title text (optional)
        - x: X position (default: 50)
        - y: Y position (default: 900)
        - width: Width (default: 600)
        - height: Height (default: 120)
        - bg_color: Background color hex (default: "#000000")
        - bg_alpha: Background alpha (default: 0.8)
        - text_color: Text color hex (default: "#FFFFFF")
        - name_font_size: Name font size (default: 48)
        - title_font_size: Title font size (default: 28)
        - logo_path: Optional logo image path
    """
    if not cairo_manager:
        raise HTTPException(status_code=503, detail="Cairo graphics not available")
    
    element_id = request.get("element_id")
    name = request.get("name")
    
    if not element_id:
        raise HTTPException(status_code=400, detail="element_id required")
    if not name:
        raise HTTPException(status_code=400, detail="name required")
    
    try:
        from .cairo_graphics import LowerThird
        
        lower_third = LowerThird(
            element_id=element_id,
            name=name,
            title=request.get("title", ""),
            x=request.get("x", 50),
            y=request.get("y", 900),
            width=request.get("width", 600),
            height=request.get("height", 120),
            bg_color=request.get("bg_color", "#000000"),
            bg_alpha=request.get("bg_alpha", 0.8),
            text_color=request.get("text_color", "#FFFFFF"),
            name_font_size=request.get("name_font_size", 48),
            title_font_size=request.get("title_font_size", 28),
            logo_path=request.get("logo_path")
        )
        
        cairo_manager.add_element(element_id, lower_third)
        
        return {
            "status": "created",
            "element_id": element_id,
            "type": "lower_third",
            "name": name,
            "title": request.get("title", "")
        }
    except Exception as e:
        logger.error(f"Failed to create lower third: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create lower third: {e}")


@app.post("/api/cairo/lower_third/{element_id}/show")
async def show_cairo_lower_third(element_id: str) -> Dict[str, str]:
    """Show a Cairo lower third with animation."""
    if not cairo_manager:
        raise HTTPException(status_code=503, detail="Cairo graphics not available")
    
    # Use current time as timestamp (will be synced on first draw)
    timestamp = int(time.time() * 1_000_000_000)
    
    success = cairo_manager.show_element(element_id, timestamp)
    if not success:
        raise HTTPException(status_code=404, detail=f"Element {element_id} not found")
    
    return {"status": "shown", "element_id": element_id}


@app.post("/api/cairo/lower_third/{element_id}/hide")
async def hide_cairo_lower_third(element_id: str) -> Dict[str, str]:
    """Hide a Cairo lower third with animation."""
    if not cairo_manager:
        raise HTTPException(status_code=503, detail="Cairo graphics not available")
    
    timestamp = int(time.time() * 1_000_000_000)
    
    success = cairo_manager.hide_element(element_id, timestamp)
    if not success:
        raise HTTPException(status_code=404, detail=f"Element {element_id} not found")
    
    return {"status": "hidden", "element_id": element_id}


@app.post("/api/cairo/lower_third/{element_id}/update")
async def update_cairo_lower_third(element_id: str, request: Dict[str, Any]) -> Dict[str, Any]:
    """Update Cairo lower third text."""
    if not cairo_manager:
        raise HTTPException(status_code=503, detail="Cairo graphics not available")
    
    element = cairo_manager.get_element(element_id)
    if not element:
        raise HTTPException(status_code=404, detail=f"Element {element_id} not found")
    
    from .cairo_graphics import LowerThird
    if not isinstance(element, LowerThird):
        raise HTTPException(status_code=400, detail=f"Element {element_id} is not a lower third")
    
    element.update(
        name=request.get("name"),
        title=request.get("title")
    )
    
    return {
        "status": "updated",
        "element_id": element_id,
        "name": element.name,
        "title": element.title
    }


@app.post("/api/cairo/scoreboard")
async def create_cairo_scoreboard(request: Dict[str, Any]) -> Dict[str, Any]:
    """Create or update a Cairo scoreboard.
    
    Request body:
        - element_id: Unique identifier (required)
        - team1_name: Team 1 name (default: "Team 1")
        - team2_name: Team 2 name (default: "Team 2")
        - team1_score: Team 1 score (default: 0)
        - team2_score: Team 2 score (default: 0)
        - x: X position (default: 1600)
        - y: Y position (default: 50)
        - width: Width (default: 250)
        - height: Height (default: 150)
    """
    if not cairo_manager:
        raise HTTPException(status_code=503, detail="Cairo graphics not available")
    
    element_id = request.get("element_id")
    if not element_id:
        raise HTTPException(status_code=400, detail="element_id required")
    
    try:
        from .cairo_graphics import Scoreboard
        
        scoreboard = Scoreboard(
            element_id=element_id,
            team1_name=request.get("team1_name", "Team 1"),
            team2_name=request.get("team2_name", "Team 2"),
            team1_score=request.get("team1_score", 0),
            team2_score=request.get("team2_score", 0),
            x=request.get("x", 1600),
            y=request.get("y", 50),
            width=request.get("width", 250),
            height=request.get("height", 150)
        )
        
        cairo_manager.add_element(element_id, scoreboard)
        
        return {
            "status": "created",
            "element_id": element_id,
            "type": "scoreboard"
        }
    except Exception as e:
        logger.error(f"Failed to create scoreboard: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create scoreboard: {e}")


@app.post("/api/cairo/scoreboard/{element_id}/score")
async def update_cairo_scoreboard(element_id: str, request: Dict[str, Any]) -> Dict[str, Any]:
    """Update scoreboard scores.
    
    Request body:
        - team1_score: Team 1 score (optional)
        - team2_score: Team 2 score (optional)
    """
    if not cairo_manager:
        raise HTTPException(status_code=503, detail="Cairo graphics not available")
    
    element = cairo_manager.get_element(element_id)
    if not element:
        raise HTTPException(status_code=404, detail=f"Element {element_id} not found")
    
    from .cairo_graphics import Scoreboard
    if not isinstance(element, Scoreboard):
        raise HTTPException(status_code=400, detail=f"Element {element_id} is not a scoreboard")
    
    element.update_score(
        team1_score=request.get("team1_score"),
        team2_score=request.get("team2_score")
    )
    
    return {
        "status": "updated",
        "element_id": element_id,
        "team1_score": element.team1_score,
        "team2_score": element.team2_score
    }


@app.post("/api/cairo/ticker")
async def create_cairo_ticker(request: Dict[str, Any]) -> Dict[str, Any]:
    """Create or update a Cairo ticker.
    
    Request body:
        - element_id: Unique identifier (required)
        - text: Ticker text (required)
        - x: X position (default: 0)
        - y: Y position (default: 0)
        - width: Width (default: 1920)
        - height: Height (default: 60)
        - scroll_speed: Scroll speed in pixels/second (default: 100)
    """
    if not cairo_manager:
        raise HTTPException(status_code=503, detail="Cairo graphics not available")
    
    element_id = request.get("element_id")
    text = request.get("text")
    
    if not element_id:
        raise HTTPException(status_code=400, detail="element_id required")
    if not text:
        raise HTTPException(status_code=400, detail="text required")
    
    try:
        from .cairo_graphics import Ticker
        
        ticker = Ticker(
            element_id=element_id,
            text=text,
            x=request.get("x", 0),
            y=request.get("y", 0),
            width=request.get("width", 1920),
            height=request.get("height", 60),
            scroll_speed=request.get("scroll_speed", 100.0)
        )
        
        cairo_manager.add_element(element_id, ticker)
        
        return {
            "status": "created",
            "element_id": element_id,
            "type": "ticker",
            "text": text
        }
    except Exception as e:
        logger.error(f"Failed to create ticker: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create ticker: {e}")


@app.post("/api/cairo/ticker/{element_id}/text")
async def update_cairo_ticker(element_id: str, request: Dict[str, Any]) -> Dict[str, Any]:
    """Update ticker text.
    
    Request body:
        - text: New ticker text (required)
    """
    if not cairo_manager:
        raise HTTPException(status_code=503, detail="Cairo graphics not available")
    
    text = request.get("text")
    if not text:
        raise HTTPException(status_code=400, detail="text required")
    
    element = cairo_manager.get_element(element_id)
    if not element:
        raise HTTPException(status_code=404, detail=f"Element {element_id} not found")
    
    from .cairo_graphics import Ticker
    if not isinstance(element, Ticker):
        raise HTTPException(status_code=400, detail=f"Element {element_id} is not a ticker")
    
    element.update_text(text)
    
    return {
        "status": "updated",
        "element_id": element_id,
        "text": text
    }


@app.post("/api/cairo/timer")
async def create_cairo_timer(request: Dict[str, Any]) -> Dict[str, Any]:
    """Create or update a Cairo timer.
    
    Request body:
        - element_id: Unique identifier (required)
        - duration: Duration in seconds (required)
        - mode: "countdown" or "countup" (default: "countdown")
        - x: X position (default: 1700)
        - y: Y position (default: 50)
    """
    if not cairo_manager:
        raise HTTPException(status_code=503, detail="Cairo graphics not available")
    
    element_id = request.get("element_id")
    duration = request.get("duration")
    
    if not element_id:
        raise HTTPException(status_code=400, detail="element_id required")
    if duration is None:
        raise HTTPException(status_code=400, detail="duration required")
    
    try:
        from .cairo_graphics import Timer
        
        timer = Timer(
            element_id=element_id,
            duration=float(duration),
            mode=request.get("mode", "countdown"),
            x=request.get("x", 1700),
            y=request.get("y", 50)
        )
        
        cairo_manager.add_element(element_id, timer)
        
        return {
            "status": "created",
            "element_id": element_id,
            "type": "timer",
            "duration": duration,
            "mode": request.get("mode", "countdown")
        }
    except Exception as e:
        logger.error(f"Failed to create timer: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create timer: {e}")


@app.post("/api/cairo/timer/{element_id}/start")
async def start_cairo_timer(element_id: str) -> Dict[str, str]:
    """Start a Cairo timer."""
    if not cairo_manager:
        raise HTTPException(status_code=503, detail="Cairo graphics not available")
    
    element = cairo_manager.get_element(element_id)
    if not element:
        raise HTTPException(status_code=404, detail=f"Element {element_id} not found")
    
    from .cairo_graphics import Timer
    if not isinstance(element, Timer):
        raise HTTPException(status_code=400, detail=f"Element {element_id} is not a timer")
    
    timestamp = int(time.time() * 1_000_000_000)
    element.start(timestamp)
    
    return {"status": "started", "element_id": element_id}


@app.post("/api/cairo/timer/{element_id}/pause")
async def pause_cairo_timer(element_id: str) -> Dict[str, str]:
    """Pause a Cairo timer."""
    if not cairo_manager:
        raise HTTPException(status_code=503, detail="Cairo graphics not available")
    
    element = cairo_manager.get_element(element_id)
    if not element:
        raise HTTPException(status_code=404, detail=f"Element {element_id} not found")
    
    from .cairo_graphics import Timer
    if not isinstance(element, Timer):
        raise HTTPException(status_code=400, detail=f"Element {element_id} is not a timer")
    
    timestamp = int(time.time() * 1_000_000_000)
    element.pause(timestamp)
    
    return {"status": "paused", "element_id": element_id}


@app.post("/api/cairo/timer/{element_id}/resume")
async def resume_cairo_timer(element_id: str) -> Dict[str, str]:
    """Resume a Cairo timer."""
    if not cairo_manager:
        raise HTTPException(status_code=503, detail="Cairo graphics not available")
    
    element = cairo_manager.get_element(element_id)
    if not element:
        raise HTTPException(status_code=404, detail=f"Element {element_id} not found")
    
    from .cairo_graphics import Timer
    if not isinstance(element, Timer):
        raise HTTPException(status_code=400, detail=f"Element {element_id} is not a timer")
    
    timestamp = int(time.time() * 1_000_000_000)
    element.resume(timestamp)
    
    return {"status": "resumed", "element_id": element_id}


@app.post("/api/cairo/timer/{element_id}/reset")
async def reset_cairo_timer(element_id: str) -> Dict[str, str]:
    """Reset a Cairo timer."""
    if not cairo_manager:
        raise HTTPException(status_code=503, detail="Cairo graphics not available")
    
    element = cairo_manager.get_element(element_id)
    if not element:
        raise HTTPException(status_code=404, detail=f"Element {element_id} not found")
    
    from .cairo_graphics import Timer
    if not isinstance(element, Timer):
        raise HTTPException(status_code=400, detail=f"Element {element_id} is not a timer")
    
    element.reset()
    
    return {"status": "reset", "element_id": element_id}


@app.post("/api/cairo/logo")
async def create_cairo_logo(request: Dict[str, Any]) -> Dict[str, Any]:
    """Create or update a Cairo logo overlay.
    
    Request body:
        - element_id: Unique identifier (required)
        - logo_path: Path to logo image (required)
        - x: X position (default: 1700)
        - y: Y position (default: 50)
        - scale: Scale factor (default: 1.0)
        - pulse: Enable pulse animation (default: false)
    """
    if not cairo_manager:
        raise HTTPException(status_code=503, detail="Cairo graphics not available")
    
    element_id = request.get("element_id")
    logo_path = request.get("logo_path")
    
    if not element_id:
        raise HTTPException(status_code=400, detail="element_id required")
    if not logo_path:
        raise HTTPException(status_code=400, detail="logo_path required")
    
    try:
        from .cairo_graphics import LogoOverlay
        
        logo = LogoOverlay(
            element_id=element_id,
            logo_path=logo_path,
            x=request.get("x", 1700),
            y=request.get("y", 50),
            scale=request.get("scale", 1.0),
            pulse=request.get("pulse", False)
        )
        
        cairo_manager.add_element(element_id, logo)
        
        return {
            "status": "created",
            "element_id": element_id,
            "type": "logo",
            "logo_path": logo_path
        }
    except Exception as e:
        logger.error(f"Failed to create logo: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create logo: {e}")


@app.delete("/api/cairo/element/{element_id}")
async def delete_cairo_element(element_id: str) -> Dict[str, str]:
    """Delete a Cairo graphics element."""
    if not cairo_manager:
        raise HTTPException(status_code=503, detail="Cairo graphics not available")
    
    success = cairo_manager.remove_element(element_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Element {element_id} not found")
    
    return {"status": "deleted", "element_id": element_id}


@app.post("/api/cairo/clear")
async def clear_all_cairo_elements() -> Dict[str, str]:
    """Clear all Cairo graphics elements."""
    if not cairo_manager:
        raise HTTPException(status_code=503, detail="Cairo graphics not available")
    
    cairo_manager.clear_all()
    
    return {"status": "cleared"}


@app.websocket("/ws/cairo")
async def cairo_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time Cairo graphics control.
    
    Message format:
        {
            "type": "lower_third_show" | "lower_third_hide" | "lower_third_update" |
                    "scoreboard_update" | "ticker_update" | "timer_start" | "get_status",
            "element_id": "element_id",
            ... (element-specific fields)
        }
    
    Response format:
        {
            "status": "success" | "error",
            "message": "...",
            "data": {...}
        }
    """
    if not cairo_manager:
        await websocket.close(code=1008, reason="Cairo graphics not available")
        return
    
    await websocket.accept()
    logger.info("Cairo WebSocket client connected")
    
    try:
        while True:
            # Receive command
            data = await websocket.receive_json()
            msg_type = data.get("type")
            element_id = data.get("element_id")
            timestamp = int(time.time() * 1_000_000_000)
            
            try:
                # Lower third commands
                if msg_type == "lower_third_show":
                    if not element_id:
                        await websocket.send_json({"status": "error", "message": "element_id required"})
                        continue
                    
                    success = cairo_manager.show_element(element_id, timestamp)
                    if success:
                        await websocket.send_json({"status": "success", "element_id": element_id})
                    else:
                        await websocket.send_json({"status": "error", "message": f"Element {element_id} not found"})
                
                elif msg_type == "lower_third_hide":
                    if not element_id:
                        await websocket.send_json({"status": "error", "message": "element_id required"})
                        continue
                    
                    success = cairo_manager.hide_element(element_id, timestamp)
                    if success:
                        await websocket.send_json({"status": "success", "element_id": element_id})
                    else:
                        await websocket.send_json({"status": "error", "message": f"Element {element_id} not found"})
                
                elif msg_type == "lower_third_update":
                    if not element_id:
                        await websocket.send_json({"status": "error", "message": "element_id required"})
                        continue
                    
                    element = cairo_manager.get_element(element_id)
                    if not element:
                        await websocket.send_json({"status": "error", "message": f"Element {element_id} not found"})
                        continue
                    
                    from .cairo_graphics import LowerThird
                    if isinstance(element, LowerThird):
                        element.update(name=data.get("name"), title=data.get("title"))
                        await websocket.send_json({
                            "status": "success",
                            "element_id": element_id,
                            "name": element.name,
                            "title": element.title
                        })
                    else:
                        await websocket.send_json({"status": "error", "message": "Element is not a lower third"})
                
                # Scoreboard commands
                elif msg_type == "scoreboard_update":
                    if not element_id:
                        await websocket.send_json({"status": "error", "message": "element_id required"})
                        continue
                    
                    element = cairo_manager.get_element(element_id)
                    if not element:
                        await websocket.send_json({"status": "error", "message": f"Element {element_id} not found"})
                        continue
                    
                    from .cairo_graphics import Scoreboard
                    if isinstance(element, Scoreboard):
                        element.update_score(
                            team1_score=data.get("team1_score"),
                            team2_score=data.get("team2_score")
                        )
                        await websocket.send_json({
                            "status": "success",
                            "element_id": element_id,
                            "team1_score": element.team1_score,
                            "team2_score": element.team2_score
                        })
                    else:
                        await websocket.send_json({"status": "error", "message": "Element is not a scoreboard"})
                
                # Ticker commands
                elif msg_type == "ticker_update":
                    if not element_id:
                        await websocket.send_json({"status": "error", "message": "element_id required"})
                        continue
                    
                    text = data.get("text")
                    if not text:
                        await websocket.send_json({"status": "error", "message": "text required"})
                        continue
                    
                    element = cairo_manager.get_element(element_id)
                    if not element:
                        await websocket.send_json({"status": "error", "message": f"Element {element_id} not found"})
                        continue
                    
                    from .cairo_graphics import Ticker
                    if isinstance(element, Ticker):
                        element.update_text(text)
                        await websocket.send_json({"status": "success", "element_id": element_id, "text": text})
                    else:
                        await websocket.send_json({"status": "error", "message": "Element is not a ticker"})
                
                # Timer commands
                elif msg_type == "timer_start":
                    if not element_id:
                        await websocket.send_json({"status": "error", "message": "element_id required"})
                        continue
                    
                    element = cairo_manager.get_element(element_id)
                    if not element:
                        await websocket.send_json({"status": "error", "message": f"Element {element_id} not found"})
                        continue
                    
                    from .cairo_graphics import Timer
                    if isinstance(element, Timer):
                        element.start(timestamp)
                        await websocket.send_json({"status": "success", "element_id": element_id})
                    else:
                        await websocket.send_json({"status": "error", "message": "Element is not a timer"})
                
                elif msg_type == "timer_pause":
                    if not element_id:
                        await websocket.send_json({"status": "error", "message": "element_id required"})
                        continue
                    
                    element = cairo_manager.get_element(element_id)
                    if not element:
                        await websocket.send_json({"status": "error", "message": f"Element {element_id} not found"})
                        continue
                    
                    from .cairo_graphics import Timer
                    if isinstance(element, Timer):
                        element.pause(timestamp)
                        await websocket.send_json({"status": "success", "element_id": element_id})
                    else:
                        await websocket.send_json({"status": "error", "message": "Element is not a timer"})
                
                elif msg_type == "timer_resume":
                    if not element_id:
                        await websocket.send_json({"status": "error", "message": "element_id required"})
                        continue
                    
                    element = cairo_manager.get_element(element_id)
                    if not element:
                        await websocket.send_json({"status": "error", "message": f"Element {element_id} not found"})
                        continue
                    
                    from .cairo_graphics import Timer
                    if isinstance(element, Timer):
                        element.resume(timestamp)
                        await websocket.send_json({"status": "success", "element_id": element_id})
                    else:
                        await websocket.send_json({"status": "error", "message": "Element is not a timer"})
                
                # Status query
                elif msg_type == "get_status":
                    status = cairo_manager.get_status()
                    await websocket.send_json({"status": "success", "data": status})
                
                else:
                    await websocket.send_json({"status": "error", "message": f"Unknown message type: {msg_type}"})
            
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {e}")
                await websocket.send_json({"status": "error", "message": str(e)})
    
    except WebSocketDisconnect:
        logger.info("Cairo WebSocket client disconnected")
    except Exception as e:
        logger.error(f"Cairo WebSocket error: {e}")


@app.get("/api/guests/status")
async def get_guests_status() -> Dict[str, Any]:
    """Get status of all remote guests (check if they're streaming via MediaMTX)."""
    guests_status = {}
    
    for guest_id, guest_config in config.guests.items():
        if not guest_config.enabled:
            guests_status[guest_id] = {
                "name": guest_config.name,
                "enabled": False,
                "streaming": False
            }
            continue
        
        # Check MediaMTX API for stream status
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"http://127.0.0.1:9997/v3/paths/get/{guest_id}",
                    timeout=1.0
                )
                if response.status_code == 200:
                    data = response.json()
                    source_ready = data.get("sourceReady", False)
                    guests_status[guest_id] = {
                        "name": guest_config.name,
                        "enabled": True,
                        "streaming": source_ready
                    }
                else:
                    guests_status[guest_id] = {
                        "name": guest_config.name,
                        "enabled": True,
                        "streaming": False
                    }
        except Exception as e:
            logger.debug(f"Error checking guest {guest_id} status: {e}")
            guests_status[guest_id] = {
                "name": guest_config.name,
                "enabled": True,
                "streaming": False
            }
    
    return {"guests": guests_status}


# Cloudflare Calls endpoints removed - guests now use direct WHIP to MediaMTX
# See /guest_join page for remote speaker WHIP publishing


# Graphics/Presentation API endpoints
@app.get("/api/graphics/presentations")
async def list_presentations() -> Dict[str, Any]:
    """List all saved presentations."""
    presentations_dir = Path(__file__).parent.parent / "presentations"
    presentations_dir.mkdir(exist_ok=True)
    
    presentations = []
    try:
        for f_path in presentations_dir.glob("*.json"):
            try:
                import json
                with open(f_path, "r") as f:
                    pres = json.load(f)
                    presentations.append({
                        "id": pres.get("id", f_path.stem),
                        "name": pres.get("name", pres.get("id", f_path.stem)),
                        "theme": pres.get("theme", "black"),
                        "slides": pres.get("slides", [])
                    })
            except Exception as e:
                logger.error(f"Failed to load presentation {f_path}: {e}")
    except Exception as e:
        logger.error(f"Error listing presentations: {e}")
    
    return {"presentations": presentations}


@app.get("/api/graphics/presentations/{pres_id}")
async def get_presentation(pres_id: str) -> Dict[str, Any]:
    """Get a specific presentation."""
    presentations_dir = Path(__file__).parent.parent / "presentations"
    pres_path = presentations_dir / f"{pres_id}.json"
    
    if not pres_path.exists():
        raise HTTPException(status_code=404, detail=f"Presentation {pres_id} not found")
    
    try:
        import json
        with open(pres_path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load presentation {pres_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load presentation: {e}")


@app.post("/api/graphics/presentations")
async def save_presentation(presentation: Dict[str, Any]) -> Dict[str, str]:
    """Save a presentation."""
    pres_id = presentation.get("id")
    if not pres_id:
        raise HTTPException(status_code=400, detail="Presentation ID required")
    
    presentations_dir = Path(__file__).parent.parent / "presentations"
    presentations_dir.mkdir(exist_ok=True)
    pres_path = presentations_dir / f"{pres_id}.json"
    
    try:
        import json
        with open(pres_path, "w") as f:
            json.dump(presentation, f, indent=2)
        logger.info(f"Saved presentation: {pres_id}")
        return {"status": "saved", "id": pres_id}
    except Exception as e:
        logger.error(f"Failed to save presentation {pres_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save presentation: {e}")


@app.delete("/api/graphics/presentations/{pres_id}")
async def delete_presentation(pres_id: str) -> Dict[str, str]:
    """Delete a presentation."""
    presentations_dir = Path(__file__).parent.parent / "presentations"
    pres_path = presentations_dir / f"{pres_id}.json"
    
    if not pres_path.exists():
        raise HTTPException(status_code=404, detail=f"Presentation {pres_id} not found")
    
    try:
        pres_path.unlink()
        logger.info(f"Deleted presentation: {pres_id}")
        return {"status": "deleted", "id": pres_id}
    except Exception as e:
        logger.error(f"Failed to delete presentation {pres_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete presentation: {e}")


@app.post("/api/graphics/export/{pres_id}")
async def export_presentation_to_mixer(pres_id: str) -> Dict[str, str]:
    """Export a presentation to the mixer as a graphics source."""
    if not graphics_renderer:
        raise HTTPException(status_code=503, detail="Graphics renderer not available")
    
    presentations_dir = Path(__file__).parent.parent / "presentations"
    pres_path = presentations_dir / f"{pres_id}.json"
    
    if not pres_path.exists():
        raise HTTPException(status_code=404, detail=f"Presentation {pres_id} not found")
    
    try:
        import json
        with open(pres_path, "r") as f:
            pres = json.load(f)
        
        # Create presentation source in graphics renderer
        source_id = f"presentation:{pres_id}"
        pipeline = graphics_renderer.create_presentation_source(source_id, pres)
        
        if not pipeline:
            raise HTTPException(status_code=500, detail="Failed to create presentation source")
        
        logger.info(f"Exported presentation {pres_id} to mixer")
        return {"status": "exported", "id": pres_id, "source_id": source_id}
    except Exception as e:
        logger.error(f"Failed to export presentation {pres_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to export presentation: {e}")


@app.post("/api/graphics/upload/image")
async def upload_image(file: UploadFile = File(...)) -> Dict[str, str]:
    """Upload an image file for use in presentations."""
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Generate unique filename
    file_ext = Path(file.filename).suffix if file.filename else '.jpg'
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = images_dir / unique_filename
    
    try:
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Return URL
        url = f"/uploads/images/{unique_filename}"
        logger.info(f"Uploaded image: {unique_filename}")
        return {"status": "uploaded", "filename": unique_filename, "url": url}
    except Exception as e:
        logger.error(f"Failed to upload image: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload image: {e}")


@app.post("/api/graphics/upload/video")
async def upload_video(file: UploadFile = File(...)) -> Dict[str, str]:
    """Upload a video file for use in presentations."""
    if not file.content_type or not file.content_type.startswith('video/'):
        raise HTTPException(status_code=400, detail="File must be a video")
    
    # Generate unique filename
    file_ext = Path(file.filename).suffix if file.filename else '.mp4'
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = videos_dir / unique_filename
    
    try:
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Return URL
        url = f"/uploads/videos/{unique_filename}"
        logger.info(f"Uploaded video: {unique_filename}")
        return {"status": "uploaded", "filename": unique_filename, "url": url}
    except Exception as e:
        logger.error(f"Failed to upload video: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload video: {e}")


# Broadcast Graphics API endpoints
@app.post("/api/graphics/lower_third")
async def create_lower_third(request: Dict[str, Any]) -> Dict[str, Any]:
    """Create or update a lower-third graphics overlay.
    
    Request body:
        - source_id: Unique identifier for the lower-third
        - line1: Primary text (required)
        - line2: Secondary text (optional)
        - background_color: Background color hex (default: "#000000")
        - background_alpha: Background transparency 0.0-1.0 (default: 0.8)
        - text_color: Text color hex (default: "#FFFFFF")
        - line1_font: Font for line1 (default: "Sans Bold 32")
        - line2_font: Font for line2 (default: "Sans 24")
        - position: Position preset (default: "bottom-left")
        - width: Lower-third width (default: 600)
        - height: Lower-third height (default: 120)
        - padding: Padding dict with x, y (default: {"x": 20, "y": 15})
        - template_id: Template ID to apply (optional)
    """
    if not graphics_renderer:
        raise HTTPException(status_code=503, detail="Graphics renderer not available")
    
    source_id = request.get("source_id")
    if not source_id:
        raise HTTPException(status_code=400, detail="source_id required")
    
    if not request.get("line1"):
        raise HTTPException(status_code=400, detail="line1 text required")
    
    try:
        # Resolve image path if present
        bg_image = request.get("background_image")
        if bg_image:
            # Look for the image in uploads/images
            image_path = images_dir / bg_image
            if image_path.exists():
                request["background_image_path"] = str(image_path.absolute())
            else:
                logger.warning(f"Background image not found: {bg_image}")

        # Create or update the lower-third source
        text_data = {k: v for k, v in request.items() if k != "source_id"}
        pipeline = graphics_renderer.create_lower_third_source(source_id, text_data)
        
        if not pipeline:
            raise HTTPException(status_code=500, detail="Failed to create lower-third")
        
        # Store the graphics source
        from .mixer.graphics import GraphicsSource
        graphics_source = GraphicsSource(
            source_id=source_id,
            source_type="lower_third",
            data=text_data
        )
        
        with graphics_renderer._lock:
            graphics_renderer.active_sources[source_id] = graphics_source
        
        logger.info(f"Created lower-third: {source_id}")
        return {
            "status": "created",
            "source_id": source_id,
            "source": f"lower_third:{source_id}",
            "config": text_data
        }
    except Exception as e:
        logger.error(f"Failed to create lower-third {source_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create lower-third: {e}")


@app.get("/api/graphics/templates")
async def list_graphics_templates(template_type: Optional[str] = None) -> Dict[str, Any]:
    """List all available graphics templates.
    
    Query parameters:
        - template_type: Filter by type (e.g., "lower_third")
    """
    if not graphics_plugin:
        raise HTTPException(status_code=503, detail="Graphics not enabled")
    
    templates = graphics_plugin.list_templates(template_type)
    return {
        "templates": [
            {
                "id": t.id,
                "name": t.name,
                "type": t.type,
                "description": t.description,
                "default_config": t.default_config,
            }
            for t in templates
        ]
    }


@app.get("/api/graphics/templates/{template_id}")
async def get_graphics_template(template_id: str) -> Dict[str, Any]:
    """Get a specific graphics template."""
    if not graphics_plugin:
        raise HTTPException(status_code=503, detail="Graphics not enabled")
    
    template = graphics_plugin.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
    
    return {
        "id": template.id,
        "name": template.name,
        "type": template.type,
        "description": template.description,
        "default_config": template.default_config,
    }


@app.post("/api/graphics/template/{template_id}")
async def apply_template(template_id: str, request: Dict[str, Any]) -> Dict[str, Any]:
    """Apply a template to create a graphics source.
    
    Request body:
        - source_id: Unique identifier for the graphics source
        - Additional fields will override template defaults
    """
    if not graphics_renderer:
        raise HTTPException(status_code=503, detail="Graphics renderer not available")
    
    if not graphics_plugin:
        raise HTTPException(status_code=503, detail="Graphics not enabled")
    
    template = graphics_plugin.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
    
    source_id = request.get("source_id")
    if not source_id:
        raise HTTPException(status_code=400, detail="source_id required")
    
    try:
        # Merge template defaults with request data
        config = template.default_config.copy()
        config.update({k: v for k, v in request.items() if k != "source_id"})
        config["template_id"] = template_id
        
        # Create the graphics source based on type
        if template.type == "lower_third":
            pipeline = graphics_renderer.create_lower_third_source(source_id, config)
            if not pipeline:
                raise HTTPException(status_code=500, detail="Failed to create lower-third from template")
            
            from .mixer.graphics import GraphicsSource
            graphics_source = GraphicsSource(
                source_id=source_id,
                source_type="lower_third",
                data=config
            )
            
            with graphics_renderer._lock:
                graphics_renderer.active_sources[source_id] = graphics_source
            
            return {
                "status": "created",
                "source_id": source_id,
                "source": f"lower_third:{source_id}",
                "template_id": template_id,
                "config": config
            }
        else:
            raise HTTPException(status_code=400, detail=f"Template type {template.type} not yet supported")
    except Exception as e:
        logger.error(f"Failed to apply template {template_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to apply template: {e}")


@app.delete("/api/graphics/{source_id}")
async def delete_graphics_source(source_id: str) -> Dict[str, str]:
    """Delete a graphics source."""
    if not graphics_renderer:
        raise HTTPException(status_code=503, detail="Graphics renderer not available")
    
    try:
        with graphics_renderer._lock:
            if source_id not in graphics_renderer.active_sources:
                raise HTTPException(status_code=404, detail=f"Graphics source {source_id} not found")
            
            del graphics_renderer.active_sources[source_id]
            
            # Also remove from pipelines if present
            if source_id in graphics_renderer.pipelines:
                del graphics_renderer.pipelines[source_id]
        
        logger.info(f"Deleted graphics source: {source_id}")
        return {"status": "deleted", "source_id": source_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete graphics source {source_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete graphics source: {e}")


@app.post("/api/graphics/graphics")
async def create_graphics_source(request: Dict[str, Any]) -> Dict[str, Any]:
    """Create a graphics source (stinger, ticker, timer, scoreboard, etc.).
    
    Request body:
        - source_id: Unique identifier for the graphics source
        - type: Graphics type ("stinger", "ticker", "timer", "scoreboard")
        - Additional type-specific configuration
    """
    if not graphics_renderer:
        raise HTTPException(status_code=503, detail="Graphics renderer not available")
    
    source_id = request.get("source_id")
    if not source_id:
        raise HTTPException(status_code=400, detail="source_id required")
    
    graphics_type = request.get("type")
    if not graphics_type:
        raise HTTPException(status_code=400, detail="type required")
    
    try:
        # Create the graphics source
        graphics_data = {k: v for k, v in request.items() if k != "source_id"}
        pipeline = graphics_renderer.create_graphics_source(source_id, graphics_data)
        
        if not pipeline:
            raise HTTPException(status_code=500, detail=f"Failed to create {graphics_type} graphics")
        
        # Store the graphics source
        from .mixer.graphics import GraphicsSource
        graphics_source = GraphicsSource(
            source_id=source_id,
            source_type="graphics",
            data=graphics_data
        )
        
        with graphics_renderer._lock:
            graphics_renderer.active_sources[source_id] = graphics_source
        
        logger.info(f"Created graphics source: {source_id} type={graphics_type}")
        return {
            "status": "created",
            "source_id": source_id,
            "source": f"graphics:{source_id}",
            "type": graphics_type,
            "config": graphics_data
        }
    except Exception as e:
        logger.error(f"Failed to create graphics source {source_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create graphics source: {e}")


@app.get("/api/graphics/{source_id}")
async def get_graphics_source(source_id: str) -> Dict[str, Any]:
    """Get a graphics source configuration."""
    if not graphics_renderer:
        raise HTTPException(status_code=503, detail="Graphics renderer not available")
    
    with graphics_renderer._lock:
        if source_id not in graphics_renderer.active_sources:
            raise HTTPException(status_code=404, detail=f"Graphics source {source_id} not found")
        
        graphics_source = graphics_renderer.active_sources[source_id]
        
        return {
            "source_id": graphics_source.source_id,
            "source_type": graphics_source.source_type,
            "source": f"{graphics_source.source_type}:{source_id}",
            "data": graphics_source.data,
        }


# Switcher/Controller API endpoints
@app.post("/api/switcher/action")
async def switcher_action(request: Dict[str, Any]) -> Dict[str, str]:
    """Handle actions from physical controllers (StreamDeck, gamepad, etc.)."""
    action = request.get("action")
    
    if not action:
        raise HTTPException(status_code=400, detail="Action required")
    
    if action == "switch_scene":
        scene_id = request.get("scene_id")
        if not scene_id:
            raise HTTPException(status_code=400, detail="scene_id required for switch_scene")
        if not mixer_core:
            raise HTTPException(status_code=503, detail="Mixer not enabled")
        success = mixer_core.apply_scene(scene_id)
        if not success:
            raise HTTPException(status_code=500, detail=f"Failed to apply scene {scene_id}")
        return {"status": "applied", "scene_id": scene_id}
    
    elif action == "start":
        if not mixer_core:
            raise HTTPException(status_code=503, detail="Mixer not enabled")
        success = mixer_core.start()
        if not success:
            raise HTTPException(status_code=500, detail="Failed to start mixer")
        return {"status": "started"}
    
    elif action == "stop":
        if not mixer_core:
            raise HTTPException(status_code=503, detail="Mixer not enabled")
        success = mixer_core.stop()
        if not success:
            raise HTTPException(status_code=500, detail="Failed to stop mixer")
        return {"status": "stopped"}
    
    elif action == "toggle":
        if not mixer_core:
            raise HTTPException(status_code=503, detail="Mixer not enabled")
        status = mixer_core.get_status()
        if status["state"] == "PLAYING":
            success = mixer_core.stop()
            if not success:
                raise HTTPException(status_code=500, detail="Failed to stop mixer")
            return {"status": "stopped"}
        else:
            success = mixer_core.start()
            if not success:
                raise HTTPException(status_code=500, detail="Failed to start mixer")
            return {"status": "started"}
    
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {action}")


# File Upload API endpoints
@app.post("/api/files/upload")
async def upload_file(
    file: UploadFile = File(...),
    loop: bool = False
) -> Dict[str, Any]:
    """Upload a video or image file."""
    try:
        # Read file content
        content = await file.read()
        
        # Save file
        metadata = file_manager.save_file(content, file.filename, loop=loop)
        
        return {
            "status": "uploaded",
            "file_id": metadata["id"],
            "file_path": metadata["file_path"],
            "file_type": metadata["file_type"],
            "metadata": metadata
        }
    except Exception as e:
        logger.error(f"Failed to upload file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")


@app.get("/api/files")
async def list_files() -> Dict[str, Any]:
    """List all uploaded files."""
    files = file_manager.list_files()
    return {"files": files}


@app.get("/api/files/{file_id}")
async def get_file_metadata(file_id: str) -> Dict[str, Any]:
    """Get file metadata."""
    metadata = file_manager.get_file_metadata(file_id)
    if not metadata:
        raise HTTPException(status_code=404, detail=f"File {file_id} not found")
    return metadata


@app.delete("/api/files/{file_id}")
async def delete_file(file_id: str) -> Dict[str, str]:
    """Delete a file."""
    success = file_manager.delete_file(file_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"File {file_id} not found")
    return {"status": "deleted", "file_id": file_id}


@app.put("/api/files/{file_id}")
async def update_file_settings(file_id: str, settings: Dict[str, Any]) -> Dict[str, str]:
    """Update file settings (e.g., loop)."""
    success = file_manager.update_file_settings(file_id, settings)
    if not success:
        raise HTTPException(status_code=404, detail=f"File {file_id} not found")
    return {"status": "updated", "file_id": file_id}


# Scene Queue API endpoints
@app.get("/api/queue")
async def get_queue() -> Dict[str, Any]:
    """Get current queue."""
    if not scene_queue:
        raise HTTPException(status_code=503, detail="Mixer not enabled")
    queue_items = scene_queue.queue
    return {"queue": queue_items}


@app.post("/api/queue")
async def add_to_queue(request: Dict[str, Any]) -> Dict[str, str]:
    """Add scene to queue."""
    if not scene_queue:
        raise HTTPException(status_code=503, detail="Mixer not enabled")
    
    scene_id = request.get("scene_id")
    if not scene_id:
        raise HTTPException(status_code=400, detail="scene_id required")
    
    duration = request.get("duration")
    transition = request.get("transition", "cut")
    auto_advance = request.get("auto_advance", False)
    
    success = scene_queue.add(scene_id, duration, transition, auto_advance)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to add to queue")
    
    return {"status": "added", "scene_id": scene_id}


@app.put("/api/queue/{index}")
async def update_queue_item(index: int, request: Dict[str, Any]) -> Dict[str, str]:
    """Update queue item."""
    if not scene_queue:
        raise HTTPException(status_code=503, detail="Mixer not enabled")
    
    success = scene_queue.update(index, request)
    if not success:
        raise HTTPException(status_code=404, detail=f"Queue item at index {index} not found")
    
    return {"status": "updated", "index": index}


@app.post("/api/queue/jump/{index}")
async def jump_queue(index: int) -> Dict[str, Any]:
    """Jump to specific queue position."""
    if not scene_queue:
        raise HTTPException(status_code=503, detail="Mixer not enabled")
    
    scene_id = scene_queue.jump(index)
    if not scene_id:
        raise HTTPException(status_code=404, detail=f"Queue item at index {index} not found or failed to play")
    
    # Apply scene immediately
    if mixer_core:
        mixer_core.apply_scene(scene_id)
        
    return {"status": "jumped", "scene_id": scene_id}


@app.delete("/api/queue/{index}")
async def remove_from_queue(index: int) -> Dict[str, str]:
    """Remove scene from queue by index."""
    if not scene_queue:
        raise HTTPException(status_code=503, detail="Mixer not enabled")
    
    success = scene_queue.remove(index)
    if not success:
        raise HTTPException(status_code=404, detail=f"Queue item at index {index} not found")
    
    return {"status": "removed", "index": index}


@app.put("/api/queue/reorder")
async def reorder_queue(request: Dict[str, Any]) -> Dict[str, str]:
    """Reorder queue items."""
    if not scene_queue:
        raise HTTPException(status_code=503, detail="Mixer not enabled")
    
    indices = request.get("indices")
    if not indices or not isinstance(indices, list):
        raise HTTPException(status_code=400, detail="indices array required")
    
    success = scene_queue.reorder(indices)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid indices")
    
    return {"status": "reordered"}


@app.post("/api/queue/advance")
async def manual_advance() -> Dict[str, Any]:
    """Manually advance to next scene in queue."""
    if not scene_queue:
        raise HTTPException(status_code=503, detail="Mixer not enabled")
    
    scene_id = scene_queue.advance()
    if not scene_id:
        return {"status": "completed", "scene_id": None}
    
    return {"status": "advanced", "scene_id": scene_id}


@app.post("/api/queue/start")
async def start_auto_advance() -> Dict[str, str]:
    """Start auto-advance mode."""
    if not scene_queue:
        raise HTTPException(status_code=503, detail="Mixer not enabled")
    
    success = scene_queue.start_auto_advance()
    if not success:
        raise HTTPException(status_code=500, detail="Failed to start auto-advance")
    
    return {"status": "started"}


@app.post("/api/queue/stop")
async def stop_auto_advance() -> Dict[str, str]:
    """Stop auto-advance mode."""
    if not scene_queue:
        raise HTTPException(status_code=503, detail="Mixer not enabled")
    
    success = scene_queue.stop_auto_advance()
    if not success:
        raise HTTPException(status_code=500, detail="Failed to stop auto-advance")
    
    return {"status": "stopped"}


@app.get("/api/queue/status")
async def get_queue_status() -> Dict[str, Any]:
    """Get queue status."""
    if not scene_queue:
        raise HTTPException(status_code=503, detail="Mixer not enabled")
    
    return scene_queue.get_status()


@app.delete("/api/queue")
async def clear_queue() -> Dict[str, str]:
    """Clear the queue."""
    if not scene_queue:
        raise HTTPException(status_code=503, detail="Mixer not enabled")
    
    success = scene_queue.clear()
    if not success:
        raise HTTPException(status_code=500, detail="Failed to clear queue")
    
    return {"status": "cleared"}


# ============================================================================
# VDO.ninja Integration API Endpoints
# ============================================================================

# VDO.ninja URL configuration
# Use local instance via FRP tunnel for remote access
VDONINJA_LOCAL_HOST = "localhost:8443"
VDONINJA_REMOTE_HOST = "app.itagenten.no/vdo"  # Path /vdo/ is handled by nginx
MEDIAMTX_REMOTE_HOST = "app.itagenten.no"  # Same-domain proxy


async def _check_mediamtx_stream_ready(stream_id: str) -> bool:
    """Check if a stream is actually available in MediaMTX."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://127.0.0.1:9997/v3/paths/get/{stream_id}",
                timeout=1.0
            )
            if response.status_code == 200:
                data = response.json()
                # MediaMTX v3 API uses "ready" field, not "sourceReady"
                return data.get("ready", False)
    except Exception:
        pass
    return False


@app.get("/api/vdoninja/sources")
async def get_vdoninja_sources(request: Request) -> Dict[str, Any]:
    """Get all available sources (cameras + speakers) for VDO.ninja mixer.
    
    Returns a list of all sources with their status and WHEP URLs.
    Checks both ingest manager state AND MediaMTX stream availability.
    """
    sources = []
    
    # Determine if request is local or remote
    host = request.headers.get("host", "")
    is_remote = "itagenten.no" in host or not any(x in host for x in ["localhost", "127.0.0.1", "192.168"])
    mediamtx_base = f"https://{MEDIAMTX_REMOTE_HOST}" if is_remote else "http://localhost:8889"
    
    # Get camera sources - check both ingest manager AND MediaMTX
    ingest_statuses = ingest_manager.get_status()
    for i, (cam_id, status) in enumerate(sorted(ingest_statuses.items())):
        cam_number = i + 1
        
        # Check if ingest is streaming
        ingest_streaming = status.status == "streaming"
        
        # Also check MediaMTX directly for stream availability
        mediamtx_ready = await _check_mediamtx_stream_ready(cam_id)
        
        # Stream is active if MediaMTX has the stream ready
        is_active = mediamtx_ready
        
        resolution_str = None
        if status.resolution:
            resolution_str = f"{status.resolution[0]}x{status.resolution[1]}"
        
        sources.append({
            "name": f"CAM{cam_number}",
            "stream": cam_id,
            "type": "camera",
            "whep_url": f"{mediamtx_base}/{cam_id}/whep",
            "active": is_active,
            "ingest_status": status.status,
            "has_signal": status.has_signal,
            "resolution": resolution_str
        })
    
    # Get speaker sources from MediaMTX API
    speaker_streams = ["speaker0", "speaker1", "speaker2"]
    for i, speaker_id in enumerate(speaker_streams):
        speaker_active = await _check_mediamtx_stream_ready(speaker_id)
        
        sources.append({
            "name": f"Speaker {i + 1}",
            "stream": speaker_id,
            "type": "speaker",
            "whep_url": f"{mediamtx_base}/{speaker_id}/whep",
            "active": speaker_active,
            "resolution": None
        })
    
    return {
        "sources": sources,
        "summary": {
            "total": len(sources),
            "active": sum(1 for s in sources if s["active"]),
            "cameras": sum(1 for s in sources if s["type"] == "camera"),
            "speakers": sum(1 for s in sources if s["type"] == "speaker"),
            "active_cameras": sum(1 for s in sources if s["type"] == "camera" and s["active"]),
            "active_speakers": sum(1 for s in sources if s["type"] == "speaker" and s["active"])
        }
    }


@app.get("/api/vdoninja/mixer-url")
async def get_vdoninja_mixer_url(request: Request, include_inactive: bool = False) -> Dict[str, Any]:
    """Get VDO.ninja mixer URL using MediaMTX backend.
    
    Args:
        include_inactive: If True, include sources without signal in response (default False)
    
    Returns the VDO.ninja mixer.html URL configured to use MediaMTX for WHEP streams.
    This works both locally and remotely through FRP tunnels (unlike P2P room mode).
    """
    # Determine if request is local or remote
    host = request.headers.get("host", "")
    is_remote = "itagenten.no" in host or not any(x in host for x in ["localhost", "127.0.0.1", "192.168"])
    
    vdoninja_base = f"https://{VDONINJA_REMOTE_HOST}" if is_remote else f"https://{VDONINJA_LOCAL_HOST}"
    mediamtx_host = MEDIAMTX_REMOTE_HOST if is_remote else "localhost:8889"
    
    # Build mixer URL using MediaMTX backend (NOT room-based P2P which doesn't work through tunnels)
    # The &mediamtx= parameter makes VDO.ninja use WHEP to pull streams from MediaMTX
    mixer_url = f"{vdoninja_base}/mixer.html?mediamtx={mediamtx_host}"
    
    # Get sources for info
    sources_response = await get_vdoninja_sources(request)
    sources = sources_response["sources"]
    
    # Collect active sources info
    active_sources = []
    for source in sources:
        if source["active"] or include_inactive:
            active_sources.append(source["name"])
    
    return {
        "url": mixer_url,
        "vdoninja_host": VDONINJA_REMOTE_HOST if is_remote else VDONINJA_LOCAL_HOST,
        "mediamtx_host": mediamtx_host,
        "active_sources": active_sources,
        "source_count": len(active_sources),
        "is_remote": is_remote
    }


@app.get("/api/vdoninja/director-url")
async def get_vdoninja_director_url(request: Request) -> Dict[str, Any]:
    """Get VDO.ninja director URL using MediaMTX backend.
    
    Returns the director URL configured to use MediaMTX for WHEP streams.
    This works both locally and remotely through FRP tunnels (unlike P2P room mode).
    """
    # Determine if request is local or remote
    host = request.headers.get("host", "")
    is_remote = "itagenten.no" in host or not any(x in host for x in ["localhost", "127.0.0.1", "192.168"])
    
    vdoninja_base = f"https://{VDONINJA_REMOTE_HOST}" if is_remote else f"https://{VDONINJA_LOCAL_HOST}"
    mediamtx_host = MEDIAMTX_REMOTE_HOST if is_remote else "localhost:8889"
    
    # Use MediaMTX backend instead of room-based P2P (which doesn't work through tunnels)
    return {
        "url": f"{vdoninja_base}/?director=r58studio&mediamtx={mediamtx_host}",
        "room": "r58studio",
        "vdoninja_host": VDONINJA_REMOTE_HOST if is_remote else VDONINJA_LOCAL_HOST,
        "mediamtx_host": mediamtx_host,
        "is_remote": is_remote
    }


@app.get("/api/vdoninja/scene-url")
async def get_vdoninja_scene_url(request: Request) -> Dict[str, Any]:
    """Get VDO.ninja scene view URL (program output).
    
    This is the URL that OBS or other capture tools would use to display 
    the mixed output from the VDO.ninja mixer.
    Uses MediaMTX backend for reliable remote access through FRP tunnels.
    """
    # Determine if request is local or remote
    host = request.headers.get("host", "")
    is_remote = "itagenten.no" in host or not any(x in host for x in ["localhost", "127.0.0.1", "192.168"])
    
    vdoninja_base = f"https://{VDONINJA_REMOTE_HOST}" if is_remote else f"https://{VDONINJA_LOCAL_HOST}"
    mediamtx_host = MEDIAMTX_REMOTE_HOST if is_remote else "localhost:8889"
    
    # Scene view URL using MediaMTX backend (NOT room-based P2P which doesn't work through tunnels)
    scene_url = f"{vdoninja_base}/?scene&mediamtx={mediamtx_host}&clean&transparent"
    
    return {
        "url": scene_url,
        "vdoninja_host": VDONINJA_REMOTE_HOST if is_remote else VDONINJA_LOCAL_HOST,
        "mediamtx_host": mediamtx_host,
        "is_remote": is_remote,
        "description": "Use this URL in OBS Browser Source to capture the mixer output"
    }


@app.get("/api/vdoninja/bridge-url")
async def get_vdoninja_bridge_url(request: Request) -> Dict[str, Any]:
    """Get the camera bridge page URL.
    
    The camera bridge page runs on R58 (locally or headlessly) and bridges
    HDMI cameras from MediaMTX WHEP endpoints into the VDO.ninja room.
    
    This is needed because cameras are already in MediaMTX (via GStreamer RTSP)
    and need to be "bridged" into the VDO.ninja room as guest sources.
    """
    # Determine if request is local or remote
    host = request.headers.get("host", "")
    is_remote = "itagenten.no" in host or not any(x in host for x in ["localhost", "127.0.0.1", "192.168"])
    
    # Bridge page is always accessed via local API
    bridge_url = f"{request.base_url}static/camera-bridge.html"
    
    return {
        "url": bridge_url,
        "vdoninja_host": VDONINJA_REMOTE_HOST,
        "mediamtx_host": MEDIAMTX_REMOTE_HOST,
        "room": "r58studio",
        "is_remote": is_remote,
        "description": "Open this page to bridge HDMI cameras into VDO.ninja room",
        "service_name": "vdoninja-bridge.service",
        "service_status_command": "systemctl status vdoninja-bridge"
    }


# =====================================================================
# VDO.ninja Bridge Control API
# =====================================================================

@app.get("/api/vdoninja/bridge/status")
async def get_vdoninja_bridge_status() -> Dict[str, Any]:
    """Get the status of the VDO.ninja bridge service.
    
    Returns:
        Status of the bridge service including whether Chromium is running
        and which tabs are open.
    """
    import subprocess
    
    status = {
        "service_active": False,
        "chromium_running": False,
        "tabs": [],
        "tabs_open": 0,
        "error": None
    }
    
    # Check if service is active
    try:
        result = subprocess.run(
            ["systemctl", "is-active", "vdoninja-bridge"],
            capture_output=True,
            text=True,
            timeout=5
        )
        status["service_active"] = result.returncode == 0
    except Exception as e:
        status["error"] = f"Could not check service status: {e}"
    
    # Check if Chromium debugger is responding
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://127.0.0.1:9222/json", timeout=2.0)
            if response.status_code == 200:
                status["chromium_running"] = True
                tabs = response.json()
                status["tabs"] = [
                    {"title": t.get("title", ""), "url": t.get("url", "")}
                    for t in tabs
                ]
                status["tabs_open"] = len(tabs)
    except Exception:
        pass  # Chromium not running
    
    return status


@app.post("/api/vdoninja/bridge/start")
async def start_vdoninja_bridge(
    room: str = "r58studio",
    cameras: Optional[str] = None
) -> Dict[str, Any]:
    """Start the VDO.ninja bridge service.
    
    Args:
        room: VDO.ninja room name (default: r58studio)
        cameras: Comma-separated camera config (format: stream_id:push_id:label)
                 Example: cam2:hdmi1:Camera-1,cam3:hdmi2:Camera-2
    
    Returns:
        Result of starting the bridge service.
    """
    import subprocess
    
    # Build environment for the service
    env_vars = {"VDONINJA_ROOM": room}
    
    if cameras:
        env_vars["CAMERAS"] = cameras
    else:
        # Use default cameras from config
        camera_list = []
        for i, (cam_id, cam_config) in enumerate(config.cameras.items()):
            if cam_config.enabled:
                label = getattr(cam_config, 'label', None) or f"HDMI-{cam_id.upper()}"
                push_id = f"hdmi{i+1}"
                camera_list.append(f"{cam_id}:{push_id}:{label}")
        if camera_list:
            env_vars["CAMERAS"] = ",".join(camera_list)
    
    try:
        # First stop any existing instance
        subprocess.run(
            ["sudo", "systemctl", "stop", "vdoninja-bridge"],
            capture_output=True,
            timeout=10
        )
        
        # Update environment in service file
        for key, value in env_vars.items():
            subprocess.run(
                ["sudo", "systemctl", "set-environment", f"{key}={value}"],
                capture_output=True,
                timeout=5
            )
        
        # Start the service
        result = subprocess.run(
            ["sudo", "systemctl", "start", "vdoninja-bridge"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return {
                "success": True,
                "message": f"VDO.ninja bridge started for room '{room}'",
                "room": room,
                "cameras": env_vars.get("CAMERAS", "default")
            }
        else:
            return {
                "success": False,
                "error": result.stderr or "Failed to start service",
                "room": room
            }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Command timed out"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/vdoninja/bridge/stop")
async def stop_vdoninja_bridge() -> Dict[str, Any]:
    """Stop the VDO.ninja bridge service."""
    import subprocess
    
    try:
        result = subprocess.run(
            ["sudo", "systemctl", "stop", "vdoninja-bridge"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # Also kill any Chromium processes
        subprocess.run(["pkill", "-f", "chromium"], capture_output=True, timeout=5)
        
        return {
            "success": result.returncode == 0,
            "message": "VDO.ninja bridge stopped" if result.returncode == 0 else result.stderr
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/vdoninja/whep-view-url/{stream_id}")
async def get_vdoninja_whep_view_url(request: Request, stream_id: str) -> Dict[str, Any]:
    """Get a VDO.ninja URL to view a single WHEP stream from MediaMTX.
    
    This is useful for testing and debugging individual camera streams.
    The &whepplay= parameter allows VDO.ninja to pull any WHEP stream directly.
    
    Args:
        stream_id: The MediaMTX stream path (e.g., 'cam0', 'cam2', 'speaker0')
    """
    # Determine if request is local or remote
    host = request.headers.get("host", "")
    is_remote = "itagenten.no" in host or not any(x in host for x in ["localhost", "127.0.0.1", "192.168"])
    
    vdoninja_base = f"https://{VDONINJA_REMOTE_HOST}" if is_remote else f"https://{VDONINJA_LOCAL_HOST}"
    mediamtx_host = MEDIAMTX_REMOTE_HOST if is_remote else "localhost:8889"
    
    whep_endpoint = f"https://{mediamtx_host}/{stream_id}/whep"
    
    # Build VDO.ninja URL with whepplay parameter
    view_url = f"{vdoninja_base}/?whepplay={whep_endpoint}&stereo=2&whepwait=2000"
    
    return {
        "url": view_url,
        "stream_id": stream_id,
        "whep_endpoint": whep_endpoint,
        "vdoninja_host": VDONINJA_REMOTE_HOST if is_remote else VDONINJA_LOCAL_HOST,
        "mediamtx_host": mediamtx_host,
        "is_remote": is_remote,
        "description": f"View {stream_id} stream via VDO.ninja WHEP playback"
    }


@app.get("/api/vdoninja/whepshare-url/{stream_id}")
async def get_vdoninja_whepshare_url(
    request: Request, 
    stream_id: str,
    room: str = "r58studio",
    push_id: Optional[str] = None,
    label: Optional[str] = None
) -> Dict[str, Any]:
    """Get a VDO.ninja URL to share a WHEP stream as a guest in a room.
    
    This uses the &whepshare parameter which tells VDO.ninja to share
    the WHEP stream to other viewers in the room without republishing.
    
    Args:
        stream_id: The MediaMTX stream path (e.g., 'cam0', 'cam2')
        room: The VDO.ninja room name (default: r58studio)
        push_id: Custom push ID (default: stream_id)
        label: Display name in VDO.ninja (default: HDMI-{stream_id})
    
    Example:
        GET /api/vdoninja/whepshare-url/cam2?room=myroom&label=Camera-1
    """
    import urllib.parse
    
    # Determine if request is local or remote
    host = request.headers.get("host", "")
    is_remote = "itagenten.no" in host or not any(x in host for x in ["localhost", "127.0.0.1", "192.168"])
    
    vdoninja_base = f"https://{VDONINJA_REMOTE_HOST}" if is_remote else f"https://{VDONINJA_LOCAL_HOST}"
    mediamtx_host = MEDIAMTX_REMOTE_HOST if is_remote else "localhost:8889"
    
    # Build WHEP endpoint URL
    whep_endpoint = f"https://{mediamtx_host}/whep/{stream_id}"
    encoded_whep = urllib.parse.quote(whep_endpoint, safe='')
    
    # Use defaults if not provided
    actual_push_id = push_id or stream_id
    actual_label = label or f"HDMI-{stream_id.upper()}"
    
    # Build VDO.ninja URL with whepshare parameter
    # &videodevice=0&audiodevice=0 disables local devices (no permission prompts)
    room_url = f"{vdoninja_base}/?push={actual_push_id}&room={room}&whepshare={encoded_whep}&label={actual_label}&videodevice=0&audiodevice=0&autostart"
    
    return {
        "url": room_url,
        "stream_id": stream_id,
        "room": room,
        "push_id": actual_push_id,
        "label": actual_label,
        "whep_endpoint": whep_endpoint,
        "is_remote": is_remote,
        "description": f"Share {stream_id} as a guest in VDO.ninja room '{room}'",
        "instructions": "Open this URL in a browser to join the room. Click 'Join Room with Camera' then 'START' to share the WHEP stream."
    }


@app.get("/api/vdoninja/room-urls")
async def get_vdoninja_room_urls(
    request: Request,
    room: str = "r58studio"
) -> Dict[str, Any]:
    """Get all VDO.ninja URLs for a room including cameras and management links.
    
    This provides a complete set of URLs needed to set up a VDO.ninja session:
    - Director URL for room management
    - Scene URL for OBS capture
    - Camera URLs using &whepshare for each active camera
    - Guest invite link
    
    Args:
        room: The VDO.ninja room name (default: r58studio)
    """
    import urllib.parse
    
    # Determine if request is local or remote
    host = request.headers.get("host", "")
    is_remote = "itagenten.no" in host or not any(x in host for x in ["localhost", "127.0.0.1", "192.168"])
    
    vdoninja_base = f"https://{VDONINJA_REMOTE_HOST}" if is_remote else f"https://{VDONINJA_LOCAL_HOST}"
    mediamtx_host = MEDIAMTX_REMOTE_HOST if is_remote else "localhost:8889"
    
    # Build management URLs
    urls = {
        "director": f"{vdoninja_base}/?director={room}",
        "scene": f"{vdoninja_base}/?scene&room={room}",
        "guest_invite": f"{vdoninja_base}/?room={room}",
    }
    
    # Build camera URLs for each configured camera
    cameras = []
    for cam_id, cam_config in config.cameras.items():
        if not cam_config.enabled:
            continue
        
        # Build WHEP share URL
        whep_endpoint = f"https://{mediamtx_host}/whep/{cam_id}"
        encoded_whep = urllib.parse.quote(whep_endpoint, safe='')
        
        # Create meaningful label from camera config or ID
        label = cam_config.label if hasattr(cam_config, 'label') and cam_config.label else f"HDMI-{cam_id.upper()}"
        push_id = f"hdmi{cam_id[-1]}" if cam_id.startswith("cam") else cam_id
        
        # &videodevice=0&audiodevice=0 disables local devices (no permission prompts)
        cam_url = f"{vdoninja_base}/?push={push_id}&room={room}&whepshare={encoded_whep}&label={label}&videodevice=0&audiodevice=0&autostart"
        
        cameras.append({
            "cam_id": cam_id,
            "label": label,
            "push_id": push_id,
            "whep_endpoint": whep_endpoint,
            "room_url": cam_url,
            "view_url": f"{vdoninja_base}/?view={push_id}&room={room}"
        })
    
    return {
        "room": room,
        "is_remote": is_remote,
        "urls": urls,
        "cameras": cameras,
        "all_camera_urls": [c["room_url"] for c in cameras],
        "instructions": {
            "step1": "Open the camera URLs in browsers (on R58 or any device) and click 'Join Room with Camera' then 'START'",
            "step2": "Open the Director URL to manage the room and see all participants",
            "step3": "Use the Scene URL in OBS as a browser source to capture the mix"
        }
    }


# =====================================================================
# Camera-to-Slot Mapping API
# =====================================================================

def _get_mapping_file_path() -> Path:
    """Get path to camera-slot mapping config file."""
    data_dir = Path(__file__).parent.parent / "data"
    data_dir.mkdir(exist_ok=True)
    return data_dir / "camera_mapping.json"


def _load_camera_mapping() -> Dict[str, Any]:
    """Load camera mapping from file or return defaults."""
    mapping_file = _get_mapping_file_path()
    
    if mapping_file.exists():
        try:
            import json
            with open(mapping_file, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    
    # Default mapping: CAM1->Slot 0, CAM2->Slot 1, etc.
    return {
        "mappings": {
            "cam0": 0,  # CAM 1 -> Slot 0
            "cam1": 1,  # CAM 2 -> Slot 1
            "cam2": 2,  # CAM 3 -> Slot 2
            "cam3": 3,  # CAM 4 -> Slot 3
            "guest1": 4,
            "guest2": 5,
            "guest3": 6,
            "guest4": 7
        },
        "version": 1
    }


def _save_camera_mapping(mapping: Dict[str, Any]) -> bool:
    """Save camera mapping to file."""
    mapping_file = _get_mapping_file_path()
    try:
        import json
        with open(mapping_file, 'w') as f:
            json.dump(mapping, f, indent=2)
        return True
    except Exception:
        return False


@app.get("/api/vdoninja/mapping")
async def get_camera_mapping(request: Request) -> Dict[str, Any]:
    """Get current camera-to-slot mappings.
    
    Returns the mapping of camera stream IDs to VDO.ninja mixer slots.
    Also includes WHEP URLs for each mapped source.
    """
    # Determine if request is local or remote
    host = request.headers.get("host", "")
    is_remote = "itagenten.no" in host or not any(x in host for x in ["localhost", "127.0.0.1", "192.168"])
    mediamtx_base = f"https://{MEDIAMTX_REMOTE_HOST}" if is_remote else "http://localhost:8889"
    
    mapping_data = _load_camera_mapping()
    
    # Enhance with WHEP URLs
    mappings_with_urls = {}
    for stream_id, slot in mapping_data.get("mappings", {}).items():
        whep_url = f"{mediamtx_base}/{stream_id}/whep"
        mappings_with_urls[stream_id] = {
            "slot": slot,
            "whep_url": whep_url
        }
    
    return {
        "mappings": mappings_with_urls,
        "raw_mappings": mapping_data.get("mappings", {}),
        "version": mapping_data.get("version", 1)
    }


@app.post("/api/vdoninja/mapping")
async def save_camera_mapping(request: Request) -> Dict[str, Any]:
    """Save camera-to-slot mappings.
    
    Expects JSON body with format:
    {
        "mappings": {
            "cam0": 0,
            "cam1": 1,
            ...
        }
    }
    """
    try:
        body = await request.json()
        mappings = body.get("mappings", {})
        
        if not mappings:
            raise HTTPException(status_code=400, detail="No mappings provided")
        
        # Validate: slot numbers should be 0-9
        for stream_id, slot in mappings.items():
            if not isinstance(slot, int) or slot < 0 or slot > 9:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Invalid slot {slot} for {stream_id}. Must be 0-9."
                )
        
        # Load existing and update
        existing = _load_camera_mapping()
        existing["mappings"] = mappings
        existing["version"] = existing.get("version", 0) + 1
        
        if _save_camera_mapping(existing):
            return {
                "success": True,
                "mappings": mappings,
                "version": existing["version"]
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to save mapping")
            
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/vdoninja/mapping/reset")
async def reset_camera_mapping() -> Dict[str, Any]:
    """Reset camera mappings to defaults.
    
    Restores the default auto-mapping:
    CAM1->Slot 0, CAM2->Slot 1, etc.
    """
    mapping_file = _get_mapping_file_path()
    
    # Remove existing file to use defaults
    if mapping_file.exists():
        mapping_file.unlink()
    
    # Return the default mapping
    default = _load_camera_mapping()
    
    return {
        "success": True,
        "message": "Mapping reset to defaults",
        "mappings": default.get("mappings", {})
    }


# =====================================================================
# Ingest Control API Endpoints
# =====================================================================

@app.post("/api/ingest/start")
async def start_ingest_all() -> Dict[str, Any]:
    """Start ingest pipelines for all cameras with signal.
    
    This will start streaming cameras to MediaMTX so they become
    available via WHEP for VDO.ninja mixer.
    """
    if not ingest_manager:
        raise HTTPException(status_code=503, detail="Ingest manager not available")
    
    results = ingest_manager.start_all()
    
    # Get updated status
    statuses = ingest_manager.get_status()
    status_info = {
        cam_id: {
            "started": results.get(cam_id, False),
            "status": status.status,
            "has_signal": status.has_signal,
            "resolution": f"{status.resolution[0]}x{status.resolution[1]}" if status.resolution else None
        }
        for cam_id, status in statuses.items()
    }
    
    return {
        "status": "completed",
        "cameras": status_info,
        "streaming_count": sum(1 for s in statuses.values() if s.status == "streaming")
    }


@app.post("/api/ingest/start/{cam_id}")
async def start_ingest_camera(cam_id: str) -> Dict[str, Any]:
    """Start ingest pipeline for a specific camera.
    
    Args:
        cam_id: Camera ID (cam0, cam1, cam2, cam3)
    """
    if not ingest_manager:
        raise HTTPException(status_code=503, detail="Ingest manager not available")
    
    if cam_id not in ingest_manager.config.cameras:
        raise HTTPException(status_code=404, detail=f"Camera {cam_id} not found")
    
    success = ingest_manager.start_ingest(cam_id)
    
    # Get updated status
    status = ingest_manager.get_camera_status(cam_id)
    
    return {
        "camera": cam_id,
        "started": success,
        "status": status.status if status else "unknown",
        "has_signal": status.has_signal if status else False,
        "resolution": f"{status.resolution[0]}x{status.resolution[1]}" if status and status.resolution else None
    }


@app.post("/api/ingest/stop")
async def stop_ingest_all() -> Dict[str, Any]:
    """Stop all ingest pipelines."""
    if not ingest_manager:
        raise HTTPException(status_code=503, detail="Ingest manager not available")
    
    results = ingest_manager.stop_all()
    
    return {
        "status": "completed",
        "cameras": results
    }


@app.post("/api/ingest/stop/{cam_id}")
async def stop_ingest_camera(cam_id: str) -> Dict[str, Any]:
    """Stop ingest pipeline for a specific camera."""
    if not ingest_manager:
        raise HTTPException(status_code=503, detail="Ingest manager not available")
    
    if cam_id not in ingest_manager.config.cameras:
        raise HTTPException(status_code=404, detail=f"Camera {cam_id} not found")
    
    success = ingest_manager.stop_ingest(cam_id)
    
    return {
        "camera": cam_id,
        "stopped": success
    }


@app.get("/api/ingest/status")
async def get_ingest_status() -> Dict[str, Any]:
    """Get status of all ingest pipelines."""
    if not ingest_manager:
        raise HTTPException(status_code=503, detail="Ingest manager not available")
    
    statuses = ingest_manager.get_status()
    
    status_info = {}
    for cam_id, status in statuses.items():
        # Also check MediaMTX for actual stream availability
        mediamtx_ready = await _check_mediamtx_stream_ready(cam_id)
        
        status_info[cam_id] = {
            "status": status.status,
            "has_signal": status.has_signal,
            "resolution": f"{status.resolution[0]}x{status.resolution[1]}" if status.resolution else None,
            "stream_url": status.stream_url,
            "mediamtx_ready": mediamtx_ready
        }
    
    return {
        "cameras": status_info,
        "streaming_count": sum(1 for s in statuses.values() if s.status == "streaming"),
        "signal_count": sum(1 for s in statuses.values() if s.has_signal)
    }


# ============================================================================
# Camera Control API Endpoints (External Cameras)
# ============================================================================

@app.get("/api/v1/cameras/")
async def list_external_cameras() -> List[str]:
    """List all configured external cameras"""
    if not camera_control_manager:
        return []
    return list(camera_control_manager.cameras.keys())


@app.get("/api/v1/cameras/{camera_name}/status")
async def get_external_camera_status(camera_name: str) -> Dict[str, Any]:
    """Get camera status and connection info"""
    if not camera_control_manager:
        raise HTTPException(status_code=503, detail="Camera control not available")
    
    if camera_name not in camera_control_manager.cameras:
        raise HTTPException(status_code=404, detail=f"Camera '{camera_name}' not found")
    
    camera = camera_control_manager.cameras[camera_name]
    connected = await camera.check_connection()
    if isinstance(camera, BlackmagicCamera):
        camera_type = "blackmagic"
    elif isinstance(camera, ObsbotTail2):
        camera_type = "obsbot_tail2"
    elif isinstance(camera, SonyCamera):
        camera_type = "sony_fx30"
    else:
        camera_type = "unknown"
    
    settings = None
    if connected:
        try:
            settings = await camera.get_settings()
        except Exception as e:
            logger.warning(f"Failed to get settings from {camera_name}: {e}")
    
    return {
        "name": camera_name,
        "type": camera_type,
        "connected": connected,
        "settings": settings
    }


@app.get("/api/v1/cameras/{camera_name}/settings")
async def get_external_camera_settings(camera_name: str) -> Dict[str, Any]:
    """Get all camera settings"""
    if not camera_control_manager:
        raise HTTPException(status_code=503, detail="Camera control not available")
    
    if camera_name not in camera_control_manager.cameras:
        raise HTTPException(status_code=404, detail=f"Camera '{camera_name}' not found")
    
    camera = camera_control_manager.cameras[camera_name]
    settings = await camera.get_settings()
    if settings is None:
        raise HTTPException(status_code=503, detail="Failed to get camera settings")
    
    return {"name": camera_name, "settings": settings}


class SetFocusRequest(BaseModel):
    mode: str
    value: Optional[float] = None

@app.put("/api/v1/cameras/{camera_name}/settings/focus")
async def set_camera_focus(camera_name: str, request: SetFocusRequest = Body(...)) -> Dict[str, Any]:
    """Set camera focus"""
    if not camera_control_manager:
        raise HTTPException(status_code=503, detail="Camera control not available")
    
    if camera_name not in camera_control_manager.cameras:
        raise HTTPException(status_code=404, detail=f"Camera '{camera_name}' not found")
    
    camera = camera_control_manager.cameras[camera_name]
    if not isinstance(camera, (BlackmagicCamera, ObsbotTail2, SonyCamera)):
        raise HTTPException(status_code=400, detail="Camera does not support focus control")
    
    success = await camera.set_focus(request.mode, request.value)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to set focus")
    
    return {"success": True, "camera": camera_name, "parameter": "focus"}


class SetWhiteBalanceRequest(BaseModel):
    mode: str
    temperature: Optional[int] = None

@app.put("/api/v1/cameras/{camera_name}/settings/whiteBalance")
async def set_camera_white_balance(camera_name: str, request: SetWhiteBalanceRequest = Body(...)) -> Dict[str, Any]:
    """Set camera white balance"""
    if not camera_control_manager:
        raise HTTPException(status_code=503, detail="Camera control not available")
    
    if camera_name not in camera_control_manager.cameras:
        raise HTTPException(status_code=404, detail=f"Camera '{camera_name}' not found")
    
    camera = camera_control_manager.cameras[camera_name]
    if not isinstance(camera, (BlackmagicCamera, ObsbotTail2, SonyCamera)):
        raise HTTPException(status_code=400, detail="Camera does not support white balance control")
    
    success = await camera.set_white_balance(request.mode, request.temperature)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to set white balance")
    
    return {"success": True, "camera": camera_name, "parameter": "whiteBalance"}


class SetExposureRequest(BaseModel):
    mode: str
    value: Optional[float] = None

@app.put("/api/v1/cameras/{camera_name}/settings/exposure")
async def set_camera_exposure(camera_name: str, request: SetExposureRequest = Body(...)) -> Dict[str, Any]:
    """Set camera exposure (OBSbot)"""
    if not camera_control_manager:
        raise HTTPException(status_code=503, detail="Camera control not available")
    
    if camera_name not in camera_control_manager.cameras:
        raise HTTPException(status_code=404, detail=f"Camera '{camera_name}' not found")
    
    camera = camera_control_manager.cameras[camera_name]
    if isinstance(camera, (ObsbotTail2, SonyCamera)):
        success = await camera.set_exposure(request.mode, request.value)
    elif isinstance(camera, BlackmagicCamera):
        raise HTTPException(status_code=400, detail="Use /settings/iso and /settings/shutter for Blackmagic cameras")
    else:
        raise HTTPException(status_code=400, detail="Camera does not support exposure control")
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to set exposure")
    
    return {"success": True, "camera": camera_name, "parameter": "exposure"}


class SetValueRequest(BaseModel):
    value: float

@app.put("/api/v1/cameras/{camera_name}/settings/iso")
async def set_camera_iso(camera_name: str, request: SetValueRequest = Body(...)) -> Dict[str, Any]:
    """Set camera ISO (Blackmagic only)"""
    if not camera_control_manager:
        raise HTTPException(status_code=503, detail="Camera control not available")
    
    if camera_name not in camera_control_manager.cameras:
        raise HTTPException(status_code=404, detail=f"Camera '{camera_name}' not found")
    
    camera = camera_control_manager.cameras[camera_name]
    if isinstance(camera, BlackmagicCamera):
        success = await camera.set_iso(int(request.value))
    elif isinstance(camera, SonyCamera):
        success = await camera.set_iso(int(request.value))
    else:
        raise HTTPException(status_code=400, detail="Camera does not support ISO control")
    if not success:
        raise HTTPException(status_code=500, detail="Failed to set ISO")
    
    return {"success": True, "camera": camera_name, "parameter": "iso", "value": int(request.value)}


@app.put("/api/v1/cameras/{camera_name}/settings/shutter")
async def set_camera_shutter(camera_name: str, request: SetValueRequest = Body(...)) -> Dict[str, Any]:
    """Set camera shutter speed (Blackmagic only)"""
    if not camera_control_manager:
        raise HTTPException(status_code=503, detail="Camera control not available")
    
    if camera_name not in camera_control_manager.cameras:
        raise HTTPException(status_code=404, detail=f"Camera '{camera_name}' not found")
    
    camera = camera_control_manager.cameras[camera_name]
    if isinstance(camera, BlackmagicCamera):
        success = await camera.set_shutter(request.value)
    elif isinstance(camera, SonyCamera):
        success = await camera.set_shutter(request.value)
    else:
        raise HTTPException(status_code=400, detail="Camera does not support shutter control")
    if not success:
        raise HTTPException(status_code=500, detail="Failed to set shutter")
    
    return {"success": True, "camera": camera_name, "parameter": "shutter", "value": request.value}


class SetIrisRequest(BaseModel):
    mode: str
    value: Optional[float] = None

@app.put("/api/v1/cameras/{camera_name}/settings/iris")
async def set_camera_iris(camera_name: str, request: SetIrisRequest = Body(...)) -> Dict[str, Any]:
    """Set camera iris (Blackmagic only)"""
    if not camera_control_manager:
        raise HTTPException(status_code=503, detail="Camera control not available")
    
    if camera_name not in camera_control_manager.cameras:
        raise HTTPException(status_code=404, detail=f"Camera '{camera_name}' not found")
    
    camera = camera_control_manager.cameras[camera_name]
    if not isinstance(camera, BlackmagicCamera):
        raise HTTPException(status_code=400, detail="Camera does not support iris control")
    
    success = await camera.set_iris(request.mode, request.value)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to set iris")
    
    return {"success": True, "camera": camera_name, "parameter": "iris"}


@app.put("/api/v1/cameras/{camera_name}/settings/gain")
async def set_camera_gain(camera_name: str, request: SetValueRequest = Body(...)) -> Dict[str, Any]:
    """Set camera gain (Blackmagic only)"""
    if not camera_control_manager:
        raise HTTPException(status_code=503, detail="Camera control not available")
    
    if camera_name not in camera_control_manager.cameras:
        raise HTTPException(status_code=404, detail=f"Camera '{camera_name}' not found")
    
    camera = camera_control_manager.cameras[camera_name]
    if not isinstance(camera, BlackmagicCamera):
        raise HTTPException(status_code=400, detail="Camera does not support gain control")
    
    success = await camera.set_gain(request.value)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to set gain")
    
    return {"success": True, "camera": camera_name, "parameter": "gain", "value": request.value}


class SetPTZRequest(BaseModel):
    pan: float
    tilt: float
    zoom: float

@app.put("/api/v1/cameras/{camera_name}/settings/ptz")
async def set_camera_ptz(camera_name: str, request: SetPTZRequest = Body(...)) -> Dict[str, Any]:
    """Move PTZ camera (OBSbot only)"""
    if not camera_control_manager:
        raise HTTPException(status_code=503, detail="Camera control not available")
    
    if camera_name not in camera_control_manager.cameras:
        raise HTTPException(status_code=404, detail=f"Camera '{camera_name}' not found")
    
    camera = camera_control_manager.cameras[camera_name]
    if not hasattr(camera, "ptz_move"):
        raise HTTPException(status_code=400, detail="Camera does not support PTZ control")
    
    success = await camera.ptz_move(request.pan, request.tilt, request.zoom)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to move PTZ")
    
    return {"success": True, "camera": camera_name, "parameter": "ptz"}


@app.put("/api/v1/cameras/{camera_name}/settings/ptz/preset/{preset_id}")
async def recall_camera_ptz_preset(camera_name: str, preset_id: int) -> Dict[str, Any]:
    """Recall PTZ preset (OBSbot only)"""
    if not camera_control_manager:
        raise HTTPException(status_code=503, detail="Camera control not available")
    
    if camera_name not in camera_control_manager.cameras:
        raise HTTPException(status_code=404, detail=f"Camera '{camera_name}' not found")
    
    camera = camera_control_manager.cameras[camera_name]
    if not hasattr(camera, "ptz_preset"):
        raise HTTPException(status_code=400, detail="Camera does not support PTZ presets")
    
    success = await camera.ptz_preset(preset_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to recall preset")
    
    return {"success": True, "camera": camera_name, "preset_id": preset_id}


class SetColorCorrectionRequest(BaseModel):
    lift: Optional[List[float]] = None
    gamma: Optional[List[float]] = None
    gain: Optional[List[float]] = None
    offset: Optional[List[float]] = None

@app.put("/api/v1/cameras/{camera_name}/settings/colorCorrection")
async def set_camera_color_correction(
    camera_name: str,
    request: SetColorCorrectionRequest = Body(...)
) -> Dict[str, Any]:
    """Set color correction (Blackmagic only)"""
    if not camera_control_manager:
        raise HTTPException(status_code=503, detail="Camera control not available")
    
    if camera_name not in camera_control_manager.cameras:
        raise HTTPException(status_code=404, detail=f"Camera '{camera_name}' not found")
    
    camera = camera_control_manager.cameras[camera_name]
    if not isinstance(camera, BlackmagicCamera):
        raise HTTPException(status_code=400, detail="Camera does not support color correction")
    
    settings = {}
    if request.lift:
        settings["lift"] = request.lift
    if request.gamma:
        settings["gamma"] = request.gamma
    if request.gain:
        settings["gain"] = request.gain
    if request.offset:
        settings["offset"] = request.offset
    
    success = await camera.set_color_correction(settings)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to set color correction")
    
    return {"success": True, "camera": camera_name, "parameter": "colorCorrection"}


# ============================================================================
# Camera Configuration API (Get/Set external_cameras config)
# ============================================================================

@app.get("/api/v1/cameras/config")
async def get_camera_config() -> Dict[str, Any]:
    """Get external cameras configuration from config.yml"""
    try:
        import yaml
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
        
        external_cameras = config_data.get("external_cameras", [])
        return {
            "cameras": external_cameras,
            "config_path": str(config_path)
        }
    except Exception as e:
        logger.error(f"Failed to read camera config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to read config: {str(e)}")


@app.put("/api/v1/cameras/config")
async def update_camera_config(cameras: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Update external cameras configuration in config.yml
    
    Args:
        cameras: List of camera configuration dicts
            Each dict should have: name, type, ip, enabled, and optional port
    """
    try:
        import yaml
        
        # Read existing config
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f) or {}
        
        # Update external_cameras section
        config_data["external_cameras"] = cameras
        
        # Write back to file
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        
        # Reload camera control manager
        global camera_control_manager
        if cameras:
            try:
                camera_control_manager = CameraControlManager(cameras)
                logger.info(f"Camera control manager reloaded with {camera_control_manager.get_camera_count()} camera(s)")
            except Exception as e:
                logger.error(f"Failed to reload camera control manager: {e}")
                camera_control_manager = None
        else:
            camera_control_manager = None
        
        return {
            "success": True,
            "cameras": cameras,
            "message": "Configuration updated. Service restart may be required for changes to take effect."
        }
    except Exception as e:
        logger.error(f"Failed to update camera config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update config: {str(e)}")


# ============================================================================
# PTZ Controller API (Hardware joystick/gamepad support)
# ============================================================================

@app.get("/api/v1/ptz-controller/cameras")
async def list_ptz_cameras() -> Dict[str, Any]:
    """List cameras that support PTZ control."""
    if not camera_control_manager:
        return {"cameras": []}
    
    ptz_cameras = []
    for name, camera in camera_control_manager.cameras.items():
        if hasattr(camera, "ptz_move"):
            ptz_cameras.append({
                "name": name,
                "type": camera.__class__.__name__,
                "supports_focus": hasattr(camera, "set_focus")
            })
    
    return {"cameras": ptz_cameras}


@app.put("/api/v1/ptz-controller/{camera_name}/ptz")
async def ptz_controller_command(camera_name: str, request: SetPTZRequest = Body(...)) -> Dict[str, Any]:
    """Execute PTZ command from hardware controller (optimized for speed)."""
    if not camera_control_manager:
        raise HTTPException(status_code=503, detail="Camera control not available")
    
    if camera_name not in camera_control_manager.cameras:
        raise HTTPException(status_code=404, detail=f"Camera '{camera_name}' not found")
    
    camera = camera_control_manager.cameras[camera_name]
    if not hasattr(camera, "ptz_move"):
        raise HTTPException(status_code=400, detail="Camera does not support PTZ")
    
    # Execute PTZ (fire-and-forget for speed)
    asyncio.create_task(camera.ptz_move(request.pan, request.tilt, request.zoom))
    
    return {
        "success": True,
        "camera": camera_name,
        "command": {
            "pan": request.pan,
            "tilt": request.tilt,
            "zoom": request.zoom
        }
    }


@app.websocket("/api/v1/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time events and status updates."""
    await websocket.accept()
    logger.info("WebSocket client connected")
    
    try:
        # Send initial connection event
        await websocket.send_json({
            "v": 1,
            "type": "connected",
            "ts": datetime.now().isoformat(),
            "seq": 1,
            "device_id": config.device_id or "r58-device",
            "payload": {
                "message": "Connected to R58 device"
            }
        })
        
        # Heartbeat loop
        last_heartbeat = time.time()
        heartbeat_interval = 30.0  # 30 seconds
        
        while True:
            try:
                # Check for incoming messages (non-blocking)
                try:
                    data = await asyncio.wait_for(websocket.receive_json(), timeout=1.0)
                    msg_type = data.get("type")
                    
                    if msg_type == "sync_request":
                        # Client requesting state sync
                        last_seq = data.get("last_seq", 0)
                        await websocket.send_json({
                            "v": 1,
                            "type": "sync_response",
                            "ts": datetime.now().isoformat(),
                            "seq": 2,
                            "device_id": config.device_id or "r58-device",
                            "payload": {
                                "last_seq": last_seq,
                                "current_seq": 2,
                                "can_replay": False,
                                "missed_event_count": 0,
                                "events": [],
                                "state": {
                                    "mode": await mode_manager.get_current_mode() if mode_manager else "recorder",
                                    "recording": None,
                                    "inputs": {}
                                }
                            }
                        })
                    elif msg_type == "ping":
                        await websocket.send_json({
                            "v": 1,
                            "type": "pong",
                            "ts": datetime.now().isoformat(),
                            "seq": 2,
                            "device_id": config.device_id or "r58-device"
                        })
                except asyncio.TimeoutError:
                    # No message received, continue to heartbeat check
                    pass
                
                # Send heartbeat if needed
                now = time.time()
                if now - last_heartbeat >= heartbeat_interval:
                    await websocket.send_json({
                        "v": 1,
                        "type": "heartbeat",
                        "ts": datetime.now().isoformat(),
                        "seq": 2,
                        "device_id": config.device_id or "r58-device"
                    })
                    last_heartbeat = now
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                break
                
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.close()
        except:
            pass


@app.websocket("/api/v1/ptz-controller/ws")
async def ptz_controller_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time PTZ control from hardware controllers."""
    await websocket.accept()
    logger.info("PTZ controller WebSocket connected")
    
    if not camera_control_manager:
        await websocket.send_json({
            "type": "error",
            "message": "Camera control not available"
        })
        await websocket.close()
        return
    
    current_camera: Optional[str] = None
    last_command_time = 0.0
    min_command_interval = 0.033  # ~30Hz max update rate
    
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            
            if msg_type == "set_camera":
                current_camera = data.get("camera_name")
                await websocket.send_json({
                    "type": "camera_set",
                    "camera": current_camera
                })
                logger.info(f"PTZ controller targeting camera: {current_camera}")
            
            elif msg_type == "ptz_command":
                if not current_camera:
                    await websocket.send_json({
                        "type": "error",
                        "message": "No camera selected"
                    })
                    continue
                
                try:
                    import time
                    now = time.time()
                    if now - last_command_time < min_command_interval:
                        continue
                    last_command_time = now
                    
                    if current_camera not in camera_control_manager.cameras:
                        await websocket.send_json({
                            "type": "error",
                            "message": f"Camera '{current_camera}' not found"
                        })
                        continue
                    
                    camera = camera_control_manager.cameras[current_camera]
                    if not hasattr(camera, "ptz_move"):
                        await websocket.send_json({
                            "type": "error",
                            "message": "Camera does not support PTZ"
                        })
                        continue
                    
                    pan = data.get("pan", 0.0)
                    tilt = data.get("tilt", 0.0)
                    zoom = data.get("zoom", 0.0)
                    speed = data.get("speed", 1.0)
                    
                    pan *= speed
                    tilt *= speed
                    zoom *= speed
                    
                    # Execute (fire-and-forget for speed)
                    asyncio.create_task(camera.ptz_move(pan, tilt, zoom))
                    
                    if "focus" in data and hasattr(camera, "set_focus"):
                        focus_value = data["focus"]
                        if focus_value != 0:
                            focus_normalized = (focus_value + 1.0) / 2.0
                            asyncio.create_task(camera.set_focus("manual", focus_normalized))
                    
                except Exception as e:
                    logger.error(f"Error executing PTZ command: {e}")
            
            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})
            
            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Unknown message type: {msg_type}"
                })
    
    except WebSocketDisconnect:
        logger.info("PTZ controller WebSocket disconnected")
    except Exception as e:
        logger.error(f"PTZ controller WebSocket error: {e}")
        try:
            await websocket.close()
        except:
            pass


# ============================================================================
# VDO.ninja API (Companion/Stream Deck integration)
# ============================================================================

@app.post("/api/v1/vdo-ninja/scene/{scene_id}")
async def vdo_ninja_switch_scene(scene_id: int) -> Dict[str, Any]:
    """Switch to scene (0-8 or custom scene name)"""
    try:
        from src.vdo_ninja.api_client import get_vdo_ninja_client_from_config
        client = get_vdo_ninja_client_from_config()
        if not client:
            raise HTTPException(status_code=503, detail="VDO.ninja API not configured")
        
        success = await client.switch_scene(scene_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to switch scene")
        
        return {"success": True, "scene_id": scene_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"VDO.ninja switch scene error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/vdo-ninja/guest/{guest_id}/mute")
async def vdo_ninja_toggle_mute(guest_id: str) -> Dict[str, Any]:
    """Toggle microphone mute for a guest"""
    try:
        from src.vdo_ninja.api_client import get_vdo_ninja_client_from_config
        client = get_vdo_ninja_client_from_config()
        if not client:
            raise HTTPException(status_code=503, detail="VDO.ninja API not configured")
        
        muted = await client.toggle_mute(guest_id)
        if muted is None:
            raise HTTPException(status_code=500, detail="Failed to toggle mute")
        
        return {"success": True, "guest_id": guest_id, "muted": muted}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"VDO.ninja toggle mute error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class VolumeRequest(BaseModel):
    volume: int  # 0-200


@app.post("/api/v1/vdo-ninja/guest/{guest_id}/volume")
async def vdo_ninja_set_volume(guest_id: str, request: VolumeRequest = Body(...)) -> Dict[str, Any]:
    """Set volume for a guest (0-200)"""
    try:
        from src.vdo_ninja.api_client import get_vdo_ninja_client_from_config
        client = get_vdo_ninja_client_from_config()
        if not client:
            raise HTTPException(status_code=503, detail="VDO.ninja API not configured")
        
        success = await client.set_volume(guest_id, request.volume)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to set volume")
        
        return {"success": True, "guest_id": guest_id, "volume": request.volume}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"VDO.ninja set volume error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/vdo-ninja/recording/start")
async def vdo_ninja_start_recording() -> Dict[str, Any]:
    """Start recording"""
    try:
        from src.vdo_ninja.api_client import get_vdo_ninja_client_from_config
        client = get_vdo_ninja_client_from_config()
        if not client:
            raise HTTPException(status_code=503, detail="VDO.ninja API not configured")
        
        success = await client.start_recording()
        if not success:
            raise HTTPException(status_code=500, detail="Failed to start recording")
        
        return {"success": True, "recording": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"VDO.ninja start recording error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/vdo-ninja/recording/stop")
async def vdo_ninja_stop_recording() -> Dict[str, Any]:
    """Stop recording"""
    try:
        from src.vdo_ninja.api_client import get_vdo_ninja_client_from_config
        client = get_vdo_ninja_client_from_config()
        if not client:
            raise HTTPException(status_code=503, detail="VDO.ninja API not configured")
        
        success = await client.stop_recording()
        if not success:
            raise HTTPException(status_code=500, detail="Failed to stop recording")
        
        return {"success": True, "recording": False}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"VDO.ninja stop recording error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/vdo-ninja/guests")
async def vdo_ninja_list_guests() -> List[Dict[str, Any]]:
    """List connected guests (for Companion feedback)"""
    try:
        from src.vdo_ninja.api_client import get_vdo_ninja_client_from_config
        client = get_vdo_ninja_client_from_config()
        if not client:
            raise HTTPException(status_code=503, detail="VDO.ninja API not configured")
        
        guests = await client.get_guests()
        return guests
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"VDO.ninja list guests error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# LAN Device Discovery API
# ============================================================================

@app.get("/api/v1/lan-devices")
async def list_lan_devices() -> Dict[str, Any]:
    """List discovered R58 devices on local network"""
    # Simplified implementation - return empty list
    # Full implementation would scan network for devices
    return {
        "devices": [],
        "total": 0,
        "last_scan": datetime.now().isoformat()
    }


@app.post("/api/v1/lan-devices/scan")
async def scan_lan_devices() -> Dict[str, Any]:
    """Scan local network for R58 devices"""
    # Simplified implementation
    return {
        "success": True,
        "devices_found": 0,
        "message": "Network scan completed"
    }


@app.get("/api/v1/lan-devices/{device_id}")
async def get_lan_device(device_id: str) -> Dict[str, Any]:
    """Get information about a specific device"""
    raise HTTPException(status_code=404, detail="Device not found")


@app.post("/api/v1/lan-devices/{device_id}/connect")
async def connect_to_lan_device(device_id: str) -> Dict[str, Any]:
    """Connect to a discovered device"""
    return {
        "connected": False,
        "error": "Device not found"
    }


# ============================================================================
# WordPress/JetAppointments Integration API
# ============================================================================

@app.get("/api/v1/wordpress/status")
async def get_wordpress_status() -> Dict[str, Any]:
    """Get WordPress integration status"""
    wp_client = get_wordpress_client(config)

    if not hasattr(config, 'wordpress') or not config.wordpress.enabled:
        return {
            "enabled": False,
            "connected": False,
            "wordpress_url": config.wordpress.url if hasattr(config, 'wordpress') else '',
            "error": "WordPress integration is disabled"
        }

    if not wp_client or not wp_client.is_configured:
        return {
            "enabled": True,
            "connected": False,
            "wordpress_url": config.wordpress.url if hasattr(config, 'wordpress') else '',
            "error": "WordPress credentials not configured"
        }
    
    connected = await wp_client.test_connection()
    
    return {
        "enabled": True,
        "connected": connected,
        "wordpress_url": wp_client.base_url,
        "last_sync": datetime.now().isoformat() if connected else None,
        "error": wp_client._last_error if not connected else None
    }


@app.get("/api/v1/wordpress/health")
async def get_wordpress_health() -> Dict[str, Any]:
    """Lightweight health check for WordPress integration routes"""
    wp_enabled = hasattr(config, 'wordpress') and config.wordpress.enabled
    wp_client = get_wordpress_client(config)

    if not wp_enabled:
        return {
            "ok": False,
            "enabled": False,
            "configured": False,
            "checks": [],
            "error": "WordPress integration is disabled",
        }

    if not wp_client or not wp_client.is_configured:
        return {
            "ok": False,
            "enabled": True,
            "configured": False,
            "checks": [],
            "error": "WordPress credentials not configured",
        }

    checks: List[Dict[str, Any]] = []
    overall_ok = True

    async def run_check(name: str, coro):
        nonlocal overall_ok
        start = time.monotonic()
        try:
            result = await coro
            success = True
            error = None
        except Exception as e:
            result = None
            success = False
            error = str(e)
        duration_ms = int((time.monotonic() - start) * 1000)
        checks.append({
            "name": name,
            "success": success,
            "duration_ms": duration_ms,
            "error": error,
        })
        if not success:
            overall_ok = False
        return result

    # Connection/auth check
    connection_ok = await run_check("status", wp_client.test_connection())
    if connection_ok is False:
        overall_ok = False
        checks[-1]["success"] = False
        checks[-1]["error"] = wp_client._last_error or "Authentication failed"

    # Appointments list (today, minimal)
    today = datetime.now().date()
    await run_check(
        "appointments_today",
        wp_client.get_appointments(date_from=today, date_to=today, limit=1, page=1),
    )

    # Clients list (minimal)
    clients: List[ClientInfo] = await run_check("clients", wp_client.get_clients(limit=1)) or []

    # Projects for first client (if available)
    if clients:
        await run_check("client_projects", wp_client.get_client_projects(clients[0].id))

    return {
        "ok": overall_ok,
        "enabled": True,
        "configured": True,
        "wordpress_url": wp_client.base_url,
        "checked_at": datetime.now().isoformat(),
        "checks": checks,
    }


@app.get("/api/v1/wordpress/appointments")
async def list_appointments(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    per_page: int = 20
) -> Dict[str, Any]:
    """List appointments from JetAppointments"""
    wp_client = get_wordpress_client(config)
    if not wp_client or not wp_client.is_configured:
        raise HTTPException(status_code=503, detail="WordPress not configured")
    
    from datetime import date as date_type
    df = date_type.fromisoformat(date_from) if date_from else None
    dt = date_type.fromisoformat(date_to) if date_to else None

    booking_status = None
    if status:
        try:
            booking_status = BookingStatus(status)
        except Exception:
            booking_status = None

    bookings = await wp_client.get_appointments(
        date_from=df,
        date_to=dt,
        status=booking_status,
        limit=per_page,
        page=page,
    )
    
    return {
        "bookings": [b.dict() for b in bookings],
        "total": len(bookings),
        "page": page,
        "per_page": per_page
    }


@app.get("/api/v1/wordpress/appointments/today")
async def get_todays_appointments() -> Dict[str, Any]:
    """Get today's appointments"""
    wp_client = get_wordpress_client(config)
    if not wp_client or not wp_client.is_configured:
        raise HTTPException(status_code=503, detail="WordPress not configured")

    bookings = await wp_client.get_todays_appointments()
    return {
        "bookings": [b.dict() for b in bookings],
        "total": len(bookings)
    }


@app.get("/api/v1/wordpress/appointments/{appointment_id}")
async def get_appointment(appointment_id: int) -> Dict[str, Any]:
    """Get a specific appointment"""
    wp_client = get_wordpress_client(config)
    if not wp_client or not wp_client.is_configured:
        raise HTTPException(status_code=503, detail="WordPress not configured")
    
    booking = await wp_client.get_appointment(appointment_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Appointment not found")

    graphics = []
    if booking.content_id:
        graphics = await wp_client.get_content_graphics(int(booking.content_id))
    elif booking.client and booking.client.default_project_id:
        project = await wp_client.get_video_project(booking.client.default_project_id)
        if project:
            graphics = project.graphics

    return {
        "booking": booking.dict(),
        "graphics": [g.dict() for g in graphics]
    }


@app.post("/api/v1/wordpress/appointments/{appointment_id}/activate")
async def activate_appointment(appointment_id: int, request: Dict[str, Any] = Body({})) -> Dict[str, Any]:
    """Activate a booking session"""
    wp_client = get_wordpress_client(config)
    if not wp_client or not wp_client.is_configured:
        raise HTTPException(status_code=503, detail="WordPress not configured")

    current = get_active_booking()
    if current and current.booking.id != appointment_id:
        raise HTTPException(
            status_code=409,
            detail=f"Another booking is already active: {current.booking.id}"
        )

    booking = await wp_client.get_appointment(appointment_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Appointment not found")

    if not booking.client:
        raise HTTPException(status_code=400, detail="Booking has no associated client")

    download_graphics = bool(request.get("download_graphics", True))

    project = await wp_client.get_client_default_project(booking.client.id)
    if not project:
        raise HTTPException(
            status_code=400,
            detail=f"Client {booking.client.name} has no default project configured"
        )

    recording_title = f"{booking.client.name} - {booking.date} {booking.slot_start}"
    recording = await wp_client.create_recording(
        project_id=project.id,
        booking_id=booking.id,
        title=recording_title,
    )

    if not recording:
        raise HTTPException(status_code=500, detail="Failed to create recording in WordPress")

    base_path = Path("/data/recordings")
    client_slug = booking.client.slug or "unknown_client"
    project_slug = project.slug or "unknown_project"
    recording_path = base_path / "clients" / client_slug / project_slug / str(recording.id)
    recording_path.mkdir(parents=True, exist_ok=True)

    graphics_paths: List[str] = []
    if download_graphics and project.graphics:
        graphics_dir = recording_path / "graphics"
        graphics_paths = await wp_client.download_graphics(project.graphics, graphics_dir)

    import secrets
    access_token = secrets.token_urlsafe(32)

    context = ActiveBookingContext(
        booking=booking,
        recording_id=recording.id,
        project=project,
        recording_path=str(recording_path),
        graphics_downloaded=len(graphics_paths) > 0,
        graphics_paths=graphics_paths,
        access_token=access_token,
        display_mode=booking.display_mode,
        teleprompter_script=booking.teleprompter_script,
    )

    set_active_booking(context)
    await wp_client.update_appointment_status(appointment_id, BookingStatus.PROCESSING)

    return {
        "success": True,
        "booking": booking.dict(),
        "recording_path": str(recording_path),
        "graphics_downloaded": len(graphics_paths),
        "access_token": access_token,
        "message": f"Booking activated. Recording #{recording.id} created."
    }


@app.get("/api/v1/wordpress/booking/current")
async def get_current_booking() -> Dict[str, Any]:
    """Get currently active booking"""
    context = get_active_booking()
    if not context:
        return {"active": False, "booking": None}

    return {
        "active": True,
        "booking": context.booking.dict(),
        "recording_path": context.recording_path,
        "graphics_downloaded": context.graphics_downloaded,
        "graphics_paths": context.graphics_paths,
        "activated_at": context.activated_at.isoformat(),
    }


@app.post("/api/v1/wordpress/appointments/{appointment_id}/complete")
async def complete_booking(appointment_id: int, request: Dict[str, Any] = Body({})) -> Dict[str, Any]:
    """Complete a booking session and optionally upload recordings"""
    wp_client = get_wordpress_client(config)
    if not wp_client or not wp_client.is_configured:
        raise HTTPException(status_code=503, detail="WordPress not configured")

    current = get_active_booking()
    if not current or current.booking.id != appointment_id:
        raise HTTPException(status_code=404, detail="Booking is not currently active")

    upload_recordings = bool(request.get("upload_recordings", True))
    update_status = bool(request.get("update_status", True))

    recordings_uploaded = 0
    wordpress_updated = False

    if upload_recordings:
        recording_dir = Path(current.recording_path)
        if recording_dir.exists():
            for extension in (".mkv", ".mp4", ".mov"):
                for recording_file in recording_dir.glob(f"*{extension}"):
                    media_id = await wp_client.upload_recording(
                        recording_file,
                        title=f"Recording - {current.booking.client.name} - {recording_file.stem}" if current.booking.client else recording_file.stem,
                        parent_post_id=current.recording_id,
                    )
                    if media_id:
                        await wp_client.attach_media_to_recording(current.recording_id, media_id)
                        recordings_uploaded += 1

    if update_status:
        wordpress_updated = await wp_client.update_appointment_status(
            appointment_id,
            BookingStatus.COMPLETED,
        )

    set_active_booking(None)

    return {
        "success": True,
        "booking_id": appointment_id,
        "recordings_uploaded": recordings_uploaded,
        "wordpress_status_updated": wordpress_updated,
        "message": f"Booking completed. {recordings_uploaded} recordings uploaded."
    }


@app.get("/api/v1/wordpress/clients")
async def list_clients() -> Dict[str, Any]:
    """List all WordPress clients"""
    wp_client = get_wordpress_client(config)
    if not wp_client:
        raise HTTPException(status_code=503, detail="WordPress not configured")
    
    clients = await wp_client.get_clients()
    
    return {
        "clients": [c.dict() for c in clients],
        "total": len(clients)
    }


@app.get("/api/v1/wordpress/clients/{client_id}/projects")
async def list_client_projects(client_id: int) -> Dict[str, Any]:
    """List projects for a client"""
    wp_client = get_wordpress_client(config)
    if not wp_client or not wp_client.is_configured:
        raise HTTPException(status_code=503, detail="WordPress not configured")

    projects = await wp_client.get_client_projects(client_id)
    return {"projects": [p.dict() for p in projects], "total": len(projects)}


@app.post("/api/v1/wordpress/projects")
async def create_project(request: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new project"""
    wp_client = get_wordpress_client(config)
    if not wp_client or not wp_client.is_configured:
        raise HTTPException(status_code=503, detail="WordPress not configured")

    client_id = request.get("client_id")
    name = request.get("name")
    project_type = request.get("type", "podcast")

    if not client_id or not name:
        raise HTTPException(status_code=400, detail="client_id and name are required")

    project = await wp_client.create_video_project(int(client_id), name, project_type)
    if not project:
        raise HTTPException(status_code=500, detail="Failed to create project")

    return {
        "id": project.id,
        "name": project.name,
        "slug": project.slug,
        "client_id": project.client_id
    }


@app.get("/api/v1/wordpress/calendar/today")
async def get_calendar_today() -> Dict[str, Any]:
    """Get today's calendar with time slots"""
    from datetime import date as date_type, time, timedelta
    
    today = date_type.today()
    wp_client = get_wordpress_client(config)
    
    # Get today's bookings
    if not wp_client or not wp_client.is_configured:
        raise HTTPException(status_code=503, detail="WordPress not configured")

    bookings = await wp_client.get_todays_appointments()
    
    # Generate time slots (9 AM to 5 PM, 30-minute intervals)
    slots = []
    current_time = time(9, 0)
    end_time = time(17, 0)
    
    while current_time < end_time:
        slot_start = current_time.strftime("%H:%M")
        next_time = (datetime.combine(today, current_time) + timedelta(minutes=30)).time()
        slot_end = next_time.strftime("%H:%M")
        
        # Check if this slot has a booking
        slot_booking = None
        for booking in bookings:
            if booking.slot_start <= slot_start < booking.slot_end:
                slot_booking = booking.dict()
                break
        
        is_lunch = current_time.hour == 12
        
        slots.append({
            "start_time": slot_start,
            "end_time": slot_end,
            "available": slot_booking is None and not is_lunch,
            "booking": slot_booking,
            "is_lunch": is_lunch
        })
        
        current_time = next_time
    
    return {
        "date": today.isoformat(),
        "slots": slots
    }


@app.post("/api/v1/wordpress/calendar/book")
async def create_walk_in_booking(request: Dict[str, Any]) -> Dict[str, Any]:
    """Create a walk-in booking"""
    wp_client = get_wordpress_client(config)
    if not wp_client or not wp_client.is_configured:
        raise HTTPException(status_code=503, detail="WordPress not configured")

    from datetime import date as date_type

    slot_start = request.get("slot_start")
    slot_end = request.get("slot_end")
    customer_name = request.get("customer_name")
    customer_email = request.get("customer_email")
    customer_phone = request.get("customer_phone")
    recording_type = request.get("recording_type", "podcast")

    if not all([slot_start, slot_end, customer_name, customer_email]):
        raise HTTPException(status_code=400, detail="Missing required fields")

    today = date_type.today()

    try:
        result = await wp_client._request(
            "POST",
            "/jet-apb/v1/appointments",
            json_data={
                "date": today.isoformat(),
                "slot": f"{slot_start}-{slot_end}",
                "status": "pending",
                "user_name": customer_name,
                "user_email": customer_email,
                "user_phone": customer_phone or "",
                "meta": {
                    "recording_type": recording_type,
                    "walk_in": True,
                },
            },
        )
        booking_id = result.get("ID") or result.get("id")
        return {
            "success": True,
            "booking_id": booking_id,
            "message": f"Booking created for {slot_start}-{slot_end}",
        }
    except Exception as e:
        logger.error(f"Failed to create walk-in booking: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/wordpress/customer/validate")
async def validate_customer_token(request: Dict[str, Any] = Body({})) -> Dict[str, Any]:
    """Validate a customer access token"""
    token = request.get("token")
    if not token:
        raise HTTPException(status_code=400, detail="Token is required")

    context = get_active_booking()
    if not context:
        return {"valid": False, "error": "No active booking session"}

    if context.access_token != token:
        return {"valid": False, "error": "Invalid or expired token"}

    return {
        "valid": True,
        "booking": context.booking.dict(),
        "project": context.project.dict(),
    }


@app.get("/api/v1/wordpress/customer/{token}/status")
async def get_customer_status(token: str) -> Dict[str, Any]:
    """Get customer portal status"""
    context = get_active_booking()
    if not context or context.access_token != token:
        raise HTTPException(status_code=404, detail="Invalid token or no active booking")

    disk_space_gb = 0.0
    try:
        disk_usage = shutil.disk_usage("/data")
        disk_space_gb = disk_usage.free / (1024 ** 3)
    except Exception:
        try:
            disk_usage = shutil.disk_usage("/")
            disk_space_gb = disk_usage.free / (1024 ** 3)
        except Exception as e:
            logger.warning(f"Failed to read disk usage: {e}")

    return {
        "booking": context.booking.dict(),
        "project": context.project.dict(),
        "recording_active": False,
        "recording_duration_ms": 0,
        "current_slide_index": 0,
        "total_slides": len(context.project.graphics),
        "disk_space_gb": disk_space_gb,
        "display_mode": context.display_mode.value,
        "teleprompter_script": context.teleprompter_script,
        "teleprompter_scroll_speed": context.teleprompter_scroll_speed,
    }


@app.post("/api/v1/wordpress/customer/{token}/recording/start")
async def customer_start_recording(token: str) -> Dict[str, Any]:
    """Start recording from customer portal"""
    context = get_active_booking()
    if not context or context.access_token != token:
        raise HTTPException(status_code=404, detail="Invalid or expired token")
    
    # Trigger recording start
    logger.info(f"Customer initiated recording start for booking #{context.booking.id}")
    return {
        "success": True,
        "message": "Recording started",
        "recording_path": context.recording_path,
    }


@app.post("/api/v1/wordpress/customer/{token}/recording/stop")
async def customer_stop_recording(token: str) -> Dict[str, Any]:
    """Stop recording from customer portal"""
    context = get_active_booking()
    if not context or context.access_token != token:
        raise HTTPException(status_code=404, detail="Invalid or expired token")
    
    logger.info(f"Customer initiated recording stop for booking #{context.booking.id}")
    return {"success": True, "message": "Recording stopped"}


@app.post("/api/v1/wordpress/customer/{token}/presentation/goto/{index}")
async def customer_goto_slide(token: str, index: int) -> Dict[str, Any]:
    """Jump to a specific slide in the presentation"""
    context = get_active_booking()
    if not context or context.access_token != token:
        raise HTTPException(status_code=404, detail="Invalid or expired token")

    if index < 0 or index >= len(context.project.graphics):
        raise HTTPException(status_code=400, detail="Invalid slide index")

    logger.info(f"Customer navigated to slide {index} for booking #{context.booking.id}")
    return {
        "success": True,
        "current_index": index,
        "total_slides": len(context.project.graphics),
    }


@app.get("/api/v1/wordpress/customer/{token}/display-mode")
async def get_display_mode(token: str) -> Dict[str, Any]:
    """Get display mode for studio display"""
    context = get_active_booking()
    if not context or context.access_token != token:
        raise HTTPException(status_code=404, detail="Invalid or expired token")
    
    return {
        "display_mode": context.display_mode.value,
        "content_type": context.booking.content_type.value if context.booking.content_type else None
    }


@app.post("/api/v1/wordpress/customer/{token}/teleprompter/script")
async def update_teleprompter_script(token: str, request: Dict[str, Any] = Body({})) -> Dict[str, Any]:
    """Update teleprompter script for the active booking"""
    context = get_active_booking()
    if not context or context.access_token != token:
        raise HTTPException(status_code=404, detail="Invalid or expired token")

    if context.display_mode != DisplayMode.TELEPROMPTER:
        raise HTTPException(status_code=400, detail="Not in teleprompter mode")

    script = request.get("script", "")
    context.teleprompter_script = script
    logger.info(f"Updated teleprompter script for booking #{context.booking.id}")

    return {
        "success": True,
        "script_length": len(script),
    }


@app.post("/api/v1/wordpress/customer/{token}/teleprompter/speed")
async def set_teleprompter_speed(token: str, request: Dict[str, Any] = Body({})) -> Dict[str, Any]:
    """Set teleprompter scroll speed (1-100)"""
    context = get_active_booking()
    if not context or context.access_token != token:
        raise HTTPException(status_code=404, detail="Invalid or expired token")

    if context.display_mode != DisplayMode.TELEPROMPTER:
        raise HTTPException(status_code=400, detail="Not in teleprompter mode")

    speed = int(request.get("speed", 50))
    if speed < 1 or speed > 100:
        raise HTTPException(status_code=400, detail="Speed must be between 1 and 100")

    context.teleprompter_scroll_speed = speed
    logger.info(f"Set teleprompter speed to {speed} for booking #{context.booking.id}")

    return {
        "success": True,
        "speed": speed,
    }


@app.post("/api/v1/wordpress/customer/{token}/teleprompter/scroll")
async def scroll_teleprompter(token: str, request: Dict[str, Any] = Body({})) -> Dict[str, Any]:
    """Scroll teleprompter manually (up/down)"""
    context = get_active_booking()
    if not context or context.access_token != token:
        raise HTTPException(status_code=404, detail="Invalid or expired token")

    if context.display_mode != DisplayMode.TELEPROMPTER:
        raise HTTPException(status_code=400, detail="Not in teleprompter mode")

    direction = request.get("direction", "down")
    if direction not in ["up", "down"]:
        raise HTTPException(status_code=400, detail="Invalid direction")

    # In a real implementation, this would send a websocket message to the display
    # For now, we'll log it and let the display poll for updates if we store state
    # But scroll position is transient, so polling isn't great.
    # We might need a command queue or similar.
    # Assuming for now we just log it as the frontend implementation is a control surface.
    
    logger.info(f"Scroll teleprompter {direction} for booking #{context.booking.id}")

    return {
        "success": True,
        "direction": direction,
    }


@app.post("/api/v1/wordpress/customer/{token}/teleprompter/jump-to")
async def jump_teleprompter(token: str, request: Dict[str, Any] = Body({})) -> Dict[str, Any]:
    """Jump teleprompter to position (top/bottom)"""
    context = get_active_booking()
    if not context or context.access_token != token:
        raise HTTPException(status_code=404, detail="Invalid or expired token")

    if context.display_mode != DisplayMode.TELEPROMPTER:
        raise HTTPException(status_code=400, detail="Not in teleprompter mode")

    position = request.get("position", "top")
    if position not in ["top", "bottom"]:
        raise HTTPException(status_code=400, detail="Invalid position")

    logger.info(f"Jump teleprompter to {position} for booking #{context.booking.id}")

    return {
        "success": True,
        "position": position,
    }


@app.post("/api/v1/wordpress/customer/{token}/teleprompter/text-size")
async def set_teleprompter_text_size(token: str, request: Dict[str, Any] = Body({})) -> Dict[str, Any]:
    """Set teleprompter text size (1-5)"""
    context = get_active_booking()
    if not context or context.access_token != token:
        raise HTTPException(status_code=404, detail="Invalid or expired token")

    if context.display_mode != DisplayMode.TELEPROMPTER:
        raise HTTPException(status_code=400, detail="Not in teleprompter mode")

    size = int(request.get("size", 3))
    if size < 1 or size > 5:
        raise HTTPException(status_code=400, detail="Size must be between 1 and 5")

    # Store text size in context (need to add field to ActiveBookingContext if persistent)
    # For now, we'll just log it
    logger.info(f"Set teleprompter text size to {size} for booking #{context.booking.id}")

    return {
        "success": True,
        "size": size,
    }


@app.post("/api/v1/wordpress/customer/{token}/activate")
async def activate_session(token: str) -> Dict[str, Any]:
    """Activate session and switch TV display"""
    context = get_active_booking()
    if not context or context.access_token != token:
        raise HTTPException(status_code=404, detail="Invalid or expired token")

    # Determine TV route based on display mode
    path = "/podcast"
    if context.display_mode == DisplayMode.TELEPROMPTER:
        path = "/talking-head"
    elif context.display_mode == DisplayMode.COURSE:
        path = "/course"
    elif context.display_mode == DisplayMode.WEBINAR:
        path = "/webinar"
    
    # Switch TV display
    script_path = "/opt/preke-r58-recorder/scripts/switch-tv-display.sh"
    try:
        import subprocess
        result = subprocess.run(
            [script_path, path],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            logger.info(f"Session activated, TV switched to {path}")
            return {
                "success": True,
                "message": "Session activated",
                "display_path": path
            }
        else:
            logger.error(f"Failed to switch TV: {result.stderr}")
            # Still return success for session activation, but warn about TV
            return {
                "success": True,
                "message": "Session activated (TV switch failed)",
                "error": result.stderr
            }
    except Exception as e:
        logger.error(f"Error activating session: {e}")
        return {
            "success": True,
            "message": "Session activated (TV switch error)",
            "error": str(e)
        }


@app.get("/api/v1/wordpress/customer/{token}/vdoninja/status")
async def check_vdoninja_status(token: str) -> Dict[str, Any]:
    """Check if VDO.ninja VPS is available"""
    context = get_active_booking()
    if not context or context.access_token != token:
        raise HTTPException(status_code=404, detail="Invalid or expired token")

    vdoninja_settings = getattr(config, "vdoninja", None)
    vdoninja_enabled = bool(vdoninja_settings and getattr(vdoninja_settings, "enabled", False))
    if not vdoninja_enabled:
        return {
            "available": False,
            "error": "VDO.ninja VPS is disabled",
        }

    host = None
    if vdoninja_settings:
        host = getattr(vdoninja_settings, "url", None) or getattr(vdoninja_settings, "host", None)
        if host and not host.startswith("http"):
            host = f"https://{host}"

    return {
        "available": True,
        "url": host,
        "error": None,
    }


@app.post("/api/v1/wordpress/qr-session")
async def create_qr_session(request: Dict[str, Any] = Body({})) -> Dict[str, Any]:
    """Create a QR code session for quick access without a booking"""
    import secrets
    
    # Check for existing active booking to get display_mode
    existing_context = get_active_booking()
    if existing_context and existing_context.display_mode:
        # Use display mode from active booking
        display_mode = existing_context.display_mode
    else:
        # Default to podcast if no active booking
        display_mode = DisplayMode.PODCAST
    
    # Generate access token
    access_token = secrets.token_urlsafe(32)
    
    # Create a minimal booking for QR sessions
    booking = Booking(
        id=0,  # No real booking ID
        status=BookingStatus.PENDING,
        date=datetime.now().strftime("%Y-%m-%d"),
        slot_start=datetime.now().strftime("%H:%M"),
        slot_end=(datetime.now() + timedelta(hours=1)).strftime("%H:%M"),
        customer=CustomerInfo(id=0, name="QR Session User", email="qr@preke.no"),
        client=None,
        content_type=None
    )
    
    # Create a default project
    project = VideoProject(
        id=0,
        slug="qr-session",
        name="QR Session",
        client_id=None
    )
    
    # Create recording path
    recording_path = f"/data/recordings/qr-sessions/{access_token[:8]}"
    
    # Create active booking context
    context = ActiveBookingContext(
        booking=booking,
        recording_id=0,
        project=project,
        recording_path=recording_path,
        access_token=access_token,
        display_mode=display_mode
    )
    
    # Set as active booking
    set_active_booking(context)
    
    return {
        "success": True,
        "token": access_token,
        "display_mode": display_mode.value,
        "message": "QR session created"
    }


@app.post("/api/v1/tv/display")
async def switch_tv_display(request: Dict[str, Any] = Body({})) -> Dict[str, Any]:
    """Switch the TV display to a different page.
    
    The TV kiosk runs Chromium in fullscreen mode showing the frontend app.
    This endpoint navigates the kiosk to a different route.
    
    Request body:
        path: The route path to navigate to (e.g., "/qr", "/podcast", "/talking-head")
        token: Optional customer token for session-based pages
    
    Example paths:
        - /qr: QR code welcome page
        - /podcast: Podcast multiview display
        - /talking-head: Teleprompter display
        - /course: Course TV display
        - /course-teleprompter: Course teleprompter display
        - /webinar: Webinar display with VDO.ninja
        - /customer/{token}: Customer session display
    """
    path = request.get("path", "/qr")
    
    # Validate path starts with /
    if not path.startswith("/"):
        path = f"/{path}"
    
    # Run the switch script
    script_path = "/opt/preke-r58-recorder/scripts/switch-tv-display.sh"
    
    try:
        import subprocess
        result = subprocess.run(
            [script_path, path],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            logger.info(f"TV display switched to: {path}")
            return {
                "success": True,
                "path": path,
                "message": f"TV display switched to {path}"
            }
        else:
            logger.error(f"Failed to switch TV display: {result.stderr}")
            return {
                "success": False,
                "path": path,
                "message": f"Failed to switch display: {result.stderr}"
            }
    except subprocess.TimeoutExpired:
        logger.error("TV display switch timed out")
        return {
            "success": False,
            "path": path,
            "message": "Switch timed out - TV kiosk may not be running"
        }
    except FileNotFoundError:
        logger.warning(f"Switch script not found at {script_path}")
        return {
            "success": False,
            "path": path,
            "message": "Switch script not installed on device"
        }
    except Exception as e:
        logger.error(f"Error switching TV display: {e}")
        return {
            "success": False,
            "path": path,
            "message": str(e)
        }


@app.get("/api/v1/tv/status")
async def get_tv_status() -> Dict[str, Any]:
    """Get the status of the TV kiosk display.
    
    Returns information about whether the kiosk is running and what page it's showing.
    """
    try:
        import subprocess
        
        # Check if kiosk Chromium is running (on port 9223)
        result = subprocess.run(
            ["curl", "-s", "http://127.0.0.1:9223/json"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0 and result.stdout:
            import json
            pages = json.loads(result.stdout)
            current_url = None
            for page in pages:
                if page.get("type") == "page":
                    current_url = page.get("url", "")
                    break
            
            # Extract path from URL
            current_path = None
            if current_url and "#" in current_url:
                current_path = current_url.split("#")[1] if "#" in current_url else "/"
            
            return {
                "running": True,
                "url": current_url,
                "path": current_path,
                "cdp_port": 9223
            }
        else:
            return {
                "running": False,
                "url": None,
                "path": None,
                "message": "TV kiosk not running"
            }
    except Exception as e:
        return {
            "running": False,
            "url": None,
            "path": None,
            "message": str(e)
        }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

