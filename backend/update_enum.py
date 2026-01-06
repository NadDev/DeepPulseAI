"""Add RUNNING to bot_status enum"""
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')

engine = create_engine(DATABASE_URL)
with engine.connect() as conn:
    # Add RUNNING to bot_status enum if not exists
    try:
        conn.execute(text("ALTER TYPE bot_status ADD VALUE IF NOT EXISTS 'RUNNING'"))
        conn.commit()
        print('✅ Added RUNNING to bot_status enum')
    except Exception as e:
        print(f'Note: {e}')
    
    # List current enum values
    result = conn.execute(text("SELECT enumlabel FROM pg_enum WHERE enumtypid = 'bot_status'::regtype"))
    print('Current bot_status values:', [r[0] for r in result])
