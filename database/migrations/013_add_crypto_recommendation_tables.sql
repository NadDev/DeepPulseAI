-- Migration 013: Add crypto market data and recommendation tables for RecommendationCrypto feature

-- Table 1: crypto_market_data - Historical market data for 200+ cryptocurrencies
CREATE TABLE IF NOT EXISTS crypto_market_data (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,           -- BTCUSDT, ETHUSDT, etc.
    timestamp BIGINT NOT NULL,              -- Unix milliseconds
    open DECIMAL(20,8) NOT NULL,
    high DECIMAL(20,8) NOT NULL,
    low DECIMAL(20,8) NOT NULL,
    close DECIMAL(20,8) NOT NULL,
    volume DECIMAL(20,8) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,         -- '1h', '4h', '1d'
    created_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(symbol, timestamp, timeframe)
);

CREATE INDEX IF NOT EXISTS idx_crypto_symbol_timestamp ON crypto_market_data(symbol, timestamp);
CREATE INDEX IF NOT EXISTS idx_crypto_symbol_timeframe ON crypto_market_data(symbol, timeframe);
CREATE INDEX IF NOT EXISTS idx_crypto_timeframe ON crypto_market_data(timeframe);

-- Table 2: watchlist_recommendations - Daily AI recommendations for users
CREATE TABLE IF NOT EXISTS watchlist_recommendations (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    score FLOAT NOT NULL,                   -- 0-100 score
    action VARCHAR(10) NOT NULL,            -- 'ADD' or 'REMOVE'
    reasoning TEXT,                         -- DeepSeek analysis/explanation
    accepted BOOLEAN DEFAULT NULL,          -- NULL=pending, true=accepted, false=rejected
    accepted_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create unique constraint using expression index (one recommendation per symbol per day)
CREATE UNIQUE INDEX IF NOT EXISTS idx_rec_user_symbol_date ON watchlist_recommendations(user_id, symbol, DATE(created_at));

CREATE INDEX IF NOT EXISTS idx_rec_user_created ON watchlist_recommendations(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_rec_user_accepted ON watchlist_recommendations(user_id, accepted);
CREATE INDEX IF NOT EXISTS idx_rec_symbol ON watchlist_recommendations(symbol);

-- Table 3: recommendation_score_log - Score component breakdown for ML training
CREATE TABLE IF NOT EXISTS recommendation_score_log (
    id UUID PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    score FLOAT NOT NULL,
    components JSONB NOT NULL,              -- {momentum, volume, volatility, rsi} with values
    timestamp TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_score_log_symbol ON recommendation_score_log(symbol);
CREATE INDEX IF NOT EXISTS idx_score_log_timestamp ON recommendation_score_log(timestamp);

-- Verify tables exist
SELECT 'crypto_market_data'::text as table_name, count(*) as row_count FROM crypto_market_data
UNION ALL
SELECT 'watchlist_recommendations', count(*) FROM watchlist_recommendations
UNION ALL
SELECT 'recommendation_score_log', count(*) FROM recommendation_score_log;
