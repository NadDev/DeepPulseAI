-- Migration: Add TP2 and phase tracking to trades table
-- Date: January 18, 2026
-- Purpose: Support fractional TP exits and trade phase management

BEGIN;

-- Add new columns to trades table
ALTER TABLE trades ADD COLUMN IF NOT EXISTS take_profit_2 FLOAT;
ALTER TABLE trades ADD COLUMN IF NOT EXISTS trade_phase VARCHAR(20);
ALTER TABLE trades ADD COLUMN IF NOT EXISTS tp1_partial_executed BOOLEAN DEFAULT FALSE;

-- Add comments
COMMENT ON COLUMN trades.take_profit_2 IS 'Runner TP level (for partial TP1 exits)';
COMMENT ON COLUMN trades.trade_phase IS 'Trade phase: PENDING, VALIDATED, or TRAILING';
COMMENT ON COLUMN trades.tp1_partial_executed IS 'True if 50% was exited at TP1';

-- Create index for phase queries
CREATE INDEX IF NOT EXISTS idx_trades_phase ON trades(trade_phase);

COMMIT;
