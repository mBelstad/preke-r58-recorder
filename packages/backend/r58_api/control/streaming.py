"""Streaming Control API - RTMP/SRT relay configuration via MediaMTX runOnReady hook"""
import logging
from typing import List, Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/streaming", tags=["Streaming"])

# MediaMTX API endpoint
MEDIAMTX_API = "http://localhost:9997"


class RTMPDestination(BaseModel):
    """RTMP streaming destination configuration"""
    platform: str  # youtube, twitch, facebook, custom
    rtmp_url: str
    stream_key: str
    enabled: bool = True


class StartStreamingRequest(BaseModel):
    """Request to start RTMP relay from MediaMTX to external platform"""
    destinations: List[RTMPDestination]


class StreamingStatus(BaseModel):
    """Current streaming status"""
    active: bool
    destinations: List[RTMPDestination]
    mixer_program_active: bool  # Whether mixer_program stream is active in MediaMTX
    run_on_ready: Optional[str] = None  # Current runOnReady command if configured


def build_ffmpeg_relay_command(destinations: List[RTMPDestination]) -> str:
    """
    Build FFmpeg command to relay to multiple RTMP destinations.
    
    Uses tee muxer for multiple outputs to avoid re-encoding.
    """
    if not destinations:
        return ""
    
    # For single destination, simple command
    if len(destinations) == 1:
        dest = destinations[0]
        rtmp_url = f"{dest.rtmp_url}{dest.stream_key}"
        return f"ffmpeg -i rtsp://localhost:8554/mixer_program -c copy -f flv '{rtmp_url}'"
    
    # For multiple destinations, use tee muxer
    outputs = []
    for dest in destinations:
        rtmp_url = f"{dest.rtmp_url}{dest.stream_key}"
        # Escape special characters for tee muxer
        outputs.append(f"[f=flv]{rtmp_url}")
    
    tee_output = "|".join(outputs)
    return f"ffmpeg -i rtsp://localhost:8554/mixer_program -c copy -f tee '{tee_output}'"


@router.post("/rtmp/start")
async def start_rtmp_streaming(request: StartStreamingRequest):
    """
    Start RTMP relay using MediaMTX's runOnReady hook.
    
    This configures MediaMTX to automatically spawn FFmpeg when the
    mixer_program stream becomes ready. MediaMTX manages the FFmpeg
    process lifecycle, including automatic restart on failure.
    
    Benefits over manual FFmpeg:
    - Automatic start when stream is published
    - Automatic stop when stream ends
    - Automatic restart on FFmpeg crash (runOnReadyRestart: true)
    - No need for systemd services
    - Process managed by MediaMTX
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
            "runOnReadyRestart": True  # Restart FFmpeg if it crashes
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
        raise HTTPException(
            status_code=502, 
            detail=f"Failed to configure MediaMTX: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Failed to configure RTMP streaming: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rtmp/stop")
async def stop_rtmp_streaming():
    """
    Stop RTMP relay by removing the runOnReady hook from MediaMTX.
    
    This will terminate any running FFmpeg processes managed by MediaMTX.
    """
    try:
        # Remove runOnReady hook from mixer_program path
        config = {
            "source": "publisher",
            "runOnReady": "",  # Clear the hook
            "runOnReadyRestart": False
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.patch(
                f"{MEDIAMTX_API}/v3/config/paths/patch/mixer_program",
                json=config
            )
            
            # 404 is fine - path might not exist
            if response.status_code != 404:
                response.raise_for_status()
        
        logger.info("RTMP relay stopped - runOnReady hook removed")
        
        return {
            "status": "success",
            "message": "RTMP relay stopped"
        }
        
    except httpx.HTTPError as e:
        logger.error(f"MediaMTX API error: {e}")
        raise HTTPException(
            status_code=502, 
            detail=f"Failed to stop RTMP relay: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Failed to stop RTMP streaming: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_streaming_status():
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
            
            return {
                "active": mixer_active,
                "mixer_program_active": mixer_active,
                "rtmp_relay_configured": bool(run_on_ready),
                "run_on_ready": run_on_ready or None,
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


@router.get("/destinations")
async def get_streaming_destinations():
    """
    Get currently configured RTMP destinations from MediaMTX runOnReady hook.
    
    Parses the FFmpeg command to extract destination URLs.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{MEDIAMTX_API}/v3/config/paths/get/mixer_program"
            )
            
            if response.status_code == 404:
                return {"destinations": [], "configured": False}
            
            response.raise_for_status()
            data = response.json()
            
            run_on_ready = data.get("runOnReady", "")
            
            if not run_on_ready:
                return {"destinations": [], "configured": False}
            
            # Parse destinations from FFmpeg command
            # This is a simple parser - in production you might store
            # destinations separately in a database
            destinations = []
            if "rtmp://" in run_on_ready:
                # Extract RTMP URLs from command
                import re
                rtmp_urls = re.findall(r"rtmp://[^\s'\"]+", run_on_ready)
                for url in rtmp_urls:
                    # Determine platform from URL
                    platform = "custom"
                    if "youtube.com" in url or "rtmp.youtube.com" in url:
                        platform = "youtube"
                    elif "twitch.tv" in url:
                        platform = "twitch"
                    elif "facebook.com" in url:
                        platform = "facebook"
                    
                    destinations.append({
                        "platform": platform,
                        "url": url,
                        "enabled": True
                    })
            
            return {
                "destinations": destinations,
                "configured": True,
                "raw_command": run_on_ready
            }
            
    except httpx.HTTPError:
        return {"destinations": [], "configured": False, "error": "MediaMTX API not available"}
    except Exception as e:
        logger.error(f"Failed to get destinations: {e}")
        raise HTTPException(status_code=500, detail=str(e))
