-- =====================================================
-- CRBOT DATABASE SCHEMA
-- PostgreSQL 15 - Production-ready
-- =====================================================

-- Create UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ===================== ENUMS =====================
CREATE TYPE trade_status AS ENUM ('OPEN', 'CLOSED', 'CANCELLED');
CREATE TYPE trade_type AS ENUM ('LONG', 'SHORT');
CREATE TYPE order_status AS ENUM ('PENDING', 'FILLED', 'CANCELED', 'PARTIALLY_FILLED');
CREATE TYPE risk_level AS ENUM ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL');
CREATE TYPE bot_status AS ENUM ('IDLE', 'RUNNING', 'PAUSED', 'ERROR');

-- ===================== BOTS TABLE =====================
CREATE TABLE bots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL UNIQUE,
    strategy VARCHAR(100) NOT NULL,
    exchange VARCHAR(50) NOT NULL,
    trading_pair VARCHAR(20) NOT NULL,
    status bot_status DEFAULT 'IDLE',
    
    -- Configuration
    initial_capital DECIMAL(20, 8) NOT NULL,
    max_drawdown_limit DECIMAL(5, 2) DEFAULT 10.0,
    daily_loss_limit DECIMAL(20, 8),
    position_size_method VARCHAR(50) DEFAULT 'FIXED_PERCENT',
    risk_per_trade DECIMAL(5, 2) DEFAULT 2.0,
    
    -- Performance metrics
    total_profit_loss DECIMAL(20, 8) DEFAULT 0,
    win_rate DECIMAL(5, 2) DEFAULT 0,
    total_trades INT DEFAULT 0,
    winning_trades INT DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_trade_at TIMESTAMP,
    
    INDEX idx_status (status),
    INDEX idx_exchange_pair (exchange, trading_pair),
    INDEX idx_created_at (created_at DESC)
);

-- ===================== TRADES TABLE =====================
CREATE TABLE trades (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    bot_id UUID NOT NULL REFERENCES bots(id) ON DELETE CASCADE,
    
    -- Trade details
    symbol VARCHAR(20) NOT NULL,
    trade_type trade_type NOT NULL,
    status trade_status NOT NULL DEFAULT 'OPEN',
    
    -- Entry
    entry_price DECIMAL(20, 8) NOT NULL,
    entry_time TIMESTAMP NOT NULL,
    entry_quantity DECIMAL(20, 8) NOT NULL,
    
    -- Exit
    exit_price DECIMAL(20, 8),
    exit_time TIMESTAMP,
    exit_quantity DECIMAL(20, 8),
    
    -- Risk management
    stop_loss DECIMAL(20, 8) NOT NULL,
    take_profit DECIMAL(20, 8),
    risk_amount DECIMAL(20, 8) NOT NULL,
    reward_amount DECIMAL(20, 8),
    
    -- Results
    profit_loss DECIMAL(20, 8),
    profit_loss_percent DECIMAL(10, 2),
    fees DECIMAL(20, 8) DEFAULT 0,
    
    -- Metadata
    strategy_used VARCHAR(100) NOT NULL,
    notes TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_bot_id (bot_id),
    INDEX idx_symbol (symbol),
    INDEX idx_status (status),
    INDEX idx_entry_time (entry_time DESC),
    INDEX idx_exit_time (exit_time DESC),
    INDEX idx_profit (profit_loss DESC)
);

-- ===================== STRATEGY_PERFORMANCE TABLE =====================
CREATE TABLE strategy_performance (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    bot_id UUID NOT NULL REFERENCES bots(id) ON DELETE CASCADE,
    strategy_name VARCHAR(100) NOT NULL,
    
    -- Period metrics
    period_start TIMESTAMP NOT NULL,
    period_end TIMESTAMP NOT NULL,
    
    -- Performance
    trades_count INT DEFAULT 0,
    winning_trades INT DEFAULT 0,
    losing_trades INT DEFAULT 0,
    total_profit_loss DECIMAL(20, 8) DEFAULT 0,
    
    -- Analytics
    win_rate DECIMAL(5, 2),
    profit_factor DECIMAL(10, 4),
    sharpe_ratio DECIMAL(10, 4),
    sortino_ratio DECIMAL(10, 4),
    max_drawdown DECIMAL(10, 2),
    average_win DECIMAL(20, 8),
    average_loss DECIMAL(20, 8),
    largest_win DECIMAL(20, 8),
    largest_loss DECIMAL(20, 8),
    
    -- Risk metrics
    consecutive_wins INT DEFAULT 0,
    consecutive_losses INT DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_bot_strategy (bot_id, strategy_name),
    INDEX idx_period (period_start, period_end)
);

-- ===================== BOT_METRICS TABLE =====================
CREATE TABLE bot_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    bot_id UUID NOT NULL REFERENCES bots(id) ON DELETE CASCADE,
    
    -- Portfolio value
    equity DECIMAL(20, 8) NOT NULL,
    cash DECIMAL(20, 8) NOT NULL,
    positions_value DECIMAL(20, 8) NOT NULL,
    
    -- Performance
    daily_pnl DECIMAL(20, 8),
    cumulative_pnl DECIMAL(20, 8),
    
    -- Risk
    current_drawdown DECIMAL(10, 2),
    max_drawdown DECIMAL(10, 2),
    
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_bot_id (bot_id),
    INDEX idx_recorded_at (recorded_at DESC)
);

-- ===================== RISK_EVENTS TABLE =====================
CREATE TABLE risk_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    bot_id UUID NOT NULL REFERENCES bots(id) ON DELETE CASCADE,
    
    event_type VARCHAR(100) NOT NULL,
    risk_level risk_level NOT NULL,
    description TEXT NOT NULL,
    
    -- Trigger values
    threshold_value DECIMAL(20, 8),
    current_value DECIMAL(20, 8),
    
    -- Resolution
    resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP,
    resolution_action VARCHAR(255),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_bot_id (bot_id),
    INDEX idx_risk_level (risk_level),
    INDEX idx_resolved (resolved),
    INDEX idx_created_at (created_at DESC)
);

-- ===================== EQUITY_CURVE TABLE =====================
CREATE TABLE equity_curve (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    bot_id UUID NOT NULL REFERENCES bots(id) ON DELETE CASCADE,
    
    equity_value DECIMAL(20, 8) NOT NULL,
    cash_value DECIMAL(20, 8) NOT NULL,
    recorded_at TIMESTAMP NOT NULL,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_bot_recorded (bot_id, recorded_at DESC),
    INDEX idx_recorded_at (recorded_at DESC)
);

-- ===================== MATERIALIZED VIEWS =====================

-- Dashboard Summary View
CREATE MATERIALIZED VIEW mv_dashboard_summary AS
SELECT 
    b.id,
    b.name,
    b.strategy,
    b.exchange,
    b.trading_pair,
    b.status,
    b.initial_capital,
    b.total_profit_loss,
    b.win_rate,
    b.total_trades,
    b.winning_trades,
    (b.total_profit_loss / b.initial_capital * 100) AS roi_percent,
    b.created_at,
    b.updated_at,
    COUNT(CASE WHEN t.status = 'OPEN' THEN 1 END) AS open_trades_count
FROM bots b
LEFT JOIN trades t ON b.id = t.bot_id
GROUP BY b.id;

-- Recent Trades View
CREATE MATERIALIZED VIEW mv_recent_trades AS
SELECT 
    t.id,
    t.bot_id,
    b.name AS bot_name,
    t.symbol,
    t.trade_type,
    t.status,
    t.entry_price,
    t.entry_time,
    t.exit_price,
    t.exit_time,
    t.profit_loss,
    t.profit_loss_percent,
    t.strategy_used
FROM trades t
LEFT JOIN bots b ON t.bot_id = b.id
ORDER BY t.entry_time DESC
LIMIT 100;

-- Strategy Comparison View
CREATE MATERIALIZED VIEW mv_strategy_comparison AS
SELECT 
    strategy_name,
    COUNT(*) AS total_tests,
    AVG(win_rate) AS avg_win_rate,
    AVG(profit_factor) AS avg_profit_factor,
    AVG(max_drawdown) AS avg_max_drawdown,
    SUM(total_profit_loss) AS total_profit,
    AVG(sharpe_ratio) AS avg_sharpe
FROM strategy_performance
GROUP BY strategy_name;

-- ===================== INDEXES =====================
CREATE INDEX idx_trades_symbol_trgm ON trades USING GIN (symbol gin_trgm_ops);
CREATE INDEX idx_bots_name_trgm ON bots USING GIN (name gin_trgm_ops);

-- ===================== TRIGGERS =====================

-- Update bot.updated_at when trades change
CREATE OR REPLACE FUNCTION update_bot_metrics()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE bots SET updated_at = CURRENT_TIMESTAMP 
    WHERE id = NEW.bot_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_bot_on_trade
AFTER INSERT OR UPDATE ON trades
FOR EACH ROW
EXECUTE FUNCTION update_bot_metrics();

-- ===================== GRANTS =====================
-- Application user (read/write)
CREATE USER crbot_app WITH PASSWORD 'crbot_app_secure_password';
GRANT CONNECT ON DATABASE crbot TO crbot_app;
GRANT USAGE ON SCHEMA public TO crbot_app;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO crbot_app;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO crbot_app;

-- Analytics user (read-only)
CREATE USER crbot_analytics WITH PASSWORD 'crbot_analytics_read_only';
GRANT CONNECT ON DATABASE crbot TO crbot_analytics;
GRANT USAGE ON SCHEMA public TO crbot_analytics;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO crbot_analytics;
GRANT SELECT ON ALL MATERIALIZED VIEWS IN SCHEMA public TO crbot_analytics;
