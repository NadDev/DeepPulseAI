"""
Auth module initialization
Imports from local_auth (JWT + bcrypt-based authentication)
"""
from app.auth.local_auth import (
    get_current_user,
    register_user,
    login_user,
    refresh_token,
    reset_password,
    UserRegister,
    UserLogin,
    UserResponse,
    AuthResponse,
    TokenRefresh,
    PasswordReset
)

__all__ = [
    "get_current_user",
    "register_user",
    "login_user",
    "refresh_token",
    "reset_password",
    "UserRegister",
    "UserLogin",
    "UserResponse",
    "AuthResponse",
    "TokenRefresh",
    "PasswordReset"
]
