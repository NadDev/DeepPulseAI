from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

# Import routes
from app.routes import health, portfolio, crypto, bots, reports, risk, trades, translations, ml, auth
from app.config import settings
from app.db.database import Base, engine

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create tables on startup
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 CRBot API Starting...")
    Base.metadata.create_all(bind=engine)
    logger.info("[OK] Database tables created")
    yield
    # Shutdown
    logger.info("🛑 CRBot API Shutting down...")

# Create FastAPI app
app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version=settings.API_VERSION,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)  # Auth routes first
app.include_router(health.router)
app.include_router(portfolio.router)
app.include_router(crypto.router)
app.include_router(bots.router)
app.include_router(reports.router)
app.include_router(risk.router)
app.include_router(trades.router)
app.include_router(translations.router)
app.include_router(ml.router)

@app.get("/")
async def root():
    return {
        "message": "Welcome to CRBot API",
        "docs": "/docs",
        "version": settings.API_VERSION
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
