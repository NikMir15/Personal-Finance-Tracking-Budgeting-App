"""
Structured logging configuration for the Expense Tracker application.

This module provides:
- JSON structured logging with request IDs
- Consistent error log formatting
- PII-safe logging utilities
- Request/response logging middleware
- Performance monitoring integration
"""

import json
import logging
import sys
import time
import uuid
from contextvars import ContextVar
from typing import Any, Dict, Optional, Union
from datetime import datetime

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

# Context variables for request tracking
request_id_var: ContextVar[str] = ContextVar('request_id', default='')
user_id_var: ContextVar[str] = ContextVar('user_id', default='')
request_path_var: ContextVar[str] = ContextVar('request_path', default='')


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Middleware to add request context to all logs."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next):
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        request_id_var.set(request_id)
        request_path_var.set(str(request.url.path))
        
        # Extract user ID from JWT if available
        user_id = self._extract_user_id(request)
        if user_id:
            user_id_var.set(user_id)
        
        # Add request ID to response headers
        start_time = time.time()
        
        try:
            response = await call_next(request)
            
            # Log the request
            duration = time.time() - start_time
            self._log_request(request, response, duration, request_id)
            
            response.headers["X-Request-ID"] = request_id
            return response
            
        except Exception as e:
            # Log the error
            duration = time.time() - start_time
            self._log_error(request, e, duration, request_id)
            raise
    
    def _extract_user_id(self, request: Request) -> Optional[str]:
        """Extract user ID from JWT token (PII-safe)."""
        try:
            auth_header = request.headers.get("authorization", "")
            if not auth_header.startswith("Bearer "):
                return None
            
            # In a real implementation, you'd decode the JWT
            # For now, we'll use a placeholder
            # token = auth_header.split(" ")[1]
            # payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            # return payload.get("sub")  # subject (user identifier)
            
            return "user_from_jwt"  # Placeholder
        except Exception:
            return None
    
    def _log_request(self, request: Request, response: Response, duration: float, request_id: str):
        """Log HTTP request/response in structured format."""
        log_data = {
            "request_id": request_id,
            "method": request.method,
            "path": str(request.url.path),
            "query_params": dict(request.query_params) if request.query_params else None,
            "status_code": response.status_code,
            "duration_ms": round(duration * 1000, 2),
            "user_agent": request.headers.get("user-agent"),
            "client_ip": self._get_client_ip(request),
            "user_id": user_id_var.get() if user_id_var.get() != '' else None,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Log at appropriate level based on status code
        if response.status_code >= 500:
            structlog.get_logger().error("HTTP request completed", **log_data)
        elif response.status_code >= 400:
            structlog.get_logger().warning("HTTP request completed", **log_data)
        else:
            structlog.get_logger().info("HTTP request completed", **log_data)
    
    def _log_error(self, request: Request, error: Exception, duration: float, request_id: str):
        """Log HTTP request errors in structured format."""
        log_data = {
            "request_id": request_id,
            "method": request.method,
            "path": str(request.url.path),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "duration_ms": round(duration * 1000, 2),
            "user_agent": request.headers.get("user-agent"),
            "client_ip": self._get_client_ip(request),
            "user_id": user_id_var.get() if user_id_var.get() != '' else None,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        structlog.get_logger().error("HTTP request failed", **log_data, exc_info=True)
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address (with proxy support)."""
        # Check for forwarded headers first (reverse proxy/load balancer)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fallback to direct connection
        if hasattr(request.client, 'host'):
            return request.client.host
        
        return "unknown"


def setup_logging(
    log_level: str = "INFO",
    json_logs: bool = True,
    include_request_id: bool = True
) -> None:
    """
    Configure structured logging for the application.
    
    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_logs: Whether to output logs in JSON format
        include_request_id: Whether to include request ID in all logs
    """
    
    # Configure structlog
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
    ]
    
    if include_request_id:
        processors.append(add_request_context)
    
    if json_logs:
        processors.extend([
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer()
        ])
    else:
        processors.extend([
            structlog.dev.ConsoleRenderer(colors=True)
        ])
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(log_level.upper())
        ),
        logger_factory=structlog.WriteLoggerFactory(sys.stdout),
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper())
    )
    
    # Suppress noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)


def add_request_context(logger, method_name, event_dict):
    """Add request context to log entries."""
    request_id = request_id_var.get()
    user_id = user_id_var.get()
    request_path = request_path_var.get()
    
    if request_id:
        event_dict["request_id"] = request_id
    if user_id:
        event_dict["user_id"] = user_id
    if request_path:
        event_dict["request_path"] = request_path
    
    # Add timestamp if not present
    if "timestamp" not in event_dict:
        event_dict["timestamp"] = datetime.utcnow().isoformat()
    
    return event_dict


def get_logger(name: str = None) -> structlog.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


def log_pii_safe(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove or mask PII from data before logging.
    
    Args:
        data: Dictionary potentially containing PII
        
    Returns:
        Dictionary with PII removed/masked
    """
    pii_fields = {
        'password', 'hashed_password', 'secret', 'token', 'api_key',
        'email', 'phone', 'ssn', 'credit_card', 'account_number',
        'full_name', 'first_name', 'last_name', 'address'
    }
    
    safe_data = {}
    
    for key, value in data.items():
        key_lower = key.lower()
        
        if any(pii_field in key_lower for pii_field in pii_fields):
            if key_lower in ['email']:
                # Partially mask email
                if isinstance(value, str) and '@' in value:
                    local, domain = value.split('@', 1)
                    masked_local = local[:2] + '*' * (len(local) - 2)
                    safe_data[key] = f"{masked_local}@{domain}"
                else:
                    safe_data[key] = "[MASKED]"
            else:
                # Completely mask other PII
                safe_data[key] = "[MASKED]"
        else:
            safe_data[key] = value
    
    return safe_data


def log_database_operation(
    operation: str,
    table: str,
    record_id: Optional[str] = None,
    user_id: Optional[str] = None,
    duration_ms: Optional[float] = None,
    error: Optional[Exception] = None
) -> None:
    """
    Log database operations in a structured way.
    
    Args:
        operation: Type of operation (SELECT, INSERT, UPDATE, DELETE)
        table: Database table name
        record_id: ID of the record (if applicable)
        user_id: User performing the operation
        duration_ms: Operation duration in milliseconds
        error: Any error that occurred
    """
    logger = get_logger("database")
    
    log_data = {
        "operation": operation.upper(),
        "table": table,
        "record_id": record_id,
        "user_id": user_id or user_id_var.get(),
        "duration_ms": duration_ms,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if error:
        log_data["error_type"] = type(error).__name__
        log_data["error_message"] = str(error)
        logger.error("Database operation failed", **log_data)
    else:
        logger.info("Database operation completed", **log_data)


def log_api_error(
    error: Exception,
    request: Request,
    additional_context: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log API errors with consistent formatting.
    
    Args:
        error: The exception that occurred
        request: FastAPI request object
        additional_context: Additional context to include in log
    """
    logger = get_logger("api")
    
    # Build PII-safe context
    context = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "method": request.method,
        "path": str(request.url.path),
        "query_params": dict(request.query_params) if request.query_params else None,
        "user_agent": request.headers.get("user-agent"),
        "client_ip": RequestContextMiddleware(None)._get_client_ip(request),
        "request_id": request_id_var.get(),
        "user_id": user_id_var.get() if user_id_var.get() != '' else None,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if additional_context:
        # Apply PII filtering to additional context
        safe_context = log_pii_safe(additional_context)
        context.update(safe_context)
    
    logger.error("API error occurred", **context, exc_info=True)


def log_business_event(
    event_type: str,
    user_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log business/application events.
    
    Args:
        event_type: Type of business event (e.g., 'user_registered', 'expense_created')
        user_id: User ID associated with the event
        details: Additional event details (will be PII-filtered)
    """
    logger = get_logger("business")
    
    log_data = {
        "event_type": event_type,
        "user_id": user_id or user_id_var.get(),
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if details:
        safe_details = log_pii_safe(details)
        log_data["details"] = safe_details
    
    logger.info("Business event occurred", **log_data)


# Pre-configured loggers for different components
api_logger = get_logger("api")
database_logger = get_logger("database")
business_logger = get_logger("business")
security_logger = get_logger("security")
performance_logger = get_logger("performance")
