#!/usr/bin/env python
"""
Test connection to Supabase PostgreSQL
Run: python test_db_connection.py
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set in .env")
    exit(1)

print(f"Testing connection to: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'LOCAL'}\n")

try:
    engine = create_engine(DATABASE_URL, echo=False, connect_args={"timeout": 5})
    
    with engine.connect() as conn:
        # Test basic connection
        result = conn.execute(text("SELECT 1"))
        print("✅ Connection successful!")
        
        # Get version
        version = conn.execute(text("SELECT version()")).scalar()
        print(f"✅ Database version: {version.split(',')[0]}\n")
        
        # List tables
        tables_query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        ORDER BY table_name
        """
        tables = conn.execute(text(tables_query)).fetchall()
        
        if tables:
            print(f"✅ Found {len(tables)} tables:")
            for table in tables:
                print(f"   - {table[0]}")
        else:
            print("⚠️  No tables found. Run: python seed_data.py")
        
        print("\n✅ All checks passed!")
        
except Exception as e:
    print(f"❌ Connection failed: {e}")
    print("\nTroubleshooting:")
    print("1. Check DATABASE_URL in .env")
    print("2. Verify Supabase is running")
    print("3. Check firewall settings")
    exit(1)
