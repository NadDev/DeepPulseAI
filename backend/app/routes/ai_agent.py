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
from app.services.ai_agent import ai_agent
from app.services.ai_bot_controller import ai_bot_controller
from app.services.bot_engine import bot_engine
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai-agent", tags=["AI Agent"])


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
    if not ai_agent:
        raise HTTPException(status_code=503, detail="AI Agent not initialized")
    
    ai_status = ai_agent.get_status() if hasattr(ai_agent, 'get_status') else {
        "enabled": False,
        "error": "AI Agent not fully initialized"
    }
    
    controller_status = ai_bot_controller.get_status() if ai_bot_controller else {}
    
    engine_status = {}
    if bot_engine:
        engine_status = {
            "running": bot_engine._running,
            "active_bots": len(bot_engine.active_bots),
            "ai_enabled": bot_engine.ai_enabled,
            "ai_mode": bot_engine.ai_mode,
            "ai_min_confidence": bot_engine.ai_min_confidence
        }
    
    return {
        "ai_agent": ai_status,
        "controller": controller_status,
        "engine": engine_status,
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
    """Analyze a single symbol with AI"""
    if not ai_agent or not ai_agent.enabled:
        raise HTTPException(status_code=503, detail="AI Agent is disabled")
    
    try:
        # Get market data (simplified - in production would use real market data)
        market_data = {
            "close": 0,
            "high": 0,
            "low": 0,
            "volume": 0,
            "change_24h": 0
        }
        
        indicators = {
            "rsi": 50,
            "sma_20": 0,
            "sma_50": 0,
            "bb_upper": 0,
            "bb_middle": 0,
            "bb_lower": 0,
            "support": 0,
            "resistance": 0
        }
        
        # TODO: Fetch real market data
        
        analysis = await ai_agent.analyze_market(
            symbol=request.symbol,
            market_data=market_data,
            indicators=indicators
        )
        
        return analysis
        
    except Exception as e:
        logger.error(f"Analysis error for {request.symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recommendations")
async def get_recommendations(
    limit: int = Query(5, ge=1, le=20),
    min_confidence: int = Query(60, ge=0, le=100),
    current_user: UserResponse = Depends(get_current_user)
):
    """Get top AI recommendations"""
    if not ai_bot_controller:
        raise HTTPException(status_code=503, detail="AI Bot Controller not available")
    
    try:
        # Get recommendations from AI Bot Controller
        recommendations = ai_bot_controller.get_ai_bots()
        
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
    if not ai_agent:
        raise HTTPException(status_code=503, detail="AI Agent not initialized")
    
    try:
        response = await ai_agent.chat(request.message, request.context)
        
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
    try:
        if request.target == "controller":
            if not ai_bot_controller:
                raise ValueError("AI Bot Controller not available")
            
            ai_bot_controller.set_mode(request.mode)
            
            # Start/stop controller based on mode
            if request.mode == "observation":
                if ai_bot_controller._running:
                    import asyncio
                    asyncio.create_task(ai_bot_controller.stop())
            elif request.mode in ["paper", "live"]:
                if not ai_bot_controller._running:
                    import asyncio
                    asyncio.create_task(ai_bot_controller.start())
            
            return {
                "status": "success",
                "target": "controller",
                "mode": request.mode,
                "message": f"AI Bot Controller mode changed to {request.mode}"
            }
        
        elif request.target == "engine":
            if not bot_engine:
                raise ValueError("Bot Engine not available")
            
            # Toggle engine AI mode (advisory/autonomous)
            bot_engine.configure_ai(
                enabled=True,
                mode=request.mode,
                min_confidence=bot_engine.ai_min_confidence
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
    if not ai_bot_controller:
        raise HTTPException(status_code=503, detail="AI Bot Controller not available")
    
    try:
        # Build config dict with only non-None values
        config_update = {
            k: v for k, v in request.dict().items()
            if v is not None
        }
        
        result = ai_bot_controller.update_config(config_update)
        
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
    if not ai_bot_controller:
        raise HTTPException(status_code=503, detail="AI Bot Controller not available")
    
    return {
        "config": ai_bot_controller.config,
        "mode": ai_bot_controller.mode,
        "enabled": ai_bot_controller.enabled
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
    if not ai_agent:
        raise HTTPException(status_code=503, detail="AI Agent not initialized")
    
    try:
        history = ai_agent.get_decision_history(limit)
        
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
    if not ai_bot_controller:
        raise HTTPException(status_code=503, detail="AI Bot Controller not available")
    
    try:
        bots = ai_bot_controller.get_ai_bots()
        
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
    if not bot_engine:
        raise HTTPException(status_code=503, detail="Bot Engine not available")
    
    try:
        bot_engine.configure_ai(
            enabled=enabled,
            mode=mode,
            min_confidence=min_confidence
        )
        
        return {
            "status": "success",
            "message": "Engine AI configuration updated",
            "enabled": bot_engine.ai_enabled,
            "mode": bot_engine.ai_mode,
            "min_confidence": bot_engine.ai_min_confidence
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
        raise HTTPException(status_code=500, detail=str(e))
