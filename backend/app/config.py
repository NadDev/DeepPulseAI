import os
from dotenv import load_dotenv
from typing import List

load_dotenv()

class Settings:
    # ========== ENVIRONMENT ==========
    ENV = os.getenv("ENV", "development")
    DEBUG = ENV == "development"
    
    # ========== SECURITY ==========
    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "dev-insecure-key-change-in-production"
    )
    
    # API Key encryption (for broker credentials)
    API_KEY_ENCRYPTION_KEY = os.getenv(
        "API_KEY_ENCRYPTION_KEY",
        "dev-encryption-key"
    )
    
    # JWT Configuration
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))
    REFRESH_TOKEN_EXPIRATION_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRATION_DAYS", "30"))
    
    # ========== DATABASE ==========
    # Use Supabase PostgreSQL for both dev and prod
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:admin@localhost:5432/crbot"  # Local fallback for offline dev
    )
    
    # ========== REDIS (Caching) ==========
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_ENABLED = ENV != "development"
    
    # ========== API CONFIGURATION ==========
    API_TITLE = "CRBot API"
    API_VERSION = "1.0.0"
    API_DESCRIPTION = "Crypto Trading Bot Platform"
    
    # ========== CORS ==========
    ALLOWED_ORIGINS: List[str] = []
    if ENV == "development":
        ALLOWED_ORIGINS = [
            "http://localhost:3000",
            "http://localhost:3001",
            "http://localhost:5173",
            "http://localhost:8002",
            "http://localhost:8003",
            "http://localhost:8080",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3001",
            "http://127.0.0.1:8002",
            "http://127.0.0.1:8003",
            "http://127.0.0.1:8080",
            "http://127.0.0.1:8000",
        ]
    elif ENV == "staging":
        ALLOWED_ORIGINS = [
            "https://staging.yourapp.com",
        ]
    else:  # production
        ALLOWED_ORIGINS = [
            "https://deep-pulse-ai.vercel.app",  # Production domain (stable)
        ]
    
    # ========== RATE LIMITING ==========
    RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
    RATE_LIMIT_PERIOD_SECONDS = int(os.getenv("RATE_LIMIT_PERIOD_SECONDS", "60"))
    
    # ========== BROKER CREDENTIALS (ENCRYPTED) ==========
    BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
    BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", "")
    BINANCE_TESTNET = os.getenv("BINANCE_TESTNET", "true").lower() == "true"
    
    # MetaTrader (optional)
    METATRADER_LOGIN = os.getenv("METATRADER_LOGIN", "")
    METATRADER_PASSWORD = os.getenv("METATRADER_PASSWORD", "")
    METATRADER_SERVER = os.getenv("METATRADER_SERVER", "")
    
    # ========== LOGGING ==========
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO" if ENV != "development" else "DEBUG")
    
    # ========== EXTERNAL SERVICES ==========
    # LLM (FEATURE 5.1)
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    
    # ========== RISK MANAGEMENT ==========
    MAX_DAILY_LOSS_PERCENT = float(os.getenv("MAX_DAILY_LOSS_PERCENT", "5.0"))
    MAX_DRAWDOWN_PERCENT = float(os.getenv("MAX_DRAWDOWN_PERCENT", "10.0"))
    MAX_TRADES_PER_DAY = int(os.getenv("MAX_TRADES_PER_DAY", "10"))
    MAX_POSITION_SIZE_PERCENT = float(os.getenv("MAX_POSITION_SIZE_PERCENT", "5.0"))
    
    # ========== FEATURE FLAGS ==========
    FEATURE_ML_PREDICTIONS = os.getenv("FEATURE_ML_PREDICTIONS", "true").lower() == "true"
    FEATURE_REAL_TRADING = os.getenv("FEATURE_REAL_TRADING", "false").lower() == "true"
    FEATURE_PAPER_TRADING = os.getenv("FEATURE_PAPER_TRADING", "true").lower() == "true"
    FEATURE_WEBHOOK_ALERTS = os.getenv("FEATURE_WEBHOOK_ALERTS", "false").lower() == "true"
    
    # ========== NOTIFICATIONS ==========
    # Email
    EMAIL_ENABLED = os.getenv("EMAIL_ENABLED", "false").lower() == "true"
    EMAIL_FROM = os.getenv("EMAIL_FROM", "noreply@crbot.com")
    EMAIL_SMTP_HOST = os.getenv("EMAIL_SMTP_HOST", "smtp.gmail.com")
    EMAIL_SMTP_PORT = int(os.getenv("EMAIL_SMTP_PORT", "587"))
    EMAIL_SMTP_USER = os.getenv("EMAIL_SMTP_USER", "")
    EMAIL_SMTP_PASSWORD = os.getenv("EMAIL_SMTP_PASSWORD", "")
    
    # Discord
    DISCORD_WEBHOOK_ALERTS = os.getenv("DISCORD_WEBHOOK_ALERTS", "")
    DISCORD_WEBHOOK_ERRORS = os.getenv("DISCORD_WEBHOOK_ERRORS", "")
    
    # ========== BACKUP ==========
    BACKUP_ENABLED = os.getenv("BACKUP_ENABLED", "true").lower() == "true"
    BACKUP_SCHEDULE_HOURS = int(os.getenv("BACKUP_SCHEDULE_HOURS", "24"))
    BACKUP_RETENTION_DAYS = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))
    
    # ========== VALIDATION ==========
    @property
    def is_production(self) -> bool:
        return self.ENV == "production"
    
    @property
    def is_secure(self) -> bool:
        """Check if security requirements are met for production"""
        if not self.is_production:
            return True
        
        checks = [
            self.SECRET_KEY != "dev-insecure-key-change-in-production",
            self.API_KEY_ENCRYPTION_KEY != "dev-encryption-key",
            not self.DEBUG,
            self.BINANCE_API_KEY and self.BINANCE_API_SECRET,
        ]
        return all(checks)

settings = Settings()
