"""
Create a test user in Railway PostgreSQL database.
This allows bot creation to work with the foreign key constraint.
"""
import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ ERROR: DATABASE_URL not found")
    sys.exit(1)

try:
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        # User ID from the error message
        user_id = "0539799d-0842-4403-9fe2-243426a8c69f"
        
        # Check if user exists
        result = conn.execute(text("SELECT id FROM users WHERE id = :user_id"), {"user_id": user_id})
        existing_user = result.fetchone()
        
        if existing_user:
            print(f"✅ User {user_id} already exists")
        else:
            # Create the test user
            conn.execute(text("""
                INSERT INTO users (id, email) 
                VALUES (:user_id, 'test@example.com')
            """), {"user_id": user_id})
            conn.commit()
            print(f"✅ Created test user: {user_id}")
        
        # Also create a portfolio for this user
        portfolio_result = conn.execute(text("SELECT user_id FROM portfolios WHERE user_id = :user_id"), {"user_id": user_id})
        existing_portfolio = portfolio_result.fetchone()
        
        if existing_portfolio:
            print(f"✅ Portfolio for user {user_id} already exists")
        else:
            conn.execute(text("""
                INSERT INTO portfolios (user_id, total_value, cash_balance) 
                VALUES (:user_id, 100000.0, 100000.0)
            """), {"user_id": user_id})
            conn.commit()
            print(f"✅ Created portfolio for user: {user_id}")
        
        print("\n🎉 Test user and portfolio ready!")
        
except Exception as e:
    print(f"❌ ERROR: {e}")
    sys.exit(1)