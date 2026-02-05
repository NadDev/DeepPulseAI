"""
Check Missing Trading Settings
==============================
Diagnose users without trading settings and create defaults.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.db.database import SessionLocal
from app.models.database_models import User, UserTradingSettings
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def check_and_fix_missing_settings():
    """
    1. Count users vs user_trading_settings
    2. Identify users without settings
    3. Create default settings for them
    """
    db = SessionLocal()
    
    try:
        # 1. Count users
        user_count = db.query(User).count()
        logger.info(f"📊 Total users in system: {user_count}")
        
        # 2. Count user_trading_settings
        settings_count = db.query(UserTradingSettings).count()
        logger.info(f"📊 Users with trading settings: {settings_count}")
        
        # 3. Find users WITHOUT settings
        users = db.query(User).all()
        users_with_settings = {str(s.user_id) for s in db.query(UserTradingSettings).all()}
        
        missing_users = []
        for user in users:
            if str(user.id) not in users_with_settings:
                missing_users.append(user)
                logger.warning(f"⚠️  User {user.email or user.username} ({user.id}) has NO trading settings")
        
        if not missing_users:
            logger.info("✅ All users have trading settings!")
            return
        
        # 4. Summary
        logger.info(f"\n📋 SUMMARY:")
        logger.info(f"   Users without settings: {len(missing_users)} / {user_count}")
        logger.info(f"   Missing percentage: {len(missing_users)/user_count*100:.1f}%")
        
        # 5. Propose fix
        print("\n" + "="*60)
        print("💡 FIX REQUIRED:")
        print("="*60)
        print(f"Create default trading settings for {len(missing_users)} users")
        print("\nOptions:")
        print("  1) Run: python backend/create_default_settings_for_all_users.py")
        print("  2) Or execute SQL directly:")
        print("\n  INSERT INTO user_trading_settings (user_id, sl_tp_profile)")
        print("  SELECT id, 'BALANCED'")
        print("  FROM users")
        print("  WHERE id NOT IN (SELECT user_id FROM user_trading_settings);")
        print("="*60)
        
        # 6. Ask for confirmation to auto-fix
        response = input("\n🔧 Create default BALANCED settings for all missing users? (yes/no): ")
        
        if response.lower() in ['yes', 'y']:
            created_count = 0
            for user in missing_users:
                settings = UserTradingSettings(
                    user_id=user.id,
                    sl_tp_profile="BALANCED"
                )
                db.add(settings)
                created_count += 1
                logger.info(f"   ✅ Created settings for {user.email or user.username}")
            
            db.commit()
            logger.info(f"\n🎉 Successfully created settings for {created_count} users!")
        else:
            logger.info("❌ Skipped auto-fix. Run the SQL manually or use the script later.")
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    print("="*60)
    print("🔍 CHECKING USER TRADING SETTINGS COVERAGE")
    print("="*60 + "\n")
    
    check_and_fix_missing_settings()
