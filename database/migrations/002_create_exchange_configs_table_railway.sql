-- Migration: Create exchange_configs table (Railway version)
-- Created: 2026-01-09
-- Description: Stores exchange/broker API configurations per user (encrypted)
-- Compatible with Railway PostgreSQL (no Supabase auth schema)

-- Create the exchange_configs table
CREATE TABLE IF NOT EXISTS exchange_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    
    -- Exchange Info
    exchange VARCHAR(50) NOT NULL,
    name VARCHAR(100),
    
    -- Credentials (Encrypted using Fernet)
    api_key_encrypted TEXT NOT NULL,
    api_secret_encrypted TEXT NOT NULL,
    passphrase_encrypted TEXT,
    
    -- Configuration
    is_active BOOLEAN DEFAULT true,
    is_default BOOLEAN DEFAULT false,
    paper_trading BOOLEAN DEFAULT true,
    use_testnet BOOLEAN DEFAULT true,
    
    -- Trading Limits
    max_trade_size FLOAT DEFAULT 1000.0,
    max_daily_trades INTEGER DEFAULT 50,
    allowed_symbols TEXT,  -- JSON array
    
    -- Connection Status
    last_connection_test TIMESTAMPTZ,
    connection_status VARCHAR(20) DEFAULT 'untested',
    connection_error TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_exchange_configs_user_id ON exchange_configs(user_id);
CREATE INDEX IF NOT EXISTS idx_exchange_configs_exchange ON exchange_configs(exchange);
CREATE INDEX IF NOT EXISTS idx_exchange_configs_is_active ON exchange_configs(is_active);

-- Unique constraint: one config per exchange per user
CREATE UNIQUE INDEX IF NOT EXISTS idx_exchange_configs_user_exchange 
ON exchange_configs(user_id, exchange);

-- Comment on table
COMMENT ON TABLE exchange_configs IS 'Stores encrypted exchange/broker API configurations per user';
COMMENT ON COLUMN exchange_configs.api_key_encrypted IS 'Fernet-encrypted API key';
COMMENT ON COLUMN exchange_configs.api_secret_encrypted IS 'Fernet-encrypted API secret';
COMMENT ON COLUMN exchange_configs.passphrase_encrypted IS 'Fernet-encrypted passphrase (for exchanges that require it)';
