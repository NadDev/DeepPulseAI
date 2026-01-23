-- Migration 011: Normalize watchlist symbols to Binance format (BTCUSDT, not BTC/USDT)
-- This ensures consistency between database storage and Binance API calls

BEGIN;

-- Step 1: Remove slashes and normalize all watchlist symbols
UPDATE watchlist_items
SET symbol = REPLACE(REPLACE(symbol, '/', ''), 'USDT', '') || 'USDT'
WHERE symbol LIKE '%/%' OR symbol LIKE '%USDT/USDT%';

-- Step 2: Ensure all symbols end with USDT (for those that don't)
UPDATE watchlist_items
SET symbol = symbol || 'USDT'
WHERE NOT symbol LIKE '%USDT';

-- Verify the migration
-- SELECT id, symbol, base_currency, quote_currency FROM watchlist_items ORDER BY created_at DESC;

COMMIT;
