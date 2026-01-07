"""
Apply watchlist schema migration to Supabase database
"""
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables from backend/.env
env_path = Path(__file__).parent.parent / "backend" / ".env"
load_dotenv(env_path)

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("ERROR: DATABASE_URL not found in environment variables")
    print(f"Tried loading from: {env_path}")
    sys.exit(1)

print(f"Connecting to database...")

engine = create_engine(DATABASE_URL)

# Read migration SQL
migration_file = Path(__file__).parent.parent / "database" / "migrations" / "004_fix_watchlist_schema.sql"

with open(migration_file, 'r', encoding='utf-8') as f:
    sql = f.read()

print(f"Applying migration from {migration_file.name}...")

try:
    with engine.connect() as conn:
        # Execute migration
        conn.execute(text(sql))
        conn.commit()
        print("✅ Migration applied successfully!")
        
        # Verify table exists
        result = conn.execute(text("""
            SELECT COUNT(*) as count FROM watchlist_items
        """))
        count = result.scalar()
        print(f"✅ watchlist_items table has {count} rows")
        
except Exception as e:
    print(f"❌ Error applying migration: {e}")
    sys.exit(1)
