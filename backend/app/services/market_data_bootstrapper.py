"""
MarketDataBootstrapper - Fetches historical market data from Binance
Feature: RecommendationCrypto

Usage:
    python -m app.services.market_data_bootstrapper --cryptos=200 --days=730

This service:
1. Fetches TOP 200 cryptos by volume from Binance
2. Downloads 2 years of historical OHLCV data (1h, 4h, 1d timeframes)
3. Batch inserts into crypto_market_data table
4. Supports resume (skips already-fetched data)
"""

import asyncio
import aiohttp
import logging
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class MarketDataBootstrapper:
    """
    Bootstraps historical crypto market data from Binance.
    
    Fetches OHLCV data for multiple timeframes and stores in database.
    Handles rate limiting and provides resume capability.
    """
    
    BINANCE_API_URL = "https://api.binance.com/api/v3"
    
    # Rate limiting: Binance allows 1200 requests/minute
    # We'll be conservative: 10 requests/second max
    REQUEST_DELAY = 0.1  # 100ms between requests
    
    # Batch insert size
    BATCH_SIZE = 1000
    
    # Timeframes to fetch
    TIMEFRAMES = ["1d", "4h", "1h"]
    
    # Kline limits per request (max 1000)
    KLINE_LIMIT = 1000
    
    def __init__(self, db_session_factory):
        self.db_session_factory = db_session_factory
        self.session: Optional[aiohttp.ClientSession] = None
        self.total_inserted = 0
        self.total_skipped = 0
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_top_cryptos(self, limit: int = 200) -> List[str]:
        """
        Get top N cryptocurrencies by 24h volume from Binance.
        Filters for USDT pairs only.
        """
        url = f"{self.BINANCE_API_URL}/ticker/24hr"
        
        async with self.session.get(url) as response:
            if response.status != 200:
                logger.error(f"Failed to fetch tickers: {response.status}")
                return []
            
            tickers = await response.json()
        
        # Filter USDT pairs and sort by volume
        usdt_pairs = [
            t for t in tickers 
            if t['symbol'].endswith('USDT') 
            and not t['symbol'].startswith('USDT')
            and float(t['quoteVolume']) > 0
        ]
        
        # Sort by quote volume (USDT volume)
        usdt_pairs.sort(key=lambda x: float(x['quoteVolume']), reverse=True)
        
        # Return top N symbols
        symbols = [t['symbol'] for t in usdt_pairs[:limit]]
        logger.info(f"📊 Found {len(symbols)} USDT pairs. Top 5: {symbols[:5]}")
        
        return symbols
    
    async def fetch_klines(
        self, 
        symbol: str, 
        timeframe: str, 
        start_time: int, 
        end_time: int
    ) -> List[Dict]:
        """
        Fetch klines (candlesticks) from Binance for a symbol.
        
        Args:
            symbol: Trading pair (e.g., BTCUSDT)
            timeframe: Interval (1h, 4h, 1d)
            start_time: Start timestamp in milliseconds
            end_time: End timestamp in milliseconds
            
        Returns:
            List of kline dictionaries
        """
        url = f"{self.BINANCE_API_URL}/klines"
        params = {
            "symbol": symbol,
            "interval": timeframe,
            "startTime": start_time,
            "endTime": end_time,
            "limit": self.KLINE_LIMIT
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 429:
                    # Rate limited - wait and retry
                    logger.warning(f"⚠️ Rate limited on {symbol}. Waiting 60s...")
                    await asyncio.sleep(60)
                    return await self.fetch_klines(symbol, timeframe, start_time, end_time)
                
                if response.status != 200:
                    logger.error(f"Failed to fetch {symbol} {timeframe}: {response.status}")
                    return []
                
                klines = await response.json()
                
                # Transform Binance klines to our format
                # [open_time, open, high, low, close, volume, close_time, ...]
                return [
                    {
                        "symbol": symbol,
                        "timestamp": int(k[0]),  # open_time in ms
                        "open": float(k[1]),
                        "high": float(k[2]),
                        "low": float(k[3]),
                        "close": float(k[4]),
                        "volume": float(k[5]),
                        "timeframe": timeframe
                    }
                    for k in klines
                ]
        except Exception as e:
            logger.error(f"Error fetching {symbol} {timeframe}: {e}")
            return []
    
    def get_last_timestamp(self, db: Session, symbol: str, timeframe: str) -> Optional[int]:
        """Get the last timestamp we have for a symbol/timeframe combo."""
        result = db.execute(
            text("""
                SELECT MAX(timestamp) 
                FROM crypto_market_data 
                WHERE symbol = :symbol AND timeframe = :timeframe
            """),
            {"symbol": symbol, "timeframe": timeframe}
        ).fetchone()
        
        return result[0] if result and result[0] else None
    
    def batch_insert(self, db: Session, klines: List[Dict]) -> int:
        """
        Batch insert klines into database using proper parameterized queries.
        Uses executemany for efficiency.
        
        Returns number of rows inserted.
        """
        if not klines:
            return 0
        
        try:
            # Prepare data for batch insert
            insert_data = []
            for k in klines:
                insert_data.append({
                    'symbol': k['symbol'],
                    'timestamp': k['timestamp'],
                    'open': float(k['open']),
                    'high': float(k['high']),
                    'low': float(k['low']),
                    'close': float(k['close']),
                    'volume': float(k['volume']),
                    'timeframe': k['timeframe']
                })
            
            # Use parameterized insert to avoid SQL injection and handle large batches
            query = text("""
                INSERT INTO crypto_market_data 
                (symbol, timestamp, open, high, low, close, volume, timeframe)
                VALUES (:symbol, :timestamp, :open, :high, :low, :close, :volume, :timeframe)
                ON CONFLICT (symbol, timestamp, timeframe) DO NOTHING
            """)
            
            # Execute batch insert
            db.execute(query, insert_data)
            db.commit()
            
            logger.debug(f"✅ Batch inserted {len(insert_data)} klines")
            return len(insert_data)
        
        except Exception as e:
            logger.error(f"❌ Batch insert failed: {e}", exc_info=True)
            db.rollback()
            return 0
    
    async def bootstrap_symbol(
        self, 
        symbol: str, 
        days: int = 730,
        timeframes: List[str] = None
    ) -> Tuple[int, int]:
        """
        Bootstrap historical data for a single symbol.
        
        Args:
            symbol: Trading pair
            days: Number of days of history to fetch
            timeframes: List of timeframes to fetch
            
        Returns:
            Tuple of (inserted_count, skipped_count)
        """
        timeframes = timeframes or self.TIMEFRAMES
        inserted = 0
        skipped = 0
        
        db = self.db_session_factory()
        
async def bootstrap_symbol(
        self, 
        symbol: str, 
        days: int = 730,
        timeframes: List[str] = None,
        force_full: bool = False
    ) -> Tuple[int, int]:
        """
        Bootstrap historical data for a single symbol.
        
        Args:
            symbol: Trading pair
            days: Number of days of history to fetch (only used if force_full=True)
            timeframes: List of timeframes to fetch
            force_full: If True, always fetch full 730 days. If False, resume from last data.
            
        Returns:
            Tuple of (inserted_count, skipped_count)
        """
        timeframes = timeframes or self.TIMEFRAMES
        inserted = 0
        skipped = 0
        
        db = self.db_session_factory()
        
        try:
            for tf in timeframes:
                # Check if we already have data
                last_ts = self.get_last_timestamp(db, symbol, tf)
                
                # Calculate time range
                end_time = int(datetime.now().timestamp() * 1000)
                
                if last_ts and not force_full:
                    # Resume from last timestamp + 1 interval (incremental update)
                    start_time = last_ts + self._get_interval_ms(tf)
                    if start_time >= end_time:
                        logger.debug(f"  ⏭️ {symbol} {tf}: Already up to date")
                        skipped += 1
                        continue
                    logger.info(f"  📥 {symbol} {tf}: Delta update from {datetime.fromtimestamp(start_time/1000)}")
                else:
                    # Fetch full 730 days (initial bootstrap or force_full=True)
                    start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
                    if force_full:
                        logger.info(f"  📥 {symbol} {tf}: Force full fetch from {datetime.fromtimestamp(start_time/1000)}")
                    else:
                        logger.info(f"  📥 {symbol} {tf}: Initial fetch from {datetime.fromtimestamp(start_time/1000)}")
                
                # Fetch in chunks (max 1000 candles per request)
                all_klines = []
                current_start = start_time
                chunk_count = 0
                
                while current_start < end_time:
                    klines = await self.fetch_klines(
                        symbol, tf, current_start, end_time
                    )
                    
                    if not klines:
                        logger.debug(f"    No more data for {symbol} {tf}")
                        break
                    
                    all_klines.extend(klines)
                    chunk_count += 1
                    
                    # Move to next chunk
                    current_start = klines[-1]["timestamp"] + self._get_interval_ms(tf)
                    
                    # Rate limiting
                    await asyncio.sleep(self.REQUEST_DELAY)
                
                # Batch insert
                if all_klines:
                    count = self.batch_insert(db, all_klines)
                    inserted += count
                    logger.info(f"  ✅ {symbol} {tf}: Fetched {len(all_klines)} candles ({chunk_count} chunks), inserted {count}")
                else:
                    logger.warning(f"  ⚠️ {symbol} {tf}: No data fetched from Binance")
                
        finally:
            db.close()
        
        return inserted, skipped
    
    def _get_interval_ms(self, timeframe: str) -> int:
        """Get interval duration in milliseconds."""
        intervals = {
            "1m": 60 * 1000,
            "5m": 5 * 60 * 1000,
            "15m": 15 * 60 * 1000,
            "1h": 60 * 60 * 1000,
            "4h": 4 * 60 * 60 * 1000,
            "1d": 24 * 60 * 60 * 1000,
        }
        return intervals.get(timeframe, 60 * 60 * 1000)
    
    async def run(
        self, 
        crypto_count: int = 200, 
        days: int = 730,
        timeframes: List[str] = None,
        force_full: bool = False
    ):
        """
        Main bootstrap process.
        
        Args:
            crypto_count: Number of top cryptos to fetch
            days: Days of history per crypto
            timeframes: Timeframes to fetch
            force_full: If True, always fetch full history (ignores existing data)
        """
        start_time = datetime.now()
        logger.info(f"🚀 Starting MarketDataBootstrapper")
        logger.info(f"   Cryptos: {crypto_count} | Days: {days} | Timeframes: {timeframes or self.TIMEFRAMES}")
        if force_full:
            logger.info(f"   ⚠️  FORCE_FULL=True - Will refetch full {days} days (ignore existing data)")
        
        # Get top cryptos
        symbols = await self.get_top_cryptos(crypto_count)
        
        if not symbols:
            logger.error("❌ No symbols found. Aborting.")
            return
        
        total_inserted = 0
        total_skipped = 0
        
        for i, symbol in enumerate(symbols, 1):
            logger.info(f"📊 [{i}/{len(symbols)}] Processing {symbol}...")
            
            try:
                inserted, skipped = await self.bootstrap_symbol(
                    symbol, days, timeframes, force_full=force_full
                )
                total_inserted += inserted
                total_skipped += skipped
            except Exception as e:
                logger.error(f"❌ Error processing {symbol}: {e}")
                continue
        
        elapsed = datetime.now() - start_time
        logger.info(f"")
        logger.info(f"✅ Bootstrap complete!")
        logger.info(f"   Total inserted: {total_inserted:,} candles")
        logger.info(f"   Total skipped: {total_skipped} (already up to date)")
        logger.info(f"   Duration: {elapsed}")


async def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Bootstrap crypto market data from Binance")
    parser.add_argument("--cryptos", type=int, default=200, help="Number of top cryptos to fetch")
    parser.add_argument("--days", type=int, default=730, help="Days of history to fetch")
    parser.add_argument("--timeframes", type=str, default="1d,4h,1h", help="Comma-separated timeframes")
    
    args = parser.parse_args()
    timeframes = args.timeframes.split(",")
    
    # Import here to avoid circular imports
    from app.db.database import SessionLocal
    
    async with MarketDataBootstrapper(SessionLocal) as bootstrapper:
        await bootstrapper.run(
            crypto_count=args.cryptos,
            days=args.days,
            timeframes=timeframes
        )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s"
    )
    
    # Fix for Windows async DNS issue
    import sys
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main())
