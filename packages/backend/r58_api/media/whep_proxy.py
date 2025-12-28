"""WHEP proxy for accessing MediaMTX streams over HTTPS.

This module proxies WHEP requests from the frontend (served over HTTPS)
to the local MediaMTX instance, avoiding mixed-content browser errors.
"""
import httpx
from fastapi import APIRouter, Request, Response, HTTPException

from ..config import get_settings

router = APIRouter(prefix="/api/v1/whep", tags=["WHEP Proxy"])

# HTTP client for proxying requests to MediaMTX
_client: httpx.AsyncClient | None = None


def get_client() -> httpx.AsyncClient:
    """Get or create HTTP client for MediaMTX requests."""
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=10.0)
    return _client


@router.api_route("/{stream_id}/whep", methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"])
async def whep_proxy(stream_id: str, request: Request) -> Response:
    """
    Proxy WHEP requests to local MediaMTX.
    
    Supports all WHEP operations:
    - POST: Create WHEP session (send SDP offer, receive answer)
    - PATCH: ICE trickle candidates
    - DELETE: Close session
    - GET: Check stream availability
    """
    settings = get_settings()
    mediamtx_url = f"{settings.mediamtx_whep_base}/{stream_id}/whep"
    
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
            url=mediamtx_url,
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

