import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Database
    ENV = os.getenv("ENV", "development")
    
    # Use SQLite for local development, PostgreSQL for production
    if ENV == "development":
        DATABASE_URL = os.getenv(
            "DATABASE_URL",
            "sqlite:///./crbot.db"
        )
    else:
        DATABASE_URL = os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:postgres_dev_password@localhost:5432/crbot"
        )
    
    # Redis
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # Environment
    ENV = os.getenv("ENV", "development")
    DEBUG = ENV == "development"
    
    # API
    API_TITLE = "CRBot API"
    API_VERSION = "1.0.0"
    API_DESCRIPTION = "Crypto Trading Bot Platform"
    
    # CORS - Allow all origins for development
    ALLOWED_ORIGINS = [
        "*",  # Allow all origins in development
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:8002",
    ]

settings = Settings()
