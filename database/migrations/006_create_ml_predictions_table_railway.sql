-- Migration: Create ml_predictions table for storing LSTM predictions
-- Date: 2026-01-10
-- Purpose: Persist LSTM model predictions to enable backtesting and accuracy measurement
-- Railway compatible: No auth.users reference (user_id is just UUID, no FK)

CREATE TABLE IF NOT EXISTS ml_predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    
    -- LSTM Predictions
    pred_1h FLOAT,
    confidence_1h FLOAT CHECK (confidence_1h >= 0 AND confidence_1h <= 1),
    pred_24h FLOAT,
    confidence_24h FLOAT CHECK (confidence_24h >= 0 AND confidence_24h <= 1),
    pred_7d FLOAT,
    confidence_7d FLOAT CHECK (confidence_7d >= 0 AND confidence_7d <= 1),
    
    -- Context at prediction time
    current_price FLOAT NOT NULL,
    patterns JSONB,  -- Detected chart patterns: ["bullish_engulfing", "support_bounce", etc]
    
    -- Actual prices (filled later)
    actual_price_1h FLOAT DEFAULT NULL,  -- Filled 1h after prediction
    actual_price_24h FLOAT DEFAULT NULL, -- Filled 24h after prediction
    actual_price_7d FLOAT DEFAULT NULL,  -- Filled 7d after prediction
    actual_filled_at_1h TIMESTAMPTZ DEFAULT NULL,
    actual_filled_at_24h TIMESTAMPTZ DEFAULT NULL,
    actual_filled_at_7d TIMESTAMPTZ DEFAULT NULL,
    
    -- Accuracy metrics (calculated after actual price available)
    error_1h FLOAT DEFAULT NULL,         -- (actual - predicted) / predicted
    error_24h FLOAT DEFAULT NULL,
    error_7d FLOAT DEFAULT NULL,
    
    correct_direction_1h BOOLEAN DEFAULT NULL,  -- Did price move in predicted direction?
    correct_direction_24h BOOLEAN DEFAULT NULL,
    correct_direction_7d BOOLEAN DEFAULT NULL,
    
    -- Metadata
    model_version VARCHAR(20) DEFAULT 'lstm-1.0.0',
    lookback_days INT DEFAULT 90,        -- Historical data used for prediction
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_ml_predictions_user_symbol_time 
    ON ml_predictions(user_id, symbol, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_ml_predictions_symbol_created 
    ON ml_predictions(symbol, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_ml_predictions_pending_accuracy
    ON ml_predictions(user_id, timestamp DESC)
    WHERE correct_direction_1h IS NULL;
