-- Migration 020: Create long_term_positions table
-- Date: 2026-02-05
-- Description: Table pour gérer les positions long terme (DCA accumulation)

-- Create long_term_positions table
CREATE TABLE IF NOT EXISTS long_term_positions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Asset info
    symbol VARCHAR(20) NOT NULL,
    
    -- Accumulation tracking
    total_quantity DECIMAL(20,8) NOT NULL DEFAULT 0,
    avg_entry_price DECIMAL(20,8) NOT NULL DEFAULT 0,
    total_invested DECIMAL(20,8) NOT NULL DEFAULT 0,
    dca_count INTEGER NOT NULL DEFAULT 0,  -- Nombre de DCA effectués
    last_dca_at TIMESTAMP,
    next_dca_scheduled_at TIMESTAMP,
    
    -- Market data at entry
    market_cap_at_entry DECIMAL(20,2),
    ath_price_at_entry DECIMAL(20,8),
    ath_distance_pct_at_entry DECIMAL(10,4),  -- Distance from ATH at first DCA
    
    -- Current unrealized PnL
    current_price DECIMAL(20,8),
    unrealized_pnl DECIMAL(20,8) DEFAULT 0,
    unrealized_pnl_pct DECIMAL(10,4) DEFAULT 0,
    last_price_update TIMESTAMP,
    
    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'ACCUMULATING' CHECK (status IN ('ACCUMULATING', 'HOLDING', 'PARTIAL_EXIT', 'CLOSED')),
    -- ACCUMULATING: En cours d'achat DCA
    -- HOLDING: DCA terminé, on garde
    -- PARTIAL_EXIT: Sorti partiellement (TP hit)
    -- CLOSED: Position fermée complètement
    
    -- Take Profit levels (optionnel)
    tp1_price DECIMAL(20,8),
    tp1_pct DECIMAL(5,2) DEFAULT 20.0,  -- Vendre 20% à TP1
    tp1_hit BOOLEAN DEFAULT false,
    tp1_hit_at TIMESTAMP,
    
    tp2_price DECIMAL(20,8),
    tp2_pct DECIMAL(5,2) DEFAULT 30.0,
    tp2_hit BOOLEAN DEFAULT false,
    tp2_hit_at TIMESTAMP,
    
    tp3_price DECIMAL(20,8),
    tp3_pct DECIMAL(5,2) DEFAULT 30.0,
    tp3_hit BOOLEAN DEFAULT false,
    tp3_hit_at TIMESTAMP,
    
    -- Runner (20% restant pour "moon")
    runner_quantity DECIMAL(20,8) DEFAULT 0,
    
    -- Exit info
    total_exit_value DECIMAL(20,8) DEFAULT 0,
    realized_pnl DECIMAL(20,8) DEFAULT 0,
    realized_pnl_pct DECIMAL(10,4) DEFAULT 0,
    
    -- Confidence scores history (JSONB array)
    confidence_scores JSONB DEFAULT '[]',  -- [{date, score, criteria}, ...]
    
    -- Timestamps
    opened_at TIMESTAMP NOT NULL DEFAULT NOW(),
    closed_at TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Constraints
    UNIQUE(user_id, symbol)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_lt_positions_user ON long_term_positions(user_id);
CREATE INDEX IF NOT EXISTS idx_lt_positions_status ON long_term_positions(status);
CREATE INDEX IF NOT EXISTS idx_lt_positions_symbol ON long_term_positions(symbol);
CREATE INDEX IF NOT EXISTS idx_lt_positions_next_dca ON long_term_positions(next_dca_scheduled_at) WHERE status = 'ACCUMULATING';

-- Add comments
COMMENT ON TABLE long_term_positions IS 'Positions long terme avec DCA accumulation. Une position = accumulation sur un symbole.';
COMMENT ON COLUMN long_term_positions.dca_count IS 'Nombre total de DCA effectués pour cette position.';
COMMENT ON COLUMN long_term_positions.ath_distance_pct_at_entry IS 'Distance from ATH au moment du premier DCA (mesure timing).';
COMMENT ON COLUMN long_term_positions.confidence_scores IS 'Historique des scores de confiance à chaque évaluation.';
