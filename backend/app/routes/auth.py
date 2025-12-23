"""
Authentication Routes
Handles user registration, login, logout, and token refresh
"""
from fastapi import APIRouter, Depends, HTTPException, status
from app.auth import (
    register_user,
    login_user,
    logout_user,
    refresh_token,
    get_current_user,
    UserRegister,
    UserLogin,
    UserResponse,
    AuthResponse,
    TokenRefresh
)

router = APIRouter(prefix="/api/auth", tags=["authentication"])


@router.post("/register", response_model=AuthResponse)
async def register(data: UserRegister):
    """
    Register a new user account.
    
    - **email**: Valid email address
    - **password**: Password (min 6 characters)
    - **username**: Optional display name
    """
    return await register_user(data)


@router.post("/login", response_model=AuthResponse)
async def login(data: UserLogin):
    """
    Login with email and password.
    
    Returns access token and refresh token.
    """
    return await login_user(data)


@router.post("/logout")
async def logout(current_user: UserResponse = Depends(get_current_user)):
    """
    Logout current user and invalidate session.
    """
    success = await logout_user("")
    return {"message": "Logged out successfully", "success": success}


@router.post("/refresh", response_model=AuthResponse)
async def refresh(data: TokenRefresh):
    """
    Refresh access token using refresh token.
    """
    return await refresh_token(data)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: UserResponse = Depends(get_current_user)):
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
