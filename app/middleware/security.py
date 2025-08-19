"""
Security middleware for the Expense Tracker application.

This module provides middleware for:
- Security headers injection
- HTTPS enforcement  
- Rate limiting
- Request security validation
"""

import time
import asyncio
from typing import Dict, Any, Optional
from collections import defaultdict, deque
from datetime import datetime, timedelta

from fastapi import Request, Response, HTTPException, status
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config.security import security_config, security_utils


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses."""
    
    async def dispatch(self, request: Request, call_next):
        """Add security headers to response."""
        response = await call_next(request)
        
        # Add all configured security headers
        for header_name, header_value in security_config.SECURITY_HEADERS.items():
            response.headers[header_name] = header_value
        
        # Add security-related headers based on environment
        if security_utils.is_production():
            # Additional production security headers
            response.headers["Server"] = "ExpenseTracker"  # Hide server details
            
        return response


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce HTTPS in production."""
    
    async def dispatch(self, request: Request, call_next):
        """Redirect HTTP to HTTPS if required."""
        if not security_config.HTTPS_ONLY:
            return await call_next(request)
        
        # Check if request is already HTTPS or from reverse proxy
        is_secure = (
            request.url.scheme == "https" or
            security_utils.should_enforce_https(dict(request.headers))
        )
        
        if not is_secure and security_utils.is_production():
            # Redirect to HTTPS
            url = request.url.replace(scheme="https")
            return RedirectResponse(url=str(url), status_code=301)
        
        return await call_next(request)


class RateLimitStore:
    """In-memory rate limiting store with sliding window."""
    
    def __init__(self):
        self.requests: Dict[str, deque] = defaultdict(lambda: deque())
        self.cleanup_interval = 60  # Cleanup every 60 seconds
        self.last_cleanup = time.time()
    
    def is_allowed(self, key: str, limit: int, window_seconds: int) -> bool:
        """Check if request is allowed under rate limit."""
        now = time.time()
        
        # Periodic cleanup
        if now - self.last_cleanup > self.cleanup_interval:
            self._cleanup()
            self.last_cleanup = now
        
        # Get request times for this key
        request_times = self.requests[key]
        
        # Remove requests outside the window
        cutoff = now - window_seconds
        while request_times and request_times[0] < cutoff:
            request_times.popleft()
        
        # Check if limit is exceeded
        if len(request_times) >= limit:
            return False
        
        # Record this request
        request_times.append(now)
        return True
    
    def get_reset_time(self, key: str, window_seconds: int) -> float:
        """Get the time when the rate limit resets."""
        request_times = self.requests[key]
        if not request_times:
            return time.time()
        
        return request_times[0] + window_seconds
    
    def _cleanup(self):
        """Remove old entries to prevent memory leaks."""
        now = time.time()
        keys_to_remove = []
        
        for key, request_times in self.requests.items():
            # Remove old requests
            cutoff = now - 3600  # Keep data for 1 hour
            while request_times and request_times[0] < cutoff:
                request_times.popleft()
            
            # If no recent requests, remove the key
            if not request_times:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.requests[key]


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware with different limits for different endpoints."""
    
    def __init__(self, app):
        super().__init__(app)
        self.store = RateLimitStore()
        
        # Rate limit configurations (requests, window_seconds)
        self.limits = {
            "auth": (5, 60),      # 5 requests per minute for auth
            "write": (100, 60),   # 100 requests per minute for writes
            "read": (1000, 60),   # 1000 requests per minute for reads
            "default": (500, 60), # 500 requests per minute default
        }
    
    async def dispatch(self, request: Request, call_next):
        """Apply rate limiting based on endpoint type."""
        if not security_config.RATE_LIMIT_ENABLED:
            return await call_next(request)
        
        # Determine rate limit category
        limit_category = self._get_limit_category(request)
        limit, window = self.limits[limit_category]
        
        # Generate rate limit key
        client_ip = self._get_client_ip(request)
        user_id = getattr(request.state, "user_id", None)
        key = security_utils.get_rate_limit_key(
            f"{limit_category}:{client_ip}", 
            user_id
        )
        
        # Check rate limit
        if not self.store.is_allowed(key, limit, window):
            reset_time = self.store.get_reset_time(key, window)
            retry_after = max(1, int(reset_time - time.time()))
            
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": f"Rate limit exceeded for {limit_category} operations",
                    "retry_after": retry_after,
                    "limit": limit,
                    "window": window
                },
                headers={"Retry-After": str(retry_after)}
            )
        
        # Add rate limit headers to response
        response = await call_next(request)
        
        # Calculate remaining requests
        request_times = self.store.requests[key]
        remaining = max(0, limit - len(request_times))
        reset_time = self.store.get_reset_time(key, window)
        
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(reset_time))
        response.headers["X-RateLimit-Window"] = str(window)
        
        return response
    
    def _get_limit_category(self, request: Request) -> str:
        """Determine rate limit category based on request."""
        path = request.url.path
        method = request.method
        
        # Auth endpoints (most restrictive)
        if path.startswith("/auth/"):
            return "auth"
        
        # Write operations
        if method in ["POST", "PUT", "PATCH", "DELETE"]:
            return "write"
        
        # Read operations
        if method in ["GET", "HEAD", "OPTIONS"]:
            return "read"
        
        return "default"
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request."""
        # Check common reverse proxy headers
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()
        
        # Fallback to direct connection
        return request.client.host if request.client else "unknown"


class SecurityValidationMiddleware(BaseHTTPMiddleware):
    """Middleware for general security validation."""
    
    async def dispatch(self, request: Request, call_next):
        """Perform security validations on incoming requests."""
        
        # Validate request size (prevent DoS)
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                size = int(content_length)
                max_size = 10 * 1024 * 1024  # 10MB limit
                if size > max_size:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail={
                            "code": "REQUEST_TOO_LARGE",
                            "message": f"Request size {size} exceeds maximum {max_size} bytes"
                        }
                    )
            except ValueError:
                pass
        
        # Validate Host header (prevent Host header injection)
        if security_utils.is_production():
            host = request.headers.get("host", "")
            allowed_hosts = [
                "api.expensetracker.com",  # Replace with actual domain
                "expensetracker.com",
                "www.expensetracker.com"
            ]
            
            if host and not any(host.endswith(allowed) for allowed in allowed_hosts):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "code": "INVALID_HOST",
                        "message": "Invalid Host header"
                    }
                )
        
        # Check for suspicious headers/patterns
        user_agent = request.headers.get("user-agent", "").lower()
        suspicious_patterns = [
            "sqlmap", "nikto", "nmap", "masscan", 
            "zgrab", "shodan", "censys"
        ]
        
        if any(pattern in user_agent for pattern in suspicious_patterns):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "SUSPICIOUS_REQUEST",
                    "message": "Request rejected for security reasons"
                }
            )
        
        return await call_next(request)


# Global middleware instances
security_headers_middleware = SecurityHeadersMiddleware
https_redirect_middleware = HTTPSRedirectMiddleware  
rate_limit_middleware = RateLimitMiddleware
security_validation_middleware = SecurityValidationMiddleware
