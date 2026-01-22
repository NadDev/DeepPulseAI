-- Migration 010: Add market_context columns to trades table
-- Purpose: Store market context information at time of trade entry for reporting

ALTER TABLE trades 
ADD COLUMN IF NOT EXISTS market_context VARCHAR(50),
ADD COLUMN IF NOT EXISTS market_context_confidence FLOAT;

-- Create index for filtering by market context
CREATE INDEX IF NOT EXISTS idx_trades_market_context ON trades(market_context);
CREATE INDEX IF NOT EXISTS idx_trades_user_market_context ON trades(user_id, market_context);

-- Log migration
SELECT 'Migration 010 completed: Added market_context and market_context_confidence to trades table' as migration_status;
