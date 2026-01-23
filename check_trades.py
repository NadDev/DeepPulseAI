#!/usr/bin/env python3
import sys
sys.path.insert(0, 'backend')

from app.db.database import SessionLocal
from app.models.database_models import Trade, Portfolio, Bot

db = SessionLocal()

print("=" * 50)
print("DATABASE STATISTICS")
print("=" * 50)

# Count all trades
all_trades = db.query(Trade).count()
print(f'📊 Total trades in DB: {all_trades}')

# Count closed trades
closed_trades = db.query(Trade).filter(Trade.status == 'CLOSED').count()
print(f'📊 Closed trades in DB: {closed_trades}')

# Count open trades  
open_trades = db.query(Trade).filter(Trade.status == 'OPEN').count()
print(f'📊 Open trades in DB: {open_trades}')

# Check portfolios
portfolios = db.query(Portfolio).count()
print(f'💼 Portfolios in DB: {portfolios}')

# Check bots
bots = db.query(Bot).count()
print(f'🤖 Bots in DB: {bots}')

# Show sample trades
print('\n📋 Sample trades:')
trades = db.query(Trade).limit(5).all()
if trades:
    for t in trades:
        print(f'  - {t.symbol} | {t.status} | user_id: {t.user_id} | P&L: {t.pnl}')
else:
    print('  ❌ No trades found!')

# Check user counts
print('\n👥 Users with data:')
from sqlalchemy import func, distinct
user_trades = db.query(distinct(Trade.user_id)).count()
user_portfolios = db.query(distinct(Portfolio.user_id)).count()
print(f'  Users with trades: {user_trades}')
print(f'  Users with portfolio: {user_portfolios}')

db.close()
