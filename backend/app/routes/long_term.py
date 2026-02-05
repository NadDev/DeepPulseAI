"""
Long-Term Strategy API Routes
Endpoints for managing long-term DCA accumulation strategy.

Features:
- Allocation settings (OPT-IN toggle)
- Position tracking
- Transaction history
- Analysis engine
- Manual DCA triggers
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.database_models import PortfolioAllocation, LongTermPosition, LongTermTransaction, Portfolio
from app.services.long_term_manager import LongTermManager
from app.services.market_data import MarketDataCollector
from app.services.technical_analysis import TechnicalAnalysis
from app.services.ml_engine import ML_Engine
from app.auth.local_auth import get_current_user, UserResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/long-term", tags=["long-term"])


# ============================================================================
# Pydantic Models
# ============================================================================

class AllocationUpdateRequest(BaseModel):
    """Request to update allocation settings"""
    lt_enabled: Optional[bool] = None
    long_term_pct: Optional[float] = None  # 0-20%
    lt_assets: Optional[List[str]] = None
    lt_asset_weights: Optional[Dict[str, float]] = None
    lt_dca_frequency: Optional[str] = None  # daily, weekly, monthly
    lt_dca_day: Optional[int] = None
    lt_dca_amount_pct: Optional[float] = None
    lt_min_confidence_score: Optional[int] = None
    lt_require_ml_7d_confidence: Optional[int] = None
    lt_max_fear_greed_index: Optional[int] = None


class AnalyzeSymbolResponse(BaseModel):
    """Response from symbol analysis"""
    symbol: str
    confidence_score: float
    criteria_met: Dict[str, Any]
    recommendation: str  # BUY, SKIP
    reason: str
    details: Dict[str, Any]
    analyzed_at: datetime


# ============================================================================
# Routes: Allocation Management
# ============================================================================

@router.get("/allocation")
async def get_allocation_settings(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Get user's long-term allocation settings.
    Returns OPT-IN status, allocation %, DCA config, etc.
    """
    user_id = current_user.id
    
    allocation = db.query(PortfolioAllocation).filter(
        PortfolioAllocation.user_id == user_id
    ).first()
    
    if not allocation:
        # Create default allocation (disabled, per OPT-IN philosophy)
        allocation = PortfolioAllocation(
            user_id=user_id,
            lt_enabled=False,
            long_term_pct=0.0,
            long_term_max_pct=20.0,
            day_trading_pct=100.0,
            lt_assets=["BTCUSDT", "ETHUSDT"],
            lt_asset_weights={"BTCUSDT": 60.0, "ETHUSDT": 40.0},
            lt_dca_frequency="weekly",
            lt_dca_day=1,  # Monday
            lt_dca_amount_pct=10.0,
            lt_min_confidence_score=80,
            lt_require_ml_7d_confidence=70,
            lt_max_fear_greed_index=30
        )
        db.add(allocation)
        db.commit()
        db.refresh(allocation)
    
    return {
        "user_id": str(allocation.user_id),
        "lt_enabled": allocation.lt_enabled,
        "long_term_pct": float(allocation.long_term_pct),
        "long_term_max_pct": float(allocation.long_term_max_pct),
        "day_trading_pct": float(allocation.day_trading_pct),
        "lt_assets": allocation.lt_assets,
        "lt_asset_weights": allocation.lt_asset_weights,
        "lt_dca_frequency": allocation.lt_dca_frequency,
        "lt_dca_day": allocation.lt_dca_day,
        "lt_dca_amount_pct": float(allocation.lt_dca_amount_pct),
        "lt_min_confidence_score": allocation.lt_min_confidence_score,
        "lt_require_ml_7d_confidence": allocation.lt_require_ml_7d_confidence,
        "lt_max_fear_greed_index": allocation.lt_max_fear_greed_index,
        "created_at": allocation.created_at,
        "updated_at": allocation.updated_at
    }


@router.put("/allocation")
async def update_allocation_settings(
    request: AllocationUpdateRequest,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Update long-term allocation settings.
    Can enable/disable strategy (OPT-IN), change allocation %, assets, etc.
    """
    user_id = current_user.id
    
    allocation = db.query(PortfolioAllocation).filter(
        PortfolioAllocation.user_id == user_id
    ).first()
    
    if not allocation:
        raise HTTPException(status_code=404, detail="Allocation not found. Call GET first to create default.")
    
    # Update fields
    if request.lt_enabled is not None:
        allocation.lt_enabled = request.lt_enabled
        logger.info(f"User {user_id} {'ENABLED' if request.lt_enabled else 'DISABLED'} long-term strategy (OPT-IN)")
    
    if request.long_term_pct is not None:
        if request.long_term_pct < 0 or request.long_term_pct > 20:
            raise HTTPException(status_code=400, detail="long_term_pct must be 0-20%")
        allocation.long_term_pct = request.long_term_pct
        allocation.day_trading_pct = 100.0 - request.long_term_pct
    
    if request.lt_assets is not None:
        allocation.lt_assets = request.lt_assets
    
    if request.lt_asset_weights is not None:
        allocation.lt_asset_weights = request.lt_asset_weights
    
    if request.lt_dca_frequency is not None:
        if request.lt_dca_frequency not in ["daily", "weekly", "monthly"]:
            raise HTTPException(status_code=400, detail="Invalid DCA frequency")
        allocation.lt_dca_frequency = request.lt_dca_frequency
    
    if request.lt_dca_day is not None:
        allocation.lt_dca_day = request.lt_dca_day
    
    if request.lt_dca_amount_pct is not None:
        allocation.lt_dca_amount_pct = request.lt_dca_amount_pct
    
    if request.lt_min_confidence_score is not None:
        if request.lt_min_confidence_score < 60 or request.lt_min_confidence_score > 100:
            raise HTTPException(status_code=400, detail="Confidence score must be 60-100")
        allocation.lt_min_confidence_score = request.lt_min_confidence_score
    
    if request.lt_require_ml_7d_confidence is not None:
        allocation.lt_require_ml_7d_confidence = request.lt_require_ml_7d_confidence
    
    if request.lt_max_fear_greed_index is not None:
        allocation.lt_max_fear_greed_index = request.lt_max_fear_greed_index
    
    db.commit()
    db.refresh(allocation)
    
    return {"status": "success", "message": "Allocation updated"}


# ============================================================================
# Routes: Positions & Transactions
# ============================================================================

@router.get("/positions")
async def get_lt_positions(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Get user's long-term positions.
    Can filter by status: ACCUMULATING, HOLDING, PARTIAL_EXIT, CLOSED
    """
    user_id = current_user.id
    
    # Initialize manager to get positions (uses existing method)
    lt_manager = LongTermManager(
        db_session=db,
        market_data=MarketDataCollector(),
        technical_analysis=TechnicalAnalysis(),
        ml_engine=None
    )
    
    positions = await lt_manager.get_positions(user_id, status)
    
    # Format response
    result = []
    for pos in positions:
        result.append({
            "id": str(pos.id),
            "symbol": pos.symbol,
            "status": pos.status,
            "total_quantity": float(pos.total_quantity),
            "avg_entry_price": float(pos.avg_entry_price),
            "total_invested": float(pos.total_invested),
            "unrealized_pnl": float(pos.unrealized_pnl) if pos.unrealized_pnl else 0,
            "unrealized_pnl_pct": float(pos.unrealized_pnl_pct) if pos.unrealized_pnl_pct else 0,
            "dca_count": pos.dca_count,
            "last_dca_at": pos.last_dca_at,
            "tp1_price": float(pos.tp1_price) if pos.tp1_price else None,
            "tp2_price": float(pos.tp2_price) if pos.tp2_price else None,
            "tp3_price": float(pos.tp3_price) if pos.tp3_price else None,
            "tp1_hit": pos.tp1_hit,
            "tp2_hit": pos.tp2_hit,
            "tp3_hit": pos.tp3_hit,
            "created_at": pos.created_at,
            "updated_at": pos.updated_at
        })
    
    return {"positions": result, "count": len(result)}


@router.get("/transactions")
async def get_lt_transactions(
    symbol: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Get user's long-term transaction history.
    Can filter by symbol.
    """
    user_id = current_user.id
    
    query = db.query(LongTermTransaction).filter(
        LongTermTransaction.user_id == user_id
    )
    
    if symbol:
        query = query.filter(LongTermTransaction.symbol == symbol)
    
    transactions = query.order_by(LongTermTransaction.executed_at.desc()).limit(limit).all()
    
    result = []
    for tx in transactions:
        result.append({
            "id": str(tx.id),
            "symbol": tx.symbol,
            "side": tx.side,
            "quantity": float(tx.quantity),
            "price": float(tx.price),
            "total_value": float(tx.total_value),
            "transaction_type": tx.transaction_type,
            "confidence_score": tx.confidence_score,
            "pnl": float(tx.pnl) if tx.pnl else None,
            "pnl_pct": float(tx.pnl_pct) if tx.pnl_pct else None,
            "executed_at": tx.executed_at,
            "market_context": tx.market_context,
            "fear_greed_index": tx.fear_greed_index
        })
    
    return {"transactions": result, "count": len(result)}


# ============================================================================
# Routes: Analysis Engine
# ============================================================================

@router.post("/analyze/{symbol}")
async def analyze_symbol_for_lt(
    symbol: str,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Analyze a symbol for long-term opportunity.
    Returns confidence score (0-100) and breakdown by criteria.
    """
    user_id = current_user.id
    
    # Initialize manager
    lt_manager = LongTermManager(
        db_session=db,
        market_data=MarketDataCollector(),
        technical_analysis=TechnicalAnalysis(),
        ml_engine=None  # TODO: Initialize ML if available
    )
    
    # Run analysis
    try:
        analysis = await lt_manager.analyze_lt_opportunity(symbol, user_id)
        
        return {
            "symbol": symbol,
            "confidence_score": analysis["confidence_score"],
            "criteria_met": analysis["criteria_met"],
            "recommendation": analysis["recommendation"],
            "reason": analysis["reason"],
            "details": analysis["details"],
            "analyzed_at": datetime.now()
        }
    
    except Exception as e:
        logger.error(f"Analysis failed for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/dca/trigger")
async def trigger_dca_check(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Manually trigger DCA check for current user.
    Useful for testing or impatient users.
    """
    user_id = current_user.id
    
    # Initialize manager
    lt_manager = LongTermManager(
        db_session=db,
        market_data=MarketDataCollector(),
        technical_analysis=TechnicalAnalysis(),
        ml_engine=None
    )
    
    # Check if should execute DCA
    decision = await lt_manager.should_execute_dca(user_id)
    
    if not decision["should_execute"]:
        return {
            "executed": False,
            "reason": decision.get("reason", "Unknown"),
            "analyses": decision.get("analyses", {})
        }
    
    # Execute DCA for qualified symbols
    results = []
    for symbol in decision["symbols"]:
        try:
            amount = decision["amounts"][symbol]
            analysis = decision["analyses"][symbol]
            
            transaction = await lt_manager.execute_dca(
                user_id=user_id,
                symbol=symbol,
                amount=amount,
                analysis=analysis
            )
            
            results.append({
                "symbol": symbol,
                "amount": amount,
                "success": transaction is not None,
                "transaction_id": str(transaction.id) if transaction else None
            })
        
        except Exception as e:
            logger.error(f"Failed to execute DCA for {symbol}: {e}")
            results.append({
                "symbol": symbol,
                "amount": decision["amounts"][symbol],
                "success": False,
                "error": str(e)
            })
    
    return {
        "executed": True,
        "total_symbols": len(decision["symbols"]),
        "total_amount": sum(decision["amounts"].values()),
        "results": results
    }
