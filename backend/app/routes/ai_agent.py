"""
AI Agent API Routes
Endpoints for interacting with the AI Trading Agent and AI Bot Controller
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from app.db.database import get_db
from app.auth.supabase_auth import get_current_user, UserResponse
from app.services import ai_agent as ai_agent_module
from app.services.ai_bot_controller import get_ai_bot_controller
from app.services import bot_engine as bot_engine_module
from app.services.market_data import market_data_collector
from app.services.technical_analysis import TechnicalAnalysis
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai-agent", tags=["AI Agent"])

# Technical analysis instance
ta = TechnicalAnalysis()

# Helper functions to get runtime instances
def get_ai_agent():
    return ai_agent_module.ai_agent

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


# ============================================
# Health & Status Endpoints
# ============================================

@router.get("/status")
async def get_ai_status(
    current_user: UserResponse = Depends(get_current_user)
):
    """Get AI Agent and Bot Engine status"""
    agent = get_ai_agent()
    controller = get_controller()
    engine = get_bot_engine()
    
    if not agent:
        raise HTTPException(status_code=503, detail="AI Agent not initialized")
    
    # Get AI Agent status including running state
    ai_status = {
        "enabled": agent.enabled,
        "running": agent._running,  # Add running state
        "mode": agent.mode,
        "decision_history_count": len(agent.decision_history) if hasattr(agent, 'decision_history') else 0
    }
    
    controller_status = controller.get_status() if controller else {}
    # Add controller running state too
    if controller:
        controller_status["running"] = controller.enabled
    
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
        "ai_agent": ai_status,
        "controller": controller_status,
        "engine": engine_status,
        "running": ai_status["running"],  # Top-level running state for convenience
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
    min_confidence: int = Query(50, ge=0, le=100)
):
    """
    Analyze all symbols from user's watchlist with AI.
    Returns recommendations sorted by confidence.
    """
    from app.models.database_models import WatchlistItem
    
    agent = get_ai_agent()
    if not agent or not agent.enabled:
        raise HTTPException(status_code=503, detail="AI Agent is disabled")
    
    try:
        # Get user's active watchlist items from database
        watchlist_items = db.query(WatchlistItem).filter(
            WatchlistItem.user_id == str(current_user.id),
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
async def toggle_ai_mode(
    request: ModeToggleRequest,
    current_user: UserResponse = Depends(get_current_user)
):
    """Toggle AI Agent mode"""
    controller = get_controller()
    engine = get_bot_engine()
    
    try:
        if request.target == "controller":
            if not controller:
                raise ValueError("AI Bot Controller not available")
            
            controller.set_mode(request.mode)
            
            # Start/stop controller based on mode
            if request.mode == "observation":
                if controller._running:
                    import asyncio
                    asyncio.create_task(controller.stop())
            elif request.mode in ["paper", "live"]:
                if not controller._running:
                    import asyncio
                    asyncio.create_task(controller.start())
            
            return {
                "status": "success",
                "target": "controller",
                "mode": request.mode,
                "message": f"AI Bot Controller mode changed to {request.mode}"
            }
        
        elif request.target == "engine":
            if not engine:
                raise ValueError("Bot Engine not available")
            
            # Toggle engine AI mode (advisory/autonomous)
            engine.configure_ai(
                enabled=True,
                mode=request.mode,
                min_confidence=engine.ai_min_confidence
            )
            
            return {
                "status": "success",
                "target": "engine",
                "mode": request.mode,
                "message": f"Bot Engine AI mode changed to {request.mode}"
            }
        
        else:
            raise ValueError(f"Unknown target: {request.target}")
        
    except Exception as e:
        logger.error(f"Error toggling mode: {str(e)}")
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
    """Get current AI Agent configuration"""
    controller = get_controller()
    if not controller:
        raise HTTPException(status_code=503, detail="AI Bot Controller not available")
    
    return {
        "config": controller.config,
        "mode": controller.mode,
        "enabled": controller.enabled
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
async def get_ai_bots(
    current_user: UserResponse = Depends(get_current_user)
):
    """Get list of AI-managed bots"""
    controller = get_controller()
    if not controller:
        raise HTTPException(status_code=503, detail="AI Bot Controller not available")
    
    try:
        bots = controller.get_ai_bots()
        
        return {
            "bots": bots,
            "count": len(bots),
            "active": sum(1 for b in bots if b.get("status") == "RUNNING")
        }
        
    except Exception as e:
        logger.error(f"Error getting AI bots: {str(e)}")
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
    current_user: UserResponse = Depends(get_current_user)
):
    """Start/Resume the AI Agent"""
    agent = get_ai_agent()
    if not agent:
        raise HTTPException(status_code=503, detail="AI Agent not initialized")
    
    try:
        if agent._running:
            return {"message": "AI Agent already running", "running": True}
        
        await agent.start()
        logger.info(f"🚀 AI Agent started by user {current_user.id}")
        
        return {
            "message": "AI Agent started successfully",
            "running": True,
            "mode": agent.mode
        }
    except Exception as e:
        logger.error(f"Error starting AI Agent: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_ai_agent(
    current_user: UserResponse = Depends(get_current_user)
):
    """Stop/Pause the AI Agent"""
    agent = get_ai_agent()
    if not agent:
        raise HTTPException(status_code=503, detail="AI Agent not initialized")
    
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


@router.post("/toggle")
async def toggle_ai_agent(
    current_user: UserResponse = Depends(get_current_user)
):
    """Toggle AI Agent on/off"""
    agent = get_ai_agent()
    if not agent:
        raise HTTPException(status_code=503, detail="AI Agent not initialized")
    
    try:
        if agent._running:
            await agent.stop()
            action = "stopped"
            running = False
        else:
            await agent.start()
            action = "started"
            running = True
        
        logger.info(f"🔄 AI Agent {action} by user {current_user.id}")
        
        return {
            "message": f"AI Agent {action} successfully",
            "running": running,
            "mode": agent.mode
        }
    except Exception as e:
        logger.error(f"Error toggling AI Agent: {str(e)}")
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
