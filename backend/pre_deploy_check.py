#!/usr/bin/env python
"""
Pre-deployment checklist for CRBot
Run: python pre_deploy_check.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import subprocess

load_dotenv()

print("=" * 70)
print("CRBot PRE-DEPLOYMENT CHECKLIST")
print("=" * 70)

checks_passed = 0
checks_failed = 0

def check(name, condition, error_msg=""):
    global checks_passed, checks_failed
    if condition:
        print(f"✅ {name}")
        checks_passed += 1
    else:
        print(f"❌ {name}")
        if error_msg:
            print(f"   {error_msg}")
        checks_failed += 1

# 1. Environment variables
print("\n📋 ENVIRONMENT VARIABLES")
check("ENV variable set", os.getenv("ENV"), "Missing ENV in .env")
check("SUPABASE_URL set", os.getenv("SUPABASE_URL"), "Missing SUPABASE_URL")
check("SUPABASE_ANON_KEY set", os.getenv("SUPABASE_ANON_KEY"), "Missing SUPABASE_ANON_KEY")
check("DATABASE_URL set", os.getenv("DATABASE_URL"), "Missing DATABASE_URL")
check("SECRET_KEY set", os.getenv("SECRET_KEY"), "Missing SECRET_KEY")

# 2. Files & Directories
print("\n📁 FILES & DIRECTORIES")
check("Dockerfile exists", Path("Dockerfile").exists(), "Missing backend/Dockerfile")
check("railway.json exists", Path("railway.json").exists(), "Missing backend/railway.json")
check("requirements.txt exists", Path("requirements.txt").exists(), "Missing backend/requirements.txt")
check("seed_data.py exists", Path("seed_data.py").exists(), "Missing backend/seed_data.py")
check("test_db_connection.py exists", Path("test_db_connection.py").exists(), "Missing backend/test_db_connection.py")

# 3. Database configuration
print("\n🗄️  DATABASE CONFIGURATION")
db_url = os.getenv("DATABASE_URL", "")
is_postgres = "postgresql" in db_url
check("Using PostgreSQL (not SQLite)", is_postgres, "DATABASE_URL should use postgresql:// not sqlite://")
check("DATABASE_URL contains host", "@" in db_url, "DATABASE_URL missing host (@ symbol)")

# 4. Python environment
print("\n🐍 PYTHON ENVIRONMENT")
try:
    import sqlalchemy
    check("SQLAlchemy installed", True)
except ImportError:
    check("SQLAlchemy installed", False, "Run: pip install -r requirements.txt")

try:
    import psycopg2
    check("psycopg2 installed", True)
except ImportError:
    check("psycopg2 installed", False, "Run: pip install psycopg2-binary")

try:
    import fastapi
    check("FastAPI installed", True)
except ImportError:
    check("FastAPI installed", False, "Run: pip install -r requirements.txt")

# 5. Database connectivity (optional - requires DATABASE_URL to be valid)
print("\n🔌 DATABASE CONNECTIVITY")
try:
    from sqlalchemy import create_engine, text
    
    engine = create_engine(os.getenv("DATABASE_URL"), echo=False)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        check("PostgreSQL connection works", True)
        
        # Check if tables exist
        tables_query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        """
        tables = conn.execute(text(tables_query)).fetchall()
        check(f"Database tables exist ({len(tables)} tables)", len(tables) > 0, 
              "Run: supabase_schema.sql in Supabase SQL Editor, then seed_data.py")
except Exception as e:
    check("PostgreSQL connection works", False, str(e))
    check("Database tables exist", False, "Skipped - no connection")

# 6. Frontend configuration
print("\n🎨 FRONTEND CONFIGURATION")
frontend_env = Path("../frontend/.env.production")
if frontend_env.exists():
    with open(frontend_env) as f:
        content = f.read()
        check("VITE_API_URL configured", "VITE_API_URL" in content, "Set VITE_API_URL in frontend/.env.production")
else:
    check("frontend/.env.production exists", False, "Create frontend/.env.production")

# 7. Docker build (optional)
print("\n🐳 DOCKER BUILD (Optional)")
try:
    result = subprocess.run(
        ["docker", "build", "-f", "Dockerfile", "-t", "crbot-backend:test", "."],
        capture_output=True,
        text=True,
        timeout=60
    )
    check("Docker image builds successfully", result.returncode == 0, 
          "Run: docker build locally to debug")
except Exception as e:
    print(f"⚠️  Docker build check skipped: {e}")

# Summary
print("\n" + "=" * 70)
print(f"RESULTS: {checks_passed} passed, {checks_failed} failed")
print("=" * 70)

if checks_failed == 0:
    print("\n✅ ALL CHECKS PASSED! Ready for deployment.\n")
    print("Next steps:")
    print("  1. If not already done: Run Supabase schema in SQL Editor")
    print("  2. Run: python seed_data.py")
    print("  3. Test locally: python -m uvicorn app.main:app --port 8002")
    print("  4. Push to GitHub and deploy on Railway")
    sys.exit(0)
else:
    print(f"\n❌ {checks_failed} CHECK(S) FAILED. Please fix before deploying.\n")
    sys.exit(1)
