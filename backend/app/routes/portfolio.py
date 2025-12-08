from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.database_models import Portfolio, Trade
from sqlalchemy import desc
from datetime import datetime, timedelta

router = APIRouter(prefix="/api", tags=["portfolio"])

@router.get("/portfolio/summary")
async def get_portfolio_summary(db: Session = Depends(get_db)):
    """Get portfolio summary (KPIs)"""
    # Get portfolio (for demo, using first user)
    portfolio = db.query(Portfolio).first()
    
    if not portfolio:
        # Create demo portfolio if not exists
        portfolio = Portfolio(
            user_id="user_1",
            total_value=145230.50,
            cash_balance=45230.50,
            daily_pnl=2450.0,
            total_pnl=45230.50,
            win_rate=58.3,
            max_drawdown=-18.5
        )
        db.add(portfolio)
        db.commit()
    
    # Get recent trades
    recent_trades = db.query(Trade).order_by(desc(Trade.entry_time)).limit(5).all()
    
    return {
        "portfolio_value": portfolio.total_value,
        "cash_balance": portfolio.cash_balance,
        "daily_pnl": portfolio.daily_pnl,
        "total_pnl": portfolio.total_pnl,
        "win_rate": portfolio.win_rate,
        "max_drawdown": portfolio.max_drawdown,
        "recent_trades_count": len(recent_trades),
        "last_updated": portfolio.updated_at.isoformat()
    }

@router.get("/trades")
async def get_trades(
    limit: int = 20,
    offset: int = 0,
    status: str = None,
    db: Session = Depends(get_db)
):
    """Get trades with pagination and filtering"""
    query = db.query(Trade)
    
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
async def get_equity_curve(days: int = 30, db: Session = Depends(get_db)):
    """Get equity curve data for last N days"""
    portfolio = db.query(Portfolio).first()
    
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
