-- ============================================
-- Migration 008: Add CLOSING status to trade_status enum
-- Date: January 18, 2026
-- Issue: Risk Manager checks for CLOSING status but enum doesn't have it
-- ============================================

-- PostgreSQL doesn't allow direct ALTER TYPE, so we need to:
-- 1. Create new ENUM type with CLOSING
-- 2. Rename old column to backup
-- 3. Recreate column with new type
-- 4. Update values
-- 5. Drop old type

-- Step 1: Create new enum type with CLOSING
DO $$ BEGIN
    CREATE TYPE trade_status_new AS ENUM ('OPEN', 'CLOSED', 'CANCELLED', 'CLOSING');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Step 2: Add new column with new type (trades table)
ALTER TABLE trades
ADD COLUMN status_new trade_status_new DEFAULT 'OPEN';

-- Step 3: Copy data (cast old to new)
UPDATE trades 
SET status_new = status::text::trade_status_new;

-- Step 4: Drop old column and rename
ALTER TABLE trades 
DROP COLUMN status;

ALTER TABLE trades 
RENAME COLUMN status_new TO status;

-- Step 5: Drop old enum
DROP TYPE IF EXISTS trade_status;

-- Step 6: Rename new enum to original name
ALTER TYPE trade_status_new RENAME TO trade_status;

-- ============================================
-- Verify the change
-- ============================================
-- SELECT e.enumlabel FROM pg_enum e 
-- JOIN pg_type t ON e.enumtypid = t.oid 
-- WHERE t.typname = 'trade_status' 
-- ORDER BY e.enumsortorder;
-- Should show: OPEN, CLOSED, CANCELLED, CLOSING

COMMENT ON TYPE trade_status IS 'Trade status: OPEN (active), CLOSING (in process of closing), CLOSED (finalized), CANCELLED (not executed)';
