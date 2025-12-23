"""
==============================================
ENCRYPTION MODULE - Secure API Keys Storage
==============================================

Chiffre les credentials du broker avant stockage
Utilise Fernet (AES-128)
"""

from cryptography.fernet import Fernet
from app.config import settings
import base64
import hashlib


class KeyManager:
    """Gère le chiffrement/déchiffrement des API keys"""
    
    def __init__(self):
        # Génère une clé de 32 bytes à partir de la clé config
        key_material = hashlib.pbkdf2_hmac(
            'sha256',
            settings.API_KEY_ENCRYPTION_KEY.encode(),
            b'crbot_salt',
            100000
        )
        # Encode en base64 pour Fernet
        self.cipher_key = base64.urlsafe_b64encode(key_material[:32])
        self.cipher = Fernet(self.cipher_key)
    
    def encrypt(self, plaintext: str) -> str:
        """Chiffre une clé API"""
        if not plaintext:
            return ""
        encrypted = self.cipher.encrypt(plaintext.encode())
        return encrypted.decode()
    
    def decrypt(self, encrypted: str) -> str:
        """Déchiffre une clé API"""
        if not encrypted:
            return ""
        try:
            decrypted = self.cipher.decrypt(encrypted.encode())
            return decrypted.decode()
        except Exception as e:
            raise ValueError(f"Decryption failed: {str(e)}")


class BrokerCredentials:
    """Stocke les credentials chiffrées"""
    
    def __init__(self, broker_type: str, api_key: str, api_secret: str):
        self.broker_type = broker_type
        self.key_manager = KeyManager()
        self.encrypted_api_key = self.key_manager.encrypt(api_key)
        self.encrypted_api_secret = self.key_manager.encrypt(api_secret)
    
    def get_api_key(self) -> str:
        """Retourne la clé API déchiffrée"""
        return self.key_manager.decrypt(self.encrypted_api_key)
    
    def get_api_secret(self) -> str:
        """Retourne le secret API déchiffré"""
        return self.key_manager.decrypt(self.encrypted_api_secret)
    
    def to_dict(self):
        """Retourne le dictionnaire (chiffré - sûr pour stockage)"""
        return {
            "broker_type": self.broker_type,
            "encrypted_api_key": self.encrypted_api_key,
            "encrypted_api_secret": self.encrypted_api_secret,
        }


# Instance globale
key_manager = KeyManager()
