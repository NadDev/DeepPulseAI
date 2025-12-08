from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.database_models import Bot, Trade, StrategyPerformance
from sqlalchemy import desc
from datetime import datetime

router = APIRouter(prefix="/api/bots", tags=["bots"])

@router.get("/list")
async def get_bots(db: Session = Depends(get_db)):
    """Get all bots with their current status and metrics"""
    bots = db.query(Bot).all()
    
    result = []
    for bot in bots:
        # Get open trades count
        open_trades = db.query(Trade).filter(
            Trade.bot_id == bot.id,
            Trade.status == "OPEN"
        ).count()
        
        result.append({
            "id": bot.id,
            "name": bot.name,
            "strategy": bot.strategy,
            "status": bot.status,
            "is_live": bot.is_live,
            "total_trades": bot.total_trades,
            "win_rate": bot.win_rate,
            "total_pnl": bot.total_pnl,
            "max_drawdown": bot.max_drawdown,
            "open_trades": open_trades,
            "risk_percent": bot.risk_percent,
            "created_at": bot.created_at.isoformat() if bot.created_at else None,
            "updated_at": bot.updated_at.isoformat() if bot.updated_at else None,
        })
    
    return {"bots": result, "total": len(result)}

@router.get("/{bot_id}")
async def get_bot(bot_id: str, db: Session = Depends(get_db)):
    """Get specific bot details"""
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    # Get performance stats
    trades = db.query(Trade).filter(Trade.bot_id == bot.id).all()
    open_trades = [t for t in trades if t.status == "OPEN"]
    closed_trades = [t for t in trades if t.status == "CLOSED"]
    
    total_pnl = sum([t.pnl or 0 for t in closed_trades])
    
    return {
        "id": bot.id,
        "name": bot.name,
        "strategy": bot.strategy,
        "status": bot.status,
        "is_live": bot.is_live,
        "total_trades": len(trades),
        "open_trades": len(open_trades),
        "closed_trades": len(closed_trades),
        "win_rate": bot.win_rate,
        "total_pnl": total_pnl,
        "max_drawdown": bot.max_drawdown,
        "risk_percent": bot.risk_percent,
        "created_at": bot.created_at.isoformat() if bot.created_at else None,
        "updated_at": bot.updated_at.isoformat() if bot.updated_at else None,
    }

@router.post("/{bot_id}/start")
async def start_bot(bot_id: str, db: Session = Depends(get_db)):
    """Start a bot"""
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    bot.status = "ACTIVE"
    bot.updated_at = datetime.utcnow()
    db.commit()
    
    return {"message": f"Bot {bot.name} started", "status": "ACTIVE"}

@router.post("/{bot_id}/pause")
async def pause_bot(bot_id: str, db: Session = Depends(get_db)):
    """Pause a bot"""
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    bot.status = "PAUSED"
    bot.updated_at = datetime.utcnow()
    db.commit()
    
    return {"message": f"Bot {bot.name} paused", "status": "PAUSED"}

@router.post("/{bot_id}/stop")
async def stop_bot(bot_id: str, db: Session = Depends(get_db)):
    """Stop a bot"""
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    bot.status = "INACTIVE"
    bot.updated_at = datetime.utcnow()
    db.commit()
    
    return {"message": f"Bot {bot.name} stopped", "status": "INACTIVE"}

@router.get("/{bot_id}/performance")
async def get_bot_performance(bot_id: str, db: Session = Depends(get_db)):
    """Get bot performance metrics"""
    performance = db.query(StrategyPerformance).filter(
        StrategyPerformance.strategy_name == bot_id
    ).all()
    
    if not performance:
        raise HTTPException(status_code=404, detail="Performance data not found")
    
    latest = performance[-1] if performance else None
    
    return {
        "total_trades": latest.total_trades if latest else 0,
        "winning_trades": latest.winning_trades if latest else 0,
        "losing_trades": latest.losing_trades if latest else 0,
        "win_rate": latest.win_rate if latest else 0,
        "avg_win": latest.avg_win if latest else 0,
        "avg_loss": latest.avg_loss if latest else 0,
        "profit_factor": latest.profit_factor if latest else 0,
        "sharpe_ratio": latest.sharpe_ratio if latest else 0,
        "max_drawdown": latest.max_drawdown if latest else 0,
    }
