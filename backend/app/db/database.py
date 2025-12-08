from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

# Create database engine
# For SQLite, disable some features that PostgreSQL has
kwargs = {
    "echo": settings.DEBUG,
    "pool_pre_ping": True,
}

# PostgreSQL-specific settings
if "postgresql" in settings.DATABASE_URL:
    kwargs.update({
        "pool_size": 10,
        "max_overflow": 20,
    })

# SQLite-specific settings
if "sqlite" in settings.DATABASE_URL:
    kwargs.update({
        "connect_args": {"check_same_thread": False}
    })

engine = create_engine(settings.DATABASE_URL, **kwargs)

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
