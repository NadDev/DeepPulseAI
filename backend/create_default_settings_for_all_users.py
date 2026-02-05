"""
Create Default Trading Settings for All Users
==============================================
Ensures every user has a row in user_trading_settings.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.db.database import SessionLocal
from app.models.database_models import User, UserTradingSettings
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def create_missing_settings():
    """
    Create default BALANCED settings for users that don't have any.
    """
    db = SessionLocal()
    
    try:
        # Get all users
        all_users = db.query(User).all()
        logger.info(f"📊 Found {len(all_users)} users in system\n")
        
        # Get users with settings
        users_with_settings = {str(s.user_id) for s in db.query(UserTradingSettings).all()}
        logger.info(f"✅ {len(users_with_settings)} users already have settings")
        
        # Find missing users
        missing_count = 0
        created_count = 0
        
        for user in all_users:
            user_id_str = str(user.id)
            display_name = user.email or user.username or user_id_str
            
            if user_id_str not in users_with_settings:
                logger.info(f"⚠️  Creating settings for: {display_name}")
                
                # Create default BALANCED settings
                settings = UserTradingSettings(
                    user_id=user.id,
                    sl_tp_profile="BALANCED"
                    # All other fields will use SQLAlchemy defaults
                )
                db.add(settings)
                missing_count += 1
            else:
                # Show existing profile
                existing = db.query(UserTradingSettings).filter(
                    UserTradingSettings.user_id == user.id
                ).first()
                logger.info(f"✅ {display_name}: {existing.sl_tp_profile} (sl_fixed_pct={existing.sl_fixed_pct}%)")
        
        if missing_count > 0:
            db.commit()
            logger.info(f"\n🎉 Created default settings for {missing_count} users!")
        else:
            logger.info(f"\n✅ All users already have settings!")
        
        # Final summary
        final_count = db.query(UserTradingSettings).count()
        logger.info(f"\n📊 SUMMARY:")
        logger.info(f"   Total users:    {len(all_users)}")
        logger.info(f"   With settings:  {final_count}")
        logger.info(f"   Coverage:       {final_count}/{len(all_users)} ({final_count/len(all_users)*100:.0f}%)")
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("="*60)
    print("🔧 CREATING DEFAULT TRADING SETTINGS FOR ALL USERS")
    print("="*60 + "\n")
    
    create_missing_settings()
