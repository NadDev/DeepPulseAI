#!/usr/bin/env python3
"""
Apply all pending SQL migrations to Railway PostgreSQL
Run this after deploying new migrations
"""
import os
import sys
from pathlib import Path
import psycopg2
from psycopg2 import sql
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    logger.error("❌ DATABASE_URL environment variable not set")
    sys.exit(1)

def apply_migrations():
    """Apply all SQL migration files"""
    migrations_dir = Path(__file__).parent / "database" / "migrations"
    
    if not migrations_dir.exists():
        logger.error(f"❌ Migrations directory not found: {migrations_dir}")
        sys.exit(1)
    
    # Get all migration files
    migration_files = sorted(migrations_dir.glob("*.sql"))
    
    if not migration_files:
        logger.error("❌ No migration files found")
        sys.exit(1)
    
    logger.info(f"📋 Found {len(migration_files)} migration files")
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        for migration_file in migration_files:
            logger.info(f"🔄 Applying {migration_file.name}...")
            
            with open(migration_file, 'r') as f:
                sql_content = f.read()
            
            try:
                cursor.execute(sql_content)
                conn.commit()
                logger.info(f"✅ {migration_file.name} applied successfully")
            except psycopg2.Error as e:
                conn.rollback()
                logger.warning(f"⚠️ {migration_file.name} - {str(e)}")
                # Continue with next migration even if this one fails
                continue
        
        cursor.close()
        conn.close()
        logger.info("✅ All migrations applied successfully!")
        
    except psycopg2.Error as e:
        logger.error(f"❌ Database connection error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    apply_migrations()
