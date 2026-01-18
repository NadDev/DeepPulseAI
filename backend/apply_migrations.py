#!/usr/bin/env python3
"""
Apply all pending SQL migrations to Railway PostgreSQL
Run this after deploying new migrations

This script tracks which migrations have been applied using schema_migrations table
to avoid re-applying migrations and to handle failures gracefully.
"""
import os
import sys
from pathlib import Path
import psycopg2
from psycopg2 import sql
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    logger.error("❌ DATABASE_URL environment variable not set")
    logger.info("Set it with: export DATABASE_URL='postgresql://user:pass@host:port/db'")
    sys.exit(1)

def get_applied_migrations(cursor):
    """Get list of already applied migrations from database"""
    try:
        cursor.execute("""
            SELECT migration_name FROM schema_migrations 
            ORDER BY applied_at
        """)
        applied = {row[0] for row in cursor.fetchall()}
        logger.info(f"✅ Database has {len(applied)} migrations already applied")
        return applied
    except psycopg2.Error as e:
        # Table doesn't exist yet, need to create it
        logger.info("📋 Creating schema_migrations tracking table...")
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    id SERIAL PRIMARY KEY,
                    migration_name VARCHAR(255) UNIQUE NOT NULL,
                    applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            logger.info("✅ schema_migrations table created")
            return set()
        except psycopg2.Error as create_error:
            logger.error(f"❌ Failed to create schema_migrations table: {create_error}")
            raise

def apply_migrations():
    """Apply all SQL migration files that haven't been applied yet"""
    migrations_dir = Path(__file__).parent / "database" / "migrations"
    
    if not migrations_dir.exists():
        logger.error(f"❌ Migrations directory not found: {migrations_dir}")
        sys.exit(1)
    
    # Get all migration files sorted by name
    migration_files = sorted(migrations_dir.glob("*.sql"))
    
    if not migration_files:
        logger.error("❌ No migration files found")
        sys.exit(1)
    
    logger.info(f"📋 Found {len(migration_files)} migration files available")
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Get already applied migrations
        applied = get_applied_migrations(cursor)
        
        pending_migrations = []
        
        for migration_file in migration_files:
            migration_name = migration_file.name
            
            # Skip if already applied
            if migration_name in applied:
                logger.info(f"⏭️  {migration_name} (already applied)")
                continue
            
            pending_migrations.append((migration_name, migration_file))
        
        if not pending_migrations:
            logger.info("✅ All migrations already applied!")
            cursor.close()
            conn.close()
            return
        
        logger.info(f"🔄 Applying {len(pending_migrations)} pending migration(s)...")
        
        for migration_name, migration_file in pending_migrations:
            logger.info(f"🔄 [{pending_migrations.index((migration_name, migration_file)) + 1}/{len(pending_migrations)}] {migration_name}...")
            
            try:
                with open(migration_file, 'r') as f:
                    sql_content = f.read()
                
                # Execute migration
                cursor.execute(sql_content)
                
                # Record that migration was applied
                cursor.execute(
                    "INSERT INTO schema_migrations (migration_name) VALUES (%s)",
                    (migration_name,)
                )
                
                conn.commit()
                logger.info(f"✅ {migration_name} applied successfully")
                
            except psycopg2.Error as e:
                conn.rollback()
                logger.error(f"❌ {migration_name} FAILED")
                logger.error(f"   Error: {str(e)}")
                logger.warning(f"⚠️  Continuing with next migration...")
                continue
            except Exception as e:
                conn.rollback()
                logger.error(f"❌ {migration_name} FAILED with unexpected error")
                logger.error(f"   Error: {str(e)}")
                continue
        
        cursor.close()
        conn.close()
        logger.info("✅ Migration process completed!")
        
    except psycopg2.OperationalError as e:
        logger.error(f"❌ Database connection failed: {e}")
        logger.error("Check your DATABASE_URL environment variable")
        sys.exit(1)

if __name__ == "__main__":
    apply_migrations()

if __name__ == "__main__":
    apply_migrations()
