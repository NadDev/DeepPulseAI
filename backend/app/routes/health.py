from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.database_models import Portfolio, Trade
from sqlalchemy import desc, text
from datetime import datetime, timedelta
from pathlib import Path
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["health"])

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "CRBot API"
    }

@router.get("/ready")
async def ready_check(db: Session = Depends(get_db)):
    """Readiness check with database connection"""
    try:
        db.execute(text("SELECT 1"))
        return {"ready": True, "database": "connected"}
    except Exception as e:
        return {"ready": False, "error": str(e)}

@router.post("/apply-migrations")
async def apply_migrations(db: Session = Depends(get_db)):
    """Apply pending SQL migrations - ADMIN ONLY"""
    try:
        migrations_dir = Path(__file__).parent.parent.parent / "database" / "migrations"
        migration_files = sorted(migrations_dir.glob("*.sql"))
        
        results = []
        
        for migration_file in migration_files:
            try:
                with open(migration_file, 'r') as f:
                    sql_content = f.read()
                
                db.execute(text(sql_content))
                db.commit()
                results.append({"file": migration_file.name, "status": "✅ applied"})
                logger.info(f"✅ Applied migration: {migration_file.name}")
            except Exception as e:
                db.rollback()
                results.append({"file": migration_file.name, "status": f"⚠️ {str(e)[:100]}"})
                logger.warning(f"⚠️ Migration {migration_file.name} failed: {str(e)}")
                continue
        
        return {
            "message": "Migrations application completed",
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        logger.error(f"❌ Migration error: {str(e)}")
        return {"error": str(e)}

@router.post("/create-ai-decisions-table")
async def create_ai_decisions_table(db: Session = Depends(get_db)):
    """Create ai_decisions table if it doesn't exist - EMERGENCY FIX"""
    try:
        # First check if table exists
        try:
            db.execute(text("SELECT 1 FROM ai_decisions LIMIT 1"))
            return {"status": "✅ ai_decisions table already exists"}
        except:
            pass
        
        # Table doesn't exist, create it
        logger.info("⚙️ Creating ai_decisions table...")
        
        # Use Railway-compatible migration (without Supabase dependencies)
        migration_paths = [
            Path(__file__).parent.parent.parent / "database" / "migrations" / "001_create_ai_decisions_table_railway.sql",
            Path("/app/database/migrations/001_create_ai_decisions_table_railway.sql"),
            Path("database/migrations/001_create_ai_decisions_table_railway.sql"),
        ]
        
        migration_sql = None
        found_path = None
        
        for path in migration_paths:
            try:
                migration_sql = open(path).read()
                found_path = path
                break
            except:
                continue
        
        if not migration_sql:
            return {
                "status": "❌ FAILED",
                "error": "Could not find migration file",
                "tried_paths": [str(p) for p in migration_paths]
            }
        
        # Execute migration
        db.execute(text(migration_sql))
        db.commit()
        
        logger.info("✅ ai_decisions table created successfully")
        return {
            "status": "✅ ai_decisions table created",
            "migration_file": str(found_path),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to create ai_decisions table: {str(e)}")
        return {
            "status": "❌ FAILED",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

