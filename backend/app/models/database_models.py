from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text
from sqlalchemy.sql import func
from app.db.database import Base

class Portfolio(Base):
    __tablename__ = "portfolios"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), unique=True, index=True)
    total_value = Column(Float, default=100000.0)
    cash_balance = Column(Float, default=100000.0)
    daily_pnl = Column(Float, default=0.0)
    total_pnl = Column(Float, default=0.0)
    win_rate = Column(Float, default=0.0)
    max_drawdown = Column(Float, default=0.0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class Trade(Base):
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, index=True)
    bot_id = Column(String(50), index=True)
    symbol = Column(String(20), index=True)
    side = Column(String(10))  # BUY or SELL
    entry_price = Column(Float)
    exit_price = Column(Float, nullable=True)
    quantity = Column(Float)
    pnl = Column(Float, nullable=True)
    pnl_percent = Column(Float, nullable=True)
    status = Column(String(20))  # OPEN, CLOSED
    entry_time = Column(DateTime)
    exit_time = Column(DateTime, nullable=True)
    strategy = Column(String(50))
    # FEATURE 1.1: Trading Limits
    stop_loss_price = Column(Float, nullable=True)
    take_profit_price = Column(Float, nullable=True)
    trailing_stop_percent = Column(Float, nullable=True)
    max_loss_amount = Column(Float, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

class Bot(Base):
    __tablename__ = "bots"
    
    id = Column(String(50), primary_key=True, index=True)
    name = Column(String(100))
    strategy = Column(String(50))
    status = Column(String(20))  # ACTIVE, INACTIVE, PAUSED
    risk_percent = Column(Float, default=2.0)
    max_drawdown = Column(Float, default=20.0)
    is_live = Column(Boolean, default=False)
    total_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)
    total_pnl = Column(Float, default=0.0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class StrategyPerformance(Base):
    __tablename__ = "strategy_performance"
    
    id = Column(Integer, primary_key=True, index=True)
    strategy_name = Column(String(50), index=True)
    symbol = Column(String(20), index=True)
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)
    avg_win = Column(Float, default=0.0)
    avg_loss = Column(Float, default=0.0)
    profit_factor = Column(Float, default=0.0)
    sharpe_ratio = Column(Float, default=0.0)
    max_drawdown = Column(Float, default=0.0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class RiskEvent(Base):
    __tablename__ = "risk_events"
    
    id = Column(Integer, primary_key=True, index=True)
    bot_id = Column(String(50), index=True)
    event_type = Column(String(50))  # DRAWDOWN_LIMIT, DAILY_LOSS, CORRELATION_HIGH
    severity = Column(String(20))  # INFO, WARNING, CRITICAL
    message = Column(Text)
    action_taken = Column(String(100), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

class SentimentData(Base):
    __tablename__ = "sentiment_data"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), index=True)
    sentiment_score = Column(Float)  # -1.0 to 1.0
    fear_greed_index = Column(Float)  # 0 to 100
    source = Column(String(50))  # twitter, news, etc
    created_at = Column(DateTime, server_default=func.now())
