-- Migration: Create AI Decisions Table
-- Purpose: Log all AI Agent decisions for analysis and backtesting
-- Date: 2026-01-07

CREATE TABLE IF NOT EXISTS ai_decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    bot_id UUID REFERENCES bots(id) ON DELETE SET NULL,
    
    -- Decision Info
    symbol VARCHAR(20) NOT NULL,
    action VARCHAR(10) NOT NULL,  -- BUY, SELL, HOLD
    confidence INTEGER CHECK (confidence >= 0 AND confidence <= 100),
    reasoning TEXT,
    
    -- Market Context
    entry_price DECIMAL(20, 8),
    target_price DECIMAL(20, 8),
    stop_loss DECIMAL(20, 8),
    risk_level VARCHAR(10),  -- LOW, MEDIUM, HIGH
    timeframe VARCHAR(10) DEFAULT '1h',
    
    -- Execution Info
    executed BOOLEAN DEFAULT FALSE,
    blocked BOOLEAN DEFAULT FALSE,
    blocked_reason TEXT,
    
    -- Mode & Context
    mode VARCHAR(20),  -- observation, paper, live or advisory, autonomous
    strategy_proposed VARCHAR(50),
    ai_agrees BOOLEAN,
    
    -- Trade Result
    trade_id UUID REFERENCES trades(id) ON DELETE SET NULL,
    result_pnl DECIMAL(20, 8),
    result_pnl_percent DECIMAL(10, 4),
    result_status VARCHAR(20),  -- OPEN, CLOSED, CANCELLED
    closed_at TIMESTAMP WITH TIME ZONE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for efficient querying
CREATE INDEX idx_ai_decisions_user_id ON ai_decisions(user_id);
CREATE INDEX idx_ai_decisions_bot_id ON ai_decisions(bot_id);
CREATE INDEX idx_ai_decisions_symbol ON ai_decisions(symbol);
CREATE INDEX idx_ai_decisions_action ON ai_decisions(action);
CREATE INDEX idx_ai_decisions_executed ON ai_decisions(executed);
CREATE INDEX idx_ai_decisions_created_at ON ai_decisions(created_at);
CREATE INDEX idx_ai_decisions_user_created ON ai_decisions(user_id, created_at DESC);

-- Trigger to update updated_at on changes
CREATE OR REPLACE FUNCTION update_ai_decisions_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_ai_decisions_timestamp
BEFORE UPDATE ON ai_decisions
FOR EACH ROW
EXECUTE FUNCTION update_ai_decisions_timestamp();

-- Grant permissions to service role (for Supabase)
GRANT ALL ON ai_decisions TO authenticated;
GRANT ALL ON ai_decisions TO service_role;

-- Enable Row Level Security
ALTER TABLE ai_decisions ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their own decisions
CREATE POLICY "Users can view their own decisions"
ON ai_decisions FOR SELECT
USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own decisions"
ON ai_decisions FOR INSERT
WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own decisions"
ON ai_decisions FOR UPDATE
USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own decisions"
ON ai_decisions FOR DELETE
USING (auth.uid() = user_id);
