"""
Portfolio Sync Service
Synchronizes local Portfolio database with exchange account balance via broker abstraction
Runs periodically (every 60 seconds) to keep data in sync

This is CRITICAL for production to ensure:
1. Portfolio value matches actual exchange balance
2. Detect discrepancies (drift detection)
3. Reconcile automatically if out of sync
"""

import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
import logging
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.database_models import Portfolio, ExchangeConfig, Trade, LongTermPosition
from app.brokers import BrokerFactory
from sqlalchemy import and_
import os

logger = logging.getLogger(__name__)


class PortfolioSyncService:
    """
    Synchronizes local Portfolio with exchange balance via broker abstraction
    Handles:
    1. Fetching account balance from exchange (via BrokerFactory)
    2. Detecting drift (local vs exchange balance)
    3. Automatic reconciliation
    4. Daily reset of counters
    """
    
    def __init__(self):
        self.running = False
        self.sync_interval = 60  # Sync every 60 seconds
        self.drift_threshold = 100.0  # Alert if diff > 100 USDT
    
    async def start(self):
        """Start the portfolio sync loop"""
        self.running = True
        logger.info("🚀 Portfolio Sync Service started")
        
        while self.running:
            try:
                await self.sync_all_portfolios()
                await asyncio.sleep(self.sync_interval)
            except Exception as e:
                logger.error(f"Error in portfolio sync loop: {str(e)}")
                await asyncio.sleep(10)  # Retry after 10s on error
    
    def stop(self):
        """Stop the sync loop"""
        self.running = False
        logger.info("🛑 Portfolio Sync Service stopped")
    
    async def sync_all_portfolios(self):
        """Sync all active user portfolios"""
        db = SessionLocal()
        try:
            # Get all active exchange configs
            exchange_configs = db.query(ExchangeConfig).filter(
                ExchangeConfig.is_active == True,
                ExchangeConfig.paper_trading == False  # Only sync LIVE accounts
            ).all()
            
            for config in exchange_configs:
                try:
                    await self.sync_user_portfolio(config.user_id, db)
                except Exception as e:
                    logger.error(f"Failed to sync user {config.user_id}: {str(e)}")
                    continue
        
        finally:
            db.close()
    
    async def sync_user_portfolio(self, user_id: str, db: Session) -> bool:
        """
        Sync a single user's portfolio with their exchange account via broker abstraction.
        Works for BOTH paper trading and live trading modes.
        
        Returns:
            True if synced successfully, False if error
        """
        logger.info(f"🔄 Syncing portfolio for user {user_id}")
        
        # Get user's exchange config
        exchange_config = db.query(ExchangeConfig).filter(
            ExchangeConfig.user_id == user_id,
            ExchangeConfig.is_active == True
        ).first()
        
        if not exchange_config:
            logger.warning(f"No active exchange config for user {user_id}")
            return False
        
        # Get or create portfolio record
        portfolio = db.query(Portfolio).filter(
            Portfolio.user_id == user_id
        ).first()
        
        if not portfolio:
            logger.info(f"Creating portfolio for user {user_id}")
            portfolio = Portfolio(
                user_id=user_id,
                total_value=0.0,
                cash_balance=0.0,
                daily_pnl=0.0,
                total_pnl=0.0,
                win_rate=0.0,
                max_drawdown=0.0
            )
            db.add(portfolio)
            db.commit()
            db.refresh(portfolio)
        
        try:
            # === FETCH REAL DATA FROM EXCHANGE VIA BROKER ===
            broker = BrokerFactory.create(exchange_config, db)
            
            logger.info(f"Fetching account balance for {user_id} via {broker.name}...")
            
            # Get account balance
            account_balance = await broker.get_account_balance()
            
            if not account_balance:
                logger.error(f"Invalid account balance for {user_id}")
                return False
            
            # === EXTRACT KEY METRICS (using correct AccountBalance attributes) ===
            exchange_cash_balance = account_balance.free_usdt
            exchange_total_value = account_balance.total_value_usdt
            
            logger.info(
                f"  Broker balance: Free=${exchange_cash_balance:.2f}, "
                f"Total=${exchange_total_value:.2f}, "
                f"Assets={len(account_balance.assets)}"
            )
            
            # === UPDATE PORTFOLIO ===
            old_total = portfolio.total_value
            
            portfolio.cash_balance = exchange_cash_balance
            portfolio.total_value = exchange_total_value
            
            # Log drift if significant
            drift = abs(old_total - exchange_total_value)
            if drift > self.drift_threshold:
                logger.warning(
                    f"⚠️ DRIFT DETECTED for {user_id}: "
                    f"Old=${old_total:.2f} → New=${exchange_total_value:.2f} "
                    f"(Diff=${drift:.2f})"
                )
            
            db.commit()
            
            logger.info(
                f"✅ Portfolio synced for {user_id}: "
                f"Cash=${exchange_cash_balance:.2f}, "
                f"Total=${exchange_total_value:.2f}"
            )
            
            return True
        
        except Exception as e:
            logger.error(f"❌ Sync failed for {user_id}: {str(e)}")
            return False
    
    async def _calculate_lt_positions_value(self, user_id: str, db: Session, broker) -> float:
        """
        Calculate total value of Long-Term positions using broker for price data.
        Fetches all LT positions and multiplies quantity * current_price.
        
        Args:
            user_id: User ID
            db: Database session
            broker: Broker instance for price queries
        
        Returns:
            Total value in USDT
        """
        try:
            positions = db.query(LongTermPosition).filter(
                and_(
                    LongTermPosition.user_id == user_id,
                    LongTermPosition.status.in_(["ACCUMULATING", "HOLDING", "PARTIAL_EXIT"])
                )
            ).all()
            
            if not positions:
                return 0.0
            
            total_value = 0.0
            
            for pos in positions:
                try:
                    # Get current price via broker
                    current_price = await broker.get_latest_price(pos.symbol)
                    
                    # Calculate position value
                    position_value = pos.total_quantity * current_price
                    total_value += position_value
                    
                    # Update unrealized PnL (opportunistic update)
                    pos.unrealized_pnl = position_value - pos.total_invested
                    pos.unrealized_pnl_pct = (pos.unrealized_pnl / pos.total_invested * 100) if pos.total_invested > 0 else 0
                    
                    logger.debug(f"  LT {pos.symbol}: {pos.total_quantity:.8f} @ ${current_price:.2f} = ${position_value:.2f}")
                
                except Exception as e:
                    logger.warning(f"Could not get price for LT position {pos.symbol}: {str(e)}")
                    # Fallback to avg entry price
                    fallback_value = pos.total_quantity * pos.avg_entry_price
                    total_value += fallback_value
            
            db.commit()  # Save PnL updates
            
            logger.debug(f"💰 Total LT positions value: ${total_value:.2f}")
            return total_value
        
        except Exception as e:
            logger.error(f"Error calculating LT positions value: {e}")
            return 0.0
    
    async def reset_daily_counters(self):
        """
        Reset daily trade counters
        Should be called once per day at UTC midnight
        """
        db = SessionLocal()
        try:
            portfolios = db.query(Portfolio).all()
            
            for portfolio in portfolios:
                portfolio.daily_trade_count = 0
                portfolio.daily_loss_amount = 0.0
            
            db.commit()
            logger.info("✅ Daily counters reset")
        
        finally:
            db.close()


# Global instance
portfolio_sync_service: Optional[PortfolioSyncService] = None


def get_portfolio_sync_service() -> PortfolioSyncService:
    """Get or create the global portfolio sync service"""
    global portfolio_sync_service
    if portfolio_sync_service is None:
        portfolio_sync_service = PortfolioSyncService()
    return portfolio_sync_service


async def start_portfolio_sync_service():
    """Start the background portfolio sync job"""
    service = get_portfolio_sync_service()
    await service.start()


def stop_portfolio_sync_service():
    """Stop the background portfolio sync job"""
    service = get_portfolio_sync_service()
    service.stop()
