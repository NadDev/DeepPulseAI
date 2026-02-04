"""
AI Agent API Routes
Endpoints for interacting with the AI Trading Agent and AI Bot Controller
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from app.db.database import get_db
from app.auth.local_auth import get_current_user, UserResponse
from app.services import ai_agent as ai_agent_module
from app.services.ai_agent_manager import ai_agent_manager
from app.services.ai_bot_controller import get_ai_bot_controller
from app.services import bot_engine as bot_engine_module
from app.services.market_data import market_data_collector
from app.services.technical_analysis import TechnicalAnalysis
import logging
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai-agent", tags=["AI Agent"])

# Technical analysis instance
ta = TechnicalAnalysis()

# Helper functions to get runtime instances
def get_ai_agent():
    """Get global AI agent (legacy, for backwards compatibility)"""
    return ai_agent_module.ai_agent

def get_user_ai_agent(user_id: str):
    """Get AI agent for specific user"""
    return ai_agent_manager.user_agents.get(user_id)

def get_user_bot_controller(user_id: str):
    """Get Bot Controller for specific user"""
    return ai_agent_manager.user_controllers.get(user_id)

def get_bot_engine():
    return bot_engine_module.bot_engine

def get_controller():
    return get_ai_bot_controller()


async def fetch_market_data_with_indicators(symbol: str) -> Optional[Dict[str, Any]]:
    """
    Fetch real market data from Binance and calculate technical indicators.
    Reuses the same logic as BotEngine._get_market_data()
    
    Args:
        symbol: Trading pair (e.g., 'BTCUSDT' or 'BTC')
        
    Returns:
        Dictionary with price data and calculated indicators
    """
    try:
        # Ensure symbol format for Binance
        binance_symbol = symbol if symbol.endswith("USDT") else f"{symbol}USDT"
        
        # Get historical candles from Binance (100 candles, 1h timeframe)
        candles = await market_data_collector.get_candles(binance_symbol, timeframe="1h", limit=100)
        
        if not candles or len(candles) < 20:
            logger.warning(f"Insufficient market data for {symbol}: got {len(candles) if candles else 0} candles")
            return None
        
        # Extract price arrays
        closes = [c['close'] for c in candles]
        highs = [c['high'] for c in candles]
        lows = [c['low'] for c in candles]
        volumes = [c['volume'] for c in candles]
        
        # Calculate technical indicators using TechnicalAnalysis class
        sma_20 = ta.calculate_sma(closes, 20)
        sma_50 = ta.calculate_sma(closes, 50)
        rsi = ta.calculate_rsi(closes, 14)
        bb_upper, bb_middle, bb_lower = ta.calculate_bollinger_bands(closes, 20, 2)
        macd_line, signal_line, histogram = ta.calculate_macd(closes)
        
        # Calculate support/resistance (simple method: recent highs/lows)
        resistance = max(highs[-20:])
        support = min(lows[-20:])
        avg_volume = sum(volumes[-20:]) / 20
        
        # Get current candle data
        current = candles[-1]
        prev = candles[-2] if len(candles) > 1 else candles[-1]
        
        # Calculate 24h change
        change_24h = ((current['close'] - prev['close']) / prev['close'] * 100) if prev['close'] > 0 else 0
        
        return {
            "symbol": binance_symbol,
            "close": current['close'],
            "high": current['high'],
            "low": current['low'],
            "open": current['open'],
            "volume": current['volume'],
            "change_24h": round(change_24h, 2),
            "timestamp": current['timestamp'],
            "indicators": {
                "rsi": round(rsi[-1], 2) if rsi and rsi[-1] is not None else None,
                "sma_20": round(sma_20[-1], 2) if sma_20 and sma_20[-1] is not None else None,
                "sma_50": round(sma_50[-1], 2) if sma_50 and sma_50[-1] is not None else None,
                "bb_upper": round(bb_upper[-1], 2) if bb_upper and bb_upper[-1] is not None else None,
                "bb_middle": round(bb_middle[-1], 2) if bb_middle and bb_middle[-1] is not None else None,
                "bb_lower": round(bb_lower[-1], 2) if bb_lower and bb_lower[-1] is not None else None,
                "macd": round(macd_line[-1], 4) if macd_line and macd_line[-1] is not None else None,
                "macd_signal": round(signal_line[-1], 4) if signal_line and signal_line[-1] is not None else None,
                "macd_histogram": round(histogram[-1], 4) if histogram and histogram[-1] is not None else None,
                "resistance": round(resistance, 2),
                "support": round(support, 2),
                "avg_volume": round(avg_volume, 2)
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching market data for {symbol}: {str(e)}")
        return None


# ============================================
# Pydantic Models for Request/Response
# ============================================

class AnalyzeRequest(BaseModel):
    """Request to analyze a symbol"""
    symbol: str
    timeframe: Optional[str] = "1h"


class AnalyzeResponse(BaseModel):
    """AI analysis response"""
    symbol: str
    action: str  # BUY, SELL, HOLD
    confidence: int  # 0-100
    reasoning: str
    risk_level: str  # LOW, MEDIUM, HIGH
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None


class ChatRequest(BaseModel):
    """Chat request to AI Agent"""
    message: str
    context: Optional[Dict[str, Any]] = None


class ConfigUpdateRequest(BaseModel):
    """Request to update AI Agent configuration"""
    # Trading Parameters
    max_daily_trades: Optional[int] = None
    max_active_bots: Optional[int] = None
    default_risk_percent: Optional[float] = None
    max_risk_percent: Optional[float] = None
    default_stop_loss_percent: Optional[float] = None
    max_stop_loss_percent: Optional[float] = None
    
    # AI Settings
    min_confidence: Optional[int] = None
    check_interval: Optional[int] = None
    cooldown_after_loss: Optional[int] = None
    loss_threshold_for_cooldown: Optional[float] = None
    
    # Watchlist
    watchlist_symbols: Optional[List[str]] = None
    
    # Status
    enabled: Optional[bool] = None


class ModeToggleRequest(BaseModel):
    """Request to toggle AI Agent mode"""
    mode: str  # observation, paper, live (for controller) or advisory, autonomous (for engine)
    target: Optional[str] = "controller"  # controller or engine


class AutonomousModeRequest(BaseModel):
    """Request to enable/disable autonomous trading mode"""
    enabled: bool
    
    
class AutonomousConfigResponse(BaseModel):
    """Response with autonomous trading configuration"""
    autonomous_enabled: bool
    mode: str
    risk_limits: Dict[str, Any]
    ai_trade_config: Dict[str, Any]


class StartAgentRequest(BaseModel):
    """Request to start AI Agent"""
    mode: Optional[str] = "trading"  # trading mode by default
    controller_mode: Optional[str] = "paper"  # paper mode by default


# ============================================
# Health & Status Endpoints
# ============================================

@router.get("/status")
async def get_ai_status(
    current_user: UserResponse = Depends(get_current_user)
):
    """Get AI Agent and Bot Engine status (per-user AI)"""
    user_id = str(current_user.id)
    
    # Get user's AI Agent status
    agent_status = ai_agent_manager.get_agent_status(user_id)
    controller_status = ai_agent_manager.get_controller_status(user_id)
    
    # Get user's AI Agent instance if exists
    user_agent = get_user_ai_agent(user_id)
    if user_agent:
        agent_status["decision_history_count"] = len(user_agent.decision_history)
    
    # Get user's Bot Controller instance if exists
    user_controller = get_user_bot_controller(user_id)
    if user_controller:
        controller_status.update(user_controller.get_status())
    
    # Bot Engine is still global (manages all bots)
    engine = get_bot_engine()
    engine_status = {}
    if engine:
        engine_status = {
            "running": engine._running,
            "active_bots": len(engine.active_bots),
            "ai_enabled": engine.ai_enabled,
            "ai_mode": engine.ai_mode,
            "ai_min_confidence": engine.ai_min_confidence
        }
    
    return {
        "ai_agent": agent_status,
        "controller": controller_status,
        "engine": engine_status,
        "running": agent_status.get("running", False),  # Top-level running state for convenience
        "user_id": user_id,
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================
# Analysis Endpoints
# ============================================

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_symbol(
    request: AnalyzeRequest,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    """Analyze a single symbol with AI using real market data from Binance"""
    agent = get_ai_agent()
    if not agent or not agent.enabled:
        raise HTTPException(status_code=503, detail="AI Agent is disabled")
    
    try:
        # Fetch REAL market data from Binance with calculated indicators
        data = await fetch_market_data_with_indicators(request.symbol)
        
        if not data:
            raise HTTPException(
                status_code=404, 
                detail=f"Could not fetch market data for {request.symbol}"
            )
        
        # Prepare market data for AI analysis
        market_data = {
            "close": data["close"],
            "high": data["high"],
            "low": data["low"],
            "open": data.get("open", data["close"]),
            "volume": data["volume"],
            "change_24h": data["change_24h"]
        }
        
        # Use calculated indicators
        indicators = data["indicators"]
        
        logger.info(f"🔍 Analyzing {request.symbol}: Price=${data['close']}, RSI={indicators.get('rsi')}")
        
        # Call AI Agent with simplified API
        analysis = await agent.analyze_market(symbol=request.symbol)
        
        return analysis
        
    except Exception as e:
        logger.error(f"Analysis error for {request.symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-watchlist")
async def analyze_watchlist(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
    limit: int = Query(10, ge=1, le=50),
    min_confidence: int = Query(40, ge=0, le=100)
):
    """
    Analyze all symbols from user's watchlist with AI (per-user AI).
    Returns recommendations sorted by confidence.
    """
    from app.models.database_models import WatchlistItem
    from uuid import UUID
    
    user_id = str(current_user.id)
    
    # Get user's AI Agent
    agent = get_user_ai_agent(user_id)
    if not agent or not agent.enabled:
        raise HTTPException(
            status_code=503, 
            detail="AI Agent is not running. Please enable it first by clicking the toggle button."
        )
    
    try:
        # Get user's active watchlist items from database
        watchlist_items = db.query(WatchlistItem).filter(
            WatchlistItem.user_id == UUID(current_user.id),
            WatchlistItem.is_active == True
        ).order_by(WatchlistItem.priority.desc()).limit(limit).all()
        
        logger.info(f"📊 Found {len(watchlist_items)} active watchlist items for user {current_user.id}")
        
        # Fallback: If no DB watchlist, use AI config watchlist_symbols
        symbols_to_analyze = []
        if watchlist_items:
            symbols_to_analyze = [(item.symbol, item.notes, item.priority) for item in watchlist_items]
            logger.info(f"✅ Analyzing {len(symbols_to_analyze)} symbols from DB watchlist")
        else:
            # Try to get symbols from AI controller config
            controller = get_controller()
            if controller and hasattr(controller, 'config'):
                config_symbols = controller.config.get('watchlist_symbols', [])
                if config_symbols:
                    logger.info(f"📋 Using AI config watchlist: {config_symbols}")
                    symbols_to_analyze = [(sym, None, 0) for sym in config_symbols]
            else:
                logger.warning("⚠️ No watchlist items found in DB or AI config")
        
        if not symbols_to_analyze:
            return {
                "recommendations": [],
                "count": 0,
                "message": "No symbols in watchlist. Add symbols in Settings → AI Agent → Watchlist."
            }
        
        recommendations = []
        errors = []
        
        for symbol_tuple in symbols_to_analyze:
            symbol_with_slash, notes, priority = symbol_tuple
            try:
                # Convert BTC/USDT to BTCUSDT format for Binance
                symbol = symbol_with_slash.replace("/", "")
                logger.info(f"🔍 Analyzing {symbol}...")
                
                # Fetch real market data
                data = await fetch_market_data_with_indicators(symbol)
                
                if not data:
                    errors.append(f"Could not fetch data for {symbol_with_slash}")
                    logger.warning(f"⚠️ No market data for {symbol}")
                    continue
                
                # Prepare data for AI
                market_data = {
                    "close": data["close"],
                    "high": data["high"],
                    "low": data["low"],
                    "open": data.get("open", data["close"]),
                    "volume": data["volume"],
                    "change_24h": data["change_24h"]
                }
                
                # Analyze with AI - simplified API
                analysis = await agent.analyze_market(symbol=symbol)
                logger.info(f"✅ {symbol}: {analysis.get('action')} at {analysis.get('confidence')}% confidence")
                
                # Only include if confidence meets threshold
                if analysis.get("confidence", 0) >= min_confidence:
                    if notes:
                        analysis["watchlist_notes"] = notes
                    if priority:
                        analysis["priority"] = priority
                    recommendations.append(analysis)
                    logger.info(f"✅ Added {symbol} to recommendations")
                else:
                    logger.info(f"⏭️ Skipped {symbol} (confidence {analysis.get('confidence')}% < {min_confidence}%)")
                    
            except Exception as e:
                logger.error(f"❌ Error analyzing {symbol_with_slash}: {str(e)}")
                errors.append(f"Error analyzing {symbol_with_slash}: {str(e)}")
        
        # Sort by confidence (highest first)
        recommendations.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        
        return {
            "recommendations": recommendations,
            "count": len(recommendations),
            "analyzed": len(symbols_to_analyze),
            "errors": errors if errors else None,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error analyzing watchlist: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recommendations")
async def get_recommendations(
    limit: int = Query(5, ge=1, le=20),
    min_confidence: int = Query(60, ge=0, le=100),
    current_user: UserResponse = Depends(get_current_user)
):
    """Get top AI recommendations"""
    controller = get_controller()
    if not controller:
        raise HTTPException(status_code=503, detail="AI Bot Controller not available")
    
    try:
        # Get recommendations from AI Bot Controller
        recommendations = controller.get_ai_bots()
        
        # Filter and sort by confidence
        filtered = [
            r for r in recommendations
            if r.get("confidence", 0) >= min_confidence
        ]
        
        return {
            "recommendations": filtered[:limit],
            "count": len(filtered),
            "total": len(recommendations)
        }
        
    except Exception as e:
        logger.error(f"Error getting recommendations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Chat Endpoint
# ============================================

@router.post("/chat")
async def chat_with_ai(
    request: ChatRequest,
    current_user: UserResponse = Depends(get_current_user)
):
    """Chat with AI Agent about trading"""
    agent = get_ai_agent()
    if not agent:
        raise HTTPException(status_code=503, detail="AI Agent not initialized")
    
    try:
        response = await agent.chat(request.message, request.context)
        
        return {
            "response": response,
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": str(current_user.id)
        }
        
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Control Endpoints
# ============================================

@router.post("/toggle")
async def toggle_ai_agent(
    current_user: UserResponse = Depends(get_current_user)
):
    """Toggle AI Agent on/off (per-user AI) - Simple start/stop"""
    user_id = str(current_user.id)
    
    try:
        # Check if user has an agent
        agent_status = ai_agent_manager.get_agent_status(user_id)
        
        if agent_status.get("running"):
            # Stop the agent
            await ai_agent_manager.stop_agent(user_id)
            await ai_agent_manager.stop_controller(user_id)
            
            return {
                "status": "success",
                "running": False,
                "message": "AI Agent stopped",
                "user_id": user_id
            }
        else:
            # Start the agent
            api_key = os.getenv("DEEPSEEK_API_KEY")
            if not api_key:
                raise HTTPException(status_code=500, detail="DeepSeek API key not configured")
            
            # Create and start agent
            agent = await ai_agent_manager.get_or_create_agent(
                user_id=user_id,
                api_key=api_key,
                model="deepseek-chat"
            )
            agent.mode = "trading"
            
            # Create and start controller
            controller = await ai_agent_manager.get_or_create_controller(
                user_id=user_id,
                bot_engine=get_bot_engine()
            )
            controller.set_ai_agent(agent)
            controller.mode = "paper"
            
            # Start both
            await agent.start()
            await controller.start()
            
            return {
                "status": "success",
                "running": True,
                "message": "AI Agent started",
                "user_id": user_id
            }
        
    except Exception as e:
        logger.error(f"Error toggling AI Agent: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/config")
async def update_config(
    request: ConfigUpdateRequest,
    current_user: UserResponse = Depends(get_current_user)
):
    """Update AI Agent configuration"""
    controller = get_controller()
    if not controller:
        raise HTTPException(status_code=503, detail="AI Bot Controller not available")
    
    try:
        # Build config dict with only non-None values
        config_update = {
            k: v for k, v in request.dict().items()
            if v is not None
        }
        
        result = controller.update_config(config_update)
        
        return {
            "status": "success",
            "message": "Configuration updated",
            "config": result["config"],
            "warnings": result.get("warnings", [])
        }
        
    except Exception as e:
        logger.error(f"Error updating config: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config")
async def get_config(
    current_user: UserResponse = Depends(get_current_user)
):
    """Get current AI Agent configuration (per-user)"""
    user_id = str(current_user.id)
    
    # Get user's Bot Controller
    controller = get_user_bot_controller(user_id)
    if not controller:
        raise HTTPException(
            status_code=503, 
            detail="AI Bot Controller not running. Please enable AI Agent first."
        )
    
    return {
        "config": controller.config,
        "mode": controller.mode,
        "enabled": controller.enabled,
        "user_id": user_id
    }


# ============================================
# History & Stats Endpoints
# ============================================

@router.get("/history")
async def get_decision_history(
    limit: int = Query(10, ge=1, le=100),
    current_user: UserResponse = Depends(get_current_user)
):
    """Get AI decision history"""
    agent = get_ai_agent()
    if not agent:
        raise HTTPException(status_code=503, detail="AI Agent not initialized")
    
    try:
        history = agent.get_decision_history(limit)
        
        return {
            "decisions": history,
            "count": len(history),
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"Error getting history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bots")
async def get_ai_bots_endpoint(
    current_user: UserResponse = Depends(get_current_user)
):
    """Get list of AI-managed bots for current user"""
    from app.services.ai_agent_manager import ai_agent_manager
    
    # Get the Bot Controller for this specific user
    controller = await ai_agent_manager.get_or_create_controller(
        user_id=current_user.id,
        bot_engine=None  # Not needed for reading bots
    )
    
    if not controller:
        raise HTTPException(status_code=503, detail="Bot Controller not available")
    
    try:
        # Get AI bots - controller already knows its user_id
        bots = controller.get_ai_bots(user_id=current_user.id)
        
        return {
            "bots": bots,
            "count": len(bots),
            "active": sum(1 for b in bots if b.get("status") == "RUNNING")
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting AI bots for user {current_user.id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Engine Control Endpoints
# ============================================

@router.post("/engine/configure")
async def configure_engine_ai(
    enabled: bool = True,
    mode: str = "advisory",
    min_confidence: int = 60,
    current_user: UserResponse = Depends(get_current_user)
):
    """Configure AI integration in Bot Engine"""
    engine = get_bot_engine()
    if not engine:
        raise HTTPException(status_code=503, detail="Bot Engine not available")
    
    try:
        engine.configure_ai(
            enabled=enabled,
            mode=mode,
            min_confidence=min_confidence
        )
        
        return {
            "status": "success",
            "message": "Engine AI configuration updated",
            "enabled": engine.ai_enabled,
            "mode": engine.ai_mode,
            "min_confidence": engine.ai_min_confidence
        }
        
    except Exception as e:
        logger.error(f"Error configuring engine: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Autonomous Trading Mode Endpoints
# ============================================

@router.get("/autonomous/status")
async def get_autonomous_status(
    current_user: UserResponse = Depends(get_current_user)
):
    """Get current autonomous trading mode status for user"""
    user_id = str(current_user.id)
    
    try:
        # Get user's AI Agent
        agent = get_user_ai_agent(user_id)
        
        if not agent:
            return {
                "autonomous_enabled": False,
                "mode": "not_initialized",
                "message": "AI Agent not initialized for this user"
            }
        
        # Get risk manager config if available
        risk_config = {}
        ai_trade_config = {}
        
        if agent.risk_manager:
            risk_config = {
                "max_position_size_pct": agent.risk_manager.limits.max_position_size_pct,
                "max_open_positions": agent.risk_manager.limits.max_open_positions,
                "max_daily_trades": agent.risk_manager.limits.max_daily_trades,
                "max_drawdown_pct": agent.risk_manager.limits.max_drawdown_pct,
                "min_cash_buffer": agent.risk_manager.limits.min_cash_buffer,
                "min_confidence": agent.risk_manager.limits.min_confidence,
            }
            ai_trade_config = {
                "position_size_pct": agent.risk_manager.ai_config.position_size_pct,
                "sl_method": agent.risk_manager.ai_config.sl_method,
                "sl_atr_multiplier": agent.risk_manager.ai_config.sl_atr_multiplier,
                "sl_fixed_pct": agent.risk_manager.ai_config.sl_fixed_pct,
                "tp_method": agent.risk_manager.ai_config.tp_method,
                "tp_atr_multiplier": agent.risk_manager.ai_config.tp_atr_multiplier,
                "tp_fixed_pct": agent.risk_manager.ai_config.tp_fixed_pct,
                "min_risk_reward": agent.risk_manager.ai_config.min_risk_reward,
            }
        
        return {
            "autonomous_enabled": agent.autonomous_enabled,
            "mode": agent.mode,
            "risk_limits": risk_config,
            "ai_trade_config": ai_trade_config
        }
        
    except Exception as e:
        logger.error(f"Error getting autonomous status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/autonomous/toggle")
async def toggle_autonomous_mode(
    request: AutonomousModeRequest,
    current_user: UserResponse = Depends(get_current_user)
):
    """Enable or disable autonomous trading mode for user's AI Agent"""
    user_id = str(current_user.id)
    
    try:
        # Get or create user's AI Agent
        agent = get_user_ai_agent(user_id)
        
        if not agent:
            # Try to initialize agent if not exists
            from app.services.ai_agent_manager import ai_agent_manager
            await ai_agent_manager.get_or_create_user_agent(user_id)
            agent = get_user_ai_agent(user_id)
        
        if not agent:
            raise HTTPException(
                status_code=503, 
                detail="Failed to initialize AI Agent for user"
            )
        
        # Toggle autonomous mode
        agent.enable_autonomous_mode(request.enabled)
        
        logger.info(f"🤖 User {user_id}: Autonomous mode {'ENABLED' if request.enabled else 'DISABLED'}")
        
        return {
            "status": "success",
            "autonomous_enabled": agent.autonomous_enabled,
            "mode": agent.mode,
            "message": f"Autonomous trading {'enabled' if request.enabled else 'disabled'}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling autonomous mode: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/autonomous/trades")
async def get_autonomous_trades(
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = Query(None, description="Filter by status: OPEN, CLOSED"),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    """Get trades executed by AI Agent in autonomous mode"""
    from app.models.database_models import Trade
    
    try:
        query = db.query(Trade).filter(
            Trade.user_id == current_user.id,
            Trade.strategy == "AI_AGENT"  # AI autonomous trades have this strategy
        )
        
        if status:
            query = query.filter(Trade.status == status.upper())
        
        trades = query.order_by(Trade.entry_time.desc()).limit(limit).all()
        
        # Calculate stats
        total_pnl = sum(float(t.pnl or 0) for t in trades if t.status == "CLOSED")
        winning = sum(1 for t in trades if t.status == "CLOSED" and (t.pnl or 0) > 0)
        losing = sum(1 for t in trades if t.status == "CLOSED" and (t.pnl or 0) < 0)
        open_count = sum(1 for t in trades if t.status == "OPEN")
        
        return {
            "trades": [
                {
                    "id": str(t.id),
                    "symbol": t.symbol,
                    "side": t.side,
                    "entry_price": float(t.entry_price) if t.entry_price else None,
                    "exit_price": float(t.exit_price) if t.exit_price else None,
                    "quantity": float(t.quantity) if t.quantity else None,
                    "pnl": float(t.pnl) if t.pnl else None,
                    "pnl_percent": float(t.pnl_percent) if t.pnl_percent else None,
                    "status": t.status,
                    "entry_time": t.entry_time.isoformat() if t.entry_time else None,
                    "exit_time": t.exit_time.isoformat() if t.exit_time else None,
                    "stop_loss": float(t.stop_loss_price) if t.stop_loss_price else None,
                    "take_profit": float(t.take_profit_price) if t.take_profit_price else None,
                }
                for t in trades
            ],
            "stats": {
                "total_trades": len(trades),
                "open_positions": open_count,
                "closed_trades": len(trades) - open_count,
                "total_pnl": round(total_pnl, 2),
                "winning_trades": winning,
                "losing_trades": losing,
                "win_rate": round(winning / (winning + losing) * 100, 1) if (winning + losing) > 0 else 0
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting autonomous trades: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/autonomous/stats")
async def get_autonomous_stats(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    """Get statistics for AI autonomous trading"""
    from app.models.database_models import Trade, AIDecision
    from datetime import timedelta
    
    try:
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        # Get AI trades
        trades = db.query(Trade).filter(
            Trade.user_id == current_user.id,
            Trade.strategy == "AI_AGENT",
            Trade.entry_time >= cutoff
        ).all()
        
        # Get AI decisions
        decisions = db.query(AIDecision).filter(
            AIDecision.user_id == current_user.id,
            AIDecision.created_at >= cutoff
        ).all()
        
        # Calculate trade stats
        closed_trades = [t for t in trades if t.status == "CLOSED"]
        total_pnl = sum(float(t.pnl or 0) for t in closed_trades)
        winning = [t for t in closed_trades if (t.pnl or 0) > 0]
        losing = [t for t in closed_trades if (t.pnl or 0) < 0]
        
        # Calculate decision stats
        executed_decisions = sum(1 for d in decisions if d.executed)
        buy_decisions = sum(1 for d in decisions if d.action == "BUY")
        sell_decisions = sum(1 for d in decisions if d.action == "SELL")
        
        return {
            "period_days": days,
            "trades": {
                "total": len(trades),
                "open": sum(1 for t in trades if t.status == "OPEN"),
                "closed": len(closed_trades),
                "winning": len(winning),
                "losing": len(losing),
                "win_rate": round(len(winning) / len(closed_trades) * 100, 1) if closed_trades else 0,
                "total_pnl": round(total_pnl, 2),
                "avg_win": round(sum(float(t.pnl) for t in winning) / len(winning), 2) if winning else 0,
                "avg_loss": round(sum(float(t.pnl) for t in losing) / len(losing), 2) if losing else 0,
            },
            "decisions": {
                "total": len(decisions),
                "executed": executed_decisions,
                "execution_rate": round(executed_decisions / len(decisions) * 100, 1) if decisions else 0,
                "buy_signals": buy_decisions,
                "sell_signals": sell_decisions,
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting autonomous stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/autonomous/config")
async def get_autonomous_config(
    current_user: UserResponse = Depends(get_current_user)
):
    """Get autonomous trading configuration for user's AI Agent"""
    user_id = str(current_user.id)
    
    try:
        agent = get_user_ai_agent(user_id)
        
        if not agent:
            # Return default config
            return {
                "autonomous_mode": False,
                "position_size_pct": 5.0,
                "min_confidence": 65,
                "use_risk_manager_sl_tp": True,
                "notifications_enabled": True
            }
        
        return {
            "autonomous_mode": agent.autonomous_enabled,
            "position_size_pct": agent.autonomous_config.get("position_size_pct", 5.0),
            "min_confidence": agent.autonomous_config.get("min_confidence", 65),
            "use_risk_manager_sl_tp": agent.autonomous_config.get("use_risk_manager_sl_tp", True),
            "notifications_enabled": agent.autonomous_config.get("notifications_enabled", True)
        }
        
    except Exception as e:
        logger.error(f"Error getting autonomous config: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


class AutonomousConfigUpdateRequest(BaseModel):
    """Request to update autonomous trading configuration"""
    position_size_pct: Optional[float] = None
    min_confidence: Optional[int] = None
    use_risk_manager_sl_tp: Optional[bool] = None
    notifications_enabled: Optional[bool] = None


@router.put("/autonomous/config")
async def update_autonomous_config(
    request: AutonomousConfigUpdateRequest,
    current_user: UserResponse = Depends(get_current_user)
):
    """Update autonomous trading configuration"""
    user_id = str(current_user.id)
    
    try:
        # Get or create user's AI Agent
        agent = get_user_ai_agent(user_id)
        
        if not agent:
            from app.services.ai_agent_manager import ai_agent_manager
            await ai_agent_manager.get_or_create_user_agent(user_id)
            agent = get_user_ai_agent(user_id)
        
        if not agent:
            raise HTTPException(
                status_code=503, 
                detail="Failed to initialize AI Agent for user"
            )
        
        # Update config values
        if request.position_size_pct is not None:
            agent.autonomous_config["position_size_pct"] = request.position_size_pct
        
        if request.min_confidence is not None:
            agent.autonomous_config["min_confidence"] = request.min_confidence
        
        if request.use_risk_manager_sl_tp is not None:
            agent.autonomous_config["use_risk_manager_sl_tp"] = request.use_risk_manager_sl_tp
        
        if request.notifications_enabled is not None:
            agent.autonomous_config["notifications_enabled"] = request.notifications_enabled
        
        logger.info(f"🤖 User {user_id}: Updated autonomous config: {agent.autonomous_config}")
        
        return {
            "status": "success",
            "config": agent.autonomous_config,
            "message": "Autonomous configuration updated"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating autonomous config: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Database Queries for AI Decisions
# ============================================

@router.get("/decisions")
async def get_ai_decisions(
    limit: int = Query(50, ge=1, le=500),
    symbol: Optional[str] = None,
    action: Optional[str] = None,
    executed: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    """Get AI decisions history from database"""
    from app.models.database_models import AIDecision
    
    try:
        query = db.query(AIDecision).filter(AIDecision.user_id == current_user.id)
        
        if symbol:
            query = query.filter(AIDecision.symbol == symbol.upper())
        
        if action:
            query = query.filter(AIDecision.action == action.upper())
        
        if executed is not None:
            query = query.filter(AIDecision.executed == executed)
        
        decisions = query.order_by(AIDecision.created_at.desc()).limit(limit).all()
        
        return {
            "decisions": [
                {
                    "id": str(d.id),
                    "symbol": d.symbol,
                    "action": d.action,
                    "confidence": d.confidence,
                    "executed": d.executed,
                    "blocked": d.blocked,
                    "blocked_reason": d.blocked_reason,
                    "mode": d.mode,
                    "reasoning": d.reasoning,
                    "entry_price": float(d.entry_price) if d.entry_price else None,
                    "target_price": float(d.target_price) if d.target_price else None,
                    "stop_loss": float(d.stop_loss) if d.stop_loss else None,
                    "risk_level": d.risk_level,
                    "result_pnl": float(d.result_pnl) if d.result_pnl else None,
                    "result_pnl_percent": float(d.result_pnl_percent) if d.result_pnl_percent else None,
                    "created_at": d.created_at.isoformat() if d.created_at else None,
                }
                for d in decisions
            ],
            "count": len(decisions),
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"Error fetching decisions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/decisions/stats")
async def get_ai_decisions_stats(
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    """Get AI decisions statistics"""
    from app.models.database_models import AIDecision
    from sqlalchemy import func
    from datetime import timedelta
    
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        decisions = db.query(AIDecision).filter(
            AIDecision.user_id == current_user.id,
            AIDecision.created_at >= cutoff_date
        ).all()
        
        # Calculate stats
        total = len(decisions)
        executed = sum(1 for d in decisions if d.executed)
        blocked = sum(1 for d in decisions if d.blocked)
        
        by_action = {
            "BUY": sum(1 for d in decisions if d.action == "BUY"),
            "SELL": sum(1 for d in decisions if d.action == "SELL"),
            "HOLD": sum(1 for d in decisions if d.action == "HOLD"),
        }
        
        avg_confidence = (
            sum(d.confidence for d in decisions) / total
            if total > 0 else 0
        )
        
        # Calculate PnL for executed decisions
        closed_trades = [d for d in decisions if d.executed and d.result_pnl is not None]
        total_pnl = sum(float(d.result_pnl) for d in closed_trades) if closed_trades else 0
        win_rate = (
            sum(1 for d in closed_trades if float(d.result_pnl) > 0) / len(closed_trades) * 100
            if closed_trades else 0
        )
        
        return {
            "period_days": days,
            "total_decisions": total,
            "executed_decisions": executed,
            "blocked_decisions": blocked,
            "execution_rate": (executed / total * 100) if total > 0 else 0,
            "by_action": by_action,
            "avg_confidence": round(avg_confidence, 2),
            "closed_trades": len(closed_trades),
            "total_pnl": round(total_pnl, 8),
            "win_rate": round(win_rate, 2),
        }
        
    except Exception as e:
        logger.error(f"Error calculating stats: {str(e)}")
        # Return safe defaults if table doesn't exist
        return {
            "period_days": days,
            "total_decisions": 0,
            "executed_decisions": 0,
            "blocked_decisions": 0,
            "execution_rate": 0,
            "by_action": {"BUY": 0, "SELL": 0, "HOLD": 0},
            "avg_confidence": 0,
            "closed_trades": 0,
            "total_pnl": 0,
            "win_rate": 0,
            "note": "ai_decisions table not yet created"
        }


# ============================================
# Control Endpoints (Start/Stop/Pause)
# ============================================

@router.post("/start")
async def start_ai_agent(
    current_user: UserResponse = Depends(get_current_user),
    request: StartAgentRequest = Body(default=StartAgentRequest(mode="trading", controller_mode="paper"))
):
    """Start/Resume the AI Agent (per-user AI)"""
    user_id = str(current_user.id)
    
    try:
        # Get or create user's AI Agent
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="DeepSeek API key not configured")
        
        agent = await ai_agent_manager.get_or_create_agent(
            user_id=user_id,
            api_key=api_key,
            model="deepseek-chat"
        )
        
        # Get or create user's Bot Controller
        controller = await ai_agent_manager.get_or_create_controller(
            user_id=user_id,
            bot_engine=get_bot_engine()
        )
        
        # Link agent to controller
        controller.set_ai_agent(agent)
        
        # ✅ Configure BotEngine to enable AI integration
        engine = get_bot_engine()
        if engine and agent:
            engine.set_ai_agent(agent)
            engine.configure_ai(enabled=True, mode="autonomous", min_confidence=60)
            logger.info(f"🤖 BotEngine AI configured: enabled=True, mode=autonomous")
        
        # Start both
        if not agent._running:
            agent.mode = request.mode
            await agent.start()
            logger.info(f"🚀 AI Agent started for user {user_id} in {request.mode} mode")
        
        if not controller._running:
            controller.mode = request.controller_mode
            await controller.start()
            logger.info(f"🚀 Bot Controller started for user {user_id} in {request.controller_mode} mode")
        
        return {
            "message": "AI Agent started successfully",
            "running": True,
            "mode": agent.mode,
            "user_id": user_id
        }
    except Exception as e:
        logger.error(f"Error starting AI Agent for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_ai_agent(
    current_user: UserResponse = Depends(get_current_user)
):
    """Stop/Pause the AI Agent (per-user AI)"""
    user_id = str(current_user.id)
    
    try:
        # Stop user's AI Agent
        await ai_agent_manager.stop_agent(user_id)
        
        # Stop user's Bot Controller
        await ai_agent_manager.stop_controller(user_id)
        
        logger.info(f"🛑 AI Agent stopped for user {user_id}")
        
        return {
            "message": "AI Agent stopped successfully",
            "running": False,
            "user_id": user_id
        }
    except Exception as e:
        logger.error(f"Error stopping AI Agent for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    try:
        if not agent._running:
            return {"message": "AI Agent already stopped", "running": False}
        
        await agent.stop()
        logger.info(f"⏸️ AI Agent stopped by user {current_user.id}")
        
        return {
            "message": "AI Agent stopped successfully",
            "running": False,
            "mode": agent.mode
        }
    except Exception as e:
        logger.error(f"Error stopping AI Agent: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# AI Bot Controller Control Endpoints
# ============================================

@router.post("/controller/start")
async def start_controller(
    current_user: UserResponse = Depends(get_current_user)
):
    """Start the AI Bot Controller"""
    controller = get_controller()
    if not controller:
        raise HTTPException(status_code=503, detail="AI Bot Controller not initialized")
    
    try:
        if controller._running:
            return {
                "message": "AI Bot Controller already running",
                "running": True,
                "mode": controller.mode
            }
        
        await controller.start()
        logger.info(f"🚀 AI Bot Controller started by user {current_user.id}")
        
        return {
            "message": "AI Bot Controller started successfully",
            "running": True,
            "mode": controller.mode
        }
    except Exception as e:
        logger.error(f"Error starting AI Bot Controller: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/controller/stop")
async def stop_controller(
    current_user: UserResponse = Depends(get_current_user)
):
    """Stop the AI Bot Controller"""
    controller = get_controller()
    if not controller:
        raise HTTPException(status_code=503, detail="AI Bot Controller not initialized")
    
    try:
        if not controller._running:
            return {
                "message": "AI Bot Controller already stopped",
                "running": False,
                "mode": controller.mode
            }
        
        await controller.stop()
        logger.info(f"⏸️ AI Bot Controller stopped by user {current_user.id}")
        
        return {
            "message": "AI Bot Controller stopped successfully",
            "running": False,
            "mode": controller.mode
        }
    except Exception as e:
        logger.error(f"Error stopping AI Bot Controller: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/controller/toggle")
async def toggle_controller(
    current_user: UserResponse = Depends(get_current_user)
):
    """Toggle AI Bot Controller on/off"""
    controller = get_controller()
    if not controller:
        raise HTTPException(status_code=503, detail="AI Bot Controller not initialized")
    
    try:
        if controller._running:
            await controller.stop()
            action = "stopped"
            running = False
        else:
            await controller.start()
            action = "started"
            running = True
        
        logger.info(f"🔄 AI Bot Controller {action} by user {current_user.id}")
        
        return {
            "message": f"AI Bot Controller {action} successfully",
            "running": running,
            "mode": controller.mode,
            "ai_bots": len(controller.ai_bots)
        }
    except Exception as e:
        logger.error(f"Error toggling AI Bot Controller: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
