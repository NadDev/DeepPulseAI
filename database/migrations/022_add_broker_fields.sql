-- Migration 022: Add Broker Integration Fields
-- Adds exchange-specific fields to support multi-broker architecture
-- Required for phase P5 of broker abstraction

-- ==========================================
-- 1️⃣ TRADES TABLE - Exchange Order Tracking
-- ==========================================
ALTER TABLE trades 
ADD COLUMN IF NOT EXISTS exchange VARCHAR(50) DEFAULT 'binance',
ADD COLUMN IF NOT EXISTS exchange_order_id VARCHAR(255),
ADD COLUMN IF NOT EXISTS exchange_trade_id VARCHAR(255),
ADD COLUMN IF NOT EXISTS commission_amount DECIMAL(30,10),
ADD COLUMN IF NOT EXISTS commission_asset VARCHAR(20),
ADD COLUMN IF NOT EXISTS actual_fill_price DECIMAL(30,10),
ADD COLUMN IF NOT EXISTS fill_timestamp TIMESTAMP,
ADD COLUMN IF NOT EXISTS last_synced TIMESTAMP;

-- Create index for exchange queries
CREATE INDEX IF NOT EXISTS idx_trades_exchange_order ON trades(exchange, exchange_order_id);
CREATE INDEX IF NOT EXISTS idx_trades_last_synced ON trades(last_synced);

-- ==========================================
-- 2️⃣ PORTFOLIOS TABLE - Multi-Exchange Support
-- ==========================================
ALTER TABLE portfolios
ADD COLUMN IF NOT EXISTS exchange VARCHAR(50) DEFAULT 'binance',
ADD COLUMN IF NOT EXISTS exchange_config_id UUID,
ADD COLUMN IF NOT EXISTS exchange_cash_balance DECIMAL(30,10),
ADD COLUMN IF NOT EXISTS exchange_total_value DECIMAL(30,10),
ADD COLUMN IF NOT EXISTS balance_difference DECIMAL(30,10) DEFAULT 0.0,
ADD COLUMN IF NOT EXISTS is_synced BOOLEAN DEFAULT true,
ADD COLUMN IF NOT EXISTS last_synced_with_exchange TIMESTAMP;

-- Add foreign key to exchange_configs if table exists
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'exchange_configs') THEN
        ALTER TABLE portfolios
        ADD CONSTRAINT fk_portfolios_exchange_config 
        FOREIGN KEY (exchange_config_id) 
        REFERENCES exchange_configs(id)
        ON DELETE SET NULL;
    END IF;
END $$;

-- Create index for exchange queries
CREATE INDEX IF NOT EXISTS idx_portfolios_exchange ON portfolios(exchange, user_id);
CREATE INDEX IF NOT EXISTS idx_portfolios_synced ON portfolios(is_synced);

-- ==========================================
-- 3️⃣ PAPER_MARKET_DATA TABLE - Historical Data Storage
-- ==========================================
-- Stores historical market data for paper trading replay/strategy testing
CREATE TABLE IF NOT EXISTS paper_market_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,  -- 1m, 5m, 15m, 1h, 4h, 1d
    timestamp TIMESTAMP NOT NULL,
    open_price DECIMAL(30,10) NOT NULL,
    high_price DECIMAL(30,10) NOT NULL,
    low_price DECIMAL(30,10) NOT NULL,
    close_price DECIMAL(30,10) NOT NULL,
    volume DECIMAL(30,10) NOT NULL,
    quote_volume DECIMAL(30,10),
    trades_count INTEGER,
    
    -- Source metadata
    source VARCHAR(50) DEFAULT 'binance',  -- binance, kraken, etc.
    collected_at TIMESTAMP DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT paper_market_data_unique_candle 
    UNIQUE (symbol, timeframe, timestamp, source)
);

-- Indexes for fast candle queries
CREATE INDEX IF NOT EXISTS idx_paper_candles_symbol_time 
ON paper_market_data(symbol, timeframe, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_paper_candles_collected 
ON paper_market_data(collected_at DESC);

-- ==========================================
-- 4️⃣ COMMENTS
-- ==========================================
COMMENT ON COLUMN trades.exchange IS 'Exchange where trade was executed (binance, kraken, paper)';
COMMENT ON COLUMN trades.exchange_order_id IS 'Exchange-specific order ID (e.g., Binance orderId)';
COMMENT ON COLUMN trades.exchange_trade_id IS 'Exchange-specific trade ID (e.g., Binance tradeId from fills)';
COMMENT ON COLUMN trades.commission_amount IS 'Commission paid for this trade';
COMMENT ON COLUMN trades.commission_asset IS 'Asset used to pay commission (USDT, BNB, etc.)';
COMMENT ON COLUMN trades.actual_fill_price IS 'Actual fill price from exchange (may differ from limit price)';
COMMENT ON COLUMN trades.fill_timestamp IS 'Timestamp when order was filled on exchange';
COMMENT ON COLUMN trades.last_synced IS 'Last time trade status was synchronized with exchange';

COMMENT ON COLUMN portfolios.exchange IS 'Exchange this portfolio tracks (binance, kraken, paper)';
COMMENT ON COLUMN portfolios.exchange_config_id IS 'Foreign key to exchange_configs table';
COMMENT ON COLUMN portfolios.exchange_cash_balance IS 'Cash balance reported by exchange API';
COMMENT ON COLUMN portfolios.exchange_total_value IS 'Total portfolio value reported by exchange';
COMMENT ON COLUMN portfolios.balance_difference IS 'Difference between local and exchange balance (drift detection)';
COMMENT ON COLUMN portfolios.is_synced IS 'Whether local portfolio is synced with exchange';
COMMENT ON COLUMN portfolios.last_synced_with_exchange IS 'Last successful sync timestamp';

COMMENT ON TABLE paper_market_data IS 'Historical market data for paper trading replay and strategy backtesting';
