-- ============================================
-- Migration 007: Create user_trading_settings table
-- Date: January 18, 2026
-- Feature: Intelligent SL/TP with user profiles
-- ============================================

-- Create ENUM type for SL/TP risk profiles
DO $$ BEGIN
    CREATE TYPE sl_tp_profile_type AS ENUM ('PRUDENT', 'BALANCED', 'AGGRESSIVE');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Create ENUM type for SL calculation method
DO $$ BEGIN
    CREATE TYPE sl_method_type AS ENUM ('ATR', 'STRUCTURE', 'FIXED_PCT', 'HYBRID');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- ============================================
-- Main table: user_trading_settings
-- Stores per-user SL/TP preferences
-- ============================================
CREATE TABLE IF NOT EXISTS user_trading_settings (
    -- Primary key = user_id (one row per user)
    user_id UUID PRIMARY KEY,
    
    -- ============================================
    -- SL/TP Profile Selection
    -- ============================================
    sl_tp_profile sl_tp_profile_type NOT NULL DEFAULT 'BALANCED',
    
    -- ============================================
    -- SL Configuration
    -- ============================================
    sl_method sl_method_type NOT NULL DEFAULT 'ATR',
    
    -- ATR-based SL (multiplier of ATR)
    sl_atr_multiplier FLOAT DEFAULT 1.5,
    
    -- Fixed percentage fallback (if ATR unavailable)
    sl_fixed_pct FLOAT DEFAULT 2.5,
    
    -- Minimum SL distance (absolute value in quote currency)
    sl_min_distance FLOAT DEFAULT 0.01,
    
    -- Maximum SL distance (percentage)
    sl_max_pct FLOAT DEFAULT 5.0,
    
    -- ============================================
    -- TP Configuration
    -- ============================================
    -- Primary TP (partial exit)
    tp1_risk_reward FLOAT DEFAULT 1.5,  -- R:R ratio for TP1
    tp1_exit_pct FLOAT DEFAULT 50.0,    -- % of position to exit at TP1
    
    -- Secondary TP (runner)
    tp2_risk_reward FLOAT DEFAULT 3.0,  -- R:R ratio for TP2
    -- Remaining position exits at TP2 or trailing
    
    -- ============================================
    -- Trailing Stop Configuration
    -- ============================================
    enable_trailing_sl BOOLEAN DEFAULT TRUE,
    trailing_activation_pct FLOAT DEFAULT 1.5,  -- Activate trailing after +1.5%
    trailing_distance_pct FLOAT DEFAULT 1.0,    -- Trail at 1% distance
    
    -- ============================================
    -- Trade Phase Configuration
    -- ============================================
    enable_trade_phases BOOLEAN DEFAULT TRUE,
    validation_threshold_pct FLOAT DEFAULT 0.5,  -- +0.5% to validate trade
    move_sl_to_breakeven BOOLEAN DEFAULT TRUE,   -- Move SL to entry on validation
    
    -- ============================================
    -- Partial TP Configuration
    -- ============================================
    enable_partial_tp BOOLEAN DEFAULT TRUE,
    
    -- ============================================
    -- Risk Limits (per user override)
    -- ============================================
    max_position_pct FLOAT DEFAULT 25.0,       -- Max 25% of portfolio per trade
    max_daily_loss_pct FLOAT DEFAULT 5.0,      -- Stop trading after -5% daily
    max_trades_per_day INTEGER DEFAULT 10,     -- Max trades per day
    
    -- ============================================
    -- Timestamps
    -- ============================================
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for fast lookups
CREATE INDEX IF NOT EXISTS idx_user_trading_settings_profile 
    ON user_trading_settings(sl_tp_profile);

-- ============================================
-- Profile presets reference table
-- Stores the 3 default profiles configuration
-- ============================================
CREATE TABLE IF NOT EXISTS sl_tp_profile_presets (
    profile_name sl_tp_profile_type PRIMARY KEY,
    
    -- Description
    display_name VARCHAR(50) NOT NULL,
    description TEXT,
    
    -- SL Config
    sl_atr_multiplier FLOAT NOT NULL,
    sl_fixed_pct FLOAT NOT NULL,
    sl_max_pct FLOAT NOT NULL,
    
    -- TP Config
    tp1_risk_reward FLOAT NOT NULL,
    tp1_exit_pct FLOAT NOT NULL,
    tp2_risk_reward FLOAT NOT NULL,
    
    -- Trailing Config
    trailing_activation_pct FLOAT NOT NULL,
    trailing_distance_pct FLOAT NOT NULL,
    
    -- Phase Config
    validation_threshold_pct FLOAT NOT NULL
);

-- ============================================
-- Insert default profile presets
-- ============================================
INSERT INTO sl_tp_profile_presets (
    profile_name, display_name, description,
    sl_atr_multiplier, sl_fixed_pct, sl_max_pct,
    tp1_risk_reward, tp1_exit_pct, tp2_risk_reward,
    trailing_activation_pct, trailing_distance_pct,
    validation_threshold_pct
) VALUES 
(
    'PRUDENT',
    'Prudent',
    'Conservative profile: tight stops, secure small gains quickly. Best for beginners or volatile markets.',
    1.0,    -- sl_atr_multiplier: 1x ATR (tight)
    1.5,    -- sl_fixed_pct: -1.5%
    3.0,    -- sl_max_pct: max -3%
    1.3,    -- tp1_risk_reward: 1.3:1
    70.0,   -- tp1_exit_pct: exit 70% at TP1
    2.0,    -- tp2_risk_reward: 2:1
    1.0,    -- trailing_activation_pct: +1%
    0.75,   -- trailing_distance_pct: 0.75%
    0.3     -- validation_threshold_pct: +0.3% to validate
),
(
    'BALANCED',
    'Balanced',
    'Balanced risk/reward profile. Good for most market conditions.',
    1.5,    -- sl_atr_multiplier: 1.5x ATR
    2.5,    -- sl_fixed_pct: -2.5%
    5.0,    -- sl_max_pct: max -5%
    1.5,    -- tp1_risk_reward: 1.5:1
    50.0,   -- tp1_exit_pct: exit 50% at TP1
    3.0,    -- tp2_risk_reward: 3:1
    1.5,    -- trailing_activation_pct: +1.5%
    1.0,    -- trailing_distance_pct: 1%
    0.5     -- validation_threshold_pct: +0.5% to validate
),
(
    'AGGRESSIVE',
    'Aggressive',
    'Let profits run with wider stops. Best for trending markets and experienced traders.',
    2.0,    -- sl_atr_multiplier: 2x ATR (wide)
    4.0,    -- sl_fixed_pct: -4%
    8.0,    -- sl_max_pct: max -8%
    1.5,    -- tp1_risk_reward: 1.5:1
    30.0,   -- tp1_exit_pct: exit only 30% at TP1
    4.0,    -- tp2_risk_reward: 4:1
    2.0,    -- trailing_activation_pct: +2%
    1.5,    -- trailing_distance_pct: 1.5%
    0.75    -- validation_threshold_pct: +0.75% to validate
)
ON CONFLICT (profile_name) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    sl_atr_multiplier = EXCLUDED.sl_atr_multiplier,
    sl_fixed_pct = EXCLUDED.sl_fixed_pct,
    sl_max_pct = EXCLUDED.sl_max_pct,
    tp1_risk_reward = EXCLUDED.tp1_risk_reward,
    tp1_exit_pct = EXCLUDED.tp1_exit_pct,
    tp2_risk_reward = EXCLUDED.tp2_risk_reward,
    trailing_activation_pct = EXCLUDED.trailing_activation_pct,
    trailing_distance_pct = EXCLUDED.trailing_distance_pct,
    validation_threshold_pct = EXCLUDED.validation_threshold_pct;

-- ============================================
-- Function to auto-update updated_at
-- ============================================
CREATE OR REPLACE FUNCTION update_user_trading_settings_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for auto-updating timestamp
DROP TRIGGER IF EXISTS trigger_update_user_trading_settings_timestamp ON user_trading_settings;
CREATE TRIGGER trigger_update_user_trading_settings_timestamp
    BEFORE UPDATE ON user_trading_settings
    FOR EACH ROW
    EXECUTE FUNCTION update_user_trading_settings_timestamp();

-- ============================================
-- Function to create default settings for new users
-- Can be called from application or triggered
-- ============================================
CREATE OR REPLACE FUNCTION create_default_trading_settings(p_user_id UUID)
RETURNS void AS $$
BEGIN
    INSERT INTO user_trading_settings (user_id, sl_tp_profile)
    VALUES (p_user_id, 'BALANCED')
    ON CONFLICT (user_id) DO NOTHING;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- View: user settings with profile details
-- Combines user overrides with profile defaults
-- ============================================
CREATE OR REPLACE VIEW v_user_trading_config AS
SELECT 
    uts.user_id,
    uts.sl_tp_profile,
    p.display_name as profile_display_name,
    p.description as profile_description,
    
    -- SL Config (user override or profile default)
    uts.sl_method,
    COALESCE(uts.sl_atr_multiplier, p.sl_atr_multiplier) as sl_atr_multiplier,
    COALESCE(uts.sl_fixed_pct, p.sl_fixed_pct) as sl_fixed_pct,
    uts.sl_min_distance,
    COALESCE(uts.sl_max_pct, p.sl_max_pct) as sl_max_pct,
    
    -- TP Config
    COALESCE(uts.tp1_risk_reward, p.tp1_risk_reward) as tp1_risk_reward,
    COALESCE(uts.tp1_exit_pct, p.tp1_exit_pct) as tp1_exit_pct,
    COALESCE(uts.tp2_risk_reward, p.tp2_risk_reward) as tp2_risk_reward,
    
    -- Trailing Config
    uts.enable_trailing_sl,
    COALESCE(uts.trailing_activation_pct, p.trailing_activation_pct) as trailing_activation_pct,
    COALESCE(uts.trailing_distance_pct, p.trailing_distance_pct) as trailing_distance_pct,
    
    -- Phase Config
    uts.enable_trade_phases,
    COALESCE(uts.validation_threshold_pct, p.validation_threshold_pct) as validation_threshold_pct,
    uts.move_sl_to_breakeven,
    
    -- Partial TP
    uts.enable_partial_tp,
    
    -- Risk Limits
    uts.max_position_pct,
    uts.max_daily_loss_pct,
    uts.max_trades_per_day,
    
    -- Timestamps
    uts.created_at,
    uts.updated_at
FROM user_trading_settings uts
JOIN sl_tp_profile_presets p ON uts.sl_tp_profile = p.profile_name;

-- ============================================
-- Grant permissions (adjust as needed)
-- ============================================
-- GRANT SELECT, INSERT, UPDATE ON user_trading_settings TO crbot_app;
-- GRANT SELECT ON sl_tp_profile_presets TO crbot_app;
-- GRANT SELECT ON v_user_trading_config TO crbot_app;

COMMENT ON TABLE user_trading_settings IS 'Per-user SL/TP configuration and trading preferences';
COMMENT ON TABLE sl_tp_profile_presets IS 'Default configurations for PRUDENT, BALANCED, AGGRESSIVE profiles';
COMMENT ON VIEW v_user_trading_config IS 'Combined view of user settings with profile defaults';
