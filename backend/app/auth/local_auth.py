"""
Local Authentication Module - JWT & Password-based Auth
=======================================================
Replaces Supabase Auth with local bcrypt password hashing and JWT token generation
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
import bcrypt
import logging
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.database_models import User
from app.config import settings

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


class PasswordReset(BaseModel):
    email: EmailStr
    new_password: str


class UserResponse(BaseModel):
    id: str
    email: str
    username: Optional[str] = None
    created_at: Optional[str] = None
    
    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    user: UserResponse
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    refresh_token: str


# ============== Password Hashing ==============

class PasswordHasher:
    """Handles password hashing with bcrypt"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt"""
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """Verify a password against its hash"""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False


# ============== JWT Token Management ==============

class TokenManager:
    """Handles JWT token generation and verification"""
    
    @staticmethod
    def create_access_token(user_id: str, email: str) -> str:
        """Create JWT access token"""
        to_encode = {
            "sub": str(user_id),
            "email": email,
            "type": "access"
        }
        expire = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRATION_HOURS)
        to_encode.update({"exp": expire})
        
        encoded_jwt = jwt.encode(
            to_encode,
            settings.SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(user_id: str) -> str:
        """Create JWT refresh token"""
        to_encode = {
            "sub": str(user_id),
            "type": "refresh"
        }
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRATION_DAYS)
        to_encode.update({"exp": expire})
        
        encoded_jwt = jwt.encode(
            to_encode,
            settings.SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> dict:
        """Verify JWT token and return payload"""
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            return payload
        except JWTError as e:
            logger.error(f"Token verification error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )


# ============== Auth Functions ==============

async def register_user(data: UserRegister, db: Session) -> AuthResponse:
    """Register a new user with email and password"""
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(
            (User.email == data.email) | (User.username == (data.username or data.email.split('@')[0]))
        ).first()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email or username already exists"
            )
        
        # Hash password
        password_hash = PasswordHasher.hash_password(data.password)
        
        # Create user
        username = data.username or data.email.split('@')[0]
        user = User(
            email=data.email,
            username=username,
            password_hash=password_hash
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        logger.info(f"✅ [AUTH] User registered: {user.email} (id={user.id})")
        
        # Generate tokens
        access_token = TokenManager.create_access_token(str(user.id), user.email)
        refresh_token = TokenManager.create_refresh_token(str(user.id))
        
        return AuthResponse(
            user=UserResponse(
                id=str(user.id),
                email=user.email,
                username=user.username,
                created_at=user.created_at.isoformat() if user.created_at else None
            ),
            access_token=access_token,
            refresh_token=refresh_token
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ [AUTH] Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


async def login_user(data: UserLogin, db: Session) -> AuthResponse:
    """Login user with email and password"""
    try:
        # Find user by email
        user = db.query(User).filter(User.email == data.email).first()
        
        if not user:
            logger.warning(f"⚠️ [AUTH] Failed login attempt for email: {data.email} - user not found")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Check if user has a password_hash (new users have it, existing users might not)
        if not user.password_hash:
            logger.warning(f"⚠️ [AUTH] Login attempt for user without password_hash: {data.email}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Password not set. Please use 'Forgot password' to create a new password."
            )
        
        # Verify password
        if not PasswordHasher.verify_password(data.password, user.password_hash):
            logger.warning(f"⚠️ [AUTH] Failed login attempt for email: {data.email} - invalid password")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        logger.info(f"✅ [AUTH] User logged in: {user.email} (id={user.id})")
        
        # Generate tokens
        access_token = TokenManager.create_access_token(str(user.id), user.email)
        refresh_token = TokenManager.create_refresh_token(str(user.id))
        
        return AuthResponse(
            user=UserResponse(
                id=str(user.id),
                email=user.email,
                username=user.username,
                created_at=user.created_at.isoformat() if user.created_at else None
            ),
            access_token=access_token,
            refresh_token=refresh_token
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [AUTH] Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login failed"
        )


async def refresh_token(data: TokenRefresh, db: Session) -> AuthResponse:
    """Refresh access token using refresh token"""
    try:
        payload = TokenManager.verify_token(data.refresh_token)
        
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        user_id = payload.get("sub")
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        logger.info(f"✅ [AUTH] Token refreshed for user: {user.email}")
        
        # Create new access token
        access_token = TokenManager.create_access_token(str(user.id), user.email)
        
        return AuthResponse(
            user=UserResponse(
                id=str(user.id),
                email=user.email,
                username=user.username,
                created_at=user.created_at.isoformat() if user.created_at else None
            ),
            access_token=access_token,
            refresh_token=data.refresh_token  # Keep the same refresh token
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [AUTH] Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token refresh failed"
        )


async def reset_password(data: PasswordReset, db: Session) -> dict:
    """Reset password for users without one or forgot password"""
    try:
        # Find user by email
        user = db.query(User).filter(User.email == data.email).first()
        
        if not user:
            logger.warning(f"⚠️ [AUTH] Password reset attempted for non-existent user: {data.email}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Hash and update password
        password_hash = PasswordHasher.hash_password(data.new_password)
        user.password_hash = password_hash
        db.commit()
        
        logger.info(f"✅ [AUTH] Password reset for user: {user.email}")
        
        return {
            "success": True,
            "message": "Password has been set successfully. You can now log in.",
            "user_id": str(user.id),
            "email": user.email
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [AUTH] Password reset error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset password"
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> UserResponse:
    """
    Dependency to extract and verify current user from JWT token
    Used in route handlers: @app.get("/protected", dependencies=[Depends(get_current_user)])
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization credentials"
        )
    
    token = credentials.credentials
    
    try:
        payload = TokenManager.verify_token(token)
        user_id = payload.get("sub")
        email = payload.get("email")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Fetch user from database
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        return UserResponse(
            id=str(user.id),
            email=user.email,
            username=user.username,
            created_at=user.created_at.isoformat() if user.created_at else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [AUTH] get_current_user error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )
