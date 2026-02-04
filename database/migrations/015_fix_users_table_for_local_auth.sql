-- Migration 015: Fix users table to support local authentication
-- Add missing columns: username and password_hash
-- These columns are required by the local auth system

ALTER TABLE users ADD COLUMN IF NOT EXISTS username VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255);

-- Create unique index on username if it doesn't exist
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username ON users(username);
