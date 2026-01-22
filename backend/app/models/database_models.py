from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from app.db.database import Base

class Portfolio(Base):
    __tablename__ = "portfolios"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), unique=True, index=True, nullable=False)
    total_value = Column(Float, default=100000.0)
    cash_balance = Column(Float, default=100000.0)
    daily_pnl = Column(Float, default=0.0)
    total_pnl = Column(Float, default=0.0)
    win_rate = Column(Float, default=0.0)
    max_drawdown = Column(Float, default=0.0)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class Trade(Base):
    __tablename__ = "trades"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), index=True, nullable=False)  # Supabase user UUID
    bot_id = Column(UUID(as_uuid=True), index=True)
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
    take_profit_price = Column(Float, nullable=True)  # TP1 or full TP
    take_profit_2 = Column(Float, nullable=True)  # Runner TP (for partial exits)
    trailing_stop_percent = Column(Float, nullable=True)
    max_loss_amount = Column(Float, nullable=True)
    # FEATURE 1.2: Intelligent SL/TP
    trade_phase = Column(String(20), nullable=True)  # PENDING, VALIDATED, TRAILING
    tp1_partial_executed = Column(Boolean, default=False)  # True if 50% exited at TP1
    # FEATURE 1.3: Market Context
    market_context = Column(String(50), nullable=True)  # STRONG_BULLISH, WEAK_BULLISH, STRONG_BEARISH, etc
    market_context_confidence = Column(Float, nullable=True)  # 0-100% confidence in market context
    created_at = Column(DateTime, server_default=func.now())

class Bot(Base):
    __tablename__ = "bots"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), index=True, nullable=False)  # Supabase user UUID
    name = Column(String(100))
    strategy = Column(String(50))  # trend_following, breakout, mean_reversion
    status = Column(String(20))  # ACTIVE, INACTIVE, PAUSED, ERROR
    config = Column(Text, nullable=True)  # JSON config for strategy parameters
    paper_trading = Column(Boolean, default=True)  # Paper trading mode
    risk_percent = Column(Float, default=2.0)
    max_drawdown = Column(Float, default=20.0)
    is_live = Column(Boolean, default=False)
    total_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)
    total_pnl = Column(Float, default=0.0)
    symbols = Column(Text, nullable=True)  # JSON array of symbols to trade
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class StrategyPerformance(Base):
    __tablename__ = "strategy_performance"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), index=True, nullable=False)
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
    user_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    bot_id = Column(UUID(as_uuid=True), index=True)
    event_type = Column(String(50))  # DRAWDOWN_LIMIT, DAILY_LOSS, CORRELATION_HIGH
    severity = Column(String(20))  # INFO, WARNING, CRITICAL
    message = Column(Text)
    action_taken = Column(String(100), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    __tablename__ = "sentiment_data"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    symbol = Column(String(20), index=True)
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), index=True)
    sentiment_score = Column(Float)  # -1.0 to 1.0
    fear_greed_index = Column(Float)  # 0 to 100
    source = Column(String(50))  # twitter, news, etc
    created_at = Column(DateTime, server_default=func.now())


class AIDecision(Base):
    """
    Logs all AI Agent decisions for analysis and backtesting
    Tracks every BUY/SELL/HOLD recommendation and whether it was executed
    """
    __tablename__ = "ai_decisions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    bot_id = Column(UUID(as_uuid=True), index=True, nullable=True)  # Bot that executed (if any)
    
    # === Decision Info ===
    symbol = Column(String(20), index=True, nullable=False)
    action = Column(String(10), index=True)  # BUY, SELL, HOLD
    confidence = Column(Integer)  # 0-100
    reasoning = Column(Text)  # AI reasoning
    
    # === Market Context ===
    entry_price = Column(Float, nullable=True)  # Market price at decision time
    target_price = Column(Float, nullable=True)  # Target if BUY/SELL
    stop_loss = Column(Float, nullable=True)  # Suggested stop loss
    risk_level = Column(String(10))  # LOW, MEDIUM, HIGH
    timeframe = Column(String(10), default="1h")  # 5m, 15m, 1h, 4h, 1d
    
    # === Execution Info ===
    executed = Column(Boolean, default=False, index=True)  # Was this decision executed?
    blocked = Column(Boolean, default=False)  # Was this decision blocked by safety checks?
    blocked_reason = Column(Text, nullable=True)  # Why it was blocked
    
    # === Mode & Context ===
    mode = Column(String(20))  # observation, paper, live (for controller) or advisory, autonomous (for engine)
    strategy_proposed = Column(String(50), nullable=True)  # Strategy that generated the signal
    ai_agrees = Column(Boolean, nullable=True)  # Did AI agree with strategy?
    
    # === Trade Result (if executed) ===
    trade_id = Column(UUID(as_uuid=True), index=True, nullable=True)  # Link to actual trade
    result_pnl = Column(Float, nullable=True)  # Profit/loss if closed
    result_pnl_percent = Column(Float, nullable=True)  # PnL %
    result_status = Column(String(20), nullable=True)  # OPEN, CLOSED, CANCELLED
    closed_at = Column(DateTime, nullable=True)  # When the trade closed
    
    # === Timestamps ===
    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class ExchangeConfig(Base):
    """
    Stores exchange/broker API configurations per user
    API keys are encrypted using Fernet symmetric encryption
    """
    __tablename__ = "exchange_configs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    
    # === Exchange Info ===
    exchange = Column(String(50), nullable=False)  # binance, kraken, coinbase, etc.
    name = Column(String(100), nullable=True)  # User-friendly name
    
    # === Credentials (Encrypted) ===
    api_key_encrypted = Column(Text, nullable=False)  # Encrypted API key
    api_secret_encrypted = Column(Text, nullable=False)  # Encrypted API secret
    passphrase_encrypted = Column(Text, nullable=True)  # For exchanges that require it (Coinbase Pro)
    
    # === Configuration ===
    is_active = Column(Boolean, default=True)  # Is this exchange active?
    is_default = Column(Boolean, default=False)  # Default exchange for user
    paper_trading = Column(Boolean, default=True)  # Paper trading mode (testnet)
    use_testnet = Column(Boolean, default=True)  # Use testnet/sandbox APIs
    
    # === Trading Limits ===
    max_trade_size = Column(Float, default=1000.0)  # Max trade size in quote currency
    max_daily_trades = Column(Integer, default=50)  # Max trades per day
    allowed_symbols = Column(Text, nullable=True)  # JSON array of allowed symbols
    
    # === Connection Status ===
    last_connection_test = Column(DateTime, nullable=True)
    connection_status = Column(String(20), default="untested")  # untested, connected, failed
    connection_error = Column(Text, nullable=True)  # Last error message
    
    # === Timestamps ===
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class WatchlistItem(Base):
    """
    Stores individual crypto symbols in user's watchlist
    Each user can have multiple symbols they want the AI to analyze
    """
    __tablename__ = "watchlist_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    
    # Symbol info
    symbol = Column(String(20), nullable=False)  # e.g., BTC/USDT
    base_currency = Column(String(10), nullable=True)  # e.g., BTC
    quote_currency = Column(String(10), nullable=True)  # e.g., USDT
    
    # Status
    is_active = Column(Boolean, default=True)  # Include in AI analysis
    priority = Column(Integer, default=0)  # Higher = analyzed first
    
    # User notes
    notes = Column(Text, nullable=True)  # Optional user notes
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class MLPrediction(Base):
    """
    Stores LSTM neural network predictions for cryptocurrency prices.
    Used for backtesting, model accuracy measurement, and signal validation.
    Enables Phase 1 of ML integration: persistance des prédictions LSTM.
    """
    __tablename__ = "ml_predictions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    symbol = Column(String(20), index=True, nullable=False)
    timestamp = Column(DateTime, server_default=func.now(), index=True)
    
    # === LSTM Predictions ===
    pred_1h = Column(Float, nullable=True)  # 1-hour ahead price prediction
    confidence_1h = Column(Float, nullable=True)  # Confidence 0-1
    pred_24h = Column(Float, nullable=True)  # 24-hour ahead prediction
    confidence_24h = Column(Float, nullable=True)  # Confidence 0-1
    pred_7d = Column(Float, nullable=True)  # 7-day ahead prediction
    confidence_7d = Column(Float, nullable=True)  # Confidence 0-1
    
    # === Context at Prediction Time ===
    current_price = Column(Float, nullable=False)  # Market price when prediction was made
    patterns = Column(JSON, nullable=True)  # Detected chart patterns ["bullish_engulfing", ...]
    
    # === Actual Prices (Filled Later) ===
    actual_price_1h = Column(Float, nullable=True)  # Actual price 1h after prediction
    actual_price_24h = Column(Float, nullable=True)  # Actual price 24h after prediction
    actual_price_7d = Column(Float, nullable=True)  # Actual price 7d after prediction
    actual_filled_at_1h = Column(DateTime, nullable=True)  # When 1h actual was filled
    actual_filled_at_24h = Column(DateTime, nullable=True)  # When 24h actual was filled
    actual_filled_at_7d = Column(DateTime, nullable=True)  # When 7d actual was filled
    
    # === Accuracy Metrics (Calculated After Actual Available) ===
    error_1h = Column(Float, nullable=True)  # (actual - predicted) / predicted * 100
    error_24h = Column(Float, nullable=True)  # Same for 24h
    error_7d = Column(Float, nullable=True)  # Same for 7d
    
    correct_direction_1h = Column(Boolean, nullable=True)  # Did price move as predicted?
    correct_direction_24h = Column(Boolean, nullable=True)
    correct_direction_7d = Column(Boolean, nullable=True)
    
    # === Metadata ===
    model_version = Column(String(20), default="lstm-1.0.0")  # Model version used
    lookback_days = Column(Integer, default=90)  # Days of historical data used
    
    # === Timestamps ===
    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<MLPrediction {self.symbol} pred_1h={self.pred_1h:.2f}±{self.confidence_1h:.2%} @ {self.timestamp}>"


# ============================================
# User Trading Settings
# Per-user SL/TP configuration and preferences
# ============================================
class UserTradingSettings(Base):
    """
    Stores per-user trading preferences including SL/TP profile selection.
    
    Profiles:
    - PRUDENT: Tight stops, secure gains quickly (beginners, volatile markets)
    - BALANCED: Standard risk/reward (most traders)
    - AGGRESSIVE: Wide stops, let profits run (trending markets, experienced)
    """
    __tablename__ = "user_trading_settings"
    
    # Primary key = user_id (one row per user)
    user_id = Column(UUID(as_uuid=True), primary_key=True)
    
    # ============================================
    # SL/TP Profile Selection
    # ============================================
    sl_tp_profile = Column(String(20), default="BALANCED", nullable=False)  # PRUDENT, BALANCED, AGGRESSIVE
    
    # ============================================
    # SL Configuration
    # ============================================
    sl_method = Column(String(20), default="ATR", nullable=False)  # ATR, STRUCTURE, FIXED_PCT, HYBRID
    sl_atr_multiplier = Column(Float, default=1.5)
    sl_fixed_pct = Column(Float, default=2.5)
    sl_min_distance = Column(Float, default=0.01)
    sl_max_pct = Column(Float, default=5.0)
    
    # ============================================
    # TP Configuration
    # ============================================
    tp1_risk_reward = Column(Float, default=1.5)  # R:R ratio for TP1
    tp1_exit_pct = Column(Float, default=50.0)    # % of position to exit at TP1
    tp2_risk_reward = Column(Float, default=3.0)  # R:R ratio for TP2
    
    # ============================================
    # Trailing Stop Configuration
    # ============================================
    enable_trailing_sl = Column(Boolean, default=True)
    trailing_activation_pct = Column(Float, default=1.5)
    trailing_distance_pct = Column(Float, default=1.0)
    
    # ============================================
    # Trade Phase Configuration
    # ============================================
    enable_trade_phases = Column(Boolean, default=True)
    validation_threshold_pct = Column(Float, default=0.5)
    move_sl_to_breakeven = Column(Boolean, default=True)
    
    # ============================================
    # Partial TP Configuration
    # ============================================
    enable_partial_tp = Column(Boolean, default=True)
    
    # ============================================
    # Risk Limits (per user override)
    # ============================================
    max_position_pct = Column(Float, default=25.0)
    max_daily_loss_pct = Column(Float, default=5.0)
    max_trades_per_day = Column(Integer, default=10)
    
    # ============================================
    # Timestamps
    # ============================================
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<UserTradingSettings user={self.user_id} profile={self.sl_tp_profile}>"


# ============================================
# SL/TP Profile Presets
# Default configurations for each profile
# ============================================
class SLTPProfilePreset(Base):
    """
    Stores default configurations for PRUDENT, BALANCED, AGGRESSIVE profiles.
    Used as reference/defaults when user doesn't override specific values.
    """
    __tablename__ = "sl_tp_profile_presets"
    
    profile_name = Column(String(20), primary_key=True)  # PRUDENT, BALANCED, AGGRESSIVE
    display_name = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    
    # SL Config
    sl_atr_multiplier = Column(Float, nullable=False)
    sl_fixed_pct = Column(Float, nullable=False)
    sl_max_pct = Column(Float, nullable=False)
    
    # TP Config
    tp1_risk_reward = Column(Float, nullable=False)
    tp1_exit_pct = Column(Float, nullable=False)
    tp2_risk_reward = Column(Float, nullable=False)
    
    # Trailing Config
    trailing_activation_pct = Column(Float, nullable=False)
    trailing_distance_pct = Column(Float, nullable=False)
    
    # Phase Config
    validation_threshold_pct = Column(Float, nullable=False)
    
    def __repr__(self):
        return f"<SLTPProfilePreset {self.profile_name}: SL={self.sl_fixed_pct}%, TP1={self.tp1_risk_reward}R>"


# ============================================
# Profile Presets Data (for seeding)
# ============================================
SLTP_PROFILE_PRESETS = {
    "PRUDENT": {
        "display_name": "Prudent",
        "description": "Conservative: tight stops, secure gains quickly. Best for beginners or volatile markets.",
        "sl_atr_multiplier": 1.0,
        "sl_fixed_pct": 1.5,
        "sl_max_pct": 3.0,
        "tp1_risk_reward": 1.3,
        "tp1_exit_pct": 70.0,
        "tp2_risk_reward": 2.0,
        "trailing_activation_pct": 1.0,
        "trailing_distance_pct": 0.75,
        "validation_threshold_pct": 0.3
    },
    "BALANCED": {
        "display_name": "Balanced",
        "description": "Balanced risk/reward. Good for most market conditions.",
        "sl_atr_multiplier": 1.5,
        "sl_fixed_pct": 2.5,
        "sl_max_pct": 5.0,
        "tp1_risk_reward": 1.5,
        "tp1_exit_pct": 50.0,
        "tp2_risk_reward": 3.0,
        "trailing_activation_pct": 1.5,
        "trailing_distance_pct": 1.0,
        "validation_threshold_pct": 0.5
    },
    "AGGRESSIVE": {
        "display_name": "Aggressive",
        "description": "Let profits run with wider stops. Best for trending markets and experienced traders.",
        "sl_atr_multiplier": 2.0,
        "sl_fixed_pct": 4.0,
        "sl_max_pct": 8.0,
        "tp1_risk_reward": 1.5,
        "tp1_exit_pct": 30.0,
        "tp2_risk_reward": 4.0,
        "trailing_activation_pct": 2.0,
        "trailing_distance_pct": 1.5,
        "validation_threshold_pct": 0.75
    }
}
