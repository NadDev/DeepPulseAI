from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.database_models import RiskEvent

router = APIRouter(prefix="/api", tags=["risk"])

@router.get("/risk-events")
async def get_risk_events(db: Session = Depends(get_db)):
    """Get risk events and alerts"""
    events = db.query(RiskEvent).order_by(RiskEvent.created_at.desc()).limit(10).all()
    
    return {
        "events": [
            {
                "id": e.id,
                "event_type": e.event_type,
                "description": e.description,
                "level": e.level,
                "created_at": e.created_at
            }
            for e in events
        ]
    }

@router.get("/risk-summary")
async def get_risk_summary(db: Session = Depends(get_db)):
    """Get overall risk summary"""
    from app.models.database_models import Portfolio
    
    portfolio = db.query(Portfolio).first()
    if not portfolio:
        return {
            "max_drawdown": 0,
            "daily_risk": 0,
            "position_count": 0,
            "leverage_ratio": 1.0,
            "risk_score": 0
        }
    
    return {
        "max_drawdown": portfolio.max_drawdown or 0,
        "daily_risk": portfolio.daily_pnl or 0,
        "position_count": 0,
        "leverage_ratio": 1.0,
        "risk_score": abs(portfolio.max_drawdown or 0) * 10
    }
