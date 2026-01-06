from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import asyncio

# Import routes
from app.routes import health, portfolio, crypto, bots, reports, risk, trades, translations, ml, auth
from app.config import settings
from app.db.database import Base, engine, SessionLocal
from app.services.bot_engine import BotEngine, bot_engine

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global bot engine
_bot_engine: BotEngine = None

# Note: Tables are already created via supabase_schema.sql in production
# Don't create tables on startup - they should exist in Supabase

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _bot_engine
    
    # Startup
    logger.info("🚀 CRBot API Starting...")
    # Tables should already exist in Supabase PostgreSQL
    logger.info("[OK] Database connection ready")
    
    # Start Bot Engine
    try:
        _bot_engine = BotEngine(SessionLocal)
        await _bot_engine.start()
        logger.info("[OK] Bot Engine started")
    except Exception as e:
        logger.error(f"[ERROR] Failed to start Bot Engine: {e}")
    
    yield
    
    # Shutdown
    logger.info("🛑 CRBot API Shutting down...")
    if _bot_engine:
        await _bot_engine.stop()
        logger.info("[OK] Bot Engine stopped")

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

@app.get("/api/engine/status")
async def get_engine_status():
    """Get the current status of the Bot Engine"""
    if not _bot_engine:
        return {
            "status": "not_initialized",
            "running": False,
            "active_bots": 0,
            "message": "Bot Engine not initialized"
        }
    
    active_bots_info = []
    for bot_id, bot_state in _bot_engine.active_bots.items():
        active_bots_info.append({
            "bot_id": bot_id,
            "name": bot_state.get("name"),
            "symbols": bot_state.get("symbols"),
            "last_check": bot_state.get("last_check").isoformat() if bot_state.get("last_check") else None
        })
    
    return {
        "status": "running" if _bot_engine._running else "stopped",
        "running": _bot_engine._running,
        "active_bots": len(_bot_engine.active_bots),
        "active_bots_details": active_bots_info,
        "message": "Bot Engine is operational"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
