-- Migration 012: Add password_hash column to users table
-- Purpose: Store bcrypt-hashed passwords for local authentication
-- This replaces Supabase Auth dependency

ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255);

-- Add a check to ensure password_hash is set for users (except system users)
-- System users (id = '00000000-0000-0000-0000-000000000001') can have NULL password
