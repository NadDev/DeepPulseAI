from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import asyncio
import os

# Suppress TensorFlow and CUDA verbose logging
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # Suppress TensorFlow info/warnings
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'  # Disable oneDNN optimization to reduce warnings

# Import routes
from app.routes import health, portfolio, crypto, bots, reports, risk, trades, translations, ml, auth, ai_agent, exchange, watchlist, settings as settings_routes
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
logging.getLogger("tensorflow").setLevel(logging.ERROR)  # Suppress TensorFlow logs

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
        
        # Check if ml_predictions table exists, if not create it
        try:
            db.execute(text("SELECT 1 FROM ml_predictions LIMIT 1"))
            logger.info("[OK] ml_predictions table exists")
        except Exception as check_error:
            try:
                logger.info(f"⚙️ Creating ml_predictions table...")
                
                migration_paths = [
                    "/app/database/migrations/006_create_ml_predictions_table_railway.sql",
                    "database/migrations/006_create_ml_predictions_table_railway.sql",
                    pathlib.Path(__file__).parent.parent.parent / "database/migrations/006_create_ml_predictions_table_railway.sql"
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
                    logger.info("✅ ml_predictions table created successfully")
                else:
                    logger.error(f"❌ Could not find ml_predictions migration file")
            except Exception as create_error:
                logger.error(f"❌ Failed to create ml_predictions table: {create_error}")
        
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
        
        # Check if user_trading_settings table exists, if not create it
        try:
            db.execute(text("SELECT 1 FROM user_trading_settings LIMIT 1"))
            logger.info("[OK] user_trading_settings table exists")
        except Exception as check_error:
            try:
                logger.info(f"⚙️ Creating user_trading_settings table...")
                
                migration_paths = [
                    "/app/database/migrations/007_create_user_trading_settings.sql",
                    "database/migrations/007_create_user_trading_settings.sql",
                    pathlib.Path(__file__).parent.parent.parent / "database/migrations/007_create_user_trading_settings.sql"
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
                    logger.info("✅ user_trading_settings table created successfully")
                else:
                    logger.error(f"❌ Could not find user_trading_settings migration file")
            except Exception as create_error:
                logger.error(f"❌ Failed to create user_trading_settings table: {create_error}")
        
        # Check if trades table has TP2/phase columns, if not add them (migration 009)
        try:
            db.execute(text("SELECT take_profit_2, trade_phase FROM trades LIMIT 1"))
            logger.info("[OK] trades table has TP2/phase columns")
        except Exception as check_error:
            try:
                logger.info(f"⚙️ Adding TP2/phase columns to trades table...")
                
                migration_paths = [
                    "/app/database/migrations/009_add_tp2_and_phase_to_trades.sql",
                    "database/migrations/009_add_tp2_and_phase_to_trades.sql",
                    pathlib.Path(__file__).parent.parent.parent / "database/migrations/009_add_tp2_and_phase_to_trades.sql"
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
                    logger.info("✅ trades table extended with TP2/phase columns successfully")
                else:
                    logger.error(f"❌ Could not find trades TP2/phase migration file")
            except Exception as create_error:
                logger.error(f"❌ Failed to add TP2/phase columns: {create_error}")
        
        # Check if trades table has market_context columns, if not add them (migration 010)
        try:
            db.execute(text("SELECT market_context, market_context_confidence FROM trades LIMIT 1"))
            logger.info("[OK] trades table has market_context columns")
        except Exception as check_error:
            try:
                logger.info(f"⚙️ Adding market_context columns to trades table...")
                
                migration_paths = [
                    "/app/database/migrations/010_add_market_context_to_trades.sql",
                    "database/migrations/010_add_market_context_to_trades.sql",
                    pathlib.Path(__file__).parent.parent.parent / "database/migrations/010_add_market_context_to_trades.sql"
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
                    logger.info("✅ trades table extended with market_context columns successfully")
                else:
                    logger.error(f"❌ Could not find trades market_context migration file")
            except Exception as create_error:
                logger.error(f"❌ Failed to add market_context columns: {create_error}")
        
        # Normalize watchlist symbols to Binance format (migration 011)
        try:
            # Check if normalization is needed
            result = db.execute(text("SELECT COUNT(*) as count FROM watchlist_items WHERE symbol LIKE '%/%'"))
            row = result.fetchone()
            symbols_with_slash = row[0] if row else 0
            
            if symbols_with_slash > 0:
                logger.info(f"⚙️ Found {symbols_with_slash} watchlist symbols with slashes - normalizing to Binance format...")
                
                migration_paths = [
                    "/app/database/migrations/011_normalize_watchlist_symbols.sql",
                    "database/migrations/011_normalize_watchlist_symbols.sql",
                    pathlib.Path(__file__).parent.parent.parent / "database/migrations/011_normalize_watchlist_symbols.sql"
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
                    logger.info("✅ Watchlist symbols normalized to Binance format (BTCUSDT, not BTC/USDT)")
                else:
                    logger.warning(f"⚠️ Could not find watchlist normalization migration file - manual update needed")
            else:
                logger.info("[OK] Watchlist symbols already normalized to Binance format")
        except Exception as normalize_error:
            logger.warning(f"⚠️ Watchlist symbol normalization check failed: {normalize_error}")
        
        # Check if crypto_market_data table exists, if not create it (migration 013)
        try:
            db.execute(text("SELECT 1 FROM crypto_market_data LIMIT 1"))
            logger.info("[OK] crypto_market_data table exists")
        except Exception as check_error:
            try:
                logger.info(f"⚙️ Creating crypto recommendation tables (migration 013)...")
                
                migration_paths = [
                    "/app/database/migrations/013_add_crypto_recommendation_tables.sql",
                    "database/migrations/013_add_crypto_recommendation_tables.sql",
                    pathlib.Path(__file__).parent.parent.parent / "database/migrations/013_add_crypto_recommendation_tables.sql"
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
                    logger.info("✅ Crypto recommendation tables created successfully (crypto_market_data, watchlist_recommendations, recommendation_score_log)")
                else:
                    logger.error(f"❌ Could not find crypto recommendation migration file")
            except Exception as create_error:
                logger.error(f"❌ Failed to create crypto recommendation tables: {create_error}")
        
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
    
    # Initialize Strategy Context Manager
    try:
        from app.services.strategy_context_manager import initialize_strategy_context_manager
        initialize_strategy_context_manager()
        logger.info("[OK] Strategy Context Manager initialized")
    except Exception as e:
        logger.error(f"[ERROR] Failed to initialize Strategy Context Manager: {e}")
    
    # ===== START GLOBAL TRADE MONITOR (monitors ALL trades including AI_AGENT) =====
    try:
        from app.services.sl_tp_manager import GlobalTradeMonitor, create_sltp_manager
        from app.services.market_data import market_data_collector
        from app.services.technical_analysis import TechnicalAnalysis
        
        # Create SLTPManager with dependencies
        sltp_manager = create_sltp_manager(
            market_data_service=market_data_collector,
            technical_analysis=TechnicalAnalysis(),
            db_session_factory=SessionLocal
        )
        
        # Create and start GlobalTradeMonitor
        global_trade_monitor = GlobalTradeMonitor(
            sltp_manager=sltp_manager,
            db_session_factory=SessionLocal,
            market_data_service=market_data_collector
        )
        await global_trade_monitor.start()
        
        # Store reference for shutdown
        app.state.global_trade_monitor = global_trade_monitor
        logger.info("[OK] GlobalTradeMonitor started - monitoring ALL trades (incl. AI_AGENT)")
    except Exception as e:
        logger.error(f"[ERROR] Failed to start GlobalTradeMonitor: {e}")
    
    # ===== START RECOMMENDATION CRYPTO SYSTEM =====
    recommendation_enabled = os.getenv("RECOMMENDATION_ENABLE", "true").lower() == "true"
    if recommendation_enabled:
        try:
            # Check if crypto_market_data has data (needs bootstrap)
            db_check = SessionLocal()
            result = db_check.execute(text("SELECT COUNT(*) FROM crypto_market_data"))
            market_data_count = result.scalar()
            db_check.close()
            
            if market_data_count == 0:
                logger.warning("⚠️  Crypto market data is EMPTY - bootstrap needed!")
                logger.warning("   Run: python -c 'from app.services.market_data_bootstrapper import bootstrap_market_data; bootstrap_market_data()'")
            else:
                logger.info(f"✅ Crypto market data ready: {market_data_count:,} candles loaded")
            
            # Start Market Data Updater (async background job - updates every 4 hours)
            try:
                from app.services.market_data_updater import MarketDataUpdater
                market_data_updater = MarketDataUpdater(db_session_factory=SessionLocal)
                asyncio.create_task(market_data_updater.start())
                app.state.market_data_updater = market_data_updater
                logger.info("✅ Market Data Updater started (updates every 4 hours)")
            except Exception as e:
                logger.error(f"❌ Failed to start Market Data Updater: {e}")
            
            # Start Daily Recommendation Scheduler (APScheduler - runs at 08:00 UTC daily)
            try:
                from app.services.daily_recommendation_scheduler import DailyRecommendationScheduler
                recommendation_time = os.getenv("RECOMMENDATION_DAILY_TIME", "08:00")
                scheduler = DailyRecommendationScheduler(
                    db_session_factory=SessionLocal,
                    scheduled_time=recommendation_time  # e.g., "08:00"
                )
                asyncio.create_task(scheduler.start())
                app.state.recommendation_scheduler = scheduler
                logger.info(f"✅ Daily Recommendation Scheduler started (daily at {recommendation_time} UTC)")
            except Exception as e:
                logger.error(f"❌ Failed to start Daily Recommendation Scheduler: {e}")
            
            logger.info("✓ Recommendation system initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Recommendation system: {e}")
    else:
        logger.info("[SKIP] Recommendation system disabled (set RECOMMENDATION_ENABLE=true to enable)")
    
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
                
                # ✅ Enable AI in Bot Engine globally (will use per-user agents)
                if bot_engine_module.bot_engine:
                    bot_engine_module.bot_engine.configure_ai(
                        enabled=True,
                        mode="autonomous",
                        min_confidence=60
                    )
                    logger.info("✅ [STARTUP] Bot Engine AI enabled globally (autonomous mode, min_confidence=60%)")
                
                # ⚠️ DO NOT start global Bot Controller - it will be created per-user on demand
                logger.info("[SKIP] Global Bot Controller disabled - using per-user Bot Controller system")
            else:
                logger.warning("⚠️ DEEPSEEK_API_KEY not found - AI Agent disabled")
        except Exception as e:
            logger.error(f"[ERROR] Failed to initialize AI Agent: {e}")
    
    # === Phase 1: Start ML Accuracy Tracker ===
    try:
        from app.services.ml_engine.accuracy_tracker import get_accuracy_tracker
        import asyncio
        
        tracker = get_accuracy_tracker()
        # Start tracker in background
        asyncio.create_task(tracker.start())
        logger.info("✅ ML Accuracy Tracker started")
    except Exception as e:
        logger.warning(f"⚠️ Could not start ML Accuracy Tracker: {e}")
    
    # === Phase 2: Start Portfolio Sync Service (Production Mode) ===
    try:
        from app.services.portfolio_sync_service import get_portfolio_sync_service
        
        # Check if we should enable portfolio sync
        enable_sync = os.getenv("ENABLE_PORTFOLIO_SYNC", "false").lower() == "true"
        
        if enable_sync:
            sync_service = get_portfolio_sync_service()
            asyncio.create_task(sync_service.start())
            logger.info("✅ Portfolio Sync Service started (production mode)")
        else:
            logger.info("[SKIP] Portfolio Sync Service disabled (set ENABLE_PORTFOLIO_SYNC=true to enable)")
    except Exception as e:
        logger.warning(f"⚠️ Could not start Portfolio Sync Service: {e}")
    
    yield
    
    # Shutdown
    logger.info("🛑 CRBot API Shutting down...")
    
    # Stop GlobalTradeMonitor first
    try:
        if hasattr(app.state, 'global_trade_monitor') and app.state.global_trade_monitor:
            await app.state.global_trade_monitor.stop()
            logger.info("[OK] GlobalTradeMonitor stopped")
    except Exception as e:
        logger.debug(f"Error stopping GlobalTradeMonitor: {e}")
    
    # Stop accuracy tracker
    try:
        from app.services.ml_engine.accuracy_tracker import stop_accuracy_tracker
        stop_accuracy_tracker()
        logger.info("[OK] ML Accuracy Tracker stopped")
    except Exception as e:
        logger.debug(f"Error stopping accuracy tracker: {e}")
    
    # Stop portfolio sync service
    try:
        from app.services.portfolio_sync_service import stop_portfolio_sync_service
        stop_portfolio_sync_service()
        logger.info("[OK] Portfolio Sync Service stopped")
    except Exception as e:
        logger.debug(f"Error stopping portfolio sync service: {e}")
    
    # Stop recommendation scheduler
    try:
        if hasattr(app.state, 'recommendation_scheduler') and app.state.recommendation_scheduler:
            await app.state.recommendation_scheduler.stop()
            logger.info("[OK] Recommendation Scheduler stopped")
    except Exception as e:
        logger.debug(f"Error stopping recommendation scheduler: {e}")
    
    # Stop market data updater
    try:
        if hasattr(app.state, 'market_data_updater') and app.state.market_data_updater:
            await app.state.market_data_updater.stop()
            logger.info("[OK] Market Data Updater stopped")
    except Exception as e:
        logger.debug(f"Error stopping market data updater: {e}")
    
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
app.include_router(settings_routes.router)  # Trading settings routes

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
