-- Migration 021: Create long_term_transactions table
-- Date: 2026-02-05
-- Description: Historique de chaque transaction DCA/exit pour les positions long terme

-- Create long_term_transactions table
CREATE TABLE IF NOT EXISTS long_term_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    position_id UUID NOT NULL REFERENCES long_term_positions(id) ON DELETE CASCADE,
    
    -- Transaction info
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL CHECK (side IN ('BUY', 'SELL')),
    quantity DECIMAL(20,8) NOT NULL,
    price DECIMAL(20,8) NOT NULL,
    total_value DECIMAL(20,8) NOT NULL,
    
    -- Context
    transaction_type VARCHAR(20) NOT NULL CHECK (transaction_type IN ('DCA_REGULAR', 'DCA_BOOSTED', 'DCA_MANUAL', 'TP1_EXIT', 'TP2_EXIT', 'TP3_EXIT', 'MANUAL_EXIT')),
    -- DCA_REGULAR: Achat DCA normal (scheduled)
    -- DCA_BOOSTED: Achat DCA boosté (extreme fear detected)
    -- DCA_MANUAL: DCA manuel déclenché par user
    -- TP1_EXIT: Vente partielle TP1 (+50%)
    -- TP2_EXIT: Vente partielle TP2 (+100%)
    -- TP3_EXIT: Vente partielle TP3 (+200%)
    -- MANUAL_EXIT: Sortie manuelle complète/partielle
    
    -- Market context at transaction
    market_context VARCHAR(20),  -- STRONG_BULLISH, BULLISH, NEUTRAL, BEARISH, STRONG_BEARISH
    fear_greed_index INTEGER,
    market_cap DECIMAL(20,2),
    ath_distance_pct DECIMAL(10,4),
    
    -- Confidence score (pour les DCA)
    confidence_score INTEGER CHECK (confidence_score >= 0 AND confidence_score <= 100),
    confidence_criteria JSONB,  -- Détails des critères qui ont justifié ce DCA
    
    -- ML predictions at time of transaction
    ml_7d_prediction JSONB,  -- {direction, confidence, predicted_price}
    ml_24h_prediction JSONB,
    
    -- PnL at exit (pour les SELL)
    pnl_realized DECIMAL(20,8),
    pnl_realized_pct DECIMAL(10,4),
    
    -- Exchange info
    exchange_order_id VARCHAR(100),
    exchange VARCHAR(20) DEFAULT 'Binance',
    
    -- Notes
    notes TEXT,
    
    -- Timestamps
    executed_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_lt_trans_user ON long_term_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_lt_trans_position ON long_term_transactions(position_id);
CREATE INDEX IF NOT EXISTS idx_lt_trans_symbol ON long_term_transactions(symbol);
CREATE INDEX IF NOT EXISTS idx_lt_trans_type ON long_term_transactions(transaction_type);
CREATE INDEX IF NOT EXISTS idx_lt_trans_executed ON long_term_transactions(executed_at DESC);

-- Add comments
COMMENT ON TABLE long_term_transactions IS 'Historique complet de toutes les transactions long terme (DCA + exits).';
COMMENT ON COLUMN long_term_transactions.transaction_type IS 'Type de transaction: DCA normal/boosted, TP exits, ou sortie manuelle.';
COMMENT ON COLUMN long_term_transactions.confidence_score IS 'Score de confiance (0-100) qui a justifié ce DCA.';
COMMENT ON COLUMN long_term_transactions.confidence_criteria IS 'Détails des critères: timeframes, indicators, ML, market context, etc.';
COMMENT ON COLUMN long_term_transactions.ath_distance_pct IS 'Distance from ATH au moment de la transaction (mesure timing).';
