# 🚀 Phase 1: Railway Deployment - SL/TP Management System

**Goal:** Deploy the intelligent SL/TP management system to Railway and test it on the live site  
**Status:** Ready to deploy  
**Date:** January 18, 2026

---

## 📋 Phase 1 Checklist

### ✅ Step 1: Apply Database Migration to Railway

```bash
# 1.1 SSH into Railway or use Railway CLI
railway run python backend/apply_migrations.py

# This will:
# ✅ Create user_trading_settings table
# ✅ Create sl_tp_profile_type ENUM (PRUDENT, BALANCED, AGGRESSIVE)
# ✅ Create sl_method_type ENUM (ATR, STRUCTURE, FIXED_PCT, HYBRID)
# ✅ Create sl_tp_profile_presets table
# ✅ Insert 3 default profiles (PRUDENT, BALANCED, AGGRESSIVE)
```

**Verification:**
```bash
railway run psql -c "\dt user_trading_settings"
railway run psql -c "SELECT * FROM sl_tp_profile_presets LIMIT 3;"
```

**Expected Output:**
```
 profile_name | sl_atr_multiplier | tp1_risk_reward | tp2_risk_reward
-----------+-------------------+-----------------+------------------
 PRUDENT    |               1.3 |             1.3 |               2.0
 BALANCED   |               1.5 |             1.5 |               3.0
 AGGRESSIVE |               1.7 |             2.0 |               4.0
```

---

### ✅ Step 2: Test API Endpoints

Once migration is applied, test these endpoints:

#### 2.1 Get User Trading Settings
```bash
curl -X GET "http://localhost:8000/api/settings/trading" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json"

# Expected Response:
{
  "user_id": "uuid-here",
  "sl_tp_profile": "BALANCED",
  "sl_method": "ATR",
  "sl_atr_multiplier": 1.5,
  "tp1_risk_reward": 1.5,
  "tp2_risk_reward": 3.0,
  "enable_trailing_sl": true,
  "trailing_activation_pct": 1.5,
  "validation_threshold_pct": 0.5
}
```

#### 2.2 Update User Trading Settings
```bash
curl -X PUT "http://localhost:8000/api/settings/trading" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "sl_tp_profile": "PRUDENT",
    "sl_method": "ATR",
    "sl_atr_multiplier": 1.3
  }'

# Expected Response:
{
  "message": "Trading settings updated successfully",
  "user_id": "uuid-here",
  "sl_tp_profile": "PRUDENT"
}
```

#### 2.3 Get Available Profiles
```bash
curl -X GET "http://localhost:8000/api/settings/trading/profiles" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Expected Response:
{
  "profiles": [
    {
      "profile_name": "PRUDENT",
      "description": "Conservative profile with tight SL/TP",
      "sl_atr_multiplier": 1.3,
      "tp1_risk_reward": 1.3,
      "tp2_risk_reward": 2.0
    },
    {
      "profile_name": "BALANCED",
      "description": "Default balanced approach",
      "sl_atr_multiplier": 1.5,
      "tp1_risk_reward": 1.5,
      "tp2_risk_reward": 3.0
    },
    {
      "profile_name": "AGGRESSIVE",
      "description": "Aggressive profile with wider targets",
      "sl_atr_multiplier": 1.7,
      "tp1_risk_reward": 2.0,
      "tp2_risk_reward": 4.0
    }
  ]
}
```

#### 2.4 Reset Settings to Defaults
```bash
curl -X POST "http://localhost:8000/api/settings/trading/reset" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Expected Response:
{
  "message": "Trading settings reset to defaults",
  "user_id": "uuid-here",
  "sl_tp_profile": "BALANCED"
}
```

---

### ✅ Step 3: Test in Frontend

#### 3.1 Frontend Component Already Integrated ✅
The `TradingSettings.jsx` component is already in:
- **Location:** `frontend/src/components/TradingSettings.jsx`
- **Integrated into:** `frontend/src/components/Settings.jsx` (Trading tab)
- **Status:** Ready to test

#### 3.2 Manual Testing Steps

1. **Start Backend (with Railway DB)**
   ```bash
   cd backend
   python app.py
   ```

2. **Start Frontend (local)**
   ```bash
   cd frontend
   npm run dev
   ```

3. **Navigate to Settings**
   - Login to the app
   - Click Settings (top right)
   - Select "Trading" tab
   - You should see 3 profile cards: PRUDENT, BALANCED, AGGRESSIVE

4. **Test Profile Selection**
   - Click a profile (e.g., PRUDENT)
   - Click "Save Settings"
   - Should see: "Settings saved successfully ✅"
   - Refresh page → Profile should persist

5. **Verify API Call**
   - Open browser DevTools (F12)
   - Go to Network tab
   - Select a profile and save
   - Look for request to `/api/settings/trading` (PUT)
   - Verify response contains your selected profile

---

### ✅ Step 4: Verify SL/TP Calculations in Bot Engine

Create a test bot and monitor that SL/TP are calculated correctly:

#### 4.1 Create Test Bot
```bash
# Via API
curl -X POST "http://localhost:8000/api/bots" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "SL/TP Test Bot",
    "strategy": "GridTrading",
    "symbol": "BTCUSDT",
    "config": {
      "grid_step": 5,
      "order_amount": 500
    }
  }'
```

#### 4.2 Monitor Bot Logs
```bash
# Watch logs for SL/TP calculations
tail -f logs/app.log | grep -i "sl\|tp\|signal"

# Expected logs:
# 📊 [SIGNAL] SL/TP Test Bot | BTCUSDT | BUY
# ✅ [BUY-EXEC] BTCUSDT | Entry: $42,000 | SL: $40,200 | TP1: $43,800 | TP2: $45,600
```

#### 4.3 Check Trade Details
```bash
curl -X GET "http://localhost:8000/api/trades" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Verify each trade has:
{
  "id": "uuid",
  "symbol": "BTCUSDT",
  "entry_price": 42000,
  "stop_loss": 40200,          # ✅ Calculated by SLTPManager
  "take_profit_1": 43800,      # ✅ Calculated by SLTPManager
  "take_profit_2": 45600,      # ✅ Calculated by SLTPManager
  "status": "OPEN"
}
```

---

## 🔍 What Gets Tested in Phase 1

| Component | Test | Expected Result |
|-----------|------|-----------------|
| **Database** | Migration runs without errors | ✅ Tables created, enums created |
| **API Endpoints** | GET /api/settings/trading | ✅ Returns user settings |
| **API Endpoints** | PUT /api/settings/trading | ✅ Updates settings in DB |
| **API Endpoints** | GET /api/settings/trading/profiles | ✅ Returns 3 profiles |
| **Frontend** | TradingSettings loads | ✅ Shows 3 profile cards |
| **Frontend** | Select profile + Save | ✅ Persists to DB |
| **Integration** | Bot creates trade | ✅ SL/TP calculated from user settings |
| **Integration** | Trade has SL/TP values | ✅ Match SLTPManager calculations |

---

## 🚀 Deployment Steps (Actual Railway)

### Step 1: Ensure Railway Database is Connected
```bash
# Check if DATABASE_URL is set
railway variables

# Should show:
# DATABASE_URL=postgresql://user:pass@host:port/db
```

### Step 2: Deploy Code to Railway
```bash
# Push to main branch (already done)
git push origin main

# Railway auto-deploys on push to main
# Monitor deployment:
railway logs backend
```

### Step 3: Run Migration on Railway
```bash
# Option A: Via Railway CLI
railway run python backend/apply_migrations.py

# Option B: Via SSH into Railway container
# (See Railway dashboard)
```

### Step 4: Verify Database Changes
```bash
# Connect to Railway database
railway run psql

# Inside psql:
\dt user_trading_settings    # Should show table
SELECT * FROM sl_tp_profile_presets;  # Should show 3 rows
```

### Step 5: Test Endpoints (Production)
```bash
# Replace YOUR_JWT_TOKEN with real token from login
curl -X GET "https://yourapp.vercel.app/api/settings/trading" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## ⚠️ Common Issues & Fixes

### Issue: Migration fails with "column already exists"
**Cause:** Migration already ran once  
**Fix:** This is OK - the migration has `IF NOT EXISTS` protection

### Issue: API returns 404 for /api/settings/trading
**Cause:** Backend not restarted or migration not applied  
**Fix:**
```bash
# Restart backend
railway redeploy backend

# Wait 2-3 minutes for redeploy
railway logs backend
```

### Issue: Frontend doesn't save settings
**Cause:** Backend API unreachable or JWT invalid  
**Fix:**
```bash
# 1. Check backend is running
curl http://localhost:8000/api/health

# 2. Check JWT is valid
# Open DevTools → Network → Find PUT request to /api/settings/trading
# Check response - should not be 401 Unauthorized
```

### Issue: "user_id not in JWT token"
**Cause:** JWT doesn't have user_id claim  
**Fix:** Verify Supabase auth is working
```bash
# Check JWT in browser DevTools:
# 1. Open Settings page
# 2. DevTools → Application → Cookies
# 3. Look for supabase-auth or session token
```

---

## 📊 Expected Results After Phase 1

✅ **Database:** user_trading_settings table exists with 3 profiles  
✅ **API:** All 4 endpoints working (/get, /put, /profiles, /reset)  
✅ **Frontend:** TradingSettings component visible and functional  
✅ **Integration:** New trades use user's selected SL/TP profile  
✅ **Persistence:** User's profile selection persists across sessions  

---

## 🎯 Success Criteria

- [ ] Migration applies to Railway without errors
- [ ] GET /api/settings/trading returns user settings
- [ ] PUT /api/settings/trading updates settings
- [ ] Frontend loads TradingSettings component
- [ ] Can select and save a profile
- [ ] Profile persists after page refresh
- [ ] New trades have SL/TP calculated from selected profile
- [ ] Logs show SL/TP calculations

---

## 📋 Next: Phase 2 (After Phase 1 Success)

Phase 2 focuses on:
- [ ] Intensive bot testing with multiple profiles
- [ ] Trailing stop testing in live conditions
- [ ] Partial TP exit testing (TP1 @ 50%, TP2 remaining)
- [ ] Performance monitoring (24+ hours)
- [ ] Error handling and edge cases

---

## 🔗 Related Files

- **Migration:** `database/migrations/007_create_user_trading_settings.sql`
- **API Routes:** `backend/app/routes/settings.py`
- **Database Model:** `backend/app/models/database_models.py::UserTradingSettings`
- **SLTPManager:** `backend/app/services/sl_tp_manager.py`
- **Frontend Component:** `frontend/src/components/TradingSettings.jsx`
- **Integration Tests:** `tests/test_sltp_integration.py`

---

**Created:** January 18, 2026  
**Phase:** 1 of 5 (Deployment & Basic Testing)  
**Estimated Time:** 30-60 minutes  
**Required:** Railway database access, JWT tokens for API testing
