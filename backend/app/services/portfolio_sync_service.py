"""
Portfolio Sync Service
Synchronizes local Portfolio database with real Binance account balance
Runs periodically (every 60 seconds) to keep data in sync

This is CRITICAL for production to ensure:
1. Portfolio value matches actual Binance balance
2. Detect discrepancies (drift detection)
3. Reconcile automatically if out of sync
"""

import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
import logging
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.database_models import Portfolio, ExchangeConfig, Trade
from app.services.market_data import MarketDataCollector
from app.services.crypto_service import get_crypto_service
from cryptography.fernet import Fernet
import os

logger = logging.getLogger(__name__)


class PortfolioSyncService:
    """
    Synchronizes local Portfolio with real Binance balance
    Handles:
    1. Fetching account balance from Binance
    2. Converting all assets to quote currency (USDT)
    3. Detecting drift (local vs exchange balance)
    4. Automatic reconciliation
    5. Daily reset of counters
    """
    
    def __init__(self):
        self.market_collector = MarketDataCollector()
        self.running = False
        self.sync_interval = 60  # Sync every 60 seconds
        self.drift_threshold = 100.0  # Alert if diff > 100 USDT
        self.encryption_key = os.getenv("PORTFOLIO_ENCRYPTION_KEY", "default-key-change-in-prod")
    
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
        Sync a single user's portfolio with their Binance account
        
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
            # Decrypt credentials
            cipher = Fernet(self.encryption_key.encode())
            api_key = cipher.decrypt(exchange_config.api_key_encrypted.encode()).decode()
            api_secret = cipher.decrypt(exchange_config.api_secret_encrypted.encode()).decode()
            
            # Get Binance client
            crypto_service = get_crypto_service()
            binance_client = crypto_service.get_exchange_client(
                exchange_config.exchange,
                api_key,
                api_secret,
                testnet=exchange_config.use_testnet
            )
            
            # === FETCH REAL DATA FROM BINANCE ===
            
            # 1. Get account balance
            logger.debug(f"Fetching account balance for {user_id}...")
            account = await binance_client.get_account()
            
            if not account or "balances" not in account:
                logger.error(f"Invalid account response for {user_id}")
                return False
            
            # 2. Calculate total value in quote asset (USDT)
            quote_asset = "USDT"
            exchange_balances = {}
            exchange_total_value = 0
            
            for balance in account["balances"]:
                asset = balance["asset"]
                free = float(balance.get("free", 0))
                locked = float(balance.get("locked", 0))
                total = free + locked
                
                if total == 0:
                    continue
                
                exchange_balances[asset] = {
                    "free": free,
                    "locked": locked,
                    "total": total
                }
                
                if asset == quote_asset:
                    exchange_total_value += total
                else:
                    # Convert to USDT
                    try:
                        ticker = await self.market_collector.get_ticker(f"{asset}{quote_asset}")
                        price = float(ticker.get("close", 0))
                        value_in_quote = total * price
                        exchange_total_value += value_in_quote
                        
                        logger.debug(f"  {asset}: {total:.8f} @ ${price:.2f} = ${value_in_quote:.2f}")
                    except Exception as e:
                        logger.warning(f"Could not get price for {asset}: {str(e)}")
                        continue
            
            # === UPDATE DATABASE ===
            
            # Store exchange values (source of truth)
            exchange_cash_balance = exchange_balances.get(quote_asset, {}).get("free", 0)
            
            # Calculate difference
            old_exchange_value = portfolio.exchange_total_value or 0
            balance_difference = abs(portfolio.local_total_value - exchange_total_value)
            
            # Update portfolio
            portfolio.exchange_cash_balance = exchange_cash_balance
            portfolio.exchange_total_value = exchange_total_value
            portfolio.balance_difference = balance_difference
            portfolio.last_synced_with_exchange = datetime.utcnow()
            
            # Check if synced
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
                portfolio.local_total_value = exchange_total_value
                portfolio.cash_balance = exchange_cash_balance
                portfolio.is_synced = True
            else:
                portfolio.is_synced = True
            
            db.commit()
            
            logger.info(
                f"✅ Synced {user_id}: "
                f"Cash=${exchange_cash_balance:.2f}, "
                f"Total=${exchange_total_value:.2f}, "
                f"Sync={'✓' if portfolio.is_synced else '✗'}"
            )
            
            return True
        
        except Exception as e:
            logger.error(f"❌ Sync failed for {user_id}: {str(e)}")
            portfolio.is_synced = False
            db.commit()
            return False
    
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
