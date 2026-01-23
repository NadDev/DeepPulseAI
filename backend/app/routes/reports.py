from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.database_models import Bot, Trade, StrategyPerformance, Portfolio
from app.auth.supabase_auth import get_current_user, UserResponse
from sqlalchemy import func, desc
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reports", tags=["reports"])

@router.get("/dashboard")
async def get_dashboard_report(
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get dashboard summary report with comprehensive KPIs"""
    logger.info(f"📊 [DASHBOARD] Request from user: {current_user.id} | email: {current_user.email}")
    user_id = current_user.id
    
    portfolio = db.query(Portfolio).filter(Portfolio.user_id == user_id).first()
    bots = db.query(Bot).filter(Bot.user_id == user_id).all()
    
    # Calculate totals
    total_bots = len(bots)
    active_bots = len([b for b in bots if b.status == "ACTIVE"])
    total_trades = db.query(Trade).filter(Trade.user_id == user_id).count()
    
    # Calculate overall metrics
    closed_trades = db.query(Trade).filter(
        Trade.user_id == user_id,
        Trade.status == "CLOSED"
    ).all()
    total_pnl = sum([t.pnl or 0 for t in closed_trades])
    winning_trades = len([t for t in closed_trades if t.pnl and t.pnl > 0])
    losing_trades = len([t for t in closed_trades if t.pnl and t.pnl < 0])
    
    # Calculate advanced metrics
    winning_pnls = [t.pnl for t in closed_trades if t.pnl and t.pnl > 0]
    losing_pnls = [t.pnl for t in closed_trades if t.pnl and t.pnl < 0]
    
    average_win = sum(winning_pnls) / len(winning_pnls) if winning_pnls else 0
    average_loss = sum(losing_pnls) / len(losing_pnls) if losing_pnls else 0
    best_trade = max(winning_pnls) if winning_pnls else 0
    worst_trade = min(losing_pnls) if losing_pnls else 0
    avg_trade_pnl = total_pnl / len(closed_trades) if closed_trades else 0
    
    # Calculate profit factor (sum of wins / absolute sum of losses)
    sum_wins = sum(winning_pnls) if winning_pnls else 0
    sum_losses = abs(sum(losing_pnls)) if losing_pnls else 1
    profit_factor = sum_wins / sum_losses if sum_losses > 0 else 0
    
    return {
        "portfolio_value": portfolio.total_value if portfolio else 0,
        "total_bots": total_bots,
        "active_bots": active_bots,
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "total_pnl": total_pnl,
        "win_rate": (winning_trades / len(closed_trades) * 100) if closed_trades else 0,
        "profit_factor": profit_factor,
        "average_win": average_win,
        "average_loss": average_loss,
        "best_trade": best_trade,
        "worst_trade": worst_trade,
        "avg_trade_pnl": avg_trade_pnl,
        "last_updated": datetime.utcnow().isoformat(),
    }

@router.get("/equity-curve")
async def get_equity_curve(
    days: int = 30,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get equity curve data for charts"""
    user_id = current_user.id
    
    # In a real app, this would query a PortfolioHistory table
    # For now, we generate realistic data based on current portfolio value
    
    portfolio = db.query(Portfolio).filter(Portfolio.user_id == user_id).first()
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
    current_user: UserResponse = Depends(get_current_user),
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
    """    logger.info(f"📋 [TRADES] Request from user: {current_user.id} | days={days}")    user_id = current_user.user_id
    since = datetime.utcnow() - timedelta(days=days)
    
    query = db.query(Trade).filter(
        Trade.user_id == user_id,
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
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get strategy performance broken down by market context
    Shows win rate and P&L for each strategy in each market condition
    """
    user_id = current_user.id
    since = datetime.utcnow() - timedelta(days=days)
    
    all_trades = db.query(Trade).filter(
        Trade.user_id == user_id,
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
async def get_strategies_report(
    days: int = 30,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get strategies comparison report with market context breakdown
    Shows performance of each strategy globally and per market condition
    """
    logger.info(f"🎯 [STRATEGIES] Request from user: {current_user.id} | days={days}")
    user_id = current_user.id
    since = datetime.utcnow() - timedelta(days=days)
    
    # Get all trades for the period
    all_trades = db.query(Trade).filter(
        Trade.user_id == user_id,
        Trade.entry_time >= since,
        Trade.status == "CLOSED"
    ).all()
    
    if not all_trades:
        return {
            "strategies": [],
            "total_strategies": 0,
            "context_breakdown": {}
        }
    
    # Aggregate by strategy (global stats)
    strategy_global = {}
    strategy_by_context = {}
    
    for trade in all_trades:
        strategy = trade.strategy or "UNKNOWN"
        context = trade.market_context or "UNKNOWN"
        
        # Global strategy stats
        if strategy not in strategy_global:
            strategy_global[strategy] = {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "total_pnl": 0,
                "best_pnl": None,
                "worst_pnl": None
            }
        
        # By-context stats
        key = f"{strategy}|{context}"
        if key not in strategy_by_context:
            strategy_by_context[key] = {
                "strategy": strategy,
                "market_context": context,
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "total_pnl": 0,
                "best_pnl": None,
                "worst_pnl": None
            }
        
        # Update global stats
        strategy_global[strategy]["total_trades"] += 1
        if trade.pnl and trade.pnl > 0:
            strategy_global[strategy]["winning_trades"] += 1
        elif trade.pnl and trade.pnl < 0:
            strategy_global[strategy]["losing_trades"] += 1
        
        strategy_global[strategy]["total_pnl"] += trade.pnl or 0
        
        if strategy_global[strategy]["best_pnl"] is None or trade.pnl > strategy_global[strategy]["best_pnl"]:
            strategy_global[strategy]["best_pnl"] = trade.pnl
        
        if strategy_global[strategy]["worst_pnl"] is None or trade.pnl < strategy_global[strategy]["worst_pnl"]:
            strategy_global[strategy]["worst_pnl"] = trade.pnl
        
        # Update by-context stats
        strategy_by_context[key]["total_trades"] += 1
        if trade.pnl and trade.pnl > 0:
            strategy_by_context[key]["winning_trades"] += 1
        elif trade.pnl and trade.pnl < 0:
            strategy_by_context[key]["losing_trades"] += 1
        
        strategy_by_context[key]["total_pnl"] += trade.pnl or 0
        
        if strategy_by_context[key]["best_pnl"] is None or trade.pnl > strategy_by_context[key]["best_pnl"]:
            strategy_by_context[key]["best_pnl"] = trade.pnl
        
        if strategy_by_context[key]["worst_pnl"] is None or trade.pnl < strategy_by_context[key]["worst_pnl"]:
            strategy_by_context[key]["worst_pnl"] = trade.pnl
    
    # Build result with global stats
    result = []
    for strategy, stats in strategy_global.items():
        if stats["total_trades"] > 0:
            win_rate = (stats["winning_trades"] / stats["total_trades"]) * 100
            avg_pnl = stats["total_pnl"] / stats["total_trades"]
            profit_factor = 0
            
            # Calculate profit factor (total wins / abs(total losses))
            if stats["losing_trades"] > 0:
                total_wins = sum([t.pnl for t in all_trades if t.strategy == strategy and t.pnl and t.pnl > 0]) or 0
                total_losses = sum([abs(t.pnl) for t in all_trades if t.strategy == strategy and t.pnl and t.pnl < 0]) or 0
                if total_losses > 0:
                    profit_factor = total_wins / total_losses
        else:
            win_rate = 0
            avg_pnl = 0
            profit_factor = 0
        
        result.append({
            "strategy": strategy,
            "total_trades": stats["total_trades"],
            "winning_trades": stats["winning_trades"],
            "losing_trades": stats["losing_trades"],
            "win_rate": round(win_rate, 2),
            "total_pnl": round(stats["total_pnl"], 2),
            "avg_pnl": round(avg_pnl, 2),
            "best_trade": round(stats["best_pnl"], 2) if stats["best_pnl"] else None,
            "worst_trade": round(stats["worst_pnl"], 2) if stats["worst_pnl"] else None,
            "profit_factor": round(profit_factor, 2)
        })
    
    # Build context breakdown
    context_breakdown = {}
    for key, stats in strategy_by_context.items():
        strategy, context = key.split("|")
        
        if strategy not in context_breakdown:
            context_breakdown[strategy] = {}
        
        if stats["total_trades"] > 0:
            win_rate = (stats["winning_trades"] / stats["total_trades"]) * 100
            avg_pnl = stats["total_pnl"] / stats["total_trades"]
        else:
            win_rate = 0
            avg_pnl = 0
        
        context_breakdown[strategy][context] = {
            "total_trades": stats["total_trades"],
            "winning_trades": stats["winning_trades"],
            "losing_trades": stats["losing_trades"],
            "win_rate": round(win_rate, 2),
            "total_pnl": round(stats["total_pnl"], 2),
            "avg_pnl": round(avg_pnl, 2),
            "best_trade": round(stats["best_pnl"], 2) if stats["best_pnl"] else None,
            "worst_trade": round(stats["worst_pnl"], 2) if stats["worst_pnl"] else None
        }
    
    # Sort result by total trades descending
    result = sorted(result, key=lambda x: x["total_trades"], reverse=True)
    
    return {
        "strategies": result,
        "total_strategies": len(result),
        "context_breakdown": context_breakdown,  # NEW: Breakdown by market context
        "period": {
            "start": since.isoformat(),
            "end": datetime.utcnow().isoformat(),
            "days": days
        }
    }

@router.get("/strategies/{strategy_name}")
async def get_strategy_detail(
    strategy_name: str,
    days: int = 30,
    db: Session = Depends(get_db)
):
    """
    Get detailed performance for a specific strategy
    Including trades list and performance by market context
    """
    since = datetime.utcnow() - timedelta(days=days)
    
    # Get all trades for this strategy
    trades = db.query(Trade).filter(
        Trade.strategy == strategy_name,
        Trade.entry_time >= since,
        Trade.status == "CLOSED"
    ).order_by(desc(Trade.exit_time)).all()
    
    if not trades:
        return {
            "strategy": strategy_name,
            "total_trades": 0,
            "error": "No trades found for this strategy"
        }
    
    # Global stats
    winning = len([t for t in trades if t.pnl and t.pnl > 0])
    losing = len([t for t in trades if t.pnl and t.pnl < 0])
    total_pnl = sum([t.pnl or 0 for t in trades])
    
    winning_pnl = sum([t.pnl for t in trades if t.pnl and t.pnl > 0]) or 0
    losing_pnl = sum([abs(t.pnl) for t in trades if t.pnl and t.pnl < 0]) or 0
    
    profit_factor = (winning_pnl / losing_pnl) if losing_pnl > 0 else 0
    
    # By context
    context_stats = {}
    for trade in trades:
        context = trade.market_context or "UNKNOWN"
        if context not in context_stats:
            context_stats[context] = {
                "trades": 0,
                "wins": 0,
                "losses": 0,
                "total_pnl": 0,
                "best": None,
                "worst": None
            }
        
        context_stats[context]["trades"] += 1
        if trade.pnl and trade.pnl > 0:
            context_stats[context]["wins"] += 1
        elif trade.pnl and trade.pnl < 0:
            context_stats[context]["losses"] += 1
        
        context_stats[context]["total_pnl"] += trade.pnl or 0
        
        if context_stats[context]["best"] is None or trade.pnl > context_stats[context]["best"]:
            context_stats[context]["best"] = trade.pnl
        
        if context_stats[context]["worst"] is None or trade.pnl < context_stats[context]["worst"]:
            context_stats[context]["worst"] = trade.pnl
    
    # Format context stats
    context_breakdown = {}
    for context, stats in context_stats.items():
        win_rate = (stats["wins"] / stats["trades"] * 100) if stats["trades"] > 0 else 0
        context_breakdown[context] = {
            "trades": stats["trades"],
            "wins": stats["wins"],
            "losses": stats["losses"],
            "win_rate": round(win_rate, 2),
            "total_pnl": round(stats["total_pnl"], 2),
            "avg_pnl": round(stats["total_pnl"] / stats["trades"], 2) if stats["trades"] > 0 else 0,
            "best_trade": round(stats["best"], 2) if stats["best"] is not None else None,
            "worst_trade": round(stats["worst"], 2) if stats["worst"] is not None else None
        }
    
    return {
        "strategy": strategy_name,
        "total_trades": len(trades),
        "winning_trades": winning,
        "losing_trades": losing,
        "win_rate": round((winning / len(trades) * 100), 2) if trades else 0,
        "total_pnl": round(total_pnl, 2),
        "avg_pnl": round(total_pnl / len(trades), 2) if trades else 0,
        "profit_factor": round(profit_factor, 2),
        "best_trade": round(max([t.pnl for t in trades if t.pnl]), 2),
        "worst_trade": round(min([t.pnl for t in trades if t.pnl]), 2),
        "context_performance": context_breakdown,
        "recent_trades": [
            {
                "id": str(t.id),
                "symbol": t.symbol,
                "entry_price": t.entry_price,
                "exit_price": t.exit_price,
                "pnl": round(t.pnl, 2) if t.pnl else None,
                "pnl_percent": round(t.pnl_percent, 2) if t.pnl_percent else None,
                "market_context": t.market_context,
                "exit_time": t.exit_time.isoformat() if t.exit_time else None
            }
            for t in trades[:10]  # Last 10 trades
        ]
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

@router.get("/drawdown-history")
async def get_drawdown_history(days: int = 30, db: Session = Depends(get_db)):
    """Get drawdown over time for charts"""
    # Calculate drawdown from equity curve
    portfolio = db.query(Portfolio).first()
    current_value = portfolio.total_value if portfolio else 100000
    
    data = []
    import random
    
    # Generate realistic drawdown data
    value = current_value
    peak = current_value
    now = datetime.utcnow()
    
    for i in range(days, 0, -1):
        date = (now - timedelta(days=i)).date()
        
        # Simulate daily changes
        daily_change = random.uniform(-0.02, 0.03)  # -2% to +3%
        value = value * (1 + daily_change)
        
        # Update peak if new high
        if value > peak:
            peak = value
        
        # Calculate drawdown percentage
        drawdown_pct = ((value - peak) / peak * 100) if peak > 0 else 0
        
        data.append({
            "date": date.isoformat(),
            "drawdown": max(0, abs(drawdown_pct)),
            "value": value,
            "recovery_days": 0  # Would need actual recovery logic
        })
    
    return data
