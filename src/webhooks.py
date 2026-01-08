"""Webhook management for external integrations (e.g., DaVinci Resolve automation)."""
import logging
from typing import Dict, List, Any
import httpx

logger = logging.getLogger(__name__)


class WebhookManager:
    """Manages webhook delivery to external services.
    
    Uses synchronous HTTP requests for simplicity and reliability
    when called from background threads.
    """
    
    def __init__(self, webhook_urls: List[str], timeout: float = 5.0):
        """Initialize webhook manager.
        
        Args:
            webhook_urls: List of webhook URLs to send events to
            timeout: HTTP request timeout in seconds
        """
        self.webhook_urls = webhook_urls
        self.timeout = timeout
    
    def send_session_start(
        self,
        session_id: str,
        start_time: str,
        cameras: Dict[str, Any],
        file_paths: Dict[str, str]
    ) -> None:
        """Send session start webhook to all configured URLs.
        
        Args:
            session_id: Unique session identifier
            start_time: ISO format timestamp of session start
            cameras: Dictionary of camera status information
            file_paths: Dictionary mapping camera IDs to file paths
        """
        if not self.webhook_urls:
            return
        
        payload = {
            "event": "session_start",
            "session_id": session_id,
            "start_time": start_time,
            "cameras": cameras,
            "file_paths": file_paths
        }
        
        self._send_to_all_urls(payload)
    
    def send_session_stop(
        self,
        session_id: str,
        end_time: str,
        cameras: Dict[str, Any]
    ) -> None:
        """Send session stop webhook to all configured URLs.
        
        Args:
            session_id: Unique session identifier
            end_time: ISO format timestamp of session end
            cameras: Dictionary of camera status information
        """
        if not self.webhook_urls:
            return
        
        payload = {
            "event": "session_stop",
            "session_id": session_id,
            "end_time": end_time,
            "cameras": cameras
        }
        
        self._send_to_all_urls(payload)
    
    def send_file_added(
        self,
        session_id: str,
        cam_id: str,
        file_path: str
    ) -> None:
        """Send file added webhook for incremental imports.
        
        Args:
            session_id: Session identifier
            cam_id: Camera identifier
            file_path: Path to the new file
        """
        if not self.webhook_urls:
            return
        
        payload = {
            "event": "file_added",
            "session_id": session_id,
            "cam_id": cam_id,
            "file_path": file_path
        }
        
        self._send_to_all_urls(payload)
    
    def _send_to_all_urls(self, payload: Dict[str, Any]) -> None:
        """Send webhook to all configured URLs."""
        for url in self.webhook_urls:
            self._send_webhook(url, payload)
    
    def _send_webhook(self, url: str, payload: Dict[str, Any]) -> bool:
        """Send a single webhook request.
        
        Args:
            url: Webhook URL
            payload: JSON payload to send
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                logger.info(f"Successfully sent webhook to {url}")
                return True
        except httpx.TimeoutException:
            logger.warning(f"Webhook timeout to {url}")
            return False
        except httpx.HTTPStatusError as e:
            logger.warning(f"Webhook HTTP error to {url}: {e.response.status_code}")
            return False
        except httpx.ConnectError as e:
            logger.warning(f"Webhook connection error to {url}: {e}")
            return False
        except Exception as e:
            logger.warning(f"Webhook error to {url}: {e}")
            return False
