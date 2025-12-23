-- =====================================================
-- CRBOT DATABASE SCHEMA FOR SUPABASE PostgreSQL
-- With user_id for multi-tenancy
-- Execute this in Supabase SQL Editor
-- =====================================================

-- Create UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ===================== ENUMS =====================
CREATE TYPE trade_status AS ENUM ('OPEN', 'CLOSED', 'CANCELLED');
CREATE TYPE bot_status AS ENUM ('IDLE', 'RUNNING', 'PAUSED', 'ERROR');

-- ===================== BOTS TABLE =====================
CREATE TABLE bots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    strategy VARCHAR(100) NOT NULL,
    status bot_status DEFAULT 'IDLE',
    
    -- Configuration
    config JSONB DEFAULT '{}'::jsonb,
    paper_trading BOOLEAN DEFAULT true,
    risk_percent DECIMAL(5, 2) DEFAULT 2.0,
    max_drawdown DECIMAL(5, 2) DEFAULT 20.0,
    
    -- Performance metrics
    is_live BOOLEAN DEFAULT false,
    total_trades INT DEFAULT 0,
    win_rate DECIMAL(5, 2) DEFAULT 0.0,
    total_pnl DECIMAL(20, 8) DEFAULT 0.0,
    symbols JSONB DEFAULT '[]'::jsonb,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_user_bot_name UNIQUE(user_id, name),
    CONSTRAINT fk_user_id FOREIGN KEY(user_id) REFERENCES auth.users(id) ON DELETE CASCADE
);

CREATE INDEX idx_bots_user_id ON bots(user_id);
CREATE INDEX idx_bots_status ON bots(status);
CREATE INDEX idx_bots_created_at ON bots(created_at DESC);

-- ===================== TRADES TABLE =====================
CREATE TABLE trades (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    bot_id UUID REFERENCES bots(id) ON DELETE CASCADE,
    
    -- Trade details
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,
    status trade_status DEFAULT 'OPEN',
    
    -- Prices
    entry_price DECIMAL(20, 8) NOT NULL,
    exit_price DECIMAL(20, 8),
    quantity DECIMAL(20, 8) NOT NULL,
    
    -- P&L
    pnl DECIMAL(20, 8),
    pnl_percent DECIMAL(10, 2),
    
    -- Times
    entry_time TIMESTAMP NOT NULL,
    exit_time TIMESTAMP,
    
    -- Risk management
    strategy VARCHAR(100),
    stop_loss_price DECIMAL(20, 8),
    take_profit_price DECIMAL(20, 8),
    trailing_stop_percent DECIMAL(5, 2),
    max_loss_amount DECIMAL(20, 8),
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_user_id FOREIGN KEY(user_id) REFERENCES auth.users(id) ON DELETE CASCADE
);

CREATE INDEX idx_trades_user_id ON trades(user_id);
CREATE INDEX idx_trades_bot_id ON trades(bot_id);
CREATE INDEX idx_trades_symbol ON trades(symbol);
CREATE INDEX idx_trades_status ON trades(status);
CREATE INDEX idx_trades_entry_time ON trades(entry_time DESC);

-- ===================== PORTFOLIOS TABLE =====================
CREATE TABLE portfolios (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL UNIQUE,
    total_value DECIMAL(20, 8) DEFAULT 100000.0,
    cash_balance DECIMAL(20, 8) DEFAULT 100000.0,
    daily_pnl DECIMAL(20, 8) DEFAULT 0.0,
    total_pnl DECIMAL(20, 8) DEFAULT 0.0,
    win_rate DECIMAL(5, 2) DEFAULT 0.0,
    max_drawdown DECIMAL(5, 2) DEFAULT 0.0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_portfolio_user FOREIGN KEY(user_id) REFERENCES auth.users(id) ON DELETE CASCADE
);

CREATE INDEX idx_portfolio_user_id ON portfolios(user_id);

-- ===================== SENTIMENT DATA TABLE =====================
CREATE TABLE sentiment_data (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    sentiment_score DECIMAL(5, 2),
    fear_greed_index DECIMAL(5, 2),
    source VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_sentiment_user FOREIGN KEY(user_id) REFERENCES auth.users(id) ON DELETE CASCADE
);

CREATE INDEX idx_sentiment_user ON sentiment_data(user_id);
CREATE INDEX idx_sentiment_symbol ON sentiment_data(symbol);

-- ===================== RISK EVENTS TABLE =====================
CREATE TABLE risk_events (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    bot_id UUID REFERENCES bots(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    message TEXT,
    action_taken VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_risk_user FOREIGN KEY(user_id) REFERENCES auth.users(id) ON DELETE CASCADE
);

CREATE INDEX idx_risk_user ON risk_events(user_id);
CREATE INDEX idx_risk_bot ON risk_events(bot_id);

-- ===================== STRATEGY PERFORMANCE TABLE =====================
CREATE TABLE strategy_performance (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    strategy_name VARCHAR(100) NOT NULL,
    symbol VARCHAR(20),
    total_trades INT DEFAULT 0,
    winning_trades INT DEFAULT 0,
    losing_trades INT DEFAULT 0,
    win_rate DECIMAL(5, 2) DEFAULT 0.0,
    avg_win DECIMAL(20, 8),
    avg_loss DECIMAL(20, 8),
    profit_factor DECIMAL(10, 2),
    sharpe_ratio DECIMAL(10, 4),
    max_drawdown DECIMAL(5, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_strategy_user FOREIGN KEY(user_id) REFERENCES auth.users(id) ON DELETE CASCADE
);

CREATE INDEX idx_strategy_user ON strategy_performance(user_id);

-- ===================== BROKER CONNECTIONS TABLE (for Phase 4) =====================
CREATE TABLE broker_connections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    broker_name VARCHAR(100) NOT NULL,
    api_key_encrypted TEXT NOT NULL,
    secret_key_encrypted TEXT NOT NULL,
    is_testnet BOOLEAN DEFAULT true,
    is_active BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_user_broker UNIQUE(user_id, broker_name),
    CONSTRAINT fk_broker_user FOREIGN KEY(user_id) REFERENCES auth.users(id) ON DELETE CASCADE
);

CREATE INDEX idx_broker_user ON broker_connections(user_id);

-- ===================== ROW LEVEL SECURITY (RLS) =====================
-- Enable RLS on all tables
ALTER TABLE bots ENABLE ROW LEVEL SECURITY;
ALTER TABLE trades ENABLE ROW LEVEL SECURITY;
ALTER TABLE portfolios ENABLE ROW LEVEL SECURITY;
ALTER TABLE sentiment_data ENABLE ROW LEVEL SECURITY;
ALTER TABLE risk_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE strategy_performance ENABLE ROW LEVEL SECURITY;
ALTER TABLE broker_connections ENABLE ROW LEVEL SECURITY;

-- Policies for bots
CREATE POLICY "Users can view their own bots"
    ON bots FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own bots"
    ON bots FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own bots"
    ON bots FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own bots"
    ON bots FOR DELETE
    USING (auth.uid() = user_id);

-- Policies for trades
CREATE POLICY "Users can view their own trades"
    ON trades FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own trades"
    ON trades FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own trades"
    ON trades FOR UPDATE
    USING (auth.uid() = user_id);

-- Policies for portfolios
CREATE POLICY "Users can view their own portfolio"
    ON portfolios FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can update their own portfolio"
    ON portfolios FOR UPDATE
    USING (auth.uid() = user_id);

-- Policies for sentiment_data
CREATE POLICY "Users can view their sentiment data"
    ON sentiment_data FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert sentiment data"
    ON sentiment_data FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Policies for risk_events
CREATE POLICY "Users can view their risk events"
    ON risk_events FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert risk events"
    ON risk_events FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Policies for strategy_performance
CREATE POLICY "Users can view their strategy performance"
    ON strategy_performance FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can update their strategy performance"
    ON strategy_performance FOR UPDATE
    USING (auth.uid() = user_id);

-- Policies for broker_connections
CREATE POLICY "Users can view their broker connections"
    ON broker_connections FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can manage their broker connections"
    ON broker_connections FOR ALL
    USING (auth.uid() = user_id);

-- ===================== GRANT PERMISSIONS =====================
GRANT SELECT, INSERT, UPDATE, DELETE ON bots TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON trades TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON portfolios TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON sentiment_data TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON risk_events TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON strategy_performance TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON broker_connections TO authenticated;
