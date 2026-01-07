-- Migration 003: Create Watchlist Tables
-- This migration creates the watchlist and watchlist_items tables for crypto tracking

-- Watchlists table: stores user watchlist metadata
CREATE TABLE IF NOT EXISTS watchlists (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    name VARCHAR(100) NOT NULL DEFAULT 'Ma Watchlist',
    is_default BOOLEAN DEFAULT FALSE,
    symbols_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Watchlist items table: stores individual symbols in watchlists
CREATE TABLE IF NOT EXISTS watchlist_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    watchlist_id UUID NOT NULL REFERENCES watchlists(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    notes TEXT,
    priority VARCHAR(20) DEFAULT 'medium' CHECK (priority IN ('high', 'medium', 'low')),
    alerts_enabled BOOLEAN DEFAULT FALSE,
    alert_price_above DECIMAL(20, 8),
    alert_price_below DECIMAL(20, 8)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_watchlists_user_id ON watchlists(user_id);
CREATE INDEX IF NOT EXISTS idx_watchlist_items_watchlist_id ON watchlist_items(watchlist_id);
CREATE INDEX IF NOT EXISTS idx_watchlist_items_user_id ON watchlist_items(user_id);
CREATE INDEX IF NOT EXISTS idx_watchlist_items_symbol ON watchlist_items(symbol);

-- Unique constraint: one symbol per watchlist per user
CREATE UNIQUE INDEX IF NOT EXISTS idx_watchlist_items_unique 
    ON watchlist_items(watchlist_id, user_id, symbol);

-- Function to update symbols_count on watchlist
CREATE OR REPLACE FUNCTION update_watchlist_symbols_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE watchlists 
        SET symbols_count = (
            SELECT COUNT(*) FROM watchlist_items 
            WHERE watchlist_id = NEW.watchlist_id
        ),
        updated_at = NOW()
        WHERE id = NEW.watchlist_id;
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE watchlists 
        SET symbols_count = (
            SELECT COUNT(*) FROM watchlist_items 
            WHERE watchlist_id = OLD.watchlist_id
        ),
        updated_at = NOW()
        WHERE id = OLD.watchlist_id;
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Drop trigger if exists and recreate
DROP TRIGGER IF EXISTS trigger_update_symbols_count ON watchlist_items;

CREATE TRIGGER trigger_update_symbols_count
AFTER INSERT OR DELETE ON watchlist_items
FOR EACH ROW
EXECUTE FUNCTION update_watchlist_symbols_count();

-- Comments for documentation
COMMENT ON TABLE watchlists IS 'User watchlists for tracking cryptocurrency assets';
COMMENT ON TABLE watchlist_items IS 'Individual crypto symbols within user watchlists';
COMMENT ON COLUMN watchlists.is_default IS 'Indicates the default watchlist for the user';
COMMENT ON COLUMN watchlist_items.priority IS 'Monitoring priority: high, medium, or low';
COMMENT ON COLUMN watchlist_items.alerts_enabled IS 'Whether price alerts are active for this symbol';
COMMENT ON COLUMN watchlist_items.alert_price_above IS 'Alert when price goes above this value';
COMMENT ON COLUMN watchlist_items.alert_price_below IS 'Alert when price goes below this value';
