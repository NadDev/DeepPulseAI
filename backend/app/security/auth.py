"""
==============================================
AUTH MODULE - JWT & Rate Limiting
==============================================
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import HTTPException, status
from app.config import settings
import secrets


class TokenManager:
    """Gère la génération et validation des JWT"""
    
    @staticmethod
    def create_access_token(data: dict) -> str:
        """Crée un JWT token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRATION_HOURS)
        to_encode.update({"exp": expire})
        
        encoded_jwt = jwt.encode(
            to_encode,
            settings.SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> dict:
        """Valide un JWT token"""
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            return payload
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    
    @staticmethod
    def create_refresh_token(data: dict) -> str:
        """Crée un refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRATION_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        
        encoded_jwt = jwt.encode(
            to_encode,
            settings.SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        return encoded_jwt


class ApiKeyManager:
    """Gère les API keys d'authentification"""
    
    @staticmethod
    def generate_api_key() -> str:
        """Génère une nouvelle API key pour un utilisateur"""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """Hash l'API key avant stockage (one-way)"""
        import hashlib
        return hashlib.sha256(api_key.encode()).hexdigest()


class RateLimiter:
    """Rate limiting in-memory simple"""
    
    def __init__(self):
        self.requests = {}  # {ip: [(timestamp, count)]}
    
    def is_allowed(self, client_id: str) -> bool:
        """Vérifie si le client peut faire une requête"""
        if not settings.RATE_LIMIT_ENABLED:
            return True
        
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=settings.RATE_LIMIT_PERIOD_SECONDS)
        
        if client_id not in self.requests:
            self.requests[client_id] = []
        
        # Nettoie les anciennes requêtes
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if req_time > window_start
        ]
        
        # Vérifie la limite
        if len(self.requests[client_id]) >= settings.RATE_LIMIT_REQUESTS:
            return False
        
        # Ajoute la requête actuelle
        self.requests[client_id].append(now)
        return True


# Instances globales
token_manager = TokenManager()
api_key_manager = ApiKeyManager()
rate_limiter = RateLimiter()
