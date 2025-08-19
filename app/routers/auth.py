from datetime import datetime, timedelta
from typing import Dict, Optional

import bcrypt
from fastapi import APIRouter, HTTPException, status, Depends
from jose import jwt
from sqlalchemy.orm import Session

from app.core.security import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from app.dependencies.db import get_db
from app.models.user import User
from app.dependencies.jwt_auth import get_current_user
from app.schemas.auth import UserCredentials, Token, UserResponse, UserRegister
from app.schemas.common import ErrorResponse

router = APIRouter()


def _hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against the stored bcrypt hash."""
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def _create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


@router.post(
    "/register", 
    response_model=Token, 
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user account with username, email, and password. Returns a JWT token for authentication.",
    responses={
        201: {"description": "User registered successfully"},
        400: {"model": ErrorResponse, "description": "Username already exists or validation error"},
        422: {"description": "Validation error in request body"}
    }
)
async def register(
    credentials: UserRegister, 
    db: Session = Depends(get_db)
):
    """Register a new user account."""
    # Check if username already exists
    existing_user = db.query(User).filter(User.username == credentials.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "USERNAME_EXISTS", "message": "Username already registered"}
        )
    
    # Check if email already exists (if email field exists in User model)
    if hasattr(User, 'email'):
        existing_email = db.query(User).filter(User.email == credentials.email).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "EMAIL_EXISTS", "message": "Email already registered"}
            )
    
    # Create new user
    new_user = User(
        username=credentials.username, 
        hashed_password=_hash_password(credentials.password)
    )
    
    # Add email if the model supports it
    if hasattr(new_user, 'email'):
        new_user.email = credentials.email
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Generate token
    token = _create_access_token({"sub": new_user.username})
    return {"access_token": token, "token_type": "bearer"}


@router.post(
    "/login", 
    response_model=Token, 
    summary="Login and get a JWT token",
    description="Authenticate user with username and password. Returns a JWT token for accessing protected endpoints.",
    responses={
        200: {"description": "Login successful"},
        401: {"model": ErrorResponse, "description": "Invalid credentials"},
        422: {"description": "Validation error in request body"}
    }
)
async def login(
    credentials: UserCredentials, 
    db: Session = Depends(get_db)
):
    """Login with username and password."""
    user = db.query(User).filter(User.username == credentials.username).first()
    if not user or not _verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_CREDENTIALS", "message": "Incorrect username or password"}
        )
    
    token = _create_access_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}


@router.get(
    "/me", 
    response_model=UserResponse,
    summary="Get current user information",
    description="Return current user's information if JWT token is valid.",
    responses={
        200: {"description": "User information retrieved successfully"},
        401: {"model": ErrorResponse, "description": "Invalid or missing authentication token"}
    }
)
async def get_me(current_user: str = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return current user's information."""
    user = db.query(User).filter(User.username == current_user).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "USER_NOT_FOUND", "message": "User not found"}
        )
    
    return {
        "username": user.username,
        "email": user.email or ""  # Return empty string if email is None
    } 