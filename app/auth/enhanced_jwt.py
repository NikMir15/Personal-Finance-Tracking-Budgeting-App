"""
Enhanced JWT authentication with security features.

This module provides:
- JWT access and refresh tokens with proper expiry
- Key rotation support
- Token revocation
- Secure token generation and validation
"""

import os
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass

import jwt
from fastapi import HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext

from app.config.security import security_config


@dataclass
class TokenData:
    """Token data structure."""
    username: str
    user_id: str
    token_type: str  # "access" or "refresh"
    issued_at: datetime
    expires_at: datetime
    key_id: str  # For key rotation


@dataclass
class TokenPair:
    """Access and refresh token pair."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 0  # Access token expiry in seconds


class EnhancedJWTAuth:
    """Enhanced JWT authentication with security features."""
    
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.security = HTTPBearer()
        
        # Token revocation store (in production, use Redis or database)
        self.revoked_tokens: set = set()
        
        # Key rotation
        self.current_key_id = self._get_current_key_id()
        self.signing_keys = self._load_signing_keys()
    
    def _get_current_key_id(self) -> str:
        """Get current key ID for key rotation."""
        key_id = os.getenv("JWT_KEY_ID", "")
        if not key_id:
            # Generate a new key ID based on date for automatic rotation
            now = datetime.utcnow()
            rotation_period = security_config.JWT_KEY_ROTATION_DAYS
            key_date = now - timedelta(days=now.day % rotation_period)
            key_id = key_date.strftime("%Y%m%d")
        return key_id
    
    def _load_signing_keys(self) -> Dict[str, str]:
        """Load signing keys for current and previous periods."""
        keys = {
            self.current_key_id: security_config.JWT_SECRET_KEY
        }
        
        # Add previous keys for validation during rotation
        for i, prev_key in enumerate(security_config.JWT_PREVIOUS_KEYS):
            if prev_key.strip():
                key_id = f"prev_{i}"
                keys[key_id] = prev_key.strip()
        
        return keys
    
    def _get_signing_key(self, key_id: str = None) -> str:
        """Get signing key by ID."""
        key_id = key_id or self.current_key_id
        return self.signing_keys.get(key_id, security_config.JWT_SECRET_KEY)
    
    def create_access_token(self, data: Dict[str, Any]) -> str:
        """Create access token with proper expiry and security."""
        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=security_config.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        
        payload = {
            **data,
            "exp": expire,
            "iat": now,
            "jti": secrets.token_urlsafe(16),  # JWT ID for revocation
            "token_type": "access",
            "key_id": self.current_key_id
        }
        
        return jwt.encode(
            payload, 
            self._get_signing_key(),
            algorithm=security_config.JWT_ALGORITHM
        )
    
    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """Create refresh token with longer expiry."""
        now = datetime.now(timezone.utc)
        expire = now + timedelta(days=security_config.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
        
        payload = {
            **data,
            "exp": expire,
            "iat": now,
            "jti": secrets.token_urlsafe(16),
            "token_type": "refresh",
            "key_id": self.current_key_id
        }
        
        return jwt.encode(
            payload,
            self._get_signing_key(),
            algorithm=security_config.JWT_ALGORITHM
        )
    
    def create_token_pair(self, username: str, user_id: str) -> TokenPair:
        """Create access and refresh token pair."""
        token_data = {
            "sub": username,
            "user_id": user_id,
        }
        
        access_token = self.create_access_token(token_data)
        refresh_token = self.create_refresh_token(token_data)
        
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=security_config.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
    
    def verify_token(self, token: str, token_type: str = "access") -> TokenData:
        """Verify and decode JWT token with security checks."""
        try:
            # First, decode without verification to get key_id
            unverified_payload = jwt.decode(token, options={"verify_signature": False})
            key_id = unverified_payload.get("key_id", self.current_key_id)
            
            # Now verify with the correct key
            payload = jwt.decode(
                token,
                self._get_signing_key(key_id),
                algorithms=[security_config.JWT_ALGORITHM]
            )
            
            # Validate token type
            if payload.get("token_type") != token_type:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={
                        "code": "INVALID_TOKEN_TYPE",
                        "message": f"Expected {token_type} token"
                    }
                )
            
            # Check if token is revoked
            jti = payload.get("jti")
            if jti and jti in self.revoked_tokens:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={
                        "code": "TOKEN_REVOKED",
                        "message": "Token has been revoked"
                    }
                )
            
            # Additional security checks
            username = payload.get("sub")
            user_id = payload.get("user_id")
            
            if not username or not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={
                        "code": "INVALID_TOKEN_PAYLOAD",
                        "message": "Token missing required claims"
                    }
                )
            
            return TokenData(
                username=username,
                user_id=user_id,
                token_type=token_type,
                issued_at=datetime.fromtimestamp(payload["iat"], timezone.utc),
                expires_at=datetime.fromtimestamp(payload["exp"], timezone.utc),
                key_id=key_id
            )
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "code": "TOKEN_EXPIRED",
                    "message": "Token has expired"
                }
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "code": "INVALID_TOKEN",
                    "message": f"Invalid token: {str(e)}"
                }
            )
    
    def refresh_access_token(self, refresh_token: str) -> TokenPair:
        """Create new access token from refresh token."""
        # Verify refresh token
        token_data = self.verify_token(refresh_token, "refresh")
        
        # Create new token pair
        new_tokens = self.create_token_pair(token_data.username, token_data.user_id)
        
        # Optionally revoke the old refresh token for security
        # (uncomment for stricter security)
        # self.revoke_token(refresh_token)
        
        return new_tokens
    
    def revoke_token(self, token: str) -> bool:
        """Revoke a token by adding its JTI to revocation list."""
        try:
            unverified_payload = jwt.decode(token, options={"verify_signature": False})
            jti = unverified_payload.get("jti")
            
            if jti:
                self.revoked_tokens.add(jti)
                return True
            
        except jwt.InvalidTokenError:
            pass
        
        return False
    
    def revoke_all_user_tokens(self, user_id: str) -> int:
        """Revoke all tokens for a user (for logout all devices)."""
        # In production, this would query database for user's tokens
        # For now, this is a placeholder that would need proper implementation
        # with token storage in database
        count = 0
        
        # This is a simplified version - in production you'd store tokens
        # in a database with user_id and revoke them there
        tokens_to_revoke = []
        for jti in list(self.revoked_tokens):
            # This would check if JTI belongs to user_id
            # tokens_to_revoke.append(jti)
            pass
        
        return count
    
    def cleanup_expired_tokens(self) -> int:
        """Remove expired tokens from revocation list."""
        # In production, this would clean up database records
        # For in-memory store, we can't easily determine expiry
        # This is a placeholder for proper implementation
        return 0
    
    def get_token_info(self, token: str) -> Dict[str, Any]:
        """Get token information without full verification."""
        try:
            payload = jwt.decode(token, options={"verify_signature": False})
            
            return {
                "username": payload.get("sub"),
                "user_id": payload.get("user_id"),
                "token_type": payload.get("token_type"),
                "expires_at": datetime.fromtimestamp(payload["exp"], timezone.utc).isoformat(),
                "issued_at": datetime.fromtimestamp(payload["iat"], timezone.utc).isoformat(),
                "key_id": payload.get("key_id"),
                "jti": payload.get("jti")
            }
        except jwt.InvalidTokenError:
            return {}


# Global instance
enhanced_jwt = EnhancedJWTAuth()
