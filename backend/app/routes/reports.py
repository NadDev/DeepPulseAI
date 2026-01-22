from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.database_models import Bot, Trade, StrategyPerformance, Portfolio
from sqlalchemy import func, desc
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/reports", tags=["reports"])

@router.get("/dashboard")
async def get_dashboard_report(db: Session = Depends(get_db)):
    """Get dashboard summary report"""
    portfolio = db.query(Portfolio).first()
    bots = db.query(Bot).all()
    
    # Calculate totals
    total_bots = len(bots)
    active_bots = len([b for b in bots if b.status == "ACTIVE"])
    total_trades = db.query(Trade).count()
    
    # Calculate overall metrics
    closed_trades = db.query(Trade).filter(Trade.status == "CLOSED").all()
    total_pnl = sum([t.pnl or 0 for t in closed_trades])
    winning_trades = len([t for t in closed_trades if t.pnl and t.pnl > 0])
    
    return {
        "portfolio_value": portfolio.total_value if portfolio else 0,
        "total_bots": total_bots,
        "active_bots": active_bots,
        "total_trades": total_trades,
        "total_pnl": total_pnl,
        "win_rate": (winning_trades / len(closed_trades) * 100) if closed_trades else 0,
        "last_updated": datetime.utcnow().isoformat(),
    }

@router.get("/equity-curve")
async def get_equity_curve(days: int = 30, db: Session = Depends(get_db)):
    """Get equity curve data for charts"""
    # In a real app, this would query a PortfolioHistory table
    # For now, we generate realistic data based on current portfolio value
    
    portfolio = db.query(Portfolio).first()
    current_value = portfolio.total_value if portfolio else 100000
    
    data = []
    import random
    
    # Generate data points working backwards
    value = current_value
    now = datetime.utcnow()
    
    for i in range(days):
        date = now - timedelta(days=i)
        # Random daily change between -2% and +2.5%
        change_pct = random.uniform(-0.02, 0.025)
        
        data.append({
            "date": date.strftime("%Y-%m-%d"),
            "value": round(value, 2),
            "pnl": round(value * change_pct, 2)
        })
        
        # Previous day's value
        value = value / (1 + change_pct)
    
    return list(reversed(data))

@router.get("/trades")
async def get_trades_report(
    limit: int = 50,
    days: int = 30,
    strategy: str = None,
    symbol: str = None,
    market_context: str = None,
    min_pnl: float = None,
    max_pnl: float = None,
    status: str = None,
    db: Session = Depends(get_db)
):
    """
    Get detailed trades report with advanced filtering
    
    Query params:
    - limit: Max trades to return (default 50)
    - days: Filter trades from last N days (default 30)
    - strategy: Filter by strategy name (e.g., "GRID_TRADING", "DCA")
    - symbol: Filter by symbol (e.g., "BTCUSDT")
    - market_context: Filter by market context (e.g., "STRONG_BULLISH")
    - min_pnl: Filter by minimum P&L
    - max_pnl: Filter by maximum P&L
    - status: Filter by status (OPEN, CLOSED, CLOSING)
    """
    since = datetime.utcnow() - timedelta(days=days)
    
    query = db.query(Trade).filter(
        Trade.entry_time >= since
    )
    
    # Apply filters
    if strategy:
        query = query.filter(Trade.strategy == strategy)
    
    if symbol:
        query = query.filter(Trade.symbol == symbol.upper())
    
    if market_context:
        query = query.filter(Trade.market_context == market_context)
    
    if status:
        query = query.filter(Trade.status == status.upper())
    
    if min_pnl is not None:
        query = query.filter(Trade.pnl >= min_pnl)
    
    if max_pnl is not None:
        query = query.filter(Trade.pnl <= max_pnl)
    
    trades = query.order_by(desc(Trade.entry_time)).limit(limit).all()
    
    closed_trades = [t for t in trades if t.status == "CLOSED"]
    total_pnl = sum([t.pnl or 0 for t in closed_trades])
    winning = len([t for t in closed_trades if t.pnl and t.pnl > 0])
    
    # Group stats by market context
    context_stats = {}
    for trade in closed_trades:
        context = trade.market_context or "UNKNOWN"
        if context not in context_stats:
            context_stats[context] = {
                "count": 0,
                "winning": 0,
                "total_pnl": 0,
                "avg_pnl": 0
            }
        context_stats[context]["count"] += 1
        if trade.pnl and trade.pnl > 0:
            context_stats[context]["winning"] += 1
        context_stats[context]["total_pnl"] += trade.pnl or 0
    
    # Calculate averages
    for context in context_stats:
        if context_stats[context]["count"] > 0:
            context_stats[context]["avg_pnl"] = context_stats[context]["total_pnl"] / context_stats[context]["count"]
            context_stats[context]["win_rate"] = (context_stats[context]["winning"] / context_stats[context]["count"]) * 100
    
    return {
        "total_trades": len(trades),
        "closed_trades": len(closed_trades),
        "open_trades": len([t for t in trades if t.status == "OPEN"]),
        "total_pnl": total_pnl,
        "win_rate": (winning / len(closed_trades) * 100) if closed_trades else 0,
        "average_pnl": (total_pnl / len(closed_trades)) if closed_trades else 0,
        "context_breakdown": context_stats,  # NEW: Market context breakdown
        "trades": [
            {
                "id": str(trade.id),
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
                "market_context": trade.market_context,  # NEW: Market context at entry
                "market_context_confidence": trade.market_context_confidence,  # NEW: Context confidence
                "stop_loss_price": trade.stop_loss_price,
                "take_profit_price": trade.take_profit_price,
                "trade_phase": trade.trade_phase,
            }
            for trade in trades
        ],
        "period": {
            "start": since.isoformat(),
            "end": datetime.utcnow().isoformat(),
            "days": days
        },
        "filters_applied": {
            "strategy": strategy,
            "symbol": symbol,
            "market_context": market_context,
            "status": status,
            "pnl_range": [min_pnl, max_pnl] if min_pnl is not None or max_pnl is not None else None
        }
    }

@router.get("/trades/context-performance")
async def get_context_performance(
    days: int = 30,
    db: Session = Depends(get_db)
):
    """
    Get strategy performance broken down by market context
    Shows win rate and P&L for each strategy in each market condition
    """
    since = datetime.utcnow() - timedelta(days=days)
    
    all_trades = db.query(Trade).filter(
        Trade.entry_time >= since,
        Trade.status == "CLOSED"
    ).all()
    
    # Create matrix: strategy x context
    performance_matrix = {}
    
    for trade in all_trades:
        strategy = trade.strategy or "UNKNOWN"
        context = trade.market_context or "UNKNOWN"
        key = f"{strategy}|{context}"
        
        if key not in performance_matrix:
            performance_matrix[key] = {
                "strategy": strategy,
                "market_context": context,
                "trades": 0,
                "wins": 0,
                "losses": 0,
                "total_pnl": 0,
                "best_pnl": None,
                "worst_pnl": None
            }
        
        performance_matrix[key]["trades"] += 1
        
        if trade.pnl and trade.pnl > 0:
            performance_matrix[key]["wins"] += 1
        elif trade.pnl and trade.pnl < 0:
            performance_matrix[key]["losses"] += 1
        
        performance_matrix[key]["total_pnl"] += trade.pnl or 0
        
        if performance_matrix[key]["best_pnl"] is None or trade.pnl > performance_matrix[key]["best_pnl"]:
            performance_matrix[key]["best_pnl"] = trade.pnl
        
        if performance_matrix[key]["worst_pnl"] is None or trade.pnl < performance_matrix[key]["worst_pnl"]:
            performance_matrix[key]["worst_pnl"] = trade.pnl
    
    # Calculate metrics for each combo
    result = []
    for key, stats in performance_matrix.items():
        if stats["trades"] > 0:
            win_rate = (stats["wins"] / stats["trades"]) * 100
            avg_pnl = stats["total_pnl"] / stats["trades"]
        else:
            win_rate = 0
            avg_pnl = 0
        
        result.append({
            "strategy": stats["strategy"],
            "market_context": stats["market_context"],
            "total_trades": stats["trades"],
            "winning_trades": stats["wins"],
            "losing_trades": stats["losses"],
            "win_rate": win_rate,
            "total_pnl": stats["total_pnl"],
            "avg_pnl": avg_pnl,
            "best_trade": stats["best_pnl"],
            "worst_trade": stats["worst_pnl"]
        })
    
    # Sort by strategy, then context
    result = sorted(result, key=lambda x: (x["strategy"], x["market_context"]))
    
    return {
        "performance_matrix": result,
        "total_combos": len(result),
        "period": {
            "start": since.isoformat(),
            "end": datetime.utcnow().isoformat(),
            "days": days
        }
    }

@router.get("/strategies")
async def get_strategies_report(db: Session = Depends(get_db)):
    """Get strategies comparison report"""
    strategies = db.query(StrategyPerformance).all()
    
    # Group by strategy
    strategy_stats = {}
    for strat in strategies:
        if strat.strategy_name not in strategy_stats:
            strategy_stats[strat.strategy_name] = {
                "total_trades": 0,
                "winning_trades": 0,
                "total_pnl": 0,
                "tests": 0,
            }
        
        strategy_stats[strat.strategy_name]["total_trades"] += strat.total_trades or 0
        strategy_stats[strat.strategy_name]["winning_trades"] += strat.winning_trades or 0
        strategy_stats[strat.strategy_name]["total_pnl"] += strat.profit_factor or 0
        strategy_stats[strat.strategy_name]["tests"] += 1
    
    result = []
    for name, stats in strategy_stats.items():
        result.append({
            "strategy": name,
            "total_trades": stats["total_trades"],
            "winning_trades": stats["winning_trades"],
            "win_rate": (stats["winning_trades"] / stats["total_trades"] * 100) if stats["total_trades"] > 0 else 0,
            "average_profit_factor": stats["total_pnl"] / stats["tests"] if stats["tests"] > 0 else 0,
            "backtest_count": stats["tests"],
        })
    
    return {
        "strategies": result,
        "total_strategies": len(result)
    }

@router.get("/performance")
async def get_performance_report(db: Session = Depends(get_db)):
    """Get overall performance metrics"""
    bots = db.query(Bot).all()
    all_trades = db.query(Trade).all()
    
    closed_trades = [t for t in all_trades if t.status == "CLOSED"]
    
    if not closed_trades:
        return {"error": "No closed trades found"}
    
    total_pnl = sum([t.pnl or 0 for t in closed_trades])
    winning_trades = len([t for t in closed_trades if t.pnl and t.pnl > 0])
    losing_trades = len([t for t in closed_trades if t.pnl and t.pnl < 0])
    
    winning_pnl = sum([t.pnl for t in closed_trades if t.pnl and t.pnl > 0])
    losing_pnl = sum([t.pnl for t in closed_trades if t.pnl and t.pnl < 0])
    
    return {
        "total_trades": len(closed_trades),
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "win_rate": (winning_trades / len(closed_trades) * 100),
        "total_pnl": total_pnl,
        "average_win": (winning_pnl / winning_trades) if winning_trades > 0 else 0,
        "average_loss": (losing_pnl / losing_trades) if losing_trades > 0 else 0,
        "profit_factor": (winning_pnl / abs(losing_pnl)) if losing_pnl != 0 else 0,
        "avg_trade_pnl": (total_pnl / len(closed_trades)),
        "best_trade": max([t.pnl for t in closed_trades if t.pnl]),
        "worst_trade": min([t.pnl for t in closed_trades if t.pnl]),
    }
