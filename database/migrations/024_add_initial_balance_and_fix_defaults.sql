-- Migration 024: Add initial_balance to exchange_configs and fix Portfolio defaults
-- Purpose: Allow users to configure paper trading initial balance
-- Created: 2026-05-29

-- =====================================================
-- 1. ADD initial_balance TO exchange_configs TABLE
-- =====================================================
ALTER TABLE IF EXISTS exchange_configs
ADD COLUMN IF NOT EXISTS initial_balance FLOAT DEFAULT 10000.0;

COMMENT ON COLUMN exchange_configs.initial_balance IS 'Paper trading initial balance in USDT';

-- Create index for easier queries
CREATE INDEX IF NOT EXISTS idx_exchange_configs_initial_balance ON exchange_configs(initial_balance);

-- =====================================================
-- 2. FIX PORTFOLIO TABLE DEFAULTS
-- =====================================================
-- Note: This only affects new rows. Existing rows keep their values.
-- To reset existing portfolios with 100000.0 defaults, see script below.

-- Optional: Reset portfolios with 100000 balance to 0 if they haven't been synced
-- (Uncomment to run after confirming data integrity)
-- UPDATE portfolios
-- SET total_value = 0.0,
--     cash_balance = 0.0,
--     updated_at = NOW()
-- WHERE total_value = 100000.0 AND cash_balance = 100000.0;

-- Log the migration
INSERT INTO migrations_log (name, applied_at, status)
VALUES ('024_add_initial_balance_and_fix_defaults', NOW(), 'completed')
ON CONFLICT (name) DO NOTHING;
