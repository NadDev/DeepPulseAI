from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.database_models import Portfolio, Trade
from app.services.risk_calculator import RiskCalculator
from app.services.market_data import MarketDataCollector
from app.auth.supabase_auth import get_current_user, get_optional_user, UserResponse
from sqlalchemy import desc
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)

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
    
    # Fetch current prices for open positions to calculate unrealized PnL
    market_collector = MarketDataCollector()
    unrealized_pnl = 0
    positions_value = 0
    
    for trade in open_trades:
        try:
            # Get current price from market
            ticker_data = await market_collector.get_ticker(trade.symbol)
            current_price = float(ticker_data['close'])
            
            # Calculate position value at current price
            position_value_at_current = trade.quantity * current_price
            positions_value += position_value_at_current
            
            # Calculate unrealized PnL for this position
            trade_unrealized_pnl = trade.quantity * (current_price - float(trade.entry_price))
            unrealized_pnl += trade_unrealized_pnl
        except Exception as e:
            # Fallback: use entry price if current price not available
            logger.warning(f"Could not get current price for {trade.symbol}: {str(e)}")
            positions_value += trade.quantity * float(trade.entry_price)
    
    # Calculate realized PnL from closed trades
    realized_pnl = sum(t.pnl for t in closed_trades if t.pnl)
    
    # Update portfolio stats
    # CRITICAL: Total PnL = Realized + Unrealized
    portfolio.total_pnl = realized_pnl + unrealized_pnl
    
    # Calculate portfolio value dynamically: cash + positions at current prices
    # This gives the TRUE portfolio value
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
    from app.models.database_models import Bot
    from sqlalchemy import func as db_func
    
    query = db.query(Trade).filter(Trade.status == "OPEN")
    
    # Filter by user if authenticated
    if current_user:
        query = query.filter(Trade.user_id == current_user.id)
    
    open_trades = query.all()
    
    positions = []
    market_collector = MarketDataCollector()
    
    for trade in open_trades:
        # Get bot name if this trade is from a bot
        bot_name = None
        if trade.bot_id:
            bot = db.query(Bot).filter(Bot.id == trade.bot_id).first()
            if bot:
                bot_name = bot.name
        
        # Fetch actual current price from market
        try:
            ticker_data = await market_collector.get_ticker(trade.symbol)
            current_price = float(ticker_data['close'])
        except Exception as e:
            logger.warning(f"Could not get current price for {trade.symbol}: {str(e)}")
            # Fallback to entry price if market data unavailable
            current_price = float(trade.entry_price)
        
        pnl = (current_price - float(trade.entry_price)) * float(trade.quantity) if trade.side == "BUY" else (float(trade.entry_price) - current_price) * float(trade.quantity)
        pnl_percent = (pnl / (float(trade.entry_price) * float(trade.quantity))) * 100 if float(trade.entry_price) * float(trade.quantity) != 0 else 0
        
        positions.append({
            "id": trade.id,
            "symbol": trade.symbol,
            "side": trade.side,
            "entry_price": float(trade.entry_price),
            "current_price": current_price,
            "quantity": float(trade.quantity),
            "value": current_price * float(trade.quantity),
            "unrealized_pnl": pnl,
            "unrealized_pnl_percent": pnl_percent,
            "strategy": trade.strategy,
            "bot_name": bot_name,
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
    from app.models.database_models import Bot
    
    query = db.query(Trade)
    
    # Filter by user if authenticated
    if current_user:
        query = query.filter(Trade.user_id == current_user.id)
    
    if status:
        query = query.filter(Trade.status == status)
    
    total = query.count()
    trades = query.order_by(desc(Trade.entry_time)).offset(offset).limit(limit).all()
    
    trades_response = []
    for trade in trades:
        # Get bot name if this trade is from a bot
        bot_name = None
        if trade.bot_id:
            bot = db.query(Bot).filter(Bot.id == trade.bot_id).first()
            if bot:
                bot_name = bot.name
        
        trades_response.append({
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
            "bot_name": bot_name,
            "entry_time": trade.entry_time.isoformat() if trade.entry_time else None,
            "exit_time": trade.exit_time.isoformat() if trade.exit_time else None,
        })
    
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "trades": trades_response
    }

@router.get("/portfolio/equity-curve")
async def get_equity_curve(
    days: int = 30, 
    db: Session = Depends(get_db),
    current_user: Optional[UserResponse] = Depends(get_optional_user)
):
    """Get equity curve data for last N days (calculated from actual trades)"""
    user_id = current_user.id if current_user else "user_1"
    portfolio = db.query(Portfolio).filter(Portfolio.user_id == user_id).first()
    
    if not portfolio:
        return {"data": []}
    
    # Get all trades from the last N days
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    all_trades = db.query(Trade).filter(
        Trade.user_id == user_id,
        Trade.entry_time >= cutoff_date
    ).order_by(Trade.entry_time.asc()).all()
    
    # Calculate equity curve by simulating portfolio value over time
    data = []
    running_balance = portfolio.cash_balance
    today = datetime.utcnow()
    
    # Group trades by day
    trades_by_day = {}
    for trade in all_trades:
        day = trade.entry_time.date()
        if day not in trades_by_day:
            trades_by_day[day] = {'closed': [], 'opened': []}
        if trade.status == "CLOSED":
            trades_by_day[day]['closed'].append(trade)
        else:
            trades_by_day[day]['opened'].append(trade)
    
    # Build equity curve day by day
    for i in range(days):
        current_date = (today - timedelta(days=days-i)).date()
        
        # Start with cash balance
        daily_value = portfolio.cash_balance
        daily_pnl = 0
        
        # Add realized PnL from trades closed up to this date
        for trade in all_trades:
            if trade.entry_time.date() <= current_date and trade.status == "CLOSED" and trade.exit_time.date() <= current_date:
                daily_pnl += (trade.pnl or 0)
        
        # Add unrealized PnL from positions still open at this date
        open_at_date = [t for t in all_trades if t.entry_time.date() <= current_date and (t.status == "OPEN" or (t.status == "CLOSED" and t.exit_time.date() > current_date))]
        for trade in open_at_date:
            if trade.status == "OPEN" or (trade.status == "CLOSED" and trade.exit_time.date() > current_date):
                # This position is open at this date
                # We would need current price at this date for exact calculation
                # For now, use entry price (conservative estimate)
                position_value = trade.quantity * float(trade.entry_price)
                daily_value += position_value
        
        # Apply all PnL
        daily_value = daily_value + daily_pnl
        
        data.append({
            "date": current_date.strftime("%Y-%m-%d"),
            "value": round(daily_value, 2)
        })
    
    return {"data": data, "current_value": portfolio.total_value}
