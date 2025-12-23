"""
Authentication module for Supabase Auth
Handles user authentication, registration, and session management
"""
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional
import logging

from app.db.supabase_client import get_supabase, get_supabase_admin

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer(auto_error=False)


# ============== Pydantic Models ==============

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    username: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    username: Optional[str] = None
    email_confirmed: bool = False
    created_at: Optional[str] = None


class AuthResponse(BaseModel):
    user: UserResponse
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    refresh_token: str


# ============== Auth Functions ==============

async def register_user(data: UserRegister) -> AuthResponse:
    """Register a new user with Supabase Auth"""
    try:
        supabase = get_supabase()
        
        # Register with Supabase Auth
        response = supabase.auth.sign_up({
            "email": data.email,
            "password": data.password,
            "options": {
                "data": {
                    "username": data.username
                }
            }
        })
        
        if response.user is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration failed"
            )
        
        user = response.user
        session = response.session
        
        return AuthResponse(
            user=UserResponse(
                id=user.id,
                email=user.email,
                username=user.user_metadata.get("username"),
                email_confirmed=user.email_confirmed_at is not None,
                created_at=str(user.created_at) if user.created_at else None
            ),
            access_token=session.access_token if session else "",
            refresh_token=session.refresh_token if session else ""
        )
        
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


async def login_user(data: UserLogin) -> AuthResponse:
    """Login user with email and password"""
    try:
        supabase = get_supabase()
        
        response = supabase.auth.sign_in_with_password({
            "email": data.email,
            "password": data.password
        })
        
        if response.user is None or response.session is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        user = response.user
        session = response.session
        
        return AuthResponse(
            user=UserResponse(
                id=user.id,
                email=user.email,
                username=user.user_metadata.get("username"),
                email_confirmed=user.email_confirmed_at is not None,
                created_at=str(user.created_at) if user.created_at else None
            ),
            access_token=session.access_token,
            refresh_token=session.refresh_token
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )


async def refresh_token(data: TokenRefresh) -> AuthResponse:
    """Refresh access token using refresh token"""
    try:
        supabase = get_supabase()
        
        response = supabase.auth.refresh_session(data.refresh_token)
        
        if response.user is None or response.session is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        user = response.user
        session = response.session
        
        return AuthResponse(
            user=UserResponse(
                id=user.id,
                email=user.email,
                username=user.user_metadata.get("username"),
                email_confirmed=user.email_confirmed_at is not None,
                created_at=str(user.created_at) if user.created_at else None
            ),
            access_token=session.access_token,
            refresh_token=session.refresh_token
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token refresh failed"
        )


async def logout_user(access_token: str) -> bool:
    """Logout user and invalidate session"""
    try:
        supabase = get_supabase()
        supabase.auth.sign_out()
        return True
    except Exception as e:
        logger.error(f"Logout error: {e}")
        return False


# ============== Dependency for Protected Routes ==============

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UserResponse:
    """
    Dependency to get current authenticated user from JWT token.
    Use this in protected routes.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    try:
        supabase = get_supabase()
        
        # Verify token with Supabase
        response = supabase.auth.get_user(credentials.credentials)
        
        if response.user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        user = response.user
        
        return UserResponse(
            id=user.id,
            email=user.email,
            username=user.user_metadata.get("username"),
            email_confirmed=user.email_confirmed_at is not None,
            created_at=str(user.created_at) if user.created_at else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Optional[UserResponse]:
    """
    Dependency to optionally get current user.
    Returns None if not authenticated (doesn't raise exception).
    """
    if credentials is None:
        return None
    
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None
