"""
Long-Term DCA Scheduler Service
Checks periodically if DCA should be executed for users with long-term enabled.

Runs every hour, checks:
- Users with lt_enabled=true
- DCA schedule (daily/weekly/monthly)
- Confidence score >= threshold

Flow:
1. Get all users with lt_enabled=true
2. For each user, call should_execute_dca()
3. If yes, execute DCA for qualified symbols
4. Log results
"""

import asyncio
from datetime import datetime
from typing import Optional
import logging
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.db.database import SessionLocal
from app.models.database_models import PortfolioAllocation, Portfolio
from app.services.long_term_manager import LongTermManager
from app.services.market_data import MarketDataCollector
from app.services.technical_analysis import TechnicalAnalysis
from app.services.ml_engine import ML_Engine

logger = logging.getLogger(__name__)


class LongTermScheduler:
    """
    Periodic scheduler for long-term DCA execution.
    """
    
    def __init__(self):
        self.running = False
        self.check_interval = 3600  # Check every hour
        self.market_collector = MarketDataCollector()
        self.technical_analysis = TechnicalAnalysis()
        self.ml_engine = None  # TODO: Initialize if available
    
    async def start(self):
        """Start the DCA scheduler loop"""
        self.running = True
        logger.info("🚀 Long-Term DCA Scheduler started")
        
        while self.running:
            try:
                await self.check_and_execute_dca()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in DCA scheduler loop: {str(e)}")
                await asyncio.sleep(60)  # Retry after 1min on error
    
    def stop(self):
        """Stop the scheduler loop"""
        self.running = False
        logger.info("🛑 Long-Term DCA Scheduler stopped")
    
    async def check_and_execute_dca(self):
        """
        Check all users with LT enabled and execute DCA if conditions met.
        """
        logger.info("🔍 Checking for DCA opportunities...")
        
        db = SessionLocal()
        try:
            # Get all users with long-term enabled
            allocations = db.query(PortfolioAllocation).filter(
                PortfolioAllocation.lt_enabled == True
            ).all()
            
            if not allocations:
                logger.debug("No users with long-term enabled")
                return
            
            logger.info(f"Found {len(allocations)} users with LT enabled")
            
            for allocation in allocations:
                try:
                    await self.process_user_dca(allocation.user_id, db)
                except Exception as e:
                    logger.error(f"Failed to process DCA for user {allocation.user_id}: {str(e)}")
                    continue
        
        finally:
            db.close()
    
    async def process_user_dca(self, user_id: str, db: Session):
        """
        Process DCA for a single user.
        """
        logger.debug(f"📊 Checking DCA for user {user_id}")
        
        # Initialize LongTermManager
        lt_manager = LongTermManager(
            db_session=db,
            market_data=self.market_collector,
            technical_analysis=self.technical_analysis,
            ml_engine=self.ml_engine
        )
        
        # Check if should execute DCA
        dca_decision = await lt_manager.should_execute_dca(user_id)
        
        if not dca_decision["should_execute"]:
            logger.debug(f"⏭️ Skip DCA for {user_id}: {dca_decision.get('reason', 'Unknown')}")
            return
        
        # Execute DCA for each qualified symbol
        symbols = dca_decision["symbols"]
        amounts = dca_decision["amounts"]
        analyses = dca_decision["analyses"]
        
        logger.info(
            f"✅ DCA Trigger for {user_id}: "
            f"{len(symbols)} symbols, "
            f"${sum(amounts.values()):.2f} total"
        )
        
        for symbol in symbols:
            try:
                amount = amounts[symbol]
                analysis = analyses[symbol]
                
                transaction = await lt_manager.execute_dca(
                    user_id=user_id,
                    symbol=symbol,
                    amount=amount,
                    analysis=analysis
                )
                
                if transaction:
                    logger.info(
                        f"✅ DCA executed: {symbol} "
                        f"${amount:.2f} @ ${transaction.price:.2f} "
                        f"(Score: {analysis['confidence_score']:.1f})"
                    )
                else:
                    logger.error(f"❌ DCA failed for {symbol}")
            
            except Exception as e:
                logger.error(f"❌ Error executing DCA for {symbol}: {e}")
                continue


# Global instance
long_term_scheduler: Optional[LongTermScheduler] = None


def get_long_term_scheduler() -> LongTermScheduler:
    """Get or create the global LT scheduler"""
    global long_term_scheduler
    if long_term_scheduler is None:
        long_term_scheduler = LongTermScheduler()
    return long_term_scheduler


async def start_long_term_scheduler():
    """Start the background DCA scheduler"""
    scheduler = get_long_term_scheduler()
    await scheduler.start()


def stop_long_term_scheduler():
    """Stop the background DCA scheduler"""
    scheduler = get_long_term_scheduler()
    scheduler.stop()
