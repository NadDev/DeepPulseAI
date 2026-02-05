-- Migration 017: Add components column to watchlist_recommendations
-- Stores the score breakdown: {momentum, volume, volatility, rsi}

ALTER TABLE watchlist_recommendations
ADD COLUMN IF NOT EXISTS components JSONB DEFAULT NULL;

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_watchlist_recs_components ON watchlist_recommendations(components);

-- Log migration
DO $$
BEGIN
  RAISE NOTICE 'Migration 017: Added components column to watchlist_recommendations';
END $$;
