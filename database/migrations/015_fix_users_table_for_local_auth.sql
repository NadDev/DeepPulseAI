-- Migration 015: Fix users table to support local authentication
-- Add missing columns: username, password_hash, and updated_at
-- These columns are required by the local auth system

ALTER TABLE users ADD COLUMN IF NOT EXISTS username VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Create unique index on username if it doesn't exist
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username ON users(username);
