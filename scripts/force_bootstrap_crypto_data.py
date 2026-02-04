#!/usr/bin/env python3
"""
Force re-bootstrap of crypto market data.

Usage:
    python scripts/force_bootstrap_crypto_data.py --cryptos=200 --days=730 --force

Options:
    --cryptos: Number of top cryptos to fetch (default: 200)
    --days: Days of history (default: 730 = 2 years)
    --force: Force full refetch even if data exists (default: no)
"""

import sys
import os
import asyncio
import argparse
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

async def main():
    parser = argparse.ArgumentParser(
        description="Force re-bootstrap of crypto market data from Binance"
    )
    parser.add_argument(
        "--cryptos",
        type=int,
        default=200,
        help="Number of top cryptos to fetch (default: 200)"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=730,
        help="Days of history to fetch (default: 730 = 2 years)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force full refetch even if data exists (default: resume from last data)"
    )
    parser.add_argument(
        "--timeframes",
        type=str,
        default="1d,4h,1h",
        help="Comma-separated timeframes (default: 1d,4h,1h)"
    )
    
    args = parser.parse_args()
    timeframes = args.timeframes.split(",")
    
    try:
        # Import here to avoid circular imports
        from app.db.database import SessionLocal
        from app.services.market_data_bootstrapper import MarketDataBootstrapper
        
        logger.info("=" * 60)
        logger.info("🚀 FORCE BOOTSTRAP CRYPTO MARKET DATA")
        logger.info("=" * 60)
        logger.info(f"📊 Config:")
        logger.info(f"   Cryptos: {args.cryptos}")
        logger.info(f"   Days: {args.days}")
        logger.info(f"   Timeframes: {', '.join(timeframes)}")
        logger.info(f"   Force Full: {args.force}")
        logger.info("=" * 60)
        logger.info("")
        
        async with MarketDataBootstrapper(SessionLocal) as bootstrapper:
            await bootstrapper.run(
                crypto_count=args.cryptos,
                days=args.days,
                timeframes=timeframes,
                force_full=args.force
            )
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("✅ Bootstrap completed successfully!")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ Bootstrap failed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    # Fix for Windows async DNS issue
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main())
