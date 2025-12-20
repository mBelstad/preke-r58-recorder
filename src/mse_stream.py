"""MSE (Media Source Extensions) streaming over WebSocket.

Streams H.265 video from MediaMTX RTSP to browser via WebSocket using fMP4 format.
Works through Cloudflare Tunnel (WSS) with lower latency than HLS.
"""
import asyncio
import logging
import subprocess
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter()


class MSEStreamer:
    """Manages FFmpeg process for MSE streaming."""
    
    def __init__(self, stream_path: str, codec: str = "hevc"):
        """Initialize MSE streamer.
        
        Args:
            stream_path: MediaMTX stream path (e.g., "cam0")
            codec: Video codec - "hevc" (H.265) or "h264"
        """
        self.stream_path = stream_path
        self.codec = codec
        self.process: Optional[subprocess.Popen] = None
        self.rtsp_url = f"rtsp://localhost:8554/{stream_path}"
        
    async def start(self) -> bool:
        """Start FFmpeg process to convert RTSP to fMP4 fragments.
        
        Returns:
            True if started successfully, False otherwise
        """
        try:
            # FFmpeg command to convert RTSP H.265 to fMP4 fragments
            # -c:v copy: No transcoding (copy H.265 as-is)
            # -f mp4: Output as MP4 container
            # -movflags: fMP4 flags for streaming
            #   - frag_keyframe: Start new fragment at each keyframe
            #   - empty_moov: Put moov atom at start (required for MSE)
            #   - default_base_moof: Use default base for moof atoms
            #   - omit_tfhd_offset: Omit offset in tfhd (better compatibility)
            # -frag_duration: Fragment duration in microseconds (500ms = 500000us)
            # -reset_timestamps 1: Reset timestamps to start from 0
            
            if self.codec == "h264":
                # Transcode to H.264 for Firefox/unsupported browsers
                video_args = [
                    "-c:v", "libx264",
                    "-preset", "ultrafast",
                    "-tune", "zerolatency",
                    "-profile:v", "baseline",
                    "-level", "3.0",
                    "-b:v", "2M",
                    "-maxrate", "2M",
                    "-bufsize", "4M",
                    "-g", "30",  # Keyframe every 30 frames (1s at 30fps)
                ]
            else:
                # Copy H.265 as-is (no transcoding)
                video_args = ["-c:v", "copy"]
            
            cmd = [
                "ffmpeg",
                "-rtsp_transport", "tcp",
                "-i", self.rtsp_url,
                *video_args,
                "-an",  # No audio for now
                "-f", "mp4",
                "-movflags", "frag_keyframe+empty_moov+default_base_moof+omit_tfhd_offset",
                "-frag_duration", "500000",  # 500ms fragments
                "-reset_timestamps", "1",
                "-loglevel", "warning",
                "pipe:1"
            ]
            
            logger.info(f"Starting MSE stream for {self.stream_path} (codec: {self.codec})")
            logger.debug(f"FFmpeg command: {' '.join(cmd)}")
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=65536  # 64KB buffer
            )
            
            # Wait a bit to check if process started successfully
            await asyncio.sleep(0.5)
            if self.process.poll() is not None:
                stderr = self.process.stderr.read().decode() if self.process.stderr else ""
                logger.error(f"FFmpeg process failed to start: {stderr}")
                return False
            
            logger.info(f"MSE stream started for {self.stream_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start MSE stream: {e}")
            return False
    
    async def read_chunk(self) -> Optional[bytes]:
        """Read next fMP4 chunk from FFmpeg stdout.
        
        Returns:
            Binary chunk data or None if stream ended
        """
        if not self.process or not self.process.stdout:
            return None
        
        try:
            # Read chunk in non-blocking way
            loop = asyncio.get_event_loop()
            chunk = await loop.run_in_executor(
                None,
                self.process.stdout.read,
                65536  # Read up to 64KB at a time
            )
            
            if not chunk:
                logger.debug(f"No more data from FFmpeg for {self.stream_path}")
                return None
            
            return chunk
            
        except Exception as e:
            logger.error(f"Error reading from FFmpeg: {e}")
            return None
    
    def stop(self):
        """Stop FFmpeg process."""
        if self.process:
            logger.info(f"Stopping MSE stream for {self.stream_path}")
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning(f"FFmpeg didn't terminate, killing process")
                self.process.kill()
            except Exception as e:
                logger.error(f"Error stopping FFmpeg: {e}")
            finally:
                self.process = None


@router.websocket("/ws/mse/{stream_path}")
async def mse_stream_endpoint(websocket: WebSocket, stream_path: str):
    """WebSocket endpoint for MSE streaming.
    
    Args:
        websocket: WebSocket connection
        stream_path: MediaMTX stream path (e.g., "cam0", "cam1")
    """
    await websocket.accept()
    logger.info(f"MSE WebSocket connected for {stream_path}")
    
    # Check if client wants H.264 (for Firefox)
    # Client can send "h264" as first message to request transcoding
    codec = "hevc"  # Default to H.265
    
    streamer = None
    
    try:
        # Wait briefly for codec preference (non-blocking)
        try:
            codec_msg = await asyncio.wait_for(
                websocket.receive_text(),
                timeout=0.5
            )
            if codec_msg.lower() == "h264":
                codec = "h264"
                logger.info(f"Client requested H.264 transcoding for {stream_path}")
        except asyncio.TimeoutError:
            # No codec preference received, use default H.265
            pass
        
        # Create and start streamer
        streamer = MSEStreamer(stream_path, codec=codec)
        
        if not await streamer.start():
            await websocket.send_text("error:failed_to_start")
            return
        
        # Send codec info to client
        await websocket.send_text(f"codec:{codec}")
        
        # Stream fMP4 chunks to client
        chunk_count = 0
        bytes_sent = 0
        
        while True:
            chunk = await streamer.read_chunk()
            
            if chunk is None:
                logger.info(f"Stream ended for {stream_path} after {chunk_count} chunks ({bytes_sent} bytes)")
                break
            
            try:
                await websocket.send_bytes(chunk)
                chunk_count += 1
                bytes_sent += len(chunk)
                
                # Log progress every 100 chunks (~50 seconds at 500ms fragments)
                if chunk_count % 100 == 0:
                    logger.debug(f"Sent {chunk_count} chunks ({bytes_sent / 1024 / 1024:.1f} MB) for {stream_path}")
                
            except Exception as e:
                logger.error(f"Error sending chunk: {e}")
                break
        
    except WebSocketDisconnect:
        logger.info(f"MSE WebSocket disconnected for {stream_path}")
    except Exception as e:
        logger.error(f"MSE streaming error for {stream_path}: {e}")
    finally:
        if streamer:
            streamer.stop()
        try:
            await websocket.close()
        except:
            pass


@router.get("/api/mse/test")
async def mse_test_info():
    """Get MSE streaming test information."""
    return {
        "status": "available",
        "endpoints": {
            "websocket": "/ws/mse/{stream_path}",
            "test_page": "/static/mse_test.html"
        },
        "supported_codecs": ["hevc", "h264"],
        "supported_streams": ["cam0", "cam1", "cam2", "cam3", "mixer_program"],
        "usage": {
            "connect": "ws://hostname/ws/mse/cam0",
            "codec_selection": "Send 'h264' as first message for H.264 transcoding, otherwise H.265 is used"
        }
    }
