-- Migration 014: Increase volume column precision for crypto_market_data
-- Issue: PEPEUSDT and other low-price tokens have huge volumes that overflow DECIMAL(20,8)
-- Solution: Change volume to DECIMAL(35,8) to support volumes up to 10^27

ALTER TABLE crypto_market_data 
ALTER COLUMN volume SET DATA TYPE DECIMAL(35, 8);
