"""Structured logging configuration for R58 API"""
import json
import logging
import sys
import os
import uuid
from contextvars import ContextVar
from datetime import datetime
from typing import Any, Dict, Optional

# Context variable for request trace ID
_trace_id: ContextVar[str] = ContextVar("trace_id", default="")


def set_trace_id(trace_id: str) -> None:
    """Set the trace ID for the current request context"""
    _trace_id.set(trace_id)


def get_trace_id() -> str:
    """Get the current trace ID, or generate a short one if not set"""
    trace = _trace_id.get()
    return trace if trace else str(uuid.uuid4())[:8]


def generate_trace_id() -> str:
    """Generate a new trace ID"""
    return str(uuid.uuid4())[:8]


class StructuredFormatter(logging.Formatter):
    """JSON structured log formatter for production"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        
        # Add trace ID if available
        trace_id = get_trace_id()
        if trace_id:
            log_entry["trace_id"] = trace_id
        
        # Add source location for errors
        if record.levelno >= logging.ERROR:
            log_entry["location"] = f"{record.pathname}:{record.lineno}"
        
        # Add extra fields from record
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            log_entry.update(record.extra)
        
        # Add any extra attributes set via extra= parameter
        for key in ["user_id", "device_id", "session_id", "input_id", "duration_ms", "bytes"]:
            if hasattr(record, key):
                log_entry[key] = getattr(record, key)
        
        # Add exception info
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, default=str)


class DevelopmentFormatter(logging.Formatter):
    """Human-readable formatter for development"""
    
    COLORS = {
        "DEBUG": "\033[36m",    # Cyan
        "INFO": "\033[32m",     # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",    # Red
        "CRITICAL": "\033[35m", # Magenta
    }
    RESET = "\033[0m"
    
    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, "")
        trace_id = get_trace_id()
        trace_part = f"[{trace_id}] " if trace_id else ""
        
        # Format: [TIME] LEVEL [TRACE] LOGGER: MESSAGE
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        message = record.getMessage()
        
        formatted = f"{color}[{timestamp}] {record.levelname:8s}{self.RESET} {trace_part}{record.name}: {message}"
        
        if record.exc_info:
            formatted += "\n" + self.formatException(record.exc_info)
        
        return formatted


def setup_logging(
    level: str = "INFO",
    json_format: bool = False,
    log_file: Optional[str] = None,
) -> None:
    """
    Configure logging for the R58 API.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: If True, use JSON structured logging
        log_file: Optional file path for logging
    """
    # Get log level from env or parameter
    level = os.environ.get("R58_LOG_LEVEL", level).upper()
    json_format = os.environ.get("R58_LOG_FORMAT", "text").lower() == "json" or json_format
    
    # Create handler(s)
    handlers = []
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    if json_format:
        console_handler.setFormatter(StructuredFormatter())
    else:
        console_handler.setFormatter(DevelopmentFormatter())
    handlers.append(console_handler)
    
    # File handler if specified
    if log_file:
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=50 * 1024 * 1024,  # 50MB
            backupCount=5,
        )
        file_handler.setFormatter(StructuredFormatter())
        handlers.append(file_handler)
    
    # Configure root logger
    root = logging.getLogger()
    root.setLevel(getattr(logging, level, logging.INFO))
    
    # Remove existing handlers
    for handler in root.handlers[:]:
        root.removeHandler(handler)
    
    # Add our handlers
    for handler in handlers:
        root.addHandler(handler)
    
    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("websockets").setLevel(logging.WARNING)
    
    # Log startup
    logger = logging.getLogger(__name__)
    logger.info(
        f"Logging configured: level={level}, format={'json' if json_format else 'text'}"
    )


class LoggerAdapter(logging.LoggerAdapter):
    """Logger adapter that includes trace ID and extra context"""
    
    def process(self, msg, kwargs):
        # Add trace ID to extra
        extra = kwargs.get("extra", {})
        extra["trace_id"] = get_trace_id()
        kwargs["extra"] = extra
        return msg, kwargs


def get_logger(name: str) -> LoggerAdapter:
    """Get a logger with trace ID support"""
    return LoggerAdapter(logging.getLogger(name), {})

