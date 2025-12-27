#!/usr/bin/env python3
"""
WHEP to VDO.ninja Bridge

This script bridges HDMI camera streams from MediaMTX WHEP endpoints
to VDO.ninja rooms via WebRTC signaling.

Architecture:
  MediaMTX WHEP → aiortc (receive) → aiortc (publish) → VDO.ninja peers

Usage:
  python whep_vdo_bridge.py --room r58studio --cameras cam2,cam3
"""

import asyncio
import json
import logging
import uuid
import argparse
import ssl
import signal
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from urllib.parse import urlparse

import httpx
import websockets
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceCandidate, MediaStreamTrack
from aiortc.contrib.media import MediaRelay

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('whep-vdo-bridge')

# Suppress noisy aiortc codec warnings (H264 decode errors during relay)
# These warnings are normal when relaying without transcoding
logging.getLogger('aiortc.codecs.h264').setLevel(logging.ERROR)
logging.getLogger('aiortc.codecs').setLevel(logging.ERROR)
logging.getLogger('aioice').setLevel(logging.WARNING)


@dataclass
class BridgeConfig:
    """Configuration for the WHEP-VDO bridge"""
    signaling_url: str = "wss://localhost:8443"
    mediamtx_url: str = "http://localhost:8889"
    api_url: str = "http://localhost:8000"
    room: str = "r58studio"
    cameras: List[str] = field(default_factory=list)
    ice_servers: List[dict] = field(default_factory=lambda: [
        {"urls": "stun:stun.l.google.com:19302"},
        {"urls": "stun:stun1.l.google.com:19302"}
    ])
    reconnect_delay: float = 5.0
    ssl_verify: bool = False  # For self-signed certs


class WHEPClient:
    """
    WHEP (WebRTC-HTTP Egress Protocol) client.
    
    Pulls video/audio streams from a MediaMTX WHEP endpoint.
    """
    
    def __init__(self, whep_url: str, ice_servers: List[dict] = None):
        self.whep_url = whep_url
        self.ice_servers = ice_servers or [{"urls": "stun:stun.l.google.com:19302"}]
        self.pc: Optional[RTCPeerConnection] = None
        self.tracks: Dict[str, MediaStreamTrack] = {}
        self._connected = asyncio.Event()
        self._closed = False
        
    async def connect(self) -> Dict[str, MediaStreamTrack]:
        """
        Connect to WHEP endpoint and return received tracks.
        
        Returns:
            Dict mapping track kind ('video', 'audio') to MediaStreamTrack
        """
        logger.info(f"Connecting to WHEP endpoint: {self.whep_url}")
        
        # Create peer connection
        from aiortc import RTCConfiguration, RTCIceServer
        ice_servers = [RTCIceServer(urls=s["urls"]) for s in self.ice_servers]
        config = RTCConfiguration(iceServers=ice_servers)
        self.pc = RTCPeerConnection(configuration=config)
        
        # Add receive-only transceivers
        self.pc.addTransceiver("video", direction="recvonly")
        self.pc.addTransceiver("audio", direction="recvonly")
        
        # Handle incoming tracks
        @self.pc.on("track")
        def on_track(track: MediaStreamTrack):
            logger.info(f"Received {track.kind} track from WHEP")
            self.tracks[track.kind] = track
            
            @track.on("ended")
            async def on_ended():
                logger.warning(f"{track.kind} track ended")
                if track.kind in self.tracks:
                    del self.tracks[track.kind]
        
        # Handle connection state
        @self.pc.on("connectionstatechange")
        async def on_connection_state_change():
            logger.info(f"WHEP connection state: {self.pc.connectionState}")
            if self.pc.connectionState == "connected":
                self._connected.set()
            elif self.pc.connectionState in ("failed", "closed"):
                self._connected.clear()
        
        # Create and send offer
        offer = await self.pc.createOffer()
        await self.pc.setLocalDescription(offer)
        
        # Wait for ICE gathering to complete
        while self.pc.iceGatheringState != "complete":
            await asyncio.sleep(0.1)
        
        # Send offer to WHEP endpoint
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(
                self.whep_url,
                content=self.pc.localDescription.sdp,
                headers={"Content-Type": "application/sdp"}
            )
            
            if response.status_code != 201 and response.status_code != 200:
                raise Exception(f"WHEP request failed: {response.status_code} {response.text}")
            
            answer_sdp = response.text
        
        # Set remote answer
        answer = RTCSessionDescription(sdp=answer_sdp, type="answer")
        await self.pc.setRemoteDescription(answer)
        
        # Wait for connection
        try:
            await asyncio.wait_for(self._connected.wait(), timeout=10.0)
        except asyncio.TimeoutError:
            logger.warning("WHEP connection timeout, but continuing...")
        
        logger.info(f"WHEP connected, received tracks: {list(self.tracks.keys())}")
        return self.tracks
    
    async def close(self):
        """Close the WHEP connection"""
        self._closed = True
        if self.pc:
            await self.pc.close()
            self.pc = None
        self.tracks.clear()
        logger.info("WHEP connection closed")


class VDONinjaBridge:
    """
    VDO.ninja signaling bridge.
    
    Connects to VDO.ninja WebSocket signaling server and handles
    WebRTC negotiation with peers.
    """
    
    def __init__(
        self,
        signaling_url: str,
        room: str,
        stream_id: str,
        ice_servers: List[dict] = None,
        ssl_verify: bool = False
    ):
        self.signaling_url = signaling_url
        self.room = room
        self.stream_id = stream_id
        self.ice_servers = ice_servers or [{"urls": "stun:stun.l.google.com:19302"}]
        self.ssl_verify = ssl_verify
        
        self.uuid = str(uuid.uuid4())
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.peer_connections: Dict[str, RTCPeerConnection] = {}
        self.tracks: Dict[str, MediaStreamTrack] = {}
        self.relay = MediaRelay()
        
        self._running = False
        self._connected = asyncio.Event()
    
    def set_tracks(self, tracks: Dict[str, MediaStreamTrack]):
        """Set the tracks to publish to VDO.ninja peers"""
        self.tracks = tracks
        logger.info(f"Set tracks for publishing: {list(tracks.keys())}")
    
    async def connect(self):
        """Connect to VDO.ninja signaling server"""
        logger.info(f"Connecting to VDO.ninja signaling: {self.signaling_url}")
        
        # Create SSL context for self-signed certs
        ssl_context = None
        if self.signaling_url.startswith("wss://"):
            ssl_context = ssl.create_default_context()
            if not self.ssl_verify:
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
        
        self.ws = await websockets.connect(
            self.signaling_url,
            ssl=ssl_context,
            ping_interval=20,
            ping_timeout=20
        )
        
        self._running = True
        self._connected.set()
        
        # Join room
        await self._send_join_room()
        
        logger.info(f"Connected to VDO.ninja, joined room: {self.room} as {self.stream_id}")
    
    async def _send_join_room(self):
        """Send joinroom message to signaling server"""
        message = {
            "request": "joinroom",
            "roomid": self.room,
            "streamid": self.stream_id,
            "UUID": self.uuid
        }
        await self.ws.send(json.dumps(message))
        logger.debug(f"Sent joinroom: {message}")
    
    async def run(self):
        """Run the signaling message loop"""
        if not self.ws:
            raise Exception("Not connected to signaling server")
        
        try:
            async for message in self.ws:
                await self._handle_message(message)
        except websockets.exceptions.ConnectionClosed as e:
            logger.warning(f"WebSocket connection closed: {e}")
        finally:
            self._running = False
            self._connected.clear()
    
    async def _handle_message(self, message: str):
        """Handle incoming signaling message"""
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON message: {message[:100]}")
            return
        
        # Ignore our own messages
        if data.get("UUID") == self.uuid:
            return
        
        peer_uuid = data.get("UUID", "unknown")
        
        # Handle different message types
        if data.get("request") == "joinroom":
            logger.info(f"Peer joined room: {data.get('streamid', 'unknown')}")
            
        elif "description" in data:
            desc = data["description"]
            if desc.get("type") == "offer":
                await self._handle_offer(peer_uuid, desc)
            elif desc.get("type") == "answer":
                await self._handle_answer(peer_uuid, desc)
                
        elif "candidate" in data:
            await self._handle_ice_candidate(peer_uuid, data["candidate"])
            
        elif data.get("request") == "offerSDP":
            # Peer is requesting our stream
            target = data.get("streamID")
            if target == self.stream_id:
                logger.info(f"Peer {peer_uuid} requesting stream {self.stream_id}")
                await self._send_offer_to_peer(peer_uuid)
    
    async def _handle_offer(self, peer_uuid: str, description: dict):
        """Handle incoming WebRTC offer"""
        logger.info(f"Received offer from {peer_uuid}")
        
        # Create peer connection for this peer
        pc = await self._create_peer_connection(peer_uuid)
        
        # Set remote description (the offer)
        offer = RTCSessionDescription(
            sdp=description.get("sdp", ""),
            type="offer"
        )
        await pc.setRemoteDescription(offer)
        
        # Add our tracks
        for kind, track in self.tracks.items():
            relayed_track = self.relay.subscribe(track)
            pc.addTrack(relayed_track)
            logger.debug(f"Added {kind} track to peer connection")
        
        # Create and send answer
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        
        # Wait for ICE gathering
        while pc.iceGatheringState != "complete":
            await asyncio.sleep(0.1)
        
        # Send answer
        await self._send_description(peer_uuid, pc.localDescription)
        logger.info(f"Sent answer to {peer_uuid}")
    
    async def _handle_answer(self, peer_uuid: str, description: dict):
        """Handle incoming WebRTC answer"""
        pc = self.peer_connections.get(peer_uuid)
        if not pc:
            logger.warning(f"No peer connection for answer from {peer_uuid}")
            return
        
        answer = RTCSessionDescription(
            sdp=description.get("sdp", ""),
            type="answer"
        )
        await pc.setRemoteDescription(answer)
        logger.info(f"Set remote answer from {peer_uuid}")
    
    async def _handle_ice_candidate(self, peer_uuid: str, candidate_data: dict):
        """Handle incoming ICE candidate"""
        pc = self.peer_connections.get(peer_uuid)
        if not pc:
            return
        
        try:
            candidate = RTCIceCandidate(
                sdpMid=candidate_data.get("sdpMid"),
                sdpMLineIndex=candidate_data.get("sdpMLineIndex"),
                candidate=candidate_data.get("candidate", "")
            )
            await pc.addIceCandidate(candidate)
        except Exception as e:
            logger.debug(f"Failed to add ICE candidate: {e}")
    
    async def _send_offer_to_peer(self, peer_uuid: str):
        """Create and send offer to a specific peer"""
        pc = await self._create_peer_connection(peer_uuid)
        
        # Add tracks
        for kind, track in self.tracks.items():
            relayed_track = self.relay.subscribe(track)
            pc.addTrack(relayed_track)
        
        # Create and send offer
        offer = await pc.createOffer()
        await pc.setLocalDescription(offer)
        
        # Wait for ICE gathering
        while pc.iceGatheringState != "complete":
            await asyncio.sleep(0.1)
        
        await self._send_description(peer_uuid, pc.localDescription)
        logger.info(f"Sent offer to {peer_uuid}")
    
    async def _create_peer_connection(self, peer_uuid: str) -> RTCPeerConnection:
        """Create a new peer connection for a peer"""
        # Close existing connection if any
        if peer_uuid in self.peer_connections:
            await self.peer_connections[peer_uuid].close()
        
        from aiortc import RTCConfiguration, RTCIceServer
        ice_servers = [RTCIceServer(urls=s["urls"]) for s in self.ice_servers]
        config = RTCConfiguration(iceServers=ice_servers)
        pc = RTCPeerConnection(configuration=config)
        self.peer_connections[peer_uuid] = pc
        
        @pc.on("connectionstatechange")
        async def on_state_change():
            logger.info(f"Peer {peer_uuid} connection state: {pc.connectionState}")
            if pc.connectionState in ("failed", "closed"):
                if peer_uuid in self.peer_connections:
                    del self.peer_connections[peer_uuid]
        
        @pc.on("icecandidate")
        async def on_ice_candidate(candidate):
            if candidate:
                await self._send_ice_candidate(peer_uuid, candidate)
        
        return pc
    
    async def _send_description(self, peer_uuid: str, description: RTCSessionDescription):
        """Send SDP description to peer via signaling"""
        message = {
            "UUID": self.uuid,
            "streamID": self.stream_id,
            "targetUUID": peer_uuid,
            "description": {
                "type": description.type,
                "sdp": description.sdp
            }
        }
        await self.ws.send(json.dumps(message))
    
    async def _send_ice_candidate(self, peer_uuid: str, candidate: RTCIceCandidate):
        """Send ICE candidate to peer via signaling"""
        message = {
            "UUID": self.uuid,
            "streamID": self.stream_id,
            "targetUUID": peer_uuid,
            "candidate": {
                "candidate": candidate.candidate,
                "sdpMid": candidate.sdpMid,
                "sdpMLineIndex": candidate.sdpMLineIndex
            }
        }
        await self.ws.send(json.dumps(message))
    
    async def close(self):
        """Close all connections"""
        self._running = False
        
        # Close peer connections
        for peer_uuid, pc in list(self.peer_connections.items()):
            await pc.close()
        self.peer_connections.clear()
        
        # Close WebSocket
        if self.ws:
            await self.ws.close()
            self.ws = None
        
        logger.info("VDO.ninja bridge closed")


class CameraBridge:
    """
    Bridges a single camera from MediaMTX WHEP to VDO.ninja room.
    
    Combines WHEPClient (receive) + VDONinjaBridge (publish).
    """
    
    def __init__(
        self,
        camera_id: str,
        config: BridgeConfig
    ):
        self.camera_id = camera_id
        self.config = config
        
        self.whep_url = f"{config.mediamtx_url}/{camera_id}/whep"
        self.whep_client: Optional[WHEPClient] = None
        self.vdo_bridge: Optional[VDONinjaBridge] = None
        
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start bridging the camera"""
        logger.info(f"Starting bridge for camera: {self.camera_id}")
        self._running = True
        
        while self._running:
            try:
                # Connect to WHEP
                self.whep_client = WHEPClient(
                    self.whep_url,
                    self.config.ice_servers
                )
                tracks = await self.whep_client.connect()
                
                if not tracks:
                    logger.warning(f"No tracks received for {self.camera_id}")
                    await asyncio.sleep(self.config.reconnect_delay)
                    continue
                
                # Connect to VDO.ninja
                self.vdo_bridge = VDONinjaBridge(
                    self.config.signaling_url,
                    self.config.room,
                    self.camera_id,
                    self.config.ice_servers,
                    ssl_verify=self.config.ssl_verify
                )
                self.vdo_bridge.set_tracks(tracks)
                await self.vdo_bridge.connect()
                
                # Run signaling loop
                await self.vdo_bridge.run()
                
            except Exception as e:
                logger.error(f"Bridge error for {self.camera_id}: {e}")
            
            # Cleanup before retry
            await self._cleanup()
            
            if self._running:
                logger.info(f"Reconnecting {self.camera_id} in {self.config.reconnect_delay}s...")
                await asyncio.sleep(self.config.reconnect_delay)
    
    async def _cleanup(self):
        """Cleanup connections"""
        if self.vdo_bridge:
            await self.vdo_bridge.close()
            self.vdo_bridge = None
        
        if self.whep_client:
            await self.whep_client.close()
            self.whep_client = None
    
    async def stop(self):
        """Stop the bridge"""
        self._running = False
        await self._cleanup()
        logger.info(f"Bridge stopped for {self.camera_id}")


class WHEPVDOBridgeManager:
    """
    Manages multiple camera bridges.
    
    Can auto-discover cameras from the API or use a static list.
    """
    
    def __init__(self, config: BridgeConfig):
        self.config = config
        self.bridges: Dict[str, CameraBridge] = {}
        self._running = False
    
    async def discover_cameras(self) -> List[str]:
        """Discover active cameras from the API"""
        try:
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.get(f"{self.config.api_url}/api/vdoninja/sources")
                if response.status_code == 200:
                    data = response.json()
                    cameras = [
                        s["stream"] for s in data.get("sources", [])
                        if s.get("type") == "camera" and s.get("active")
                    ]
                    logger.info(f"Discovered active cameras: {cameras}")
                    return cameras
        except Exception as e:
            logger.warning(f"Failed to discover cameras: {e}")
        
        return self.config.cameras
    
    async def start(self, auto_discover: bool = True, single_camera: bool = False):
        """Start all camera bridges"""
        self._running = True
        
        # Get camera list
        if auto_discover:
            cameras = await self.discover_cameras()
        else:
            cameras = self.config.cameras
        
        if not cameras:
            logger.warning("No cameras to bridge")
            return
        
        # Single camera mode for testing
        if single_camera and cameras:
            cameras = [cameras[0]]
            logger.info(f"Single camera mode: only bridging {cameras[0]}")
        
        logger.info(f"Starting bridges for cameras: {cameras}")
        
        # Create and start bridges
        tasks = []
        for camera_id in cameras:
            bridge = CameraBridge(camera_id, self.config)
            self.bridges[camera_id] = bridge
            tasks.append(asyncio.create_task(bridge.start()))
        
        # Wait for all bridges
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            logger.info("Bridge manager cancelled")
    
    async def stop(self):
        """Stop all bridges"""
        self._running = False
        for bridge in self.bridges.values():
            await bridge.stop()
        self.bridges.clear()
        logger.info("All bridges stopped")


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="WHEP to VDO.ninja Bridge")
    parser.add_argument("--signaling", default="wss://localhost:8443",
                        help="VDO.ninja signaling URL")
    parser.add_argument("--mediamtx", default="http://localhost:8889",
                        help="MediaMTX base URL")
    parser.add_argument("--api", default="http://localhost:8000",
                        help="R58 API URL for camera discovery")
    parser.add_argument("--room", default="r58studio",
                        help="VDO.ninja room name")
    parser.add_argument("--cameras", default="",
                        help="Comma-separated camera IDs (empty for auto-discover)")
    parser.add_argument("--no-discover", action="store_true",
                        help="Disable camera auto-discovery")
    parser.add_argument("--single", action="store_true",
                        help="Only bridge first camera (for testing)")
    parser.add_argument("--debug", action="store_true",
                        help="Enable debug logging")
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create config
    config = BridgeConfig(
        signaling_url=args.signaling,
        mediamtx_url=args.mediamtx,
        api_url=args.api,
        room=args.room,
        cameras=args.cameras.split(",") if args.cameras else []
    )
    
    logger.info("WHEP to VDO.ninja Bridge starting...")
    logger.info(f"  Signaling: {config.signaling_url}")
    logger.info(f"  MediaMTX: {config.mediamtx_url}")
    logger.info(f"  Room: {config.room}")
    
    # Create manager
    manager = WHEPVDOBridgeManager(config)
    
    # Handle shutdown
    loop = asyncio.get_event_loop()
    
    def signal_handler():
        logger.info("Shutdown signal received")
        asyncio.create_task(manager.stop())
    
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)
    
    # Run
    try:
        await manager.start(
            auto_discover=not args.no_discover,
            single_camera=args.single
        )
    except KeyboardInterrupt:
        pass
    finally:
        await manager.stop()
    
    logger.info("Bridge shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())

