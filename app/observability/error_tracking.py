"""
Error tracking and monitoring for the Expense Tracker application.

This module provides:
- Sentry integration with PII-safe configuration
- Custom error tracking with breadcrumbs
- Error categorization and filtering
- Performance monitoring integration
- PII scrubbing for error reports
"""

import os
import re
import logging
from typing import Any, Dict, List, Optional, Union
from functools import wraps

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from fastapi import Request, HTTPException

from app.observability.logging_config import get_logger, request_id_var, user_id_var

logger = get_logger("error_tracking")


class PIIScrubber:
    """Class to scrub PII from error data before sending to Sentry."""
    
    # Patterns for PII detection
    PII_PATTERNS = {
        'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
        'phone': re.compile(r'(\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})'),
        'ssn': re.compile(r'\b\d{3}-?\d{2}-?\d{4}\b'),
        'credit_card': re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b'),
        'ip_address': re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'),
        'jwt_token': re.compile(r'\beyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*\b'),
        'api_key': re.compile(r'\b[A-Za-z0-9]{32,}\b'),
        'password': re.compile(r'(password|pwd|pass)["\s]*[:=]["\s]*[^"\s,}]+', re.IGNORECASE)
    }
    
    # Fields that should be completely removed
    PII_FIELDS = {
        'password', 'hashed_password', 'secret', 'token', 'api_key',
        'email', 'phone', 'ssn', 'credit_card', 'full_name',
        'first_name', 'last_name', 'address', 'postal_code',
        'social_security_number', 'date_of_birth', 'driver_license'
    }
    
    @classmethod
    def scrub_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Scrub PII from a dictionary."""
        if not isinstance(data, dict):
            return data
        
        scrubbed = {}
        
        for key, value in data.items():
            key_lower = key.lower()
            
            # Check if field should be completely removed
            if any(pii_field in key_lower for pii_field in cls.PII_FIELDS):
                if 'email' in key_lower:
                    # Partially mask email for debugging
                    scrubbed[key] = cls._mask_email(str(value)) if value else "[MASKED]"
                else:
                    scrubbed[key] = "[MASKED]"
            elif isinstance(value, dict):
                scrubbed[key] = cls.scrub_dict(value)
            elif isinstance(value, list):
                scrubbed[key] = [cls.scrub_dict(item) if isinstance(item, dict) else cls._scrub_string(str(item)) for item in value]
            elif isinstance(value, str):
                scrubbed[key] = cls._scrub_string(value)
            else:
                scrubbed[key] = value
        
        return scrubbed
    
    @classmethod
    def _scrub_string(cls, text: str) -> str:
        """Scrub PII patterns from a string."""
        if not isinstance(text, str):
            return text
        
        scrubbed = text
        
        for pattern_name, pattern in cls.PII_PATTERNS.items():
            if pattern_name == 'email':
                # Replace emails with masked version
                scrubbed = pattern.sub(lambda m: cls._mask_email(m.group()), scrubbed)
            else:
                # Replace other patterns with placeholder
                scrubbed = pattern.sub(f'[{pattern_name.upper()}_MASKED]', scrubbed)
        
        return scrubbed
    
    @classmethod
    def _mask_email(cls, email: str) -> str:
        """Mask email while preserving domain for debugging."""
        try:
            if '@' not in email:
                return "[INVALID_EMAIL]"
            
            local, domain = email.split('@', 1)
            if len(local) <= 2:
                masked_local = '*' * len(local)
            else:
                masked_local = local[:1] + '*' * (len(local) - 2) + local[-1:]
            
            return f"{masked_local}@{domain}"
        except:
            return "[EMAIL_MASK_ERROR]"


def before_send(event, hint):
    """
    Sentry before_send hook to scrub PII and add context.
    
    This function is called before every event is sent to Sentry.
    """
    try:
        # Add request context if available
        request_id = request_id_var.get('')
        user_id = user_id_var.get('')
        
        if request_id:
            event.setdefault('tags', {})['request_id'] = request_id
        
        if user_id and user_id != '':
            # Hash user ID for privacy
            import hashlib
            hashed_user_id = hashlib.sha256(user_id.encode()).hexdigest()[:8]
            event.setdefault('tags', {})['user_id_hash'] = hashed_user_id
        
        # Scrub PII from the event
        if 'extra' in event:
            event['extra'] = PIIScrubber.scrub_dict(event['extra'])
        
        if 'breadcrumbs' in event:
            for breadcrumb in event['breadcrumbs']['values']:
                if 'data' in breadcrumb:
                    breadcrumb['data'] = PIIScrubber.scrub_dict(breadcrumb['data'])
                if 'message' in breadcrumb:
                    breadcrumb['message'] = PIIScrubber._scrub_string(breadcrumb['message'])
        
        # Scrub exception values
        if 'exception' in event:
            for exception in event['exception']['values']:
                if 'value' in exception:
                    exception['value'] = PIIScrubber._scrub_string(exception['value'])
        
        # Scrub request data
        if 'request' in event:
            request_data = event['request']
            
            # Scrub headers
            if 'headers' in request_data:
                scrubbed_headers = {}
                for key, value in request_data['headers'].items():
                    key_lower = key.lower()
                    if 'authorization' in key_lower or 'cookie' in key_lower or 'token' in key_lower:
                        scrubbed_headers[key] = "[MASKED]"
                    else:
                        scrubbed_headers[key] = PIIScrubber._scrub_string(str(value))
                request_data['headers'] = scrubbed_headers
            
            # Scrub form data and JSON data
            for data_key in ['data', 'json']:
                if data_key in request_data:
                    request_data[data_key] = PIIScrubber.scrub_dict(request_data[data_key])
        
        return event
        
    except Exception as e:
        # If scrubbing fails, log it but still send the event
        logger.error(f"Error in Sentry before_send hook: {e}")
        return event


def initialize_error_tracking(
    dsn: Optional[str] = None,
    environment: str = "development",
    sample_rate: float = 1.0,
    traces_sample_rate: float = 0.1,
    enable_tracing: bool = True
) -> None:
    """
    Initialize Sentry error tracking.
    
    Args:
        dsn: Sentry DSN (if None, will check environment variables)
        environment: Environment name (development, staging, production)
        sample_rate: Error sampling rate (0.0 to 1.0)
        traces_sample_rate: Performance monitoring sampling rate
        enable_tracing: Whether to enable performance monitoring
    """
    
    # Get DSN from environment if not provided
    if not dsn:
        dsn = os.getenv('SENTRY_DSN')
    
    if not dsn:
        logger.warning("Sentry DSN not configured, error tracking disabled")
        return
    
    # Configure integrations
    integrations = [
        FastApiIntegration(auto_enabling_integrations=False),
        SqlalchemyIntegration(),
        LoggingIntegration(
            level=logging.INFO,        # Capture info and above as breadcrumbs
            event_level=logging.ERROR  # Send errors and above as events
        ),
    ]
    
    # Initialize Sentry
    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        sample_rate=sample_rate,
        traces_sample_rate=traces_sample_rate if enable_tracing else 0.0,
        integrations=integrations,
        before_send=before_send,
        send_default_pii=False,  # Never send PII
        attach_stacktrace=True,
        max_breadcrumbs=50,
        release=os.getenv('APP_VERSION', '1.0.0'),
        server_name=os.getenv('SERVER_NAME', 'expense-tracker'),
    )
    
    logger.info(
        "Sentry error tracking initialized",
        environment=environment,
        sample_rate=sample_rate,
        traces_sample_rate=traces_sample_rate
    )


def capture_exception(
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    user_context: Optional[Dict[str, Any]] = None,
    tags: Optional[Dict[str, str]] = None,
    level: str = "error"
) -> Optional[str]:
    """
    Capture an exception with additional context.
    
    Args:
        error: The exception to capture
        context: Additional context data
        user_context: User-specific context (will be scrubbed)
        tags: Tags to add to the event
        level: Error level (error, warning, info, debug)
        
    Returns:
        Event ID if captured successfully
    """
    
    with sentry_sdk.configure_scope() as scope:
        # Add context
        if context:
            for key, value in PIIScrubber.scrub_dict(context).items():
                scope.set_extra(key, value)
        
        # Add user context (scrubbed)
        if user_context:
            scrubbed_user = PIIScrubber.scrub_dict(user_context)
            scope.set_user(scrubbed_user)
        
        # Add tags
        if tags:
            for key, value in tags.items():
                scope.set_tag(key, value)
        
        # Add request context
        request_id = request_id_var.get('')
        user_id = user_id_var.get('')
        
        if request_id:
            scope.set_tag('request_id', request_id)
        
        if user_id:
            # Hash user ID for privacy
            import hashlib
            hashed_user_id = hashlib.sha256(user_id.encode()).hexdigest()[:8]
            scope.set_tag('user_id_hash', hashed_user_id)
        
        # Capture the exception
        event_id = sentry_sdk.capture_exception(error)
        
        logger.info(
            "Exception captured",
            event_id=event_id,
            error_type=type(error).__name__,
            error_message=str(error)
        )
        
        return event_id


def add_breadcrumb(
    message: str,
    category: str = "custom",
    level: str = "info",
    data: Optional[Dict[str, Any]] = None
) -> None:
    """
    Add a breadcrumb for debugging context.
    
    Args:
        message: Breadcrumb message
        category: Category (http, db, auth, business, etc.)
        level: Level (debug, info, warning, error)
        data: Additional data (will be scrubbed)
    """
    
    # Scrub PII from data and message
    safe_message = PIIScrubber._scrub_string(message)
    safe_data = PIIScrubber.scrub_dict(data) if data else None
    
    sentry_sdk.add_breadcrumb(
        message=safe_message,
        category=category,
        level=level,
        data=safe_data
    )


def track_performance(
    operation_name: str,
    description: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None
):
    """
    Context manager for performance tracking.
    
    Args:
        operation_name: Name of the operation
        description: Optional description
        data: Additional data (will be scrubbed)
    """
    
    safe_data = PIIScrubber.scrub_dict(data) if data else None
    
    return sentry_sdk.start_transaction(
        op=operation_name,
        name=description or operation_name,
        custom_sampling_context=safe_data
    )


def sentry_trace(operation_name: str = None):
    """
    Decorator to automatically trace function performance.
    
    Args:
        operation_name: Custom operation name (defaults to function name)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            
            with track_performance(op_name):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    capture_exception(
                        e,
                        context={
                            'function': func.__name__,
                            'module': func.__module__,
                            'args_count': len(args),
                            'kwargs_keys': list(kwargs.keys())
                        },
                        tags={'component': 'function_call'}
                    )
                    raise
        return wrapper
    return decorator


def capture_message(
    message: str,
    level: str = "info",
    context: Optional[Dict[str, Any]] = None,
    tags: Optional[Dict[str, str]] = None
) -> Optional[str]:
    """
    Capture a custom message.
    
    Args:
        message: Message to capture
        level: Message level
        context: Additional context
        tags: Tags to add
        
    Returns:
        Event ID if captured successfully
    """
    
    safe_message = PIIScrubber._scrub_string(message)
    
    with sentry_sdk.configure_scope() as scope:
        if context:
            for key, value in PIIScrubber.scrub_dict(context).items():
                scope.set_extra(key, value)
        
        if tags:
            for key, value in tags.items():
                scope.set_tag(key, value)
        
        return sentry_sdk.capture_message(safe_message, level=level)


def setup_custom_error_handlers(app):
    """Setup custom error handlers for FastAPI."""
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions with proper logging and tracking."""
        
        # Add breadcrumb for HTTP error
        add_breadcrumb(
            message=f"HTTP {exc.status_code}: {exc.detail}",
            category="http",
            level="warning" if exc.status_code < 500 else "error",
            data={
                'status_code': exc.status_code,
                'method': request.method,
                'url': str(request.url),
                'client_ip': request.client.host if request.client else None
            }
        )
        
        # Capture 5xx errors in Sentry
        if exc.status_code >= 500:
            capture_exception(
                exc,
                context={
                    'status_code': exc.status_code,
                    'method': request.method,
                    'url': str(request.url),
                    'detail': exc.detail
                },
                tags={
                    'error_type': 'http_exception',
                    'status_code': str(exc.status_code)
                }
            )
        
        # Return the original response
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": f"HTTP_{exc.status_code}",
                "message": str(exc.detail) if exc.detail else "An error occurred"
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle general exceptions."""
        
        # Capture all unhandled exceptions
        event_id = capture_exception(
            exc,
            context={
                'method': request.method,
                'url': str(request.url),
                'client_ip': request.client.host if request.client else None
            },
            tags={
                'error_type': 'unhandled_exception',
                'handler': 'general_exception_handler'
            }
        )
        
        logger.error(
            "Unhandled exception",
            error_type=type(exc).__name__,
            error_message=str(exc),
            event_id=event_id,
            method=request.method,
            url=str(request.url)
        )
        
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=500,
            content={
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
                "error_id": event_id
            }
        )
