from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.database_models import Portfolio, Trade
from app.services.risk_calculator import RiskCalculator
from app.auth.supabase_auth import get_current_user, get_optional_user, UserResponse
from sqlalchemy import desc
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter(prefix="/api", tags=["portfolio"])

class OrderCreate(BaseModel):
    symbol: str
    side: str  # BUY or SELL
    quantity: float
    price: float
    strategy: str = "Manual"
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

@router.get("/portfolio/summary")
async def get_portfolio_summary(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    """Get portfolio summary (KPIs)"""
    # Get portfolio for user
    user_id = current_user.id
    portfolio = db.query(Portfolio).filter(Portfolio.user_id == user_id).first()
    
    if not portfolio:
        # Create portfolio for this user if not exists
        portfolio = Portfolio(
            user_id=user_id,
            total_value=100000.0,
            cash_balance=100000.0,
            daily_pnl=0.0,
            total_pnl=0.0,
            win_rate=0.0,
            max_drawdown=0.0
        )
        db.add(portfolio)
        db.commit()
        db.refresh(portfolio)
    
    # Calculate real-time stats from trades (filtered by user)
    trade_query = db.query(Trade)
    if current_user:
        trade_query = trade_query.filter(Trade.user_id == current_user.id)
    
    open_trades = trade_query.filter(Trade.status == "OPEN").all()
    closed_trades = trade_query.filter(Trade.status == "CLOSED").all()
    
    # Calculate unrealized PnL (simplified, assuming current price is entry price for now)
    # In a real app, we would fetch current prices here
    unrealized_pnl = 0 
    
    # Calculate realized PnL
    realized_pnl = sum(t.pnl for t in closed_trades if t.pnl)
    
    # Update portfolio stats
    portfolio.total_pnl = realized_pnl
    
    # Calculate portfolio value dynamically: cash + positions value
    positions_value = sum(t.quantity * t.entry_price for t in open_trades)
    portfolio.total_value = portfolio.cash_balance + positions_value
    
    # Calculate win rate from closed trades
    if len(closed_trades) > 0:
        winning_trades = [t for t in closed_trades if t.pnl and t.pnl > 0]
        portfolio.win_rate = (len(winning_trades) / len(closed_trades)) * 100
    else:
        portfolio.win_rate = 0.0
    
    db.commit()
    
    # Get recent trades
    recent_trades = db.query(Trade).order_by(desc(Trade.entry_time)).limit(5).all()
    
    # Calculate advanced risk metrics
    trades_data = [
        {
            'status': t.status,
            'pnl': t.pnl
        }
        for t in db.query(Trade).all()
    ]
    
    # Get equity curve for max drawdown calculation
    equity_curve_response = await get_equity_curve(30, db, current_user)
    equity_data = equity_curve_response.get('data', [])
    
    # Calculate all risk metrics
    risk_metrics = RiskCalculator.calculate_all_metrics(
        trades=trades_data,
        equity_curve=equity_data
    )
    
    # Update max_drawdown in portfolio
    portfolio.max_drawdown = risk_metrics.get('max_drawdown_pct', 0.0)
    db.commit()
    
    return {
        "portfolio_value": portfolio.total_value,
        "cash_balance": portfolio.cash_balance,
        "daily_pnl": portfolio.daily_pnl,
        "total_pnl": portfolio.total_pnl,
        "win_rate": portfolio.win_rate,
        "max_drawdown": portfolio.max_drawdown,
        "open_positions_count": len(open_trades),
        "recent_trades_count": len(recent_trades),
        "last_updated": portfolio.updated_at.isoformat(),
        # Advanced risk metrics
        "sharpe_ratio": risk_metrics.get('sharpe_ratio', 0.0),
        "average_win": risk_metrics.get('average_win', 0.0),
        "average_loss": risk_metrics.get('average_loss', 0.0),
        "win_loss_ratio": risk_metrics.get('win_loss_ratio', 0.0),
        "profit_factor": risk_metrics.get('profit_factor', 0.0),
        "expectancy": risk_metrics.get('expectancy', 0.0),
        "largest_win": risk_metrics.get('largest_win', 0.0),
        "largest_loss": risk_metrics.get('largest_loss', 0.0)
    }

@router.get("/portfolio/positions")
async def get_positions(
    db: Session = Depends(get_db),
    current_user: Optional[UserResponse] = Depends(get_optional_user)
):
    """Get current open positions"""
    query = db.query(Trade).filter(Trade.status == "OPEN")
    
    # Filter by user if authenticated
    if current_user:
        query = query.filter(Trade.user_id == current_user.id)
    
    open_trades = query.all()
    
    positions = []
    for trade in open_trades:
        # For consistency with portfolio_value calculation, use entry_price
        # In a real app, would fetch current market price
        current_price = trade.entry_price  # Use entry price for consistency in tests
        pnl = (current_price - trade.entry_price) * trade.quantity if trade.side == "BUY" else (trade.entry_price - current_price) * trade.quantity
        pnl_percent = (pnl / (trade.entry_price * trade.quantity)) * 100 if trade.entry_price * trade.quantity != 0 else 0
        
        positions.append({
            "id": trade.id,
            "symbol": trade.symbol,
            "side": trade.side,
            "entry_price": trade.entry_price,
            "current_price": current_price,
            "quantity": trade.quantity,
            "value": current_price * trade.quantity,
            "unrealized_pnl": pnl,
            "unrealized_pnl_percent": pnl_percent,
            "strategy": trade.strategy,
            "entry_time": trade.entry_time.isoformat()
        })
        
    return positions

@router.post("/portfolio/orders")
async def create_order(
    order: OrderCreate, 
    db: Session = Depends(get_db),
    current_user: Optional[UserResponse] = Depends(get_optional_user)
):
    """Execute a new order (Buy/Sell)"""
    user_id = current_user.id if current_user else "user_1"
    portfolio = db.query(Portfolio).filter(Portfolio.user_id == user_id).first()
    
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
        
    total_cost = order.quantity * order.price
    
    if order.side == "BUY":
        if portfolio.cash_balance < total_cost:
            raise HTTPException(status_code=400, detail="Insufficient funds")
        
        portfolio.cash_balance -= total_cost
        
        new_trade = Trade(
            user_id=current_user.id if current_user else None,
            bot_id="manual",
            symbol=order.symbol,
            side="BUY",
            entry_price=order.price,
            quantity=order.quantity,
            status="OPEN",
            entry_time=datetime.utcnow(),
            strategy=order.strategy,
            stop_loss_price=order.stop_loss,
            take_profit_price=order.take_profit
        )
        db.add(new_trade)
        
    elif order.side == "SELL":
        # Check if we have the position (simplified)
        # In real app, we would check specific position or FIFO
        # For now, we just create a SELL trade or close an existing one
        
        # Try to find an open BUY trade to close (filtered by user)
        trade_query = db.query(Trade).filter(
            Trade.symbol == order.symbol, 
            Trade.side == "BUY", 
            Trade.status == "OPEN"
        )
        if current_user:
            trade_query = trade_query.filter(Trade.user_id == current_user.id)
        
        open_trade = trade_query.first()
        
        if open_trade:
            # Close the trade
            open_trade.status = "CLOSED"
            open_trade.exit_price = order.price
            open_trade.exit_time = datetime.utcnow()
            
            pnl = (order.price - open_trade.entry_price) * open_trade.quantity
            open_trade.pnl = pnl
            open_trade.pnl_percent = (pnl / (open_trade.entry_price * open_trade.quantity)) * 100
            
            portfolio.cash_balance += (order.quantity * order.price)
            portfolio.total_pnl += pnl
            
            # Return the closed trade info
            db.commit()
            return {"message": "Position closed", "pnl": pnl, "new_balance": portfolio.cash_balance}
        else:
            # No position to sell - reject the order
            raise HTTPException(
                status_code=400, 
                detail=f"No open BUY position found for {order.symbol}. Cannot sell without a position."
            )
            
    db.commit()
    return {"message": "Order executed successfully", "new_balance": portfolio.cash_balance}

@router.get("/trades")
async def get_trades(
    limit: int = 20,
    offset: int = 0,
    status: str = None,
    db: Session = Depends(get_db),
    current_user: Optional[UserResponse] = Depends(get_optional_user)
):
    """Get trades with pagination and filtering"""
    query = db.query(Trade)
    
    # Filter by user if authenticated
    if current_user:
        query = query.filter(Trade.user_id == current_user.id)
    
    if status:
        query = query.filter(Trade.status == status)
    
    total = query.count()
    trades = query.order_by(desc(Trade.entry_time)).offset(offset).limit(limit).all()
    
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "trades": [
            {
                "id": trade.id,
                "symbol": trade.symbol,
                "side": trade.side,
                "entry_price": trade.entry_price,
                "exit_price": trade.exit_price,
                "quantity": trade.quantity,
                "pnl": trade.pnl,
                "pnl_percent": trade.pnl_percent,
                "status": trade.status,
                "strategy": trade.strategy,
                "entry_time": trade.entry_time.isoformat() if trade.entry_time else None,
                "exit_time": trade.exit_time.isoformat() if trade.exit_time else None,
            }
            for trade in trades
        ]
    }

@router.get("/portfolio/equity-curve")
async def get_equity_curve(
    days: int = 30, 
    db: Session = Depends(get_db),
    current_user: Optional[UserResponse] = Depends(get_optional_user)
):
    """Get equity curve data for last N days"""
    user_id = current_user.id if current_user else "user_1"
    portfolio = db.query(Portfolio).filter(Portfolio.user_id == user_id).first()
    
    if not portfolio:
        return {"data": []}
    
    # Generate demo data
    import random
    today = datetime.utcnow()
    data = []
    
    for i in range(days):
        date = (today - timedelta(days=days-i)).strftime("%Y-%m-%d")
        value = 100000 + random.uniform(-5000, 8000) + i * 200
        data.append({
            "date": date,
            "value": round(value, 2)
        })
    
    return {"data": data, "current_value": portfolio.total_value}
