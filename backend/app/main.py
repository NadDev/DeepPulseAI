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

# Reduce verbosity of httpx logs (Binance/DeepSeek API calls)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

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
        
        # Check if exchange_configs table exists, if not create it
        try:
            db.execute(text("SELECT 1 FROM exchange_configs LIMIT 1"))
            logger.info("[OK] exchange_configs table exists")
        except Exception as check_error:
            try:
                logger.info(f"⚙️ Creating exchange_configs table...")
                
                migration_paths = [
                    "/app/database/migrations/002_create_exchange_configs_table_railway.sql",
                    "database/migrations/002_create_exchange_configs_table_railway.sql",
                    pathlib.Path(__file__).parent.parent.parent / "database/migrations/002_create_exchange_configs_table_railway.sql"
                ]
                
                migration_sql = None
                for path in migration_paths:
                    try:
                        migration_sql = open(path).read()
                        logger.info(f"✅ Found migration at: {path}")
                        break
                    except:
                        continue
                
                if migration_sql:
                    db.execute(text(migration_sql))
                    db.commit()
                    logger.info("✅ exchange_configs table created successfully")
                else:
                    logger.error(f"❌ Could not find exchange_configs migration file")
            except Exception as create_error:
                logger.error(f"❌ Failed to create exchange_configs table: {create_error}")
        
        # Create AI system user if not exists
        try:
            db.execute(text("SELECT 1 FROM users WHERE id = '00000000-0000-0000-0000-000000000001'::uuid LIMIT 1"))
            logger.info("[OK] AI system user exists")
        except Exception as check_error:
            try:
                logger.info(f"⚙️ Creating AI system user...")
                
                migration_paths = [
                    "/app/database/migrations/005_create_ai_system_user.sql",
                    "database/migrations/005_create_ai_system_user.sql",
                    pathlib.Path(__file__).parent.parent.parent / "database/migrations/005_create_ai_system_user.sql"
                ]
                
                migration_sql = None
                for path in migration_paths:
                    try:
                        migration_sql = open(path).read()
                        logger.info(f"✅ Found migration at: {path}")
                        break
                    except:
                        continue
                
                if migration_sql:
                    db.execute(text(migration_sql))
                    db.commit()
                    logger.info("✅ AI system user created successfully")
                else:
                    logger.error(f"❌ Could not find AI system user migration file")
            except Exception as create_error:
                logger.error(f"❌ Failed to create AI system user: {create_error}")
        
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
                # Get mode from environment (observation, paper, live, advisory, autonomous)
                raw_mode = os.getenv("AI_AGENT_MODE", "observation")
                
                # Map unified mode to each service's expected format:
                # - AI Agent expects: "observation" or "trading"
                # - Bot Controller expects: "observation", "paper", "live"  
                # - Bot Engine expects: "advisory", "autonomous"
                
                # AI Agent mode mapping
                ai_agent_mode = "trading" if raw_mode in ["paper", "live", "autonomous"] else "observation"
                
                # Bot Controller mode mapping  
                bot_controller_mode = raw_mode if raw_mode in ["observation", "paper", "live"] else "observation"
                
                # Bot Engine mode mapping
                bot_engine_mode = "autonomous" if raw_mode in ["autonomous", "live"] else "advisory"
                
                logger.info(f"🎛️ Mode configuration: raw={raw_mode}, agent={ai_agent_mode}, controller={bot_controller_mode}, engine={bot_engine_mode}")
                
                # ⚠️ DO NOT start global AI Agent - it will be created per-user on demand
                # AI Agents are now created via ai_agent_manager when user calls /api/ai-agent/start
                logger.info("[SKIP] Global AI Agent disabled - using per-user AI Agent system")
                
                # Keep legacy reference as None for backwards compatibility
                ai_agent_module.ai_agent = None
                
                # Bot Engine AI integration disabled (will be managed per-user)
                if bot_engine_module.bot_engine:
                    logger.info("[INFO] Bot Engine AI will be configured per-user")
                
                # ⚠️ DO NOT start global Bot Controller - it will be created per-user on demand
                logger.info("[SKIP] Global Bot Controller disabled - using per-user Bot Controller system")
                    logger.info(f"[OK] AI Bot Controller ready (mode: {bot_controller_mode} - not auto-started)")
            else:
                logger.warning("⚠️ DEEPSEEK_API_KEY not found - AI Agent disabled")
        except Exception as e:
            logger.error(f"[ERROR] Failed to initialize AI Agent: {e}")
    
    yield
    
    # Shutdown
    logger.info("🛑 CRBot API Shutting down...")
    
    # Stop all per-user AI Agents and Controllers
    from app.services.ai_agent_manager import ai_agent_manager
    for user_id in list(ai_agent_manager.user_agents.keys()):
        await ai_agent_manager.stop_agent(user_id)
    for user_id in list(ai_agent_manager.user_controllers.keys()):
        await ai_agent_manager.stop_controller(user_id)
    logger.info("[OK] All per-user AI Agents and Controllers stopped")
    
    # Legacy global instances (should be None now)
    if ai_bot_controller_module.ai_bot_controller and ai_bot_controller_module.ai_bot_controller._running:
        await ai_bot_controller_module.ai_bot_controller.stop()
        logger.info("[OK] Global AI Bot Controller stopped")
    if ai_agent_module.ai_agent:
        await ai_agent_module.ai_agent.stop()
        logger.info("[OK] Global AI Agent stopped")
    
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
