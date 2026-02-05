"""
Admin endpoints for system management and maintenance.

Protected by admin-only access.
"""

import asyncio
import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db.database import get_db
from app.auth.local_auth import get_current_user, UserResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/bootstrap")
async def force_bootstrap_crypto_data(
    background_tasks: BackgroundTasks,
    cryptos: int = 200,
    days: int = 730,
    force: bool = True,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Force bootstrap of crypto market data from Binance.
    
    Runs in background to avoid timeout.
    
    Query params:
    - cryptos: Number of top cryptos (default: 200)
    - days: Days of history (default: 730)
    - force: Force full refetch (default: true)
    """
    # TODO: Implement proper admin role system in database
    # For now, any authenticated user can trigger bootstrap
    logger.info(f"📌 Bootstrap requested by {current_user.email}")
    logger.info(f"   Config: cryptos={cryptos}, days={days}, force={force}")
    
    # Add task to background
    background_tasks.add_task(
        _run_bootstrap_task,
        cryptos=cryptos,
        days=days,
        force=force
    )
    
    return {
        "status": "bootstrap_started",
        "message": f"Bootstrap started in background (fetching {cryptos} cryptos with {days} days history)",
        "requested_by": current_user.email
    }


async def _run_bootstrap_task(cryptos: int = 200, days: int = 730, force: bool = True):
    """Background task to run bootstrap."""
    try:
        logger.info("=" * 60)
        logger.info("🚀 BACKGROUND BOOTSTRAP STARTED")
        logger.info("=" * 60)
        
        from app.services.market_data_bootstrapper import MarketDataBootstrapper
        from app.db.database import SessionLocal
        
        async with MarketDataBootstrapper(SessionLocal) as bootstrapper:
            await bootstrapper.run(
                crypto_count=cryptos,
                days=days,
                timeframes=["1d", "4h", "1h"],
                force_full=force
            )
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("✅ BACKGROUND BOOTSTRAP COMPLETED!")
        logger.info("=" * 60)
        
        # After bootstrap, generate recommendations for all users
        logger.info("")
        logger.info("=" * 60)
        logger.info("🔄 STARTING RECOMMENDATION GENERATION...")
        logger.info("=" * 60)
        await _generate_recommendations_for_all_users()
        
    except Exception as e:
        logger.error(f"❌ Bootstrap task failed: {e}", exc_info=True)


@router.get("/bootstrap-status")
async def get_bootstrap_status(
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get crypto market data statistics."""
    try:
        result = db.execute(text("""
            SELECT 
                timeframe,
                COUNT(*) as total_candles,
                COUNT(DISTINCT symbol) as unique_symbols,
                ROUND(COUNT(*) / COUNT(DISTINCT symbol)::float, 1) as avg_candles_per_symbol,
                MIN(timestamp) as oldest_candle,
                MAX(timestamp) as newest_candle
            FROM crypto_market_data
            GROUP BY timeframe
            ORDER BY timeframe
        """))
        
        timeframe_stats = []
        for row in result:
            timeframe_stats.append({
                "timeframe": row.timeframe,
                "total_candles": row.total_candles,
                "unique_symbols": row.unique_symbols,
                "avg_candles_per_symbol": row.avg_candles_per_symbol,
                "oldest_candle_ms": row.oldest_candle,
                "newest_candle_ms": row.newest_candle
            })
        
        # Total stats
        total_result = db.execute(text("""
            SELECT 
                COUNT(*) as total_candles,
                COUNT(DISTINCT symbol) as unique_symbols,
                ROUND(COUNT(*) / COUNT(DISTINCT symbol)::float, 1) as avg_candles_per_symbol
            FROM crypto_market_data
        """))
        
        total_row = total_result.fetchone()
        
        return {
            "total_candles": total_row.total_candles,
            "unique_symbols": total_row.unique_symbols,
            "avg_candles_per_symbol": total_row.avg_candles_per_symbol,
            "by_timeframe": timeframe_stats,
            "expected_for_200_cryptos_2years": {
                "description": "200 cryptos × 730 days × 3 timeframes (1d/4h/1h)",
                "1d": 200 * 730,
                "4h": 200 * 730 * 6,
                "1h": 200 * 730 * 24,
                "total": 200 * 730 * (1 + 6 + 24)
            }
        }
    except Exception as e:
        logger.error(f"Error getting bootstrap status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-recommendations")
async def generate_recommendations_now(
    background_tasks: BackgroundTasks,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Trigger manual recommendation generation for all users.
    
    This is called automatically after bootstrap, but can also be triggered manually.
    """
    logger.info(f"📌 Manual recommendation generation requested by {current_user.email}")
    
    background_tasks.add_task(_generate_recommendations_for_all_users)
    
    return {
        "status": "recommendation_generation_started",
        "message": "Recommendation generation triggered for all users",
        "requested_by": current_user.email
    }


async def _generate_recommendations_for_all_users():
    """Background task to generate recommendations for all users."""
    try:
        from app.services.watchlist_recommendation_engine import get_recommendation_engine
        from app.db.database import SessionLocal
        
        db = SessionLocal()
        
        try:
            # Get all active users
            result = db.execute(text("""
                SELECT DISTINCT user_id FROM watchlist_items WHERE is_active = true
                UNION
                SELECT DISTINCT user_id FROM bots WHERE status IN ('RUNNING', 'PAUSED')
            """))
            
            user_ids = [row[0] for row in result.fetchall()]
            logger.info(f"📊 [GEN-REC] Found {len(user_ids)} active users for recommendation generation")
            
            if not user_ids:
                logger.warning("⚠️ [GEN-REC] No active users found - skipping recommendation generation")
                return
            
            engine = get_recommendation_engine(SessionLocal)
            total_saved = 0
            
            for user_id in user_ids:
                try:
                    logger.info(f"🔄 [GEN-REC] Processing user {user_id[:8]}...")
                    
                    # Generate recommendations
                    recommendations = engine.generate_recommendations(
                        user_id=user_id,
                        top_n=50,
                        min_score=0
                    )
                    
                    logger.info(f"📝 [GEN-REC] Generated {len(recommendations)} recommendations for {user_id[:8]}")
                    
                    # Filter to only ADD and REMOVE actions
                    actionable = [r for r in recommendations if r.action != "HOLD"]
                    
                    if actionable:
                        logger.info(f"✅ [GEN-REC] {len(actionable)} actionable recommendations for {user_id[:8]}")
                        
                        # Add AI reasoning
                        actionable_with_reasoning = await engine.generate_reasoning_batch(
                            actionable[:20]  # Limit to top 20 for cost control
                        )
                        
                        # Save to database
                        user_db = SessionLocal()
                        try:
                            saved = engine.save_recommendations(user_db, user_id, actionable_with_reasoning)
                            total_saved += saved
                            user_db.commit()
                            logger.info(f"💾 [GEN-REC] Saved {saved} recommendations for {user_id[:8]}")
                        except Exception as save_err:
                            user_db.rollback()
                            logger.error(f"❌ [GEN-REC] Error saving recommendations: {save_err}")
                        finally:
                            user_db.close()
                    else:
                        logger.info(f"ℹ️ [GEN-REC] No actionable recommendations for {user_id[:8]}")
                    
                except Exception as e:
                    logger.error(f"❌ [GEN-REC] Error for user {user_id[:8]}: {e}", exc_info=True)
                    continue
            
            logger.info("")
            logger.info("=" * 60)
            logger.info(f"✅ [GEN-REC] COMPLETE! Generated {total_saved} total recommendations for {len(user_ids)} users")
            logger.info("=" * 60)
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ [GEN-REC] Recommendation generation failed: {e}", exc_info=True)
