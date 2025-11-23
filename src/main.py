"""FastAPI application for R58 recorder."""
import logging
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from .config import AppConfig
from .recorder import Recorder
from .preview import PreviewManager
from .mixer.scenes import SceneManager
from .mixer.core import MixerCore

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

# Initialize recorder and preview manager
recorder = Recorder(config)
preview_manager = PreviewManager(config)

# Initialize mixer (if enabled)
mixer_core: Optional[MixerCore] = None
scene_manager: Optional[SceneManager] = None
if config.mixer.enabled:
    scene_manager = SceneManager(scenes_dir=config.mixer.scenes_dir)
    mixer_core = MixerCore(
        config=config,
        scene_manager=scene_manager,
        output_resolution=config.mixer.output_resolution,
        output_bitrate=config.mixer.output_bitrate,
        output_codec=config.mixer.output_codec,
        recording_enabled=config.mixer.recording_enabled,
        recording_path=config.mixer.recording_path,
        mediamtx_enabled=config.mixer.mediamtx_enabled,
        mediamtx_path=config.mixer.mediamtx_path,
    )
    logger.info("Mixer Core initialized")
else:
    logger.info("Mixer Core disabled in configuration")

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


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the frontend."""
    index_path = Path(__file__).parent / "static" / "index.html"
    if index_path.exists():
        return index_path.read_text()
    return "<h1>R58 Recorder API</h1><p>Frontend not found. API is available at /docs</p>"


@app.get("/health")
async def health() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "platform": config.platform}


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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

