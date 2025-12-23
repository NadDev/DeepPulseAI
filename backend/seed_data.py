#!/usr/bin/env python
"""
Seed script pour initialiser la base Supabase PostgreSQL avec des données de test
Run: python seed_data.py
"""

import os
import uuid
from datetime import datetime, timedelta
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Load environment
load_dotenv()

# Import models
from app.models.database_models import Base, Bot, Trade, Portfolio

# Get database URL
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set in .env")
    exit(1)

print(f"Connecting to: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'LOCAL'}")

# Create engine and tables
engine = create_engine(DATABASE_URL, echo=False)
Base.metadata.create_all(bind=engine)
print("✅ Tables created")

# Create session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

try:
    # Get or create test user ID (use a fixed UUID for testing)
    TEST_USER_ID = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")  # Fixed UUID for testing
    
    # Check if data already exists
    existing_bot = db.query(Bot).filter(Bot.user_id == TEST_USER_ID).first()
    if existing_bot:
        print("⚠️  Data already exists for test user. Skipping seed.")
        exit(0)
    
    print(f"\nSeeding data for user: {TEST_USER_ID}\n")
    
    # Create portfolio
    portfolio = Portfolio(
        user_id=TEST_USER_ID,
        total_value=100000.0,
        cash_balance=99850.0,
        daily_pnl=0.0,
        total_pnl=0.0,
        win_rate=0.0,
        max_drawdown=10.58
    )
    db.add(portfolio)
    db.commit()
    print("✅ Portfolio created")
    
    # Create bots
    bots_data = [
        {
            "name": "Trend Follower Bot",
            "strategy": "trend_following",
            "status": "PAUSED",
            "config": {
                "rsi_period": 14,
                "rsi_oversold": 30,
                "rsi_overbought": 70,
                "sma_fast": 20,
                "sma_slow": 50,
                "stop_loss_pct": 2,
                "risk_reward_ratio": 2
            },
            "symbols": ["BTCUSDT", "ETHUSDT"]
        },
        {
            "name": "Breakout Hunter",
            "strategy": "breakout",
            "status": "ACTIVE",
            "config": {
                "lookback_period": 20,
                "breakout_threshold": 0.5,
                "volume_multiplier": 1.5,
                "stop_loss_pct": 2,
                "profit_target_multiplier": 2
            },
            "symbols": ["BTCUSDT"]
        },
        {
            "name": "Mean Reversion Pro",
            "strategy": "mean_reversion",
            "status": "IDLE",
            "config": {
                "lookback_period": 20,
                "std_dev_threshold": 2,
                "mean_period": 20,
                "stop_loss_pct": 3,
                "take_profit_pct": 2
            },
            "symbols": ["ETHUSDT", "BNBUSDT"]
        }
    ]
    
    bots = []
    for bot_data in bots_data:
        bot = Bot(
            user_id=TEST_USER_ID,
            name=bot_data["name"],
            strategy=bot_data["strategy"],
            status=bot_data["status"],
            config=bot_data["config"],
            paper_trading=True,
            risk_percent=2.0,
            max_drawdown=20.0,
            is_live=False,
            total_trades=0,
            win_rate=0.0,
            total_pnl=0.0,
            symbols=bot_data["symbols"]
        )
        bots.append(bot)
        db.add(bot)
    
    db.commit()
    print(f"✅ {len(bots)} bots created")
    
    # Create sample trades
    now = datetime.utcnow()
    trades_data = [
        {
            "bot_id": bots[0].id,
            "symbol": "BTCUSDT",
            "side": "BUY",
            "status": "OPEN",
            "entry_price": 45000.0,
            "entry_time": now - timedelta(hours=2),
            "quantity": 0.5,
            "pnl": None,
            "pnl_percent": None,
            "strategy": "trend_following"
        },
        {
            "bot_id": bots[1].id,
            "symbol": "BTCUSDT",
            "side": "BUY",
            "status": "CLOSED",
            "entry_price": 44000.0,
            "entry_time": now - timedelta(days=1),
            "exit_price": 45500.0,
            "exit_time": now - timedelta(hours=12),
            "quantity": 1.0,
            "pnl": 1500.0,
            "pnl_percent": 3.41,
            "strategy": "breakout"
        }
    ]
    
    for trade_data in trades_data:
        trade = Trade(
            user_id=TEST_USER_ID,
            bot_id=trade_data["bot_id"],
            symbol=trade_data["symbol"],
            side=trade_data["side"],
            status=trade_data["status"],
            entry_price=trade_data["entry_price"],
            entry_time=trade_data["entry_time"],
            quantity=trade_data["quantity"],
            pnl=trade_data.get("pnl"),
            pnl_percent=trade_data.get("pnl_percent"),
            exit_price=trade_data.get("exit_price"),
            exit_time=trade_data.get("exit_time"),
            strategy=trade_data["strategy"]
        )
        db.add(trade)
    
    db.commit()
    print(f"✅ {len(trades_data)} trades created")
    
    print(f"\n✅ Seed complete!")
    print(f"   Test user: {TEST_USER_ID}")
    print(f"   Portfolio: $100,000")
    print(f"   Bots: {len(bots)}")
    print(f"   Trades: {len(trades_data)}")

except Exception as e:
    print(f"❌ Error: {e}")
    db.rollback()
    exit(1)

finally:
    db.close()
