"""
Migration script to add user_id column to trades and bots tables
Run this once to update the existing SQLite database schema
"""
import sqlite3
import os

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), "crbot.db")

def migrate():
    print(f"🔧 Migrating database: {DB_PATH}")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Add user_id to trades table
        print("📝 Adding user_id column to trades table...")
        cursor.execute("""
            ALTER TABLE trades ADD COLUMN user_id VARCHAR(50);
        """)
        print("✅ trades.user_id added")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("⚠️  trades.user_id already exists")
        else:
            raise
    
    try:
        # Add user_id to bots table
        print("📝 Adding user_id column to bots table...")
        cursor.execute("""
            ALTER TABLE bots ADD COLUMN user_id VARCHAR(50);
        """)
        print("✅ bots.user_id added")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("⚠️  bots.user_id already exists")
        else:
            raise
    
    # Create indexes for better performance
    try:
        print("📝 Creating index on trades.user_id...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_trades_user_id ON trades(user_id);
        """)
        print("✅ Index created on trades.user_id")
    except Exception as e:
        print(f"⚠️  Index creation failed: {e}")
    
    try:
        print("📝 Creating index on bots.user_id...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_bots_user_id ON bots(user_id);
        """)
        print("✅ Index created on bots.user_id")
    except Exception as e:
        print(f"⚠️  Index creation failed: {e}")
    
    conn.commit()
    conn.close()
    
    print("🎉 Migration completed successfully!")
    print("⚠️  Note: Existing data will have NULL user_id values")

if __name__ == "__main__":
    migrate()
