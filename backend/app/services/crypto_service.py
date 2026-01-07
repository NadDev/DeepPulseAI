"""
Crypto Service for API Key Encryption
Uses Fernet symmetric encryption to securely store API keys
"""
import os
import base64
import logging
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Optional

logger = logging.getLogger(__name__)


class CryptoService:
    """
    Handles encryption and decryption of sensitive data like API keys.
    Uses Fernet (AES-128-CBC) with a key derived from ENCRYPTION_KEY env var.
    """
    
    def __init__(self):
        self._fernet: Optional[Fernet] = None
        self._initialized = False
        self._init_encryption()
    
    def _init_encryption(self):
        """Initialize the Fernet encryption with environment key"""
        try:
            # Get encryption key from environment
            encryption_key = os.getenv("ENCRYPTION_KEY")
            
            if not encryption_key:
                # Generate a key for development (NOT for production!)
                logger.warning("⚠️ ENCRYPTION_KEY not set! Using development key - NOT SECURE FOR PRODUCTION!")
                encryption_key = "dev-encryption-key-change-in-production"
            
            # Derive a proper Fernet key from the password using PBKDF2
            salt = b'crbot_salt_v1'  # Static salt - in production, could be per-user
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(encryption_key.encode()))
            
            self._fernet = Fernet(key)
            self._initialized = True
            logger.info("🔐 Crypto service initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize crypto service: {e}")
            self._initialized = False
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a string and return base64-encoded ciphertext.
        
        Args:
            plaintext: The string to encrypt (e.g., API key)
            
        Returns:
            Base64-encoded encrypted string
        """
        if not self._initialized or not self._fernet:
            raise RuntimeError("Crypto service not initialized")
        
        if not plaintext:
            raise ValueError("Cannot encrypt empty string")
        
        try:
            encrypted = self._fernet.encrypt(plaintext.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise
    
    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt a base64-encoded ciphertext and return plaintext.
        
        Args:
            ciphertext: Base64-encoded encrypted string
            
        Returns:
            Decrypted plaintext string
        """
        if not self._initialized or not self._fernet:
            raise RuntimeError("Crypto service not initialized")
        
        if not ciphertext:
            raise ValueError("Cannot decrypt empty string")
        
        try:
            decrypted = self._fernet.decrypt(ciphertext.encode())
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise
    
    def is_initialized(self) -> bool:
        """Check if crypto service is properly initialized"""
        return self._initialized
    
    def mask_key(self, key: str, visible_chars: int = 4) -> str:
        """
        Mask an API key for display purposes.
        Shows first and last N characters, masks the rest.
        
        Args:
            key: The key to mask
            visible_chars: Number of characters to show at start/end
            
        Returns:
            Masked string like "sk-ab...xy"
        """
        if not key or len(key) < visible_chars * 2 + 3:
            return "***"
        
        return f"{key[:visible_chars]}...{key[-visible_chars:]}"


# Singleton instance
crypto_service = CryptoService()


def get_crypto_service() -> CryptoService:
    """Get the crypto service singleton"""
    return crypto_service
