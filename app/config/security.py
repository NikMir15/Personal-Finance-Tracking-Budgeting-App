"""
Security configuration for the Expense Tracker application.

This module provides centralized security configuration including:
- CORS settings with environment-based origins
- Security headers configuration
- JWT settings with proper expiry and rotation
- Rate limiting configuration
- HTTPS and cookie security settings
"""

import os
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()


class SecurityConfig:
    """Centralized security configuration."""
    
    # CORS Configuration
    _base_cors_origins = [
        # Development origins
        "http://localhost:3000",  # React dev server
        "http://localhost:8080",  # Vue dev server  
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:5173",
    ]
    
    # Add production origins from environment
    _env_origins = os.getenv("CORS_ORIGINS", "").split(",") if os.getenv("CORS_ORIGINS") else []
    CORS_ORIGINS: List[str] = _base_cors_origins + _env_origins
    
    # Remove empty strings and wildcards
    CORS_ORIGINS = [origin.strip() for origin in CORS_ORIGINS if origin.strip() and origin.strip() != "*"]
    
    # HTTPS and Cookie Security
    SECURE_COOKIES = os.getenv("SECURE_COOKIES", "false").lower() == "true"
    HTTPS_ONLY = os.getenv("HTTPS_ONLY", "false").lower() == "true"
    
    # JWT Security Configuration
    JWT_SECRET_KEY = os.getenv("SECRET_KEY", "development-secret-key-change-in-production")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    JWT_REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    
    # Key rotation settings
    JWT_KEY_ROTATION_DAYS = int(os.getenv("JWT_KEY_ROTATION_DAYS", "30"))
    JWT_PREVIOUS_KEYS = os.getenv("JWT_PREVIOUS_KEYS", "").split(",") if os.getenv("JWT_PREVIOUS_KEYS") else []
    
    # Rate Limiting Configuration
    RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    
    # Auth endpoints rate limits (more restrictive)
    AUTH_RATE_LIMIT = os.getenv("AUTH_RATE_LIMIT", "5/minute")  # 5 attempts per minute
    AUTH_BURST_LIMIT = os.getenv("AUTH_BURST_LIMIT", "20/hour")  # 20 attempts per hour
    
    # Write endpoints rate limits
    WRITE_RATE_LIMIT = os.getenv("WRITE_RATE_LIMIT", "100/minute")  # 100 writes per minute
    WRITE_BURST_LIMIT = os.getenv("WRITE_BURST_LIMIT", "1000/hour")  # 1000 writes per hour
    
    # General API rate limits
    API_RATE_LIMIT = os.getenv("API_RATE_LIMIT", "1000/minute")  # 1000 requests per minute
    API_BURST_LIMIT = os.getenv("API_BURST_LIMIT", "10000/hour")  # 10000 requests per hour
    
    # Security Headers Configuration
    SECURITY_HEADERS = {
        # Prevent MIME type sniffing
        "X-Content-Type-Options": "nosniff",
        
        # Prevent embedding in frames (clickjacking protection)
        "X-Frame-Options": "DENY",
        
        # XSS protection
        "X-XSS-Protection": "1; mode=block",
        
        # Referrer policy
        "Referrer-Policy": "strict-origin-when-cross-origin",
        
        # Permissions policy (formerly Feature-Policy)
        "Permissions-Policy": "camera=(), microphone=(), geolocation=(), interest-cohort=()",
        
        # Content Security Policy
        "Content-Security-Policy": (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://unpkg.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
            "img-src 'self' data: blob: https:; "
            "font-src 'self' https://fonts.gstatic.com; "
            "connect-src 'self'; "
            "media-src 'self'; "
            "object-src 'none'; "
            "child-src 'none'; "
            "worker-src 'self'; "
            "manifest-src 'self'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "frame-ancestors 'none'; "
            "upgrade-insecure-requests"
        )
    }
    
    # HTTPS-specific headers (only when HTTPS is enabled)
    if HTTPS_ONLY:
        SECURITY_HEADERS.update({
            # HTTP Strict Transport Security
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
            
            # Expect-CT (Certificate Transparency)
            "Expect-CT": "max-age=86400, enforce"
        })
    
    # Environment-specific CSP adjustments
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    
    if ENVIRONMENT == "development":
        # More permissive CSP for development
        SECURITY_HEADERS["Content-Security-Policy"] = (
            "default-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https: http:; "
            "style-src 'self' 'unsafe-inline' https: http:; "
            "img-src 'self' data: blob: https: http:; "
            "font-src 'self' https: http: data:; "
            "connect-src 'self' https: http: ws: wss:; "
            "media-src 'self' https: http:; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )


class SecurityUtils:
    """Security utility functions."""
    
    @staticmethod
    def get_cors_origins() -> List[str]:
        """Get CORS origins based on environment."""
        origins = SecurityConfig.CORS_ORIGINS.copy()
        
        # In development, allow localhost variations
        if SecurityConfig.ENVIRONMENT == "development":
            dev_origins = [
                "http://localhost:8000",  # API itself for docs
                "http://127.0.0.1:8000",
            ]
            origins.extend(dev_origins)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_origins = []
        for origin in origins:
            if origin not in seen:
                seen.add(origin)
                unique_origins.append(origin)
        
        return unique_origins
    
    @staticmethod
    def is_production() -> bool:
        """Check if running in production environment."""
        return SecurityConfig.ENVIRONMENT == "production"
    
    @staticmethod
    def get_cookie_settings() -> Dict[str, Any]:
        """Get secure cookie settings based on environment."""
        return {
            "secure": SecurityConfig.SECURE_COOKIES,
            "httponly": True,
            "samesite": "strict" if SecurityConfig.HTTPS_ONLY else "lax",
            "max_age": SecurityConfig.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
    
    @staticmethod
    def get_rate_limit_key(request_info: str, user_id: str = None) -> str:
        """Generate rate limit key for request."""
        if user_id:
            return f"rate_limit:{user_id}:{request_info}"
        else:
            return f"rate_limit:anonymous:{request_info}"
    
    @staticmethod
    def should_enforce_https(request_headers: Dict[str, str]) -> bool:
        """Check if HTTPS should be enforced based on headers."""
        if not SecurityConfig.HTTPS_ONLY:
            return False
        
        # Check for common reverse proxy headers
        forwarded_proto = request_headers.get("x-forwarded-proto", "").lower()
        forwarded_ssl = request_headers.get("x-forwarded-ssl", "").lower()
        
        return (
            forwarded_proto == "https" or
            forwarded_ssl == "on" or
            SecurityConfig.ENVIRONMENT == "production"
        )


# Export the main configuration
security_config = SecurityConfig()
security_utils = SecurityUtils()
