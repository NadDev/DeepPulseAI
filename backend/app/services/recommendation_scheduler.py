"""
Daily Recommendation Scheduler - APScheduler for daily crypto recommendations
Feature: RecommendationCrypto

Runs daily at 8:00 AM UTC:
1. Generates recommendations for all users
2. Calls WatchlistRecommendationEngine.generate_recommendations()
3. Adds DeepSeek reasoning
4. Saves to watchlist_recommendations table
"""

import logging
import asyncio
from datetime import datetime
from typing import Optional, List
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class DailyRecommendationScheduler:
    """
    Schedules and runs daily crypto recommendation generation.
    
    Uses APScheduler for reliable scheduling.
    Generates recommendations for all active users at 8:00 AM UTC.
    """
    
    def __init__(self, db_session_factory):
        self.db_session_factory = db_session_factory
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.running = False
        
        # Stats
        self.last_run: Optional[datetime] = None
        self.last_run_duration: float = 0
        self.total_runs: int = 0
        self.total_recommendations: int = 0
    
    def start(self, run_time: str = "08:00"):
        """
        Start the scheduler.
        
        Args:
            run_time: Time to run daily (HH:MM format, UTC)
        """
        if self.running:
            logger.warning("[SCHEDULER] Already running")
            return
        
        hour, minute = map(int, run_time.split(":"))
        
        self.scheduler = AsyncIOScheduler(timezone="UTC")
        self.scheduler.add_job(
            self._run_daily_recommendations,
            trigger=CronTrigger(hour=hour, minute=minute),
            id="daily_recommendations",
            name="Daily Crypto Recommendations",
            replace_existing=True
        )
        
        self.scheduler.start()
        self.running = True
        
        logger.info(f"🕐 [SCHEDULER] Started - Daily recommendations at {run_time} UTC")
    
    def stop(self):
        """Stop the scheduler."""
        if self.scheduler:
            self.scheduler.shutdown(wait=False)
            self.running = False
            logger.info("🛑 [SCHEDULER] Stopped")
    
    async def run_now(self):
        """
        Run recommendations immediately (for testing or manual trigger).
        """
        logger.info("[SCHEDULER] Manual trigger - running recommendations now")
        await self._run_daily_recommendations()
    
    async def _run_daily_recommendations(self):
        """
        Main job: Generate recommendations for all users.
        """
        start_time = datetime.now()
        logger.info("🚀 [SCHEDULER] Starting daily recommendation generation...")
        
        try:
            from app.services.watchlist_recommendation_engine import get_recommendation_engine
            engine = get_recommendation_engine(self.db_session_factory)
            
            # Get all users who have watchlist items (active users)
            users = self._get_active_users()
            logger.info(f"[SCHEDULER] Found {len(users)} active users")
            
            total_saved = 0
            
            for user_id in users:
                try:
                    # Generate recommendations
                    recommendations = engine.generate_recommendations(
                        user_id=user_id,
                        top_n=50,
                        min_score=0  # Get all, let UI filter
                    )
                    
                    # Filter to only ADD and REMOVE actions
                    actionable = [r for r in recommendations if r.action != "HOLD"]
                    
                    if actionable:
                        # Add AI reasoning (async)
                        actionable_with_reasoning = await engine.generate_reasoning_batch(
                            actionable[:20]  # Limit to top 20 for API cost control
                        )
                        
                        # Save to database
                        db = self.db_session_factory()
                        try:
                            saved = engine.save_recommendations(db, user_id, actionable_with_reasoning)
                            total_saved += saved
                        finally:
                            db.close()
                    
                    logger.info(f"[SCHEDULER] User {user_id[:8]}: {len(actionable)} recommendations")
                    
                except Exception as e:
                    logger.error(f"[SCHEDULER] Error for user {user_id[:8]}: {e}")
                    continue
            
            # Update stats
            self.last_run = datetime.now()
            self.last_run_duration = (self.last_run - start_time).total_seconds()
            self.total_runs += 1
            self.total_recommendations += total_saved
            
            logger.info(f"✅ [SCHEDULER] Complete! Generated {total_saved} recommendations "
                       f"for {len(users)} users in {self.last_run_duration:.1f}s")
            
        except Exception as e:
            logger.error(f"❌ [SCHEDULER] Daily recommendation failed: {e}")
    
    def _get_active_users(self) -> List[str]:
        """
        Get list of active user IDs.
        Active = has at least one watchlist item or one bot.
        """
        db = self.db_session_factory()
        
        try:
            # Get users with watchlist items OR active bots
            result = db.execute(text("""
                SELECT DISTINCT user_id FROM (
                    SELECT user_id FROM watchlist_items
                    UNION
                    SELECT user_id FROM bots WHERE status = 'ACTIVE'
                    UNION
                    SELECT user_id FROM portfolios
                ) active_users
            """))
            
            return [str(row[0]) for row in result.fetchall()]
            
        finally:
            db.close()
    
    def get_stats(self) -> dict:
        """Get scheduler statistics."""
        next_run = None
        if self.scheduler and self.running:
            job = self.scheduler.get_job("daily_recommendations")
            if job and job.next_run_time:
                next_run = job.next_run_time.isoformat()
        
        return {
            "running": self.running,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "last_run_duration_seconds": self.last_run_duration,
            "total_runs": self.total_runs,
            "total_recommendations": self.total_recommendations,
            "next_run": next_run
        }


# Global instance
_scheduler: Optional[DailyRecommendationScheduler] = None


def get_recommendation_scheduler(db_session_factory=None) -> DailyRecommendationScheduler:
    """Get or create the scheduler singleton."""
    global _scheduler
    
    if _scheduler is None:
        if db_session_factory is None:
            from app.db.database import SessionLocal
            db_session_factory = SessionLocal
        _scheduler = DailyRecommendationScheduler(db_session_factory)
    
    return _scheduler


def start_recommendation_scheduler(run_time: str = "08:00"):
    """Convenience function to start the scheduler."""
    scheduler = get_recommendation_scheduler()
    scheduler.start(run_time)
    return scheduler
