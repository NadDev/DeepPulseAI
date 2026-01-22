# 🔄 ROLLBACK INSTRUCTIONS - Intelligent SL/TP Management System

**Branch Merged:** `feature/intelligent-sl-tp` → `main`  
**Merge Commit:** See `git log --oneline -1`  
**Date:** January 18, 2026

---

## Quick Rollback (Emergency Only)

If something goes wrong in production and you need to **immediately rollback**, use this:

```bash
# OPTION 1: Revert the entire merge commit (safest)
git revert -m 1 <merge-commit-hash>
git push origin main

# Example:
git revert -m 1 d79d666
git push origin main
```

---

## Complete Rollback Guide

### ✅ Step 1: Identify the Merge Commit

```bash
cd c:\CRBot

# See the merge commit hash
git log --oneline -n 10

# You'll see something like:
# a1b2c3d (HEAD -> main) merge(sltp): Merge intelligent SL/TP management system
# 5d931f2 (origin/main) Fix 3 Critical Trading Bugs
```

### ✅ Step 2: Choose Your Rollback Strategy

#### **Option A: Revert (Recommended for Production)**
```bash
# Reverts the entire merge, but keeps history
git revert -m 1 a1b2c3d

# This creates a NEW commit that undoes the merge
# Safe because it preserves history
git push origin main
```

#### **Option B: Reset (Use only if merge NOT pushed yet)**
```bash
# Resets to before the merge (DESTRUCTIVE)
git reset --hard 5d931f2

# WARNING: This loses the merge commit entirely
# Only use if NOT pushed to remote
```

#### **Option C: Selective Rollback (Advanced)**
```bash
# Rollback only specific files
git checkout 5d931f2 -- backend/app/services/sl_tp_manager.py
git commit -m "revert(sltp): Remove SLTPManager service"

# Then selectively remove other files as needed
git checkout 5d931f2 -- frontend/src/components/TradingSettings.jsx
git commit -m "revert(ui): Remove TradingSettings component"
```

---

## What Gets Reverted

If you rollback completely, these will be **removed/reverted**:

### ❌ Removed Files
```
backend/app/routes/settings.py          (264 lines)
backend/app/services/sl_tp_manager.py   (848 lines)
frontend/src/components/TradingSettings.jsx (599 lines)
database/migrations/007_create_user_trading_settings.sql
tests/test_sltp_manager.py              (592 lines)
tests/test_sltp_integration.py          (341 lines)
```

### ❌ Modified Files (Reverted)
```
backend/app/main.py
  └─ Removes: settings router import
  
backend/app/models/database_models.py
  └─ Removes: UserTradingSettings model
  
backend/app/services/bot_engine.py
  └─ Removes: SLTPManager integration
  
backend/app/services/ai_agent.py
  └─ Reverts: Re-enables SELL execution
  
frontend/src/components/Settings.jsx
  └─ Removes: Trading tab
```

### ❌ Documentation (Removed)
```
INTELLIGENT_SLTP_SUMMARY.md
TESTING_COMPLETION_CHECKLIST.md
TEST_REPORT.md
```

---

## Rollback Scenarios

### Scenario 1: Immediate Rollback (First 1-2 hours)
```bash
# Fastest revert
git revert -m 1 a1b2c3d
git push origin main

# Time: 2 minutes
# Risk: Low (reverts entire feature cleanly)
```

### Scenario 2: Partial Rollback (Database Issues)
```bash
# Keep code, remove database migration
git show a1b2c3d:database/migrations/007_create_user_trading_settings.sql > temp.sql

# Manually create DROP migration:
# database/migrations/008_drop_user_trading_settings.sql
CREATE DATABASE migration file to drop the table

# Apply it
psql -U user -d database -f database/migrations/008_drop_user_trading_settings.sql
```

### Scenario 3: Rollback Specific Component
```bash
# Rollback only AI Agent changes
git checkout 5d931f2 -- backend/app/services/ai_agent.py
git commit -m "revert(ai): Re-enable SELL execution (rollback)"

# Keep rest of SL/TP system
```

---

## Verification After Rollback

### ✅ Verify Rollback Succeeded

```bash
# Check current state
git log --oneline -n 5

# Should show:
# a1b2c3d Revert "merge(sltp): ..."
# a1b2c3d merge(sltp): Merge intelligent SL/TP...
# 5d931f2 Fix 3 Critical Trading Bugs

# Verify files removed
git ls-files | grep sltp_manager.py
# Should be EMPTY

# Verify AI Agent reverted
git show HEAD:backend/app/services/ai_agent.py | grep "def _execute_autonomous_trade"
# Should NOT contain "SELL delegated to SLTPManager"
```

### ✅ Verify Application Still Works

```bash
# Restart backend
cd backend
python app.py

# Check logs
# Should not have errors about SLTPManager

# Test old endpoints still work
curl http://localhost:8000/api/bots
# Should return 200 OK
```

---

## Git History After Rollback

### If you use `git revert`:

```
a1b2c3d (HEAD -> main) Revert "merge(sltp): Merge intelligent SL/TP..."
a1b2c3d merge(sltp): Merge intelligent SL/TP management system
d79d666 docs: Add testing completion checklist
...
5d931f2 (origin/main) Fix 3 Critical Trading Bugs
```

**History is preserved** ✅ - You can see what was reverted

### If you use `git reset --hard`:

```
5d931f2 (HEAD -> main, origin/main) Fix 3 Critical Trading Bugs
...
```

**History is lost** ❌ - Only use if not pushed

---

## Database Rollback

If you already applied the migration to Railway:

### ✅ Option 1: Create a DROP Migration

```sql
-- database/migrations/008_drop_user_trading_settings.sql
DROP TABLE IF EXISTS user_trading_settings CASCADE;
DROP TYPE IF EXISTS sl_tp_profile_enum CASCADE;
```

Then run:
```bash
# Apply to Railway
railway run python backend/apply_migrations.py
```

### ✅ Option 2: Manual Database Rollback

```bash
# Connect to Railway database
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME

# Drop table
DROP TABLE user_trading_settings CASCADE;
DROP TYPE sl_tp_profile_enum CASCADE;

# Verify
\dt  # Should not show user_trading_settings
```

---

## Prevention: Monitoring

### ✅ Monitor These After Merge

1. **API Endpoints**
   - Test all existing endpoints still work
   - Check `/api/bots`, `/api/trades`, etc.

2. **Bot Engine**
   - Monitor trade creation
   - Check SL/TP calculations
   - Watch for errors in logs

3. **AI Agent**
   - Monitor BUY signals
   - Verify SELL signals are ignored
   - Check position monitoring

4. **Database**
   - User settings table should exist
   - Check for migration errors
   - Monitor connection pools

### ✅ Sample Monitoring Commands

```bash
# Check logs for errors
tail -f logs/app.log | grep -i "error\|exception"

# Monitor trades being created
curl http://localhost:8000/api/trades | jq '.[] | {id, status, created_at}'

# Check AI Agent status
curl http://localhost:8000/api/ai/status

# Database health
psql -c "SELECT COUNT(*) FROM trades;"
```

---

## Timeline: When to Rollback

| Time Since Merge | Action | Urgency |
|------------------|--------|---------|
| 0-30 min | Any issue → Rollback | 🔴 CRITICAL |
| 30 min - 2 hrs | Real issue → Rollback | 🔴 CRITICAL |
| 2-6 hrs | Monitor, don't rollback | 🟡 HIGH |
| 6-24 hrs | Fix forward, patch | 🟢 MEDIUM |
| 24+ hrs | Fix forward, monitor | 🟢 LOW |

---

## If You Need Help

### 📞 Quick Reference

**Immediate revert (safest):**
```bash
git revert -m 1 <commit-hash>
git push origin main
```

**Check what would change:**
```bash
git diff main...feature/intelligent-sl-tp
```

**See merge details:**
```bash
git show <merge-commit-hash>
```

**Restore a file from before merge:**
```bash
git checkout 5d931f2 -- <filepath>
```

---

## Post-Rollback Steps

1. **Notify team** - Let developers know rollback was executed
2. **Document issue** - Create bug report with exact error
3. **Preserve logs** - Keep error logs for analysis
4. **Plan fix** - Decide if fix goes forward or creates new PR
5. **Test thoroughly** - Before next merge attempt

---

## Important Notes

⚠️ **CRITICAL:**
- Keep this guide accessible in your team wiki
- Train team on rollback procedures
- Test rollback in staging BEFORE production issue
- Never assume rollback won't be needed

✅ **GOOD PRACTICE:**
- Monitor first 24 hours closely
- Have rollback commit hash ready
- Keep database backups
- Document any issues immediately

---

## Contact / Questions

If you need to rollback or have questions:

1. **Check logs first** - Find the actual error
2. **Review this guide** - Pick appropriate strategy
3. **Test in staging** - Never rollback blind in production
4. **Execute carefully** - Verify each step

---

**Document Created:** January 18, 2026  
**Merge Commit:** feature/intelligent-sl-tp → main  
**Status:** Ready for production, with rollback safety

**Remember:** It's easier to rollback than to debug production issues! 🚀
