"""
MarketDataUpdater - Real-time updates for crypto market data
Feature: RecommendationCrypto

This service runs as a background task and:
1. Updates TOP 100 cryptos every 1 minute
2. Updates TOP 100-200 cryptos every 5 minutes
3. Updates REST every 30 minutes

Uses UPSERT for latest candle to avoid duplicates.
"""

import asyncio
import aiohttp
import logging
from datetime import datetime
from typing import List, Dict, Optional, Set
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class MarketDataUpdater:
    """
    Real-time market data updater for crypto recommendations.
    
    Implements tiered update frequency based on crypto ranking:
    - Tier 1 (1-100): Every 1 minute
    - Tier 2 (101-200): Every 5 minutes
    - Tier 3 (201+): Every 30 minutes
    """
    
    BINANCE_API_URL = "https://api.binance.com/api/v3"
    
    # Update intervals (seconds)
    TIER1_INTERVAL = 60      # 1 minute
    TIER2_INTERVAL = 300     # 5 minutes
    TIER3_INTERVAL = 1800    # 30 minutes
    
    # Retry settings
    MAX_RETRIES = 3
    RETRY_DELAY = 5  # seconds
    
    def __init__(self, db_session_factory):
        self.db_session_factory = db_session_factory
        self.session: Optional[aiohttp.ClientSession] = None
        self.running = False
        
        # Symbol tiers (populated on start)
        self.tier1_symbols: List[str] = []  # Top 100
        self.tier2_symbols: List[str] = []  # 101-200
        self.tier3_symbols: List[str] = []  # 201+
        
        # Track last update times
        self.last_tier1_update = datetime.min
        self.last_tier2_update = datetime.min
        self.last_tier3_update = datetime.min
        
        # Stats
        self.update_count = 0
        self.error_count = 0
    
    async def start(self):
        """Start the background update loop."""
        if self.running:
            logger.warning("MarketDataUpdater already running")
            return
        
        self.running = True
        self.session = aiohttp.ClientSession()
        
        logger.info("🚀 [MARKET_UPDATE] Starting MarketDataUpdater...")
        
        # Initial symbol ranking fetch
        await self.refresh_symbol_tiers()
        
        # Start update loop
        asyncio.create_task(self._update_loop())
        
        logger.info(f"✅ [MARKET_UPDATE] Started with {len(self.tier1_symbols)} tier1, "
                   f"{len(self.tier2_symbols)} tier2 symbols")
    
    async def stop(self):
        """Stop the update loop."""
        self.running = False
        if self.session:
            await self.session.close()
        logger.info("🛑 [MARKET_UPDATE] Stopped")
    
    async def refresh_symbol_tiers(self):
        """
        Refresh the symbol tier rankings based on 24h volume.
        Should be called periodically (e.g., every hour).
        """
        url = f"{self.BINANCE_API_URL}/ticker/24hr"
        
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    logger.error(f"[MARKET_UPDATE] Failed to fetch tickers: {response.status}")
                    return
                
                tickers = await response.json()
            
            # Filter USDT pairs and sort by volume
            usdt_pairs = [
                t['symbol'] for t in tickers 
                if t['symbol'].endswith('USDT') 
                and not t['symbol'].startswith('USDT')
                and float(t['quoteVolume']) > 0
            ]
            
            # Sort by volume (already sorted from API) and assign tiers
            usdt_pairs_sorted = sorted(
                [(t['symbol'], float(t['quoteVolume'])) for t in tickers 
                 if t['symbol'].endswith('USDT') and not t['symbol'].startswith('USDT')],
                key=lambda x: x[1],
                reverse=True
            )
            
            symbols = [s[0] for s in usdt_pairs_sorted]
            
            self.tier1_symbols = symbols[:100]
            self.tier2_symbols = symbols[100:200]
            self.tier3_symbols = symbols[200:300]  # Optional: extend if needed
            
            logger.info(f"📊 [MARKET_UPDATE] Refreshed tiers: T1={len(self.tier1_symbols)}, "
                       f"T2={len(self.tier2_symbols)}, T3={len(self.tier3_symbols)}")
            
        except Exception as e:
            logger.error(f"[MARKET_UPDATE] Error refreshing tiers: {e}")
    
    async def _update_loop(self):
        """Main update loop - runs continuously."""
        tier_refresh_counter = 0
        
        while self.running:
            try:
                now = datetime.now()
                
                # Update tier 1 (every minute)
                if (now - self.last_tier1_update).total_seconds() >= self.TIER1_INTERVAL:
                    await self._update_tier(self.tier1_symbols, "TIER1")
                    self.last_tier1_update = now
                
                # Update tier 2 (every 5 minutes)
                if (now - self.last_tier2_update).total_seconds() >= self.TIER2_INTERVAL:
                    await self._update_tier(self.tier2_symbols, "TIER2")
                    self.last_tier2_update = now
                
                # Update tier 3 (every 30 minutes)
                if (now - self.last_tier3_update).total_seconds() >= self.TIER3_INTERVAL:
                    await self._update_tier(self.tier3_symbols, "TIER3")
                    self.last_tier3_update = now
                
                # Refresh symbol rankings every hour
                tier_refresh_counter += 1
                if tier_refresh_counter >= 60:  # ~60 iterations = ~1 hour
                    await self.refresh_symbol_tiers()
                    tier_refresh_counter = 0
                
                # Small sleep to prevent tight loop
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"[MARKET_UPDATE] Error in update loop: {e}")
                self.error_count += 1
                await asyncio.sleep(5)
    
    async def _update_tier(self, symbols: List[str], tier_name: str):
        """Update all symbols in a tier."""
        if not symbols:
            return
        
        logger.debug(f"[MARKET_UPDATE] Updating {tier_name}: {len(symbols)} symbols")
        
        updated = 0
        errors = 0
        
        for symbol in symbols:
            try:
                success = await self._update_symbol(symbol)
                if success:
                    updated += 1
                else:
                    errors += 1
            except Exception as e:
                logger.error(f"[MARKET_UPDATE] Error updating {symbol}: {e}")
                errors += 1
            
            # Small delay to avoid rate limiting
            await asyncio.sleep(0.05)  # 50ms between requests
        
        self.update_count += updated
        logger.info(f"✅ [MARKET_UPDATE] {tier_name}: Updated {updated}/{len(symbols)} symbols "
                   f"({errors} errors)")
    
    async def _update_symbol(self, symbol: str) -> bool:
        """
        Update latest candle for a symbol (all timeframes).
        
        Returns True if successful.
        """
        timeframes = ["1d", "4h", "1h"]
        
        for tf in timeframes:
            url = f"{self.BINANCE_API_URL}/klines"
            params = {
                "symbol": symbol,
                "interval": tf,
                "limit": 2  # Get last 2 candles (current + previous)
            }
            
            for retry in range(self.MAX_RETRIES):
                try:
                    async with self.session.get(url, params=params, timeout=10) as response:
                        if response.status == 429:
                            logger.warning(f"[MARKET_UPDATE] Rate limited. Waiting...")
                            await asyncio.sleep(60)
                            continue
                        
                        if response.status != 200:
                            continue
                        
                        klines = await response.json()
                        
                        if klines:
                            await self._upsert_klines(symbol, tf, klines)
                        
                        break
                        
                except asyncio.TimeoutError:
                    logger.warning(f"[MARKET_UPDATE] Timeout for {symbol} {tf}")
                    await asyncio.sleep(self.RETRY_DELAY)
                except Exception as e:
                    logger.error(f"[MARKET_UPDATE] Error fetching {symbol} {tf}: {e}")
                    await asyncio.sleep(self.RETRY_DELAY)
        
        return True
    
    async def _upsert_klines(self, symbol: str, timeframe: str, klines: List):
        """
        Upsert klines into database.
        Uses ON CONFLICT DO UPDATE for the latest candle.
        """
        db = self.db_session_factory()
        
        try:
            for k in klines:
                # Binance kline format: [open_time, open, high, low, close, volume, ...]
                timestamp = int(k[0])
                open_price = float(k[1])
                high = float(k[2])
                low = float(k[3])
                close = float(k[4])
                volume = float(k[5])
                
                query = text("""
                    INSERT INTO crypto_market_data 
                    (symbol, timestamp, open, high, low, close, volume, timeframe)
                    VALUES (:symbol, :timestamp, :open, :high, :low, :close, :volume, :timeframe)
                    ON CONFLICT (symbol, timestamp, timeframe) 
                    DO UPDATE SET 
                        open = EXCLUDED.open,
                        high = EXCLUDED.high,
                        low = EXCLUDED.low,
                        close = EXCLUDED.close,
                        volume = EXCLUDED.volume
                """)
                
                db.execute(query, {
                    "symbol": symbol,
                    "timestamp": timestamp,
                    "open": open_price,
                    "high": high,
                    "low": low,
                    "close": close,
                    "volume": volume,
                    "timeframe": timeframe
                })
            
            db.commit()
            
        except Exception as e:
            logger.error(f"[MARKET_UPDATE] Error upserting {symbol} {timeframe}: {e}")
            db.rollback()
        finally:
            db.close()
    
    def get_stats(self) -> Dict:
        """Get updater statistics."""
        return {
            "running": self.running,
            "update_count": self.update_count,
            "error_count": self.error_count,
            "tier1_count": len(self.tier1_symbols),
            "tier2_count": len(self.tier2_symbols),
            "tier3_count": len(self.tier3_symbols),
            "last_tier1_update": self.last_tier1_update.isoformat() if self.last_tier1_update != datetime.min else None,
            "last_tier2_update": self.last_tier2_update.isoformat() if self.last_tier2_update != datetime.min else None,
        }


# Global instance for import
market_data_updater: Optional[MarketDataUpdater] = None


def get_market_data_updater() -> Optional[MarketDataUpdater]:
    """Get the global MarketDataUpdater instance."""
    return market_data_updater


async def initialize_market_data_updater(db_session_factory) -> MarketDataUpdater:
    """Initialize and start the global MarketDataUpdater."""
    global market_data_updater
    
    if market_data_updater is None:
        market_data_updater = MarketDataUpdater(db_session_factory)
        await market_data_updater.start()
    
    return market_data_updater
