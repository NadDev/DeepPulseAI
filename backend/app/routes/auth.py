"""
Authentication Routes
Handles user registration, login, logout, and token refresh
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.auth import (
    register_user,
    login_user,
    refresh_token,
    reset_password,
    get_current_user,
    UserRegister,
    UserLogin,
    UserResponse,
    AuthResponse,
    PasswordReset,
    TokenRefresh
)
from app.db.database import get_db

router = APIRouter(prefix="/api/auth", tags=["authentication"])


@router.post("/register", response_model=AuthResponse)
async def register(
    data: UserRegister,
    db: Session = Depends(get_db)
):
    """
    Register a new user account.
    
    - **email**: Valid email address
    - **password**: Password (min 6 characters)
    - **username**: Optional display name
    """
    return await register_user(data, db)


@router.post("/login", response_model=AuthResponse)
async def login(
    data: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Login with email and password.

    Returns access token and refresh token.
    """
    return await login_user(data, db)


@router.post("/logout")
async def logout(current_user: UserResponse = Depends(get_current_user)):
    """
    Logout current user and invalidate session.
    Note: Token-based logout - just clear token on client side
    """
    return {"message": "Logged out successfully", "success": True}


@router.post("/refresh", response_model=AuthResponse)
async def refresh(
    data: TokenRefresh,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token.
    """
    return await refresh_token(data, db)


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user: UserResponse = Depends(get_current_user)):
    """
    Get current authenticated user profile.
    """
    return current_user


@router.get("/verify")
async def verify_token(current_user: UserResponse = Depends(get_current_user)):
    """
    Verify if current token is valid.
    """
    return {
        "valid": True,
        "user_id": current_user.id,
        "email": current_user.email
    }


@router.post("/password-reset")
async def password_reset(
    data: PasswordReset,
    db: Session = Depends(get_db)
):
    """
    Reset password for users without one (existing users) or forgot password.
    
    - **email**: User email address
    - **new_password**: New password (min 6 characters)
    """
    return await reset_password(data, db)
