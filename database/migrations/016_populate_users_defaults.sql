-- Migration 016: Populate username and password_hash for existing users
-- For users without these values, generate default ones

-- Generate username from email (before @) for users without username
UPDATE users 
SET username = SPLIT_PART(email, '@', 1)
WHERE username IS NULL AND email IS NOT NULL;

-- For users without password_hash, we need to handle them differently
-- We'll set a flag that they need to reset their password on first login
-- For now, we'll add a temporary placeholder that signals they need to set a password

-- This is a data migration - existing users will need to use "forgot password" to set their password
-- OR we can implement a first-login flow that forces password reset
