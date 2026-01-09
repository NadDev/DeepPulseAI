-- Create AI System User
-- This user is used by the AI Bot Controller to create and manage AI-driven bots

-- Insert AI system user if not exists
INSERT INTO users (id, email, username, created_at, updated_at)
VALUES (
    '00000000-0000-0000-0000-000000000001'::uuid,
    'ai-system@deeppulseai.internal',
    'AI System',
    NOW(),
    NOW()
)
ON CONFLICT (id) DO NOTHING;

-- Create default portfolio for AI system user
INSERT INTO portfolios (id, user_id, balance, created_at, updated_at)
VALUES (
    '00000000-0000-0000-0000-000000000010'::uuid,
    '00000000-0000-0000-0000-000000000001'::uuid,
    0.0,  -- AI system doesn't need real balance
    NOW(),
    NOW()
)
ON CONFLICT (user_id) DO NOTHING;
