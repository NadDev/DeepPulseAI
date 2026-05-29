#!/usr/bin/env python3
"""
🧹 EMERGENCY DATABASE CLEANUP SCRIPT

Clears old data to free disk space and prevent "No space left on device" errors.
This script implements aggressive cleanup for PostgreSQL storage crisis.

PRIORITY ORDER (what gets deleted first):
1. ⚠️  OLD CRYPTO MARKET DATA (>90 days)
2. ⚠️  OLD AI DECISIONS (>30 days) 
3. ⚠️  OLD LOGS (>7 days)
4. ⚠️  CLOSED/CANCELLED TRADES >180 days

Usage:
    python backend/cleanup_database.py                    # Normal cleanup (90-day retention)
    python backend/cleanup_database.py --aggressive       # Aggressive (30-day retention)
    python backend/cleanup_database.py --dry-run          # Preview what will be deleted
    python backend/cleanup_database.py --analyze          # Show storage usage
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, func
from sqlalchemy.orm import sessionmaker
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    logger.error("❌ DATABASE_URL not set")
    sys.exit(1)

# Database connection
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def analyze_storage():
    """Show current storage usage by table"""
    logger.info("📊 ANALYZING STORAGE USAGE...\n")
    db = SessionLocal()
    
    try:
        # PostgreSQL storage query
        query = text("""
            SELECT 
                schemaname,
                tablename,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
                pg_total_relation_size(schemaname||'.'||tablename) AS size_bytes,
                n_live_tup AS row_count
            FROM pg_stat_user_tables
            WHERE schemaname = 'public'
            ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
        """)
        
        result = db.execute(query)
        rows = result.fetchall()
        
        total_bytes = 0
        print("=" * 80)
        print(f"{'TABLE':<30} {'SIZE':>15} {'ROWS':>12}")
        print("=" * 80)
        
        for row in rows:
            schema, table, size_str, size_bytes, row_count = row
            total_bytes += size_bytes
            print(f"{table:<30} {size_str:>15} {row_count:>12,}")
        
        print("=" * 80)
        print(f"{'TOTAL':<30} {bytes_to_mb(total_bytes):>15} MB\n")
        
        # Show oldest/newest data
        check_data_age()
        
    finally:
        db.close()

def bytes_to_mb(b):
    return f"{b / (1024*1024):.1f}"

def check_data_age():
    """Show age of oldest data in key tables"""
    logger.info("📅 DATA AGE ANALYSIS\n")
    db = SessionLocal()
    
    try:
        tables = {
            'crypto_market_data': 'MAX(timestamp)',  # Unix ms - needs conversion
            'ai_decisions': 'created_at',
            'trades': 'created_at',
        }
        
        for table, date_col in tables.items():
            try:
                # Check if table exists
                query = text(f"SELECT COUNT(*) FROM {table}")
                count_result = db.execute(query)
                count = count_result.scalar()
                
                if count == 0:
                    print(f"  {table}: (empty)")
                    continue
                
                # Get oldest date
                if table == 'crypto_market_data':
                    # timestamp is in milliseconds, convert to seconds
                    query = text(f"""
                        SELECT 
                            COUNT(*) as total_rows,
                            MIN(TO_TIMESTAMP(timestamp/1000.0)) as oldest,
                            MAX(TO_TIMESTAMP(timestamp/1000.0)) as newest
                        FROM {table}
                    """)
                else:
                    query = text(f"""
                        SELECT 
                            COUNT(*) as total_rows,
                            MIN({date_col}) as oldest,
                            MAX({date_col}) as newest
                        FROM {table}
                    """)
                
                result = db.execute(query)
                row = result.fetchone()
                
                if row and row[1]:
                    total, oldest, newest = row
                    age_days = (datetime.utcnow() - oldest).days
                    print(f"  {table:25} | Rows: {total:>10,} | Age: {age_days:>4} days | Range: {oldest.date()} → {newest.date()}")
            except Exception as e:
                pass
        
        print()
    
    finally:
        db.close()

def cleanup_crypto_market_data(days_to_keep=90, dry_run=False):
    """Delete old cryptocurrency market data"""
    logger.info(f"🗑️  CLEANING CRYPTO MARKET DATA (keep {days_to_keep} days)...")
    db = SessionLocal()
    
    try:
        # Convert days to milliseconds (crypto_market_data uses Unix ms timestamps)
        cutoff_timestamp = int((datetime.utcnow() - timedelta(days=days_to_keep)).timestamp() * 1000)
        
        # Count rows to delete
        count_query = text("""
            SELECT COUNT(*) FROM crypto_market_data 
            WHERE timestamp < :cutoff
        """)
        count_result = db.execute(count_query, {"cutoff": cutoff_timestamp})
        rows_to_delete = count_result.scalar()
        
        if rows_to_delete == 0:
            logger.info(f"   ✓ No data older than {days_to_keep} days found")
            return
        
        logger.warning(f"   📊 Will delete {rows_to_delete:,} rows (frees ~{bytes_to_mb(rows_to_delete * 100)} MB estimated)")
        
        if dry_run:
            logger.info("   [DRY RUN] No changes made")
            return
        
        # Delete
        delete_query = text("""
            DELETE FROM crypto_market_data 
            WHERE timestamp < :cutoff
        """)
        db.execute(delete_query, {"cutoff": cutoff_timestamp})
        db.commit()
        logger.info(f"   ✅ Deleted {rows_to_delete:,} rows")
        
        # Vacuum to reclaim space
        logger.info("   🧹 Vacuuming table (reclaiming space)...")
        db.execute(text("VACUUM ANALYZE crypto_market_data"))
        logger.info(f"   ✅ Vacuum complete")
        
    except Exception as e:
        db.rollback()
        logger.error(f"   ❌ Error: {e}")
    finally:
        db.close()

def cleanup_ai_decisions(days_to_keep=30, dry_run=False):
    """Delete old AI decision logs"""
    logger.info(f"🗑️  CLEANING AI DECISIONS (keep {days_to_keep} days)...")
    db = SessionLocal()
    
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        # Count rows to delete
        count_query = text("""
            SELECT COUNT(*) FROM ai_decisions 
            WHERE created_at < :cutoff
        """)
        count_result = db.execute(count_query, {"cutoff": cutoff_date})
        rows_to_delete = count_result.scalar()
        
        if rows_to_delete == 0:
            logger.info(f"   ✓ No decisions older than {days_to_keep} days found")
            return
        
        logger.warning(f"   📊 Will delete {rows_to_delete:,} rows")
        
        if dry_run:
            logger.info("   [DRY RUN] No changes made")
            return
        
        # Delete
        delete_query = text("""
            DELETE FROM ai_decisions 
            WHERE created_at < :cutoff
        """)
        db.execute(delete_query, {"cutoff": cutoff_date})
        db.commit()
        logger.info(f"   ✅ Deleted {rows_to_delete:,} rows")
        
        # Vacuum
        db.execute(text("VACUUM ANALYZE ai_decisions"))
        
    except Exception as e:
        db.rollback()
        logger.error(f"   ❌ Error: {e}")
    finally:
        db.close()

def cleanup_old_trades(days_to_keep=180, dry_run=False):
    """Delete CLOSED/CANCELLED trades older than cutoff"""
    logger.info(f"🗑️  CLEANING OLD CLOSED TRADES (keep {days_to_keep} days)...")
    db = SessionLocal()
    
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        # Count rows to delete
        count_query = text("""
            SELECT COUNT(*) FROM trades 
            WHERE (status = 'CLOSED' OR status = 'CANCELLED')
            AND updated_at < :cutoff
        """)
        count_result = db.execute(count_query, {"cutoff": cutoff_date})
        rows_to_delete = count_result.scalar()
        
        if rows_to_delete == 0:
            logger.info(f"   ✓ No closed trades older than {days_to_keep} days found")
            return
        
        logger.warning(f"   📊 Will delete {rows_to_delete:,} closed/cancelled trades")
        
        if dry_run:
            logger.info("   [DRY RUN] No changes made")
            return
        
        # Delete
        delete_query = text("""
            DELETE FROM trades 
            WHERE (status = 'CLOSED' OR status = 'CANCELLED')
            AND updated_at < :cutoff
        """)
        db.execute(delete_query, {"cutoff": cutoff_date})
        db.commit()
        logger.info(f"   ✅ Deleted {rows_to_delete:,} rows")
        
        # Vacuum
        db.execute(text("VACUUM ANALYZE trades"))
        
    except Exception as e:
        db.rollback()
        logger.error(f"   ❌ Error: {e}")
    finally:
        db.close()

def cleanup_risk_events(days_to_keep=30, dry_run=False):
    """Delete old risk events"""
    logger.info(f"🗑️  CLEANING OLD RISK EVENTS (keep {days_to_keep} days)...")
    db = SessionLocal()
    
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        count_query = text("""
            SELECT COUNT(*) FROM risk_events 
            WHERE created_at < :cutoff
        """)
        count_result = db.execute(count_query, {"cutoff": cutoff_date})
        rows_to_delete = count_result.scalar()
        
        if rows_to_delete == 0:
            logger.info(f"   ✓ No events older than {days_to_keep} days found")
            return
        
        logger.warning(f"   📊 Will delete {rows_to_delete:,} rows")
        
        if dry_run:
            logger.info("   [DRY RUN] No changes made")
            return
        
        delete_query = text("""
            DELETE FROM risk_events 
            WHERE created_at < :cutoff
        """)
        db.execute(delete_query, {"cutoff": cutoff_date})
        db.commit()
        logger.info(f"   ✅ Deleted {rows_to_delete:,} rows")
        
        db.execute(text("VACUUM ANALYZE risk_events"))
        
    except Exception as e:
        db.rollback()
        logger.error(f"   ❌ Error: {e}")
    finally:
        db.close()

def run_cleanup(aggressive=False, dry_run=False):
    """Run cleanup sequence"""
    print("\n" + "=" * 80)
    print("🧹 CRBOT DATABASE CLEANUP - EMERGENCY RECOVERY MODE")
    print("=" * 80 + "\n")
    
    if dry_run:
        print("🔍 DRY RUN MODE - No data will be deleted\n")
    
    analyze_storage()
    
    print("=" * 80)
    print("🗑️  STARTING CLEANUP SEQUENCE...\n")
    print("=" * 80 + "\n")
    
    # Priority order for space recovery
    if aggressive:
        logger.info("⚠️  AGGRESSIVE MODE - Short retention periods")
        cleanup_crypto_market_data(days_to_keep=30, dry_run=dry_run)
        cleanup_ai_decisions(days_to_keep=7, dry_run=dry_run)
        cleanup_old_trades(days_to_keep=90, dry_run=dry_run)
        cleanup_risk_events(days_to_keep=7, dry_run=dry_run)
    else:
        logger.info("ℹ️  NORMAL MODE - Standard retention periods")
        cleanup_crypto_market_data(days_to_keep=90, dry_run=dry_run)
        cleanup_ai_decisions(days_to_keep=30, dry_run=dry_run)
        cleanup_old_trades(days_to_keep=180, dry_run=dry_run)
        cleanup_risk_events(days_to_keep=30, dry_run=dry_run)
    
    print("\n" + "=" * 80)
    analyze_storage()
    print("=" * 80)
    
    if not dry_run:
        logger.info("✅ CLEANUP COMPLETE - Database space recovered!")
    else:
        logger.info("✅ DRY RUN COMPLETE - Run without --dry-run to apply changes")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="🧹 Clean old data from CRBot database to recover disk space"
    )
    parser.add_argument(
        "--aggressive",
        action="store_true",
        help="Use aggressive cleanup (30-day retention for crypto data)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without deleting"
    )
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Show storage usage and exit"
    )
    
    args = parser.parse_args()
    
    if args.analyze:
        analyze_storage()
    else:
        run_cleanup(aggressive=args.aggressive, dry_run=args.dry_run)
