from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool
from app.config import settings
import socket

# ============================================
# DATABASE ARCHITECTURE
# ============================================
# Railway PostgreSQL: ALL business data (bots, trades, portfolios, crypto_market_data, recommendations, etc.)
# Supabase: Auth ONLY (JWT validation happens in frontend → backend, no direct DB connection needed)
#
# Why Railway for business data?
# - Unlimited storage (Supabase Free = 0.5 GB limit)
# - Better for 200 cryptos × 730 days × 3 timeframes = 44 MB historical data
# - Simpler architecture: one database for all business logic
# ============================================

# Create database engine
# For SQLite, disable some features that PostgreSQL has
kwargs = {
    "echo": settings.DEBUG,
    "pool_pre_ping": True,
}

# PostgreSQL-specific settings
if "postgresql" in settings.DATABASE_URL:
    kwargs.update({
        "pool_size": 5,
        "max_overflow": 10,
        "poolclass": QueuePool,
        "connect_args": {
            "connect_timeout": 10,
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 5,
            "tcp_user_timeout": 30000,  # 30 seconds in milliseconds
        }
    })

# SQLite-specific settings
if "sqlite" in settings.DATABASE_URL:
    kwargs.update({
        "connect_args": {"check_same_thread": False}
    })

engine = create_engine(settings.DATABASE_URL, **kwargs)

# Event listener for handling IPv6 connection issues with Supabase
@event.listens_for(engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    """
    Handle IPv6 connections to Supabase.
    Sets optimal TCP parameters for long-lived connections.
    """
    if hasattr(dbapi_conn, 'set_session'):
        # Set connection to autocommit mode for better performance
        try:
            dbapi_conn.autocommit = True
        except:
            pass

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create declarative base for models
Base = declarative_base()

# Dependency for FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
