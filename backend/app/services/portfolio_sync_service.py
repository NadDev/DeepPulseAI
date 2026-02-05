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
        Sync a single user's portfolio with their exchange account via broker abstraction
        
        Returns:
            True if synced successfully, False if error
        """
        logger.debug(f"🔄 Syncing portfolio for user {user_id}")
        
        # Get user's exchange config
        exchange_config = db.query(ExchangeConfig).filter(
            ExchangeConfig.user_id == user_id,
            ExchangeConfig.is_active == True
        ).first()
        
        if not exchange_config:
            logger.warning(f"No active exchange config for user {user_id}")
            return False
        
        # Skip paper trading accounts
        if exchange_config.paper_trading:
            return True  # Nothing to sync
        
        # Get portfolio record
        portfolio = db.query(Portfolio).filter(
            Portfolio.user_id == user_id
        ).first()
        
        if not portfolio:
            logger.warning(f"No portfolio found for user {user_id}")
            return False
        
        try:
            # === FETCH REAL DATA FROM EXCHANGE VIA BROKER ===
            
            # Create broker via factory
            broker = BrokerFactory.from_user(user_id, db)
            
            logger.debug(f"Fetching account balance for {user_id} via {broker.name}...")
            
            # Get account balance (already returns total value in quote currency)
            account_balance = await broker.get_account_balance()
            
            if not account_balance:
                logger.error(f"Invalid account balance for {user_id}")
                return False
            
            # === EXTRACT KEY METRICS ===
            
            exchange_cash_balance = account_balance.free_balance  # Free USDT
            exchange_total_value = account_balance.total_value  # All assets converted to USDT
            
            logger.debug(
                f"  Exchange balance: Free=${exchange_cash_balance:.2f}, "
                f"Total=${exchange_total_value:.2f}"
            )
            
            # === CALCULATE LONG-TERM POSITIONS VALUE ===
            
            # LT positions are held separately (not on exchange yet)
            lt_positions_value = await self._calculate_lt_positions_value(user_id, db, broker)
            
            # Total portfolio value = Exchange value + LT positions (accumulating)
            total_portfolio_value = exchange_total_value + lt_positions_value
            
            # === UPDATE DATABASE ===
            
            # Calculate difference (drift detection)
            old_local_value = portfolio.cash_balance + portfolio.total_value
            balance_difference = abs(old_local_value - total_portfolio_value)
            
            # Store exchange values
            portfolio.exchange = exchange_config.exchange
            portfolio.exchange_config_id = exchange_config.id
            portfolio.exchange_cash_balance = exchange_cash_balance
            portfolio.exchange_total_value = exchange_total_value
            portfolio.balance_difference = balance_difference
            portfolio.last_synced_with_exchange = datetime.utcnow()
            
            # === UPDATE DATABASE ===
            
            # Calculate difference (drift detection)
            old_local_value = portfolio.cash_balance + portfolio.total_value
            balance_difference = abs(old_local_value - total_portfolio_value)
            
            # Store exchange values
            portfolio.exchange = exchange_config.exchange
            portfolio.exchange_config_id = exchange_config.id
            portfolio.exchange_cash_balance = exchange_cash_balance
            portfolio.exchange_total_value = exchange_total_value
            portfolio.balance_difference = balance_difference
            portfolio.last_synced_with_exchange = datetime.utcnow()
            
            # Update total_value to include LT positions
            portfolio.total_value = total_portfolio_value
            
            # === DRIFT DETECTION & AUTO-RECONCILIATION ===
            
            # Check if synced
            if balance_difference > self.drift_threshold:
                portfolio.is_synced = False
                logger.warning(
                    f"⚠️  DRIFT DETECTED for {user_id}: "
                    f"Local=${old_local_value:.2f}, "
                    f"Exchange=${exchange_total_value:.2f}, "
                    f"Diff=${balance_difference:.2f}"
                )
                
                # Auto-reconcile: use exchange as source of truth
                logger.info(f"🔧 Auto-reconciling portfolio for {user_id}")
                portfolio.cash_balance = exchange_cash_balance
                portfolio.total_value = total_portfolio_value
                portfolio.is_synced = True
            else:
                portfolio.is_synced = True
            if balance_difference > self.drift_threshold:
                portfolio.is_synced = False
                logger.warning(
                    f"⚠️  DRIFT DETECTED for {user_id}: "
                    f"Local=${portfolio.local_total_value:.2f}, "
                    f"Exchange=${exchange_total_value:.2f}, "
                    f"Diff=${balance_difference:.2f}"
                )
                
                # Auto-reconcile: use exchange as source of truth
                logger.info(f"🔧 Auto-reconciling portfolio for {user_id}")
                portfolio.local_total_value = total_portfolio_value
                portfolio.cash_balance = exchange_cash_balance
                portfolio.total_value = total_portfolio_value
                portfolio.is_synced = True
            else:
                portfolio.is_synced = True
            
            db.commit()
            
            logger.info(
                f"✅ Synced {user_id}: "
                f"Cash=$ {exchange_cash_balance:.2f}, "
                f"DT=${exchange_total_value:.2f}, "
                f"LT=${lt_positions_value:.2f}, "
                f"Total=${total_portfolio_value:.2f}, "
                f"Sync={'✓' if portfolio.is_synced else '✗'}"
            )
            
            return True
        
        except Exception as e:
            logger.error(f" ❌ Sync failed for {user_id}: {str(e)}")
            portfolio.is_synced = False
            db.commit()
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
