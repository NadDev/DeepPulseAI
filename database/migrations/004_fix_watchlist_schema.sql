-- Migration 004: Fix Watchlist Schema to Match Python Model
-- Drop old tables and recreate with correct schema

-- Drop old tables if they exist
DROP TABLE IF EXISTS watchlist_items CASCADE;
DROP TABLE IF EXISTS watchlists CASCADE;

-- Create watchlist_items table matching Python model
CREATE TABLE watchlist_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    
    -- Symbol info
    symbol VARCHAR(20) NOT NULL,
    base_currency VARCHAR(10),
    quote_currency VARCHAR(10),
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 0,
    
    -- User notes
    notes TEXT,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_watchlist_items_user_id ON watchlist_items(user_id);
CREATE INDEX idx_watchlist_items_symbol ON watchlist_items(symbol);
CREATE INDEX idx_watchlist_items_is_active ON watchlist_items(is_active);
CREATE INDEX idx_watchlist_items_priority ON watchlist_items(priority);

-- Unique constraint: one symbol per user
CREATE UNIQUE INDEX idx_watchlist_items_user_symbol 
    ON watchlist_items(user_id, symbol);

-- Insert default watchlist for system (used by AI Agent monitoring loop)
-- Using a dummy UUID for system user
INSERT INTO watchlist_items (user_id, symbol, base_currency, quote_currency, is_active, priority, notes)
VALUES 
    ('00000000-0000-0000-0000-000000000000', 'BTC/USDT', 'BTC', 'USDT', TRUE, 10, 'Bitcoin - Top priority'),
    ('00000000-0000-0000-0000-000000000000', 'ETH/USDT', 'ETH', 'USDT', TRUE, 9, 'Ethereum'),
    ('00000000-0000-0000-0000-000000000000', 'BNB/USDT', 'BNB', 'USDT', TRUE, 8, 'Binance Coin'),
    ('00000000-0000-0000-0000-000000000000', 'SOL/USDT', 'SOL', 'USDT', TRUE, 7, 'Solana'),
    ('00000000-0000-0000-0000-000000000000', 'XRP/USDT', 'XRP', 'USDT', TRUE, 6, 'Ripple')
ON CONFLICT DO NOTHING;
