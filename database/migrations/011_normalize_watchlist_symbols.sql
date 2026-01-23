-- Migration 011: Normalize watchlist symbols to Binance format (BTCUSDT, not BTC/USDT)
-- This ensures consistency between database storage and Binance API calls

-- Step 1: Fix symbols with slash format like "BTC/USDT" -> "BTCUSDT"
UPDATE watchlist_items
SET symbol = REPLACE(symbol, '/', '')
WHERE symbol LIKE '%/%';

-- Step 2: Fix symbols with double USDT like "XMRUSDT/USDT" -> "XMRUSDT"
UPDATE watchlist_items
SET symbol = SUBSTRING(symbol, 1, LENGTH(symbol) - 5)
WHERE symbol LIKE '%USDT/USDT';

-- Step 3: Ensure all symbols end with USDT (for those that don't)
UPDATE watchlist_items
SET symbol = symbol || 'USDT'
WHERE NOT symbol LIKE '%USDT';
