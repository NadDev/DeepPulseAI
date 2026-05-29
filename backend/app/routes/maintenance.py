"""
Database maintenance routes
- Storage statistics
- Manual trigger cleanup
- Retention policy management
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.database import get_db
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/maintenance", tags=["maintenance"])

# ============================================================================
# STORAGE STATISTICS ENDPOINTS
# ============================================================================

@router.get("/storage/stats")
async def get_storage_stats(db: Session = Depends(get_db)):
    """
    Get detailed storage statistics for all tables
    Shows: size, row count, indexes, last vacuum
    """
    try:
        result = db.execute(text("SELECT * FROM get_database_storage_stats()"))
        stats = []
        for row in result:
            stats.append({
                "table": row[0],
                "size_mb": float(row[1]) if row[1] else 0,
                "row_count": row[2],
                "index_size_mb": float(row[3]) if row[3] else 0,
                "last_vacuum": row[4],
                "last_autovacuum": row[5]
            })
        
        return {
            "status": "✅ OK",
            "timestamp": datetime.utcnow().isoformat(),
            "tables": stats
        }
    except Exception as e:
        logger.error(f"❌ Storage stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/storage/total")
async def get_total_storage(db: Session = Depends(get_db)):
    """Get total database size summary"""
    try:
        result = db.execute(text("SELECT * FROM get_total_database_size()"))
        row = result.fetchone()
        
        return {
            "status": "✅ OK",
            "database": row[0],
            "total_size_mb": float(row[1]) if row[1] else 0,
            "tables_size_mb": float(row[2]) if row[2] else 0,
            "indexes_size_mb": float(row[3]) if row[3] else 0,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"❌ Total storage error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# CLEANUP ENDPOINTS
# ============================================================================

@router.post("/cleanup/run")
async def run_cleanup(db: Session = Depends(get_db), mode: str = "normal"):
    """
    Manually trigger database cleanup
    
    Modes:
    - normal: Standard cleanup (keeps 90 days crypto data, 30 days logs)
    - aggressive: Aggressive cleanup (keeps 30 days crypto data, 7 days logs)
    """
    try:
        logger.warning(f"🧹 Starting {mode} database cleanup...")
        
        result = db.execute(text("SELECT * FROM cleanup_old_data()"))
        cleanup_results = []
        total_rows_deleted = 0
        total_space_freed = 0
        
        for row in result:
            table, rows, space, status = row
            cleanup_results.append({
                "table": table,
                "rows_deleted": rows,
                "space_freed_mb": float(space) if space else 0,
                "status": status
            })
            total_rows_deleted += rows
            total_space_freed += float(space) if space else 0
        
        logger.info(f"✅ Cleanup complete: {total_rows_deleted:,} rows deleted, {total_space_freed:.1f} MB freed")
        
        return {
            "status": "✅ CLEANUP COMPLETE",
            "mode": mode,
            "timestamp": datetime.utcnow().isoformat(),
            "total_rows_deleted": total_rows_deleted,
            "total_space_freed_mb": total_space_freed,
            "details": cleanup_results
        }
    except Exception as e:
        logger.error(f"❌ Cleanup error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cleanup/status")
async def cleanup_status(db: Session = Depends(get_db)):
    """Get last cleanup status and policies"""
    try:
        result = db.execute(text("""
            SELECT 
                table_name,
                retention_days,
                enabled,
                last_cleanup,
                cleanup_frequency_hours
            FROM data_retention_policies
            ORDER BY table_name
        """))
        
        policies = []
        for row in result:
            table, retention, enabled, last_cleanup, freq = row
            policies.append({
                "table": table,
                "retention_days": retention,
                "enabled": enabled,
                "last_cleanup": last_cleanup.isoformat() if last_cleanup else None,
                "frequency_hours": freq
            })
        
        return {
            "status": "✅ OK",
            "timestamp": datetime.utcnow().isoformat(),
            "policies": policies
        }
    except Exception as e:
        logger.error(f"❌ Status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# POLICY MANAGEMENT ENDPOINTS
# ============================================================================

@router.post("/retention-policy/update")
async def update_retention_policy(
    db: Session = Depends(get_db),
    table_name: str = None,
    retention_days: int = None,
    enabled: bool = None
):
    """
    Update a retention policy
    
    Example:
        POST /api/maintenance/retention-policy/update
        ?table_name=crypto_market_data&retention_days=60&enabled=true
    """
    try:
        if not table_name or retention_days is None:
            raise HTTPException(
                status_code=400,
                detail="table_name and retention_days are required"
            )
        
        # Build update query
        query_parts = []
        if retention_days is not None:
            query_parts.append(f"retention_days = {retention_days}")
        if enabled is not None:
            query_parts.append(f"enabled = {str(enabled).lower()}")
        
        query_parts.append("updated_at = NOW()")
        
        query = text(f"""
            UPDATE data_retention_policies 
            SET {', '.join(query_parts)}
            WHERE table_name = :table_name
        """)
        
        db.execute(query, {"table_name": table_name})
        db.commit()
        
        logger.info(f"✅ Updated retention policy for {table_name}")
        
        return {
            "status": "✅ POLICY UPDATED",
            "table": table_name,
            "retention_days": retention_days,
            "enabled": enabled,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Policy update error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# ANALYSIS ENDPOINTS
# ============================================================================

@router.get("/data-age/analysis")
async def data_age_analysis(db: Session = Depends(get_db)):
    """Show age of oldest/newest data in key tables"""
    try:
        analysis = {}
        
        # Crypto market data
        try:
            result = db.execute(text("""
                SELECT 
                    COUNT(*) as row_count,
                    MIN(TO_TIMESTAMP(timestamp/1000.0)) as oldest,
                    MAX(TO_TIMESTAMP(timestamp/1000.0)) as newest
                FROM crypto_market_data
            """))
            row = result.fetchone()
            if row[0] > 0:
                analysis["crypto_market_data"] = {
                    "row_count": row[0],
                    "oldest": row[1].isoformat() if row[1] else None,
                    "newest": row[2].isoformat() if row[2] else None,
                    "age_days": (datetime.utcnow() - row[1]).days if row[1] else 0
                }
        except:
            pass
        
        # AI decisions
        try:
            result = db.execute(text("""
                SELECT 
                    COUNT(*) as row_count,
                    MIN(created_at) as oldest,
                    MAX(created_at) as newest
                FROM ai_decisions
            """))
            row = result.fetchone()
            if row[0] > 0:
                analysis["ai_decisions"] = {
                    "row_count": row[0],
                    "oldest": row[1].isoformat() if row[1] else None,
                    "newest": row[2].isoformat() if row[2] else None,
                    "age_days": (datetime.utcnow() - row[1]).days if row[1] else None
                }
        except:
            pass
        
        # Trades
        try:
            result = db.execute(text("""
                SELECT 
                    COUNT(*) as row_count,
                    SUM(CASE WHEN status IN ('CLOSED', 'CANCELLED') THEN 1 ELSE 0 END) as closed_trades,
                    MIN(created_at) as oldest,
                    MAX(created_at) as newest
                FROM trades
            """))
            row = result.fetchone()
            if row[0] > 0:
                analysis["trades"] = {
                    "total_row_count": row[0],
                    "closed_count": row[1],
                    "oldest": row[2].isoformat() if row[2] else None,
                    "newest": row[3].isoformat() if row[3] else None,
                    "age_days": (datetime.utcnow() - row[2]).days if row[2] else None
                }
        except:
            pass
        
        return {
            "status": "✅ OK",
            "timestamp": datetime.utcnow().isoformat(),
            "analysis": analysis
        }
    except Exception as e:
        logger.error(f"❌ Analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# EMERGENCY PROCEDURES
# ============================================================================

@router.post("/emergency/aggressive-cleanup")
async def emergency_cleanup(db: Session = Depends(get_db)):
    """
    ⚠️  EMERGENCY PROCEDURE - Aggressive cleanup
    
    Deletes:
    - Crypto data older than 30 days
    - AI decisions older than 7 days
    - Bot metrics older than 30 days
    - All test/demo data
    
    USE ONLY if database is critically full!
    """
    logger.warning("🚨 EMERGENCY AGGRESSIVE CLEANUP INITIATED")
    
    try:
        db.execute(text("DELETE FROM crypto_market_data WHERE timestamp < EXTRACT(EPOCH FROM (NOW() - INTERVAL '30 days')) * 1000"))
        db.execute(text("DELETE FROM ai_decisions WHERE created_at < NOW() - INTERVAL '7 days'"))
        db.execute(text("DELETE FROM bot_metrics WHERE recorded_at < NOW() - INTERVAL '30 days'"))
        db.execute(text("DELETE FROM risk_events WHERE created_at < NOW() - INTERVAL '7 days'"))
        db.execute(text("VACUUM FULL ANALYZE"))
        db.commit()
        
        logger.warning("🚨 EMERGENCY CLEANUP COMPLETE")
        
        return {
            "status": "✅ EMERGENCY CLEANUP COMPLETE",
            "warning": "Aggressive data retention applied",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Emergency cleanup error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
