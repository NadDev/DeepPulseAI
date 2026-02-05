-- Migration: 018_ensure_system_user.sql
-- Description: Ensure the Global System User (00000000-0000-0000-0000-000000000000) exists
-- This user is used to store Global Recommendations that are then filtered for individual users.

-- Insert Global System user if not exists
INSERT INTO users (id, email, username, created_at, updated_at)
VALUES (
    '00000000-0000-0000-0000-000000000000'::uuid,
    'global-system@deeppulseai.internal',
    'Global System',
    NOW(),
    NOW()
)
ON CONFLICT (id) DO NOTHING;

-- Ensure a portfolio entry exists for this user (to prevent FK errors if logic ever touches portfolios)
INSERT INTO portfolios (id, user_id, cash_balance, total_value, created_at, updated_at)
VALUES (
    '00000000-0000-0000-0000-000000000000'::uuid, -- Using same ID for simplicity
    '00000000-0000-0000-0000-000000000000'::uuid,
    0.0,
    0.0,
    NOW(), -- created_at
    NOW()  -- updated_at
)
ON CONFLICT (user_id) DO NOTHING;
