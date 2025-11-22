"""FastAPI application for R58 recorder."""
import logging
from pathlib import Path
from typing import Dict
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from .config import AppConfig
from .recorder import Recorder

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

# Initialize recorder
recorder = Recorder(config)

# Create FastAPI app
app = FastAPI(
    title="R58 Recorder API",
    description="Recording API for Mekotronics R58 4x4 3S",
    version="1.0.0",
)


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


@app.get("/status")
async def get_status() -> Dict[str, Dict[str, str]]:
    """Get status of all cameras."""
    statuses = recorder.get_status()
    return {
        "cameras": {
            cam_id: {"status": status, "config": cam_id in config.cameras}
            for cam_id, status in statuses.items()
        }
    }


@app.get("/status/{cam_id}")
async def get_camera_status(cam_id: str) -> Dict[str, str]:
    """Get status of a specific camera."""
    if cam_id not in config.cameras:
        raise HTTPException(status_code=404, detail=f"Camera {cam_id} not found")

    status = recorder.get_camera_status(cam_id)
    if status is None:
        raise HTTPException(status_code=404, detail=f"Camera {cam_id} not found")

    return {"camera": cam_id, "status": status}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

