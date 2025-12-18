"""Cloudflare Calls API integration for remote guest WebRTC sessions."""
import logging
import httpx
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

# Standard track names for guest sessions
TRACK_NAMES = ["video", "audio"]


class CloudflareCallsManager:
    """Manage Cloudflare Calls sessions for remote guests.
    
    This class handles creating and managing Cloudflare Calls sessions using
    the correct two-step API flow:
    1. Create empty session
    2. Add tracks with explicit names
    """
    
    def __init__(self, account_id: str, app_id: str, api_token: str):
        """Initialize Cloudflare Calls manager.
        
        Args:
            account_id: Cloudflare account ID
            app_id: Cloudflare Calls app ID (pre-created)
            api_token: API token with Calls permissions
        """
        self.account_id = account_id
        self.app_id = app_id
        self.api_token = api_token
        self.base_url = "https://rtc.live.cloudflare.com/v1"
        self.active_sessions: Dict[str, Dict[str, Any]] = {}  # guest_id -> session info
        
        logger.info(f"Cloudflare Calls manager initialized for app {app_id}")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for Cloudflare API requests."""
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
    
    async def create_guest_session(self, guest_id: str, sdp_offer: str) -> Dict[str, Any]:
        """Create a new Cloudflare Calls session for a guest.
        
        Args:
            guest_id: Guest identifier (guest1 or guest2)
            sdp_offer: SDP offer from guest's RTCPeerConnection
            
        Returns:
            Dict with session_id, sdp_answer, track_names, and tracks info
            
        Raises:
            Exception: If session creation fails
        """
        # Close existing session if any
        if guest_id in self.active_sessions:
            old_session_id = self.active_sessions[guest_id]["session_id"]
            logger.info(f"Closing existing session for {guest_id}: {old_session_id}")
            try:
                await self.close_session(old_session_id)
            except Exception as e:
                logger.warning(f"Failed to close old session: {e}")
        
        logger.info(f"Creating Cloudflare Calls session for {guest_id}")
        
        url = f"{self.base_url}/apps/{self.app_id}/sessions/new"
        
        payload = {
            "sessionDescription": {
                "type": "offer",
                "sdp": sdp_offer
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    headers=self._get_headers(),
                    json=payload
                )
                
                if not response.is_success:
                    error_text = response.text
                    logger.error(f"Failed to create session: {response.status_code} - {error_text}")
                    raise Exception(f"Session creation failed: {response.status_code} - {error_text}")
                
                data = response.json()
                
                # Extract session info
                session_id = data.get("sessionId")
                session_desc = data.get("sessionDescription", {})
                sdp_answer = session_desc.get("sdp")
                tracks = data.get("tracks", [])
                
                if not session_id or not sdp_answer:
                    raise Exception(f"Invalid response: {data}")
                
                # Extract track names from the tracks
                track_names = [track.get("trackName") for track in tracks if track.get("trackName")]
                if not track_names:
                    # Default to standard names if not provided
                    track_names = TRACK_NAMES
                
                # Store session info including track names
                self.active_sessions[guest_id] = {
                    "session_id": session_id,
                    "track_names": track_names,
                    "tracks": tracks
                }
                
                logger.info(f"Successfully created session for {guest_id}: {session_id} with {len(tracks)} tracks")
                
                return {
                    "session_id": session_id,
                    "sdp_answer": sdp_answer,
                    "track_names": track_names,
                    "tracks": tracks,
                    "guest_id": guest_id
                }
                
        except httpx.TimeoutException:
            logger.error("Timeout creating Cloudflare Calls session")
            raise Exception("Timeout connecting to Cloudflare Calls API")
        except httpx.ConnectError as e:
            logger.error(f"Connection error to Cloudflare Calls API: {e}")
            raise Exception("Cannot connect to Cloudflare Calls API")
        except Exception as e:
            logger.error(f"Failed to create guest session for {guest_id}: {e}")
            raise
    
    async def close_session(self, session_id: str) -> bool:
        """Close a Cloudflare Calls session.
        
        Args:
            session_id: Session ID to close
            
        Returns:
            True if successful, False otherwise
        """
        url = f"{self.base_url}/apps/{self.app_id}/sessions/{session_id}/close"
        
        logger.info(f"Closing Cloudflare Calls session: {session_id}")
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.put(
                    url,
                    headers=self._get_headers(),
                    json={}
                )
                
                if response.is_success:
                    # Remove from active sessions
                    for guest_id, info in list(self.active_sessions.items()):
                        if info["session_id"] == session_id:
                            del self.active_sessions[guest_id]
                            logger.info(f"Removed session {session_id} for {guest_id}")
                            break
                    return True
                else:
                    logger.warning(f"Failed to close session {session_id}: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error closing Cloudflare Calls session {session_id}: {e}")
            return False
    
    async def close_guest_session(self, guest_id: str) -> bool:
        """Close session for a specific guest.
        
        Args:
            guest_id: Guest identifier
            
        Returns:
            True if successful, False otherwise
        """
        if guest_id in self.active_sessions:
            session_id = self.active_sessions[guest_id]["session_id"]
            return await self.close_session(session_id)
        return False
    
    def get_active_sessions(self) -> Dict[str, str]:
        """Get all active sessions.
        
        Returns:
            Dict mapping guest_id to session_id
        """
        return {
            guest_id: info["session_id"]
            for guest_id, info in self.active_sessions.items()
        }
    
    def get_session_info(self, guest_id: str) -> Optional[Dict[str, Any]]:
        """Get full session info for a guest.
        
        Args:
            guest_id: Guest identifier
            
        Returns:
            Session info dict or None if not found
        """
        return self.active_sessions.get(guest_id)
    
    async def cleanup_all_sessions(self):
        """Close all active sessions. Called on shutdown."""
        logger.info(f"Cleaning up {len(self.active_sessions)} active Cloudflare Calls sessions")
        
        for guest_id, info in list(self.active_sessions.items()):
            try:
                await self.close_session(info["session_id"])
            except Exception as e:
                logger.error(f"Error closing session for {guest_id}: {e}")
