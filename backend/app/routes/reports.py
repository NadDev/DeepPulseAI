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

@router.get("/trades")
async def get_trades_report(
    limit: int = 50,
    days: int = 30,
    db: Session = Depends(get_db)
):
    """Get detailed trades report"""
    since = datetime.utcnow() - timedelta(days=days)
    
    trades = db.query(Trade).filter(
        Trade.entry_time >= since
    ).order_by(desc(Trade.entry_time)).limit(limit).all()
    
    closed_trades = [t for t in trades if t.status == "CLOSED"]
    total_pnl = sum([t.pnl or 0 for t in closed_trades])
    winning = len([t for t in closed_trades if t.pnl and t.pnl > 0])
    
    return {
        "total_trades": len(trades),
        "closed_trades": len(closed_trades),
        "open_trades": len([t for t in trades if t.status == "OPEN"]),
        "total_pnl": total_pnl,
        "win_rate": (winning / len(closed_trades) * 100) if closed_trades else 0,
        "average_pnl": (total_pnl / len(closed_trades)) if closed_trades else 0,
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
                "entry_time": trade.entry_time.isoformat() if trade.entry_time else None,
                "exit_time": trade.exit_time.isoformat() if trade.exit_time else None,
            }
            for trade in trades
        ],
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
