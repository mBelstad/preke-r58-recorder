"""Cloudflare Calls relay service - subscribes to tracks and relays to MediaMTX."""
import asyncio
import logging
import subprocess
import httpx
import os
from typing import Dict, Optional, Any, List
from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack
from aiortc.contrib.media import MediaRecorder, MediaBlackhole
import av

logger = logging.getLogger(__name__)


class RTMPRelay:
    """Relay WebRTC media to RTMP using MediaRecorder to file + FFmpeg restream."""
    
    def __init__(self, rtmp_url: str, guest_id: str):
        """Initialize RTMP relay.
        
        Args:
            rtmp_url: RTMP destination URL (e.g., rtmp://127.0.0.1:1935/guest1)
            guest_id: Guest identifier
        """
        self.rtmp_url = rtmp_url
        self.guest_id = guest_id
        self.recorder: Optional[MediaRecorder] = None
        self.ffmpeg_process: Optional[subprocess.Popen] = None
        self._running = False
        self._temp_file = f"/tmp/guest_{guest_id}.flv"
        self._ffmpeg_task: Optional[asyncio.Task] = None
    
    async def start(self, video_track: MediaStreamTrack, audio_track: Optional[MediaStreamTrack] = None):
        """Start relaying media to RTMP.
        
        Args:
            video_track: Video track from WebRTC
            audio_track: Audio track from WebRTC (optional)
        """
        self._running = True
        
        logger.info(f"Starting RTMP relay to {self.rtmp_url}")
        
        try:
            # Remove old temp file if exists
            if os.path.exists(self._temp_file):
                os.remove(self._temp_file)
            
            # Use MediaRecorder to save to temp file with fragmented FLV
            self.recorder = MediaRecorder(
                self._temp_file,
                format="flv",
                options={
                    "flvflags": "no_duration_filesize",
                    "frag_keyframe": "1"
                }
            )
            
            # Add tracks
            self.recorder.addTrack(video_track)
            if audio_track:
                self.recorder.addTrack(audio_track)
            
            # Start recording
            await self.recorder.start()
            logger.info(f"MediaRecorder started, writing to {self._temp_file}")
            
            # Wait a moment for file to be created
            await asyncio.sleep(1)
            
            # Start FFmpeg to restream from file to RTMP
            self._ffmpeg_task = asyncio.create_task(self._ffmpeg_restream())
            
            logger.info("RTMP relay started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start RTMP relay: {e}", exc_info=True)
            raise
    
    async def _ffmpeg_restream(self):
        """Restream from temp file to RTMP using FFmpeg."""
        try:
            # Wait for file to have some data
            for _ in range(10):
                if os.path.exists(self._temp_file) and os.path.getsize(self._temp_file) > 1024:
                    break
                await asyncio.sleep(0.5)
            
            logger.info(f"Starting FFmpeg restream from {self._temp_file} to {self.rtmp_url}")
            
            ffmpeg_cmd = [
                'ffmpeg',
                '-re',  # Read at native frame rate
                '-i', self._temp_file,
                '-c', 'copy',  # Copy without re-encoding
                '-f', 'flv',
                '-flvflags', 'no_duration_filesize',
                self.rtmp_url
            ]
            
            self.ffmpeg_process = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            logger.info("FFmpeg restream process started")
            
            # Monitor process
            while self._running and self.ffmpeg_process.poll() is None:
                await asyncio.sleep(1)
            
            if self.ffmpeg_process.poll() is not None:
                returncode = self.ffmpeg_process.returncode
                if returncode != 0:
                    stderr = self.ffmpeg_process.stderr.read().decode('utf-8', errors='ignore')[-1000:]
                    logger.error(f"FFmpeg exited with code {returncode}: {stderr}")
                    
        except Exception as e:
            logger.error(f"FFmpeg restream failed: {e}", exc_info=True)
    
    async def stop(self):
        """Stop the RTMP relay."""
        logger.info("Stopping RTMP relay...")
        self._running = False
        
        # Stop FFmpeg first
        if self.ffmpeg_process and self.ffmpeg_process.poll() is None:
            try:
                self.ffmpeg_process.terminate()
                self.ffmpeg_process.wait(timeout=3)
            except:
                try:
                    self.ffmpeg_process.kill()
                except:
                    pass
        
        # Wait for FFmpeg task
        if self._ffmpeg_task and not self._ffmpeg_task.done():
            try:
                await asyncio.wait_for(self._ffmpeg_task, timeout=2.0)
            except asyncio.TimeoutError:
                self._ffmpeg_task.cancel()
        
        # Stop recorder
        if self.recorder:
            try:
                await self.recorder.stop()
                logger.info("MediaRecorder stopped")
            except Exception as e:
                logger.error(f"Error stopping recorder: {e}")
        
        # Clean up temp file
        try:
            if os.path.exists(self._temp_file):
                os.remove(self._temp_file)
                logger.info(f"Cleaned up {self._temp_file}")
        except Exception as e:
            logger.warning(f"Failed to clean up temp file: {e}")
        
        logger.info("RTMP relay stopped")


class CloudflareCallsRelay:
    """Subscribe to Cloudflare Calls tracks and relay to MediaMTX."""
    
    def __init__(self, app_id: str, api_token: str):
        """Initialize relay service.
        
        Args:
            app_id: Cloudflare Calls app ID
            api_token: Cloudflare Calls API token
        """
        self.app_id = app_id
        self.api_token = api_token
        self.base_url = "https://rtc.live.cloudflare.com/v1"
        self.active_relays: Dict[str, Dict[str, Any]] = {}  # guest_id -> {pc, relay, session_ids}
        
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for Cloudflare API requests."""
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
    
    async def _create_subscriber_session_with_tracks(
        self,
        publisher_session_id: str,
        track_names: List[str],
        sdp_offer: str
    ) -> Dict[str, Any]:
        """Create subscriber session and subscribe to remote tracks in one call.
        
        Args:
            publisher_session_id: The guest's publisher session ID
            track_names: List of track names to subscribe to
            sdp_offer: SDP offer from our RTCPeerConnection
            
        Returns:
            Dict with sessionId and sessionDescription (SDP answer)
        """
        url = f"{self.base_url}/apps/{self.app_id}/sessions/new"
        
        payload = {
            "sessionDescription": {
                "type": "offer",
                "sdp": sdp_offer
            },
            "tracks": [
                {
                    "location": "remote",
                    "sessionId": publisher_session_id,
                    "trackName": name
                }
                for name in track_names
            ]
        }
        
        logger.info(f"Creating subscriber session for tracks {track_names} from {publisher_session_id}")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    headers=self._get_headers(),
                    json=payload
                )
                
                if not response.is_success:
                    error_text = response.text
                    logger.error(f"Failed to create subscriber session: {response.status_code} - {error_text}")
                    raise Exception(f"Subscribe failed: {response.status_code} - {error_text}")
                
                data = response.json()
                session_id = data.get("sessionId")
                session_desc = data.get("sessionDescription", {})
                sdp_answer = session_desc.get("sdp")
                
                if not session_id or not sdp_answer:
                    raise Exception(f"Invalid response: {data}")
                
                logger.info(f"Successfully created subscriber session {session_id} for tracks from {publisher_session_id}")
                return data
                
        except Exception as e:
            logger.error(f"Error creating subscriber session: {e}")
            raise
    
    async def subscribe_and_relay(
        self,
        guest_session_id: str,
        track_names: List[str],
        guest_id: str,
        rtmp_url: str
    ):
        """Subscribe to Cloudflare Calls session and relay to RTMP.
        
        Args:
            guest_session_id: Guest's publisher session ID
            track_names: List of track names to subscribe to
            guest_id: Guest identifier (for tracking)
            rtmp_url: RTMP destination URL
        """
        logger.info(f"Starting relay for {guest_id}: session {guest_session_id} -> {rtmp_url}")
        
        try:
            # Create aiortc peer connection
            pc = RTCPeerConnection()
            
            video_track = None
            audio_track = None
            rtmp_relay = RTMPRelay(rtmp_url, guest_id)
            
            @pc.on("track")
            async def on_track(track):
                nonlocal video_track, audio_track
                logger.info(f"Received {track.kind} track from Cloudflare Calls for {guest_id}")
                
                if track.kind == "video":
                    video_track = track
                elif track.kind == "audio":
                    audio_track = track
                
                # Start relay when we have video
                if video_track and not rtmp_relay._running:
                    logger.info(f"Starting RTMP relay for {guest_id}")
                    await rtmp_relay.start(video_track, audio_track)
            
            # Add transceivers to receive tracks
            pc.addTransceiver("video", direction="recvonly")
            pc.addTransceiver("audio", direction="recvonly")
            
            # Create offer
            offer = await pc.createOffer()
            await pc.setLocalDescription(offer)
            
            # Create subscriber session and subscribe to remote tracks
            subscribe_data = await self._create_subscriber_session_with_tracks(
                guest_session_id,
                track_names,
                pc.localDescription.sdp
            )
            
            sub_session_id = subscribe_data["sessionId"]
            sdp_answer = subscribe_data["sessionDescription"]["sdp"]
            
            # Set remote description
            await pc.setRemoteDescription(RTCSessionDescription(sdp=sdp_answer, type="answer"))
            
            # Store active relay
            self.active_relays[guest_id] = {
                "pc": pc,
                "relay": rtmp_relay,
                "publisher_session_id": guest_session_id,
                "subscriber_session_id": sub_session_id
            }
            
            logger.info(f"Relay established for {guest_id}")
            
        except Exception as e:
            logger.error(f"Failed to establish relay for {guest_id}: {e}")
            raise
    
    async def stop_relay(self, guest_id: str):
        """Stop relay for a guest.
        
        Args:
            guest_id: Guest identifier
        """
        if guest_id not in self.active_relays:
            return
        
        logger.info(f"Stopping relay for {guest_id}")
        
        relay_info = self.active_relays[guest_id]
        
        # Stop RTMP relay
        if "relay" in relay_info:
            await relay_info["relay"].stop()
        
        # Close peer connection
        if "pc" in relay_info:
            await relay_info["pc"].close()
        
        del self.active_relays[guest_id]
        
        logger.info(f"Relay stopped for {guest_id}")
    
    async def cleanup_all(self):
        """Stop all active relays."""
        logger.info(f"Cleaning up {len(self.active_relays)} active relays")
        
        for guest_id in list(self.active_relays.keys()):
            try:
                await self.stop_relay(guest_id)
            except Exception as e:
                logger.error(f"Error stopping relay for {guest_id}: {e}")

