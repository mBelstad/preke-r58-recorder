"""FastAPI application for R58 recorder."""
import asyncio
import logging
import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Response, Request
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
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

# Initialize Graphics plugin (optional)
graphics_plugin = None
graphics_renderer = None
if config.graphics.enabled:
    try:
        from .graphics import create_graphics_plugin
        graphics_plugin = create_graphics_plugin()
        graphics_plugin.initialize(config)
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
        mixer_plugin.initialize(config, ingest_manager, database, graphics_plugin)
        mixer_core = mixer_plugin.core
        scene_manager = mixer_plugin.scene_manager
        scene_queue = mixer_plugin.scene_queue
        logger.info("Mixer plugin initialized")
    except Exception as e:
        logger.error(f"Failed to initialize mixer plugin: {e}")
        mixer_plugin = None  # Continue without mixer
else:
    logger.info("Mixer plugin disabled in configuration")

# Initialize Cloudflare Calls manager (for remote guests)
calls_manager: Optional[Any] = None
calls_relay: Optional[Any] = None
if config.cloudflare.account_id and config.cloudflare.calls_api_token:
    try:
        from .cloudflare_calls import CloudflareCallsManager
        from .calls_relay import CloudflareCallsRelay
        
        calls_manager = CloudflareCallsManager(
            account_id=config.cloudflare.account_id,
            app_id=config.cloudflare.calls_app_id,
            api_token=config.cloudflare.calls_api_token
        )
        
        calls_relay = CloudflareCallsRelay(
            app_id=config.cloudflare.calls_app_id,
            api_token=config.cloudflare.calls_api_token
        )
        
        logger.info("Cloudflare Calls manager and relay initialized for remote guests")
    except Exception as e:
        logger.error(f"Failed to initialize Cloudflare Calls: {e}")
        calls_manager = None
        calls_relay = None
else:
    logger.info("Cloudflare Calls disabled - no credentials configured")

# Create FastAPI app
app = FastAPI(
    title="R58 Recorder API",
    description="Recording API for Mekotronics R58 4x4 3S",
    version="1.0.0",
)

# Mount static files for frontend
static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Mount Reveal.js dist files for serving presentations
reveal_js_dist_path = Path(__file__).parent.parent / "reveal.js" / "dist"
if reveal_js_dist_path.exists():
    app.mount("/reveal.js", StaticFiles(directory=str(reveal_js_dist_path)), name="reveal.js")
    logger.info(f"Mounted Reveal.js dist files at /reveal.js")

# Create uploads directory for graphics
uploads_dir = Path(__file__).parent.parent / "uploads"
uploads_dir.mkdir(exist_ok=True)
images_dir = uploads_dir / "images"
images_dir.mkdir(exist_ok=True)
videos_dir = uploads_dir / "videos"
videos_dir.mkdir(exist_ok=True)

# Mount uploads directory for serving files
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")


@app.on_event("startup")
async def startup_event():
    """Start ingest pipelines on application startup."""
    logger.info("Starting ingest pipelines for all cameras...")
    results = ingest_manager.start_all()
    for cam_id, success in results.items():
        if success:
            logger.info(f"✓ Ingest started for {cam_id}")
        else:
            logger.warning(f"✗ Failed to start ingest for {cam_id}")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the frontend."""
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
    return "<h1>Switcher Interface</h1><p>Switcher interface not found.</p>"


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
    
    return {
        "status": "healthy",
        "platform": config.platform,
        "gstreamer": gst_status,
        "gstreamer_error": gst_error
    }


@app.post("/record/start/{cam_id}")
async def start_recording(cam_id: str) -> Dict[str, str]:
    """Start recording for a specific camera."""
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
    
    # Add disk space info
    try:
        disk = shutil.disk_usage("/mnt/sdcard")
        disk_info = {
            "free_gb": round(disk.free / (1024**3), 2),
            "total_gb": round(disk.total / (1024**3), 2),
            "used_gb": round(disk.used / (1024**3), 2),
            "percent_used": round((disk.used / disk.total) * 100, 1)
        }
    except Exception as e:
        logger.error(f"Failed to get disk space: {e}")
        disk_info = {"error": str(e)}
    
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


# HLS Proxy endpoints - allows remote access through Cloudflare Tunnel
MEDIAMTX_HLS_BASE = "http://localhost:8888"


@app.get("/hls/{stream_path:path}")
async def proxy_hls(stream_path: str):
    """Proxy HLS streams from MediaMTX for remote access.
    
    This enables video streaming through Cloudflare Tunnel by proxying
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
        
        # Forward to MediaMTX WHIP endpoint
        mediamtx_whip_url = f"http://localhost:8889/{stream_path}/whip"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                mediamtx_whip_url,
                content=sdp_offer,
                headers={
                    "Content-Type": "application/sdp"
                },
                timeout=10.0
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
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "POST, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type",
                }
            )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="WHIP timeout - MediaMTX may not be responding")
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Cannot connect to MediaMTX - service may be down")
    except Exception as e:
        logger.error(f"WHIP proxy error for {stream_path}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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


@app.get("/api/turn-credentials")
async def get_turn_credentials() -> Dict[str, Any]:
    """Generate short-lived Cloudflare TURN credentials for remote WebRTC guests.
    
    This endpoint calls the Cloudflare TURN API to generate ICE servers with
    temporary credentials (24 hour TTL). These credentials enable remote guests
    to connect via WebRTC through the Cloudflare Tunnel by using TURN relay.
    """
    TURN_TOKEN_ID = "79d61c83455a63d11a18c17bedb53d3f"
    API_TOKEN = "9054653545421be55e42219295b74b1036d261e1c0259c2cf410fb9d8a372984"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://rtc.live.cloudflare.com/v1/turn/keys/{TURN_TOKEN_ID}/credentials/generate-ice-servers",
                headers={
                    "Authorization": f"Bearer {API_TOKEN}",
                    "Content-Type": "application/json"
                },
                json={"ttl": 86400},  # 24 hour validity
                timeout=10.0
            )
            
            if not response.is_success:
                logger.error(f"Cloudflare TURN API error: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Failed to get TURN credentials: {response.text}"
                )
            
            return response.json()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="TURN API timeout")
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Cannot connect to Cloudflare TURN API")
    except Exception as e:
        logger.error(f"Error getting TURN credentials: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
            "frames_received": 0,  # TODO: Add frame counter to pipelines
            "frames_dropped": 0,  # TODO: Add drop counter to pipelines
            "last_frame_timestamp": None,  # TODO: Add timestamp tracking
            "error": pipeline_error
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
        for file_path in sorted(recordings_dir.glob("*.mp4"), key=os.path.getmtime, reverse=True):
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

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="video/mp4",
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
        
        # Find all MP4 files
        for file_path in recordings_dir.glob("*.mp4"):
            try:
                stat = file_path.stat()
                
                # Extract date from filename (format: recording_YYYYMMDD_HHMMSS.mp4)
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


@app.post("/api/mixer/start")
async def start_mixer() -> Dict[str, str]:
    """Start the mixer pipeline."""
    if not mixer_core:
        raise HTTPException(status_code=503, detail="Mixer not enabled")
    
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


# Cloudflare Calls API endpoints (for remote guests)
@app.post("/api/calls/whip/{guest_id}")
async def cloudflare_calls_whip(guest_id: str, request: Request) -> Response:
    """Proxy WHIP requests to Cloudflare Calls for remote guests.
    
    This endpoint receives SDP offers from guests, forwards them to Cloudflare Calls,
    and returns the SDP answer. The guest then connects to Cloudflare's infrastructure.
    After connection, starts a relay to pull the stream and push to MediaMTX.
    """
    if not calls_manager or not calls_relay:
        raise HTTPException(status_code=503, detail="Cloudflare Calls not configured")
    
    if guest_id not in config.guests or not config.guests[guest_id].enabled:
        raise HTTPException(status_code=400, detail=f"Invalid or disabled guest: {guest_id}")
    
    try:
        # Read SDP offer from request body
        sdp_offer = (await request.body()).decode('utf-8')
        
        # Create guest session using two-step flow (returns session_id, sdp_answer, track_names)
        session_data = await calls_manager.create_guest_session(guest_id, sdp_offer)
        session_id = session_data['session_id']
        track_names = session_data['track_names']
        
        logger.info(f"Cloudflare Calls session created for {guest_id}: {session_id} with tracks {track_names}")
        
        # Start relay in background (after a short delay to let tracks be published)
        rtmp_port = config.mediamtx.rtmp_port
        rtmp_url = f"rtmp://127.0.0.1:{rtmp_port}/{guest_id}"
        
        async def start_relay_delayed():
            await asyncio.sleep(2)  # Wait for guest to publish tracks
            try:
                await calls_relay.subscribe_and_relay(
                    guest_session_id=session_id,
                    track_names=track_names,
                    guest_id=guest_id,
                    rtmp_url=rtmp_url
                )
                logger.info(f"Relay started for {guest_id}: Cloudflare -> MediaMTX")
            except Exception as e:
                logger.error(f"Failed to start relay for {guest_id}: {e}")
        
        asyncio.create_task(start_relay_delayed())
        
        # Return SDP answer
        return Response(
            content=session_data["sdp_answer"],
            media_type="application/sdp",
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to create Cloudflare Calls session for {guest_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")


@app.options("/api/calls/whip/{guest_id}")
async def cloudflare_calls_whip_options(guest_id: str):
    """Handle CORS preflight for Cloudflare Calls WHIP requests."""
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        }
    )


@app.delete("/api/calls/session/{guest_id}")
async def close_calls_session(guest_id: str) -> Dict[str, str]:
    """Close a Cloudflare Calls session and relay for a guest."""
    if not calls_manager or not calls_relay:
        raise HTTPException(status_code=503, detail="Cloudflare Calls not configured")
    
    try:
        # Stop relay first
        await calls_relay.stop_relay(guest_id)
        
        # Then close Cloudflare session
        success = await calls_manager.close_guest_session(guest_id)
        
        if success:
            logger.info(f"Closed Cloudflare Calls session and relay for {guest_id}")
            return {"status": "closed", "guest_id": guest_id}
        else:
            return {"status": "no_session", "guest_id": guest_id}
    except Exception as e:
        logger.error(f"Error closing Cloudflare Calls session for {guest_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to close session: {str(e)}")


@app.get("/api/calls/sessions")
async def get_active_calls_sessions() -> Dict[str, Any]:
    """Get all active Cloudflare Calls sessions."""
    if not calls_manager:
        return {"sessions": {}}
    
    active_sessions = calls_manager.get_active_sessions()
    return {"sessions": active_sessions}


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


# Cleanup on shutdown
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources on application shutdown."""
    logger.info("Application shutting down...")
    
    # Cleanup Cloudflare Calls relays
    if calls_relay:
        try:
            await calls_relay.cleanup_all()
        except Exception as e:
            logger.error(f"Error cleaning up Cloudflare Calls relays: {e}")
    
    # Cleanup Cloudflare Calls sessions
    if calls_manager:
        try:
            await calls_manager.cleanup_all_sessions()
        except Exception as e:
            logger.error(f"Error cleaning up Cloudflare Calls sessions: {e}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

