-- ============================================
-- Update BALANCED preset: sl_fixed_pct 2.5 → 2.0
-- Date: February 5, 2026
-- Reason: Tighter SL for better R:R (Phase 1 fixes)
-- ============================================

UPDATE sl_tp_profile_presets
SET 
    sl_fixed_pct = 2.0,  -- Changed from 2.5 to 2.0
    description = 'Balanced risk/reward profile with tighter stops. Good for most market conditions.'
WHERE profile_name = 'BALANCED';

-- Verify the change
SELECT profile_name, sl_fixed_pct, tp1_risk_reward, description
FROM sl_tp_profile_presets
ORDER BY profile_name;
