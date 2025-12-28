"""WHEP/WHIP proxy for accessing MediaMTX streams over HTTPS.

This module proxies WebRTC-HTTP requests from the frontend (served over HTTPS)
to the local MediaMTX instance, avoiding mixed-content browser errors.

WHEP (pull) - For viewing streams (camera previews)
WHIP (push) - For publishing streams (program output)
"""
import httpx
from fastapi import APIRouter, Request, Response, HTTPException

from ..config import get_settings

router = APIRouter(prefix="/api/v1", tags=["WebRTC Proxy"])

# HTTP client for proxying requests to MediaMTX
_client: httpx.AsyncClient | None = None


def get_client() -> httpx.AsyncClient:
    """Get or create HTTP client for MediaMTX requests."""
    global _client
    if _client is None:
        # Disable SSL verification for localhost (self-signed cert)
        _client = httpx.AsyncClient(timeout=10.0, verify=False)
    return _client


@router.api_route("/whep/{stream_id}/whep", methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"])
async def whep_proxy(stream_id: str, request: Request) -> Response:
    """
    Proxy WHEP requests to local MediaMTX (for viewing streams).
    
    Supports all WHEP operations:
    - POST: Create WHEP session (send SDP offer, receive answer)
    - PATCH: ICE trickle candidates
    - DELETE: Close session
    - GET: Check stream availability
    """
    settings = get_settings()
    mediamtx_url = f"{settings.mediamtx_whep_base}/{stream_id}/whep"
    
    return await _proxy_request(request, mediamtx_url)


@router.api_route("/whip/{stream_id}/whip", methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"])
async def whip_proxy(stream_id: str, request: Request) -> Response:
    """
    Proxy WHIP requests to local MediaMTX (for publishing streams).
    
    Used by VDO.ninja to push the program output to MediaMTX.
    
    Supports all WHIP operations:
    - POST: Create WHIP session (send SDP offer, receive answer)
    - PATCH: ICE trickle candidates
    - DELETE: Close session
    """
    settings = get_settings()
    # WHIP uses the same base URL as WHEP, just different endpoint
    mediamtx_base = settings.mediamtx_whep_base
    mediamtx_url = f"{mediamtx_base}/{stream_id}/whip"
    
    return await _proxy_request(request, mediamtx_url)


async def _proxy_request(request: Request, target_url: str) -> Response:
    """Common proxy logic for WHEP and WHIP requests."""
    client = get_client()
    
    # Forward headers, excluding host
    headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in ('host', 'content-length')
    }
    
    try:
        # Read request body
        body = await request.body()
        
        # Forward request to MediaMTX
        response = await client.request(
            method=request.method,
            url=target_url,
            headers=headers,
            content=body,
        )
        
        # Return response with appropriate headers
        response_headers = dict(response.headers)
        # Remove headers that shouldn't be forwarded
        for h in ('transfer-encoding', 'content-encoding', 'content-length'):
            response_headers.pop(h, None)
        
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=response_headers,
            media_type=response.headers.get('content-type', 'application/sdp')
        )
        
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="MediaMTX not available"
        )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="MediaMTX request timed out"
        )

