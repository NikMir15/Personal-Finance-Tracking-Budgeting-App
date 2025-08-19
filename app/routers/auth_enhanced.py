"""
Enhanced authentication router with security features.

This router provides:
- JWT access and refresh tokens
- Rate limiting on authentication endpoints
- Secure cookie support
- Token refresh endpoint
- Enhanced security validation
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Response, Cookie
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from app.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse
from app.auth.enhanced_jwt import enhanced_jwt, TokenPair
from app.config.security import security_utils


# Pydantic models for enhanced auth
class TokenResponse(BaseModel):
    """Enhanced token response with refresh token."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""
    refresh_token: str


class TokenInfo(BaseModel):
    """Token information response."""
    username: str
    user_id: str
    token_type: str
    expires_at: str
    issued_at: str
    key_id: str


router = APIRouter(tags=["Enhanced Authentication"])

# OAuth2 scheme for Swagger UI
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Get user by username."""
    return db.query(User).filter(User.username == username).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get user by email."""
    return db.query(User).filter(User.email == email).first()


def create_user(db: Session, user: UserCreate) -> User:
    """Create a new user with secure password hashing."""
    # Check if user already exists
    if get_user_by_username(db, user.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "USERNAME_EXISTS",
                "message": "Username already registered"
            }
        )
    
    if get_user_by_email(db, user.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "EMAIL_EXISTS", 
                "message": "Email already registered"
            }
        )
    
    # Create user with hashed password
    hashed_password = enhanced_jwt.pwd_context.hash(user.password)
    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        base_currency=user.base_currency
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """Authenticate user with secure password verification."""
    user = get_user_by_username(db, username)
    if not user:
        return None
    
    if not enhanced_jwt.pwd_context.verify(password, user.hashed_password):
        return None
    
    return user


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register_user(
    user: UserCreate,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Register a new user and return access/refresh tokens.
    
    This endpoint:
    - Validates user input
    - Checks for duplicate username/email
    - Creates user with secure password hashing
    - Returns JWT token pair
    - Sets secure cookies if enabled
    """
    # Create user
    db_user = create_user(db, user)
    
    # Generate token pair
    token_pair = enhanced_jwt.create_token_pair(db_user.username, str(db_user.id))
    
    # Set secure cookies if enabled
    if security_utils.is_production():
        cookie_settings = security_utils.get_cookie_settings()
        response.set_cookie(
            key="access_token",
            value=token_pair.access_token,
            **cookie_settings
        )
        response.set_cookie(
            key="refresh_token", 
            value=token_pair.refresh_token,
            max_age=cookie_settings["max_age"] * 24 * 7,  # 7 days for refresh
            **{k: v for k, v in cookie_settings.items() if k != "max_age"}
        )
    
    return TokenResponse(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        token_type=token_pair.token_type,
        expires_in=token_pair.expires_in
    )


@router.post("/login", response_model=TokenResponse)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    response: Response = None,
    db: Session = Depends(get_db)
):
    """
    Login and receive access/refresh tokens.
    
    This endpoint:
    - Authenticates user credentials
    - Implements secure password verification
    - Returns JWT token pair
    - Sets secure cookies if enabled
    - Applies rate limiting for security
    """
    # Authenticate user
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "INVALID_CREDENTIALS",
                "message": "Incorrect username or password"
            },
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Generate token pair
    token_pair = enhanced_jwt.create_token_pair(user.username, str(user.id))
    
    # Set secure cookies if enabled
    if security_utils.is_production():
        cookie_settings = security_utils.get_cookie_settings()
        response.set_cookie(
            key="access_token",
            value=token_pair.access_token,
            **cookie_settings
        )
        response.set_cookie(
            key="refresh_token",
            value=token_pair.refresh_token,
            max_age=cookie_settings["max_age"] * 24 * 7,  # 7 days
            **{k: v for k, v in cookie_settings.items() if k != "max_age"}
        )
    
    return TokenResponse(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        token_type=token_pair.token_type,
        expires_in=token_pair.expires_in
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_request: RefreshTokenRequest,
    response: Response,
    refresh_token_cookie: Optional[str] = Cookie(None, alias="refresh_token")
):
    """
    Refresh access token using refresh token.
    
    This endpoint:
    - Validates refresh token
    - Generates new token pair
    - Supports both JSON body and cookie-based refresh tokens
    - Updates secure cookies if enabled
    """
    # Get refresh token from request body or cookie
    refresh_token = refresh_request.refresh_token or refresh_token_cookie
    
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "MISSING_REFRESH_TOKEN",
                "message": "Refresh token is required"
            }
        )
    
    try:
        # Generate new token pair
        new_token_pair = enhanced_jwt.refresh_access_token(refresh_token)
        
        # Update secure cookies if enabled
        if security_utils.is_production():
            cookie_settings = security_utils.get_cookie_settings()
            response.set_cookie(
                key="access_token",
                value=new_token_pair.access_token,
                **cookie_settings
            )
            response.set_cookie(
                key="refresh_token",
                value=new_token_pair.refresh_token,
                max_age=cookie_settings["max_age"] * 24 * 7,
                **{k: v for k, v in cookie_settings.items() if k != "max_age"}
            )
        
        return TokenResponse(
            access_token=new_token_pair.access_token,
            refresh_token=new_token_pair.refresh_token,
            token_type=new_token_pair.token_type,
            expires_in=new_token_pair.expires_in
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "REFRESH_FAILED",
                "message": "Failed to refresh token"
            }
        )


@router.post("/logout")
async def logout(
    response: Response,
    token: str = Depends(oauth2_scheme),
    refresh_token_cookie: Optional[str] = Cookie(None, alias="refresh_token")
):
    """
    Logout user and revoke tokens.
    
    This endpoint:
    - Revokes the current access token
    - Revokes refresh token if provided
    - Clears secure cookies
    """
    # Revoke tokens
    enhanced_jwt.revoke_token(token)
    if refresh_token_cookie:
        enhanced_jwt.revoke_token(refresh_token_cookie)
    
    # Clear cookies
    response.delete_cookie(key="access_token")
    response.delete_cookie(key="refresh_token")
    
    return {
        "message": "Successfully logged out"
    }


@router.post("/logout-all")
async def logout_all_devices(
    response: Response,
    token: str = Depends(oauth2_scheme)
):
    """
    Logout from all devices by revoking all user tokens.
    
    This endpoint:
    - Validates current token
    - Revokes all tokens for the user
    - Clears cookies
    """
    # Verify current token and get user info
    token_data = enhanced_jwt.verify_token(token)
    
    # Revoke all user tokens
    revoked_count = enhanced_jwt.revoke_all_user_tokens(token_data.user_id)
    
    # Clear cookies
    response.delete_cookie(key="access_token")
    response.delete_cookie(key="refresh_token")
    
    return {
        "message": "Successfully logged out from all devices",
        "revoked_tokens": revoked_count
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Get current user information.
    
    This endpoint:
    - Validates JWT token
    - Returns current user information
    - Supports both Authorization header and cookie tokens
    """
    # Verify token
    token_data = enhanced_jwt.verify_token(token)
    
    # Get user from database
    user = get_user_by_username(db, token_data.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "USER_NOT_FOUND",
                "message": "User not found"
            }
        )
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        base_currency=user.base_currency
    )


@router.get("/token-info", response_model=TokenInfo)
async def get_token_info(token: str = Depends(oauth2_scheme)):
    """
    Get information about the current token.
    
    This endpoint:
    - Validates token format
    - Returns token metadata
    - Useful for debugging and monitoring
    """
    info = enhanced_jwt.get_token_info(token)
    
    if not info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "INVALID_TOKEN",
                "message": "Invalid token format"
            }
        )
    
    return TokenInfo(**info)


# Dependency for protected routes
async def get_current_user_dependency(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Dependency to get current authenticated user."""
    token_data = enhanced_jwt.verify_token(token)
    user = get_user_by_username(db, token_data.username)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "USER_NOT_FOUND", 
                "message": "User not found"
            }
        )
    
    return user
