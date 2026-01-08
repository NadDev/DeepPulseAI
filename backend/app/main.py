from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import asyncio
import os

# Import routes
from app.routes import health, portfolio, crypto, bots, reports, risk, trades, translations, ml, auth, ai_agent, exchange, watchlist
from app.config import settings
from app.db.database import Base, engine, SessionLocal
from app.services import bot_engine as bot_engine_module
from app.services.bot_engine import BotEngine
from app.services import ai_agent as ai_agent_module
from app.services.ai_agent import initialize_ai_agent
from app.services import ai_bot_controller as ai_bot_controller_module
from app.services.ai_bot_controller import initialize_ai_bot_controller

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Note: Tables are already created via supabase_schema.sql in production
# Don't create tables on startup - they should exist in Supabase

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 CRBot API Starting...")
    
    # Create missing tables (idempotent)
    try:
        from sqlalchemy import text
        import pathlib
        db = SessionLocal()
        
        # Check if ai_decisions table exists, if not create it
        try:
            db.execute(text("SELECT 1 FROM ai_decisions LIMIT 1"))
            logger.info("[OK] ai_decisions table exists")
        except Exception as check_error:
            try:
                logger.info(f"⚙️ Creating ai_decisions table... (error was: {check_error})")
                
                # Use Railway-compatible migration (without Supabase auth.users reference)
                migration_paths = [
                    "/app/database/migrations/001_create_ai_decisions_table_railway.sql",  # Railway Docker path
                    "database/migrations/001_create_ai_decisions_table_railway.sql",
                    pathlib.Path(__file__).parent.parent.parent / "database/migrations/001_create_ai_decisions_table_railway.sql"
                ]
                
                migration_sql = None
                found_path = None
                for path in migration_paths:
                    try:
                        migration_sql = open(path).read()
                        found_path = str(path)
                        logger.info(f"✅ Found migration file at: {found_path}")
                        break
                    except Exception as path_error:
                        logger.debug(f"   ❌ Not found at: {path} ({path_error})")
                        continue
                
                if migration_sql:
                    logger.info(f"📄 Executing migration from {found_path} ({len(migration_sql)} bytes)")
                    db.execute(text(migration_sql))
                    db.commit()
                    logger.info("✅ ai_decisions table created successfully")
                else:
                    logger.error(f"❌ Could not find migration file in any location: {[str(p) for p in migration_paths]}")
            except Exception as create_error:
                logger.error(f"❌ Failed to create ai_decisions table: {create_error}")
        
        db.close()
    except Exception as e:
        logger.warning(f"⚠️ Could not verify/create tables: {e}")
    
    logger.info("[OK] Database connection ready")
    
    # Start Bot Engine first
    try:
        bot_engine_module.bot_engine = BotEngine(SessionLocal)
        await bot_engine_module.bot_engine.start()
        logger.info("[OK] Bot Engine started")
    except Exception as e:
        logger.error(f"[ERROR] Failed to start Bot Engine: {e}")
    
    # Initialize AI Agent if enabled
    if os.getenv("AI_AGENT_ENABLED", "true").lower() == "true":
        try:
            api_key = os.getenv("DEEPSEEK_API_KEY")
            if api_key:
                ai_mode = os.getenv("AI_AGENT_MODE", "observation")
                ai_agent_module.ai_agent = initialize_ai_agent(api_key, db_session_factory=SessionLocal, mode=ai_mode)
                await ai_agent_module.ai_agent.start()
                logger.info(f"[OK] AI Trading Agent initialized with monitoring loop (mode: {ai_mode})")
                
                # Connect AI Agent to Bot Engine
                if bot_engine_module.bot_engine:
                    bot_engine_module.bot_engine.set_ai_agent(ai_agent_module.ai_agent)
                    
                    # Configure Bot Engine AI integration (advisory vs autonomous)
                    bot_ai_mode = os.getenv("AI_AGENT_MODE", "advisory")
                    bot_engine_module.bot_engine.configure_ai(
                        enabled=True,
                        mode=bot_ai_mode,
                        min_confidence=int(os.getenv("AI_MIN_CONFIDENCE", "60"))
                    )
                    logger.info(f"[OK] AI Agent connected to Bot Engine (mode: {bot_ai_mode})")
                
                # Initialize AI Bot Controller
                ai_bot_controller_module.ai_bot_controller = initialize_ai_bot_controller(
                    SessionLocal, bot_engine_module.bot_engine
                )
                ai_bot_controller_module.ai_bot_controller.mode = os.getenv("AI_AGENT_MODE", "observation")
                
                # Auto-start controller if not in observation mode
                if ai_bot_controller_module.ai_bot_controller.mode != "observation":
                    await ai_bot_controller_module.ai_bot_controller.start()
                    logger.info(f"[OK] AI Bot Controller started (mode: {ai_bot_controller_module.ai_bot_controller.mode})")
                else:
                    logger.info("[OK] AI Bot Controller ready (mode: observation - not auto-started)")
            else:
                logger.warning("⚠️ DEEPSEEK_API_KEY not found - AI Agent disabled")
        except Exception as e:
            logger.error(f"[ERROR] Failed to initialize AI Agent: {e}")
    
    yield
    
    # Shutdown
    logger.info("🛑 CRBot API Shutting down...")
    if ai_bot_controller_module.ai_bot_controller and ai_bot_controller_module.ai_bot_controller._running:
        await ai_bot_controller_module.ai_bot_controller.stop()
        logger.info("[OK] AI Bot Controller stopped")
    if ai_agent_module.ai_agent:
        await ai_agent_module.ai_agent.stop()
        logger.info("[OK] AI Agent stopped")
    if bot_engine_module.bot_engine:
        await bot_engine_module.bot_engine.stop()
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
app.include_router(ai_agent.router)  # AI Agent routes
app.include_router(exchange.router)  # Exchange configuration routes
app.include_router(watchlist.router)  # Watchlist management routes

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
    _engine = bot_engine_module.bot_engine
    if not _engine:
        return {
            "status": "not_initialized",
            "running": False,
            "active_bots": 0,
            "message": "Bot Engine not initialized"
        }
    
    active_bots_info = []
    for bot_id, bot_state in _engine.active_bots.items():
        active_bots_info.append({
            "bot_id": bot_id,
            "name": bot_state.get("name"),
            "symbols": bot_state.get("symbols"),
            "last_check": bot_state.get("last_check").isoformat() if bot_state.get("last_check") else None
        })
    
    return {
        "status": "running" if _engine._running else "stopped",
        "running": _engine._running,
        "active_bots": len(_engine.active_bots),
        "active_bots_details": active_bots_info,
        "message": "Bot Engine is operational"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
