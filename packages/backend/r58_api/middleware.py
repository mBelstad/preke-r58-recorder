"""Middleware for R58 API - Tracing, Latency, and Request Handling"""
import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .logging import set_trace_id, generate_trace_id, get_trace_id

logger = logging.getLogger(__name__)


class TraceMiddleware(BaseHTTPMiddleware):
    """
    Adds trace ID to each request for distributed tracing.
    
    - Reads X-Trace-ID from incoming request header
    - Generates new trace ID if not present
    - Adds X-Trace-ID to response headers
    - Sets trace ID in context for logging
    """
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Get or generate trace ID
        trace_id = request.headers.get("X-Trace-ID") or generate_trace_id()
        
        # Set in context for logging
        set_trace_id(trace_id)
        
        # Process request
        response = await call_next(request)
        
        # Add trace ID to response
        response.headers["X-Trace-ID"] = trace_id
        
        return response


class LatencyMiddleware(BaseHTTPMiddleware):
    """
    Measures and logs request latency.
    
    - Adds X-Response-Time-Ms header to all responses
    - Logs slow requests (>200ms)
    - Logs very slow requests (>1000ms) as warnings
    """
    
    # Thresholds in milliseconds
    SLOW_REQUEST_MS = 200
    VERY_SLOW_REQUEST_MS = 1000
    
    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        
        response = await call_next(request)
        
        # Calculate latency
        latency_ms = (time.perf_counter() - start) * 1000
        
        # Add header
        response.headers["X-Response-Time-Ms"] = f"{latency_ms:.2f}"
        
        # Log slow requests (skip health checks and static files)
        path = request.url.path
        if not path.startswith("/static") and path != "/api/v1/health":
            if latency_ms > self.VERY_SLOW_REQUEST_MS:
                logger.warning(
                    f"Very slow request: {request.method} {path} took {latency_ms:.0f}ms",
                    extra={"duration_ms": latency_ms, "method": request.method, "path": path}
                )
            elif latency_ms > self.SLOW_REQUEST_MS:
                logger.info(
                    f"Slow request: {request.method} {path} took {latency_ms:.0f}ms",
                    extra={"duration_ms": latency_ms, "method": request.method, "path": path}
                )
        
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Logs all requests with structured data.
    
    Logs:
    - Method, path, status code
    - Response time
    - Client IP (if available)
    """
    
    # Paths to skip logging (reduce noise)
    SKIP_PATHS = {"/api/v1/health", "/api/v1/ws", "/static"}
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip noisy endpoints
        path = request.url.path
        if any(path.startswith(skip) for skip in self.SKIP_PATHS):
            return await call_next(request)
        
        start = time.perf_counter()
        
        response = await call_next(request)
        
        latency_ms = (time.perf_counter() - start) * 1000
        
        # Log request
        logger.debug(
            f"{request.method} {path} -> {response.status_code} ({latency_ms:.0f}ms)",
            extra={
                "method": request.method,
                "path": path,
                "status": response.status_code,
                "duration_ms": latency_ms,
                "client": request.client.host if request.client else "unknown",
            }
        )
        
        return response

