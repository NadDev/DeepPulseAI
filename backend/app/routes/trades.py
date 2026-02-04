from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from app.db.database import get_db
from app.models.database_models import Trade, Bot
from app.auth.local_auth import get_current_user, get_optional_user, UserResponse
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter(prefix="/api/trades", tags=["trades"])

class TradeCreateRequest(BaseModel):
    """Request model for creating a trade with limits"""
    bot_id: str
    symbol: str
    side: str  # BUY or SELL
    entry_price: float
    quantity: float
    strategy: str
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    trailing_stop_percent: Optional[float] = None

class TradeResponse(BaseModel):
    """Response model for trade"""
    id: int
    user_id: Optional[str] = None
    bot_id: str
    symbol: str
    side: str
    entry_price: float
    exit_price: Optional[float]
    quantity: float
    pnl: Optional[float]
    pnl_percent: Optional[float]
    status: str
    stop_loss_price: Optional[float]
    take_profit_price: Optional[float]
    trailing_stop_percent: Optional[float]
    
    class Config:
        from_attributes = True

@router.post("/create", response_model=TradeResponse)
async def create_trade(
    trade_req: TradeCreateRequest,
    db: Session = Depends(get_db),
    current_user: Optional[UserResponse] = Depends(get_optional_user)
):
    """
    FEATURE 1.1: Create a trade with risk limits
    - stop_loss_price: Price at which to exit if trade goes wrong
    - take_profit_price: Price at which to take profit
    - trailing_stop_percent: Trailing stop as percentage of entry price
    """
    
    # Validate limits logic
    if trade_req.stop_loss_price and trade_req.entry_price:
        if trade_req.side == "BUY":
            if trade_req.stop_loss_price >= trade_req.entry_price:
                raise HTTPException(
                    status_code=400,
                    detail="Stop loss must be below entry price for BUY orders"
                )
        elif trade_req.side == "SELL":
            if trade_req.stop_loss_price <= trade_req.entry_price:
                raise HTTPException(
                    status_code=400,
                    detail="Stop loss must be above entry price for SELL orders"
                )
    
    if trade_req.take_profit_price and trade_req.entry_price:
        if trade_req.side == "BUY":
            if trade_req.take_profit_price <= trade_req.entry_price:
                raise HTTPException(
                    status_code=400,
                    detail="Take profit must be above entry price for BUY orders"
                )
        elif trade_req.side == "SELL":
            if trade_req.take_profit_price >= trade_req.entry_price:
                raise HTTPException(
                    status_code=400,
                    detail="Take profit must be below entry price for SELL orders"
                )
    
    if trade_req.trailing_stop_percent:
        if trade_req.trailing_stop_percent < 0 or trade_req.trailing_stop_percent > 100:
            raise HTTPException(
                status_code=400,
                detail="Trailing stop must be between 0 and 100"
            )
    
    # Create trade with user_id
    trade = Trade(
        user_id=current_user.id if current_user else None,
        bot_id=trade_req.bot_id,
        symbol=trade_req.symbol,
        side=trade_req.side,
        entry_price=trade_req.entry_price,
        quantity=trade_req.quantity,
        strategy=trade_req.strategy,
        status="OPEN",
        entry_time=datetime.utcnow(),
        stop_loss_price=trade_req.stop_loss_price,
        take_profit_price=trade_req.take_profit_price,
        trailing_stop_percent=trade_req.trailing_stop_percent,
        max_loss_amount=None
    )
    
    db.add(trade)
    db.commit()
    db.refresh(trade)
    
    return trade

@router.get("/list", response_model=List[TradeResponse])
async def get_trades(
    symbol: Optional[str] = None,
    status: Optional[str] = None,
    bot_id: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: Optional[UserResponse] = Depends(get_optional_user)
):
    """Get trades with optional filters (filtered by user if authenticated)"""
    query = db.query(Trade)
    
    # Filter by user_id if authenticated
    if current_user:
        query = query.filter(Trade.user_id == current_user.id)
    
    if symbol:
        query = query.filter(Trade.symbol == symbol.upper())
    if status:
        query = query.filter(Trade.status == status.upper())
    if bot_id:
        query = query.filter(Trade.bot_id == bot_id)
    
    trades = query.order_by(Trade.created_at.desc()).limit(limit).all()
    return trades

@router.get("/{trade_id}", response_model=TradeResponse)
async def get_trade(
    trade_id: int, 
    db: Session = Depends(get_db),
    current_user: Optional[UserResponse] = Depends(get_optional_user)
):
    """Get a specific trade"""
    query = db.query(Trade).filter(Trade.id == trade_id)
    
    # Filter by user_id if authenticated
    if current_user:
        query = query.filter(Trade.user_id == current_user.id)
    
    trade = query.first()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    return trade

@router.put("/{trade_id}/close")
async def close_trade(
    trade_id: int,
    exit_price: float,
    db: Session = Depends(get_db),
    current_user: Optional[UserResponse] = Depends(get_optional_user)
):
    """Close a trade and calculate P&L"""
    query = db.query(Trade).filter(Trade.id == trade_id)
    
    # Filter by user_id if authenticated
    if current_user:
        query = query.filter(Trade.user_id == current_user.id)
    
    trade = query.first()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    
    if trade.status == "CLOSED":
        raise HTTPException(status_code=400, detail="Trade already closed")
    
    # Calculate P&L
    if trade.side == "BUY":
        pnl = (exit_price - trade.entry_price) * trade.quantity
    else:  # SELL
        pnl = (trade.entry_price - exit_price) * trade.quantity
    
    pnl_percent = (pnl / (trade.entry_price * trade.quantity)) * 100
    
    # Update trade
    trade.exit_price = exit_price
    trade.pnl = pnl
    trade.pnl_percent = pnl_percent
    trade.status = "CLOSED"
    trade.exit_time = datetime.utcnow()
    
    db.commit()
    db.refresh(trade)
    
    return {
        "id": trade.id,
        "pnl": trade.pnl,
        "pnl_percent": trade.pnl_percent,
        "status": trade.status
    }
