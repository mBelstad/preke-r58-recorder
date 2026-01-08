"""Webhook management for external integrations (e.g., DaVinci Resolve automation)."""
import asyncio
import logging
from typing import Dict, List, Optional, Any
import httpx

logger = logging.getLogger(__name__)


class WebhookManager:
    """Manages webhook delivery to external services."""
    
    def __init__(self, webhook_urls: List[str], timeout: float = 2.0):
        """Initialize webhook manager.
        
        Args:
            webhook_urls: List of webhook URLs to send events to
            timeout: HTTP request timeout in seconds
        """
        self.webhook_urls = webhook_urls
        self.timeout = timeout
    
    async def send_session_start(
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
        
        # Send to all webhook URLs in parallel (fire-and-forget)
        tasks = [
            self._send_webhook(url, payload)
            for url in self.webhook_urls
        ]
        
        # Don't wait for completion - fire and forget
        asyncio.create_task(self._send_all_webhooks(tasks))
    
    async def send_session_stop(
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
        
        tasks = [
            self._send_webhook(url, payload)
            for url in self.webhook_urls
        ]
        
        asyncio.create_task(self._send_all_webhooks(tasks))
    
    async def send_file_added(
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
        
        tasks = [
            self._send_webhook(url, payload)
            for url in self.webhook_urls
        ]
        
        asyncio.create_task(self._send_all_webhooks(tasks))
    
    async def _send_all_webhooks(self, tasks: List) -> None:
        """Send all webhooks and log results."""
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(
                    f"Failed to send webhook to {self.webhook_urls[i]}: {result}"
                )
            elif result is False:
                logger.warning(
                    f"Webhook to {self.webhook_urls[i]} returned error status"
                )
    
    async def _send_webhook(self, url: str, payload: Dict[str, Any]) -> bool:
        """Send a single webhook request.
        
        Args:
            url: Webhook URL
            payload: JSON payload to send
            
        Returns:
            True if successful, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                logger.debug(f"Successfully sent webhook to {url}")
                return True
        except httpx.TimeoutException:
            logger.warning(f"Webhook timeout to {url}")
            return False
        except httpx.HTTPStatusError as e:
            logger.warning(f"Webhook HTTP error to {url}: {e.response.status_code}")
            return False
        except Exception as e:
            logger.warning(f"Webhook error to {url}: {e}")
            return False
