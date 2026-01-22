from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.database_models import Portfolio, Trade, Bot
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
    
    # === CRITICAL FIX ===
    # Cash balance calculation:
    # 1. Start with initial capital (100,000)
    # 2. Subtract cost of ALL open positions (entry_price × quantity)
    # 3. Add ALL realized PnL from closed trades
    
    # Get initial capital (should be stored, using 100k as default for now)
    initial_capital = 100000.0
    
    # Calculate cost of open positions
    cost_of_open_positions = sum(float(t.entry_price) * float(t.quantity) for t in open_trades)
    
    # Calculate realized PnL from closed trades
    realized_pnl = sum(t.pnl for t in closed_trades if t.pnl)
    
    # RECALCULATE cash_balance correctly:
    # cash_balance = initial_capital - cost_of_open_positions + realized_pnl
    recalculated_cash_balance = initial_capital - cost_of_open_positions + realized_pnl
    
    logger.debug(f"Portfolio recalculation: initial={initial_capital}, cost_open={cost_of_open_positions:.2f}, realized_pnl={realized_pnl:.2f}, cash={recalculated_cash_balance:.2f}")
    
    # Fetch current prices for open positions to calculate unrealized PnL
    market_collector = MarketDataCollector()
    unrealized_pnl = 0
    positions_current_value = 0
    
    for trade in open_trades:
        try:
            # Get current price from market
            ticker_data = await market_collector.get_ticker(trade.symbol)
            current_price = float(ticker_data['close'])
            
            # Calculate position value at current price
            position_value_at_current = float(trade.quantity) * current_price
            positions_current_value += position_value_at_current
            
            # Calculate unrealized PnL for this position
            trade_unrealized_pnl = float(trade.quantity) * (current_price - float(trade.entry_price))
            unrealized_pnl += trade_unrealized_pnl
        except Exception as e:
            # Fallback: use entry price if current price not available
            logger.warning(f"Could not get current price for {trade.symbol}: {str(e)}")
            positions_current_value += float(trade.quantity) * float(trade.entry_price)
    
    # Update portfolio stats
    # CRITICAL: Total PnL = Realized + Unrealized
    portfolio.total_pnl = realized_pnl + unrealized_pnl
    portfolio.cash_balance = recalculated_cash_balance
    
    # Calculate portfolio value dynamically:
    # total_value = cash_balance + sum(current market value of open positions)
    portfolio.total_value = recalculated_cash_balance + positions_current_value
    
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
    
    # === CRITICAL FIX #24: Calculate daily_pnl from trades closed TODAY ===
    today = datetime.now().date()
    daily_pnl = 0.0
    for trade in closed_trades:
        # Check if trade was closed today
        if trade.exit_time and trade.exit_time.date() == today:
            daily_pnl += (trade.pnl or 0)
    portfolio.daily_pnl = daily_pnl
    
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
    current_user: Optional[UserResponse] = Depends(get_optional_user),
    sort_by: str = "symbol",  # symbol, entry_price, current_price, unrealized_pnl
    sort_order: str = "asc",  # asc, desc
    symbol_filter: str = None,
    min_pnl: float = None,
    max_pnl: float = None
):
    """Get current open positions with sorting and filtering"""
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
        
        # === CRITICAL FIX #1: Always fetch current price from market ===
        # Never use entry_price as fallback - force real market data
        current_price = None
        try:
            ticker_data = await market_collector.get_ticker(trade.symbol)
            current_price = float(ticker_data['close'])
            logger.debug(f"✓ Fetched {trade.symbol}: ${current_price:.2f}")
        except Exception as e:
            logger.warning(f"⚠️ Could not get current price for {trade.symbol}: {str(e)}")
            # STILL use entry price if API fails, but log it clearly
            current_price = float(trade.entry_price)
            logger.warning(f"   Fallback: Using entry_price ${current_price:.2f}")
        
        # === CRITICAL FIX #2: Calculate unrealized PnL correctly ===
        # Always use: (current_price - entry_price) * quantity
        entry_price = float(trade.entry_price)
        quantity = float(trade.quantity)
        
        if trade.side == "BUY":
            # Buy position: profit if price went up
            unrealized_pnl = (current_price - entry_price) * quantity
        else:
            # Sell position: profit if price went down
            unrealized_pnl = (entry_price - current_price) * quantity
        
        # Calculate percentage
        position_cost = entry_price * quantity
        unrealized_pnl_percent = (unrealized_pnl / position_cost) * 100 if position_cost != 0 else 0
        
        # Apply filters
        if min_pnl is not None and unrealized_pnl < min_pnl:
            continue
        if max_pnl is not None and unrealized_pnl > max_pnl:
            continue
        if symbol_filter and trade.symbol != symbol_filter.upper():
            continue
        
        positions.append({
            "id": trade.id,
            "symbol": trade.symbol,
            "side": trade.side,
            "entry_price": entry_price,
            "current_price": current_price,
            "quantity": quantity,
            "value": current_price * quantity,
            "unrealized_pnl": unrealized_pnl,
            "unrealized_pnl_percent": unrealized_pnl_percent,
            "strategy": trade.strategy,
            "bot_name": bot_name,
            "entry_time": trade.entry_time.isoformat()
        })
    
    # Apply sorting
    sort_order_asc = sort_order.lower() != "desc"
    
    if sort_by == "entry_price":
        positions.sort(key=lambda x: x["entry_price"], reverse=not sort_order_asc)
    elif sort_by == "current_price":
        positions.sort(key=lambda x: x["current_price"], reverse=not sort_order_asc)
    elif sort_by == "unrealized_pnl":
        positions.sort(key=lambda x: x["unrealized_pnl"], reverse=not sort_order_asc)
    else:  # Default: symbol
        positions.sort(key=lambda x: x["symbol"], reverse=not sort_order_asc)
    
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

@router.get("/portfolio/trade-history")
async def get_trade_history(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
    page: int = 1,
    page_size: int = 10,
    sort_by: str = "entry_time",  # entry_time, symbol, pnl, status
    sort_order: str = "desc",  # asc, desc
    symbol_filter: str = None,
    status_filter: str = "CLOSED",  # CLOSED, OPEN, ALL
    min_pnl: float = None,
    max_pnl: float = None
):
    """
    Get trade history with pagination, sorting, and filtering
    
    Query Parameters:
    - page: Page number (default 1)
    - page_size: Trades per page (default 10, max 100)
    - sort_by: Sort field (entry_time, symbol, pnl, status)
    - sort_order: asc or desc
    - symbol_filter: Filter by symbol (e.g., BTCUSDT)
    - status_filter: CLOSED, OPEN, or ALL
    - min_pnl: Minimum PnL filter
    - max_pnl: Maximum PnL filter
    """
    user_id = current_user.id
    
    # Validate parameters
    page = max(1, page)
    page_size = min(max(1, page_size), 100)  # Max 100 per page
    sort_order = "desc" if sort_order.lower() == "desc" else "asc"
    
    # Build query
    query = db.query(Trade).filter(Trade.user_id == user_id)
    
    # Apply status filter
    if status_filter and status_filter.upper() != "ALL":
        query = query.filter(Trade.status == status_filter.upper())
    
    # Apply symbol filter
    if symbol_filter:
        query = query.filter(Trade.symbol == symbol_filter.upper())
    
    # Apply PnL filters
    if min_pnl is not None:
        query = query.filter(Trade.pnl >= min_pnl)
    if max_pnl is not None:
        query = query.filter(Trade.pnl <= max_pnl)
    
    # Apply sorting
    if sort_by == "symbol":
        sort_column = Trade.symbol
    elif sort_by == "pnl":
        sort_column = Trade.pnl
    elif sort_by == "status":
        sort_column = Trade.status
    else:  # Default to entry_time, but prefer exit_time if available (for closed trades)
        # For trades, we want to sort by exit_time (when trade closed) if available,
        # otherwise by entry_time (when trade opened)
        # This ensures most recent closed trades appear first
        sort_column = Trade.exit_time
    
    if sort_order == "desc":
        query = query.order_by(sort_column.desc().nullslast())
    else:
        query = query.order_by(sort_column.asc().nullsfirst())
    
    # Calculate pagination
    total_trades = query.count()
    total_pages = (total_trades + page_size - 1) // page_size
    
    # Apply pagination
    offset = (page - 1) * page_size
    trades = query.offset(offset).limit(page_size).all()
    
    # Format response
    trades_response = []
    for trade in trades:
        bot_name = None
        if trade.bot_id:
            bot = db.query(Bot).filter(Bot.id == trade.bot_id).first()
            if bot:
                bot_name = bot.name
        
        pnl_percent = (trade.pnl_percent or 0) if trade.pnl_percent is not None else 0
        
        trades_response.append({
            "id": str(trade.id),
            "symbol": trade.symbol,
            "side": trade.side,
            "entry_price": float(trade.entry_price),
            "exit_price": float(trade.exit_price) if trade.exit_price else None,
            "quantity": float(trade.quantity),
            "pnl": float(trade.pnl) if trade.pnl else 0,
            "pnl_percent": float(pnl_percent),
            "status": trade.status,
            "strategy": trade.strategy,
            "bot_name": bot_name,
            "entry_time": trade.entry_time.isoformat(),
            "exit_time": trade.exit_time.isoformat() if trade.exit_time else None,
            "duration_minutes": (trade.exit_time - trade.entry_time).total_seconds() / 60 if trade.exit_time else None
        })
    
    return {
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_trades": total_trades,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        },
        "filters": {
            "status": status_filter,
            "symbol": symbol_filter,
            "min_pnl": min_pnl,
            "max_pnl": max_pnl
        },
        "sorting": {
            "sort_by": sort_by,
            "sort_order": sort_order
        },
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
