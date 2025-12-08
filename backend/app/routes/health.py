from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.database_models import Portfolio, Trade
from sqlalchemy import desc
from datetime import datetime, timedelta

router = APIRouter(prefix="/api", tags=["health"])

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "CRBot API"
    }

@router.get("/ready")
async def ready_check(db: Session = Depends(get_db)):
    """Readiness check with database connection"""
    try:
        db.execute("SELECT 1")
        return {"ready": True, "database": "connected"}
    except Exception as e:
        return {"ready": False, "error": str(e)}
