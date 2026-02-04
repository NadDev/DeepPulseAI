-- Migration 013: Drop foreign key constraints to auth.users
-- Purpose: Remove Supabase Auth dependency from all tables
-- These will be replaced with simple user_id references to the local users table

-- Drop FK constraints from bots table
ALTER TABLE bots DROP CONSTRAINT IF EXISTS fk_user_id CASCADE;

-- Drop FK constraints from trades table
ALTER TABLE trades DROP CONSTRAINT IF EXISTS fk_user_id CASCADE;

-- Drop FK constraints from portfolios table
ALTER TABLE portfolios DROP CONSTRAINT IF EXISTS fk_portfolio_user CASCADE;

-- Drop FK constraints from sentiment_data table
ALTER TABLE sentiment_data DROP CONSTRAINT IF EXISTS fk_sentiment_user CASCADE;

-- Drop FK constraints from risk_events table
ALTER TABLE risk_events DROP CONSTRAINT IF EXISTS fk_risk_user CASCADE;

-- Drop FK constraints from strategy_performance table
ALTER TABLE strategy_performance DROP CONSTRAINT IF EXISTS fk_strategy_user CASCADE;

-- Drop FK constraints from broker_connections table
ALTER TABLE broker_connections DROP CONSTRAINT IF EXISTS fk_broker_user CASCADE;

-- Note: We keep the user_id columns but don't enforce FK to auth.users
-- This allows user_id to reference the local users table
