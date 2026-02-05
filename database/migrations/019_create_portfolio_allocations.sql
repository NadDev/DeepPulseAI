-- Migration 019: Create portfolio_allocations table
-- Date: 2026-02-05
-- Description: Table pour gérer l'allocation Day Trading vs Long Terme par utilisateur

-- Create portfolio_allocations table
CREATE TABLE IF NOT EXISTS portfolio_allocations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Allocations (en %)
    day_trading_pct DECIMAL(5,2) NOT NULL DEFAULT 100.0 CHECK (day_trading_pct >= 0 AND day_trading_pct <= 100),
    long_term_pct DECIMAL(5,2) NOT NULL DEFAULT 0.0 CHECK (long_term_pct >= 0 AND long_term_pct <= 20),
    long_term_max_pct DECIMAL(5,2) NOT NULL DEFAULT 20.0 CHECK (long_term_max_pct > 0 AND long_term_max_pct <= 20),
    
    -- Settings Day Trading
    dt_enabled BOOLEAN NOT NULL DEFAULT true,
    
    -- Settings Long Terme (DÉSACTIVÉ par défaut)
    lt_enabled BOOLEAN NOT NULL DEFAULT false,  -- OPT-IN obligatoire
    lt_assets JSONB DEFAULT '["BTCUSDT", "ETHUSDT"]',
    lt_asset_weights JSONB DEFAULT '{"BTCUSDT": 70, "ETHUSDT": 30}',
    
    -- Critères de sélection STRICTS
    lt_min_confidence_score INTEGER NOT NULL DEFAULT 80 CHECK (lt_min_confidence_score >= 60 AND lt_min_confidence_score <= 100),
    lt_require_weekly_bullish BOOLEAN NOT NULL DEFAULT true,
    lt_require_ml_7d_confidence INTEGER NOT NULL DEFAULT 70 CHECK (lt_require_ml_7d_confidence >= 50 AND lt_require_ml_7d_confidence <= 100),
    lt_max_fear_greed_index INTEGER NOT NULL DEFAULT 30 CHECK (lt_max_fear_greed_index >= 10 AND lt_max_fear_greed_index <= 50),
    
    -- DCA Configuration
    lt_dca_frequency VARCHAR(20) NOT NULL DEFAULT 'weekly' CHECK (lt_dca_frequency IN ('daily', 'weekly', 'monthly')),
    lt_dca_day INTEGER NOT NULL DEFAULT 1 CHECK (lt_dca_day >= 0 AND lt_dca_day <= 6),  -- 0=Dimanche, 1=Lundi, etc.
    lt_dca_amount_pct DECIMAL(5,2) NOT NULL DEFAULT 10.0 CHECK (lt_dca_amount_pct > 0 AND lt_dca_amount_pct <= 50),
    lt_min_hold_days INTEGER NOT NULL DEFAULT 180 CHECK (lt_min_hold_days >= 30),
    lt_boost_in_extreme_fear BOOLEAN NOT NULL DEFAULT true,
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Constraints
    UNIQUE(user_id),
    CHECK (day_trading_pct + long_term_pct = 100)
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_portfolio_alloc_user ON portfolio_allocations(user_id);
CREATE INDEX IF NOT EXISTS idx_portfolio_alloc_lt_enabled ON portfolio_allocations(lt_enabled);

-- Add comment
COMMENT ON TABLE portfolio_allocations IS 'Gestion allocation Day Trading vs Long Terme par utilisateur. Long Terme désactivé par défaut (OPT-IN).';
COMMENT ON COLUMN portfolio_allocations.lt_enabled IS 'Long terme désactivé par défaut. User doit activer manuellement.';
COMMENT ON COLUMN portfolio_allocations.long_term_max_pct IS 'Plafond absolu à 20% pour limiter exposition long terme.';
COMMENT ON COLUMN portfolio_allocations.lt_min_confidence_score IS 'Score minimum requis pour exécuter un trade LT (défaut: 80/100).';
