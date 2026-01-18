# 🤖 CRBot Custom Agent - Instructions

## 1️⃣ ARCHITECTURE SYSTEM
Tu travailles sur DeepPulseAI, une plateforme de day trading crypto avec:

### Backend
- **Framework:** FastAPI + SQLAlchemy ORM
- **Database:** Railway PostgreSQL (user_id filtering for multi-tenancy)
- **External APIs:** Binance (market data), DeepSeek (LLM), Supabase (auth JWT)
- **Key Services:**
  - BotEngine: 60s monitoring loop, strategy execution
  - RiskManager: Trade validation (position size, duplicates, daily limits)
  - 9 Strategies: All inherit from BaseStrategy (get_signal_direction, should_exit)
  - MLEngine: LSTM predictions with TensorFlow
  - AIAgent: DeepSeek analysis, autonomous bot creation

### Frontend
- React 18 + Vite, deployed on Vercel
- Supabase Auth (JWT tokens injected in API calls)
- Components: BotManager, Portfolio, Dashboard, AISettings

### Database Schema
- `bots` (id UUID, user_id UUID, strategy, status, config JSONB, symbols JSONB)
- `trades` (id UUID, user_id UUID, bot_id FK, symbol, entry/exit prices, status)
- `portfolios` (user_id UUID UNIQUE, cash_balance, total_value, daily/total_pnl)

---

## 2️⃣ RECENT BUGS FIXED (MEMORY)
You've just applied 5 critical fixes:

1. ✅ Grid Trading: Added state validation (SELL only if BUY exists)
2. ✅ RiskManager: Duplicate check now includes CLOSING status
3. ✅ BotEngine: Position size clamped to 25% max
4. ✅ BotEngine: Fallback amount enforces ABSOLUTE limits
5. ✅ Logging: Added [SIGNAL], [BLOCKED], [BUY-EXEC], [SELL-EXEC] prefixes

**Commit:** `5f05a87` - "Apply 5 critical Bug #2 fixes with comprehensive logging"

### ⚡ LATEST FEATURES ADDED (SLTP Integration)
- ✅ ATR calculation in market data
- ✅ NaN/invalid value validation
- ✅ Phase transitions (PENDING → VALIDATED → TRAILING)
- ✅ Trailing stop logic
- ✅ Fractional TP exits (TP1 50% + TP2 runner)
- ✅ Migration 009: trades table extended with take_profit_2, trade_phase, tp1_partial_executed

**Last Commits:**
- `217737b` - "fix(sl_tp): Add comprehensive NaN/invalid value validation"
- `fa05b4d` - "fix(bot_engine): Add cash availability check before trade execution"
- `7889785` - "feat(sltp): Integrate SLTPManager into trade monitoring"
- `47f34c2` - "fix(main): Add migration 009 to startup checks"

---

## 2️⃣ DATABASE MIGRATIONS - CRITICAL PATTERN

### ⚠️ WHEN YOU ADD A NEW MIGRATION:
1. **Create migration file** at `database/migrations/XXX_description.sql`
2. **MANDATORY:** Register in `backend/app/main.py` startup checks

### HOW TO ADD TO main.py:
```python
# Find the lifespan() function startup section (~line 40)
# Add new migration check AFTER previous ones:

# Check if [table/columns] exists, if not add them
try:
    db.execute(text("SELECT [column_to_check] FROM [table] LIMIT 1"))
    logger.info("[OK] [table] has [column]")
except Exception as check_error:
    try:
        logger.info(f"⚙️ Adding [column] to [table]...")
        
        migration_paths = [
            "/app/database/migrations/009_add_tp2_and_phase_to_trades.sql",  # Docker path
            "database/migrations/009_add_tp2_and_phase_to_trades.sql",       # Local path
            pathlib.Path(__file__).parent.parent.parent / "database/migrations/009_add_tp2_and_phase_to_trades.sql"
        ]
        
        migration_sql = None
        for path in migration_paths:
            try:
                migration_sql = open(path).read()
                logger.info(f"✅ Found migration at: {path}")
                break
            except:
                continue
        
        if migration_sql:
            db.execute(text(migration_sql))
            db.commit()
            logger.info("✅ [table] extended successfully")
        else:
            logger.error(f"❌ Could not find migration file")
    except Exception as create_error:
        logger.error(f"❌ Failed to execute migration: {create_error}")
```

### REAL EXAMPLE (lines 219-254 in main.py):
```python
# Check if trades table has TP2/phase columns, if not add them (migration 009)
try:
    db.execute(text("SELECT take_profit_2, trade_phase FROM trades LIMIT 1"))
    logger.info("[OK] trades table has TP2/phase columns")
except Exception as check_error:
    # Execute migration 009 if columns missing
```

### 🚀 WHY THIS MATTERS:
- **Without this:** Migration doesn't auto-execute on Railway deploy
- **With this:** Columns created automatically at startup, app never crashes
- **Idempotent:** Safe to run multiple times (checks first)

---

## 3️⃣ CODE PATTERNS (APPLY ALWAYS)

### Logging Pattern
```python
logger.info(f"📊 [SIGNAL] {bot_name} | {symbol} | {action}")
logger.info(f"⚠️ [BLOCKED] {symbol}: {reason}")
logger.info(f"✅ [BUY-EXEC] {symbol} | Qty: {qty} | Cost: ${cost}")


Risk Checks
PythonABSOLUTE_MAX_POSITION_PCT = 0.25  # 25% maxif cost > portfolio.total_value * 0.25:    cost = portfolio.total_value * 0.25db.query(Trade).filter(    Trade.status.in_(["OPEN", "CLOSING"])  # NOT just OPEN)Afficher plus de lignes

Reference Documents
📌 docs/planning/todoBug.md
📌 docs/planning/TODO.md
📌 docs/PROJECT_SPECIFICATIONS.md
📌 docs/architecture/
📌 docs/PHASE2_ML_INTEGRATION_SUMMARY.md

File Locations
Strategies:     backend/app/services/strategies/*.py
BotEngine:      backend/app/services/bot_engine.py
RiskManager:    backend/app/services/risk_manager.py
AI:             backend/app/services/ai_agent.py
                backend/app/services/ai_bot_controller.py
Frontend:       frontend/src/components/*.jsx
Routes:         backend/app/routes/*.py
Tests:          tests/
Docs:           docs/planning/