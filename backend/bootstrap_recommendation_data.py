#!/usr/bin/env python3
"""
Bootstrap script for RecommendationCrypto feature
Loads historical market data (OHLCV candles) for 50+ cryptocurrencies

Usage:
  # Bootstrap top 50 cryptos with 60 days of daily candles (default)
  python bootstrap_recommendation_data.py
  
  # Bootstrap top 100 cryptos with 90 days of data
  python bootstrap_recommendation_data.py --count 100 --days 90
  
  # Dry run (no database writes)
  python bootstrap_recommendation_data.py --dry-run
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from app.services.market_data_bootstrapper import MarketDataBootstrapper
from app.db.database import SessionLocal

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def bootstrap_data(crypto_count: int = 50, days: int = 60, dry_run: bool = False):
    """
    Bootstrap historical market data for RecommendationCrypto feature
    
    Args:
        crypto_count: Number of top cryptos to fetch (default: 50)
        days: Days of historical data (default: 60)
        dry_run: If True, don't write to database
    """
    try:
        logger.info(f"🚀 Starting RecommendationCrypto data bootstrap")
        logger.info(f"   Cryptos: Top {crypto_count}")
        logger.info(f"   History: Last {days} days")
        logger.info(f"   Dry run: {dry_run}")
        logger.info("")
        
        db_session = SessionLocal()
        bootstrapper = MarketDataBootstrapper(
            db_session=db_session,
            crypto_count=crypto_count,
            days=days,
            dry_run=dry_run
        )
        
        # Run bootstrap
        result = await bootstrapper.bootstrap()
        
        if result['success']:
            logger.info("")
            logger.info("✅ BOOTSTRAP SUCCESSFUL!")
            logger.info(f"   Total cryptos processed: {result['crypto_count']}")
            logger.info(f"   Total candles loaded: {result['candle_count']:,}")
            logger.info(f"   Date range: {result['date_range']}")
            logger.info(f"   Time taken: {result['duration']:.2f}s")
            
            if dry_run:
                logger.warning("")
                logger.warning("⚠️  DRY RUN MODE - no data written to database")
                logger.warning("   Remove --dry-run flag to save data")
        else:
            logger.error("")
            logger.error("❌ BOOTSTRAP FAILED!")
            logger.error(f"   Error: {result['error']}")
            return 1
        
        db_session.close()
        return 0
        
    except Exception as e:
        logger.error(f"❌ Bootstrap error: {e}", exc_info=True)
        return 1


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Bootstrap historical market data for RecommendationCrypto feature"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=50,
        help="Number of top cryptos to fetch (default: 50)"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=60,
        help="Days of historical data (default: 60)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without writing to database"
    )
    
    args = parser.parse_args()
    
    # Run async bootstrap
    exit_code = asyncio.run(
        bootstrap_data(
            crypto_count=args.count,
            days=args.days,
            dry_run=args.dry_run
        )
    )
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
